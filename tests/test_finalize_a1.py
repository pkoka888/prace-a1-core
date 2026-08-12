import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.finalize_a1 import (
    CSV_FIELDS,
    FinalizationError,
    generate_final_set,
    read_review,
    readiness_report,
    validate_review,
)
from scripts.generate_provisional_a1 import (
    build_provisional_rows,
    document_id_for_issue_year,
)


ROOT = Path(__file__).resolve().parents[1]


def employee(employee_id, surname, given_name, dob, insurance_number):
    return {
        "id": employee_id,
        "person": {
            "surname": surname,
            "given_name": given_name,
            "dob": dob,
            "birth_place": "TEPLICE",
            "nationality": "ČESKÁ REPUBLIKA",
            "insurance_number": insurance_number,
            "sex": "M",
        },
        "residence": {
            "street": "TESTOVACÍ",
            "house_number": "1",
            "city": "TEPLICE",
            "district": "TEPLICE",
            "postal_code": "415 01",
            "country_code": "CZ",
        },
        "employment": {"kind": "self_employed"},
        "a1": {"status_profile": "self_employed_multi_state"},
        "provenance": {"scans": [f"{employee_id}-op1.jpeg"]},
    }


def review_row(source, document_id):
    person = source["person"]
    residence = source["residence"]
    row = {field: "" for field in CSV_FIELDS}
    row.update(
        {
            "employee_id": source["id"],
            "source_scans": f"{source['id']}-op1.jpeg",
            "surname": person["surname"],
            "given_name": person["given_name"],
            "dob": person["dob"],
            "birth_place": person["birth_place"],
            "nationality": person["nationality"],
            "sex": person["sex"],
            "insurance_number": person["insurance_number"],
            "street": residence["street"],
            "house_number": residence["house_number"],
            "city": residence["city"],
            "district": residence["district"],
            "postal_code": residence["postal_code"],
            "country_code": residence["country_code"],
            "status_profile": "self_employed_multi_state",
            "activity_name": "Testovací samostatná činnost",
            "activity_address": "Německo, bez stálé adresy",
            "employment_id": "TEST-ID-001",
            "employment_name": "TESTOVACÍ OSOBA",
            "employment_street": "PODNIKATELSKÁ",
            "employment_house_number": "2",
            "employment_city": "TEPLICE",
            "employment_postal_code": "415 01",
            "employment_country_code": "CZ",
            "resolved_ossz": "OSSZ Teplice",
            "institution_profile": "teplice-test",
            "document_id": document_id,
            "start_date": "01.01.2026",
            "end_date": "31.12.2026",
            "issue_date": "01.01.2026",
            "signed_by": "TEST SIGNATORY",
            "identity_reviewed": "YES",
            "certificate_reviewed": "YES",
            "approved_for_pdf": "YES",
            "validated_by_user": "1",
            "activity_source": "signed activity declaration 2026-01-01",
            "activity_source_status": "AUTHORITATIVE",
            "certificate_source": "issued certificate register 2026",
            "certificate_source_status": "AUTHORITATIVE",
            "signatory_source": "official delegation record 2026",
            "signatory_source_status": "AUTHORITATIVE",
        }
    )
    return row


class FinalizationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.employees = [
            employee("anna-test", "TESTOVÁ", "ANNA", "01.02.1990", "900201/1234"),
            employee("bert-test", "PŘÍKLAD", "BERT", "03.04.1985", "850403/5678"),
        ]
        self.employees_path = self.base / "employees.json"
        self.employees_path.write_text(
            json.dumps({"employees": self.employees}, ensure_ascii=False), encoding="utf-8"
        )
        self.profile_dir = self.base / "profiles"
        self.profile_dir.mkdir()
        (self.profile_dir / "teplice-test.json").write_text(
            json.dumps(
                {
                    "version": "test",
                    "review_status": "VERIFIED",
                    "source_url": "https://example.invalid/official-institution-record",
                    "verified_on": "01.01.2026",
                    "expected_ossz": "OSSZ Teplice",
                    "institution": {
                        "name": "TEST OSSZ Teplice",
                        "street": "Přítkovská",
                        "house_number": "1",
                        "city": "Teplice",
                        "postal_code": "415 02",
                        "country_code": "CZ",
                        "code": "TEST",
                    },
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        self.review_path = self.base / "review.csv"

    def tearDown(self):
        self.temp.cleanup()

    def write_rows(self, rows):
        with self.review_path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS)
            writer.writeheader()
            writer.writerows(rows)

    def test_unapproved_row_blocks_finalization(self):
        rows = [review_row(self.employees[0], "DOC-A"), review_row(self.employees[1], "DOC-B")]
        rows[1]["approved_for_pdf"] = "NO"
        self.write_rows(rows)
        with self.assertRaisesRegex(FinalizationError, "approved_for_pdf must be YES"):
            validate_review(read_review(self.review_path), self.employees_path, self.profile_dir)

    def test_duplicate_document_id_blocks_finalization(self):
        rows = [review_row(self.employees[0], "DOC-A"), review_row(self.employees[1], "DOC-A")]
        self.write_rows(rows)
        with self.assertRaisesRegex(FinalizationError, "unique document_id"):
            validate_review(read_review(self.review_path), self.employees_path, self.profile_dir)

    def test_user_validation_is_required(self):
        rows = [review_row(self.employees[0], "DOC-A"), review_row(self.employees[1], "DOC-B")]
        rows[0]["validated_by_user"] = "0"
        self.write_rows(rows)
        with self.assertRaisesRegex(FinalizationError, "validated_by_user must be 1"):
            validate_review(read_review(self.review_path), self.employees_path, self.profile_dir)

    def test_readiness_reports_all_rows_and_missing_authorities(self):
        rows = [review_row(self.employees[0], "DOC-A"), review_row(self.employees[1], "DOC-B")]
        rows[0]["activity_source"] = ""
        rows[0]["activity_source_status"] = "UNVERIFIED"
        rows[1]["validated_by_user"] = "0"
        report = readiness_report(rows)
        self.assertFalse(report["ready"])
        self.assertEqual(2, report["blocked_employee_count"])
        self.assertIn("missing activity_source", report["employees"][0]["blockers"])
        self.assertIn("activity_source_status is not AUTHORITATIVE", report["employees"][0]["blockers"])
        self.assertIn("validated_by_user must be 1", report["employees"][1]["blockers"])

    def test_assumed_certificate_source_is_rejected(self):
        rows = [review_row(self.employees[0], "DOC-A"), review_row(self.employees[1], "DOC-B")]
        rows[0]["certificate_source"] = "dates copied from another employee"
        self.write_rows(rows)
        with self.assertRaisesRegex(FinalizationError, "assumption, not an authority"):
            validate_review(read_review(self.review_path), self.employees_path, self.profile_dir)

    def test_identity_must_match_normalized_scan_record(self):
        rows = [review_row(self.employees[0], "DOC-A"), review_row(self.employees[1], "DOC-B")]
        rows[0]["birth_place"] = "MOST"
        self.write_rows(rows)
        with self.assertRaisesRegex(FinalizationError, "differs from normalized scan source: birth_place"):
            validate_review(read_review(self.review_path), self.employees_path, self.profile_dir)

    def test_female_birth_number_month_offset_matches_dob(self):
        self.employees[0]["person"]["sex"] = "F"
        self.employees[0]["person"]["insurance_number"] = "905201/1234"
        self.employees_path.write_text(
            json.dumps({"employees": self.employees}, ensure_ascii=False), encoding="utf-8"
        )
        rows = [review_row(self.employees[0], "DOC-A"), review_row(self.employees[1], "DOC-B")]
        self.write_rows(rows)
        self.assertEqual(2, len(validate_review(read_review(self.review_path), self.employees_path, self.profile_dir)))

    def test_profile_requires_provenance(self):
        profile_path = self.profile_dir / "teplice-test.json"
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        del profile["source_url"]
        profile_path.write_text(json.dumps(profile), encoding="utf-8")
        rows = [review_row(self.employees[0], "DOC-A"), review_row(self.employees[1], "DOC-B")]
        self.write_rows(rows)
        with self.assertRaisesRegex(FinalizationError, "needs source_url and verified_on provenance"):
            validate_review(read_review(self.review_path), self.employees_path, self.profile_dir)

    def test_complete_review_publishes_verified_set(self):
        rows = [review_row(self.employees[0], "DOC-A"), review_row(self.employees[1], "DOC-B")]
        self.write_rows(rows)
        approved_review = self.review_path.read_bytes()
        approved_review_sha256 = hashlib.sha256(approved_review).hexdigest()
        output = self.base / "final"
        generate_final_set(
            self.review_path,
            self.employees_path,
            self.profile_dir,
            ROOT / "templates/a1_background.pdf",
            ROOT / "config/a1_layout.json",
            output,
        )
        self.assertEqual(
            {"A1_anna-test.pdf", "A1_bert-test.pdf", "generation_manifest.json"},
            {path.name for path in output.iterdir()},
        )
        manifest = json.loads((output / "generation_manifest.json").read_text())
        self.assertEqual(2, len(manifest["generated"]))
        self.assertEqual({"DOC-A", "DOC-B"}, {item["document_id"] for item in manifest["generated"]})
        self.assertEqual(approved_review, self.review_path.read_bytes())
        self.assertEqual(approved_review_sha256, manifest["review_sha256"])
        self.assertTrue(manifest["generated_at"])
        self.assertEqual(
            {manifest["generated_at"]},
            {item["pdf_created"] for item in manifest["generated"]},
        )

    def test_tracked_provisional_config_contains_policy_only(self):
        config = json.loads(
            (ROOT / "config/a1_provisional.json").read_text(encoding="utf-8")
        )
        self.assertEqual("DE, CZ", config["activity_address"])
        self.assertFalse(
            {"additional_people", "issue_dates", "document_ids"} & set(config)
        )

    def test_document_id_year_token_reflects_issue_date(self):
        self.assertEqual(
            "N650212S000/2026/DE",
            document_id_for_issue_year("N650212S000/{year}/DE", "16.03.2026"),
        )
        self.assertEqual(
            "N650212S000/2027/DE",
            document_id_for_issue_year("N650212S000/{year}/DE", "01.09.2027"),
        )

    def test_document_id_explicit_year_must_match_issue_date(self):
        self.assertEqual(
            "N650212S000/2026/DE",
            document_id_for_issue_year("N650212S000/2026/DE", "16.03.2026"),
        )
        with self.assertRaisesRegex(FinalizationError, "does not reflect 6.10 issue year"):
            document_id_for_issue_year("N650212S000/2025/DE", "16.03.2026")

    def test_provisional_document_ids_are_unique_after_year_binding(self):
        profile_path = self.profile_dir / "teplice-test.json"
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        profile["current_office_contact"] = {"name": "TEST CONTACT", "role": "director"}
        profile_path.write_text(json.dumps(profile), encoding="utf-8")
        rows = [review_row(self.employees[0], "N65DOC-A/{year}/DE")]
        self.write_rows(rows)
        config_path = self.base / "a1_provisional.json"
        config_path.write_text(json.dumps({
            "issue_date_reference": "11.08.2026",
            "activity_name": "x",
            "activity_address": "DE, CZ",
        }), encoding="utf-8")
        cohort_path = self.base / "cohort.json"
        cohort_path.write_text(json.dumps({
            "issue_dates": {"anna-test": "11.06.2026"},
            "document_ids": {"anna-test": "N65DOC-A/{year}/DE"},
            "additional_people": [],
        }), encoding="utf-8")
        built, _ = build_provisional_rows(
            self.review_path, self.profile_dir, config_path, cohort_path
        )
        self.assertEqual("N65DOC-A/2026/DE", built[0][0]["document_id"])

    def test_verified_project_profiles_contain_no_placeholder_values(self):
        markers = ("tbd", "doplnit", "placeholder")
        for path in (ROOT / "config/institutions").glob("*.json"):
            profile = json.loads(path.read_text(encoding="utf-8"))
            if profile.get("review_status") != "VERIFIED":
                continue
            institution = profile.get("institution", {})
            for field in ("name", "street", "house_number", "city", "postal_code", "code"):
                value = str(institution.get(field, "")).casefold()
                self.assertTrue(value, f"{path.name}: verified profile missing {field}")
                self.assertFalse(
                    any(marker in value for marker in markers),
                    f"{path.name}: verified profile has placeholder {field}",
                )


if __name__ == "__main__":
    unittest.main()
