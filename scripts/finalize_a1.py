#!/usr/bin/env python3
"""Prepare, validate, and atomically publish a reviewed set of A1 PDFs."""

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
    from .a1_core import A1ValidationError, build_form_data, enrich_residence, generate_a1_pdf
    from .a1_private import A1PrivateInputError, private_path, private_root
except ImportError:  # Direct CLI execution.
    from a1_core import A1ValidationError, build_form_data, enrich_residence, generate_a1_pdf
    from a1_private import A1PrivateInputError, private_path, private_root


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REVIEW = None
YES = "YES"
PROFILE_BY_OSSZ = {
    "OSSZ Plzeň": "plzen",
    "OSSZ Teplice": "teplice",
    "OSSZ Most": "most",
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
    return json.loads(path.read_text(encoding="utf-8"))


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
        return [{key: (value or "").strip() for key, value in row.items()} for row in reader]


def readiness_report(rows: list[dict[str, str]]) -> dict[str, Any]:
    """Return every operator-actionable publication blocker without generating PDFs."""
    required_values = (
        "activity_name", "activity_address", "document_id", "start_date", "end_date",
        "issue_date", "signed_by",
    )
    report_rows: list[dict[str, Any]] = []
    for row in rows:
        blockers: list[str] = []
        for field in required_values:
            if not row.get(field):
                blockers.append(f"missing {field}")
        for subject in ("activity", "certificate", "signatory"):
            if not row.get(f"{subject}_source"):
                blockers.append(f"missing {subject}_source")
            if row.get(f"{subject}_source_status") != AUTHORITATIVE:
                blockers.append(f"{subject}_source_status is not AUTHORITATIVE")
        for flag, expected in (
            ("certificate_reviewed", YES),
            ("approved_for_pdf", YES),
            ("validated_by_user", "1"),
        ):
            if row.get(flag) != expected:
                blockers.append(f"{flag} must be {expected}")
        report_rows.append({"employee_id": row.get("employee_id", ""), "blockers": blockers})
    return {
        "ready": all(not item["blockers"] for item in report_rows),
        "employee_count": len(report_rows),
        "blocked_employee_count": sum(bool(item["blockers"]) for item in report_rows),
        "employees": report_rows,
    }


def load_profile(profile_dir: Path, profile_id: str) -> dict[str, Any]:
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
    rows: list[dict[str, str]], employees_path: Path, profile_dir: Path
) -> list[tuple[dict[str, str], dict[str, Any]]]:
    source_employees = load_json(employees_path).get("employees", [])
    expected_by_id = {item["id"]: item for item in source_employees}
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
    required = (
        "surname", "given_name", "dob", "birth_place", "nationality", "sex",
        "insurance_number", "street", "house_number", "city", "postal_code",
        "country_code", "status_profile", "activity_name", "activity_address",
        "employment_id", "employment_name", "employment_street",
        "employment_house_number", "employment_city", "employment_postal_code",
        "employment_country_code",
        "resolved_ossz", "institution_profile", "start_date", "end_date", "issue_date",
        "signed_by",
    )
    for row in rows:
        employee_id = row["employee_id"]
        missing = [field for field in required if not row.get(field)]
        if missing:
            raise FinalizationError(f"{employee_id}: missing required values: {', '.join(missing)}")
        for flag in ("identity_reviewed", "certificate_reviewed", "approved_for_pdf"):
            if row.get(flag) != YES:
                raise FinalizationError(f"{employee_id}: {flag} must be YES")
        if row.get("validated_by_user") != "1":
            raise FinalizationError(f"{employee_id}: validated_by_user must be 1")
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
        if row["status_profile"] != "self_employed_multi_state":
            raise FinalizationError(f"{employee_id}: unsupported status_profile")
        dob = _date(row["dob"], f"{employee_id}.dob")
        start = _date(row["start_date"], f"{employee_id}.start_date")
        end = _date(row["end_date"], f"{employee_id}.end_date")
        issue = _date(row["issue_date"], f"{employee_id}.issue_date")
        if datetime.strptime(start, "%d.%m.%Y") > datetime.strptime(end, "%d.%m.%Y"):
            raise FinalizationError(f"{employee_id}: start_date is after end_date")
        if not _birth_number_matches_dob(row["insurance_number"], dob, row["sex"]):
            raise FinalizationError(f"{employee_id}: insurance_number does not match dob")

        profile = load_profile(profile_dir, row["institution_profile"])
        if profile.get("expected_ossz", "").casefold() != row["resolved_ossz"].casefold():
            raise FinalizationError(f"{employee_id}: institution profile does not match resolved_ossz")
        if row["resolved_ossz"].casefold() not in profile["institution"]["name"].casefold():
            raise FinalizationError(f"{employee_id}: institution name does not identify resolved_ossz")
        validated.append((row, profile))
    return validated


def row_to_form(row: dict[str, str], profile: dict[str, Any]) -> dict[str, Any]:
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
            "kind": "self_employed",
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
        row["activity_name"], profile["institution"]["code"],
    )
    missing = [value for value in expected if value not in text]
    if missing:
        raise FinalizationError(f"{row['employee_id']}: PDF text is missing: {missing}")
    document_id_pages = [
        i + 1 for i, page_text in enumerate(page_texts) if row["document_id"] not in page_text
    ]
    if document_id_pages:
        raise FinalizationError(
            f"{row['employee_id']}: document_id is not identical on pages {document_id_pages}"
        )
    if "{{" in text:
        raise FinalizationError(f"{row['employee_id']}: PDF contains a template placeholder")
    foreign = [
        other["insurance_number"] for other in all_rows
        if other["employee_id"] != row["employee_id"] and other["insurance_number"] in text
    ]
    if foreign:
        raise FinalizationError(f"{row['employee_id']}: PDF contains another employee identity")
    return {"page_count": len(reader.pages), "sha256": _sha256(path), "size_bytes": path.stat().st_size}


def generate_final_set(
    review_path: Path,
    employees_path: Path,
    profile_dir: Path,
    background: Path,
    layout: Path,
    output: Path,
) -> Path:
    rows = read_review(review_path)
    validated = validate_review(rows, employees_path, profile_dir)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".a1-staging-", dir=output.parent))
    generated_at = datetime.now(timezone.utc).isoformat()
    manifest: dict[str, Any] = {
        "generated_at": generated_at,
        "review_sha256": _sha256(review_path),
        "generated": [],
    }
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
        backup = None
        if output.exists():
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            backup = output.with_name(f"{output.name}.backup-{stamp}")
            os.replace(output, backup)
        try:
            os.replace(staging, output)
        except Exception:
            if backup is not None and backup.exists() and not output.exists():
                os.replace(backup, output)
            raise
        return output
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
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
    generate = sub.add_parser("generate", help="generate and atomically publish the complete reviewed set")
    generate.add_argument("--review", type=Path)
    generate.add_argument("--background", type=Path, default=ROOT / "templates/a1_background.pdf")
    generate.add_argument("--layout", type=Path, default=ROOT / "config/a1_layout.json")
    generate.add_argument("--output", type=Path, default=ROOT / "output/final")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        args.employees = args.employees or private_path("a1/employees_normalized.json")
        args.review = args.review or (
            private_root() / "a1/review.csv"
            if args.command == "prepare"
            else private_path("a1/review.csv")
        )
        if args.command == "prepare":
            prepare_review(args.employees, args.enrichment, args.current_institution, args.review)
            print(f"Prepared review CSV: {args.review}")
        elif args.command == "validate":
            validated = validate_review(read_review(args.review), args.employees, args.profiles)
            print(f"Validated {len(validated)} approved employees")
        elif args.command == "readiness":
            report = readiness_report(read_review(args.review))
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0 if report["ready"] else 1
        else:
            result = generate_final_set(
                args.review, args.employees, args.profiles, args.background, args.layout, args.output
            )
            print(f"Published final set: {result}")
        return 0
    except (
        A1PrivateInputError, FinalizationError, A1ValidationError, FileNotFoundError,
        json.JSONDecodeError,
    ) as exc:
        print(f"FINALIZATION BLOCKED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
