#!/usr/bin/env python3
"""Detect credential signatures in Git blobs without printing secret values.
This complements path review; it does not establish absence of PII.

Three classes are checked:

* credential signatures -- private keys and known token prefixes;
* business-registration identifiers -- a Czech IČO is an eight-digit number
  with a check digit, and for a sole trader it identifies a natural person.
  It is therefore a personal identifier, not a company reference, and it
  must not appear in a committed document;
* database files -- the working database holds real client identities, and
  the published history of this repository was once rewritten to remove
  PII-bearing ancestry. A database in Git would undo that, and Git history is
  permanent: removing the file later does not remove it from the clones.

Both the committed content and the staged content are checked. A leak caught
only after the commit that introduced it is a commit too late.

The working tree is checked as well. A file that is untracked, or that was
staged with ``git add -N`` (intent to add), is not visible in ``git diff
--cached`` with its real content, so a leak sitting in such a file would
survive the pre-commit review and land in the next commit that includes it.

The checks report the path only, never the matched value.
"""

import re
import subprocess
from pathlib import Path

PATTERN = re.compile(
    rb"(?:-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\b(?:sk-or-v1-|sk-proj-|ghp_)[A-Za-z0-9_-]{20,})"
)

# The blob oid of an empty file. An index entry that holds the empty blob
# while the working tree holds content is an intent-to-add entry: the index
# has no content to scan, so the working tree is scanned instead.
EMPTY_BLOB_OID = "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"

# A database file is never a committable artefact. The rule is enforced here
# rather than only in .gitignore, so that removing the ignore rule cannot
# quietly expose the working data.
DATABASE_SUFFIXES = (".sqlite3", ".sqlite", ".db", ".db3")

# Czech IČO: eight digits, weighted 8..2 over the first seven, check digit
# 11 - (sum % 11) with 10 read as 0.
_ICO_WEIGHTS = (8, 7, 6, 5, 4, 3, 2)
_ICO_NUMBER = re.compile(r"(?<![0-9A-Za-z])([0-9]{8})(?![0-9A-Za-z])")
_ICO_DATE = re.compile(r"^(19|20)\d{2}(0[1-9]|1[0-2])([0-2]\d|3[01])$")
_ICO_CONTEXT = re.compile(
    r"(?i)(i[čc]o|\bico\b|ares|identifika[čc]n[íi]|obchodn[íi]\s+rejst[řr][íi]k"
    r"|obchodn[íi]\s+jm[ée]no|registration_number|employer[_\s-]?id)"
)
_ICO_CONTEXT_WINDOW = 80
# The synthetic benchmark corpus is synthetic by construction, so a
# check-digit-valid number there is a coincidence and not a disclosure.
_ICO_SYNTHETIC_PREFIXES = ("research/synthetic/", "tests/")


def _is_valid_ico(value):
    remainder = 11 - (sum(int(value[i]) * _ICO_WEIGHTS[i] for i in range(7)) % 11)
    if remainder == 10:
        remainder = 0
    return remainder == int(value[7])


def _has_ico_context(text, start, end):
    window = text[max(0, start - _ICO_CONTEXT_WINDOW) : end + _ICO_CONTEXT_WINDOW]
    return _ICO_CONTEXT.search(window) is not None


def find_ico_occurrences(text, path):
    """Return the IČO-shaped numbers in text, with a registration context."""
    found = []
    for match in _ICO_NUMBER.finditer(text):
        value = match.group(1)
        if _ICO_DATE.match(value) or not _is_valid_ico(value):
            continue
        if any(path.startswith(p) for p in _ICO_SYNTHETIC_PREFIXES):
            continue
        if _has_ico_context(text, match.start(), match.end()):
            found.append(value)
    return found


def is_database_path(path) -> bool:
    return Path(path).suffix.lower() in DATABASE_SUFFIXES


def staged_paths():
    """The paths staged for the next commit, or an empty list outside a commit."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"], capture_output=True, text=True
    )
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]


def untracked_paths():
    """The untracked, non-ignored paths in the working tree.

    Ignored paths are excluded: they are not committable by accident and the
    protected private directories would otherwise flood the report.
    """
    result = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]


def intent_to_add_paths():
    """Paths staged with ``git add -N``: present in the index, empty in it.

    Such an entry carries the empty blob, so ``git show :<path>`` yields
    nothing to scan while the working tree holds the real content.
    """
    result = subprocess.run(["git", "ls-files", "--stage", "-z"], capture_output=True)
    if result.returncode != 0:
        return []
    paths = []
    for entry in result.stdout.split(b"\0"):
        if not entry:
            continue
        metadata, _, path = entry.partition(b"\t")
        parts = metadata.split()
        if len(parts) < 2:
            continue
        mode, oid = parts[0], parts[1]
        if mode == b"160000" or oid.decode() != EMPTY_BLOB_OID:
            continue
        paths.append(path.decode("utf-8", "replace"))
    return paths


def staged_blob(path: str):
    """The staged content of a path, which is what the next commit will hold."""
    result = subprocess.run(["git", "show", f":{path}"], capture_output=True)
    if result.returncode != 0:
        return None
    return result.stdout


def working_tree_blob(path: str):
    """The working-tree content of a path, or None when it cannot be read."""
    try:
        return Path(path).read_bytes()
    except (OSError, ValueError):
        return None


def _report(path: str, payload: bytes) -> bool:
    """Check one payload. Returns whether anything was found."""
    found = False
    # Ignore test files for credential signatures and IČO (synthetic fixtures)
    if not path.startswith("tests/"):
        if PATTERN.search(payload):
            print("CREDENTIAL_SIGNATURE:", repr(path))
            found = True
        if find_ico_occurrences(payload.decode("utf-8", "replace"), path):
            print("BUSINESS_REGISTRATION_IDENTIFIER:", repr(path))
            found = True
    if is_database_path(path):
        print("DATABASE_FILE:", repr(path))
        found = True
    return found


def main():
    failed = False
    for entry in subprocess.check_output(["git", "ls-tree", "-rz", "HEAD"]).split(
        b"\0"
    ):
        if not entry:
            continue
        metadata, path = entry.split(b"\t", 1)
        mode, kind, oid = metadata.split()
        if kind != b"blob":
            continue
        payload = subprocess.check_output(["git", "cat-file", "blob", oid.decode()])
        if _report(path.decode("utf-8", "replace"), payload):
            failed = True
    # What is about to be committed is checked as well, so a leak is caught
    # before it lands rather than after.
    for path in staged_paths():
        if is_database_path(path):
            print(
                "DATABASE_FILE_STAGED:",
                repr(path),
                "\n  a working database holds real client identities and must "
                "not be committed; back it up to the private runtime instead "
                "(docs/operations/local-database-backup.md)",
            )
            failed = True
            continue
        payload = staged_blob(path)
        if payload is None:
            continue
        if _report(path, payload):
            failed = True
    # Content that is not in the index yet is content that a later commit may
    # publish without a second review. It is scanned now, from the working
    # tree, so the leak is caught before it is staged.
    for path in untracked_paths():
        if is_database_path(path):
            print(
                "DATABASE_FILE_UNTRACKED:",
                repr(path),
                "\n  a working database holds real client identities and must "
                "not be committed; back it up to the private runtime instead "
                "(docs/operations/local-database-backup.md)",
            )
            failed = True
            continue
        payload = working_tree_blob(path)
        if payload is None:
            continue
        if _report(path, payload):
            failed = True
    # An intent-to-add entry is in the index but empty in it: the index holds
    # the empty blob, so the staged scan above saw nothing. The real content
    # is in the working tree and is scanned here.
    for path in intent_to_add_paths():
        if is_database_path(path):
            print(
                "DATABASE_FILE_INTENT_TO_ADD:",
                repr(path),
                "\n  a working database holds real client identities and must "
                "not be committed; back it up to the private runtime instead "
                "(docs/operations/local-database-backup.md)",
            )
            failed = True
            continue
        payload = working_tree_blob(path)
        if payload is None:
            continue
        if _report(path, payload):
            failed = True
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
