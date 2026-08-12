import json
import tempfile
import unittest
from pathlib import Path

import pymupdf

from scripts.a1_quality_gate import (
    QualityGateError,
    create_contact_sheets,
    expected_records,
    record_visual_review,
    render_previews,
    validate_set,
)


def pdf(path: Path, text: str, pages: int = 3) -> None:
    document = pymupdf.open()
    for _ in range(pages):
        page = document.new_page(width=595.2, height=841.92)
        font = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
        page.insert_font(fontname="LiberationSans", fontfile=font)
        page.insert_text((72, 72), text, fontsize=9, fontname="LiberationSans")
    document.save(path)
    document.close()


class A1QualityGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.pdfs = self.root / "pdfs"
        self.previews = self.root / "previews"
        self.pdfs.mkdir()
        self.config = self.root / "config.json"
        self.config.write_text(json.dumps({
            "activity_name": "Samostatná výdělečná činnost",
            "activity_address": "DE, CZ",
        }, ensure_ascii=False), encoding="utf-8")
        self.cohort = self.root / "cohort.json"
        self.cohort.write_text(json.dumps({
            "issue_dates": {"anna-test": "01.06.2026"},
            "document_ids": {"anna-test": "UNIQUE-1"},
            "additional_people": [{
                "employee_id": "anna-test", "surname": "Testová", "given_name": "Anna",
                "dob": "01.02.1990", "insurance_number": "900201/1234",
            }],
        }, ensure_ascii=False), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_config_cohort_must_be_internally_consistent(self):
        broken = json.loads(self.cohort.read_text())
        broken["document_ids"] = {}
        self.cohort.write_text(json.dumps(broken))
        with self.assertRaisesRegex(QualityGateError, "same cohort"):
            expected_records(self.config, self.cohort, None)

    def test_review_without_explicit_section_four_columns_is_rejected(self):
        review = self.root / "review.csv"
        review.write_text("employee_id,surname\nanna-test,Testová\n", encoding="utf-8")
        with self.assertRaisesRegex(QualityGateError, "explicit Section 4 columns"):
            expected_records(self.config, self.cohort, review)

    def test_render_replaces_stale_previews_and_builds_sheets(self):
        pdf(self.pdfs / "A1_anna-test.pdf", "preview")
        self.previews.mkdir()
        (self.previews / "A1_stale-page-1.png").write_bytes(b"stale")
        rendered = render_previews(self.pdfs, self.previews, dpi=144)
        sheets = create_contact_sheets(rendered, self.root / "contacts")
        self.assertEqual(3, len(rendered))
        self.assertEqual(3, len(sheets))
        self.assertFalse((self.previews / "A1_stale-page-1.png").exists())

    def test_gate_passes_complete_hash_bound_package(self):
        text = "UNIQUE-1 Testová Anna 01.02.1990 900201/1234 Samostatná výdělečná činnost DE, CZ"
        pdf(self.pdfs / "A1_anna-test.pdf", text)
        render_previews(self.pdfs, self.previews, dpi=144)
        report = validate_set(
            self.pdfs, self.previews, self.config, self.cohort, None, None,
            self.root / "qa.json", self.root / "manifest.json",
        )
        self.assertTrue(report["passed"])
        manifest = json.loads((self.root / "manifest.json").read_text())
        self.assertEqual("PASS", manifest["qa_status"])
        self.assertEqual(3, len(manifest["previews"]))

    def test_gate_fails_closed_on_missing_person_and_stale_preview(self):
        pdf(self.pdfs / "A1_anna-test.pdf", "UNIQUE-1")
        render_previews(self.pdfs, self.previews, dpi=144)
        (self.previews / "A1_foreign-page-1.png").write_bytes(b"stale")
        manifest = self.root / "manifest.json"
        manifest.write_text("stale")
        report = validate_set(
            self.pdfs, self.previews, self.config, self.cohort, None, None,
            self.root / "qa.json", manifest,
        )
        self.assertFalse(report["passed"])
        self.assertFalse(manifest.exists())
        self.assertTrue(any("missing expected surname" in issue for issue in report["pdfs"][0]["issues"]))

    def test_wrong_page_count_fails(self):
        pdf(self.pdfs / "A1_anna-test.pdf", "UNIQUE-1 Testová Anna", pages=2)
        render_previews(self.pdfs, self.previews, dpi=144)
        report = validate_set(
            self.pdfs, self.previews, self.config, self.cohort, None, None,
            self.root / "qa.json", self.root / "manifest.json",
        )
        self.assertFalse(report["passed"])
        self.assertIn("page_count=2", report["pdfs"][0]["issues"][0])

    def test_visual_review_is_bound_to_pass_manifest_and_three_sheets(self):
        manifest = self.root / "manifest.json"
        manifest.write_text(json.dumps({"qa_status": "PASS"}), encoding="utf-8")
        contacts = self.root / "contacts"
        contacts.mkdir()
        for page in range(1, 4):
            (contacts / f"contact-sheet-page-{page}.png").write_bytes(f"page-{page}".encode())
        output = self.root / "visual.json"
        review = record_visual_review(manifest, contacts, output, "reviewer", "all pages")
        self.assertEqual("PASS", review["visual_status"])
        self.assertEqual(3, len(review["contact_sheets"]))
        self.assertTrue(output.exists())


if __name__ == "__main__":
    unittest.main()
