"""Synthetic regression checks for the private scan/worker merge export.

Every fixture is invented in a temporary directory. No operational record,
scan, OCR output or OSSZ profile is read and nothing is written into the
repository tree.
"""

from __future__ import annotations

import csv
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path

from scripts import run_scan_worker_merge as merge


def _workers(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return {row["employee_id"]: row for row in csv.DictReader(handle)}


class MergeExportTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.root = Path(self._temporary.name)
        self.addCleanup(self._temporary.cleanup)
        self._write_fixtures()

    def _write(self, relative: str, text: str, *, bom: bool = False) -> Path:
        target = self.root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(("\ufeff" if bom else "") + text, encoding="utf-8")
        return target

    def _write_fixtures(self) -> None:
        for name in (
            "synthetic-worker-a-op1.jpeg",
            "synthetic-worker-a-zp1.jpeg",
            "synthetic-worker-b-op1.jpeg",
            "synthetic-worker-b-zp1.jpeg",
            "synthetic-worker-d-op1.jpeg",
            "synthetic-worker-e-op1.jpeg",
        ):
            (self.root / "scans/processed").mkdir(parents=True, exist_ok=True)
            (self.root / "scans/processed" / name).write_bytes(b"synthetic")

        self._write(
            "a1/review.csv",
            "employee_id,source_scans,surname,given_name,resolved_ossz,"
            "institution_profile,status_profile,employment_id,employment_name\n"
            "synthetic-worker-a,scans/incoming/synthetic-worker-a-op1.jpeg,"
            "TESTER,ALPHA,OSSZ Teplice,teplice,EMPLOYED,17511267,Jan Šlauf\n",
            bom=True,
        )
        self._write(
            "ocr/new_people_review.csv",
            "employee_id,source_scans,surname,health_insurance_number,insurer,"
            "resolved_ossz,institution_profile\n"
            "synthetic-worker-c,scans/processed/synthetic-worker-a-op1.jpeg,"
            "SAMPLE,111222333,SYNTHETIC INSURER,OSSZ Teplice,teplice\n",
            bom=True,
        )
        self._write(
            "ocr/new_scans_ocr2.json",
            json.dumps({
                "synthetic-worker-b-op1.jpeg": {
                    "fields": {"rodne_cislo": "000101/0001", "op_valid_from": "2020-01-01",
                               "insurance_number": "999999999", "note_text": "unmapped"},
                    "model": "synthetic",
                },
                "synthetic-worker-b-zp1.jpeg": {
                    "fields": {"insurance_number": "111222333", "insurer": "ZP SYNTHETIC",
                               "insurer_code": "999", "zp_card_valid_until": "2030-12-31"},
                    "model": "synthetic",
                },
            }),
        )
        self._write(
            "ocr/new_scans_merged.json",
            json.dumps({
                "synthetic-worker-b": [
                    ["synthetic-worker-b-op1.jpeg", {"personal_id_number": "0001010001",
                                                     "surname": "SAMPLE"}],
                ],
            }),
        )
        self._write(
            "config/institutions/teplice.json",
            json.dumps({
                "institution": {"name": "OSSZ Teplice", "code": "SYN"},
                "current_office_contact": {"address": "Synthetic 1"},
                "review_status": "VERIFIED",
            }),
        )
        self._write(
            "runtime/portal/temporary/ossz-research-abc/report.json",
            json.dumps({
                "status": "EXTRACTION_VALIDATED_NOT_PROFILE_APPROVAL",
                "office": "teplice",
                "fields": {"address": {"parsed": {"street": "Synthetic 1"}}},
            }),
        )
        self._write(
            "runtime/portal/temporary/ares-review/17511267.json",
            json.dumps({
                "registration_id": "17511267", "legal_name": "Jan Šlauf",
                "legal_form": "sole_trader", "country_code": "CZ",
                "registered_address": {"street": "Masarykova 314/15, 41901 Duchcov",
                                       "house_number": 314, "city": "Duchcov",
                                       "postal_code": 41901, "country_code": "CZ"},
                "nace_codes": ["43120", "81290"], "founded_on": "2022-09-07",
                "registry_updated_on": "2024-12-04", "verified_on": "2026-10-21",
                "source": "https://ares.example/17511267",
                "content_sha256": "ares-17511267",
            }),
        )
        self._write(
            "a1/employees_normalized.json",
            json.dumps({
                "reviewed_on": "2026-10-20", "note": "synthetic",
                "employees": [{
                    "id": "synthetic-worker-a",
                    "employment": {"kind": "employee", "employer_id": "17511267",
                                   "employer_name": "Jan Šlauf",
                                   "street": "Masarykova", "house_number": "314/15",
                                   "city": "Duchcov", "postal_code": "419 01",
                                   "country_code": "CZ"},
                }],
            }),
        )
        self._write(
            "runtime/portal/temporary/retained/ocr-scanonly-cache/"
            "synthetic-worker-d__synthetic-worker-d-op1.json",
            json.dumps({
                "employee_id": "synthetic-worker-d",
                "scan": "synthetic-worker-d-op1.jpeg",
                "fields": [
                    {"field": "family_name", "value": "Doe",
                     "confidence": 0.9, "findings": [], "source": "visual"},
                    {"field": "given_name", "value": "Jane",
                     "confidence": 0.9, "findings": [], "source": "visual"},
                    {"field": "birth_date", "value": "2000-01-01",
                     "confidence": 0.9, "findings": [], "source": "visual"},
                    {"field": "insurance_number", "value": "111222333",
                     "confidence": 0.9, "findings": ["unlabelled_ehic"],
                     "source": "visual"},
                ],
            }),
        )

    def _run(self, output: str | None = "runtime/export") -> Path:
        return merge.run(self.root, output, 90)

    def test_merge_covers_all_sources_and_separates_identifiers(self) -> None:
        out = self._run()
        rows = _workers(out / "workers.csv")

        self.assertEqual(5, len(rows))
        self.assertEqual({"REVIEWED", "OCR_REVIEWED", "OCR_ONLY", "SCAN_ONLY"},
                         {rows["synthetic-worker-a"]["data_status"],
                          rows["synthetic-worker-b"]["data_status"],
                          rows["synthetic-worker-c"]["data_status"],
                          rows["synthetic-worker-d"]["data_status"],
                          rows["synthetic-worker-e"]["data_status"]})
        self.assertEqual("OCR_REVIEWED", rows["synthetic-worker-c"]["data_status"])

        self.assertEqual("TESTER", rows["synthetic-worker-a"]["surname"])
        self.assertEqual("RESOLVED", rows["synthetic-worker-a"]["review_source_scan_status"])

        worker_b = rows["synthetic-worker-b"]
        self.assertEqual("000101/0001", worker_b["rodne_cislo"])
        self.assertEqual("0001010001", worker_b["op_document_number_raw"])
        self.assertEqual("SAMPLE", worker_b["surname"])

        sources = json.loads(worker_b["field_sources"])
        self.assertTrue(sources["insurance_number"].endswith("zp1.jpeg"))
        self.assertEqual("111222333", worker_b["insurance_number"])

        self.assertEqual("111222333", rows["synthetic-worker-c"]["insurance_number"])
        self.assertEqual("SYNTHETIC INSURER", rows["synthetic-worker-c"]["insurer"])

        worker_d = rows["synthetic-worker-d"]
        self.assertEqual("SCAN_ONLY", worker_d["data_status"])
        self.assertEqual("Doe", worker_d["surname"])
        self.assertEqual("Jane", worker_d["given_name"])
        self.assertEqual("2000-01-01", worker_d["dob"])
        self.assertEqual("YES", worker_d["has_ocr_proposal"])
        self.assertEqual("1", worker_d["ocr_proposal_count"])
        self.assertEqual("ocr_proposal:synthetic-worker-d-op1.jpeg",
                         json.loads(worker_d["field_sources"])["surname"])

        worker_e = rows["synthetic-worker-e"]
        self.assertEqual("SCAN_ONLY", worker_e["data_status"])
        self.assertEqual("Synthetic", worker_e["surname"])
        self.assertEqual("Worker", worker_e["given_name"])
        self.assertEqual("scan_filename", json.loads(worker_e["field_sources"])["surname"])
        self.assertEqual("NO", worker_e["has_ocr_proposal"])
        self.assertEqual("0", worker_e["ocr_proposal_count"])

        unmapped = list(csv.DictReader((out / "unmapped_ocr_fields.csv").open(encoding="utf-8", newline="")))
        self.assertEqual(["note_text"], sorted({r["raw_field"] for r in unmapped}))

        dropped = list(csv.DictReader((out / "ocr_proposal_dropped.csv").open(encoding="utf-8", newline="")))
        self.assertEqual(0, len(dropped))

        employers = list(csv.DictReader((out / "employers.csv").open(encoding="utf-8", newline="")))
        self.assertEqual(1, len(employers))
        self.assertEqual("17511267", employers[0]["employment_id"])
        self.assertEqual("ARES_VERIFIED", employers[0]["review_status"])
        self.assertEqual("Jan Šlauf", employers[0]["ares_legal_name"])
        self.assertEqual("43120,81290", employers[0]["ares_nace"])
        conflicts = list(csv.DictReader(
            (out / "employer_source_conflicts.csv").open(encoding="utf-8", newline="")))
        self.assertEqual(0, len(conflicts))

        for employee_id, row in rows.items():
            sources = json.loads(row["field_sources"]) if row["field_sources"] else {}
            for name, value in row.items():
                if name in {
                    "employee_id", "field_sources", "source_scans",
                    "review_source_scans_declared", "review_source_scan_status",
                    "missing_core_fields", "data_status", "has_scan", "scan_count",
                    "has_ocr", "has_a1_review", "has_people_review",
                    "has_ocr_proposal", "ocr_proposal_count", "comments",
                }:
                    continue
                if value.strip() and name not in sources:
                    self.fail(f"{employee_id}: {name} has no provenance entry")

    def test_private_permissions_and_retention(self) -> None:
        out = self._run()
        self.assertEqual(0o700, stat.S_IMODE(out.stat().st_mode))
        for path in out.iterdir():
            self.assertEqual(0o600, stat.S_IMODE(path.stat().st_mode), path.name)

        manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(90, manifest["retention"]["days"])
        self.assertEqual(5, manifest["counts"]["workers"])
        self.assertEqual(2, manifest["counts"]["worker_ossz"])

    def test_existing_permissive_output_directory_is_rejected(self) -> None:
        target = self.root / "runtime/export"
        target.mkdir(parents=True)
        os.chmod(target, 0o755)
        with self.assertRaisesRegex(merge.ExportError, "not private"):
            self._run()

    def test_missing_optional_inputs_do_not_break_export(self) -> None:
        (self.root / "config/institutions/teplice.json").unlink()
        (self.root / "runtime/portal/temporary/ossz-research-abc/report.json").unlink()
        out = self._run()
        rows = _workers(out / "workers.csv")
        self.assertEqual(5, len(rows))
        manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(0, manifest["counts"]["ossz_offices"])
        self.assertEqual(0, manifest["counts"]["research_runs"])


if __name__ == "__main__":
    unittest.main()
