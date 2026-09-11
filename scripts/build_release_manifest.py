#!/usr/bin/env python3
"""Build the release manifest for the supervised synthetic deployment.

The supervised settings module (``portal.settings_supervised_synthetic``)
refuses to start without a release manifest on disk whose SHA-256
matches ``PRACE_RELEASE_MANIFEST_SHA256``. The manifest must declare
the actual source commit, the application build identifier, and the
generation timestamp in a strict schema.

This script:

* Validates the output path is inside the approved runtime subtree and
  does not contain symlinks — same contract as
  ``portal.release1a.runtime_safety.confined_root``. The script refuses
  to write to any path that would be rejected at settings import time.
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
APPROVED_RUNTIME_PARENT = REPO_ROOT / "runtime" / "portal"


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


def _validate_confinement(out: Path) -> Path:
    """Reject the output path before any mkdir/chmod/write.

    Mirrors ``portal.release1a.runtime_safety.no_symlinks`` and
    ``confined_root``. The check operates on the raw path BEFORE
    resolve() so symlink components are visible; resolve() follows
    symlinks and would otherwise hide the very thing we want to
    reject. The output parent must already exist as a directory we
    own in the approved runtime subtree; we never create a new
    supervised-<id> tree from this script.
    """
    raw = Path(out)
    if not raw.is_absolute() or ".." in raw.parts:
        raise SystemExit(f"FAIL: manifest path {raw} must be absolute and free of '..'")
    # Reject any symlink component in the RAW path, before resolve().
    if raw.exists() and raw.is_symlink():
        raise SystemExit(f"FAIL: manifest path {raw} is a symlink")
    for parent in [raw, *raw.parents]:
        if parent.exists() and parent.is_symlink():
            raise SystemExit(f"FAIL: manifest path {raw} contains symlink component {parent}")
    # After the raw symlink check, resolve to a canonical form for
    # the layout comparison.
    resolved = raw.resolve()
    expected_parent = APPROVED_RUNTIME_PARENT / "supervised-"  # any supervised-* child
    if resolved.parent.parent != APPROVED_RUNTIME_PARENT \
            or not resolved.parent.name.startswith("supervised-") \
            or resolved.name != "release_manifest.json":
        raise SystemExit(
            f"FAIL: manifest path {resolved} is not under "
            f"{APPROVED_RUNTIME_PARENT}/supervised-*/release_manifest.json"
        )
    # Parent must already exist as a confined layout (operator-owned
    # 0700 directory under runtime/portal/). If it doesn't, the
    # settings module would refuse to load — fail closed here too.
    parent = raw.parent
    if not parent.exists():
        raise SystemExit(
            f"FAIL: parent {parent} does not exist. Run the rehearsal "
            f"script's prepare step to create it."
        )
    if not parent.is_dir() or parent.is_symlink():
        raise SystemExit(f"FAIL: parent {parent} is not a directory (or is a symlink)")
    if parent.stat().st_uid != os.getuid() or parent.stat().st_mode & 0o077:
        raise SystemExit(f"FAIL: parent {parent} is not operator-owned mode 0700")
    return raw


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT,
                        help="Path to the manifest (default: %(default)s)")
    parser.add_argument("--app-build-id", default=None,
                        help="Override the app_build_id (default: env or git describe)")
    args = parser.parse_args()

    out = _validate_confinement(args.output)
    # Parent directory must already exist; we will not create arbitrary
    # directories. The supervised settings module refuses to adopt a
    # pre-existing supervised-<id>/ directory that wasn't pre-confined,
    # so neither does this script.
    if not out.parent.exists():
        raise SystemExit(
            f"FAIL: parent directory {out.parent} does not exist. "
            f"Run the rehearsal script's prepare step to create it."
        )
    if not out.parent.is_dir():
        raise SystemExit(f"FAIL: parent path {out.parent} is not a directory")
    if out.parent.is_symlink():
        raise SystemExit(f"FAIL: parent path {out.parent} is a symlink")

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
    # Final chmod is defensive: umask may have stripped the mode.
    os.chmod(out, 0o400)
    print(f"wrote {out}")
    print(f"  git_commit   = {payload['git_commit']}")
    print(f"  app_build_id = {payload['app_build_id']}")
    print(f"  generated_at = {payload['generated_at']}")
    print(f"  sha256       = {expected_sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
