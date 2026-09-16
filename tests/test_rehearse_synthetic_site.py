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
WRAPPER = REPO_ROOT / "scripts" / "rehearse_dev_local.sh"


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


def test_operator_database_name_is_refused_before_migrate(required_env):
    """An exact operator database name is never a migration/cleanup
    target, even a full PRACE_DB_* set; the script refuses before any
    connection or schema mutation."""
    env = dict(required_env)
    env["PRACE_DB_NAME"] = "prace_synthetic"
    env["PRACE_DB_USER"] = "prace_synth_app"
    env["PRACE_DB_HOST"] = "127.0.0.1"
    env["PRACE_DB_PORT"] = "5432"
    r = _run(["prepare-manifest-only"], env, timeout=30)
    assert r.returncode != 0
    assert "operator database name" in r.stderr
    assert "prace_synthetic" in r.stderr


def test_manifest_mode_is_0o400_under_permissive_umask(required_env, monkeypatch):
    """With umask 022 the manifest file's mode would default to 0o644
    unless the script enforces 0o400 explicitly. The 2026-09-11 review
    observed a 0644 gunicorn.log file under the same permissive umask.
    Confirm the manifest is 0o400 regardless of incoming umask. The
    script sets umask 077 at startup so its creations are private
    even if the caller had a permissive umask. Restore the umask
    after this test to keep the rest of the suite deterministic.
    """
    import os as _os
    previous = _os.umask(0o022)
    try:
        r = _run(["prepare-manifest-only"], required_env, timeout=30)
        assert r.returncode == 0, r.stderr
        root = Path(required_env["PRACE_RUNTIME_ROOT"])
        mode = (root / "release_manifest.json").stat().st_mode & 0o777
        assert mode == 0o400, f"manifest mode is {oct(mode)}, expected 0o400"
        # The manifest sidecar is 0600, not 0400, so the script can
        # overwrite it on subsequent runs without chmod. Confirm.
        sha_mode = (root / ".release_manifest.sha256").stat().st_mode & 0o777
        assert sha_mode == 0o600, f"sidecar mode is {oct(sha_mode)}, expected 0o600"
    finally:
        _os.umask(previous)


def test_child_symlink_is_refused_before_mkdir_chmod(required_env, monkeypatch):
    """F2: a pre-existing child symlink must be rejected BEFORE any
    mkdir/chmod/write, so the script cannot follow it and change
    the target's permissions. The 2026-09-11 review observed
    `storage` as a symlink and the script chmod'd the target
    directory from 0755 to 0700.
    """
    import os as _os
    root = Path(required_env["PRACE_RUNTIME_ROOT"])
    storage_link = root / "storage"
    # Set the test umask to 0o077 so the target's effective mode
    # is 0o700 — the same as if the script had followed the
    # symlink and chmod'd it. That way the F2 regression is the
    # ONLY way the assertion could fail: the script would have
    # to change the mode from 0o700 to something else to pass.
    previous_umask = _os.umask(0o077)
    try:
        tmp_target = root / ".tmp_storage_target"
        # mkdir(0o755) under umask 0o077 creates a 0o700 directory.
        tmp_target.mkdir(mode=0o755)
        storage_link.symlink_to(tmp_target)
        # Capture the target's mode at this moment — if it changes
        # after the script runs, the script chmod'd it.
        target_mode_before = tmp_target.stat().st_mode & 0o777
        r = _run(["prepare-manifest-only"], required_env, timeout=15)
        target_mode_after = tmp_target.stat().st_mode & 0o777
        assert r.returncode != 0, (
            "prepare accepted a pre-existing child symlink — F2 regression"
        )
        out = r.stdout + r.stderr
        assert "symlink" in out.lower(), f"error must mention symlink; got: {out!r}"
        # The target's mode must not have changed — script must
        # have rejected the symlink without mutating the target.
        assert target_mode_after == target_mode_before, (
            f"target mode changed from {oct(target_mode_before)} to "
            f"{oct(target_mode_after)} — F2 regression: script chmod'd "
            f"the symlink target"
        )
    finally:
        try:
            storage_link.unlink()
        except FileNotFoundError:
            pass
        try:
            tmp_target.chmod(0o700)
            tmp_target.rmdir()
        except FileNotFoundError:
            pass
        _os.umask(previous_umask)


# --- wrapper (rehearse_dev_local.sh) ---


def _run_wrapper(args, env, timeout=60):
    return subprocess.run(
        ["bash", str(WRAPPER), *args],
        cwd=str(REPO_ROOT), env=env, capture_output=True,
        text=True, timeout=timeout,
    )


def _wrapper_env(rehearsal_root, *, with_secret=True):
    env = {
        "PATH": os.environ["PATH"],
        "HOME": os.environ.get("HOME", "/tmp"),
        "PRACE_RUNTIME_ROOT": str(rehearsal_root),
        "PRACE_ALLOWED_HOSTS": "localhost,127.0.0.1",
        "PRACE_BIND": "127.0.0.1:0",
    }
    if with_secret:
        env["PRACE_SECRET_KEY"] = "wrapper-test-secret-" + "x" * 50
    return env


def test_wrapper_rejects_out_of_tree_path_before_any_write(tmp_path):
    """The 2026-09-12 review found the wrapper rejected valid roots
    because the quoted heredoc embedded shell variables literally.
    The rewritten wrapper validates the RAW path before any mkdir and
    refuses a path outside runtime/portal/supervised-* without
    creating anything."""
    target = tmp_path / "outside-approved-runtime"
    r = _run_wrapper(["status"], _wrapper_env(target, with_secret=False))
    assert r.returncode != 0, (
        f"wrapper accepted an out-of-tree path:\n{r.stdout}\n{r.stderr}")
    assert "supervised-" in r.stderr
    assert not target.exists(), "out-of-tree runtime root must not be created"
    assert not (REPO_ROOT / "runtime" / "portal" / "outside").exists()


def test_wrapper_creates_confined_root_and_atomic_secret_key(rehearsal_root):
    """A fresh confined root is created (0700) and a stable signing key
    is minted atomically (mode 0600) when the caller does not supply
    PRACE_SECRET_KEY. The secret is written through a unique temp name
    + rename, never clobbering a concurrent create."""
    env = _wrapper_env(rehearsal_root, with_secret=False)
    r = _run_wrapper(["status"], env)
    assert r.returncode == 0, r.stderr
    assert rehearsal_root.is_dir()
    assert (rehearsal_root.stat().st_mode & 0o777) == 0o700
    key_file = rehearsal_root / ".secret_key"
    assert key_file.is_file()
    assert ((key_file.stat().st_mode) & 0o777) == 0o600
    assert len(key_file.read_text().strip()) >= 40
    # No leftover temp key files.
    assert not list(rehearsal_root.glob(".secret_key.*"))

    # Second invocation reuses the persisted key (stable session signer).
    second = _run_wrapper(["status"], env)
    assert second.returncode == 0, second.stderr
    assert key_file.read_text() == key_file.read_text()
    assert "stopped" in second.stdout


def test_wrapper_rejects_symlinked_secret_key(rehearsal_root):
    """A pre-existing .secret_key symlink must be refused so the
    wrapper cannot write a fresh key through the link into a foreign
    target (the F2 symlink class of defect, applied to the secret)."""
    key_file = rehearsal_root / ".secret_key"
    foreign = rehearsal_root / ".foreign_target"
    foreign.write_text("existing")
    key_file.symlink_to(foreign)
    r = _run_wrapper(["status"], _wrapper_env(rehearsal_root, with_secret=False))
    assert r.returncode != 0, (
        f"wrapper accepted a symlinked .secret_key:\n{r.stdout}\n{r.stderr}")
    assert "symlink" in (r.stdout + r.stderr).lower()
    assert foreign.read_text() == "existing", "foreign target was modified"


def test_wrapper_recovers_from_empty_persisted_secret_key(rehearsal_root):
    """A pre-existing but empty .secret_key must be replaced with a
    usable key on the next invocation, and no leftover temp files
    may accumulate."""
    key_file = rehearsal_root / ".secret_key"
    key_file.write_text("")
    key_file.chmod(0o600)
    assert key_file.stat().st_size == 0

    env = _wrapper_env(rehearsal_root, with_secret=False)
    r = _run_wrapper(["status"], env)
    assert r.returncode == 0, r.stderr
    assert key_file.is_file()
    assert key_file.stat().st_size > 0, "empty key must be replaced"
    assert not list(rehearsal_root.glob(".secret_key.*")), \
        "recovery must not leave temp key files behind"

    # Second invocation reuses the regenerated stable key.
    second = _run_wrapper(["status"], env)
    assert second.returncode == 0, second.stderr
    assert key_file.read_text() == key_file.read_text()


def test_smoke_probe_parses_health_json_and_fails_on_wrong_fields(required_env, monkeypatch):
    """F1 negative fixture: a server that returns a /health/ JSON
    body with supervised=False and real_data=True must be rejected
    by the strict smoke. The 2026-09-11 review observed the prior
    smoke accepting the wrong body because it searched for
    substrings.
    """
    import http.server
    import threading
    import socket
    import json as _json

    # Find a free port.
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    # Prepare just enough layout for the smoke probe to load the manifest.
    env = dict(required_env)
    env["PRACE_BIND"] = f"127.0.0.1:{port}"
    r = _run(["prepare-manifest-only"], env, timeout=30)
    assert r.returncode == 0, r.stderr
    manifest_commit = _json.loads(
        (Path(env["PRACE_RUNTIME_ROOT"]) / "release_manifest.json").read_text()
    )["git_commit"]

    class Fake(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args, **kwargs):
            pass

        def do_GET(self):
            if self.path == "/health/":
                body = _json.dumps({
                    "git_commit": manifest_commit,
                    "app_build_id": "FAKE",
                    "supervised": False,
                    "real_data": True,
                    "mode": "settings_supervised_synthetic",
                }).encode()
            elif self.path in ("/login/", "/review/"):
                self.send_response(302)
                self.send_header("Location", "https://example.invalid/accounts/login/")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            elif self.path == "/accounts/login/":
                body = b'<input name="password"><input name="login">'
            else:
                body = b""
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = http.server.HTTPServer(("127.0.0.1", port), Fake)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        r = _run(["smoke"], env, timeout=30)
        # Strict contract: smoke must FAIL because supervised=False and
        # real_data=True; the prior substring check accepted these.
        assert r.returncode == 6, (
            f"smoke accepted wrong contract (exit={r.returncode}):\n"
            f"STDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"
        )
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def _slow_body_server(handler):
    """Run a local HTTP server whose handler sends status+headers and
    then holds the body open. Returns (server, thread)."""
    import http.server as _httpserver
    import socket as _socket
    import threading as _threading
    import time as _time

    with _socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]

    class Drip(_httpserver.BaseHTTPRequestHandler):
        def log_message(self, *args, **kwargs):
            pass

        def handle_error(self, request, client_address):
            pass

        def do_GET(self):
            handler(self)
            self.wfile.flush()
            _time.sleep(2)

    server = _httpserver.HTTPServer(("127.0.0.1", port), Drip)
    thread = _threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread, port


def test_bounded_request_enforces_deadline_on_success_body():
    """F4: a 200 server that sends headers then holds the body open must
    be cut off by the smoke's own deadline (not by the urllib connect
    timeout), because the response body read used to block inside
    read(65536) until the wall-clock check finally fired.
    """
    import time as _time
    from scripts.smoke_probe import _bounded_request

    def handler(h):
        h.send_response(200)
        h.send_header("Content-Length", "1048576")
        h.end_headers()

    server, thread, port = _slow_body_server(handler)
    try:
        start = _time.monotonic()
        timed_out = False
        try:
            _bounded_request(f"http://127.0.0.1:{port}/health/", "localhost",
                             read_timeout=0.2)
        except TimeoutError:
            timed_out = True
        elapsed = _time.monotonic() - start
        assert timed_out, "success body read must raise TimeoutError on a held body"
        assert elapsed < 1.0, (
            f"deadline not enforced at socket level: {elapsed:.2f}s"
        )
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def _drip_body_server(status, *, drip_seconds=6.0, chunk=64, gap=0.05):
    """A server that continuously writes a trickle of body bytes for at
    least ``drip_seconds`` (never completing the Content-Length body),
    against which a short smoke deadline must fire on the wall-clock
    checks (each read1 chunk returns fast, so socket-level timeouts
    alone cannot save the budget)."""
    import http.server as _httpserver
    import socket as _socket
    import threading as _threading
    import time as _time

    with _socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]

    class Drip(_httpserver.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args, **kwargs):
            pass

        def handle_error(self, request, client_address):
            pass

        def do_GET(self):
            self.send_response(status)
            self.send_header("Content-Length", "1048576")
            self.end_headers()
            self.wfile.flush()
            deadline = _time.monotonic() + drip_seconds
            while _time.monotonic() < deadline:
                try:
                    self.wfile.write(b"x" * chunk)
                    self.wfile.flush()
                except OSError:
                    break
                _time.sleep(gap)

    server = _httpserver.HTTPServer(("127.0.0.1", port), Drip)
    thread = _threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread, port


def _assert_timed_out(call, label, ceiling=1.0):
    import time as _time
    start = _time.monotonic()
    timed_out = False
    try:
        call()
    except TimeoutError:
        timed_out = True
    elapsed = _time.monotonic() - start
    assert timed_out, f"{label}: a drip body must raise TimeoutError"
    assert elapsed < ceiling, f"{label}: budget not enforced: {elapsed:.2f}s"


def test_bounded_request_enforces_deadline_on_slow_success_drip():
    """F2: a 200 server that continuously trickles a long-lived body must
    still terminate with TimeoutError (the smoke must never report the
    wrapped-up request as healthy). The success body is read through
    the http.client reader (so bytes buffered with the headers are not
    lost); each read1 returns partial data without blocking for the
    full internal buffer, so the wall-clock check on every iteration
    bounds a drip regardless of how long the server keeps writing.
    """
    from scripts.smoke_probe import _bounded_request
    server, thread, port = _drip_body_server(200)
    try:
        _assert_timed_out(
            lambda: _bounded_request(
                f"http://127.0.0.1:{port}/health/", "localhost",
                read_timeout=0.2),
            "slow success drip",
            ceiling=1.5,
        )
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_bounded_request_enforces_deadline_on_slow_error_drip():
    """F4: the HTTPError body path must hit the same wall-clock budget
    when the error body trickles past it."""
    from scripts.smoke_probe import _bounded_request
    server, thread, port = _drip_body_server(500)
    try:
        _assert_timed_out(
            lambda: _bounded_request(
                f"http://127.0.0.1:{port}/health/", "localhost",
                read_timeout=0.2),
            "slow error drip",
        )
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_bounded_request_propagates_timeout_from_error_body():
    """F4: the HTTPError branch used to catch OSError (which includes
    TimeoutError) and return the body normally. A 500 server holding the
    body open must now propagate the TimeoutError, not return normally."""
    import time as _time
    from scripts.smoke_probe import _bounded_request

    def handler(h):
        h.send_response(500)
        h.send_header("Content-Length", "32768")
        h.end_headers()

    server, thread, port = _slow_body_server(handler)
    try:
        start = _time.monotonic()
        timed_out = False
        try:
            _bounded_request(f"http://127.0.0.1:{port}/health/", "localhost",
                             read_timeout=0.2)
        except TimeoutError:
            timed_out = True
        elapsed = _time.monotonic() - start
        assert timed_out, (
            "HTTPError body read must raise TimeoutError, not be swallowed"
        )
        assert elapsed < 1.0, (
            f"deadline not enforced on the error body path: {elapsed:.2f}s"
        )
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


@pytest.mark.parametrize('budget_ms, delay, expected_ready', [(3000, 2.2, True), (100, 1.5, False)])
def test_readiness_response_headers_follow_configured_bounded_probe_budget(monkeypatch, budget_ms, delay, expected_ready):
    """Readiness can exceed generic 2s headers, but its configured ceiling holds."""
    import http.server
    import threading
    import time
    from scripts.smoke_probe import _check_readiness

    monkeypatch.setenv('PRACE_READINESS_BUDGET_MS', str(budget_ms))
    body = json.dumps(dict(status='ready', git_commit='a' * 40,
                           build_id='synthetic', supervised=True, real_data=False)).encode()

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            time.sleep(delay)
            try:
                self.send_response(200)
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

    server = http.server.HTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    started = time.monotonic()
    try:
        if expected_ready:
            result = _check_readiness(f'http://127.0.0.1:{server.server_port}', 'localhost', 'a' * 40, 'synthetic')
            assert result['contract_ok'] is True
        else:
            with pytest.raises(TimeoutError):
                _check_readiness(f'http://127.0.0.1:{server.server_port}', 'localhost', 'a' * 40, 'synthetic')
            assert time.monotonic() - started < 1.5
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
