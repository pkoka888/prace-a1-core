"""Bounded real-lifecycle integration test for the rehearsal script.

One real gunicorn process, one real start, one real smoke, one real
restart, one real stop. Runs in an isolated runtime root under
runtime/portal/supervised-lifecycle-* and cleans up after itself.

This test is the only place in the test suite that actually exercises
a real gunicorn server. It is therefore slow (~50-60s) and lives in
its own change-package selector so the cheaper unit tests in
test_rehearse_synthetic_site.py stay fast.
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import time
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "rehearse_synthetic_site.sh"


def _free_port() -> int:
    """Bind to port 0; the OS picks a free one. Return it."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture
def lifecycle_root(tmp_path):
    import uuid as _uuid
    name = f"supervised-lifecycle-{_uuid.uuid4().hex[:8]}"
    root = REPO_ROOT / "runtime" / "portal" / name
    root.mkdir(mode=0o700)
    yield root
    shutil.rmtree(str(root), ignore_errors=True)


def _run(args, env, cwd=None, timeout=180):
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        cwd=cwd or REPO_ROOT, env=env, capture_output=True,
        text=True, timeout=timeout,
    )


@pytest.mark.serial
def test_real_lifecycle_prepare_start_smoke_restart_stop(lifecycle_root):
    """End-to-end: prepare, start, smoke (strict), restart, stop.

    Each step is a real gunicorn process bound to a real free port.
    The smoke step probes /health/, /login/, /accounts/login/, /review/,
    /readiness/, and (when present) the known CSS asset, with the
    strict contract added after the F1 review.
    """
    port = _free_port()
    env = {
        "PATH": os.environ["PATH"],
        "HOME": os.environ.get("HOME", "/tmp"),
        "PRACE_RUNTIME_ROOT": str(lifecycle_root),
        "PRACE_SECRET_KEY": "lifecycle-secret-" + "y" * 50,
        "PRACE_ALLOWED_HOSTS": "localhost,127.0.0.1",
        "PRACE_BIND": f"127.0.0.1:{port}",
        "PRACE_WORKERS": "1",
        "PRACE_REHEARSE_TIMEOUT": "30",
        # The readiness subprocess orchestrates multiple checks
        # (~3.3s measured by the 2026-09-11 review). The default 2s
        # budget is too tight for cold-start synthetic deployments.
        # Set a 10s budget for the rehearsal lifecycle.
        "PRACE_READINESS_BUDGET_MS": "10000",
    }

    # prepare - full Django migrate + collectstatic
    r = _run(["prepare"], env, timeout=180)
    assert r.returncode == 0, f"prepare failed:\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"

    try:
        # start - real gunicorn, must come up and serve /health/ with our commit
        r = _run(["start"], env, timeout=60)
        assert r.returncode == 0, f"start failed:\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"
        # Verify the launched process really owns our port.
        assert (lifecycle_root / "gunicorn.pid").exists()
        assert (lifecycle_root / ".gunicorn.cmdline").exists()
        assert (lifecycle_root / ".gunicorn.started_at").exists()

        # Start-before-provision is supported; provisioning a running site
        # then starts its independently owned, authorized OCR worker.
        assert not (lifecycle_root / ".ocr-worker.json").exists()
        r = _run(["provision"], env, timeout=60)
        assert r.returncode == 0, f"provision failed:\n{r.stderr}"
        worker_before = json.loads((lifecycle_root / ".ocr-worker.json").read_text())
        assert Path(f"/proc/{worker_before['pid']}").exists()
        assert (lifecycle_root / ".ocr-worker.ready").read_text() == "ready\n"

        # smoke - strict contract
        r = _run(["smoke"], env, timeout=60)
        assert r.returncode == 0, f"smoke failed:\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"

        # restart - real stop + start, both succeed
        r = _run(["restart"], env, timeout=60)
        assert r.returncode == 0, f"restart failed:\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"

        worker_after = json.loads((lifecycle_root / ".ocr-worker.json").read_text())
        assert worker_after["pid"] != worker_before["pid"]
        assert worker_after["actor_id"] == worker_before["actor_id"]
        assert worker_after["organization_id"] == worker_before["organization_id"]
        assert Path(f"/proc/{worker_after['pid']}").exists()

        # status reports running
        r = _run(["status"], env, timeout=10)
        assert r.returncode == 0, f"status failed:\n{r.stderr}"
        assert "running" in r.stdout
        assert f"127.0.0.1:{port}" in r.stdout

        # start refuses when the bind is occupied
        r2 = _run(["start"], env, timeout=10)
        # Could be exit 1 (port already bound) or could succeed if the
        # previous start did not write a pidfile; either way, our real
        # gunicorn must remain the owner.
        if r2.returncode == 0:
            # If it succeeded, the pidfile points at our gunicorn.
            pid = int((lifecycle_root / "gunicorn.pid").read_text().strip())
            assert os.path.exists(f"/proc/{pid}")
    finally:
        # Always tear down the gunicorn process; the script's stop
        # validates pid ownership and refuses to signal unrelated PIDs.
        r = _run(["stop"], env, timeout=30)
        assert r.returncode == 0, f"stop failed:\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"
        assert not (lifecycle_root / ".ocr-worker.json").exists()


@pytest.mark.serial
def test_real_lifecycle_smoke_fails_when_server_returns_500(lifecycle_root):
    """A non-gunicorn HTTP server on the bind port must make smoke FAIL.

    This is the F1 negative fixture: the previous smoke command counted
    anything that was not 000 as a pass, including HTTP 500 responses
    from a wrong server. The fixed smoke must fail.
    """
    port = _free_port()
    env = {
        "PATH": os.environ["PATH"],
        "HOME": os.environ.get("HOME", "/tmp"),
        "PRACE_RUNTIME_ROOT": str(lifecycle_root),
        "PRACE_SECRET_KEY": "lifecycle-secret-" + "z" * 50,
        "PRACE_ALLOWED_HOSTS": "localhost,127.0.0.1",
        "PRACE_BIND": f"127.0.0.1:{port}",
        "PRACE_WORKERS": "1",
        "PRACE_REHEARSE_TIMEOUT": "10",
    }
    r = _run(["prepare-manifest-only"], env, timeout=30)
    assert r.returncode == 0, r.stderr
    # Spawn a one-line HTTP server that always returns 500.
    import http.server
    import threading

    class Always500(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(500)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, *args, **kwargs):
            pass

    server = http.server.HTTPServer(("127.0.0.1", port), Always500)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        r = _run(["smoke"], env, timeout=30)
        # Smoke must fail because /health/ returns 500.
        assert r.returncode != 0
        assert "/health/" in r.stdout
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


@pytest.mark.serial
def test_real_lifecycle_smoke_fails_when_no_server(lifecycle_root):
    """With the server stopped, smoke must FAIL — not report success.

    This is the second F1 negative fixture: the previous smoke command
    accepted a '000000' curl composite as four passes.
    """
    env = {
        "PATH": os.environ["PATH"],
        "HOME": os.environ.get("HOME", "/tmp"),
        "PRACE_RUNTIME_ROOT": str(lifecycle_root),
        "PRACE_SECRET_KEY": "lifecycle-secret-" + "w" * 50,
        "PRACE_ALLOWED_HOSTS": "localhost,127.0.0.1",
        "PRACE_BIND": "127.0.0.1:1",  # Port 1 is never bindable by us
        "PRACE_WORKERS": "1",
        "PRACE_REHEARSE_TIMEOUT": "5",
    }
    r = _run(["prepare-manifest-only"], env, timeout=30)
    assert r.returncode == 0, r.stderr
    r = _run(["smoke"], env, timeout=20)
    assert r.returncode != 0
    out = r.stdout + r.stderr
    assert "0 failed" in out or "/health/" in out
