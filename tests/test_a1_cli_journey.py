"""Black-box, synthetic generation → render → deterministic QA acceptance.

These tests do not confer visual approval or certificate authority. Each test owns
its private inputs and subprocess environment; no service database is involved.
"""
import hashlib
import json
import os
import subprocess
import unittest
from pathlib import Path
from uuid import UUID

import pymupdf
import test_finalize_a1 as fixtures
from test_finalize_a1 import employee, review_row

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / "venv/bin/python"
GENERATE_CLI = ROOT / "scripts/generate_provisional_a1.py"
QA_CLI = ROOT / "scripts/a1_quality_gate.py"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SyntheticCLIJourney(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.FinalizationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.base = self.fixture.base
        (self.base / "a1").mkdir(exist_ok=True)
        (self.base / "a1/operator.json").write_text(json.dumps({
            "organization_id": "synthetic-organization", "actor_id": "synthetic-operator"}))
        self.env = {**os.environ, "A1_PRIVATE_DIR": str(self.base)}
        self.employees = [
            employee("synthetic-0", "TESTOVÁ", "ANNA", "01.02.1990", "900201/1234"),
            employee("synthetic-1", "PŘÍKLAD", "BERT", "03.04.1985", "850403/5678"),
            employee("synthetic-2", "VZOR", "CYRIL", "05.06.1992", "920605/9999"),
        ]
        self.rows = []
        for i, profile in enumerate(("self_employed_multi_state", "posted_employee", "employee_multi_state")):
            source = self.employees[i]
            source["a1"]["status_profile"] = profile
            source["employment"]["kind"] = "self_employed" if i == 0 else "employee"
            row = review_row(source, f"SYNTHETIC-CERTIFICATE-{i}")
            row["status_profile"] = profile
            row["employment_name"] = "Synthetic Engineering s.r.o."
            self.rows.append(row)
        self.fixture.employees_path.write_text(json.dumps({"employees": self.employees}))
        self.fixture.write_rows(self.rows)
        self.cohort = self.base / "cohort.json"
        self.cohort.write_text(json.dumps({
            "issue_dates": {r["employee_id"]: r["issue_date"] for r in self.rows},
            "document_ids": {r["employee_id"]: r["document_id"] for r in self.rows}}))
        self.config = self.base / "config.json"
        self.config.write_text(json.dumps({"notice": "CLIENT_CONFIRMATION_COPY"}))
        self.output = self.base / "output/copies"
        self.inputs = [self.fixture.employees_path, self.fixture.review_path, self.cohort,
                       self.config, self.fixture.profile_dir / "teplice-test.json"]
        self.before = {p: digest(p) for p in self.inputs}

    def run_cli(self, script, *args, env=None):
        return subprocess.run([str(PYTHON), str(script), *map(str, args)],
                              cwd=ROOT, capture_output=True, text=True,
                              env=self.env if env is None else env, timeout=180)

    def generate(self, output=None, env=None):
        return self.run_cli(GENERATE_CLI, "--review", self.fixture.review_path,
                            "--employees", self.fixture.employees_path,
                            "--profiles", self.fixture.profile_dir, "--config", self.config,
                            "--cohort", self.cohort, "--output", output or self.output, env=env)

    def assert_sanitized_failure(self, result):
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(result.stderr.strip(), "failure must emit a sanitized code to stderr")
        self.assertNotIn(str(self.base), result.stdout + result.stderr)
        self.assertNotIn("Traceback", result.stdout + result.stderr)

    def assert_inputs_unchanged(self):
        self.assertEqual(self.before, {p: digest(p) for p in self.inputs})

    def test_all_profiles_generate_render_and_validate(self):
        result = self.generate()
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest_path = self.output / "generation_manifest.json"
        self.assertTrue(manifest_path.is_file())
        manifest = json.loads(manifest_path.read_text())
        self.assertEqual(manifest["status"], "PROVISIONAL_NOT_FOR_OFFICIAL_USE")
        self.assertEqual(str(UUID(manifest["run_id"])), manifest["run_id"])
        self.assertTrue(manifest["inputs"])
        self.assertTrue(manifest["snapshot_sha256"])
        receipt = self.base / "a1/receipts" / f"{manifest['run_id']}.json"
        self.assertTrue(receipt.is_file())
        self.assertEqual(json.loads(receipt.read_text())["status"], "completed")
        self.assertEqual(receipt.stat().st_mode & 0o777, 0o600)
        pdfs = sorted(self.output.glob("A1_*.pdf"))
        self.assertEqual(len(pdfs), 3)
        for path, row in zip(pdfs, self.rows):
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            with pymupdf.open(path) as document:
                self.assertEqual(len(document), 3)
                self.assertIn(row["document_id"], "".join(page.get_text() for page in document))
        previews, contacts = self.base / "output/previews", self.base / "output/contacts"
        result = self.run_cli(QA_CLI, "render", "--pdf-dir", self.output,
                              "--preview-dir", previews, "--contact-dir", contacts, "--dpi", 200)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(list(previews.glob("A1_*-page-*.png"))), 9)
        report, qa_manifest = self.base / "output/qa.json", self.base / "output/qa-manifest.json"
        result = self.run_cli(QA_CLI, "validate", "--pdf-dir", self.output,
                              "--preview-dir", previews, "--config", self.config,
                              "--cohort", self.cohort, "--review", self.fixture.review_path,
                              "--report", report, "--manifest", qa_manifest)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertTrue(json.loads(report.read_text())["passed"])
        qa = json.loads(qa_manifest.read_text())
        self.assertEqual(qa["qa_status"], "PASS")
        self.assertEqual(qa["pdfs"], {p.name: digest(p) for p in pdfs})
        self.assertEqual(len(qa["previews"]), 9)
        for receipt in (manifest_path, report, qa_manifest):
            self.assertEqual(receipt.stat().st_mode & 0o777, 0o600)
        self.assert_inputs_unchanged()
        self.assertFalse((self.base / "output/final").exists())

    def test_malformed_csv_rejected(self):
        self.fixture.review_path.write_text("employee_id,surname\nsynthetic-0")
        self.assert_sanitized_failure(self.generate())
        self.assertFalse(self.output.exists())
        receipts = list((self.base / "a1/receipts").glob("*.json"))
        self.assertTrue(receipts, "writable protected storage must contain a failure receipt")
        self.assertTrue(all(json.loads(p.read_text())["status"] == "failed" for p in receipts))

    def test_final_destination_blocked(self):
        for name in ("final", "pdf"):
            with self.subTest(name=name):
                output = self.base / "output" / name
                self.assert_sanitized_failure(self.generate(output))
                self.assertFalse(output.exists())
        self.assert_inputs_unchanged()

    def test_duplicate_output_rejected(self):
        self.output.mkdir(parents=True)
        original = self.output / "old.pdf"
        original.write_bytes(b"synthetic sentinel")
        self.assert_sanitized_failure(self.generate())
        self.assertEqual(original.read_bytes(), b"synthetic sentinel")
        self.assertEqual(list(self.output.iterdir()), [original])
        self.assert_inputs_unchanged()

    def test_missing_private_root_blocks_generation(self):
        env = dict(self.env)
        env.pop("A1_PRIVATE_DIR")
        self.assert_sanitized_failure(self.generate(env=env))
        self.assertFalse(self.output.exists())
        self.assert_inputs_unchanged()

    def test_missing_organization_blocks_before_processing(self):
        (self.base / "a1/operator.json").write_text("{}")
        self.assert_sanitized_failure(self.generate())
        self.assertFalse(self.output.exists())
        self.assert_inputs_unchanged()

    def test_malformed_policy_is_sanitized_and_leaves_no_staging(self):
        for value in ({}, [], {"notice": None}):
            with self.subTest(value=value):
                self.config.write_text(json.dumps(value))
                self.assert_sanitized_failure(self.generate())
                self.assertFalse(self.output.exists())
                self.assertFalse(list((self.base / "output").glob(".staging-*")))
        receipts=list((self.base / "a1/receipts").glob("*.json"))
        self.assertEqual(len(receipts),3)
        self.assertTrue(all(json.loads(p.read_text())["status"]=="failed" for p in receipts))
