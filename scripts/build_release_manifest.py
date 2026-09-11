#!/usr/bin/env python3
"""Build the release manifest for the supervised synthetic deployment.

The supervised settings module (``portal.settings_supervised_synthetic``)
refuses to start without a release manifest on disk whose SHA-256
matches ``PRACE_RELEASE_MANIFEST_SHA256``. The manifest must declare
the actual source commit, the application build identifier, and the
generation timestamp in a strict schema.

This script:

* Reads the current ``git rev-parse HEAD`` and a build identifier
  derived from the environment (``PRACE_APP_BUILD_ID`` or
  ``git describe``).
* Writes the manifest as JSON to the path supplied (or to
  ``runtime/portal/supervised-development/release_manifest.json``).
* Atomically replaces the target file with mode 0o400 (read-only
  for the owner) so the read_manifest() contract is satisfied.

The script is the only place that should write a release manifest.
Operators do not edit it manually. ``PRACE_RELEASE_MANIFEST_SHA256``
is the expected hash; the manifest's hash must match it on every
service start.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = REPO_ROOT / "runtime" / "portal" / "supervised-development" / "release_manifest.json"


def _git_commit() -> str:
    proc = subprocess.run(["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
                          check=False, capture_output=True, text=True)
    sha = (proc.stdout or "").strip()
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise SystemExit(f"FAIL: HEAD is not a 40-hex commit SHA: {sha!r}")
    return sha


def _app_build_id(explicit: str | None) -> str:
    if explicit:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", explicit):
            raise SystemExit(f"FAIL: app_build_id {explicit!r} fails schema")
        return explicit
    env = os.environ.get("PRACE_APP_BUILD_ID", "").strip()
    if env and re.fullmatch(r"[A-Za-z0-9_-]{1,128}", env):
        return env
    # Fallback: git describe (e.g. v0.0.0-12-gabcdef). If describe
    # fails, use the short SHA.
    proc = subprocess.run(["git", "-C", str(REPO_ROOT), "describe", "--always", "--dirty"],
                          check=False, capture_output=True, text=True)
    describe = (proc.stdout or "").strip()
    if describe and re.fullmatch(r"[A-Za-z0-9_-]{1,128}", describe):
        return describe
    short = _git_commit()[:12]
    return f"g{short}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT,
                        help="Path to the manifest (default: %(default)s)")
    parser.add_argument("--app-build-id", default=None,
                        help="Override the app_build_id (default: env or git describe)")
    args = parser.parse_args()

    payload = {
        "git_commit": _git_commit(),
        "app_build_id": _app_build_id(args.app_build_id),
        "generated_at": _dt.datetime.now(_dt.timezone.utc)
                                     .replace(microsecond=0).isoformat()
                                     .replace("+00:00", "Z"),
        "schema_version": 1,
    }
    body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    expected_sha = hashlib.sha256(body).hexdigest()

    out = args.output.resolve()
    if not out.parent.exists():
        out.parent.mkdir(parents=True, exist_ok=True)
        out.parent.chmod(0o700)
    # Atomic write to a sibling temp file, then rename. Use mode 0o400
    # (read-only for owner) so the read_manifest() PERMISSIONS check
    # succeeds without further chmod.
    fd, tmp_path = tempfile.mkstemp(prefix=".release-manifest-",
                                     dir=str(out.parent))
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(tmp_path, 0o400)
        os.replace(tmp_path, out)
    except BaseException:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
    out.chmod(0o400)
    print(f"wrote {out}")
    print(f"  git_commit   = {payload['git_commit']}")
    print(f"  app_build_id = {payload['app_build_id']}")
    print(f"  generated_at = {payload['generated_at']}")
    print(f"  sha256       = {expected_sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
