#!/usr/bin/env python3
"""Canonical Delivery-1 persistence acceptance.

Reuses the post-restart query logic from
``tests/test_rehearse_workflow.py`` so the operator and engineering
run the exact same verification: the same row pks and artifact bytes
must come back after gunicorn restart. Nothing may be replaced.

Profiles:
  core        — worker, document, assignment and their relationships;
                A1 identifiers are not required.
  optional-a1 — additionally verifies A1 case rows and artifact bytes.

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

import argparse
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
    "ASSIGNMENT_PK",
    "DOCUMENT_SHA256",
)

# When JOURNEY_EVIDENCE_PATH is set, the verifier reads the pre-restart
# identifiers and artifact hashes from the saved journey evidence file
# instead of (or in addition to) the environment. This lets the operator
# run the canonical persistence acceptance directly from a saved
# committed-source journey without re-authoring every identifier by hand.
JOURNEY_EVIDENCE_PATH_ENV = "JOURNEY_EVIDENCE_PATH"

# A1 identifiers and artifact hashes are required only for optional-a1.
A1_REQUIRED_ENV = (
    "CASE_PK",
    "REGENERATED_CASE_PK",
    "PDF_SHA256",
    "REGEN_SHA256",
)


def _die(rc: int, *lines: str) -> None:
    for line in lines:
        print(line, file=sys.stderr)
    raise SystemExit(rc)


def _load_from_journey_evidence() -> dict:
    """Read pre-restart identifiers and artifact hashes from a saved
    journey evidence JSON file. Only fills values that are missing from
    the environment; explicit env vars take precedence. Returns the
    populated values so the caller can assert that required identities
    were actually sourced.
    """
    path_str = os.environ.get(JOURNEY_EVIDENCE_PATH_ENV)
    if not path_str:
        return {}
    try:
        evidence = json.loads(Path(path_str).read_text())
    except (OSError, json.JSONDecodeError) as exc:
        _die(2, "PERSISTENCE_ACCEPTANCE_BLOCKED",
             f"JOURNEY_EVIDENCE_PATH={path_str} unreadable: {exc}")
    if not isinstance(evidence, dict):
        _die(2, "PERSISTENCE_ACCEPTANCE_BLOCKED",
             f"JOURNEY_EVIDENCE_PATH={path_str} is not a JSON object")
    return evidence


def _setup(profile: str = "core") -> None:
    # Allow journey evidence file to supply identifiers that are not
    # already set in the environment.
    evidence = _load_from_journey_evidence()
    for env_name, evidence_key in (
        ("ORG_PK", "organization_id"),
        ("WORKER_PK", "worker_pk"),
        ("DOCUMENT_PK", "document_pk"),
        ("ASSIGNMENT_PK", "assignment_pk"),
        ("DOCUMENT_SHA256", "source_document_sha256"),
    ):
        if not os.environ.get(env_name) and evidence_key in evidence:
            os.environ[env_name] = str(evidence[evidence_key])
    if profile == "optional-a1":
        for env_name, evidence_key in (
            ("CASE_PK", "case_pk"),
            ("REGENERATED_CASE_PK", "regenerated_case_pk"),
            ("PDF_SHA256", "pdf_sha256"),
            ("REGEN_SHA256", "regen_sha256"),
        ):
            if not os.environ.get(env_name) and evidence_key in evidence:
                os.environ[env_name] = str(evidence[evidence_key])

    missing = [name for name in REQUIRED_ENV if not os.environ.get(name)]
    if missing:
        _die(2, "PERSISTENCE_ACCEPTANCE_BLOCKED", f"missing env: {', '.join(missing)}")
    if profile == "optional-a1":
        a1_missing = [name for name in A1_REQUIRED_ENV if not os.environ.get(name)]
        if a1_missing:
            _die(2, "PERSISTENCE_ACCEPTANCE_BLOCKED",
                 f"optional-a1 profile requires: {', '.join(a1_missing)}")
    os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")
    try:
        django.setup()
    except Exception as exc:
        _die(2, f"PERSISTENCE_ACCEPTANCE_BLOCKED: django.setup failed: {exc}")


def _case_artifact(pk: str, expect_sha256: str, org_pk: int) -> dict:
    from django.conf import settings
    from portal.release1a.models import A1Case

    case = A1Case.objects.filter(
        pk=int(pk), organization_id=org_pk
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


def _worker_document_relationship(worker_pk: int, document_pk: int, org_pk: int) -> dict:
    from portal.release1a.models import Worker, Document

    worker = Worker.objects.filter(pk=worker_pk, organization_id=org_pk).first()
    document = Document.objects.filter(pk=document_pk, organization_id=org_pk).first()
    if worker is None or document is None:
        return {"ok": False, "reason": "worker or document not found in org"}
    linked = document.worker_id == worker_pk
    return {"ok": linked, "worker_pk": worker_pk, "document_pk": document_pk,
            "document_worker_id": document.worker_id}


def _worker_assignment_relationship(worker_pk: int, assignment_pk: int, org_pk: int) -> dict:
    from portal.release1a.models import Worker, Assignment

    worker = Worker.objects.filter(pk=worker_pk, organization_id=org_pk).first()
    assignment = Assignment.objects.filter(pk=assignment_pk, organization_id=org_pk).first()
    if worker is None or assignment is None:
        return {"ok": False, "reason": "worker or assignment not found in org"}
    linked = assignment.worker_id == worker_pk
    return {"ok": linked, "worker_pk": worker_pk, "assignment_pk": assignment_pk,
            "assignment_worker_id": assignment.worker_id}


def _document_worker_sha256(document_pk: int, org_pk: int, expected_sha256: str | None = None) -> dict:
    from portal.release1a.models import Document

    document = Document.objects.filter(pk=document_pk, organization_id=org_pk).first()
    if document is None:
        return {"ok": False, "reason": "document not found in org"}
    actual = document.sha256
    if expected_sha256 is not None:
        matches = actual == expected_sha256
        return {"ok": matches, "actual_sha256": actual, "expected_sha256": expected_sha256,
                "matches": matches}
    return {"ok": True, "actual_sha256": actual}


def main() -> int:
    parser = argparse.ArgumentParser(description="Canonical Delivery-1 persistence acceptance")
    parser.add_argument(
        "--profile",
        choices=["core", "optional-a1"],
        default="core",
        help="Acceptance profile: 'core' covers worker/document/assignment; "
             "'optional-a1' additionally requires A1 identifiers (default: core)",
    )
    args = parser.parse_args()
    profile = args.profile

    _setup(profile=profile)
    from portal.release1a.models import Worker, Document, Assignment, A1Case

    org_pk = int(os.environ["ORG_PK"])
    worker_pk = int(os.environ["WORKER_PK"])
    document_pk = int(os.environ["DOCUMENT_PK"])
    assignment_pk = int(os.environ["ASSIGNMENT_PK"])
    document_sha256 = os.environ["DOCUMENT_SHA256"]

    case_pk = os.environ.get("CASE_PK")
    regen_pk = os.environ.get("REGENERATED_CASE_PK")
    pdf_sha256 = os.environ.get("PDF_SHA256")
    regen_sha256 = os.environ.get("REGEN_SHA256")

    checks = {
        "worker_found": Worker.objects.filter(pk=worker_pk, organization_id=org_pk).exists(),
        "document_found": Document.objects.filter(pk=document_pk, organization_id=org_pk).exists(),
        "assignment_found": Assignment.objects.filter(pk=assignment_pk, organization_id=org_pk).exists(),
        "worker_document_relationship": _worker_document_relationship(worker_pk, document_pk, org_pk),
        "worker_assignment_relationship": _worker_assignment_relationship(worker_pk, assignment_pk, org_pk),
        "document_sha256": _document_worker_sha256(document_pk, org_pk, document_sha256),
    }

    if profile == "optional-a1":
        if not case_pk or not regen_pk or not pdf_sha256 or not regen_sha256:
            _die(2, "PERSISTENCE_ACCEPTANCE_BLOCKED",
                 "optional-a1 profile requires CASE_PK, REGENERATED_CASE_PK, PDF_SHA256, REGEN_SHA256")
        checks["case_found"] = A1Case.objects.filter(pk=int(case_pk), organization_id=org_pk).exists()
        checks["regenerated_case_found"] = A1Case.objects.filter(pk=int(regen_pk), organization_id=org_pk).exists()
        checks["original_artifact"] = _case_artifact(case_pk, pdf_sha256, org_pk)
        checks["regenerated_artifact"] = _case_artifact(regen_pk, regen_sha256, org_pk)

    failed = False
    for key, value in checks.items():
        if key in ("original_artifact", "regenerated_artifact"):
            art = value if isinstance(value, dict) else {}
            if not art.get("found"):
                print(f"FAIL {key}: case row missing in org", file=sys.stderr)
                failed = True
            elif not art.get("file_exists"):
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
        elif key in ("worker_document_relationship", "worker_assignment_relationship",
                     "document_sha256"):
            rel = value if isinstance(value, dict) else {}
            if not rel.get("ok"):
                print(f"FAIL {key}: {rel.get('reason', 'check failed')}",
                      file=sys.stderr)
                failed = True
            else:
                if key == "document_sha256":
                    matches = rel.get("matches")
                    if matches is False:
                        print(f"FAIL {key}: sha256 mismatch (actual={rel.get('actual_sha256')}, expected={rel.get('expected_sha256')})",
                              file=sys.stderr)
                        failed = True
                    else:
                        print(f"ok  {key}: sha256={rel.get('actual_sha256')} matched")
                else:
                    detail = " ".join(f"{k}={v}" for k, v in rel.items() if k != "ok")
                    print(f"ok  {key}: {detail}")
        else:
            if not value:
                print(f"FAIL {key}: row missing in org", file=sys.stderr)
                failed = True
            else:
                print(f"ok  {key}")

    if failed:
        print(json.dumps({"ok": False, "profile": profile, "checks": checks}, ensure_ascii=False))
        return 1

    print(json.dumps({"ok": True, "profile": profile, "checks": checks}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
