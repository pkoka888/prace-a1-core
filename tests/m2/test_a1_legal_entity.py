"""The LegalEntity record, the situation fields and the reviewed import.

Decisions D11a and D11b (2026-10-20). The record holds registry data about
a counterparty, never the fact that a person works for it: that fact lives on
the tenant-scoped Assignment. The record carries where it came from and when
it was verified, so a correction is traceable.

Synthetic only; no real private data, scans, or PII.
"""

import contextlib
import io
import json
import tempfile
from pathlib import Path

from django.db import transaction
from django.test import TestCase

from portal.release1a.models import Assignment, LegalEntity, Organization, Worker

REPO = Path(__file__).resolve().parents[2]

REVIEW_RECORD = {
    "registration_id": "00000000",
    "legal_name": "SYNTHETICKY OBCHODNIK",
    "legal_form": "sole_trader",
    "country_code": "CZ",
    "registered_address": {"street": "SYNTHETICKÁ ULICE", "city": "SYNTHETICKÁ OBC"},
    "nace_codes": ["43120"],
    "source": "https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty/00000000",
    "verified_on": "2026-01-01",
    "content_sha256": "0" * 64,
}


class LegalEntityModelTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(key="default", label="Default")

    def test_the_record_is_tenant_scoped_and_unique_per_registration(self):
        first = LegalEntity.objects.create(
            organization=self.organization,
            registration_id="00000000",
            legal_name="SYNTHETICKY OBCHODNIK",
        )
        LegalEntity.objects.create(
            organization=self.organization,
            registration_id="00000001",
            legal_name="DRUHÝ",
        )
        # A deliberate integrity error has to be contained, or it breaks the
        # transaction the rest of the test runs in.
        with self.assertRaises(Exception), transaction.atomic():
            LegalEntity.objects.create(
                organization=self.organization,
                registration_id="00000000",
                legal_name="DUPLICATE",
            )
        self.assertEqual(LegalEntity.objects.count(), 2)
        self.assertTrue(first.organization_id)

    def test_the_situation_fields_are_nullable(self):
        """Absent means "not captured", never a default."""
        for field in ("legal_entity", "nace_code"):
            self.assertTrue(Assignment._meta.get_field(field).null)
            self.assertTrue(Assignment._meta.get_field(field).blank)
        prior = Assignment._meta.get_field("prior_activity_start")
        self.assertTrue(prior.null)
        self.assertTrue(Assignment._meta.get_field("replaces_worker").null)

    def test_the_record_keeps_its_provenance(self):
        entity = LegalEntity.objects.create(
            organization=self.organization,
            registration_id="00000000",
            legal_name="SYNTHETICKY OBCHODNIK",
            source=REVIEW_RECORD["source"],
            verified_on="2026-01-01",
            content_sha256=REVIEW_RECORD["content_sha256"],
        )
        self.assertEqual(entity.source, REVIEW_RECORD["source"])
        self.assertEqual(entity.content_sha256, REVIEW_RECORD["content_sha256"])
        self.assertEqual(entity.legal_form, "company")

    def test_an_assignment_may_reference_a_legal_entity(self):
        worker = Worker.objects.create(
            organization=self.organization,
            given_name="Alena",
            family_name="Testová",
            birth_date="1990-01-01",
            activity_profile="employee",
        )
        entity = LegalEntity.objects.create(
            organization=self.organization,
            registration_id="00000000",
            legal_name="SYNTHETICKY OBCHODNIK",
        )
        assignment = Assignment.objects.create(
            organization=self.organization,
            worker=worker,
            workplace_label="SYNTHETICKÉ",
            activity_label="SYNTHETICKÁ ČINNOST",
            start="2026-01-01",
            end="2026-12-31",
            legal_entity=entity,
            nace_code="43120",
        )
        assignment.refresh_from_db()
        self.assertEqual(assignment.legal_entity_id, entity.pk)
        self.assertEqual(assignment.nace_code, "43120")


class AresImportTests(TestCase):
    """The reviewed import: retrieve, look, then store."""

    def setUp(self):
        self.organization = Organization.objects.create(key="default", label="Default")

    def test_a_reviewed_record_is_stored_with_its_provenance(self):
        from scripts.import_ares_legal_entity import _store

        with tempfile.TemporaryDirectory(prefix="ares-review-") as temporary:
            path = Path(temporary) / "review.json"
            path.write_text(json.dumps(REVIEW_RECORD), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(_store(path), 0)
        entity = LegalEntity.objects.get(registration_id="00000000")
        self.assertEqual(entity.legal_name, "SYNTHETICKY OBCHODNIK")
        self.assertEqual(entity.legal_form, "sole_trader")
        self.assertEqual(entity.source, REVIEW_RECORD["source"])
        self.assertEqual(entity.content_sha256, REVIEW_RECORD["content_sha256"])
        self.assertEqual(entity.nace_codes, ["43120"])

    def test_storing_the_same_registration_twice_updates_it(self):
        from scripts.import_ares_legal_entity import _store

        with tempfile.TemporaryDirectory(prefix="ares-review-") as temporary:
            path = Path(temporary) / "review.json"
            path.write_text(json.dumps(REVIEW_RECORD), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                _store(path)
            changed = {**REVIEW_RECORD, "legal_name": "PŘEJMENOVANÝ"}
            path.write_text(json.dumps(changed), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                _store(path)
        self.assertEqual(LegalEntity.objects.count(), 1)
        entity = LegalEntity.objects.get(registration_id="00000000")
        self.assertEqual(entity.legal_name, "PŘEJMENOVANÝ")
