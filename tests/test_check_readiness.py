"""Synthetic source/process/HTTP controls; never access host credentials or DB."""
import json
from http.client import BadStatusLine, IncompleteRead
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import subprocess
import threading

import pytest

from scripts import validate_delivery_readiness as readiness


@pytest.fixture
def source_tree(tmp_path):
    for name in readiness.SCAN_PATHS:
        path = tmp_path / name
        if name == "tests/document_web":
            path.mkdir(parents=True)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# synthetic source\n")
    return tmp_path


@pytest.mark.parametrize("source", [
    "page.goto(url, wait_until='networkidle')",
    'page.goto(url, wait_until="networkidle")',
    "page.wait_for_load_state(\n 'networkidle')",
    "await page.waitForLoadState('networkidle')",
    'await page.goto(url, {waitUntil: "networkidle"})',
])
def test_real_scan_catches_python_js_and_multiline(source_tree, source):
    (source_tree / "scripts/playwright_smoke.py").write_text(source)
    assert readiness.scan_browser_waits(source_tree)["status"] == "failed"


def test_clean_source_and_missing_path_have_distinct_outcomes(source_tree):
    assert readiness.scan_browser_waits(source_tree)["status"] == "passed"
    (source_tree / "scripts/playwright_smoke.py").unlink()
    assert readiness.scan_browser_waits(source_tree)["status"] == "blocked"


def test_rg_in_operator_path_runs_with_sanitized_child_environment(source_tree, tmp_path, monkeypatch):
    tool_dir = tmp_path / "operator-bin"
    tool_dir.mkdir()
    executable = tool_dir / "rg"
    executable.write_text("#!/bin/sh\n[ -z \"$PRACE_DB_PASSWORD\" ] || exit 2\nexit 1\n")
    executable.chmod(0o700)
    monkeypatch.setenv("PATH", str(tool_dir))
    monkeypatch.setenv("PRACE_DB_PASSWORD", "SYNTHETIC_PRIVATE_CANARY")
    assert readiness.scan_browser_waits(source_tree)["status"] == "passed"
    executable.unlink()
    assert readiness.scan_browser_waits(source_tree)["status"] == "blocked"


@pytest.mark.parametrize("command_result", [(2, "", ""), (None, "", "timeout"),
                                            (None, "", "tool_unavailable"), (1, "unexpected", "")])
def test_scan_error_is_never_empty_success(source_tree, monkeypatch, command_result):
    monkeypatch.setattr(readiness, "bounded_command", lambda *a, **kw: command_result)
    assert readiness.scan_browser_waits(source_tree)["status"] == "blocked"


def test_subprocess_cannot_inherit_credentials_or_prompt(monkeypatch):
    monkeypatch.setenv("PRACE_DB_PASSWORD", "SYNTHETIC_PRIVATE_CANARY")
    def run(argv, **kwargs):
        assert argv == ["systemctl", "show"]
        assert kwargs["env"] == {"PATH": readiness.os.defpath, "LC_ALL": "C", "SYSTEMD_PAGER": ""}
        assert kwargs["stdin"] == subprocess.DEVNULL
        assert kwargs["timeout"] == 8
        assert not kwargs.get("shell")
        return subprocess.CompletedProcess(argv, 7, stdout="active", stderr="SYNTHETIC_PRIVATE_CANARY")
    monkeypatch.setattr(readiness.subprocess, "run", run)
    assert readiness.bounded_command(["systemctl", "show"]) == (7, "active", "")


def unit_output(**overrides):
    values = dict(LoadState="loaded", ActiveState="active", SubState="running", MainPID="42",
                  EnvironmentFiles=readiness.SERVICE_ENV + " (ignore_errors=no)", NeedDaemonReload="no",
                  StandardOutput="journal", StandardError="inherit")
    values.update(overrides)
    return "\n".join(f"{key}={value}" for key, value in values.items())


@pytest.mark.parametrize(("code", "output", "expected"), [
    (0, unit_output(), ["passed", "passed"]),
    (1, unit_output(), ["blocked"]),
    (0, "ActiveState=active", ["blocked"]),
    (0, unit_output(MainPID="0"), ["failed", "passed"]),
    (0, unit_output(EnvironmentFiles="/synthetic/wrong.env (ignore_errors=no)"), ["passed", "failed"]),
    (0, unit_output(NeedDaemonReload="yes"), ["passed", "failed"]),
])
def test_native_exit_effective_state_and_path_binding(monkeypatch, code, output, expected):
    monkeypatch.setattr(readiness, "bounded_command", lambda *a, **kw: (code, output, ""))
    assert [check["status"] for check in readiness.unit_checks()] == expected


@pytest.mark.parametrize("variant", ["valid", "wrong_identity", "malformed", "string_boolean",
                                    "missing_asset", "html_asset", "wrong_mime", "empty_asset"])
def test_existing_endpoint_contracts_with_real_synthetic_http(variant):
    commit, build = "a" * 40, "synthetic-build"
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            assert self.headers["Host"] == "synthetic.example.invalid"
            if self.path.startswith("/static/"):
                self.send_response(404 if variant == "missing_asset" else 200)
                js = self.path.endswith(".js")
                self.send_header("Content-Type", "text/html" if variant == "wrong_mime"
                                 else "application/javascript" if js else "text/css")
                body = b"/* htmx synthetic */" if js else b"/* tailwindcss synthetic */"
                if variant == "html_asset":
                    body = b"<!doctype html><html>login htmx tailwindcss</html>"
                elif variant == "empty_asset":
                    body = b""
            else:
                self.send_response(200)
                payload = {"git_commit": "b" * 40 if variant == "wrong_identity" else commit,
                           "build_id": build, "supervised": "true" if variant == "string_boolean" else True,
                           "real_data": False, "mode": "settings_supervised_synthetic", "status": "ready",
                           "diagnostic": "SYNTHETIC_PRIVATE_CANARY"}
                body = b"not json" if variant == "malformed" else json.dumps(payload).encode()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        checks = readiness.endpoint_checks(f"http://127.0.0.1:{server.server_port}",
                                           "synthetic.example.invalid", commit, build)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
    assert len(checks) == 4
    assert all(c["status"] == "passed" for c in checks) == (variant == "valid")
    assert "SYNTHETIC_PRIVATE_CANARY" not in json.dumps(checks)


@pytest.mark.parametrize("error", [BadStatusLine("SYNTHETIC_PRIVATE_CANARY"),
                                   IncompleteRead(b"SYNTHETIC_PRIVATE_CANARY"), TimeoutError("sentinel")])
def test_protocol_failures_are_sanitized_and_never_pass(monkeypatch, error):
    def fail(*args, **kwargs):
        raise error
    monkeypatch.setattr(readiness.smoke_probe, "_bounded_request", fail)
    checks = readiness.endpoint_checks("http://127.0.0.1", "synthetic.invalid", "a" * 40, "synthetic")
    assert all(check["status"] == "blocked" for check in checks)
    assert "SYNTHETIC_PRIVATE_CANARY" not in json.dumps(checks)


def test_default_execution_reads_no_files_and_performs_no_http_or_privileged_commands(monkeypatch, capsys):
    monkeypatch.setattr(readiness, "scan_browser_waits", lambda: readiness.result("source", "passed", "synthetic"))
    calls = []
    def command(argv, **kwargs):
        calls.append(argv)
        assert argv[0] == "systemctl"
        return 0, unit_output(), ""
    monkeypatch.setattr(readiness, "bounded_command", command)
    def forbidden(*args, **kwargs):
        pytest.fail("Unexpected credential/file/HTTP access")
    monkeypatch.setattr(Path, "open", forbidden)
    monkeypatch.setattr(readiness, "endpoint_checks", forbidden)
    assert readiness.main(["--json"]) == 2
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "blocked"
    assert report["counts"]["blocked"] == 2
    assert report["target"]["expected_commit"] is None
    assert report["target"]["origin"] == "http://127.0.0.1:8001"
    assert len(calls) == 1


def test_source_only_cli_wrapper_runs_from_another_directory(tmp_path):
    script = readiness.ROOT / "scripts/check_readiness.sh"
    process = subprocess.run(["bash", str(script), "--source-only", "--json"], cwd=tmp_path,
                             text=True, capture_output=True, timeout=15)
    assert process.returncode == 0, process.stderr
    report = json.loads(process.stdout)
    assert report["scope"] == "source-only" and report["status"] == "passed"
    assert report["deployment_acceptance"] is False


@pytest.mark.parametrize("args", [
    ["--expected-commit", "a" * 40], ["--expected-build-id", "synthetic"],
    ["--base-url", "http://user:password@127.0.0.1"], ["--base-url", "http://[invalid"],
    ["--base-url", "http://synthetic.example.invalid"],
    ["--host-header", "example.invalid\nInjected: value"],
])
def test_invalid_selection_stops_before_any_probe(monkeypatch, args):
    monkeypatch.setattr(readiness, "scan_browser_waits", lambda: pytest.fail("probe reached"))
    with pytest.raises(SystemExit) as exc:
        readiness.main(args)
    assert exc.value.code == 2


def test_observed_failure_does_not_hide_other_missing_evidence():
    report = readiness.summarize([readiness.result("unit", "failed", "synthetic"),
                                  readiness.result("logs", "blocked", "synthetic")], "synthetic")
    assert report["status"] == "failed"
    assert report["counts"] == {"passed": 0, "failed": 1, "blocked": 1}
