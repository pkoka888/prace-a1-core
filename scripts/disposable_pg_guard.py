"""Disposable PostgreSQL-target guard for rehearsal and cleanup paths.

Deterministically refuses to migrate or clean up a target that is not
proved disposable and exclusively owned:

- a partial ``PRACE_DB_*`` set is never accepted (mirrors the settings
  all-or-none contract),
- the operator database name(s) are refused by exact name,
- an explicit ``PRACE_DISPOSABLE_TARGET=1`` marker AND a provisioning
  ownership record (``PRACE_DISPOSABLE_OWNERSHIP`` JSON file) are
  required, so an arbitrary supplied database can never be swept: the
  record must name the exact target database (and host for TCP targets)
  and carry the ``disposable: true`` flag. The marker alone is never
  enough,
- an exclusive-use advisory lock is acquired and, for destructive
  operations, held by the same session that performs them (see
  ``exclusive_cleanup_sql``), closing the check-then-act window.

This module is deliberately connection-free at import time so unit tests
can exercise the refusal logic deterministically. Connection attempts are
wrapped and reported as blocked rather than raised, so the caller can
distinguish ``refused`` (deterministic) from ``blocked`` (unverified).

The operator database names are exact matches only; a database such as
``prace_synthetic_test`` that is legitimately provisioned as a disposable
test target is NOT refused by name — it still needs the ownership record
and the exclusive lock.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

# Exact operator database names. Treat as data-owned; changing these
# requires infra/operator authorization, not an engineering edit alone.
OPERATOR_DB_NAMES = frozenset({"prace_synthetic"})

REQUIRED_TARGET_ENV = (
    "PRACE_DB_NAME",
    "PRACE_DB_USER",
    "PRACE_DB_PASSWORD",
    "PRACE_DB_HOST",
    "PRACE_DB_PORT",
)

DISPOSABLE_MARKER_ENV = "PRACE_DISPOSABLE_TARGET"
DISPOSABLE_OWNERSHIP_ENV = "PRACE_DISPOSABLE_OWNERSHIP"
DISPOSABLE_LOCK_KEY_ENV = "PRACE_DISPOSABLE_LOCK_KEY"

# Advisory namespace for the exclusive-use lock. Keep in sync with the
# shared lock key so the probe and the held-lock cleanup agree.
DEFAULT_LOCK_KEY = 0x5052414345

# The ownership record this guard considers provably disposable.
_OWNERSHIP_FIELDS = ("database", "host", "port", "disposable")

# psql is the only way to perform the exclusive-use lock without
# introducing a second Python DB driver; absence of psql blocks.
PSQL = "psql"


def lock_key(env: dict) -> int:
    """Explicit overridable advisory lock key, defaulting to the shared
    PRACE namespace."""
    raw = env.get(DISPOSABLE_LOCK_KEY_ENV, "").strip()
    if not raw:
        return DEFAULT_LOCK_KEY
    if not re.fullmatch(r"[0-9]{1,18}", raw):
        raise ValueError(
            f"{DISPOSABLE_LOCK_KEY_ENV}={raw!r} must be a decimal integer")
    value = int(raw)
    if not 1 <= value < 2**63:
        raise ValueError(f"{DISPOSABLE_LOCK_KEY_ENV} outside valid advisory range")
    return value


def _collect_target(env: dict) -> dict | None:
    values = {name: env.get(name, "") for name in REQUIRED_TARGET_ENV}
    present = [name for name, value in values.items() if value]
    if not present:
        return None
    if len(present) != len(REQUIRED_TARGET_ENV):
        return {"refused": True, "blocked": False, "reason": (
            f"partial PostgreSQL target: {', '.join(present)}; set the full "
            "PRACE_DB_* set or none")}
    return {"refused": False, "blocked": False, "name": values["PRACE_DB_NAME"],
            "values": values}


def _read_ownership_record(env: dict) -> dict:
    """Load the provisioning ownership record that proves the target was
    provisioned as disposable. Returns a refusal dict or a normalized
    record dict. The record must exist, be strict JSON with exactly the
    expected fields, flag ``disposable`` true, and name the exact target
    database (and host and port for TCP targets)."""
    record_path = env.get(DISPOSABLE_OWNERSHIP_ENV, "").strip()
    if not record_path:
        return {"refused": True, "blocked": False,
                "reason": (f"{DISPOSABLE_OWNERSHIP_ENV} is required with "
                           f"{DISPOSABLE_MARKER_ENV}=1")}
    try:
        record = json.loads(Path(record_path).read_text())
    except (OSError, json.JSONDecodeError) as exc:
        return {"refused": True, "blocked": False,
                "reason": f"disposable ownership record unreadable: {exc}"}
    if not isinstance(record, dict):
        return {"refused": True, "blocked": False,
                "reason": "disposable ownership record is not a JSON object"}
    if set(record) != set(_OWNERSHIP_FIELDS):
        return {"refused": True, "blocked": False,
                "reason": ("disposable ownership record must contain exactly "
                           f"{', '.join(_OWNERSHIP_FIELDS)}")}
    if not isinstance(record.get("disposable"), bool) or not record["disposable"]:
        return {"refused": True, "blocked": False,
                "reason": "disposable ownership record must flag disposable: true"}
    for field in ("database", "host", "port"):
        if not isinstance(record.get(field), str) or "".join(record[field].split()) == "":
            return {"refused": True, "blocked": False,
                    "reason": f"disposable ownership record field {field!r} must be a non-empty string"}
    return {"refused": False, "blocked": False, "record": record}


def verify_target(env: dict | None = None, *, require_disposable: bool = True) -> dict:
    """Verdict for the given environment (defaults to the process env).

    Returns a dict with ``ok`` plus structured details. A deterministic
    refusal sets ``ok=False`` and ``blocked=False``; an unverifiable
    cluster sets ``ok=False`` and ``blocked=True``. When there is no
    explicit target the verdict is ``ok`` (local rehearsal default),
    so non-PostgreSQL journeys are never gated.
    """
    if env is None:
        env = os.environ
    target = _collect_target(env)
    if target is None:
        return {"ok": True, "blocked": False, "target": None,
                "reason": "no PostgreSQL target; local rehearsal default"}
    if target.get("refused"):
        return {"ok": False, "blocked": False, "target": None,
                "reason": target["reason"]}
    name = target["name"]
    if name in OPERATOR_DB_NAMES:
        return {"ok": False, "blocked": False, "target": name,
                "reason": (f"target {name!r} is the operator database name; "
                           "refused for migration/cleanup")}
    if require_disposable:
        if env.get(DISPOSABLE_MARKER_ENV, "").strip() != "1":
            return {"ok": False, "blocked": False, "target": name,
                    "reason": (f"{DISPOSABLE_MARKER_ENV}=1 and a provisioning "
                               "ownership record are required before any "
                               "migrate/cleanup against an explicitly configured "
                               "PostgreSQL target")}
        record = _read_ownership_record(env)
        if record.get("refused"):
            return {"ok": False, "blocked": False, "target": name,
                    "reason": record["reason"]}
        rec = record["record"]
        if rec["database"] != name:
            return {"ok": False, "blocked": False, "target": name,
                    "reason": (f"ownership record names {rec['database']!r} but "
                               f"the target is {name!r}")}
        if rec["port"] != target["values"]["PRACE_DB_PORT"]:
            return {"ok": False, "blocked": False, "target": name,
                    "reason": f"ownership record port {rec['port']!r} != target port"}
        # Socket (peer/trust) targets store their directory path as the
        # record host; TCP targets must match exactly.
        if rec["host"] != target["values"]["PRACE_DB_HOST"]:
            return {"ok": False, "blocked": False, "target": name,
                    "reason": f"ownership record host {rec['host']!r} != target host"}
    verdict = {"ok": True, "blocked": False, "target": name,
               "disposable": bool(require_disposable)}
    try:
        key = lock_key(env)
    except ValueError as exc:
        return {"ok": False, "blocked": False, "target": name, "reason": str(exc)}
    verdict["lock_key"] = key
    lock = _try_exclusive_lock(target["values"], key)
    verdict["lock"] = lock
    if not lock.get("acquired"):
        verdict["ok"] = False
        verdict["blocked"] = True
        verdict["reason"] = lock.get("reason") or "exclusive-use lock not acquired"
    return verdict


def exclusive_cleanup_sql(operation_sql: str, *, lock_key_value: int) -> str:
    """Wrap a destructive SQL body so the advisory lock is held by the
    same session that performs it. The guard's ``verify_target`` probe
    proves the lock was available; this wrapper proves it stays held while
    the operation runs, closing the check-then-act window."""
    return (
        f"SELECT pg_advisory_lock({lock_key_value});\n"
        f"{operation_sql}\n"
        f"SELECT pg_advisory_unlock({lock_key_value});\n"
    )


def _try_exclusive_lock(values: dict, key: int) -> dict:
    """Attempt a small exclusive-use verification on the target.

    Runs ``SELECT pg_try_advisory_lock(<key>)`` through psql with
    ``ON_ERROR_STOP`` and a short connect timeout. Any failure (missing
    psql, unreachable cluster, wrong credential, lock already held) is
    reported as blocked and therefore refuses the operation.
    """
    sql = (
        "\\set ON_ERROR_STOP on\n"
        f"SELECT pg_try_advisory_lock({key});\n"
        f"SELECT pg_advisory_unlock({key});\n"
    )
    env = dict(os.environ)
    env["PGPASSWORD"] = values.get("PRACE_DB_PASSWORD", "")
    try:
        result = subprocess.run(
            [PSQL, "-h", values["PRACE_DB_HOST"], "-p", str(values["PRACE_DB_PORT"]),
             "-U", values["PRACE_DB_USER"], "-d", values["PRACE_DB_NAME"],
             "-v", "ON_ERROR_STOP=1", "-Atc", sql],
            env=env, capture_output=True, text=True, timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {"acquired": False, "reason": "exclusive-use probe could not run"}
    if result.returncode != 0:
        return {"acquired": False, "reason": (
            f"exclusive-use probe failed (rc={result.returncode}); cluster "
            "unreachable, credentials invalid or lock already held")}
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not lines or lines[0].lower() not in ("t", "true", "1"):
        return {"acquired": False, "reason": "exclusive-use lock already held"}
    return {"acquired": True, "reason": "exclusive-use lock acquired and released"}


def main() -> int:
    verdict = verify_target(require_disposable="--no-marker" not in __import__("sys").argv)
    print(f"{'ok' if verdict['ok'] else 'FAIL'}: {verdict.get('reason') or verdict}")
    return 0 if verdict["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())