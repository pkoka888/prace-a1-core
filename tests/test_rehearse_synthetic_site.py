"""Cheap unit tests for the supervised synthetic rehearsal script.

These tests cover script existence, the unknown-command path, the
confinement-validate contract, the manifest sidecar SHA correctness, the
stop-without-pidfile, the logs-without-log-file, the status-while-stopped,
the rollback-preserves-runtime, and the secret-key-rejection contract.

They use ``prepare-manifest-only`` so they do NOT run Django migrate or
collectstatic. Each test completes in a few seconds. The full lifecycle
integration is exercised in ``test_rehearse_synthetic_site_lifecycle.py``
under its own change-package selector.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "rehearse_synthetic_site.sh"


@pytest.fixture
def rehearsal_root(tmp_path):
    """Point the script at a confined runtime root under the repo's
    existing ``runtime/portal/`` subtree (the supervised settings
    module refuses anything outside that subtree). The test cleans
    up after itself.
    """
    import uuid as _uuid
    name = f"supervised-test-{_uuid.uuid4().hex[:8]}"
    root = REPO_ROOT / "runtime" / "portal" / name
    root.mkdir(mode=0o700)
    yield root
    shutil.rmtree(str(root), ignore_errors=True)


@pytest.fixture
def required_env(rehearsal_root):
    return {
        "PATH": os.environ["PATH"],
        "HOME": os.environ.get("HOME", "/tmp"),
        "PRACE_RUNTIME_ROOT": str(rehearsal_root),
        "PRACE_SECRET_KEY": "test-secret-" + "x" * 60,
        "PRACE_ALLOWED_HOSTS": "localhost,127.0.0.1",
        "PRACE_BIND": "127.0.0.1:0",
        "PRACE_WORKERS": "1",
        "PRACE_REHEARSE_TIMEOUT": "5",
    }


def _run(args, env, cwd=None, timeout=60):
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        cwd=cwd or REPO_ROOT, env=env, capture_output=True,
        text=True, timeout=timeout,
    )


def test_script_exists_and_is_executable():
    assert SCRIPT.exists()
    assert os.access(SCRIPT, os.X_OK)


def test_unknown_command_fails_with_usage(rehearsal_root):
    r = _run(["bogus"], {
        "PATH": os.environ["PATH"],
        "PRACE_RUNTIME_ROOT": str(rehearsal_root),
    })
    assert r.returncode == 1
    assert "Usage:" in r.stderr


def test_confinement_validate_rejects_non_supervised_path(tmp_path):
    """A path outside the approved runtime subtree must be rejected
    with no filesystem mutation, exactly as settings_supervised_synthetic
    would refuse it at import time."""
    target = tmp_path / "outside-approved-runtime"
    r = _run(["prepare-manifest-only"], {
        "PATH": os.environ["PATH"],
        "PRACE_RUNTIME_ROOT": str(target),
    })
    assert r.returncode != 0
    assert "supervised-" in r.stderr
    # No files written, no directories created.
    assert not target.exists()


def test_confinement_validate_rejects_path_traversal(rehearsal_root):
    """A path containing parent-directory traversal must be rejected."""
    target = rehearsal_root.parent / "supervised-evil" / ".." / "escaped"
    r = _run(["prepare-manifest-only"], {
        "PATH": os.environ["PATH"],
        "PRACE_RUNTIME_ROOT": str(target),
    })
    assert r.returncode != 0
    # The 'escaped' directory must not have been created.
    assert not (rehearsal_root.parent / "escaped").exists()


def test_confinement_validate_rejects_existing_non_700_dir(rehearsal_root):
    """A pre-existing supervised-* directory with mode 0755 must be
    rejected without the script adopting it via chmod."""
    import stat
    rehearsal_root.chmod(0o755)
    try:
        r = _run(["prepare-manifest-only"], {
            "PATH": os.environ["PATH"],
            "PRACE_RUNTIME_ROOT": str(rehearsal_root),
        })
        assert r.returncode != 0
        assert "0700" in r.stderr
        # The original mode must be preserved.
        assert (rehearsal_root.stat().st_mode & 0o777) == 0o755
    finally:
        rehearsal_root.chmod(0o700)


def test_prepare_manifest_only_creates_confined_layout_and_manifest(required_env):
    r = _run(["prepare-manifest-only"], required_env, timeout=30)
    assert r.returncode == 0, r.stderr
    root = Path(required_env["PRACE_RUNTIME_ROOT"])
    assert (root / "release_manifest.json").exists()
    assert (root / ".release_manifest.sha256").exists()
    manifest_mode = (root / "release_manifest.json").stat().st_mode & 0o777
    assert manifest_mode == 0o400
    for child in ("storage", "media", "static", "cache", "tmp", "logs"):
        d = root / child
        assert d.is_dir(), f"missing {child}"
        assert d.stat().st_mode & 0o077 == 0, f"{child} must be operator-only"
    manifest = json.loads((root / "release_manifest.json").read_text())
    assert manifest["git_commit"]
    assert len(manifest["git_commit"]) == 40
    assert manifest["schema_version"] == 1


def test_prepare_manifest_only_sidecar_sha_matches_manifest(required_env):
    r = _run(["prepare-manifest-only"], required_env, timeout=30)
    assert r.returncode == 0, r.stderr
    root = Path(required_env["PRACE_RUNTIME_ROOT"])
    sha_file = (root / ".release_manifest.sha256").read_text().strip()
    import hashlib
    actual = hashlib.sha256(
        (root / "release_manifest.json").read_bytes()).hexdigest()
    assert sha_file == actual


def test_status_reports_stopped_when_no_pidfile(required_env):
    r = _run(["prepare-manifest-only"], required_env, timeout=30)
    assert r.returncode == 0, r.stderr
    r2 = _run(["status"], required_env)
    assert r2.returncode == 0
    assert "stopped" in r2.stdout or "no pidfile" in r2.stdout


def test_status_rejects_wrong_pidfile_contents(required_env):
    """A pidfile pointing at a non-gunicorn process must be rejected
    with exit 1, not silently reported as running."""
    r = _run(["prepare-manifest-only"], required_env, timeout=30)
    assert r.returncode == 0, r.stderr
    root = Path(required_env["PRACE_RUNTIME_ROOT"])
    # Find a real, unrelated process to point the pidfile at. Any
    # process owned by the current user that is not gunicorn works.
    own_pid = os.getpid()
    root.joinpath("gunicorn.pid").write_text(str(own_pid))
    root.joinpath(".gunicorn.cmdline").write_text(
        f"pid={own_pid}\nbind=127.0.0.1:9999\nruntime_root={root}\nlaunched_at=0\n"
    )
    root.joinpath(".gunicorn.started_at").write_text("0")
    r2 = _run(["status"], required_env)
    assert r2.returncode == 1
    assert "does not match" in r2.stdout or "stale" in r2.stdout or "do not match" in r2.stdout


def test_stop_rejects_unrelated_pidfile_contents(required_env):
    """A pidfile pointing at a non-gunicorn process must NOT result in
    a SIGTERM being sent to that process."""
    r = _run(["prepare-manifest-only"], required_env, timeout=30)
    assert r.returncode == 0, r.stderr
    root = Path(required_env["PRACE_RUNTIME_ROOT"])
    own_pid = os.getpid()
    root.joinpath("gunicorn.pid").write_text(str(own_pid))
    root.joinpath(".gunicorn.cmdline").write_text(
        f"pid={own_pid}\nbind=127.0.0.1:9999\nruntime_root={root}\nlaunched_at=0\n"
    )
    root.joinpath(".gunicorn.started_at").write_text("0")
    r2 = _run(["stop"], required_env)
    # Either rejects (exit 3) or reports the stale pidfile; it must
    # never silently SIGTERM our own process (which is the pytest test
    # runner and would crash the test).
    assert r2.returncode != 0
    assert "not gunicorn" in r2.stdout + r2.stderr \
        or "refusing to signal" in r2.stdout + r2.stderr \
        or "cmdline does not mention" in r2.stdout + r2.stderr


def test_logs_without_log_file_is_graceful(required_env):
    r = _run(["logs"], required_env)
    assert r.returncode == 0
    assert "no log file" in r.stdout


def test_stop_without_pidfile_is_graceful(required_env):
    r = _run(["stop"], required_env)
    assert r.returncode == 0
    assert "not running" in r.stdout


def test_rollback_preserves_runtime_root(required_env):
    r = _run(["prepare-manifest-only"], required_env, timeout=30)
    assert r.returncode == 0, r.stderr
    r2 = _run(["rollback"], required_env)
    assert r2.returncode == 0, r2.stderr
    assert "Preserving" in r2.stdout
    assert "Operator action" in r2.stdout
    root = Path(required_env["PRACE_RUNTIME_ROOT"])
    assert root.exists()
    assert (root / "release_manifest.json").exists()


def test_secret_key_default_is_rejected_by_settings(required_env):
    """The settings module refuses the base default secret; prepare
    must therefore fail closed at the migrate/collectstatic step.
    prepare-manifest-only succeeds (it does not load the settings
    module), so we use the full prepare here."""
    env = dict(required_env)
    env["PRACE_SECRET_KEY"] = "synthetic-m2-local-only-insecure-default"
    r = _run(["prepare"], env, timeout=60)
    # The script-level ensure_env check is in start, not prepare; the
    # supervised settings module's _require_secret_value must fail.
    # Either the script's own secret-key check (during migrate) or the
    # settings module's check produces exit != 0.
    assert r.returncode != 0
    out = r.stdout + r.stderr
    assert "secret" in out.lower() or "secret_key" in out.lower() \
        or "improperlyconfigured" in out.lower() or "synthetic-m2" in out


def test_manifest_mode_is_0o400_under_permissive_umask(required_env, monkeypatch):
    """With umask 022 the manifest file's mode would default to 0o644
    unless the script enforces 0o400 explicitly. The 2026-09-11 review
    observed a 0644 gunicorn.log file under the same permissive umask.
    Confirm the manifest is 0o400 regardless of incoming umask."""
    import os as _os
    _os.umask(0o022)
    r = _run(["prepare-manifest-only"], required_env, timeout=30)
    assert r.returncode == 0, r.stderr
    root = Path(required_env["PRACE_RUNTIME_ROOT"])
    mode = (root / "release_manifest.json").stat().st_mode & 0o777
    assert mode == 0o400, f"manifest mode is {oct(mode)}, expected 0o400"
