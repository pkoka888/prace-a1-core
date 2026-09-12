"""End-to-end authenticated workflow test for the rehearsal script.

Bounded exercise of the rehearsal script's lifecycle, the real-browser
authenticated journey, and the restart-survival of the synthetic
record set. The test invokes the canonical workflow command
(``scripts/rehearse_synthetic_site.sh workflow``) so the CLI and
pytest share one outcome contract.

The test:

1. runs ``prepare`` against an isolated runtime root.
2. runs ``provision`` so ``operator.json`` carries the jan_planner
   role and TOTP secret.
3. runs the real-browser journey through ``workflow`` (the
   documented CLI subcommand).
4. restarts gunicorn and confirms the worker and case still
   resolve through the supervised-synthetic database.
5. stops gunicorn before the runtime directory is removed; the
   test-owned process is always stopped even on failure.

The test deliberately does NOT use ``@pytest.mark.django_db`` —
every database action runs in a subprocess against the supervised
SQLite, and the pytest-django test database is unrelated to this
journey. Without ``DJANGO_SETTINGS_MODULE`` the test still runs
because pytest.ini adds the repo root to ``sys.path`` and the
journey script subprocess sets ``DJANGO_SETTINGS_MODULE``
explicitly.

Per AGENTS.md ``Default delivery unit``, the journey is the actual
acceptance path. Service calls, force-login and helper-side admin
membership are explicitly forbidden.
"""
from __future__ import annotations

import json
import os
import secrets
import shutil
import socket
import subprocess
import uuid
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "rehearse_synthetic_site.sh"
BROWSER_HELPER = REPO_ROOT / "tests" / "_rehearse_workflow_browser.py"
PYTHON_BIN = REPO_ROOT / "venv" / "bin" / "python"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _run_script(args, env, *, timeout=600):
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        cwd=str(REPO_ROOT), env=env,
        capture_output=True, text=True, timeout=timeout,
    )


def _stop_workflow_gunicorn(workflow_root: Path, env: dict) -> int:
    """Stop the test-owned gunicorn process; returns the exit code."""
    pidfile = workflow_root / "gunicorn.pid"
    if pidfile.is_file():
        try:
            pid = int(pidfile.read_text().strip())
        except (ValueError, OSError):
            pid = None
        if pid is not None:
            try:
                os.kill(pid, 0)
            except OSError:
                pid = None
            if pid is not None:
                try:
                    os.kill(pid, 15)  # SIGTERM
                except OSError:
                    pass
                deadline = 30
                import time as _time
                start = _time.monotonic()
                while _time.monotonic() - start < deadline:
                    try:
                        os.kill(pid, 0)
                    except OSError:
                        break
                    _time.sleep(0.5)
                else:
                    try:
                        os.kill(pid, 9)  # SIGKILL
                    except OSError:
                        pass
    r = _run_script(["stop"], env, timeout=60)
    return r.returncode


@pytest.fixture
def workflow_root():
    name = f"supervised-workflow-pytest-{uuid.uuid4().hex[:8]}"
    root = REPO_ROOT / "runtime" / "portal" / name
    root.mkdir(mode=0o700)
    yield root
    shutil.rmtree(str(root), ignore_errors=True)


@pytest.fixture
def workflow_env(workflow_root):
    port = _free_port()
    return {
        "PATH": os.environ["PATH"],
        "HOME": os.environ.get("HOME", "/tmp"),
        "PRACE_RUNTIME_ROOT": str(workflow_root),
        "PRACE_SECRET_KEY": "workflow-pytest-"
                            + secrets.token_urlsafe(32),
        "PRACE_ALLOWED_HOSTS": "localhost,127.0.0.1",
        "PRACE_BIND": f"127.0.0.1:{port}",
        "PRACE_WORKERS": "1",
        "PRACE_REHEARSE_TIMEOUT": "60",
        "PRACE_READINESS_BUDGET_MS": "10000",
    }


def test_workflow_prepare_provision_browser_workflow_restart_persistence(
        workflow_root, workflow_env):
    """prepare → provision → start → browser workflow → stop →
    restart → query-after-restart → stop. Always stops the
    test-owned gunicorn before the runtime directory is removed."""
    gunicorn_started = False
    try:
        # 1. prepare (full migrate + collectstatic). ~45 s.
        r = _run_script(["prepare"], workflow_env, timeout=180)
        assert r.returncode == 0, (
            f"prepare failed:\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}")
        # 2. provision (operator + organization + jan_planner + TOTP).
        r = _run_script(["provision"], workflow_env, timeout=60)
        assert r.returncode == 0, (
            f"provision failed:\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}")
        operator = json.loads(
            (workflow_root / "operator.json").read_text())
        assert operator["membership_role"] == "jan_planner"
        assert operator["password"]
        assert operator["mfa"]["secret"]

        # 3. start gunicorn.
        r = _run_script(["start"], workflow_env, timeout=60)
        assert r.returncode == 0, (
            f"start failed:\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}")
        gunicorn_started = True

        # 4. Invoke the canonical workflow subcommand so the CLI and
        # the pytest test share the same outcome contract. The script
        # sets PYTHONPATH/cwd before invoking the browser helper, so
        # the standalone and the pytest entrypoint are equivalent.
        r = _run_script(["workflow"], workflow_env, timeout=300)
        assert r.returncode == 0, (
            f"workflow command failed (rc={r.returncode}):\n"
            f"STDOUT:\n{r.stdout[:2000]}\nSTDERR:\n{r.stderr[:1000]}")
        if not r.stdout.strip():
            raise AssertionError(
                f"workflow command produced empty stdout:\n"
                f"STDERR:\n{r.stderr[:1000]}")
        journey = json.loads(r.stdout)
        assert journey.get("ok") is True, (
            "workflow evidence.ok is False; required stages failed: "
            f"{journey.get('failed_stages', journey['stages'])}\n"
            f"{json.dumps(journey['stages'], indent=2)}")
        for stage in journey["required_stages"]:
            assert journey["stages"].get(stage, {}).get("ok") is True, (
                f"required stage {stage!r} did not pass:\n"
                f"{json.dumps(journey['stages'][stage], indent=2)}")
        worker_pk = journey["worker_pk"]
        case_pk = journey["case_pk"]
        document_pk = journey["document_pk"]
        # The TOTP code never appears in evidence.
        assert "totp_code_used" not in journey, (
            "TOTP code leaked into journey evidence")
        assert "password" not in journey, (
            "operator password leaked into journey evidence")

        # 5. stop gunicorn.
        r = _run_script(["stop"], workflow_env, timeout=60)
        assert r.returncode == 0, (
            f"stop failed:\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}")
        gunicorn_started = False

        # 6. restart gunicorn.
        r = _run_script(["start"], workflow_env, timeout=60)
        assert r.returncode == 0, (
            f"start after stop failed:\nSTDOUT:\n{r.stdout}\n"
            f"STDERR:\n{r.stderr}")
        gunicorn_started = True

        # 7. query-after-restart. The subprocess reloads the
        # supervised-synthetic settings and queries the supervised
        # SQLite for the worker, document and case captured during
        # the browser journey. This is the restart-survival evidence.
        query_env = dict(workflow_env)
        query_env["PYTHONPATH"] = str(REPO_ROOT)
        query_env["DJANGO_SETTINGS_MODULE"] = (
            "portal.settings_supervised_synthetic")
        query_env["PRACE_RELEASE_MANIFEST"] = (
            str(workflow_root / "release_manifest.json"))
        query_env["PRACE_RELEASE_MANIFEST_SHA256"] = (
            (workflow_root / ".release_manifest.sha256").read_text().strip())
        query_env["WORKER_PK"] = str(worker_pk)
        query_env["DOCUMENT_PK"] = str(document_pk)
        query_env["CASE_PK"] = str(case_pk)
        proc = subprocess.run(
            [str(PYTHON_BIN), "-c", """
import os, json
import django; django.setup()
from portal.release1a.models import Worker, A1Case, Document
result = {
    'worker_found': Worker.objects.filter(pk=int(os.environ['WORKER_PK'])).exists(),
    'case_found': A1Case.objects.filter(pk=int(os.environ['CASE_PK'])).exists(),
    'document_found': Document.objects.filter(pk=int(os.environ['DOCUMENT_PK'])).exists(),
}
print(json.dumps(result))
"""],
            env=query_env,
            cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=30,
        )
        assert proc.returncode == 0, (
            f"query-after-restart failed (rc={proc.returncode}):\n"
            f"STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
        query = json.loads(proc.stdout.strip().splitlines()[-1])
        assert query.get("worker_found") is True, (
            f"worker {worker_pk} not found after restart: {query}")
        assert query.get("case_found") is True, (
            f"case {case_pk} not found after restart: {query}")
        assert query.get("document_found") is True, (
            f"document {document_pk} not found after restart: {query}")
    finally:
        # Always stop the test-owned gunicorn before the runtime
        # directory is removed by the workflow_root fixture.
        if gunicorn_started:
            rc = _stop_workflow_gunicorn(workflow_root, workflow_env)
            assert rc == 0, (
                f"final stop returned {rc}; runtime root may contain "
                f"a stale gunicorn process")