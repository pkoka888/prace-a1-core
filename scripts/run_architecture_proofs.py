#!/usr/bin/env python3
"""Fail-closed, synthetic-only Plan E proof runner and evidence verifier."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

from jsonschema import Draft7Validator

ROOT = Path(__file__).resolve().parent.parent
EXIT_OK, EXIT_FAILURE, EXIT_UNPROVEN = 0, 1, 2
PROTECTED_PARTS = {"a1", "scans", "evidence", "ocr", "data", "employees", "output", "runtime", "secrets", ".env"}
EVIDENCE_DIR = Path("docs/architecture/adr-001-evidence")
CHECKS = {
    "E-MFA": "tests/architecture/test_mfa_proof.py",
    "E-TENANT": "tests/architecture/test_tenant_isolation.py",
    "E-JOBS": "tests/architecture/test_job_recovery.py tests/architecture/test_transactions.py",
    "E-STORAGE": "tests/architecture/test_protected_storage.py",
    "E-AUDIT": "tests/architecture/test_audit_contract.py",
    "E-A1": "tests/architecture/test_a1_boundary.py",
    "E-DEPS": "tests/architecture/test_rollback.py",
    "E-ROLLBACK": "tests/architecture/test_rollback.py tests/architecture/test_job_recovery.py",
}


def synthetic_upload_samples(limit: int = 4096) -> dict[str, bytes]:
    valid_pdf = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\n%%EOF\n"
    valid_png = b"\x89PNG\r\n\x1a\n" + b"SYNTHETIC-PNG"
    return {
        "valid.pdf": valid_pdf,
        "valid.png": valid_png,
        "mime-mismatch.pdf": b"MZ-SYNTHETIC-EXECUTABLE",
        "disguised-image.png": b"#!/bin/sh\nexit 0\n",
        "duplicate-a.pdf": valid_pdf,
        "duplicate-b.pdf": valid_pdf,
        "oversize.pdf": b"%PDF-1.4\n" + (b"X" * limit),
    }


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def preflight(root: Path) -> tuple[dict, int]:
    fixture_dir = root / "tests/fixtures/release_1a"
    manifest_path = fixture_dir / "manifest.json"
    schema_path = fixture_dir / "fixture.schema.json"
    errors: list[str] = []
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"status": "unproven", "errors": [f"fixture contract unavailable: {exc.__class__.__name__}"]}, EXIT_UNPROVEN
    declared = manifest.get("fixture_files", [])
    actual = sorted(p.name for p in fixture_dir.glob("*.json") if p.name not in {"manifest.json", "fixture.schema.json"})
    if sorted(declared) != actual:
        errors.append("declared fixture set does not match JSON files")
    records: dict[str, list[dict]] = {}
    for name in declared:
        path = fixture_dir / name
        if path.is_symlink() or not path.is_file() or path.parent.resolve() != fixture_dir.resolve():
            errors.append(f"unsafe fixture path: {name}")
            continue
        if any(part in PROTECTED_PARTS for part in Path(name).parts):
            errors.append(f"protected path in fixture declaration: {name}")
        if _sha(path) != manifest.get("fixture_hashes", {}).get(name):
            errors.append(f"hash mismatch: {name}")
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            errors.append(f"invalid JSON: {name}")
            continue
        schema_errors = sorted(Draft7Validator(schema).iter_errors(value), key=lambda e: list(e.path))
        errors.extend(f"schema {name}: {error.message}" for error in schema_errors)
        if any(not row.get("_fiction") for row in value if isinstance(row, dict)):
            errors.append(f"missing fiction marker: {name}")
        records[name] = value
    orgs = {row["id"] for row in records.get("organizations.json", [])}
    users = {row["id"] for row in records.get("users.json", [])}
    workers = {row["id"] for row in records.get("workers.json", [])}
    for name in ("users.json", "workers.json", "documents.json", "assignments.json", "jobs.json", "a1_inputs.json"):
        for row in records.get(name, []):
            if row.get("organization_id") not in orgs:
                errors.append(f"unknown organization reference: {name}")
    for name in ("documents.json", "assignments.json"):
        for row in records.get(name, []):
            if row.get("worker_id") not in workers:
                errors.append(f"unknown worker reference: {name}")
    for row in records.get("documents.json", []):
        if row.get("confirmed_by") and row["confirmed_by"] not in users:
            errors.append("unknown document confirmer")
    if any(not row.get("email", "").endswith("@example.invalid") for row in records.get("users.json", [])):
        errors.append("non-synthetic email domain")
    expected = manifest.get("expected_counts", {})
    for name, count in expected.items():
        if len(records.get(name, [])) != count:
            errors.append(f"unexpected fixture count: {name}")
    samples = synthetic_upload_samples()
    if samples["duplicate-a.pdf"] != samples["duplicate-b.pdf"] or len(samples["oversize.pdf"]) <= 4096:
        errors.append("synthetic upload sample contract failed")
    status = "pass" if not errors else "failed"
    return {"status": status, "fixture_set": manifest.get("fixture_set"), "files": len(declared), "errors": errors}, EXIT_OK if not errors else EXIT_FAILURE


def _safe_relative(root: Path, value: Path) -> Path:
    resolved = (root / value).resolve()
    allowed = (root / EVIDENCE_DIR).resolve()
    if resolved != allowed or any(part in PROTECTED_PARTS for part in value.parts):
        raise ValueError("evidence output must be the declared tracked synthetic directory")
    return resolved


def run_proofs(root: Path, candidate: str) -> tuple[dict, int]:
    if candidate != "all":
        return {"status": "unproven", "errors": ["candidate must be exactly 'all'"]}, EXIT_UNPROVEN
    ready, code = preflight(root)
    if code:
        return ready, code
    evidence_dir = _safe_relative(root, EVIDENCE_DIR)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for check_id, paths in CHECKS.items():
        command = [str(root / "venv/bin/python"), "-m", "pytest", *paths.split(), "-q"]
        started = time.monotonic()
        completed = subprocess.run(command, cwd=root, text=True, capture_output=True, timeout=120)
        duration_ms = round((time.monotonic() - started) * 1000, 3)
        output = (completed.stdout + completed.stderr).strip()
        results.append({"id": check_id, "status": "passed" if completed.returncode == 0 else "failed",
                        "command": "venv/bin/python -m pytest " + paths + " -q", "duration_ms": duration_ms,
                        "output_sha256": hashlib.sha256(output.encode()).hexdigest()})
    source_paths = [Path(p) for p in sorted(set(" ".join(CHECKS.values()).split()))]
    source_paths += [Path("prototypes/architecture/adr001/proof_contract.py"), Path("requirements.txt"), Path("tests/fixtures/release_1a/manifest.json")]
    manifest = {
        "schema_version": "1.0", "evidence_kind": "synthetic-architecture-proof", "candidate": candidate,
        "environment": {"python": platform.python_version(), "platform": platform.platform(), "machine": platform.machine()},
        "source_hashes": {str(path): _sha(root / path) for path in source_paths},
        "checks": results,
        "disposition": "passed" if all(r["status"] == "passed" for r in results) else "failed",
    }
    manifest_path = evidence_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    receipt = {"manifest_sha256": _sha(manifest_path), "checks": {r["id"]: r["status"] for r in results}}
    (evidence_dir / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    status = manifest["disposition"]
    return {"status": status, "manifest": str(manifest_path.relative_to(root)), "manifest_sha256": receipt["manifest_sha256"], "checks": receipt["checks"]}, EXIT_OK if status == "passed" else EXIT_FAILURE


def verify(root: Path, manifest_arg: Path) -> tuple[dict, int]:
    expected = (root / EVIDENCE_DIR / "manifest.json").resolve()
    manifest_path = (root / manifest_arg).resolve() if not manifest_arg.is_absolute() else manifest_arg.resolve()
    if manifest_path != expected:
        return {"status": "unproven", "errors": ["only the declared manifest may be verified"]}, EXIT_UNPROVEN
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        receipt = json.loads((manifest_path.parent / "receipt.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"status": "unproven", "errors": [f"evidence unavailable: {exc.__class__.__name__}"]}, EXIT_UNPROVEN
    errors = []
    if receipt.get("manifest_sha256") != _sha(manifest_path): errors.append("manifest hash mismatch")
    for path, digest in manifest.get("source_hashes", {}).items():
        candidate = (root / path).resolve()
        if not candidate.is_file() or not candidate.is_relative_to(root.resolve()) or _sha(candidate) != digest:
            errors.append(f"source hash mismatch: {path}")
    checks = manifest.get("checks", [])
    if {c.get("id") for c in checks} != set(CHECKS): errors.append("required check set mismatch")
    if any(c.get("status") != "passed" for c in checks): errors.append("one or more checks did not pass")
    status = "pass" if not errors else "failed"
    return {"status": status, "manifest_sha256": _sha(manifest_path), "checks": len(checks), "errors": errors}, EXIT_OK if not errors else EXIT_FAILURE


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("preflight", "run", "verify"))
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--candidate", default="all")
    parser.add_argument("--manifest", type=Path, default=EVIDENCE_DIR / "manifest.json")
    parser.add_argument("--json", action="store_true")
    args, _ = parser.parse_known_args()
    if args.command == "preflight":
        result, code = preflight(args.root.resolve())
    elif args.command == "run":
        result, code = run_proofs(args.root.resolve(), args.candidate)
    else:
        result, code = verify(args.root.resolve(), args.manifest)
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else result["status"])
    return code


if __name__ == "__main__":
    sys.exit(main())
