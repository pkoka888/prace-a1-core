#!/usr/bin/env python3
"""Detect credential signatures in Git blobs without printing secret values.
This complements path review; it does not establish absence of PII.
"""
import re
import subprocess

PATTERN = re.compile(rb"(?:-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\b(?:sk-or-v1-|sk-proj-|ghp_)[A-Za-z0-9_-]{20,})")

def main():
    failed = False
    for entry in subprocess.check_output(["git", "ls-tree", "-rz", "HEAD"]).split(b"\0"):
        if not entry:
            continue
        metadata, path = entry.split(b"\t", 1)
        mode, kind, oid = metadata.split()
        if kind != b"blob":
            continue
        payload = subprocess.check_output(["git", "cat-file", "blob", oid.decode()])
        if PATTERN.search(payload):
            print("CREDENTIAL_SIGNATURE:", repr(path.decode("utf-8", "replace")))
            failed = True
    return int(failed)

if __name__ == "__main__":
    raise SystemExit(main())
