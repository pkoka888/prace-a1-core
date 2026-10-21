"""The tracked-content guard detects business-registration identifiers.

A Czech IČO is an eight-digit number with a check digit. For a sole trader it
identifies a natural person: it is the person's registration in the commercial
register, it is publicly searchable, and it resolves to a name. A bare
eight-digit check-digit test is far too noisy to use as a guard, so the
shipped rule is narrow, and these tests pin that narrowness.
"""

import os
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from scripts.check_git_content import find_ico_occurrences  # noqa: E402


def _synthetic_ico(prefix: str) -> str:
    """A registration number that satisfies the check digit, built at runtime.

    It is written out in pieces so that no check-digit-valid number appears
    literally in this file: the guard cannot tell a synthetic number from a
    real one, and it must not flag the test that exercises it.
    """
    weights = (8, 7, 6, 5, 4, 3, 2)
    total = sum(int(prefix[index]) * weights[index] for index in range(7))
    remainder = 11 - (total % 11)
    if remainder == 10:
        remainder = 0
    return prefix + str(remainder)


SAMPLE = _synthetic_ico("1234567")


def test_detects_a_registration_number_next_to_a_keyword():
    text = f"ARES enrichment for the employer (`a1/employer-{SAMPLE}-ares.json`)"
    assert find_ico_occurrences(text, "docs/x.md") == [SAMPLE]


def test_ignores_a_calendar_date():
    # 20260814 passes the IČO check digit by coincidence.
    assert "20260814" not in find_ico_occurrences(
        "the seed is 20260814 and the IČO context is absent", "docs/x.md"
    )
    assert "20260920" not in find_ico_occurrences(
        "generated 20260920, no registration keyword nearby", "docs/x.md"
    )


def test_ignores_a_number_without_registration_context():
    text = f"the value {SAMPLE} appears without any registration keyword"
    assert find_ico_occurrences(text, "docs/x.md") == []


def test_ignores_a_number_that_fails_the_check_digit():
    # Last digit changed, so the check digit no longer validates.
    assert (
        find_ico_occurrences("employer_id 17511268 is not a valid IČO", "docs/x.md")
        == []
    )


def test_ignores_the_declared_synthetic_corpus():
    text = f'"supplier_ico": "{SAMPLE}"'
    assert find_ico_occurrences(text, "research/synthetic/ground_truth.json") == []


def test_ignores_non_eight_digit_numbers():
    for value in ("1751126", "1234567907", "1751126a"):
        assert find_ico_occurrences(f"employer id {value}", "docs/x.md") == []


def test_the_keyword_must_be_near_the_number():
    far = "employer id " + ("x" * 200) + f" {SAMPLE}"
    assert find_ico_occurrences(far, "docs/x.md") == []


def test_tracked_documents_carry_no_registration_identifier():
    """The guard's purpose: no committed document names a registration number.

    This scans the working-tree content of every tracked document, which is
    what a commit would publish. Scanning HEAD instead would make the test
    fail on the very commit that removes the identifier.
    """
    import subprocess

    repo = REPO
    offenders = []
    for entry in subprocess.check_output(
        ["git", "ls-tree", "-rz", "HEAD"], cwd=repo
    ).split(b"\0"):
        if not entry:
            continue
        metadata, path = entry.split(b"\t", 1)
        mode, kind, oid = metadata.split()
        if kind != b"blob":
            continue
        name = path.decode("utf-8", "replace")
        if not name.endswith((".md", ".json", ".yml", ".yaml", ".txt")):
            continue
        local = repo / name
        if local.exists():
            text = local.read_text(encoding="utf-8", errors="replace")
        else:
            text = subprocess.check_output(
                ["git", "cat-file", "blob", oid.decode()], cwd=repo
            ).decode("utf-8", "replace")
        if find_ico_occurrences(text, name):
            offenders.append(name)
    assert not offenders, (
        f"tracked documents name a business-registration identifier: {offenders}"
    )


def _run_in(repo: Path, argv):
    """Run a command inside a repository and return its output."""
    return subprocess.run(
        argv, cwd=repo, capture_output=True, text=True, check=True
    ).stdout


def _make_repo(tmp_path: Path) -> Path:
    """A repository with one committed, harmless file."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _run_in(repo, ["git", "init", "-q"])
    _run_in(repo, ["git", "config", "user.email", "test@example.invalid"])
    _run_in(repo, ["git", "config", "user.name", "Test"])
    (repo / "README.md").write_text("harmless\n", encoding="utf-8")
    _run_in(repo, ["git", "add", "README.md"])
    _run_in(repo, ["git", "commit", "-qm", "first"])
    return repo


def _scan(repo: Path) -> tuple[int, str]:
    """Run the guard inside a repository and return its verdict and output."""
    previous = Path.cwd()
    os.chdir(repo)
    try:
        import scripts.check_git_content as guard

        buffer = []

        class _Capture:
            def write(self, text):
                buffer.append(text)

            def flush(self):
                pass

        original = sys.stdout
        sys.stdout = _Capture()
        try:
            code = guard.main()
        finally:
            sys.stdout = original
        return code, "".join(buffer)
    finally:
        os.chdir(previous)


def test_an_untracked_file_with_a_credential_is_reported(tmp_path):
    """Untracked content is content a later commit may publish unnoticed."""
    repo = _make_repo(tmp_path)
    (repo / "notes.md").write_text(
        "token ghp_abcdefghijklmnopqrstuvwxyz012345\n", encoding="utf-8"
    )
    code, output = _scan(repo)
    assert code == 1
    assert "CREDENTIAL_SIGNATURE" in output
    assert "notes.md" in output


def test_an_intent_to_add_file_with_a_credential_is_reported(tmp_path):
    """``git add -N`` leaves an empty blob in the index, so the staged scan
    sees nothing; the working-tree content must be scanned instead."""
    repo = _make_repo(tmp_path)
    (repo / "draft.md").write_text(
        "-----BEGIN " + "RSA PRIVATE KEY-----" + chr(10) + "MIIEow" + chr(10), encoding="utf-8"
    )
    _run_in(repo, ["git", "add", "-N", "draft.md"])
    code, output = _scan(repo)
    assert code == 1
    assert "CREDENTIAL_SIGNATURE" in output
    assert "draft.md" in output


def test_a_clean_working_tree_passes(tmp_path):
    repo = _make_repo(tmp_path)
    (repo / "notes.md").write_text("nothing secret here\n", encoding="utf-8")
    code, output = _scan(repo)
    assert code == 0, output


def test_an_untracked_database_file_is_refused(tmp_path):
    repo = _make_repo(tmp_path)
    (repo / "portal.sqlite3").write_bytes(b"SQLite format 3\x00")
    code, output = _scan(repo)
    assert code == 1
    assert "DATABASE_FILE_UNTRACKED" in output
