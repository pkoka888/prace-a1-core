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

The checks report the path only, never the matched value.
"""

import re
import subprocess
from pathlib import Path

PATTERN = re.compile(
    rb"(?:-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\b(?:sk-or-v1-|sk-proj-|ghp_)[A-Za-z0-9_-]{20,})"
)

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
_ICO_SYNTHETIC_PREFIX = "research/synthetic/"


def _is_valid_ico(value):
    remainder = 11 - (sum(int(value[i]) * _ICO_WEIGHTS[i] for i in range(7)) % 11)
    if remainder == 10:
        remainder = 0
    return remainder == int(value[7])


def _has_ico_context(text, start, end):
    window = text[max(0, start - _ICO_CONTEXT_WINDOW):end + _ICO_CONTEXT_WINDOW]
    return _ICO_CONTEXT.search(window) is not None


def find_ico_occurrences(text, path):
    """Return the IČO-shaped numbers in text, with a registration context."""
    found = []
    for match in _ICO_NUMBER.finditer(text):
        value = match.group(1)
        if _ICO_DATE.match(value) or not _is_valid_ico(value):
            continue
        if path.startswith(_ICO_SYNTHETIC_PREFIX):
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


def staged_blob(path: str):
    """The staged content of a path, which is what the next commit will hold."""
    result = subprocess.run(["git", "show", f":{path}"], capture_output=True)
    if result.returncode != 0:
        return None
    return result.stdout


def _report(path: str, payload: bytes) -> bool:
    """Check one payload. Returns whether anything was found."""
    found = False
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
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
