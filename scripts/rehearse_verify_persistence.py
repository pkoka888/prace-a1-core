#!/usr/bin/env python3
"""Canonical Delivery-1 persistence acceptance.

Reuses the post-restart query logic from
``tests/test_rehearse_workflow.py`` so the operator and engineering
run the exact same verification: the same row pks and artifact bytes
must come back after gunicorn restart. Nothing may be replaced.

Exit codes:
  0 — every check passed
  1 — one or more rows or artifact bytes do not match the pre-restart
      identifiers supplied through the environment
  2 — configuration error (missing env, bad DB target, etc.)

This script is intentionally not a Django management command; it is
invoked directly so the operator can run it from a clean shell with
the documented env block.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import django

REQUIRED_ENV = (
    "DJANGO_SETTINGS_MODULE",
    "PRACE_RUNTIME_ROOT",
    "PRACE_SECRET_KEY",
    "ORG_PK",
    "WORKER_PK",
    "DOCUMENT_PK",
    "CASE_PK",
    "REGENERATED_CASE_PK",
    "ASSIGNMENT_PK",
    "PDF_SHA256",
    "REGEN_SHA256",
)


def _die(rc: int, *lines: str) -> None:
    for line in lines:
        print(line, file=sys.stderr)
    raise SystemExit(rc)


def _setup() -> None:
    missing = [name for name in REQUIRED_ENV if not os.environ.get(name)]
    if missing:
        _die(2, "PERSISTENCE_ACCEPTANCE_BLOCKED", f"missing env: {', '.join(missing)}")
    os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")
    try:
        django.setup()
    except Exception as exc:
        _die(2, f"PERSISTENCE_ACCEPTANCE_BLOCKED: django.setup failed: {exc}")


def _case_artifact(pk: str, expect_sha256: str) -> dict:
    from django.conf import settings
    from portal.release1a.models import A1Case

    case = A1Case.objects.filter(
        pk=int(pk), organization_id=int(os.environ["ORG_PK"])
    ).first()
    if case is None:
        return {"found": False}
    ref = case.artifact_reference or {}
    key = ref.get("key")
    if not key:
        return {"found": True, "key": None, "file_exists": False}
    pdf = Path(settings.DOCUMENT_STORAGE_ROOT) / "j4" / key / "artifact.pdf"
    file_exists = pdf.is_file()
    sha256_matches = False
    if file_exists:
        sha256_matches = (
            hashlib.sha256(pdf.read_bytes()).hexdigest() == expect_sha256
        )
    return {
        "found": True,
        "key": key,
        "file_exists": file_exists,
        "sha256_matches": sha256_matches,
    }


def main() -> int:
    _setup()
    from portal.release1a.models import Worker, Document, Assignment, A1Case

    org_pk = int(os.environ["ORG_PK"])
    worker_pk = int(os.environ["WORKER_PK"])
    document_pk = int(os.environ["DOCUMENT_PK"])
    assignment_pk = int(os.environ["ASSIGNMENT_PK"])
    case_pk = int(os.environ["CASE_PK"])
    regen_pk = int(os.environ["REGENERATED_CASE_PK"])
    pdf_sha256 = os.environ["PDF_SHA256"]
    regen_sha256 = os.environ["REGEN_SHA256"]

    checks = {
        "worker_found": Worker.objects.filter(pk=worker_pk).exists(),
        "document_found": Document.objects.filter(pk=document_pk).exists(),
        "assignment_found": Assignment.objects.filter(pk=assignment_pk).exists(),
        "case_found": A1Case.objects.filter(pk=case_pk).exists(),
        "regenerated_case_found": A1Case.objects.filter(pk=regen_pk).exists(),
        "original_artifact": _case_artifact(case_pk, pdf_sha256),
        "regenerated_artifact": _case_artifact(regen_pk, regen_sha256),
    }

    failed = False
    for key, value in checks.items():
        if key in ("original_artifact", "regenerated_artifact"):
            art = value if isinstance(value, dict) else {}
            if not art.get("file_exists"):
                print(f"FAIL {key}: artifact file missing", file=sys.stderr)
                failed = True
            elif not art.get("sha256_matches"):
                print(
                    f"FAIL {key}: sha256 mismatch (got {art.get('key')})",
                    file=sys.stderr,
                )
                failed = True
            else:
                print(f"ok  {key}: key={art.get('key')} sha256=matched")
        else:
            if not value:
                print(f"FAIL {key}: row missing", file=sys.stderr)
                failed = True
            else:
                print(f"ok  {key}")

    if failed:
        print(json.dumps({"ok": False, "checks": checks}, ensure_ascii=False))
        return 1

    print(json.dumps({"ok": True, "checks": checks}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
