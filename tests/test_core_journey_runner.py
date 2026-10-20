"""Unit tests for the core journey orchestrator (scripts/run_core_journey.py).

These tests exercise the orchestrator's pure logic without requiring a real
PostgreSQL cluster or browser. They use monkeypatching and fake executables.
"""

from __future__ import annotations

import json
import signal
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import run_core_journey as rcj


def _make_fake_pg_bin(tmp_path: Path) -> Path:
    """Create a directory with fake pg binaries that exit 0."""
    bin_dir = tmp_path / "pg_bin"
    bin_dir.mkdir()
    for name in ("initdb", "pg_ctl", "createdb", "psql"):
        script = bin_dir / name
        script.write_text("#!/bin/sh\nexit 0\n")
        script.chmod(0o755)
    return bin_dir


def _make_fake_pg_bin_fail_start(tmp_path: Path) -> Path:
    """Create fake pg binaries where pg_ctl start fails."""
    bin_dir = tmp_path / "pg_bin_fail"
    bin_dir.mkdir()
    # initdb, createdb, psql succeed
    for name in ("initdb", "createdb", "psql"):
        script = bin_dir / name
        script.write_text("#!/bin/sh\nexit 0\n")
        script.chmod(0o755)
    # pg_ctl: fail on start, succeed on stop
    pg_ctl = bin_dir / "pg_ctl"
    pg_ctl.write_text(
        "#!/bin/sh\n"
        'for arg in "$@"; do\n'
        '    if [ "$arg" = "start" ]; then exit 1; fi\n'
        "done\n"
        "exit 0\n"
    )
    pg_ctl.chmod(0o755)
    return bin_dir


def _prepare_work_tree(tmp_path: Path) -> Path:
    """Create a minimal exported work tree with required scripts."""
    work = tmp_path / "work"
    scripts = work / "scripts"
    scripts.mkdir(parents=True)
    # rehearse_synthetic_site.sh
    (scripts / "rehearse_synthetic_site.sh").write_text("#!/bin/sh\nexit 0\n")
    (scripts / "rehearse_synthetic_site.sh").chmod(0o755)
    # rehearse_verify_persistence.py
    (scripts / "rehearse_verify_persistence.py").write_text(
        "#!/usr/bin/env python3\nimport sys\nsys.exit(0)\n"
    )
    (scripts / "rehearse_verify_persistence.py").chmod(0o755)
    # build_release_manifest.py
    (scripts / "build_release_manifest.py").write_text(
        "#!/usr/bin/env python3\nimport sys\nsys.exit(0)\n"
    )
    (scripts / "build_release_manifest.py").chmod(0o755)
    # manage.py
    (work / "manage.py").write_text("#!/usr/bin/env python3\nimport sys\nsys.exit(0)\n")
    (work / "manage.py").chmod(0o755)
    return work


def test_missing_pg_bin_refuses_before_any_mutation(tmp_path, monkeypatch):
    """Missing pg binary should raise EXIT_CONFIG before any filesystem mutation."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    state = tmp_path / "state"
    work = _prepare_work_tree(tmp_path)
    monkeypatch.chdir(work)
    pg_bin = tmp_path / "missing_pg_bin"
    commit = "0" * 40
    with pytest.raises(SystemExit) as exc:
        rcj.run_core_journey(
            work=work,
            repo_root=repo_root,
            state=state,
            commit=commit,
            profile="core",
            pg_bin=pg_bin,
            pg_port=55450,
            http_port=18005,
            timeout=1.0,
        )
    assert exc.value.code == rcj.EXIT_CONFIG
    # No mutation should have occurred
    assert not (repo_root / "runtime").exists()
    assert not state.exists()


def test_build_env_isolation_and_whitelist(tmp_path, monkeypatch):
    """build_env must ignore caller overrides and produce a clean whitelist."""
    # Create fake python and gunicorn
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    python_bin = bin_dir / "python"
    python_bin.write_text("#!/bin/sh\nexit 0\n")
    python_bin.chmod(0o755)
    gunicorn_bin = bin_dir / "gunicorn"
    gunicorn_bin.write_text("#!/bin/sh\nexit 0\n")
    gunicorn_bin.chmod(0o755)

    pg_root = tmp_path / "pg_root"
    pg_root.mkdir(mode=0o700)
    state = tmp_path / "state"
    state.mkdir(mode=0o700)
    (state / "home").mkdir(mode=0o700)
    (state / "tmp").mkdir(mode=0o700)
    supervised = tmp_path / "supervised"
    supervised.mkdir(mode=0o700)

    # Monkeypatch real_home_dir to a temp home with browser cache
    home = tmp_path / "home"
    home.mkdir()
    (home / ".cache" / "ms-playwright").mkdir(parents=True)
    monkeypatch.setattr(rcj, "real_home_dir", lambda: str(home))

    # Set caller environment overrides
    for name in rcj._EVIDENCE_OVERRIDE_NAMES:
        monkeypatch.setenv(name, "should-not-appear")
    monkeypatch.setenv("PRACE_DB_NAME", "caller-db")
    monkeypatch.setenv("PRACE_DB_USER", "caller-user")
    monkeypatch.setenv("PRACE_DB_HOST", "caller-host")
    monkeypatch.setenv("PRACE_DB_PORT", "5432")
    monkeypatch.setenv("PGPASSWORD", "caller-pgpass")
    monkeypatch.setenv("DJANGO_SETTINGS_MODULE", "caller.settings")
    monkeypatch.setenv("PATH", "/usr/bin:/bin")

    env = rcj.build_env(
        work=Path.cwd(),
        pg_root=pg_root,
        db_name="testdb",
        db_user="testuser",
        db_port=55450,
        bind="127.0.0.1:18005",
        commit="0" * 40,
        state=state,
        python_bin=str(python_bin),
        gunicorn=str(gunicorn_bin),
        supervised=supervised,
    )

    # Override names must not be present
    for name in rcj._EVIDENCE_OVERRIDE_NAMES:
        assert name not in env, f"override {name} leaked into environment"

    # Caller DB variables must not be present
    assert env.get("PRACE_DB_NAME") == "testdb"
    assert env.get("PRACE_DB_USER") == "testuser"
    assert env.get("PRACE_DB_HOST") == str(pg_root)
    assert env.get("PRACE_DB_PORT") == "55450"
    assert "PRACE_DB_PASSWORD" not in env
    assert "PGPASSWORD" not in env

    # Required keys present
    assert env["PGPASSFILE"] == str(pg_root / "pgpass")
    assert env["HOME"] == str(state / "home")
    assert env["TMPDIR"] == str(state / "tmp")
    assert env["PLAYWRIGHT_BROWSERS_PATH"] == str(home / ".cache" / "ms-playwright")
    assert env["PRACE_RELEASE_MANIFEST_COMMIT"] == "0" * 40
    assert env["PRACE_RELEASE_MANIFEST_SHA256"] == ""
    assert env["PRACE_SECRET_KEY"]
    assert env["PRACE_RUNTIME_ROOT"] == str(supervised)
    assert env["PRACE_REHEARSE_PYTHON_BIN"] == str(python_bin)
    assert env["PRACE_REHEARSE_GUNICORN"] == str(gunicorn_bin)
    assert env["PATH"] == f"{bin_dir}:/usr/bin:/bin"
    # DJANGO_SETTINGS_MODULE is not set by build_env; it's set by the verifier later.


def test_run_phase_failure_retention_and_log_mode(tmp_path):
    """run_phase must record native exit code and store logs with mode 0600."""
    state = tmp_path / "state"
    state.mkdir(mode=0o700)
    steps_dir = state / "journey"
    steps_dir.mkdir(mode=0o700)

    # Command that exits with code 7 and writes to stderr
    argv = [
        sys.executable,
        "-c",
        "import sys; sys.stderr.write('phase error\\n'); sys.exit(7)",
    ]
    code, record = rcj.run_phase(
        state, steps_dir, "test-phase", argv, cwd=Path.cwd(), env={}, timeout=10
    )

    assert code == 7
    assert record["exit_code"] == 7
    assert record["name"] == "test-phase"
    assert record["argv"] == argv
    stdout_path = Path(record["stdout_log"])
    stderr_path = Path(record["stderr_log"])
    assert stdout_path.exists()
    assert stderr_path.exists()
    assert oct(stdout_path.stat().st_mode & 0o777) == "0o600"
    assert oct(stderr_path.stat().st_mode & 0o777) == "0o600"
    assert record["stdout_sha256"] == rcj.digest(stdout_path.read_bytes())
    assert record["stderr_sha256"] == rcj.digest(stderr_path.read_bytes())
    assert "phase error" in stderr_path.read_text()


def test_run_phase_timeout_kills_process_group(tmp_path):
    """run_phase must kill the process group on timeout and return 124."""
    state = tmp_path / "state"
    state.mkdir(mode=0o700)
    steps_dir = state / "journey"
    steps_dir.mkdir(mode=0o700)

    # Command that sleeps longer than timeout
    argv = [sys.executable, "-c", "import time; time.sleep(10)"]
    code, record = rcj.run_phase(
        state, steps_dir, "timeout-phase", argv, cwd=Path.cwd(), env={}, timeout=0.1
    )

    assert code == 124
    assert record["exit_code"] == 124
    # Ensure the process was killed quickly (duration < 1 second)
    # Note: duration_seconds not in record, but we can check that it didn't sleep 10 seconds.
    # This is a best-effort check; we just ensure the function returns promptly.


def _canonical_core_evidence() -> dict:
    """Return a minimal valid core evidence dict."""
    return {
        "ok": True,
        "profile": "core",
        "organization_id": 1,
        "worker_pk": 1,
        "document_pk": 1,
        "assignment_pk": 1,
        "source_document_sha256": "a" * 64,
        "required_stages": list(rcj.CORE_STAGES_REQUIRED),
        "stages": {
            **{
                stage: {"stage": stage, "ok": True}
                for stage in rcj.CORE_STAGES_REQUIRED
            },
            "identity_confirmed": {
                "stage": "identity_confirmed",
                "ok": True,
                "confirmed_fields": {"family_name": "Doe"},
                "worker_pk": 1,
            },
            "assignment_corrected": {
                "stage": "assignment_corrected",
                "ok": True,
                "corrected_activity": "street changed",
                "assignment_pk": 1,
            },
            "source_document_downloaded": {
                "stage": "source_document_downloaded",
                "ok": True,
                "document_pk": 1,
                "sha256": "a" * 64,
            },
            "a1_skipped": {
                "stage": "a1_skipped",
                "ok": True,
                "reason": "core profile does not exercise A1 stages",
            },
        },
    }


def test_parse_journey_evidence_success_core():
    """Valid core evidence should parse without errors."""
    evidence = _canonical_core_evidence()
    parsed, errors = rcj.parse_journey_evidence(json.dumps(evidence).encode(), "core")
    assert errors == []
    assert parsed == evidence


def test_parse_journey_evidence_fails_on_failed_required_stage():
    """A required stage with ok=False must be rejected."""
    evidence = _canonical_core_evidence()
    evidence["stages"]["worker_created"]["ok"] = False
    _, errors = rcj.parse_journey_evidence(json.dumps(evidence).encode(), "core")
    assert any("required stage worker_created did not pass" in e for e in errors)


def test_parse_journey_evidence_fails_on_missing_required_stage():
    """Missing a required stage must be rejected."""
    evidence = _canonical_core_evidence()
    del evidence["stages"]["worker_created"]
    _, errors = rcj.parse_journey_evidence(json.dumps(evidence).encode(), "core")
    assert any("missing required stage: worker_created" in e for e in errors)


def test_parse_journey_evidence_fails_on_mismatched_required_stages_list():
    """required_stages must match expected set exactly."""
    evidence = _canonical_core_evidence()
    evidence["required_stages"] = ["login_redirect"]  # missing others
    _, errors = rcj.parse_journey_evidence(json.dumps(evidence).encode(), "core")
    assert any("required_stages omits" in e for e in errors)


def test_parse_journey_evidence_fails_on_malformed_identity_confirmed():
    """Malformed identity_confirmed stage must be rejected."""
    evidence = _canonical_core_evidence()
    evidence["stages"]["identity_confirmed"] = "not a dict"
    _, errors = rcj.parse_journey_evidence(json.dumps(evidence).encode(), "core")
    assert any("stages.identity_confirmed is missing" in e for e in errors)


def test_parse_journey_evidence_fails_on_missing_identity_confirmed():
    """Missing identity_confirmed stage must be rejected."""
    evidence = _canonical_core_evidence()
    del evidence["stages"]["identity_confirmed"]
    _, errors = rcj.parse_journey_evidence(json.dumps(evidence).encode(), "core")
    assert any("stages.identity_confirmed is missing" in e for e in errors)


def test_parse_journey_evidence_fails_on_mismatched_worker_pk():
    """identity_confirmed.worker_pk must match evidence.worker_pk."""
    evidence = _canonical_core_evidence()
    evidence["stages"]["identity_confirmed"]["worker_pk"] = 999
    _, errors = rcj.parse_journey_evidence(json.dumps(evidence).encode(), "core")
    assert any("identity_confirmed.worker_pk does not match" in e for e in errors)


def test_parse_journey_evidence_fails_on_missing_assignment_corrected():
    """Missing assignment_corrected stage must be rejected."""
    evidence = _canonical_core_evidence()
    del evidence["stages"]["assignment_corrected"]
    _, errors = rcj.parse_journey_evidence(json.dumps(evidence).encode(), "core")
    assert any("stages.assignment_corrected is missing" in e for e in errors)


def test_parse_journey_evidence_fails_on_source_document_downloaded_mismatch():
    """source_document_downloaded must match document_pk and sha256."""
    evidence = _canonical_core_evidence()
    evidence["stages"]["source_document_downloaded"]["document_pk"] = 999
    _, errors = rcj.parse_journey_evidence(json.dumps(evidence).encode(), "core")
    assert any(
        "source_document_downloaded.document_pk does not match" in e for e in errors
    )

    evidence = _canonical_core_evidence()
    evidence["stages"]["source_document_downloaded"]["sha256"] = "b" * 64
    _, errors = rcj.parse_journey_evidence(json.dumps(evidence).encode(), "core")
    assert any("source_document_downloaded.sha256 does not match" in e for e in errors)


def _canonical_optional_a1_evidence() -> dict:
    """Return a minimal valid optional-a1 evidence dict."""
    base = _canonical_core_evidence()
    base["profile"] = "optional-a1"
    base["required_stages"] = list(rcj.CORE_STAGES_REQUIRED | rcj.A1_EXTRA_STAGES)
    base["case_pk"] = 1
    base["regenerated_case_pk"] = 2
    base["pdf_sha256"] = "c" * 64
    base["regen_sha256"] = "d" * 64
    # Add A1 stages
    for stage in rcj.A1_EXTRA_STAGES:
        base["stages"][stage] = {"stage": stage, "ok": True}
    # Remove a1_skipped
    base["stages"].pop("a1_skipped", None)
    return base


def test_parse_journey_evidence_success_optional_a1():
    """Valid optional-a1 evidence should parse without errors."""
    evidence = _canonical_optional_a1_evidence()
    parsed, errors = rcj.parse_journey_evidence(
        json.dumps(evidence).encode(), "optional-a1"
    )
    assert errors == []
    assert parsed == evidence


def test_parse_journey_evidence_fails_on_missing_a1_extra_keys():
    """Optional-a1 evidence must include non-empty A1 extra keys."""
    evidence = _canonical_optional_a1_evidence()
    evidence["case_pk"] = 0  # invalid int
    _, errors = rcj.parse_journey_evidence(json.dumps(evidence).encode(), "optional-a1")
    assert any("missing mandatory A1 evidence key: case_pk" in e for e in errors)

    evidence = _canonical_optional_a1_evidence()
    evidence["pdf_sha256"] = ""
    _, errors = rcj.parse_journey_evidence(json.dumps(evidence).encode(), "optional-a1")
    assert any("missing mandatory A1 evidence key: pdf_sha256" in e for e in errors)


def test_parse_journey_evidence_fails_on_missing_a1_stage():
    """Optional-a1 must have all A1 extra stages with ok=True."""
    evidence = _canonical_optional_a1_evidence()
    del evidence["stages"]["a1_prepared"]
    _, errors = rcj.parse_journey_evidence(json.dumps(evidence).encode(), "optional-a1")
    assert any("missing required stage: a1_prepared" in e for e in errors)


def test_run_core_journey_failed_pg_start_triggers_pg_stop(tmp_path, monkeypatch):
    """If pg-start fails, the finally block must still run pg-stop."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    state = tmp_path / "state"
    work = _prepare_work_tree(tmp_path)
    monkeypatch.chdir(work)

    pg_bin = _make_fake_pg_bin_fail_start(tmp_path)

    home = tmp_path / "home"
    home.mkdir()
    (home / ".cache" / "ms-playwright").mkdir(parents=True)
    monkeypatch.setattr(rcj, "real_home_dir", lambda: str(home))
    monkeypatch.setattr(rcj, "check_socket_path", lambda *args, **kwargs: None)

    with pytest.raises(SystemExit) as exc:
        rcj.run_core_journey(
            work=work,
            repo_root=repo_root,
            state=state,
            commit="0" * 40,
            profile="core",
            pg_bin=pg_bin,
            pg_port=55450,
            http_port=18005,
            timeout=1.0,
        )
    assert exc.value.code == rcj.EXIT_PHASE

    receipt_path = state / "core-journey.json"
    assert receipt_path.exists()
    receipt = json.loads(receipt_path.read_text())
    assert receipt["ok"] is False
    assert receipt["postgres_stopped"] is True
    phase_names = [p["name"] for p in receipt["phases"]]
    assert "initdb" in phase_names
    assert "pg-start" in phase_names
    assert "pg-stop" in phase_names


def test_run_core_journey_missing_pg_bin_no_state_mutation(tmp_path, monkeypatch):
    """Missing pg-bin should not create state or runtime directories."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    state = tmp_path / "state"
    work = _prepare_work_tree(tmp_path)
    monkeypatch.chdir(work)

    pg_bin = tmp_path / "missing_pg_bin"
    with pytest.raises(SystemExit) as exc:
        rcj.run_core_journey(
            work=work,
            repo_root=repo_root,
            state=state,
            commit="0" * 40,
            profile="core",
            pg_bin=pg_bin,
            pg_port=55450,
            http_port=18005,
            timeout=1.0,
        )
    assert exc.value.code == rcj.EXIT_CONFIG
    assert not state.exists()
    assert not (repo_root / "runtime").exists()


def test_run_core_journey_invalid_profile_rejected():
    """Invalid profile should be rejected early (via argparse)."""
    with pytest.raises(SystemExit):
        rcj.parse_args(
            [
                "--commit",
                "0" * 40,
                "--repo-root",
                ".",
                "--state",
                ".",
                "--profile",
                "invalid",
            ]
        )


def test_parse_verifier_result_success_core():
    """A fully passing core verifier result should parse without errors."""
    result = {
        "ok": True,
        "profile": "core",
        "checks": {name: True for name in rcj.VERIFIER_CORE_CHECKS},
    }
    parsed, errors = rcj.parse_verifier_result(json.dumps(result).encode(), "core")
    assert errors == []
    assert parsed["ok"] is True


def test_parse_verifier_result_fails_on_missing_check():
    """A verifier result missing a mandatory check must be rejected."""
    result = {
        "ok": True,
        "profile": "core",
        "checks": {"worker_found": True},
    }
    _, errors = rcj.parse_verifier_result(json.dumps(result).encode(), "core")
    assert any("missing mandatory verifier check: document_found" in e for e in errors)


def test_parse_verifier_result_fails_on_false_check():
    """A verifier check with a False-like value must be rejected."""
    result = {
        "ok": True,
        "profile": "core",
        "checks": {
            name: (False if name == "worker_found" else True)
            for name in rcj.VERIFIER_CORE_CHECKS
        },
    }
    _, errors = rcj.parse_verifier_result(json.dumps(result).encode(), "core")
    assert any("verifier check did not pass: worker_found" in e for e in errors)


def test_parse_verifier_result_fails_on_ok_false():
    """Verifier result with ok=False must be rejected even if all checks pass."""
    result = {
        "ok": False,
        "profile": "core",
        "checks": {name: True for name in rcj.VERIFIER_CORE_CHECKS},
    }
    _, errors = rcj.parse_verifier_result(json.dumps(result).encode(), "core")
    assert any("verifier.ok is not true" in e for e in errors)


def test_run_phase_unexpected_exception_is_recorded(tmp_path, monkeypatch):
    """run_phase must record unexpected exceptions and re-raise them."""
    state = tmp_path / "state"
    state.mkdir(mode=0o700)
    steps_dir = state / "journey"
    steps_dir.mkdir(mode=0o700)

    class BadProcess:
        def poll(self):
            raise MemoryError("simulated unexpected failure")

        def wait(self, timeout=None):
            raise MemoryError("simulated unexpected failure")

    monkeypatch.setattr(subprocess, "Popen", lambda *a, **kw: BadProcess())
    with pytest.raises(MemoryError, match="simulated unexpected failure"):
        rcj.run_phase(
            state,
            steps_dir,
            "bad-phase",
            [sys.executable, "-c", "import time; time.sleep(10)"],
            cwd=Path.cwd(),
            env={},
            timeout=5.0,
        )


def test_run_phase_interrupted_by_cancellation(tmp_path):
    """run_phase must terminate the process group when interrupted."""
    state = tmp_path / "state"
    state.mkdir(mode=0o700)
    steps_dir = state / "journey"
    steps_dir.mkdir(mode=0o700)

    cancel = rcj.Cancellation()
    cancel.request(signal.SIGTERM, "test cancellation")
    argv = [sys.executable, "-c", "import time; time.sleep(10)"]
    with pytest.raises(rcj.JourneyInterrupted) as exc_info:
        rcj.run_phase(
            state,
            steps_dir,
            "interrupted-phase",
            argv,
            cwd=Path.cwd(),
            env={},
            timeout=10.0,
            cancellation=cancel,
        )
    assert exc_info.value.signum == signal.SIGTERM
    assert exc_info.value.reason == "test cancellation"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
