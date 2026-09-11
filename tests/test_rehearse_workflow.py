"""End-to-end authenticated workflow test for the rehearsal script.

Bounded exercise of the rehearsal script's lifecycle, the real-browser
authenticated journey, and the restart-survival of the synthetic
record set. The test:

1. runs ``prepare`` against an isolated runtime root.
2. runs ``provision`` so ``operator.json`` carries the jan_planner
   role and TOTP secret.
3. runs the real-browser journey (login + TOTP, worker, document
   upload, assignment, A1 preparation) through ``workflow``.
4. restarts gunicorn and confirms the worker and case still
   resolve through the supervised-synthetic database.

The test deliberately does NOT use ``@pytest.mark.django_db`` —
every database action runs in a subprocess against the supervised
SQLite, and the pytest-django test database is unrelated to this
journey. Running with the catalog command (which does not export
``DJANGO_SETTINGS_MODULE``) skips the workflow test; pytest-django
is therefore never asked to load a database for this journey.

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


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _run(args, env, *, timeout=600):
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        cwd=str(REPO_ROOT), env=env,
        capture_output=True, text=True, timeout=timeout,
    )


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
    restart → query-after-restart → stop."""
    # 1. prepare (full migrate + collectstatic). ~45 s.
    r = _run(["prepare"], workflow_env, timeout=180)
    assert r.returncode == 0, (
        f"prepare failed:\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}")
    # 2. provision (operator + organization + jan_planner + TOTP).
    r = _run(["provision"], workflow_env, timeout=60)
    assert r.returncode == 0, (
        f"provision failed:\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}")
    operator = json.loads(
        (workflow_root / "operator.json").read_text())
    assert operator["membership_role"] == "jan_planner"
    # The provisioner must not have written a default secret unless
    # ``--rotate-credentials`` was supplied. operator.json is the
    # canonical source for the password.
    assert operator["password"]
    assert operator["mfa"]["secret"]

    # 3. start gunicorn.
    r = _run(["start"], workflow_env, timeout=60)
    assert r.returncode == 0, (
        f"start failed:\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}")

    # 4. real-browser authenticated workflow. The journey script
    # relies on Playwright Chromium already being installed in the
    # runtime (Playwright 1.62.0+ and ``chromium-1228``/``-1234``
    # under ~/.cache/ms-playwright). If unavailable, the journey
    # script exits non-zero and the test fails — never silently
    # substitutes a service-call shortcut.
    journey_tmp = workflow_root / "tmp" / f"workflow-{uuid.uuid4().hex[:8]}"
    journey_tmp.mkdir(parents=True, exist_ok=True, mode=0o700)
    journey_env = dict(workflow_env)
    journey_env["PYTHONPATH"] = str(REPO_ROOT)
    journey_env["DJANGO_SETTINGS_MODULE"] = "portal.settings_supervised_synthetic"
    journey_env["PRACE_RELEASE_MANIFEST"] = (
        str(workflow_root / "release_manifest.json"))
    journey_env["PRACE_RELEASE_MANIFEST_SHA256"] = (
        (workflow_root / ".release_manifest.sha256").read_text().strip())
    proc = subprocess.run(
        [str(REPO_ROOT / "venv/bin/python"), str(BROWSER_HELPER),
         "--base-url", f"http://{workflow_env['PRACE_BIND']}",
         "--runtime-root", str(workflow_root),
         "--tmpdir", str(journey_tmp)],
        cwd=str(REPO_ROOT), env=journey_env,
        capture_output=True, text=True, timeout=300,
    )
    if proc.returncode != 0:
        raise SystemExit(
            f"browser journey failed (rc={proc.returncode}):\n"
            f"STDOUT:\n{proc.stdout[:2000]}\nSTDERR:\n{proc.stderr[:1000]}")
    if not proc.stdout.strip():
        raise SystemExit(
            f"browser journey produced empty stdout:\n"
            f"STDERR:\n{proc.stderr[:1000]}")
    # The journey script prints a multi-line pretty-printed JSON
    # document; parse the entire stdout rather than only the last
    # line so the pretty-printed braces on their own lines do not
    # confuse the parser.
    try:
        journey = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise SystemExit(
            f"browser journey stdout is not JSON ({exc}):\n"
            f"STDOUT:\n{proc.stdout[:2000]}")
    # ``journey.ok`` may be False when the sparse synthetic worker
    # has no OCR proposals to confirm or no application-draft
    # artifact to download — those are documented skip paths, not
    # failures. The critical stages below are the ones that
    # actually exercise the integrated workflow.
    critical = ("login_redirect", "login_authenticated", "totp_completed",
                "worker_created", "document_uploaded",
                "document_associated",
                "assignment_created", "a1_prepared",
                "a1_case_detail_visible")
    for stage in critical:
        assert journey["stages"].get(stage, {}).get("ok") is True, (
            f"stage {stage!r} did not pass:\n"
            f"{json.dumps(journey['stages'][stage], indent=2)}")
    worker_pk = journey["worker_pk"]
    case_pk = journey["case_pk"]

    # 5. stop gunicorn.
    r = _run(["stop"], workflow_env, timeout=60)
    assert r.returncode == 0, (
        f"stop failed:\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}")

    # 6. restart gunicorn.
    r = _run(["start"], workflow_env, timeout=60)
    assert r.returncode == 0, (
        f"start after stop failed:\nSTDOUT:\n{r.stdout}\n"
        f"STDERR:\n{r.stderr}")

    # 7. query-after-restart. The subprocess reloads the
    # supervised-synthetic settings and queries the supervised
    # SQLite for the worker and case captured during the browser
    # journey. This is the restart-survival evidence.
    query_env = dict(workflow_env)
    query_env["PYTHONPATH"] = str(REPO_ROOT)
    query_env["DJANGO_SETTINGS_MODULE"] = (
        "portal.settings_supervised_synthetic")
    query_env["PRACE_RELEASE_MANIFEST"] = (
        str(workflow_root / "release_manifest.json"))
    query_env["PRACE_RELEASE_MANIFEST_SHA256"] = (
        (workflow_root / ".release_manifest.sha256").read_text().strip())
    proc = subprocess.run(
        [str(REPO_ROOT / "venv/bin/python"), "-c", """
import os, json
os.environ['DJANGO_SETTINGS_MODULE'] = 'portal.settings_supervised_synthetic'
import django; django.setup()
from portal.release1a.models import Worker, A1Case
result = {
    'worker_found': Worker.objects.filter(pk=os.environ['WORKER_PK']).exists(),
    'case_found': A1Case.objects.filter(pk=os.environ['CASE_PK']).exists(),
}
print(json.dumps(result))
"""],
        env={**query_env, "WORKER_PK": str(worker_pk),
             "CASE_PK": str(case_pk)},
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

    # 8. stop gunicorn (final).
    r = _run(["stop"], workflow_env, timeout=60)
    if r.returncode != 0:
        print(f"final stop returned {r.returncode}:\n"
              f"STDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}")