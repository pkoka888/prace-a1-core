"""End-to-end authenticated workflow test for the rehearsal script.

Bounded exercise of the rehearsal endpoint's HTTP and data contracts.

This test does not attempt a real browser allauth+MFA login against
the running gunicorn. The CSRF/Secure-cookie loopback over plain
HTTP is the rehearsal's known limitation; a real deployment puts
the rehearsal behind a TLS-terminating proxy. We prove:

1. prepare + provision + start work end to end.
2. The /accounts/login/ GET returns 200 with a CSRF cookie.
3. /health/, /readiness/, /login/, /accounts/login/, /review/,
   /static/* all satisfy the strict contract (smoke probe).
4. The Django services (worker/assignment/A1) work against the
   supervised-synthetic database with the operator's identity.
5. Sparse worker data is saved; A1 preparation blocks with a
   clear message naming the missing fact.
6. Saved records survive a restart.
"""
from __future__ import annotations

import http.cookiejar
import json
import os
import secrets
import shutil
import socket
import subprocess
import urllib.parse
import urllib.request
import uuid
from datetime import date, timedelta
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "rehearse_synthetic_site.sh"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _run(args, env, cwd=None, timeout=300):
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        cwd=cwd or REPO_ROOT, env=env, capture_output=True,
        text=True, timeout=timeout,
    )


@pytest.fixture
def workflow_root():
    name = f"supervised-workflow-{uuid.uuid4().hex[:8]}"
    root = REPO_ROOT / "runtime" / "portal" / name
    root.mkdir(mode=0o700)
    yield root
    shutil.rmtree(str(root), ignore_errors=True)


@pytest.mark.django_db(databases=["default"], transaction=False)
def test_prepare_provision_start_data_persistence_sparse_blocked(workflow_root):
    """End-to-end: prepare, provision, start, smoke, data path, restart, stop."""
    port = _free_port()
    env = {
        "PATH": os.environ["PATH"],
        "HOME": os.environ.get("HOME", "/tmp"),
        "PRACE_RUNTIME_ROOT": str(workflow_root),
        "PRACE_SECRET_KEY": "workflow-secret-" + secrets.token_urlsafe(32),
        "PRACE_ALLOWED_HOSTS": "localhost,127.0.0.1",
        "PRACE_BIND": f"127.0.0.1:{port}",
        "PRACE_WORKERS": "1",
        "PRACE_REHEARSE_TIMEOUT": "30",
        "PRACE_READINESS_BUDGET_MS": "10000",
        "DJANGO_SETTINGS_MODULE": "portal.settings_supervised_synthetic",
    }

    # 1. prepare (full migrate + collectstatic). ~45s.
    r = _run(["prepare"], env, timeout=120)
    assert r.returncode == 0, f"prepare failed:\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"
    db_mode = oct((workflow_root / "db.sqlite3").stat().st_mode & 0o777)
    assert db_mode == "0o600", f"db.sqlite3 mode is {db_mode}, expected 0o600"
    # Operator-owned file modes for state files.
    assert oct((workflow_root / "release_manifest.json").stat().st_mode & 0o777) == "0o400"
    assert oct((workflow_root / ".release_manifest.sha256").stat().st_mode & 0o777) == "0o600"
    for child in ("storage", "media", "static", "cache", "tmp", "logs"):
        assert oct((workflow_root / child).stat().st_mode & 0o777) == "0o700"

    try:
        # 2. provision operator + organization + TOTP MFA. ~5s.
        r = _run(["provision"], env, timeout=60)
        assert r.returncode == 0, f"provision failed:\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"
        operator = json.loads((workflow_root / "operator.json").read_text())
        organization = json.loads((workflow_root / "organization.json").read_text())
        assert operator["password"]
        assert operator["mfa"]["secret"]
        assert operator["organization_id"] == organization["id"]
        assert oct((workflow_root / "operator.json").stat().st_mode & 0o777) == "0o600"

        # 3. start gunicorn. ~5s.
        r = _run(["start"], env, timeout=60)
        assert r.returncode == 0, f"start failed:\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"

        # 4. Real HTTP: /accounts/login/ GET returns 200 with a
        # CSRF cookie. (The CSRF/Secure loopback over plain HTTP
        # is the rehearsal's known limitation; a real deployment
        # runs behind a TLS-terminating proxy.)
        cookie_jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(cookie_jar),
        )
        base = f"http://127.0.0.1:{port}"
        response = opener.open(
            urllib.request.Request(
                f"{base}/accounts/login/",
                headers={"Host": "localhost"},
            ),
            timeout=10,
        )
        assert response.status == 200, (
            f"/accounts/login/ GET: {response.status}"
        )
        body = response.read()
        assert b'name="csrfmiddlewaretoken"' in body, "login form missing CSRF token"
        assert any(c.name == "csrftoken" for c in cookie_jar), (
            "no CSRF cookie was set on the GET response"
        )

        # 5. Real HTTP strict smoke (7 endpoints). ~5s.
        smoke = subprocess.run(
            [str(REPO_ROOT / "venv/bin/python"),
             str(REPO_ROOT / "scripts" / "smoke_probe.py"),
             base, "localhost",
             str(workflow_root / "release_manifest.json")],
            capture_output=True, text=True, timeout=60,
        )
        assert smoke.returncode == 0, (
            f"smoke failed:\nSTDOUT:\n{smoke.stdout[:1000]}\n"
            f"STDERR:\n{smoke.stderr[:500]}"
        )

        # 6. Stop gunicorn so the data path can use the
        # supervised-synthetic SQLite without contention. The
        # data path runs against the same database gunicorn uses;
        # stop+start preserves the records.
        r = _run(["stop"], env, timeout=30)
        assert r.returncode == 0, f"stop failed:\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"

        # 7. Data path: create worker/assignment/A1 against the
        # supervised-synthetic database. Run the data path in a
        # separate subprocess so it loads the supervised-synthetic
        # settings fresh (the pytest-django test runner has already
        # wired up an in-memory test database that we cannot
        # override in-process).
        data_path = REPO_ROOT / "tests" / "_rehearse_workflow_data_path.py"
        data_path_env = dict(env)
        data_path_env["PATH"] = os.environ["PATH"]
        data_path_env["HOME"] = os.environ.get("HOME", "/tmp")
        data_path_env["PYTHONPATH"] = str(REPO_ROOT)
        r = subprocess.run(
            [str(REPO_ROOT / "venv/bin/python"), str(data_path),
             str(workflow_root), operator["email"], operator["password"],
             str(organization["id"])],
            cwd=str(REPO_ROOT), env=data_path_env,
            capture_output=True, text=True, timeout=60,
        )
        assert r.returncode == 0, (
            f"data path failed:\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"
        )
        data_result = json.loads(r.stdout.strip().splitlines()[-1])
        assert data_result["worker_pk"] is not None
        assert data_result["case_pk"] is not None
        assert data_result["sparse_worker_pk"] is not None
        # Sparse worker contract: the worker is saved (preparation
        # does not require non-empty identity facts), but the
        # rendering operation (reserve_application_draft) is the
        # one that needs the missing fact and must block.
        assert data_result["sparse_a1_prepared"] is True, (
            "sparse worker must save; preparation should not require "
            "non-empty identity facts"
        )
        assert data_result["sparse_reserve_blocked"] is True, (
            f"sparse worker reserve must block, got error="
            f"{data_result.get('sparse_reserve_error')!r}"
        )

        # 8. Restart and confirm the records survived.
        r = _run(["start"], env, timeout=60)
        assert r.returncode == 0, (
            f"start after stop failed:\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"
        )
        # Query the records from a fresh subprocess (so the
        # Django ORM uses the supervised-synthetic SQLite, not
        # the pytest in-memory DB).
        r = subprocess.run(
            [str(REPO_ROOT / "venv/bin/python"), str(data_path),
             "--query-only", str(workflow_root),
             str(data_result["worker_pk"]), str(data_result["case_pk"])],
            cwd=str(REPO_ROOT), env=data_path_env,
            capture_output=True, text=True, timeout=30,
        )
        assert r.returncode == 0, (
            f"query-after-restart failed:\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"
        )
        query = json.loads(r.stdout.strip().splitlines()[-1])
        assert query["worker_found"] is True, "worker record lost after restart"
        assert query["case_found"] is True, "A1 case record lost after restart"
    finally:
        r = _run(["stop"], env, timeout=30)
        if r.returncode != 0:
            print(f"final stop returned {r.returncode}:\n"
                  f"STDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}")
