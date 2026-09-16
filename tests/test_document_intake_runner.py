"""Test owned PostgreSQL dispatch/failure handling without starting a database."""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import subprocess

import pytest

from scripts import test_document_intake as runner


@pytest.fixture
def harness(monkeypatch, tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name in ("initdb", "pg_ctl"):
        binary = bin_dir / name
        binary.touch(mode=0o700)
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    monkeypatch.setattr(runner, "BIN", bin_dir)
    # No socket is bound by these subprocess-mocked unit tests. Path-length
    # refusal is tested independently before dispatch below.
    monkeypatch.setattr(runner, "check_socket_path", lambda root: None)
    for name in ("PRACE_DB_NAME", "PRACE_DB_PASSWORD", "PRACE_DISPOSABLE_TARGET",
                 "PRACE_MIGRATION_SCOPE", "DOCUMENT_TEST_PG_HOST",
                 "DOCUMENT_TEST_PG_PASSWORD", "PGDATA", "PGHOST", "PGSERVICE",
                 "PGPASSWORD", "PGPASSFILE", "PGOPTIONS"):
        monkeypatch.setenv(name, "synthetic-unowned")
    calls = []
    exits = {}

    def fake_run(argv, *, cwd, env, stdout, stderr, check):
        phase = "initdb" if Path(argv[0]).name == "initdb" else (
            "django" if "manage.py" in argv else argv[-1])
        calls.append((phase, argv, dict(env)))
        if phase == "initdb":
            Path(argv[argv.index("-D") + 1]).mkdir()
        stdout.write(f"synthetic {phase} output\n".encode())
        stderr.write(f"synthetic {phase} diagnostic\n".encode())
        return subprocess.CompletedProcess(argv, exits.get(phase, 0))

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    return tmp_path, calls, exits


def receipt(root):
    return next((root / "runtime" / "portal").glob("pg-*/receipt.json"))


def test_selected_browser_labels_use_only_fresh_socket_for_every_subprocess(harness):
    root, calls, _ = harness
    assert runner.main(["--settings", "portal.settings_browser_tests",
                        "tests.document_web.test_browser_journey"]) == 0
    record_path = receipt(root)
    run_root = record_path.parent
    assert [phase for phase, _, _ in calls] == ["initdb", "start", "django", "stop"]
    for phase, argv, env in calls:
        assert not any(name.startswith(("PRACE_", "PG")) for name in env if name != "PGPASSFILE")
        password_file = Path(env["PGPASSFILE"])
        assert password_file.parent == run_root
        assert password_file != Path("synthetic-unowned")
        password_stat = password_file.lstat()
        assert stat.S_ISREG(password_stat.st_mode)
        assert stat.S_IMODE(password_stat.st_mode) == 0o600
        assert password_stat.st_uid == os.getuid()
        assert password_file.read_bytes() == b""
        assert "DOCUMENT_TEST_PG_HOST" not in env
        assert "DOCUMENT_TEST_PG_PASSWORD" not in env
        assert env["DOCUMENT_TEST_PG_SOCKET"] == str(run_root)
        assert env["DOCUMENT_TEST_PG_NAME"] == "prace_document_tests"
        if phase != "django":
            assert argv[argv.index("-D") + 1] == str(run_root / "db")
    django = calls[2]
    assert django[1][1:] == ["manage.py", "test", "tests.document_web.test_browser_journey",
                            "--noinput", "-v", "1"]
    assert django[2]["DJANGO_SETTINGS_MODULE"] == "portal.settings_browser_tests"
    assert "listen_addresses=''" in calls[1][1][calls[1][1].index("-o") + 1]
    assert json.loads(record_path.read_text())["stopped"] is True
    assert not (run_root / "db").exists()


@pytest.mark.parametrize("phase,code", [("initdb", 9), ("start", 7), ("django", 5), ("stop", 4)])
def test_native_failure_is_preserved_with_logs_and_owned_data(harness, phase, code):
    root, calls, exits = harness
    exits[phase] = code
    assert runner.main(["tests.document_web.test_inbox"]) == code
    record_path = receipt(root)
    assert json.loads(record_path.read_text())["exit_code"] == code
    assert (record_path.parent / f"{phase}.stderr.log").read_text() == f"synthetic {phase} diagnostic\n"
    assert (record_path.parent / "db").exists()
    if phase == "initdb":
        assert [item[0] for item in calls] == ["initdb"]
    else:
        assert calls[-1][0] == "stop"


def test_test_failure_survives_secondary_stop_failure(harness):
    root, _, exits = harness
    exits.update(django=5, stop=4)
    assert runner.main(["tests.document_web.test_inbox"]) == 5
    phases = json.loads(receipt(root).read_text())["phases"]
    assert [(p["name"], p["exit_code"]) for p in phases[-2:]] == [("django", 5), ("stop", 4)]
    assert all(p["command"] and p["started_at"] and p["finished_at"] for p in phases)


@pytest.mark.parametrize("argv", [
    ["--settings", "portal.settings"],
    ["--", "--keepdb"],
    ["outside.test_module"],
])
def test_invalid_settings_or_labels_refused_before_cluster_creation(harness, argv):
    root, calls, _ = harness
    with pytest.raises(SystemExit) as exc:
        runner.main(argv)
    assert exc.value.code == 2
    assert calls == []
    assert not (root / "runtime").exists()


def test_socket_path_limit_refuses_long_source_checkout():
    with pytest.raises(ValueError, match="shorter in-project source checkout"):
        runner.check_socket_path(Path("/" + "x" * 108))
