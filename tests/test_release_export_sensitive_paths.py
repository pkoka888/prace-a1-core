"""Export boundaries exercised with wholly synthetic disposable Git trees."""

import os
import subprocess

import pytest

from scripts import run_release_reproducer as reproducer


@pytest.fixture
def synthetic_repo(tmp_path, monkeypatch):
    for name in tuple(os.environ):
        if name.startswith("GIT_"):
            monkeypatch.delenv(name)
    root = tmp_path / "synthetic-export-repo"
    root.mkdir()

    def git(*args):
        return subprocess.check_output(
            ["git", "-C", str(root), *args], stderr=subprocess.PIPE
        )

    git("init", "-q")
    git("config", "user.name", "Synthetic Export Test")
    git("config", "user.email", "synthetic@example.invalid")

    def commit(paths):
        for relative in paths:
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text("SYNTHETIC_CANARY=fictional-only\n")
        git("add", "--", *paths)
        git("commit", "-qm", "synthetic export boundary")
        return git("rev-parse", "HEAD").decode().strip()

    return root, commit


@pytest.mark.parametrize("relative", [
    ".runtime-config/gunicorn.env",
    ".runtime-config/README.md",
    "nested/.runtime-config/gunicorn.env",
    ".env",
    ".env.production",
    "nested/.env.test",
    ".env.example.local",
    ".env.example/nested-payload.txt",
    "config/gunicorn.env",
    ".history-remediation/receipt.json",
    "nested/.history-remediation/receipt.json",
    "secrets/credential.txt",
    "config/secrets/credential.txt",
    "a1/review.csv",
    "scans/source.pdf",
    "evidence/receipt.json",
    "ocr/result.json",
    "data/private.json",
    "output/provisional/form.pdf",
    "runtime/portal/receipt.json",
    "employees/scans/source.pdf",
])
def test_protected_tree_rejected_before_any_blob_read(
    synthetic_repo, monkeypatch, relative
):
    root, commit = synthetic_repo
    sha = commit(["000-safe-source.py", relative])
    real_git = reproducer.git
    blob_reads = []

    def inspected_git(repo, *args):
        if args[:2] == ("cat-file", "blob"):
            blob_reads.append(args)
        return real_git(repo, *args)

    monkeypatch.setattr(reproducer, "git", inspected_git)
    with pytest.raises(ValueError, match="Protected data path"):
        reproducer.tree(root, sha)
    assert blob_reads == []
    assert not (root / "runtime").exists() or relative.startswith("runtime/")


def test_reviewable_templates_and_source_names_remain_exportable(synthetic_repo):
    root, commit = synthetic_repo
    paths = [
        ".env.example",
        "config/.env.example",
        "config/gunicorn.env.example",
        "docs/security/secrets.md",
        "docs/decisions/evidence/plan-e/receipt.json",
        "scripts/a1_core.py",
        "scripts/ocr_worker.py",
        "tests/test_secret_handling.py",
        "config/.runtime-config.schema.json",
    ]
    sha = commit(paths)
    entries = reproducer.tree(root, sha)
    assert set(entries) == set(paths)
    assert all(payload == b"SYNTHETIC_CANARY=fictional-only\n"
               for _, payload in entries.values())


def test_reproduce_rejects_runtime_config_before_creating_export(synthetic_repo):
    root, commit = synthetic_repo
    sha = commit([".runtime-config/gunicorn.env"])
    previous_umask = os.umask(0o077)
    try:
        with pytest.raises(ValueError, match="Protected data path"):
            reproducer.reproduce(root, sha, commands=[])
    finally:
        os.umask(previous_umask)
    assert not (root / "runtime").exists()
