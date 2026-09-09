#!/usr/bin/env python3
"""Prepare and validate A1 candidates; reserved final publication requires receipts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pypdf import PdfReader

try:
    from .a1_core import A1ValidationError, build_form_data, czech_display_case, enrich_residence, generate_a1_pdf
    from .a1_paths import PathValidationError, validate_output_path, unique_staging_path, cleanup_staging_only, protected_path, destination_lock, publish_package
    from .a1_audit import AuditWriteError, audited, audited_operation, current_run_id, write_failure_receipt, write_private_json
    from .a1_private import A1PrivateInputError, private_path, private_root
except ImportError:  # Direct CLI execution.
    from a1_core import A1ValidationError, build_form_data, czech_display_case, enrich_residence, generate_a1_pdf
    from a1_paths import PathValidationError, validate_output_path, unique_staging_path, cleanup_staging_only, protected_path, destination_lock, publish_package
    from a1_audit import AuditWriteError, audited, audited_operation, current_run_id, write_failure_receipt, write_private_json
    from a1_private import A1PrivateInputError, private_path, private_root


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REVIEW = None
YES = "YES"
PROFILE_BY_OSSZ = {
    "OSSZ Plzeň": "plzen",
    "OSSZ Teplice": "teplice",
    "OSSZ Most": "most",
    "OSSZ Louny": "louny",
        "OSSZ Frýdek-Místek": "frydek-mistek",
    "OSSZ Nový Jičín": "novy-jicin",
    "OSSZ Praha": "praha",
    "OSSZ Brno": "brno",
}
CSV_FIELDS = (
    "employee_id", "source_scans", "surname", "given_name", "dob", "birth_place",
    "nationality", "sex", "insurance_number", "street", "house_number", "city",
    "district", "postal_code", "country_code", "status_profile", "activity_name",
    "activity_address", "employment_id", "employment_name", "employment_street",
    "employment_house_number", "employment_city", "employment_postal_code",
    "employment_country_code", "resolved_ossz", "institution_profile", "document_id",
    "start_date", "end_date", "issue_date", "signed_by", "identity_reviewed",
    "certificate_reviewed", "approved_for_pdf", "pdf_created", "validated_by_user",
    "activity_source", "activity_source_status", "certificate_source",
    "certificate_source_status", "signatory_source", "signatory_source_status",
    "comments",
)
PROFILE_FIELDS = ("name", "street", "house_number", "city", "postal_code", "country_code", "code")
AUTHORITATIVE = "AUTHORITATIVE"
UNVERIFIED_SOURCE_MARKERS = ("assum", "copied", "assigned", "example", "placeholder", "template")


class FinalizationError(ValueError):
    """Raised when review data is not safe to publish."""




def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise FinalizationError("JSON_OBJECT_REQUIRED")
    return value


def _date(value: str, field: str) -> str:
    try:
        parsed = datetime.strptime(value.strip(), "%d.%m.%Y")
    except ValueError as exc:
        raise FinalizationError(f"{field} must use DD.MM.YYYY: {value!r}") from exc
    return parsed.strftime("%d.%m.%Y")


def _slug(value: str) -> str:
    if not re.fullmatch(r"[a-z0-9-]+", value or ""):
        raise FinalizationError(f"unsafe identifier: {value!r}")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def prepare_review(
    employees_path: Path,
    enrichment_path: Path,
    current_institution_path: Path,
    output_path: Path,
) -> None:
    employees = load_json(employees_path).get("employees", [])
    enrichment = load_json(enrichment_path)
    current = load_json(current_institution_path)
    rows: list[dict[str, str]] = []
    for source in employees:
        employee = dict(source)
        residence, _ = enrich_residence(employee.get("residence", {}), enrichment)
        person = employee.get("person", {})
        resolved = residence.get("ossz", "")
        is_teplice = resolved == "OSSZ Teplice"
        row = {field: "" for field in CSV_FIELDS}
        row.update(
            {
                "employee_id": employee.get("id", ""),
                "source_scans": ";".join(employee.get("provenance", {}).get("scans", [])),
                "surname": person.get("surname", ""),
                "given_name": person.get("given_name", ""),
                "dob": person.get("dob", ""),
                "birth_place": person.get("birth_place", ""),
                "nationality": person.get("nationality", ""),
                "sex": person.get("sex", ""),
                "insurance_number": person.get("insurance_number", ""),
                "street": residence.get("street", ""),
                "house_number": residence.get("house_number", ""),
                "city": residence.get("city", ""),
                "district": residence.get("district", ""),
                "postal_code": residence.get("postal_code", ""),
                "country_code": residence.get("country_code", ""),
                "status_profile": employee.get("a1", {}).get("status_profile", ""),
                "resolved_ossz": resolved,
                "institution_profile": PROFILE_BY_OSSZ.get(resolved, ""),
                "start_date": current.get("certificate", {}).get("start_date", "") if is_teplice else "",
                "end_date": current.get("certificate", {}).get("end_date", "") if is_teplice else "",
                "issue_date": current.get("issue_date", "") if is_teplice else "",
                "signed_by": current.get("signed_by", "") if is_teplice else "",
                "identity_reviewed": "NO",
                "certificate_reviewed": "NO",
                "approved_for_pdf": "NO",
                "pdf_created": "",
                "validated_by_user": "0",
                "activity_source_status": "UNVERIFIED",
                "certificate_source_status": "UNVERIFIED",
                "signatory_source_status": "UNVERIFIED",
                "comments": "REVIEW REQUIRED: add activity and unique document ID",
            }
        )
        rows.append(row)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    output_path.chmod(0o600)


def read_review(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        missing = [field for field in CSV_FIELDS if field not in (reader.fieldnames or [])]
        if missing:
            raise FinalizationError("review CSV is missing columns: " + ", ".join(missing))
        if len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise FinalizationError("review CSV has duplicate columns")
        rows = []
        for index, row in enumerate(reader, start=2):
            if None in row or any(value is None for value in row.values()):
                raise FinalizationError(f"review CSV row {index}: field count differs from header")
            rows.append({key: value.strip() for key, value in row.items()})
        if not rows:
            raise FinalizationError("review CSV contains no records")
        ids = [row["employee_id"] for row in rows]
        if len(ids) != len(set(ids)):
            raise FinalizationError("employee_id values must be unique")
        for value in ids:
            _slug(value)
        return rows


def _required_review_fields(status: str, *, provisional: bool) -> tuple[str, ...]:
    """One CSV presence contract for validation and its readiness preflight."""
    common = (
        "surname", "given_name", "dob", "birth_place", "nationality", "sex",
        "insurance_number", "street", "house_number", "city", "postal_code", "country_code",
        "status_profile", "employment_id", "employment_name",
        "employment_street", "employment_house_number", "employment_city", "employment_postal_code",
        "employment_country_code", "resolved_ossz", "institution_profile", "document_id",
        "issue_date",
    )
    # Section 5.1 is intentionally blank on provisional self-employed copies.
    activity = (("activity_address",) if provisional and status == "self_employed_multi_state"
                else ("activity_name", "activity_address"))
    certificate = () if provisional else ("start_date", "end_date", "signed_by")
    return (*common, *activity, *certificate)


def readiness_report(
    rows: list[dict[str, str]], profile_dir: Path | None = None, *, provisional: bool = False,
) -> dict[str, Any]:
    """Sanitized, mode-aware review preflight; not generation or artifact approval."""
    report_rows = []
    for index, row in enumerate(rows, 1):
        status = row.get("status_profile", "")
        required_values = _required_review_fields(status, provisional=provisional)
        blockers = [f"missing {field}" for field in required_values if not row.get(field)]
        for subject in (() if provisional else ("activity", "certificate", "signatory")):
            source = row.get(f"{subject}_source", "")
            if not source:
                blockers.append(f"missing {subject}_source")
            elif any(marker in source.casefold() for marker in UNVERIFIED_SOURCE_MARKERS):
                blockers.append(f"placeholder detected in {subject}_source")
            if row.get(f"{subject}_source_status") != AUTHORITATIVE:
                blockers.append(f"{subject}_source_status is not AUTHORITATIVE")
        for flag, expected in (("identity_reviewed", YES), ("certificate_reviewed", YES),
                               ("approved_for_pdf", YES), ("validated_by_user", "1")):
            if row.get(flag) != expected:
                blockers.append(f"{flag} must be {expected}")
        if status not in {"self_employed_multi_state", "employee_multi_state", "posted_employee"}:
            blockers.append("unsupported status_profile")
        if status in {"employee_multi_state", "posted_employee"} and "osvč" in row.get("employment_name", "").casefold():
            blockers.append("employee profile has self-employed employer data")
        dates = {}
        for field in ("dob", "start_date", "end_date", "issue_date"):
            if row.get(field):
                try:
                    dates[field] = datetime.strptime(row[field], "%d.%m.%Y")
                except ValueError:
                    blockers.append(f"invalid {field}")
        if dates.get("start_date") and dates.get("end_date") and dates["start_date"] > dates["end_date"]:
            blockers.append("start_date is after end_date")
        for field in ("employee_id", "document_id"):
            if row.get(field) and sum(other.get(field) == row[field] for other in rows) > 1:
                blockers.append(f"duplicate {field}")
        if profile_dir is not None and row.get("institution_profile"):
            try:
                profile = load_profile(profile_dir, row["institution_profile"], provisional=provisional)
                if not provisional and profile.get("expected_ossz", "").casefold() != row.get("resolved_ossz", "").casefold():
                    blockers.append("institution_profile does not match resolved_ossz")
            except (FinalizationError, OSError, ValueError):
                blockers.append("institution_profile is missing, unverified or contains placeholder fields")
        report_rows.append({"row_index": index, "blockers": blockers})
    return {"mode": "provisional" if provisional else "authoritative",
            "scope": "review_preflight",
            "ready": bool(rows) and all(not r["blockers"] for r in report_rows),
            "employee_count": len(rows), "blocked_employee_count": sum(bool(r["blockers"]) for r in report_rows),
            "employees": report_rows}


def readiness_receipt_path(requested: Path | None) -> Path:
    root = private_root().resolve()
    try:
        target = protected_path(requested or root / "a1/blocked-rows.json", ("a1", "evidence"))
    except PathValidationError as exc:
        raise FinalizationError("READINESS_DESTINATION_INVALID") from exc
    if (target.suffix != ".json" or target.name in {"cohort.json", "employees_normalized.json", "operator.json"}
            or any(target.is_relative_to(root / "a1" / name) for name in ("audit", "receipts", "locks"))
            or not any(target.is_relative_to(root / name) for name in ("a1", "evidence"))):
        raise FinalizationError("readiness receipt requires a protected non-input JSON destination")
    return target



def load_profile(profile_dir: Path, profile_id: str, provisional: bool = False) -> dict[str, Any]:
    profile = load_json(profile_dir / f"{_slug(profile_id)}.json")
    if profile.get("review_status") != "VERIFIED":
        raise FinalizationError(f"institution profile {profile_id!r} is not VERIFIED")
    if not profile.get("source_url") or not profile.get("verified_on"):
        raise FinalizationError(
            f"institution profile {profile_id!r} needs source_url and verified_on provenance"
        )
    _date(profile["verified_on"], f"institution profile {profile_id}.verified_on")
    institution = profile.get("institution", {})
    missing = [field for field in PROFILE_FIELDS if not institution.get(field)]
    if missing:
        raise FinalizationError(
            f"institution profile {profile_id!r} is missing: {', '.join(missing)}"
        )
    if not provisional:
        markers = (*UNVERIFIED_SOURCE_MARKERS, "tbd", "doplnit")
        invalid = [field for field in PROFILE_FIELDS
                   if any(marker in str(institution.get(field, "")).casefold() for marker in markers)]
        if invalid:
            raise FinalizationError("institution profile contains placeholder fields: " + ", ".join(invalid))
    return profile


def _require_authoritative_source(row: dict[str, str], subject: str) -> None:
    source = row.get(f"{subject}_source", "").strip()
    status = row.get(f"{subject}_source_status", "").strip()
    if status != AUTHORITATIVE:
        raise FinalizationError(f"{row['employee_id']}: {subject}_source_status must be AUTHORITATIVE")
    if not source:
        raise FinalizationError(f"{row['employee_id']}: {subject}_source is required")
    lowered = source.casefold()
    if any(marker in lowered for marker in UNVERIFIED_SOURCE_MARKERS):
        raise FinalizationError(
            f"{row['employee_id']}: {subject}_source describes an assumption, not an authority"
        )


def _birth_number_matches_dob(value: str, dob: str, sex: str) -> bool:
    """Validate the date-bearing prefix of a Czech/Slovak birth number.

    This intentionally does not claim checksum validity. Female month offsets of
    50 are accepted; newer capacity offsets are outside the current cohort and
    must be added only with an authoritative rule and tests.
    """
    digits = re.sub(r"\D", "", value)
    if len(digits) < 6:
        return False
    born = datetime.strptime(dob, "%d.%m.%Y")
    expected_month = born.month + (50 if sex == "F" else 0)
    return digits[:6] == f"{born.year % 100:02d}{expected_month:02d}{born.day:02d}"


def validate_review(
    rows: list[dict[str, str]], employees_path: Path, profile_dir: Path,
    provisional: bool = False,
) -> list[tuple[dict[str, str], dict[str, Any]]]:
    source_employees = load_json(employees_path).get("employees", [])
    expected_by_id = {item["id"]: item for item in source_employees}
    if not rows or not source_employees:
        raise FinalizationError("review and normalized source must not be empty")
    if len(expected_by_id) != len(source_employees):
        raise FinalizationError("normalized source employee_id values must be unique")
    expected = set(expected_by_id)
    ids = [row.get("employee_id", "") for row in rows]
    if len(ids) != len(set(ids)):
        raise FinalizationError("employee_id values must be unique")
    if set(ids) != expected:
        raise FinalizationError(
            f"review CSV employee set differs from source; expected {sorted(expected)}, got {sorted(ids)}"
        )
    document_ids = [row.get("document_id", "") for row in rows]
    if any(not value for value in document_ids) or len(document_ids) != len(set(document_ids)):
        raise FinalizationError("every employee needs a non-empty, unique document_id")

    validated: list[tuple[dict[str, str], dict[str, Any]]] = []
    for row in rows:
        employee_id = _slug(row["employee_id"])
        status = row.get("status_profile", "")
        required = _required_review_fields(status, provisional=provisional)
        missing = [field for field in required if not row.get(field)]
        if missing:
            raise FinalizationError(f"{employee_id}: missing required values: {', '.join(missing)}")
        for flag in ("identity_reviewed", "certificate_reviewed", "approved_for_pdf"):
            if row.get(flag) != YES:
                raise FinalizationError(f"{employee_id}: {flag} must be YES")
        if row.get("validated_by_user") != "1":
            raise FinalizationError(f"{employee_id}: validated_by_user must be 1")
        if not provisional:
            for subject in ("activity", "certificate", "signatory"):
                _require_authoritative_source(row, subject)
            source_employee = expected_by_id[employee_id]
            source_values = {
                **{field: source_employee.get("person", {}).get(field, "") for field in (
                    "surname", "given_name", "dob", "birth_place", "nationality",
                    "sex", "insurance_number",
                )},
                **{field: source_employee.get("residence", {}).get(field, "") for field in (
                    "street", "house_number", "city", "district", "country_code",
                )},
            }
            mismatched = [
                field for field, value in source_values.items()
                if value and row.get(field, "").casefold() != str(value).strip().casefold()
            ]
            expected_scans = set(source_employee.get("provenance", {}).get("scans", []))
            reviewed_scans = {item.strip() for item in row.get("source_scans", "").split(";") if item.strip()}
            if mismatched or reviewed_scans != expected_scans:
                details = ", ".join(mismatched) if mismatched else "source_scans"
                raise FinalizationError(
                    f"{employee_id}: reviewed identity/residence differs from normalized scan source: {details}"
                )
        if row["sex"] not in {"M", "F"}:
            raise FinalizationError(f"{employee_id}: sex must be M or F")
        if row["status_profile"] not in {"self_employed_multi_state", "employee_multi_state", "posted_employee"}:
            raise FinalizationError(f"{employee_id}: unsupported status_profile")
        if row["status_profile"] in {"employee_multi_state", "posted_employee"}:
            if "osvč" in row["employment_name"].casefold():
                raise FinalizationError("employee profile has self-employed employer data")
        dob = _date(row["dob"], f"{employee_id}.dob")
        if not provisional:
            start = _date(row["start_date"], f"{employee_id}.start_date")
            end = _date(row["end_date"], f"{employee_id}.end_date")
            issue = _date(row["issue_date"], f"{employee_id}.issue_date")
            if datetime.strptime(start, "%d.%m.%Y") > datetime.strptime(end, "%d.%m.%Y"):
                raise FinalizationError(f"{employee_id}: start_date is after end_date")
            if not _birth_number_matches_dob(row["insurance_number"], dob, row["sex"]):
                raise FinalizationError(f"{employee_id}: insurance_number does not match dob")

        profile = load_profile(profile_dir, row["institution_profile"], provisional=provisional)
        if not provisional:
            if profile.get("expected_ossz", "").casefold() != row["resolved_ossz"].casefold():
                raise FinalizationError(f"{employee_id}: institution profile does not match resolved_ossz")
            if row["resolved_ossz"].casefold() not in profile["institution"]["name"].casefold():
                raise FinalizationError(f"{employee_id}: institution name does not identify resolved_ossz")
        validated.append((row, profile))
    return validated


def display_row(row: dict[str, str]) -> dict[str, str]:
    """Display-only casing: preserve evidence, employer legal names and prose."""
    result = dict(row)
    for field in ("surname", "given_name", "birth_place", "street", "city", "district",
                  "employment_street", "employment_city"):
        value = result.get(field, "")
        if value.isupper():
            result[field] = czech_display_case(value)
    return result


def row_to_form(row: dict[str, str], profile: dict[str, Any]) -> dict[str, Any]:
    row = display_row(row)
    employee = {
        "id": row["employee_id"],
        "person": {
            "surname": row["surname"], "given_name": row["given_name"], "dob": row["dob"],
            "birth_place": row["birth_place"], "nationality": row["nationality"],
            "insurance_number": row["insurance_number"], "sex": row["sex"],
        },
        "residence": {
            "street": row["street"], "house_number": row["house_number"], "city": row["city"],
            "district": row["district"], "postal_code": row["postal_code"],
            "country_code": row["country_code"], "ossz": row["resolved_ossz"],
        },
        "employment": {
            "kind": "self_employed" if row["status_profile"] == "self_employed_multi_state" else "employee",
            "employer_id": row["employment_id"],
            "employer_name": row["employment_name"],
            "street": row["employment_street"],
            "house_number": row["employment_house_number"],
            "city": row["employment_city"],
            "postal_code": row["employment_postal_code"],
            "country_code": row["employment_country_code"],
        },
        "a1": {
            "status_profile": row["status_profile"],
            "institution_profile": row["institution_profile"],
        },
        "activity": {"name": row["activity_name"], "address": row["activity_address"]},
        "certificate": {
            "document_id": row["document_id"], "member_state": "CZ",
            "start_date": row["start_date"], "end_date": row["end_date"],
        },
        "institution": {"issue_date": row["issue_date"], "signed_by": row["signed_by"]},
    }
    institution_config = {
        "institution": profile["institution"],
        "source_url": profile["source_url"],
        "certificate": {"member_state": "CZ"},
        "issue_date": row["issue_date"],
        "signed_by": row["signed_by"],
    }
    return build_form_data(employee, institution_config)


def verify_pdf(
    path: Path,
    row: dict[str, str],
    profile: dict[str, Any],
    all_rows: list[dict[str, str]],
) -> dict[str, Any]:
    row = display_row(row)
    reader = PdfReader(str(path))
    if len(reader.pages) != 3 or reader.get_fields():
        raise FinalizationError(f"{row['employee_id']}: PDF is not a static three-page document")
    page_texts = [page.extract_text() or "" for page in reader.pages]
    text = "\n".join(page_texts)
    nationality = row["nationality"]
    if nationality.casefold() in {"česká republika", "czech republic", "cz", "cze"}:
        nationality = "CZ"
    expected = (
        row["surname"], row["given_name"], row["dob"], row["birth_place"],
        nationality, row["insurance_number"], row["street"],
        row["house_number"], row["city"], row["postal_code"], row["document_id"],
        row["start_date"], row["end_date"], row["issue_date"], row["signed_by"],
        profile["institution"]["code"],
        row["employment_id"], row["employment_street"],
        row["employment_house_number"], row["employment_city"],
        row["employment_postal_code"], row["employment_country_code"],
    )
    if row["status_profile"] == "self_employed_multi_state":
        expected += (row["surname"], row["given_name"])
        expected += (row["activity_name"], row["activity_address"])
    missing = [value for value in expected if value not in text]
    if missing:
        raise FinalizationError(f"{row['employee_id']}: PDF text is missing: {missing}")
    if row["document_id"] not in page_texts[0]:
        raise FinalizationError(
            f"{row['employee_id']}: document_id missing from page 1"
        )
    if "{{" in text:
        raise FinalizationError(f"{row['employee_id']}: PDF contains a template placeholder")
    foreign = [
        other["insurance_number"] for other in all_rows
        if other["employee_id"] != row["employee_id"]
        and other["insurance_number"]
        and other["insurance_number"] in text
    ]
    if foreign:
        raise FinalizationError(f"{row['employee_id']}: PDF contains another employee identity")
    return {"page_count": len(reader.pages), "sha256": _sha256(path), "size_bytes": path.stat().st_size}


def generation_dependencies(review, employees, profiles, background, layout, extras=()):
    paths = {"review": review, "normalized_source": employees,
             "background": background, "layout": layout,
             "renderer": ROOT / "scripts/a1_core.py",
             "mapper": Path(__file__),
             "audit": ROOT / "scripts/a1_audit.py",
             "paths": ROOT / "scripts/a1_paths.py",
             "template_repair_receipt": ROOT / "config/a1_template_repair_2026-09-06.json",
             "address_rules": ROOT / "config/address_enrichment.json"}
    paths.update({f"institution/{p.name}": p for p in profiles.glob("*.json")})
    paths.update({f"extra/{index}": p for index, p in enumerate(extras)})
    return {key: _sha256(Path(path)) for key, path in paths.items()}


def snapshot_hash(rows):
    return hashlib.sha256(json.dumps(rows, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()


@audited("candidate_generate", "a1_candidate")
def generate_final_set(
    review_path: Path,
    employees_path: Path,
    profile_dir: Path,
    background: Path,
    layout: Path,
    output: Path,
) -> Path:
    import uuid
    validate_output_path(output, review_path, employees_path)
    inputs = generation_dependencies(review_path, employees_path, profile_dir, background, layout)
    rows = read_review(review_path)
    validated = validate_review(rows, employees_path, profile_dir)
    if output.exists():
        raise FinalizationError(f"output destination already exists; must be unique: {output}")
    run_id = current_run_id()
    staging = unique_staging_path(output.parent, f"candidate-{run_id}")
    generated_at = datetime.now(timezone.utc).isoformat()
    manifest: dict[str, Any] = {
        "generated_at": generated_at,
        "status": "CANDIDATE_REQUIRES_QA_AND_APPROVAL",
        "run_id": run_id,
        "inputs": inputs,
        "snapshot_sha256": snapshot_hash(rows),
        "review_sha256": _sha256(review_path),
        "generated": [],
    }
    pid = os.getpid()
    try:
        for row, profile in validated:
            form = row_to_form(row, profile)
            target = staging / f"A1_{_slug(row['employee_id'])}.pdf"
            generate_a1_pdf(form, background, layout, target)
        for row, profile in validated:
            target = staging / f"A1_{row['employee_id']}.pdf"
            checks = verify_pdf(target, row, profile, rows)
            manifest["generated"].append(
                {
                    "employee_id": row["employee_id"], "path": target.name,
                    "document_id": row["document_id"], "institution_profile": row["institution_profile"],
                    "institution_version": profile.get("version", ""),
                    "pdf_created": generated_at,
                    **checks,
                }
            )
        if len(manifest["generated"]) != len(rows):
            raise FinalizationError("not every reviewed employee produced a verified PDF")
        (staging / "generation_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        if generation_dependencies(review_path, employees_path, profile_dir, background, layout) != inputs:
            raise FinalizationError("generation dependencies changed; candidate is stale")
        for artifact in staging.iterdir():
            artifact.chmod(0o600)
        with destination_lock(output):
            publish_package(staging, output)
        return output
    except Exception as exc:
        cleanup_staging_only(staging, pid)
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--employees", type=Path)
    parser.add_argument("--enrichment", type=Path, default=ROOT / "config/address_enrichment.json")
    parser.add_argument("--profiles", type=Path, default=ROOT / "config/institutions")
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare", help="create the pre-filled operator review CSV")
    prepare.add_argument("--current-institution", type=Path, default=ROOT / "config/institution.json")
    prepare.add_argument("--review", type=Path)
    validate = sub.add_parser("validate", help="validate an approved review CSV without writing PDFs")
    validate.add_argument("--review", type=Path)
    readiness = sub.add_parser("readiness", help="list all operator-actionable review blockers")
    readiness.add_argument("--review", type=Path)
    readiness.add_argument("--report", type=Path, help="protected JSON receipt; defaults under a1/")
    readiness.add_argument("--provisional", action="store_true",
                           help="check provisional review inputs; default checks authoritative evidence")
    generate = sub.add_parser("generate", help="generate and atomically publish the complete reviewed set")
    generate.add_argument("--review", type=Path)
    generate.add_argument("--background", type=Path, default=ROOT / "templates/a1_background.pdf")
    generate.add_argument("--layout", type=Path, default=ROOT / "config/a1_layout.json")
    generate.add_argument("--output", type=Path, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    import uuid
    args = build_parser().parse_args(argv)
    try:
        private_root()
        args.employees = args.employees or private_path("a1/employees_normalized.json")
        args.review = args.review or (private_root() / "a1/review.csv" if args.command == "prepare"
                                      else private_path("a1/review.csv"))
        if args.command == "generate":
            generate_final_set(args.review, args.employees, args.profiles, args.background,
                               args.layout, args.output or private_root() / "output/candidate" / str(uuid.uuid4()))
            print("Generated candidate set; QA and artifact approval remain required")
            return 0
        operation, purpose = {"prepare": ("review_prepare", "a1_prepare"),
                              "validate": ("review_validate", "a1_validate"),
                              "readiness": ("readiness_check", "a1_readiness")}[args.command]
        with audited_operation(operation, purpose) as run_id:
            if args.command == "prepare":
                protected_path(args.review, ("a1",))
                if args.review.exists():
                    raise FinalizationError("REVIEW_EXISTS")
                prepare_review(args.employees, args.enrichment, args.current_institution, args.review)
                args.review.chmod(0o600)
                summary = "Prepared review CSV"
            elif args.command == "validate":
                validated = validate_review(read_review(args.review), args.employees, args.profiles)
                summary = f"Validated {len(validated)} approved employees"
            else:
                destination = readiness_receipt_path(args.report)
                if (destination in {args.review.resolve(), args.employees.resolve()}
                        or destination.is_relative_to(args.profiles.resolve())):
                    raise FinalizationError("RECEIPT_INPUT_OVERLAP")
                report = readiness_report(read_review(args.review), args.profiles,
                                          provisional=args.provisional)
                report['run_id'] = run_id
                write_private_json(destination, report)
                summary = json.dumps({key: report[key] for key in ("mode", "scope", "ready", "employee_count", "blocked_employee_count")})
        print(summary)
        return (0 if report["ready"] else 1) if args.command == "readiness" else 0
    except (Exception, KeyboardInterrupt):  # Sanitize unexpected malformed-input errors at the CLI boundary.
        if args.command == "readiness":
            try:
                destination = readiness_receipt_path(args.report)
                if (destination not in {args.review.resolve(), args.employees.resolve()}
                        and not destination.is_relative_to(args.profiles.resolve())):
                    write_failure_receipt(destination, "READINESS_INPUT_INVALID")
            except (A1PrivateInputError, FinalizationError, OSError, ValueError, AttributeError):
                pass
        print("FINALIZATION_BLOCKED", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
