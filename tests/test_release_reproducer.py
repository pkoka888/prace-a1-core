"""
test_release_reproducer.py

Confirms scripts/release_reproducer.sh refuses unsafe invocations and
otherwise exports committed source to runtime/s-<sha>/ with a
protected receipt. Tests use a tmp worktree-like copy so they do not
mutate the real runtime directory.
"""
import json
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "release_reproducer.sh"


def _git_clean(repo_root: Path) -> bool:
    """True when the git working tree has no dirty or untracked entries."""
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "status", "--porcelain"],
        capture_output=True, text=True, check=True,
    )
    return proc.stdout.strip() == ""


@pytest.mark.skipif(
    not _git_clean(REPO_ROOT),
    reason="working tree is dirty; refuse to test the reproducer against an unreleased state"
)
def test_release_reproducer_refuses_dirty_tree(tmp_path):
    """A synthetic dirty marker file in tmp_path must cause the reproducer to exit non-zero."""
    # We cannot mutate the real repo to be dirty; instead, exercise the
    # dirty-check by copying the script to a tmp dir with a fake git wrapper.
    script_text = SCRIPT.read_text()
    script_text = script_text.replace(
        "REPO_ROOT=\"$(cd \"$(dirname \"$0\")/..\" && pwd)\"",
        f"REPO_ROOT=\"{tmp_path}\"",
        1,
    )
    fake_script = tmp_path / "release_reproducer.sh"
    fake_script.write_text(script_text)
    fake_script.chmod(0o755)

    # Set up a fake git dir with dirty status
    (tmp_path / "runtime").mkdir()
    subprocess.run(["git", "-C", str(tmp_path), "init", "--quiet"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "t"], check=True)
    (tmp_path / "a").write_text("hi")
    subprocess.run(["git", "-C", str(tmp_path), "add", "a"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "--quiet", "-m", "init"], check=True)
    (tmp_path / "dirty").write_text("uncommitted")

    proc = subprocess.run(
        ["bash", str(fake_script), "HEAD"], capture_output=True, text=True,
    )
    assert proc.returncode != 0, proc.stdout + proc.stderr
    assert "dirty" in proc.stderr.lower()
    assert not (tmp_path / "runtime" / "s-").exists() or not list(
        (tmp_path / "runtime" / "s-").iterdir()
    )


def test_release_reproducer_requires_one_arg():
    proc = subprocess.run(["bash", str(SCRIPT)], capture_output=True, text=True)
    assert proc.returncode == 2
    assert "Usage" in proc.stderr


def test_release_reproducer_rejects_invalid_sha():
    proc = subprocess.run(
        ["bash", str(SCRIPT), "definitely-not-a-real-sha-12345"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 2
    assert "cannot resolve" in proc.stderr


def test_release_reproducer_script_has_safety_guards():
    """The script must fail closed on missing args, bad SHA, dirty tree,
    and must not delete an existing export of a different commit."""
    content = SCRIPT.read_text()
    assert "set -euo pipefail" in content
    assert "git status --porcelain" in content
    assert "git archive" in content, "must use git archive, not worktree copy"
    assert "already contains commit" in content, (
        "must refuse to overwrite an existing differing export"
    )
    assert "chmod 0700" in content
    assert "chmod 0600" in content
    assert "RECEIPT" in content and ".json" in content
