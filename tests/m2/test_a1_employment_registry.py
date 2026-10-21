"""The employer row against the business register.

Gate D15 (2026-10-21). Section 4 of the A1 form — the employer's code,
name and seat — is a legal claim about a counterparty. The repository says
where the activity, the certificate and the signatory came from, and said
nothing about the employer, so a registry-verified employer and a hand-typed
one were indistinguishable. Two reviewed employer records made that visible.

The register is the authority for a company's registered name and seat, so a
row that disagrees with it is reported, never silently replaced.

Synthetic only; no real private data, scans, or PII.
"""

from django.test import TestCase

from portal.release1a.models import (
    Assignment,
    LegalEntity,
    Organization,
    Worker,
    WorkerIdentityRevision,
)


def _employee(organization, *, employer_name="SYNTHETICKÝ ZAMĚSTNAVATEL",
              employer_street="SYNTHETICKÁ ULICE", employer_city="TEPLICE",
              employer_postal_code="415 01"):
    worker = Worker.objects.create(
        organization=organization,
        given_name="Alena",
        family_name="Testová",
        birth_date="1990-01-01",
        activity_profile="employee",
    )
    WorkerIdentityRevision.objects.create(
        organization=organization,
        worker=worker,
        revision_number=1,
        confirmed_fields={"surname": "Testová", "given_name": "Alena"},
    )
    assignment = Assignment.objects.create(
        organization=organization,
        worker=worker,
        workplace_label="SYNTHETICKÉ",
        activity_label="SYNTHETICKÁ ČINNOST",
        start="2026-01-01",
        end="2026-12-31",
        a1_facts_json={
            "status_profile": "posted_employee",
            "employment": {
                "employer_id": "00000000",
                "employer_name": employer_name,
                "street": employer_street,
                "house_number": "1",
                "city": employer_city,
                "postal_code": employer_postal_code,
                "country_code": "CZ",
            },
        },
    )
    return worker, assignment


class EmploymentRegistryComparisonTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(key="default", label="Default")
        self.worker, self.assignment = _employee(self.organization)

    def _entity(self, **overrides):
        defaults = {
            "organization": self.organization,
            "registration_id": "00000000",
            "legal_name": "SYNTHETICKÝ ZAMĚSTNAVATEL",
            "legal_form": "company",
            "country_code": "CZ",
            "registered_address": {
                "street": "SYNTHETICKÁ ULICE",
                "city": "TEPLICE",
                "postal_code": "415 01",
            },
            "nace_codes": ["43120"],
            "source": "https://ares.gov.cz/example",
            "content_sha256": "0" * 64,
        }
        defaults.update(overrides)
        return LegalEntity.objects.create(**defaults)

    def test_a_row_that_agrees_with_the_register_is_verified(self):
        from portal.release1a.a1_exports import _employment_divergence

        entity = self._entity()
        row = {
            "employment_name": entity.legal_name,
            "employment_street": entity.registered_address["street"],
            "employment_city": entity.registered_address["city"],
            "employment_postal_code": entity.registered_address["postal_code"],
        }
        assert _employment_divergence(row, entity) == []

    def test_a_row_that_differs_is_reported_not_replaced(self):
        from portal.release1a.a1_exports import _employment_divergence

        entity = self._entity()
        row = {
            "employment_name": "JINÝ NÁZEV",
            "employment_street": entity.registered_address["street"],
            "employment_city": entity.registered_address["city"],
            "employment_postal_code": entity.registered_address["postal_code"],
        }
        differences = _employment_divergence(row, entity)
        assert any("name differs" in d for d in differences)
        # The row is not touched: the divergence is reported, not applied.
        assert row["employment_name"] == "JINÝ NÁZEV"

    def test_a_fact_the_row_does_not_state_is_reported(self):
        from portal.release1a.a1_exports import _employment_divergence

        entity = self._entity()
        row = {
            "employment_name": entity.legal_name,
            "employment_street": "",
            "employment_city": entity.registered_address["city"],
            "employment_postal_code": entity.registered_address["postal_code"],
        }
        assert any("street is not stated" in d for d in _employment_divergence(row, entity))

    def test_no_record_means_no_divergence(self):
        from portal.release1a.a1_exports import _employment_divergence

        assert _employment_divergence({"employment_name": "X"}, None) == []

    def test_the_comparison_ignores_case_and_spacing(self):
        from portal.release1a.a1_exports import _employment_divergence

        entity = self._entity()
        row = {
            "employment_name": "  synthetický   zaměstnavatel ",
            "employment_street": entity.registered_address["street"],
            "employment_city": entity.registered_address["city"],
            "employment_postal_code": entity.registered_address["postal_code"],
        }
        assert _employment_divergence(row, entity) == []


class EmploymentSourceStatusGateTests(TestCase):
    """The authoritative path refuses an employer that diverges."""

    def setUp(self):
        self.organization = Organization.objects.create(key="default", label="Default")
        self.worker, self.assignment = _employee(self.organization)
        LegalEntity.objects.create(
            organization=self.organization,
            registration_id="00000000",
            legal_name="JINÝ NÁZEV V REGISTRU",
            registered_address={"street": "JINÁ ULICE"},
        )

    def test_a_divergent_row_is_refused_before_issue(self):
        from scripts.finalize_a1 import FinalizationError, _check_employer_agreement

        row = {
            "employee_id": self.worker.id,
            "employment_source_status": "DIVERGES_FROM_REGISTER",
        }
        with self.assertRaises(FinalizationError) as raised:
            _check_employer_agreement(self.worker.id, row)
        self.assertIn("diverges from the business register", str(raised.exception))

    def test_a_verified_row_passes(self):
        from scripts.finalize_a1 import _check_employer_agreement

        _check_employer_agreement(
            self.worker.id, {"employment_source_status": "REGISTRY_VERIFIED"}
        )

    def test_a_row_with_no_record_is_not_refused(self):
        """Absence is "not stated", and the reviewer decides."""
        from scripts.finalize_a1 import _check_employer_agreement

        _check_employer_agreement(self.worker.id, {})
