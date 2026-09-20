"""Behavioral reproduction checks use disposable, wholly synthetic Git trees."""
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

import pytest

from scripts.run_release_reproducer import digest, reproduce


@pytest.fixture(autouse=True)
def isolated_git_environment(monkeypatch):
    """A hook's index/worktree must never be reused by synthetic repositories."""
    for name in tuple(os.environ):
        if name.startswith("GIT_"):
            monkeypatch.delenv(name)


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "synthetic-repo"
    root.mkdir()
    root.chmod(0o2700)  # Mirror the workspace's inherited group-directory flag.
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    for key, value in (("user.name", "Synthetic"), ("user.email", "synthetic@example.invalid")):
        git(root, "config", key, value)
    yield root
    for directory, _, _ in os.walk(root):
        Path(directory).chmod(0o700)


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args]).decode().strip()


def commit(repo, value):
    (repo / "value.py").write_text(f"VALUE = {value!r}\n")
    git(repo, "add", "value.py")
    git(repo, "commit", "-qm", "synthetic source")
    return git(repo, "rev-parse", "HEAD")


def test_old_commit_dirty_tree_and_untracked_inputs_are_isolated(repo):
    sha = commit(repo, "old")
    commit(repo, "new")
    (repo / "value.py").write_text("raise RuntimeError('dirty source imported')")
    (repo / "untracked.txt").write_text("excluded")
    commands = [[sys.executable, "-c", "import value; print(value.VALUE); assert value.VALUE == 'old'"]]
    path, receipt = reproduce(repo, sha, commands=commands)
    assert receipt["passed"]
    assert (path.parent / "check-1.stdout").read_text().strip() == "old"
    export = Path(receipt["export_dir"])
    assert set(p.name for p in export.iterdir()) == {"value.py"}
    assert receipt["environment"]["PYTHONPATH"] == receipt["test_cwd"]
    assert not path.is_relative_to(export)
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700
    assert receipt["checks"][0]["stdout_sha256"] == digest((path.parent / "check-1.stdout").read_bytes())
    assert receipt["dependencies"] and receipt["runner_sha256"]
    assert reproduce(repo, sha, commands=commands)[1]["passed"]


def test_failure_runs_exactly_once_and_records_actual_exit_code(repo):
    sha = commit(repo, "fixture")
    code = "import os,pathlib; p=pathlib.Path(os.environ['HOME'])/'counter'; p.write_text(p.read_text()+'x' if p.exists() else 'x'); raise SystemExit(7)"
    path, receipt = reproduce(repo, sha, commands=[[sys.executable, "-c", code]])
    assert not receipt["passed"]
    assert receipt["checks"][0]["exit_code"] == 7
    assert (path.parent / "home/counter").read_text() == "x"


@pytest.mark.parametrize("damage", ["bytes", "extra", "missing", "symlink", "extra_dir"])
def test_tampered_export_refused_before_commands(repo, damage):
    sha = commit(repo, "fixture")
    _, receipt = reproduce(repo, sha, commands=[])
    export = Path(receipt["export_dir"])
    export.chmod(0o700)
    source = export / "value.py"
    if damage == "bytes":
        source.chmod(0o600)
        source.write_text("changed")
    elif damage == "extra":
        (export / "extra").write_text("unexpected")
    elif damage == "extra_dir":
        (export / "extra").mkdir()
    elif damage == "missing":
        source.unlink()
    else:
        source.unlink()
        source.symlink_to(repo / "value.py")
    export.chmod(0o500)
    with pytest.raises(ValueError, match="integrity"):
        reproduce(repo, sha, commands=[])


def test_git_symlink_rejected_before_export(repo):
    commit(repo, "fixture")
    (repo / "escape").symlink_to("../outside")
    git(repo, "add", "escape")
    git(repo, "commit", "-qm", "synthetic symlink")
    with pytest.raises(ValueError, match="symlinks"):
        reproduce(repo, "HEAD", commands=[])
    assert not (repo / "runtime").exists()


def test_checks_cannot_use_enclosing_git_index(repo):
    sha = commit(repo, "fixture")
    code = "import subprocess; r=subprocess.run(['git','rev-parse','--show-toplevel'],capture_output=True); assert r.returncode != 0"
    assert reproduce(repo, sha, commands=[[sys.executable, "-c", code]])[1]["passed"]


def test_invalid_revision_has_no_runtime_side_effect(repo):
    commit(repo, "fixture")
    with pytest.raises(ValueError, match="cannot resolve"):
        reproduce(repo, "--invalid", commands=[])
    assert not (repo / "runtime").exists()


def test_shell_requires_one_argument():
    script = Path(__file__).resolve().parents[1] / "scripts/release_reproducer.sh"
    result = subprocess.run(["bash", str(script)], capture_output=True, text=True)
    assert result.returncode == 2
    assert "Usage" in result.stderr


def test_disposable_runtime_is_allowed_but_source_changes_fail(repo):
    sha = commit(repo, "fixture")
    code = "from pathlib import Path; Path('runtime').mkdir(); Path('runtime/state').write_text('synthetic')"
    path, receipt = reproduce(repo, sha, commands=[[sys.executable, "-c", code]])
    assert receipt["passed"]
    assert not (Path(receipt["export_dir"]) / "runtime").exists()
    code = "from pathlib import Path; Path('value.py').write_text('changed')"
    _, receipt = reproduce(repo, sha, commands=[[sys.executable, "-c", code]])
    assert not receipt["passed"]
    assert not receipt["source_integrity_after_checks"]


def test_unstartable_command_still_gets_receipt(repo):
    sha = commit(repo, "fixture")
    path, receipt = reproduce(repo, sha, commands=[["/synthetic/nonexistent-command"]])
    assert path.exists()
    assert receipt["checks"][0]["exit_code"] == 127
    assert not receipt["passed"]


def test_caller_postgres_target_env_is_forwarded(repo, monkeypatch):
    """The exported acceptance run inherits the operator's real PRACE_DB_*
    target and never a fabricated one."""
    sha = commit(repo, "fixture")
    monkeypatch.setenv("PRACE_DB_NAME", "synthetic_caller_db")
    monkeypatch.setenv("PRACE_DB_HOST", "127.0.0.1")
    monkeypatch.setenv("PRACE_DB_PORT", "5432")
    code = (
        "import os;"
        "assert os.environ['PRACE_DB_NAME'] == 'synthetic_caller_db';"
        "assert os.environ['PRACE_DB_HOST'] == '127.0.0.1';"
        "assert os.environ['PRACE_DB_PORT'] == '5432';"
    )
    _, receipt = reproduce(repo, sha, commands=[[sys.executable, "-c", code]])
    assert receipt["passed"]
    assert receipt["environment"]["PRACE_DB_NAME"] == "synthetic_caller_db"


def test_caller_migration_credential_pair_is_forwarded(repo, monkeypatch):
    """The migration credential pair and its scope signal must survive the
    export so a migrate step inside the acceptance run uses the schema-owner
    role and the migration statement timeout, exactly like the rehearsal
    command does. Forwarding the pair is a secret-carrying operation, so the
    receipt must still only record it as a presence marker."""
    sha = commit(repo, "fixture")
    monkeypatch.setenv("PRACE_MIGRATION_DB_USER", "prace_migrator")
    secret = "migrator-secret-9f2"
    monkeypatch.setenv("PRACE_MIGRATION_DB_PASSWORD", secret)
    monkeypatch.setenv("PRACE_MIGRATION_SCOPE", "1")
    monkeypatch.setenv("PRACE_MIGRATION_STATEMENT_TIMEOUT_MS", "120000")
    digest = hashlib.sha256(secret.encode()).hexdigest()
    code = (
        "import os, hashlib;"
        "v = os.environ['PRACE_MIGRATION_DB_PASSWORD'];"
        f"assert hashlib.sha256(v.encode()).hexdigest() == '{digest}';"
        "assert os.environ['PRACE_MIGRATION_DB_USER'] == 'prace_migrator';"
        "assert os.environ['PRACE_MIGRATION_SCOPE'] == '1';"
        "assert os.environ['PRACE_MIGRATION_STATEMENT_TIMEOUT_MS'] == '120000';"
    )
    _, receipt = reproduce(repo, sha, commands=[[sys.executable, "-c", code]])
    assert receipt["passed"]
    body = json.dumps(receipt)
    assert secret not in body, (
        "migration credential value leaked into the receipt")
    assert receipt["environment"]["PRACE_MIGRATION_DB_PASSWORD"] == "set"
    assert receipt["environment"]["PRACE_MIGRATION_SCOPE"] == "1"


def test_receipt_never_records_secret_values(repo, monkeypatch):
    """The receipt serializes an allowlisted sanitized environment; credential
    names appear as presence markers only, never with their values."""
    secret_value = "super-secret-value-1902f3a"
    sha = commit(repo, "fixture")
    for name in ("PRACE_DB_PASSWORD", "PGPASSWORD", "PRACE_SECRET_KEY",
                 "JOURNEY_EVIDENCE_PATH"):
        monkeypatch.setenv(name, "x")
    monkeypatch.setenv("PRACE_DB_PASSWORD", secret_value)
    monkeypatch.setenv("PGPASSWORD", secret_value)
    monkeypatch.setenv("PRACE_SECRET_KEY", secret_value)
    _, receipt = reproduce(repo, sha, commands=[[sys.executable, "-c", "pass"]])
    body = json.dumps(receipt)
    assert secret_value not in body, (
        "a driver credential was serialized into the receipt; the receipt "
        "must keep execution variables out of the evidence store")
    for name in ("PRACE_DB_PASSWORD", "PGPASSWORD", "PRACE_SECRET_KEY"):
        assert receipt["environment"][name] == "set", (
            f"{name} must be recorded as a set marker, got "
            f"{receipt['environment'].get(name)!r}")
    assert "JOURNEY_EVIDENCE_PATH" in receipt["environment"]
    assert receipt["passed"]


def test_acceptance_commands_include_core_journey_and_timeout():
    """The default acceptance commands must include the core journey with correct args and timeout."""
    from scripts.run_release_reproducer import acceptance_commands, ACCEPTANCE_COMMAND_TIMEOUT
    import sys
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        state = Path(tmp) / "state"
        repo = Path(tmp) / "repo"
        repo.mkdir()
        sha = "0" * 40
        commands = acceptance_commands(sys.executable, state, repo, sha)
        # Default: four commands (planning, pytest, django, core journey)
        assert len(commands) == 4
        core_cmd = commands[-1]
        assert core_cmd[0] == sys.executable
        assert core_cmd[1] == "scripts/run_core_journey.py"
        assert "--repo-root" in core_cmd
        assert str(repo) in core_cmd
        assert "--commit" in core_cmd
        assert sha in core_cmd
        assert "--state" in core_cmd
        assert str(state / "core-journey") in core_cmd
        assert "--profile" in core_cmd
        assert "core" in core_cmd
        assert ACCEPTANCE_COMMAND_TIMEOUT >= 3600
        assert ACCEPTANCE_COMMAND_TIMEOUT == 3600


def test_acceptance_commands_include_a1_when_requested():
    """--include-a1 must add the optional-a1 journey as a separate check."""
    from scripts.run_release_reproducer import acceptance_commands
    import sys
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        state = Path(tmp) / "state"
        repo = Path(tmp) / "repo"
        repo.mkdir()
        sha = "0" * 40
        commands = acceptance_commands(sys.executable, state, repo, sha, include_a1=True)
        assert len(commands) == 5
        a1_cmd = commands[-1]
        assert a1_cmd[0] == sys.executable
        assert a1_cmd[1] == "scripts/run_core_journey.py"
        assert "--profile" in a1_cmd
        assert "optional-a1" in a1_cmd
        assert str(state / "optional-a1-journey") in a1_cmd


def test_reproduce_default_excludes_a1(repo):
    """By default, reproduce runs only core acceptance (no A1 journey)."""
    sha = commit(repo, "fixture")
    commands = [[sys.executable, "-c", "print('ok')"]]
    path, receipt = reproduce(repo, sha, commands=commands)
    assert receipt["passed"]
    assert len(receipt["checks"]) == 1


def test_reproduce_include_a1_adds_a1_journey(repo):
    """When include_a1=True, the A1 journey command is appended."""
    sha = commit(repo, "fixture")
    path, receipt = reproduce(repo, sha, commands=[[sys.executable, "-c", "print('ok')"]],
                             include_a1=True)
    # 1 synthetic command + the A1 core-journey command
    assert len(receipt["checks"]) == 2
    a1_check = receipt["checks"][-1]
    assert "optional-a1" in " ".join(a1_check["argv"])


def test_reproduce_core_passes_despite_a1_failure(repo):
    """Core acceptance is independent: A1 journey failure must not invalidate core."""
    sha = commit(repo, "fixture")
    core_ok = [sys.executable, "-c", "print('core-ok')"]
    a1_fail = [sys.executable, "-c", "import sys; sys.exit(1)"]
    path, receipt = reproduce(repo, sha, commands=[core_ok, a1_fail], include_a1=True)
    assert len(receipt["checks"]) == 3
    assert receipt["checks"][0]["exit_code"] == 0
    assert receipt["checks"][2]["exit_code"] != 0
    assert "optional-a1" in " ".join(receipt["checks"][2]["argv"])
    assert receipt["checks"][0]["exit_code"] == 0
