import json
import tempfile
import unittest
from pathlib import Path

from pypdf import PdfReader

from scripts.a1_core import (
    A1ValidationError,
    build_form_data,
    czech_display_case,
    enrich_residence,
    generate_a1_pdf,
    normalize_date,
    mark_provisional,
    provisional_one_year_period,
    validate_provisional_issue_date,
    validate_form_data,
    render_overlay,
)


ROOT = Path(__file__).resolve().parents[1]


def complete_employee(status_profile="self_employed_multi_state"):
    return {
        "id": "synthetic-person",
        "person": {
            "insurance_number": "900101/0007",
            "surname": "TESTOVÁ",
            "given_name": "ALENA",
            "dob": "01.01.1990",
            "birth_place": "TESTOV",
            "nationality": "CZ",
            "sex": "F",
        },
        "residence": {
            "street": "BYTOVÁ",
            "house_number": "1",
            "city": "TESTOV",
            "postal_code": "100 00",
            "country_code": "CZ",
        },
        "employment": {
            "kind": "self_employed",
            "employer_id": "SYNTHETIC-ID",
            "employer_name": "TESTOVACÍ PODNIK",
            "street": "PODNIKATELSKÁ",
            "house_number": "2",
            "city": "TESTOV",
            "postal_code": "100 00",
            "country_code": "CZ",
        },
        "certificate": {
            "member_state": "CZ",
            "document_id": "SYNTHETIC-DOC",
            "start_date": "01.01.2026",
            "end_date": "31.12.2026",
        },
        "a1": {
            "status_profile": status_profile,
            "institution_profile": "synthetic-office",
        },
    }


def synthetic_institution():
    return {"institution": {"name": "TEST OFFICE"}, "certificate": {}}


class A1CoreUnitTests(unittest.TestCase):
    """Core journey: one reviewed employee record becomes deterministic A1 data."""

    def test_normalize_date_accepts_card_formats(self):
        self.assertEqual("22.05.1994", normalize_date("22/05/1994"))
        self.assertEqual("07.01.1989", normalize_date("07.01.1989"))

    def test_czech_display_case_for_names_places_and_streets(self):
        self.assertEqual("Pavel Kašpar", czech_display_case("PAVEL KAŠPAR"))
        self.assertEqual("Tyrše a Fügnera", czech_display_case("TYRŠE A FÜGNERA"))
        self.assertEqual("Ústí nad Labem", czech_display_case("ÚSTÍ NAD LABEM"))
        self.assertEqual("Frýdek-Místek", czech_display_case("FRÝDEK-MÍSTEK"))

    def test_provisional_issue_date_policy(self):
        self.assertEqual(
            "12.02.2026", validate_provisional_issue_date("12.02.2026", "11.08.2026")
        )
        with self.assertRaisesRegex(A1ValidationError, "Monday or Thursday"):
            validate_provisional_issue_date("13.02.2026", "11.08.2026")
        with self.assertRaisesRegex(A1ValidationError, "61–180 days"):
            validate_provisional_issue_date("10.08.2026", "11.08.2026")
        with self.assertRaisesRegex(A1ValidationError, "61–180 days"):
            validate_provisional_issue_date("12.02.2026", "12.08.2026")
        self.assertEqual(
            ("12.02.2026", "11.02.2027"), provisional_one_year_period("12.02.2026")
        )

    def test_enrichment_uses_specific_municipality_and_district_rule(self):
        rules = {
            "rules": [
                {
                    "city": "LITVÍNOV",
                    "district": "CHUDEŘÍN",
                    "postal_code": "436 03",
                    "ossz": "OSSZ Most",
                    "source": "official-test-source",
                    "verified_on": "2026-08-11",
                }
            ]
        }
        residence = {"city": "Litvínov", "district": "Chudeřín"}
        enriched, evidence = enrich_residence(residence, rules)
        self.assertEqual("436 03", enriched["postal_code"])
        self.assertEqual("OSSZ Most", enriched["ossz"])
        self.assertEqual("official-test-source", evidence[0]["source"])

    def test_build_form_data_never_reuses_another_employees_identity(self):
        employee = {
            "id": "synthetic-citizen-01",
            "person": {
                "surname": "NOVÁKOVÁ",
                "given_name": "ALENA",
                "dob": "26.05.1985",
                "insurance_number": "900101/0007",
                "birth_place": "TESTOV",
                "nationality": "ČESKÁ REPUBLIKA",
                "sex": "M",
            },
            "residence": {
                "street": "RADNIČNÍ",
                "house_number": "1148",
                "city": "TESTOV",
                "postal_code": "738 01",
                "country_code": "CZ",
            },
            "employment": {
                "kind": "self_employed",
                "employer_id": "TEST-ID-001",
                "employer_name": "ALENA NOVÁKOVÁ",
                "street": "PODNIKATELSKÁ",
                "house_number": "2",
                "city": "TESTOV",
                "postal_code": "738 01",
                "country_code": "CZ",
            },
            "a1": {
                "status_profile": "self_employed_multi_state",
                "institution_profile": "frydek-mistek",
            },
        }
        institution = json.loads((ROOT / "config/institution.json").read_text(encoding="utf-8"))
        form = build_form_data(employee, institution)
        serialized = json.dumps(form, ensure_ascii=False)
        self.assertIn("ALENA", serialized)
        self.assertNotIn("OTHER-A", serialized)
        self.assertNotIn("OTHER-B", serialized)

    def test_validation_blocks_incomplete_identity_or_address(self):
        with self.assertRaises(A1ValidationError):
            validate_form_data(
                {
                    "person": {"surname": "NOVÁK", "given_name": "JAN"},
                    "residence": {},
                    "certificate": {},
                }
            )

    def test_untrusted_nested_data_cannot_change_certificate_or_checkboxes(self):
        baseline = complete_employee()
        mutated = complete_employee()
        mutated["employment"]["posting"] = {
            "country": "DE",
            "no_fixed_address": True,
            "status_profile": "employee_multi_state",
        }
        expected = build_form_data(baseline, synthetic_institution())
        actual = build_form_data(mutated, synthetic_institution())
        self.assertEqual("CZ", actual["certificate"]["member_state"])
        self.assertEqual(expected["certificate"], actual["certificate"])
        self.assertEqual(expected["residence"], actual["residence"])
        self.assertEqual(expected["status_osv_c_multistate"], actual["status_osv_c_multistate"])
        self.assertEqual(expected["status_posted_employee"], actual["status_posted_employee"])
        self.assertFalse(actual["no_fixed_address"])

    def test_missing_explicit_employment_fields_fail_closed(self):
        employee = complete_employee()
        employee["employment"] = {"kind": "self_employed"}
        with self.assertRaisesRegex(A1ValidationError, "employment.employer_id"):
            build_form_data(employee, synthetic_institution())

    def test_supported_profiles_select_only_their_declared_checkboxes(self):
        self_employed = build_form_data(complete_employee(), synthetic_institution())
        employed = build_form_data(
            complete_employee("employee_multi_state"), synthetic_institution()
        )
        self.assertTrue(self_employed["status_osv_c_multistate"])
        self.assertTrue(self_employed["employer_type_self_employed"])
        self.assertFalse(self_employed["status_posted_employee"])
        self.assertFalse(self_employed["employer_type_employee"])
        self.assertTrue(employed["status_posted_employee"])
        self.assertTrue(employed["employer_type_employee"])
        self.assertFalse(employed["status_osv_c_multistate"])
        self.assertFalse(employed["employer_type_self_employed"])

    def test_missing_or_unsupported_status_profile_fails(self):
        for profile in (None, "", "unsupported"):
            employee = complete_employee()
            if profile is None:
                employee.pop("a1")
            else:
                employee["a1"]["status_profile"] = profile
            with self.subTest(profile=profile), self.assertRaisesRegex(
                A1ValidationError, "Missing or unsupported"
            ):
                build_form_data(employee, synthetic_institution())

    def test_institution_provenance_uses_selected_profile_path(self):
        form = build_form_data(complete_employee(), synthetic_institution())
        self.assertEqual(
            "config/institutions/synthetic-office.json",
            form["meta"]["institution_source"],
        )

    def test_layout_uses_visually_reviewed_row_baselines(self):
        layout = json.loads((ROOT / "config/a1_layout.json").read_text(encoding="utf-8"))
        self.assertEqual(453.5, layout["fields"]["person.insurance_number"]["y"])
        self.assertEqual(605, layout["fields"]["activity.address"]["y"])
        self.assertEqual(195, layout["fields"]["institution.issue_date"]["y"])
        self.assertEqual(180.5, layout["fields"]["institution.signed_by"]["y"])
        self.assertNotIn("font_scale", layout)
        self.assertTrue(all("y_offset" not in field for field in layout["fields"].values()))

    def test_dynamic_self_employed_checkboxes_are_only_on_page_two(self):
        layout = json.loads((ROOT / "config/a1_layout.json").read_text(encoding="utf-8"))
        self.assertEqual(
            {1}, {box["page"] for box in layout["checkboxes"].values()}
        )
        form = {
            "meta": {"status_profile": "self_employed_multi_state"},
            "person": {}, "residence": {}, "employment": {}, "certificate": {},
            "institution": {}, "activity": {},
            "status_osv_c_multistate": True,
            "employer_type_self_employed": True,
        }
        overlay = PdfReader(render_overlay(form, layout))
        page_one = overlay.pages[0].get_contents().get_data()
        page_two = overlay.pages[1].get_contents().get_data()
        self.assertNotIn(b" re", page_one)
        self.assertIn(b" re", page_two)
        self.assertNotIn(b"1 1 1 rg", page_two)

    def test_layout_documents_printed_a1_sections(self):
        layout = json.loads((ROOT / "config/a1_layout.json").read_text(encoding="utf-8"))
        self.assertEqual("1.1", layout["fields"]["person.insurance_number"]["section"])
        self.assertEqual("6.10", layout["fields"]["institution.issue_date"]["section"])
        self.assertEqual("6.11", layout["fields"]["institution.signed_by"]["section"])
        self.assertEqual("3.4", layout["checkboxes"]["status_osv_c_multistate"]["section"])
        self.assertTrue(all("section" in field for field in layout["fields"].values()))
        self.assertTrue(all("section" in box for box in layout["checkboxes"].values()))


class A1CoreIntegrationTests(unittest.TestCase):
    """Operator journey: the CLI core emits a clean, three-page static PDF."""

    def test_generated_pdf_preserves_shell_and_contains_only_new_identity(self):
        employee = {
            "id": "test-person",
            "person": {
                "insurance_number": "900101/0007",
                "surname": "NOVÁKOVÁ",
                "given_name": "ALENA",
                "dob": "26.05.1985",
                "birth_place": "TESTOV",
                "nationality": "ČESKÁ REPUBLIKA",
                "sex": "M",
            },
            "residence": {
                "street": "RADNIČNÍ",
                "house_number": "1148",
                "city": "TESTOV",
                "postal_code": "738 01",
                "country_code": "CZ",
            },
            "employment": {
                "employer_id": "900101/0007",
                "employer_name": "ALENA NOVÁKOVÁ",
                "street": "RADNIČNÍ",
                "house_number": "1148",
                "city": "TESTOV",
                "postal_code": "738 01",
                "country_code": "CZ",
            },
            "a1": {"status_profile": "self_employed_multi_state"},
        }
        institution = json.loads((ROOT / "config/institution.json").read_text(encoding="utf-8"))
        form = build_form_data(employee, institution)

        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "a1.pdf"
            generate_a1_pdf(
                form,
                ROOT / "templates/a1_background.pdf",
                ROOT / "config/a1_layout.json",
                output,
            )
            reader = PdfReader(str(output))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            self.assertEqual(3, len(reader.pages))
            self.assertIn("ALENA", text)
            self.assertIn("NOVÁKOVÁ", text)
            self.assertNotIn("OTHER-C", text)
            self.assertNotIn("{{", text)
            self.assertFalse(reader.get_fields())


if __name__ == "__main__":
    unittest.main()
