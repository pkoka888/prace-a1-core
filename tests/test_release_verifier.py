"""
Unit tests for the release verifier harness.

Tests the verifier's own functions and classification logic directly,
not by re-implementing detection.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


# ------------------------------------------------------------------
# Direct function tests
# ------------------------------------------------------------------

class TestCheckGateLogic:
    """Test check_gate() behavior directly."""

    def test_check_gate_returns_closed_on_unknown_record(self, tmp_path):
        """check_gate returns (False, 'not found') for unknown record."""
        from planning.approval_register import check_gate
        import tempfile, json

        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            (td / "planning").mkdir(parents=True)
            (td / "docs/decisions").mkdir(parents=True)
            (td / "docs/operations").mkdir(parents=True)
            (td / "docs/release-1a").mkdir(parents=True)
            (td / "plans").mkdir(parents=True)
            schema = (ROOT / "planning" / "approvals.schema.json").read_text()
            (td / "planning" / "approvals.schema.json").write_text(schema)
            catalog = (ROOT / "planning" / "catalog.json").read_text()
            (td / "planning" / "catalog.json").write_text(catalog)
            # Copy required source files
            for src in [
                "docs/decisions/ADR-001-jan-portal-architecture.md",
                "docs/decisions/ADR-002-release-1a-data-and-transactions.md",
                "docs/operations/release-1a-review-environment.md",
                "docs/release-1a/unblock-review-packet.md",
                "plans/PLAN-REAL-DATA.md",
                "plans/PLAN-WORKERS.md",
                "plans/INDEX.md",
            ]:
                src_path = ROOT / src
                if src_path.exists():
                    dst = td / src
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    dst.write_text(src_path.read_text())
            data = {
                "schema_version": "1.0",
                "updated_at": "2026-09-06T00:00:00Z",
                "records": [],
            }
            (td / "planning" / "approvals.json").write_text(json.dumps(data))
            is_open, reason = check_gate(td, "ENG-001")
            assert not is_open
            assert "not found" in reason.lower()

    def test_check_gate_returns_closed_on_validation_failure(self, tmp_path):
        """check_gate returns closed when register validation fails."""
        from planning.approval_register import check_gate
        import tempfile, json

        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            (td / "planning").mkdir(parents=True)
            (td / "docs/decisions").mkdir(parents=True)
            (td / "docs/operations").mkdir(parents=True)
            (td / "docs/release-1a").mkdir(parents=True)
            (td / "plans").mkdir(parents=True)
            schema = (ROOT / "planning" / "approvals.schema.json").read_text()
            (td / "planning" / "approvals.schema.json").write_text(schema)
            catalog = (ROOT / "planning" / "catalog.json").read_text()
            (td / "planning" / "catalog.json").write_text(catalog)
            # Invalid: duplicate record ID
            base = json.loads((ROOT / "planning" / "approvals.json").read_text())
            base["records"] = base["records"][:1]
            eng_id = base["records"][0]["id"]
            base["records"].append(json.loads(json.dumps(base["records"][0])))
            (td / "planning" / "approvals.json").write_text(json.dumps(base))
            is_open, reason = check_gate(td, eng_id)
            assert not is_open
            assert "validation failed" in reason.lower() or "duplicate" in reason.lower()

    def test_check_gate_requires_clean_tree_when_requested(self, tmp_path):
        """check_gate with require_clean=True returns closed on dirty tree."""
        from planning.approval_register import check_gate
        import tempfile, json

        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            (td / "planning").mkdir(parents=True)
            (td / "docs/decisions").mkdir(parents=True)
            (td / "docs/operations").mkdir(parents=True)
            (td / "docs/release-1a").mkdir(parents=True)
            (td / "plans").mkdir(parents=True)
            schema = (ROOT / "planning" / "approvals.schema.json").read_text()
            (td / "planning" / "approvals.schema.json").write_text(schema)
            catalog = (ROOT / "planning" / "catalog.json").read_text()
            (td / "planning" / "catalog.json").write_text(catalog)
            data = json.loads((ROOT / "planning" / "approvals.json").read_text())
            (td / "planning" / "approvals.json").write_text(json.dumps(data))
            # Create a dirty file in the review scope
            (td / "portal").mkdir()
            (td / "portal" / "dirty.py").write_text("# dirty")
            is_open, reason = check_gate(td, "ENG-001", require_clean=True)
            assert not is_open
            assert "dirty" in reason.lower() or "validation failed" in reason.lower()


class TestValidateLogic:
    """Test validate() behavior directly."""

    def test_validate_rejects_placeholder_approver_after_approval(self, tmp_path):
        """validate() errors when human_decision=approved but approver starts with 'pending — '."""
        from planning.approval_register import validate
        import tempfile, json

        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            (td / "planning").mkdir(parents=True)
            (td / "docs/decisions").mkdir(parents=True)
            (td / "docs/operations").mkdir(parents=True)
            (td / "docs/release-1a").mkdir(parents=True)
            (td / "plans").mkdir(parents=True)
            (td / "planning" / "approvals.schema.json").write_text(
                (ROOT / "planning" / "approvals.schema.json").read_text()
            )
            (td / "planning" / "catalog.json").write_text(
                (ROOT / "planning" / "catalog.json").read_text()
            )
            data = json.loads((ROOT / "planning" / "approvals.json").read_text())
            eng = next(r for r in data["records"] if r["id"] == "ENG-001")
            eng["human_decision"] = "approved"
            eng["approver"] = "pending — engineering gate only"
            eng["approved_at"] = "2026-09-06"
            eng["approval_evidence"] = "synthetic"
            for c in eng["checks"]:
                c["status"] = "passed"
            eng["validation"] = "passed"
            (td / "planning" / "approvals.json").write_text(json.dumps(data))
            result = validate(td)
            assert result["result"] == "fail"
            assert any("placeholder" in e.lower() for e in result["errors"])

    def test_validate_rejects_missing_dependency(self, tmp_path):
        """validate() errors on unknown dependency ID."""
        from planning.approval_register import validate
        import tempfile, json

        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            (td / "planning").mkdir(parents=True)
            (td / "docs/decisions").mkdir(parents=True)
            (td / "docs/operations").mkdir(parents=True)
            (td / "docs/release-1a").mkdir(parents=True)
            (td / "plans").mkdir(parents=True)
            (td / "planning" / "approvals.schema.json").write_text(
                (ROOT / "planning" / "approvals.schema.json").read_text()
            )
            (td / "planning" / "catalog.json").write_text(
                (ROOT / "planning" / "catalog.json").read_text()
            )
            data = json.loads((ROOT / "planning" / "approvals.json").read_text())
            eng = next(r for r in data["records"] if r["id"] == "ENG-001")
            eng["dependencies"].append({"id": "DOES-NOT-EXIST", "required_gate": "approved"})
            (td / "planning" / "approvals.json").write_text(json.dumps(data))
            result = validate(td)
            assert result["result"] == "fail"
            assert any("missing dependency DOES-NOT-EXIST" in e for e in result["errors"])

    def test_validate_rejects_wrong_approvals_hash(self, tmp_path):
        """validate() errors when expected_approvals_hash does not match."""
        from planning.approval_register import validate
        import tempfile, json

        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            (td / "planning").mkdir(parents=True)
            (td / "docs/decisions").mkdir(parents=True)
            (td / "docs/operations").mkdir(parents=True)
            (td / "docs/release-1a").mkdir(parents=True)
            (td / "plans").mkdir(parents=True)
            (td / "planning" / "approvals.schema.json").write_text(
                (ROOT / "planning" / "approvals.schema.json").read_text()
            )
            (td / "planning" / "catalog.json").write_text(
                (ROOT / "planning" / "catalog.json").read_text()
            )
            data = json.loads((ROOT / "planning" / "approvals.json").read_text())
            (td / "planning" / "approvals.json").write_text(json.dumps(data))
            result = validate(td, expected_approvals_hash="wronghash")
            assert result["result"] == "fail"
            assert any("hash" in e.lower() for e in result["errors"])


class TestVerifierExitCode:
    """Test that verifier exits non-zero when it should."""

    def test_verifier_exits_nonzero_with_stale_axe_receipt(self, tmp_path, monkeypatch):
        """Exercise real main/exit logic without invoking deployment or recursive tests."""
        from scripts import release_verifier as verifier
        monkeypatch.setenv("DJANGO_SETTINGS_MODULE", "portal.settings_document_tests")
        monkeypatch.setattr(verifier, "django_env", lambda: {})
        monkeypatch.setattr(verifier, "REPORT_DIR", tmp_path)
        monkeypatch.setattr(verifier, "REPORT_JSON", tmp_path / "report.json")
        monkeypatch.setattr(verifier, "REPORT_MD", tmp_path / "report.md")
        monkeypatch.setattr(verifier, "git_info", lambda: {"commit": "synthetic", "branch": "synthetic", "tree_clean": True})
        monkeypatch.setattr(verifier, "approvals_hash", lambda: "a" * 64)
        monkeypatch.setattr(verifier, "build_id", lambda: "synthetic")
        monkeypatch.setattr(verifier, "_ensure_verification_db", lambda: {"status": "PASS"})
        for name in ("verify_governance", "verify_django_checks", "verify_migrations",
                     "verify_backend_crud", "verify_storage", "verify_ocr", "verify_assignment",
                     "verify_frontend"):
            monkeypatch.setattr(verifier, name, lambda: [])
        monkeypatch.setattr(verifier, "verify_a1", lambda profile="core": [])
        monkeypatch.setattr(verifier, "verify_accessibility", lambda: [
            {"label": "accessibility/axe", "status": "FAIL", "error": "stale synthetic receipt"}])
        monkeypatch.setattr(verifier, "verify_eng001_checks", lambda profile="core": [
            {"label": "eng001/synthetic", "status": "PASS"}])
        # Guard against accidental future subprocess re-entry.
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: pytest.fail("no subprocess in verifier unit test"))
        monkeypatch.setattr(sys, "argv", ["release_verifier.py"])
        assert verifier.main() == 1
        report = json.loads((tmp_path / "report.json").read_text())
        assert report["summary"]["FAIL"] == 1
        assert report["checks"][0]["label"] == "accessibility/axe"

    def test_verifier_fails_when_required_check_blocked_env(self, tmp_path, monkeypatch):
        """BLOCKED_ENV on a profile-required check prevents acceptance."""
        from scripts import release_verifier as verifier
        monkeypatch.setenv("DJANGO_SETTINGS_MODULE", "portal.settings_document_tests")
        monkeypatch.setattr(verifier, "django_env", lambda: {})
        monkeypatch.setattr(verifier, "REPORT_DIR", tmp_path)
        monkeypatch.setattr(verifier, "REPORT_JSON", tmp_path / "report.json")
        monkeypatch.setattr(verifier, "REPORT_MD", tmp_path / "report.md")
        monkeypatch.setattr(verifier, "git_info", lambda: {"commit": "synthetic", "branch": "synthetic", "tree_clean": True})
        monkeypatch.setattr(verifier, "approvals_hash", lambda: "a" * 64)
        monkeypatch.setattr(verifier, "build_id", lambda: "synthetic")
        monkeypatch.setattr(verifier, "_ensure_verification_db", lambda: {"status": "PASS"})
        for name in ("verify_governance", "verify_django_checks", "verify_migrations",
                     "verify_backend_crud", "verify_storage", "verify_ocr", "verify_assignment",
                     "verify_frontend", "verify_accessibility"):
            monkeypatch.setattr(verifier, name, lambda: [])
        monkeypatch.setattr(verifier, "verify_a1", lambda profile="core": [])
        monkeypatch.setattr(verifier, "verify_eng001_checks", lambda profile="core": [
            {"label": "eng001/ENG-J2-STORAGE", "status": "BLOCKED_ENV",
             "error": "PostgreSQL-only evidence"},
        ])
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: pytest.fail("no subprocess in verifier unit test"))
        monkeypatch.setattr(sys, "argv", ["release_verifier.py"])
        # Required check unavailable: must exit 1 even though it is a
        # known infrastructure gap, not a test failure.
        assert verifier.main() == 1

    def test_verifier_tolerates_blocked_env_for_non_required_check(self, tmp_path, monkeypatch):
        """BLOCKED_ENV on a check not required for the profile stays visible but exits 0."""
        from scripts import release_verifier as verifier
        monkeypatch.setenv("DJANGO_SETTINGS_MODULE", "portal.settings_document_tests")
        monkeypatch.setattr(verifier, "django_env", lambda: {})
        monkeypatch.setattr(verifier, "REPORT_DIR", tmp_path)
        monkeypatch.setattr(verifier, "REPORT_JSON", tmp_path / "report.json")
        monkeypatch.setattr(verifier, "REPORT_MD", tmp_path / "report.md")
        monkeypatch.setattr(verifier, "git_info", lambda: {"commit": "synthetic", "branch": "synthetic", "tree_clean": True})
        monkeypatch.setattr(verifier, "approvals_hash", lambda: "a" * 64)
        monkeypatch.setattr(verifier, "build_id", lambda: "synthetic")
        monkeypatch.setattr(verifier, "_ensure_verification_db", lambda: {"status": "PASS"})
        for name in ("verify_governance", "verify_django_checks", "verify_migrations",
                     "verify_backend_crud", "verify_storage", "verify_ocr", "verify_assignment",
                     "verify_frontend", "verify_accessibility"):
            monkeypatch.setattr(verifier, name, lambda: [])
        monkeypatch.setattr(verifier, "verify_a1", lambda profile="core": [])
        monkeypatch.setattr(verifier, "verify_eng001_checks", lambda profile="core": [
            {"label": "eng001/synthetic", "status": "BLOCKED_ENV",
             "error": "Requires real Chromium"},
        ])
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: pytest.fail("no subprocess in verifier unit test"))
        monkeypatch.setattr(sys, "argv", ["release_verifier.py"])
        # Optional blocked check remains visibly BLOCKED_ENV in the report
        # without blocking the profile.
        assert verifier.main() == 0
        report = json.loads((tmp_path / "report.json").read_text())
        blocked = [c for c in report["checks"] if c["label"] == "eng001/synthetic"]
        assert blocked and blocked[0]["status"] == "BLOCKED_ENV"


class TestApprovalValidators:
    """Test that the approval validators themselves pass."""

    def test_validate_approvals_cli_passes(self):
        """scripts/validate_approvals.py exits 0 on current register."""
        proc = subprocess.run(
            [sys.executable, "scripts/validate_approvals.py"],
            capture_output=True,
            text=True,
            cwd=ROOT,
        )
        assert proc.returncode == 0, f"CLI failed: {proc.stderr}"

    def test_validate_planning_passes(self):
        """scripts/validate_planning.py exits 0 on current register."""
        proc = subprocess.run(
            [sys.executable, "scripts/validate_planning.py"],
            capture_output=True,
            text=True,
            cwd=ROOT,
            env={**os.environ, "PYTHONPATH": str(ROOT)},
        )
        assert proc.returncode == 0, f"Planning validator failed: {proc.stderr}"

    def test_approval_register_schema_valid(self):
        """approvals.json conforms to schema."""
        from planning.approval_register import validate
        result = validate(ROOT)
        assert result["result"] == "pass", f"Schema errors: {result['errors']}"


class TestVerificationDB:
    def test_verification_seed_adapter_is_isolated(self, monkeypatch):
        """Inspect the seeder adapter contract without touching any database."""
        from scripts import release_verifier as verifier
        calls = []
        def run(args, **kwargs):
            calls.append((args, kwargs))
            return subprocess.CompletedProcess(args, 0, stdout="synthetic seed", stderr="")
        monkeypatch.setattr(subprocess, "run", run)
        result = verifier._ensure_verification_db()
        assert result["status"] == "PASS"
        assert calls[0][0][0] == sys.executable
        assert Path(calls[0][0][1]).name == "seed_verification_db.py"
        assert calls[0][1]["env"]["DJANGO_SETTINGS_MODULE"] == "portal.settings_verification"
        assert calls[0][1]["timeout"] == 120
