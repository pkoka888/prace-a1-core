import json
import io
import os
import tempfile
import unittest
import uuid
from unittest.mock import patch
from contextlib import redirect_stdout, redirect_stderr
from PIL import Image
from pathlib import Path

import pymupdf

from scripts.a1_quality_gate import (
    QualityGateError,
    create_contact_sheets,
    expected_records,
    record_visual_review,
    render_previews,
    validate_set,
    _validate_preview_freshness,
    main,
    require_completed_generation,
    sha256_file,
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
        self.env = patch.dict(os.environ, {"A1_PRIVATE_DIR": self.temp.name})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.root = Path(self.temp.name) / "output"
        self.root.mkdir()
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
        self.assertIn("render_receipt", manifest)
        for path in [self.root / "qa.json", self.root / "manifest.json", self.previews / "render-receipt.json", *self.previews.glob("*.png")]:
            self.assertEqual(0o600, path.stat().st_mode & 0o777)


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

    def test_report_cannot_overwrite_input(self):
        original = self.config.read_bytes()
        with self.assertRaisesRegex(QualityGateError, "OVERLAPS"):
            validate_set(self.pdfs, self.previews, self.config, self.cohort, None, None,
                         self.config, self.root / "manifest.json")
        self.assertEqual(original, self.config.read_bytes())

    def test_cli_output_aliases_never_remove_or_overwrite_sources(self):
        private = Path(self.temp.name)
        (private / "a1").mkdir()
        (private / "a1/operator.json").write_text(json.dumps({"organization_id": "synthetic-org"}))
        source = self.pdfs / "A1_anna-test.pdf"
        pdf(source, "Synthetic test")
        originals = {path: path.read_bytes() for path in (source, self.config, self.cohort)}
        commands = [
            ["validate", "--pdf-dir", str(self.pdfs), "--preview-dir", str(self.previews),
             "--config", str(self.config), "--cohort", str(self.cohort), "--review", str(self.cohort),
             "--report", str(self.config), "--manifest", str(source)],
            ["render", "--pdf-dir", str(self.pdfs), "--preview-dir", str(self.pdfs),
             "--contact-dir", str(self.root / "contacts")],
            ["record-review", "--manifest", str(self.config), "--contact-dir", str(self.root / "contacts"),
             "--output", str(source), "--reviewer", "synthetic-reviewer", "--note", "synthetic"],
        ]
        for command in commands:
            with self.subTest(command=command[0]), redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertNotEqual(0, main(command))
            for path, original in originals.items():
                self.assertEqual(original, path.read_bytes())

    def test_empty_cohort_is_not_successful_qa(self):
        self.cohort.write_text(json.dumps({"issue_dates": {}, "document_ids": {}}))
        with self.assertRaisesRegex(QualityGateError, "empty"):
            expected_records(self.config, self.cohort, None)

    def test_freshness_uses_recorded_dpi_and_decoded_pixels(self):
        source = self.pdfs / "A1_anna-test.pdf"
        pdf(source, "Synthetic test")
        for dpi in (144, 200, 300):
            with self.subTest(dpi=dpi):
                previews = render_previews(self.pdfs, self.previews, dpi=dpi)
                first = previews[0]
                original_bytes = first.read_bytes()
                with Image.open(first) as image:
                    image.save(first, compress_level=0)
                self.assertNotEqual(original_bytes, first.read_bytes())
                with patch("tempfile.mkdtemp", side_effect=AssertionError("no disk derivative")):
                    self.assertEqual([], _validate_preview_freshness(
                        [source], previews, self.previews / "render-receipt.json"))

    def test_changed_last_page_and_source_are_rejected(self):
        source = self.pdfs / "A1_anna-test.pdf"
        pdf(source, "Synthetic test")
        previews = render_previews(self.pdfs, self.previews, dpi=200)
        with Image.open(previews[-1]) as image:
            image.putpixel((0, 0), (0, 0, 0))
            image.save(previews[-1])
        issues = _validate_preview_freshness([source], previews, self.previews / "render-receipt.json")
        self.assertEqual(["PREVIEW_STALE:row=1:page=3"], issues)
        pdf(source, "Changed source")
        self.assertEqual(["RENDER_SOURCE_CHANGED"], _validate_preview_freshness(
            [source], previews, self.previews / "render-receipt.json"))

    def test_missing_render_receipt_and_empty_previews_fail_closed(self):
        source = self.pdfs / "A1_anna-test.pdf"
        pdf(source, "Synthetic test")
        previews = render_previews(self.pdfs, self.previews)
        receipt = self.previews / "render-receipt.json"
        self.assertEqual(["PREVIEWS_MISSING"], _validate_preview_freshness([source], [], receipt))
        receipt.unlink()
        self.assertEqual(["RENDER_RECEIPT_OR_PREVIEW_INVALID"], _validate_preview_freshness([source], previews, receipt))

    def test_render_rejects_symlink_output_and_keeps_original(self):
        source = self.pdfs / "A1_anna-test.pdf"
        pdf(source, "Synthetic test")
        original = source.read_bytes()
        self.previews.symlink_to(self.pdfs, target_is_directory=True)
        with self.assertRaises((QualityGateError, ValueError)):
            render_previews(self.pdfs, self.previews)
        self.assertEqual(original, source.read_bytes())

    def test_visual_review_is_bound_to_current_pass_manifest_and_three_sheets(self):
        text = "UNIQUE-1 Testová Anna 01.02.1990 900201/1234 Samostatná výdělečná činnost DE, CZ"
        source = self.pdfs / "A1_anna-test.pdf"
        pdf(source, text)
        previews = render_previews(self.pdfs, self.previews)
        contacts = self.root / "contacts"
        create_contact_sheets(previews, contacts)
        manifest = self.root / "manifest.json"
        validate_set(self.pdfs, self.previews, self.config, self.cohort, None, None,
                     self.root / "qa.json", manifest)
        output = self.root / "visual.json"
        review = record_visual_review(manifest, contacts, output, "reviewer", "all pages")
        self.assertEqual("PASS", review["visual_status"])
        self.assertEqual(3, len(review["contact_sheets"]))
        self.assertEqual(0o600, output.stat().st_mode & 0o777)
        (contacts / "contact-sheet-page-3.png").write_bytes(b"stale")
        with self.assertRaisesRegex(QualityGateError, "CONTACT_SHEETS_STALE"):
            record_visual_review(manifest, contacts, output, "reviewer", "all pages")
        create_contact_sheets(previews, contacts)
        pdf(source, "Changed input")
        with self.assertRaisesRegex(QualityGateError, "STALE"):
            record_visual_review(manifest, contacts, output, "reviewer", "all pages")

    def completed_generation(self):
        from scripts.a1_audit import audited_operation, write_private_json
        private = Path(self.temp.name)
        (private / "a1").mkdir(exist_ok=True)
        (private / "a1/operator.json").write_text(json.dumps({"organization_id": "synthetic-org"}))
        source = self.pdfs / "A1_anna-test.pdf"
        text = "UNIQUE-1 Testová Anna 01.02.1990 900201/1234 Samostatná výdělečná činnost DE, CZ"
        pdf(source, text)
        with audited_operation("provisional_generate", "a1_provisional") as run_id:
            write_private_json(self.pdfs / "generation_manifest.json", {
                "run_id": run_id,
                "generated": [{"path": source.name, "sha256": sha256_file(source)}],
            })
        return private, run_id, source

    def test_generation_receipt_failure_states_block_qa(self):
        private, run_id, source = self.completed_generation()
        receipt_path = private / "a1/receipts" / f"{run_id}.json"
        good_receipt = receipt_path.read_bytes()
        original = source.read_bytes()
        for state in ("running", "failed", "missing", "mismatched_uuid", "completed_without_audit"):
            with self.subTest(state=state):
                receipt = json.loads(good_receipt)
                if state in ("running", "failed"):
                    receipt["status"] = state
                elif state == "mismatched_uuid":
                    receipt["run_id"] = str(uuid.uuid4())
                receipt_path.write_text(json.dumps(receipt))
                if state == "missing":
                    receipt_path.unlink()
                audit_path = private / "a1/audit/events.jsonl"
                audit = audit_path.read_bytes()
                if state == "completed_without_audit":
                    events = [json.loads(line) for line in audit.splitlines()]
                    audit_path.write_text("\n".join(json.dumps(event) for event in events if event["outcome"] != "completed") + "\n")
                try:
                    with self.assertRaisesRegex(QualityGateError, "GENERATION_COMPLETION_REQUIRED"):
                        require_completed_generation(self.pdfs)
                    self.assertEqual(original, source.read_bytes())
                finally:
                    receipt_path.write_bytes(good_receipt)
                    audit_path.write_bytes(audit)

    def test_completed_generation_is_bound_and_rechecked_by_visual_review(self):
        private, run_id, source = self.completed_generation()
        evidence = require_completed_generation(self.pdfs)
        self.assertEqual(run_id, evidence["run_id"])
        self.assertEqual(64, len(evidence["audit_terminal_sha256"]))
        previews = render_previews(self.pdfs, self.previews)
        contacts = self.root / "contacts"
        create_contact_sheets(previews, contacts)
        manifest = self.root / "manifest.json"
        report = validate_set(self.pdfs, self.previews, self.config, self.cohort, None, None,
                             self.root / "qa.json", manifest, generation_evidence=evidence)
        self.assertTrue(report["passed"])
        stored = json.loads(manifest.read_text())
        self.assertEqual(evidence, stored["generation_evidence"])
        self.assertIn(evidence["receipt"]["path"], stored["inputs"])
        output = self.root / "visual.json"
        record_visual_review(manifest, contacts, output, "reviewer", "all pages", require_generation=True)
        receipt_path = private / "a1/receipts" / f"{run_id}.json"
        receipt = json.loads(receipt_path.read_text())
        receipt["status"] = "failed"
        receipt_path.write_text(json.dumps(receipt))
        with self.assertRaisesRegex(QualityGateError, "GENERATION_COMPLETION_REQUIRED"):
            record_visual_review(manifest, contacts, output, "reviewer", "all pages", require_generation=True)

    def test_cli_cannot_validate_manifestless_package_or_render_failed_generation(self):
        private, run_id, source = self.completed_generation()
        manifest = self.pdfs / "generation_manifest.json"
        original_manifest = manifest.read_bytes()
        manifest.unlink()
        with patch("scripts.a1_quality_gate.validate_set") as validate, redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            result = main(["validate", "--pdf-dir", str(self.pdfs), "--preview-dir", str(self.previews),
                           "--report", str(self.root / "qa.json"), "--manifest", str(self.root / "qa-manifest.json")])
        self.assertEqual(2, result)
        validate.assert_not_called()
        manifest.write_bytes(original_manifest)
        receipt_path = private / "a1/receipts" / f"{run_id}.json"
        receipt = json.loads(receipt_path.read_text())
        receipt["status"] = "failed"
        receipt_path.write_text(json.dumps(receipt))
        with patch("scripts.a1_quality_gate.render_previews") as render, redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            result = main(["render", "--pdf-dir", str(self.pdfs), "--preview-dir", str(self.previews),
                           "--contact-dir", str(self.root / "contacts")])
        self.assertEqual(2, result)
        render.assert_not_called()

    def test_cli_missing_audit_context_blocks_before_render(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch("scripts.a1_quality_gate.render_previews") as render, redirect_stdout(stdout), redirect_stderr(stderr):
            result = main(["render", "--pdf-dir", str(self.pdfs), "--preview-dir", str(self.previews),
                           "--contact-dir", str(self.root / "contacts")])
        self.assertEqual(2, result)
        render.assert_not_called()
        self.assertEqual("", stdout.getvalue())
        self.assertIn("QA_OPERATION_FAILED", stderr.getvalue())
        self.assertNotIn(str(self.root), stderr.getvalue())
        receipts = list((Path(self.temp.name) / "a1/receipts").glob("*.json"))
        self.assertEqual(1, len(receipts))
        self.assertEqual("failed", json.loads(receipts[0].read_text())["status"])


if __name__ == "__main__":
    unittest.main()
