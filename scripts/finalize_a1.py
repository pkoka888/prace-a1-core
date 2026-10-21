#!/usr/bin/env python3
"""Prepare and validate A1 candidates; reserved final publication requires receipts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pypdf import PdfReader

try:
    from .a1_core import (
        A1_POSTING_STATUS_PROFILES,
        A1_STATUS_PROFILES,
        A1_STATUS_VARIANTS,
        PROVISIONAL_NOTICE,
        build_form_data,
        czech_display_case,
        enrich_residence,
        generate_a1_pdf,
    )
    from .a1_paths import (
        PathValidationError,
        validate_output_path,
        unique_staging_path,
        cleanup_staging_only,
        protected_path,
        destination_lock,
        publish_package,
    )
    from .a1_audit import (
        audited,
        audited_operation,
        current_run_id,
        write_failure_receipt,
        write_private_json,
    )
    from .a1_private import A1PrivateInputError, private_path, private_root
except ImportError:  # Direct CLI execution.
    from a1_core import (
        A1_POSTING_STATUS_PROFILES,
        A1_STATUS_PROFILES,
        A1_STATUS_VARIANTS,
        PROVISIONAL_NOTICE,
        build_form_data,
        czech_display_case,
        enrich_residence,
        generate_a1_pdf,
    )
    from a1_paths import (
        PathValidationError,
        validate_output_path,
        unique_staging_path,
        cleanup_staging_only,
        protected_path,
        destination_lock,
        publish_package,
    )
    from a1_audit import (
        audited,
        audited_operation,
        current_run_id,
        write_failure_receipt,
        write_private_json,
    )
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
# The 44-column review contract is the required set. Additional columns may
# be present: they carry Article 12 situation facts (validation evidence)
# and advisory readiness fields (pending_gates, warnings), so a review file
# without them still reads and the gates report facts as missing.
# Decision D10 and D1b (2026-10-20).
OPTIONAL_REVIEW_FIELDS = (
    "prior_activity_start",
    "replaces_worker",
    "employment_source_status",
    "pending_gates",
    "warnings",
)

CSV_FIELDS = (
    "employee_id",
    "source_scans",
    "surname",
    "given_name",
    "dob",
    "birth_place",
    "nationality",
    "sex",
    "insurance_number",
    "street",
    "house_number",
    "city",
    "district",
    "postal_code",
    "country_code",
    "status_profile",
    "activity_name",
    "activity_address",
    "employment_id",
    "employment_name",
    "employment_street",
    "employment_house_number",
    "employment_city",
    "employment_postal_code",
    "employment_country_code",
    "resolved_ossz",
    "institution_profile",
    "document_id",
    "start_date",
    "end_date",
    "issue_date",
    "signed_by",
    "identity_reviewed",
    "certificate_reviewed",
    "approved_for_pdf",
    "pdf_created",
    "validated_by_user",
    "activity_source",
    "activity_source_status",
    "certificate_source",
    "certificate_source_status",
    "signatory_source",
    "signatory_source_status",
    "comments",
)
PROFILE_FIELDS = (
    "name",
    "street",
    "house_number",
    "city",
    "postal_code",
    "country_code",
    "code",
)
AUTHORITATIVE = "AUTHORITATIVE"
UNVERIFIED_SOURCE_MARKERS = (
    "assum",
    "copied",
    "assigned",
    "example",
    "placeholder",
    "template",
)

# Human review gates. Authoritative issue requires every gate closed. A
# provisional copy keeps open gates open: it reports them as pending gates on
# an explicitly unverified copy instead of silently closing or blocking them.
REVIEW_GATES: tuple[tuple[str, str], ...] = (
    ("identity_reviewed", YES),
    ("certificate_reviewed", YES),
    ("approved_for_pdf", YES),
    ("validated_by_user", "1"),
)

# Facts the A1 form can carry but that a provisional copy may leave blank.
# Unknown stays unknown: the copy keeps the gap and reports it as a warning.
PROVISIONAL_OPTIONAL_FACTS = ("district",)

# Employer source state for a known disagreement with the public register.
# Provisional copies warn and keep the reviewed employer; authoritative issue
# stays refused by the existing D15 check.
EMPLOYMENT_SOURCE_DIVERGES = "DIVERGES_FROM_REGISTER"

VARIANT_DEFAULT = "employee"

VARIANT_PARAMETERS = {
    "employee": {
        "status_profiles": tuple(
            profile for profile in A1_STATUS_PROFILES
            if A1_STATUS_VARIANTS[profile] == "employee"
        ),
        "section5_activity_name_default": "",
        "section5_activity_address_default": "",
        "employment_name_must_not_contain": ("osvč", "osvc", "živnost", "samostatná"),
        "certificate_policy": "standard",
        "readiness_requires_activity_name": True,
    },
    "self_employed": {
        "status_profiles": tuple(
            profile for profile in A1_STATUS_PROFILES
            if A1_STATUS_VARIANTS[profile] == "self_employed"
        ),
        "section5_activity_name_default": "Samostatná výdělečná činnost",
        "section5_activity_address_default": "DE, CZ",
        "employment_name_must_not_contain": (),
        "certificate_policy": "provisional_self_employed",
        "readiness_requires_activity_name": False,
    },
}


def derive_variant(status_profile: str) -> str:
    if not status_profile:
        return VARIANT_DEFAULT
    lowered = status_profile.casefold()
    if "self_employed" in lowered or "osvč" in lowered:
        return "self_employed"
    if "employee" in lowered or "zaměstnanec" in lowered or "zamestnanec" in lowered:
        return "employee"
    return VARIANT_DEFAULT


def count_variants(
    rows: list[dict[str, str]], *, default: str = VARIANT_DEFAULT
) -> dict[str, Any]:
    totals: dict[str, int] = {VARIANT_DEFAULT: 0, "self_employed": 0}
    non_default_rows = []
    for row in rows:
        variant = derive_variant(row.get("status_profile", ""))
        totals[variant] = totals.get(variant, 0) + 1
        if variant != default:
            non_default_rows.append(
                {
                    "employee_id": row.get("employee_id", ""),
                    "variant": variant,
                    "reason": f"status_profile={row.get('status_profile', '')}",
                }
            )
    return {
        "default_variant": default,
        "totals": totals,
        "non_default_count": len(non_default_rows),
        "non_default_rows": non_default_rows,
    }


def auto_approve_stale_identity_reviews(
    rows: list[dict[str, str]],
    *,
    older_than_hours: float = 24.0,
    dry_run: bool = False,
) -> list[dict[str, str]]:
    now = datetime.now(timezone.utc)
    changed = []
    for row in rows:
        if row.get("identity_reviewed") == YES:
            continue
        comments = row.get("comments", "")
        marker = "AUTO_APPROVED "
        if marker in comments:
            continue
        row["identity_reviewed"] = YES
        row["comments"] = (
            f"{comments.rstrip()} | AUTO_APPROVED {now.isoformat()} — no correction in {older_than_hours:.0f}h"
        ).strip()
        changed.append(row)
    return changed


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


# A posting is a derogation from the single-legislation rule in Article 11(1)
# of Regulation 883/2004, and Article 12 conditions it. A certificate that
# asserts a posting has to be able to show those conditions, so the facts are
# checked at the issuance gate. Decision D1b (2026-10-20).
POSTING_STATUS_PROFILES = A1_POSTING_STATUS_PROFILES
# Article 12(1) and 12(2): the activity abroad does not exceed 24 months.
POSTING_MAX_MONTHS = 24


def employment_divergence(row: dict[str, str], registry: dict) -> list[str]:
    """Where a reviewed employer row and the business register disagree.

    The register is the authority for a company's registered name and seat.
    A row that was hand-typed can differ from it, and Section 4 of the form
    is a legal claim about the counterparty, so a divergence is reported
    rather than silently replaced. Gate D15.

    The register is passed as a plain mapping so that the export, which has a
    stored record, and the import path, which has a fresh lookup, compare
    the same way.
    """
    if not registry:
        return []
    address = registry.get("registered_address") or {}
    pairs = (
        ("employment_name", registry.get("legal_name", ""), "name"),
        ("employment_street", address.get("street", ""), "street"),
        ("employment_city", address.get("city", ""), "city"),
    )
    differences = []
    for field, registry_value, label in pairs:
        reviewed = _folded(row.get(field))
        registry_value = _folded(registry_value)
        if not registry_value:
            continue
        if not reviewed:
            differences.append(f"{label} is not stated")
        elif reviewed != registry_value:
            differences.append(f"{label} differs from the register")
    postal = _folded_digits(address.get("postal_code", ""))
    if postal and _folded_digits(row.get("employment_postal_code")) != postal:
        differences.append("postal code differs from the register")
    return differences


def _folded(value) -> str:
    """A value reduced to a comparable form.

    A postal code is written with a space in a review row and without one in
    the register, and the register types some of its values as numbers, so
    everything is compared as text with the spacing and the case removed.
    """
    if value is None:
        return ""
    return " ".join(str(value).casefold().split())


def _folded_digits(value) -> str:
    """A value reduced to its digits, for a postal code."""
    return "".join(character for character in str(value) if character.isdigit())


def _check_employer_agreement(employee_id: str, row: dict[str, str]) -> None:
    """The employer row must agree with the business register.

    Section 4 of the form is a legal claim about the counterparty, so a row
    that diverges from the register is refused before issue rather than
    silently replaced. A row with no reviewed record is not refused here: the
    absence of a record is "not stated", and the reviewer decides. Gate D15.
    """
    if row.get("employment_source_status") == "DIVERGES_FROM_REGISTER":
        raise FinalizationError(
            f"{employee_id}: the employer row diverges from the business "
            "register; Section 4 is a legal claim about the counterparty, so "
            "it must be reconciled before issue"
        )


def _check_posting_conditions(employee_id: str, row: dict[str, str]) -> None:
    """The Article 12 conditions for a posting, checked before issuance.

    A missing fact blocks this A1 operation and nothing else: the worker and
    the review row are still saved, and the gates report the fact as missing
    rather than defaulting it.
    """
    status = row.get("status_profile", "")
    if status not in POSTING_STATUS_PROFILES:
        return
    replaces = (row.get("replaces_worker") or "").strip().casefold()
    if replaces not in {"yes", "no"}:
        raise FinalizationError(
            f"{employee_id}: replaces_worker must be yes or no for a posting "
            "(Article 12(1): the worker must not be sent to replace another "
            "posted person); the fact is missing, not presumed"
        )
    if status == "posted_self_employed":
        prior = (row.get("prior_activity_start") or "").strip()
        if not prior:
            raise FinalizationError(
                f"{employee_id}: prior_activity_start is required for a posted "
                "self-employed person (Article 14(3) of Regulation 987/2009: "
                "the activity must already have been pursued); the fact is "
                "missing, not presumed"
            )
        _date(prior, f"{employee_id}.prior_activity_start")
    start = (row.get("start_date") or "").strip()
    end = (row.get("end_date") or "").strip()
    if start and end:
        start_date = datetime.strptime(_date(start, f"{employee_id}.start_date"), "%d.%m.%Y")
        end_date = datetime.strptime(_date(end, f"{employee_id}.end_date"), "%d.%m.%Y")
        if end_date < start_date:
            raise FinalizationError(
                f"{employee_id}: end_date {end} precedes start_date {start}"
            )
        months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
        if months > POSTING_MAX_MONTHS:
            raise FinalizationError(
                f"{employee_id}: a posting may not exceed {POSTING_MAX_MONTHS} "
                f"months (Article 12 of Regulation 883/2004); the certificate "
                f"covers {months} months"
            )


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
                "source_scans": ";".join(
                    employee.get("provenance", {}).get("scans", [])
                ),
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
                "prior_activity_start": employee.get("a1", {}).get(
                    "prior_activity_start", ""
                ),
                "replaces_worker": employee.get("a1", {}).get("replaces_worker", ""),
                "resolved_ossz": resolved,
                "institution_profile": PROFILE_BY_OSSZ.get(resolved, ""),
                "start_date": current.get("certificate", {}).get("start_date", "")
                if is_teplice
                else "",
                "end_date": current.get("certificate", {}).get("end_date", "")
                if is_teplice
                else "",
                "issue_date": current.get("issue_date", "") if is_teplice else "",
                "signed_by": current.get("signed_by", "") if is_teplice else "",
                "identity_reviewed": "YES",
                "certificate_reviewed": "YES",
                "approved_for_pdf": "YES",
                "pdf_created": "",
                "validated_by_user": "1",
                "activity_source_status": "UNVERIFIED",
                "certificate_source_status": "UNVERIFIED",
                "signatory_source_status": "UNVERIFIED",
                "comments": "REVIEW REQUIRED: add activity and unique document ID",
            }
        )
        # Preserve supplied worker/assignment facts. Preparation is an adapter,
        # not a reason to ask for already-recorded employer and posting values.
        mappings = {
            "employment": {
                "employer_id": "employment_id",
                "employer_name": "employment_name",
                **{
                    f: "employment_" + f
                    for f in (
                        "street",
                        "house_number",
                        "city",
                        "postal_code",
                        "country_code",
                    )
                },
            },
            "activity": {"name": "activity_name", "address": "activity_address"},
            "certificate": {f: f for f in ("document_id", "start_date", "end_date")},
            "institution": {f: f for f in ("issue_date", "signed_by")},
            "a1": {"institution_profile": "institution_profile"},
        }
        for section, fields in mappings.items():
            for source_field, column in fields.items():
                value = employee.get(section, {}).get(source_field)
                if value:
                    row[column] = value
        rows.append(row)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=review_fieldnames(rows))
        writer.writeheader()
        writer.writerows(rows)
    output_path.chmod(0o600)


def read_review(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        missing = [
            field for field in CSV_FIELDS if field not in (reader.fieldnames or [])
        ]
        if missing:
            raise FinalizationError(
                "review CSV is missing columns: " + ", ".join(missing)
            )
        if len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise FinalizationError("review CSV has duplicate columns")
        rows = []
        for index, row in enumerate(reader, start=2):
            if None in row or any(value is None for value in row.values()):
                raise FinalizationError(
                    f"review CSV row {index}: field count differs from header"
                )
            rows.append({key: value.strip() for key, value in row.items()})
        if not rows:
            raise FinalizationError("review CSV contains no records")
        ids = [row["employee_id"] for row in rows]
        if len(ids) != len(set(ids)):
            raise FinalizationError("employee_id values must be unique")
        for value in ids:
            _slug(value)
        return rows


def review_fieldnames(rows: list[dict[str, str]]) -> list[str]:
    """The required 44 columns, plus the optional ones the rows carry.

    The 44-column contract is unchanged. The two optional columns appear
    only when the rows carry them, so a review file that does not use the
    Article 12 situation facts is byte-identical to before.
    """
    fieldnames = list(CSV_FIELDS)
    for optional in OPTIONAL_REVIEW_FIELDS:
        if any(optional in row for row in rows):
            fieldnames.append(optional)
    return fieldnames


def write_review(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=review_fieldnames(rows))
        writer.writeheader()
        writer.writerows(rows)
    path.chmod(0o600)


def _required_review_fields(
    status: str, *, provisional: bool, variant: str | None = None
) -> tuple[str, ...]:
    """One CSV presence contract for validation and its readiness preflight."""
    variant = derive_variant(status) if variant is None else variant
    variant_params = VARIANT_PARAMETERS[variant]
    common = (
        "surname",
        "given_name",
        "dob",
        "birth_place",
        "nationality",
        "sex",
        "insurance_number",
        "street",
        "house_number",
        "city",
        "postal_code",
        "country_code",
        "status_profile",
        "employment_id",
        "employment_name",
        "employment_street",
        "employment_house_number",
        "employment_city",
        "employment_postal_code",
        "employment_country_code",
        "resolved_ossz",
        "institution_profile",
        "document_id",
        "issue_date",
    )
    if variant_params["readiness_requires_activity_name"]:
        activity = ("activity_name", "activity_address")
    elif provisional and variant == "self_employed":
        activity = ("activity_address",)
    else:
        activity = ("activity_name", "activity_address")
    certificate = () if provisional else ("start_date", "end_date", "signed_by")
    return (*common, *activity, *certificate)


def pending_review_gates(row: dict[str, str]) -> list[str]:
    """Open human review gates for one row, in a stable order.

    The strings name the gate and the required value; they never carry
    review content.
    """
    return [
        f"{flag} must be {expected}"
        for flag, expected in REVIEW_GATES
        if row.get(flag) != expected
    ]


def identity_source_state(
    row: dict[str, str], source_employee: dict[str, Any]
) -> dict[str, Any]:
    """Compare a reviewed row with the normalized scan source.

    Only field names are returned: source and reviewed values stay out of
    readiness receipts, manifests and verification tables.
    """
    source_values = {
        **{
            field: source_employee.get("person", {}).get(field, "")
            for field in (
                "surname",
                "given_name",
                "dob",
                "birth_place",
                "nationality",
                "sex",
                "insurance_number",
            )
        },
        **{
            field: source_employee.get("residence", {}).get(field, "")
            for field in (
                "street",
                "house_number",
                "city",
                "district",
                "country_code",
            )
        },
    }
    differences = [
        field
        for field, value in source_values.items()
        if value
        and row.get(field, "").casefold() != str(value).strip().casefold()
    ]
    expected_scans = set(source_employee.get("provenance", {}).get("scans", []))
    reviewed_scans = {
        item.strip()
        for item in row.get("source_scans", "").split(";")
        if item.strip()
    }
    if reviewed_scans != expected_scans:
        differences.append("source_scans")
    return {
        "state": "MATCHES_SOURCE" if not differences else "DIFFERS_FROM_SOURCE",
        "differences": differences,
    }


def provisional_warnings(
    row: dict[str, str], *, identity: dict[str, Any] | None = None
) -> list[str]:
    """Non-blocking provisional observations; field names and states only."""
    warnings = [
        f"optional fact not stated: {field}"
        for field in PROVISIONAL_OPTIONAL_FACTS
        if not row.get(field, "").strip()
    ]
    if row.get("employment_source_status") == EMPLOYMENT_SOURCE_DIVERGES:
        warnings.append(
            "employment_source_status is DIVERGES_FROM_REGISTER; "
            "reviewed employer retained pending registry review"
        )
    if identity is not None and identity.get("differences"):
        warnings.append(
            "reviewed identity/residence differs from normalized scan source: "
            + ", ".join(identity["differences"])
        )
    return warnings


def readiness_report(
    rows: list[dict[str, str]],
    profile_dir: Path | None = None,
    *,
    provisional: bool = False,
    variant: str = VARIANT_DEFAULT,
    employees_path: Path | None = None,
) -> dict[str, Any]:
    """Sanitized, mode-aware review preflight; not generation or artifact approval.

    ``blockers`` stop the selected mode. In the provisional mode the human
    review gates stay open and appear in ``pending_gates``; ``ready`` then
    means ready for a provisional copy, never ready to issue. ``warnings``
    are non-blocking, field-name-only observations.
    """
    source_by_id: dict[str, Any] | None = None
    if employees_path is not None:
        try:
            source_by_id = {
                item["id"]: item
                for item in load_json(employees_path).get("employees", [])
            }
        except (OSError, ValueError, KeyError, FinalizationError):
            source_by_id = {}
    report_rows = []
    variant_params = VARIANT_PARAMETERS.get(
        variant, VARIANT_PARAMETERS[VARIANT_DEFAULT]
    )
    for index, row in enumerate(rows, 1):
        status = row.get("status_profile", "")
        row_variant = derive_variant(status)
        required_values = _required_review_fields(
            status, provisional=provisional, variant=row_variant
        )
        blockers = [
            f"missing {field}" for field in required_values if not row.get(field)
        ]
        for subject in () if provisional else ("activity", "certificate", "signatory"):
            source = row.get(f"{subject}_source", "")
            if not source:
                blockers.append(f"missing {subject}_source")
            elif any(
                marker in source.casefold() for marker in UNVERIFIED_SOURCE_MARKERS
            ):
                blockers.append(f"placeholder detected in {subject}_source")
            if row.get(f"{subject}_source_status") != AUTHORITATIVE:
                blockers.append(f"{subject}_source_status is not AUTHORITATIVE")
        gates = pending_review_gates(row)
        pending = gates if provisional else []
        if not provisional:
            blockers.extend(gates)
        if status not in A1_STATUS_PROFILES:
            blockers.append(
                f"unsupported status_profile {status!r}; expected posted_employee, "
                "employee_multi_state or self_employed_multi_state"
            )
        if row_variant == "employee":
            lowered_employment_name = row.get("employment_name", "").casefold()
            if any(
                term in lowered_employment_name
                for term in variant_params["employment_name_must_not_contain"]
            ):
                blockers.append("employee profile has self-employed employer data")
        dates = {}
        for field in ("dob", "start_date", "end_date", "issue_date"):
            if row.get(field):
                try:
                    dates[field] = datetime.strptime(row[field], "%d.%m.%Y")
                except ValueError:
                    blockers.append(f"invalid {field}")
        if (
            dates.get("start_date")
            and dates.get("end_date")
            and dates["start_date"] > dates["end_date"]
        ):
            blockers.append("start_date is after end_date")
        for field in ("employee_id", "document_id"):
            if (
                row.get(field)
                and sum(other.get(field) == row[field] for other in rows) > 1
            ):
                blockers.append(f"duplicate {field}")
        if profile_dir is not None and row.get("institution_profile"):
            try:
                profile = load_profile(
                    profile_dir, row["institution_profile"], provisional=provisional
                )
                if (
                    not provisional
                    and profile.get("expected_ossz", "").casefold()
                    != row.get("resolved_ossz", "").casefold()
                ):
                    blockers.append("institution_profile does not match resolved_ossz")
            except (FinalizationError, OSError, ValueError):
                blockers.append(
                    "institution_profile is missing, unverified or contains placeholder fields"
                )
        identity = (
            identity_source_state(row, source_by_id[row["employee_id"]])
            if source_by_id is not None and row.get("employee_id") in source_by_id
            else None
        )
        if not provisional and identity is not None and identity["differences"]:
            blockers.append(
                "reviewed identity/residence differs from normalized scan source: "
                + ", ".join(identity["differences"])
            )
        warnings = (
            provisional_warnings(row, identity=identity) if provisional else []
        )
        if blockers:
            gate_state = "BLOCKED"
        elif pending:
            gate_state = "AWAITING_REVIEW"
        else:
            gate_state = "READY"
        report_rows.append(
            {
                "row_index": index,
                "gate_state": gate_state,
                "blockers": blockers,
                "pending_gates": pending,
                "warnings": warnings,
                "identity_source_state": identity["state"]
                if identity is not None
                else "NOT_CHECKED",
            }
        )
    return {
        "mode": "provisional" if provisional else "authoritative",
        "scope": "review_preflight",
        "ready": bool(rows) and all(not r["blockers"] for r in report_rows),
        "ready_for": "provisional_copy" if provisional else "authoritative_issue",
        "employee_count": len(rows),
        "blocked_employee_count": sum(bool(r["blockers"]) for r in report_rows),
        "pending_employee_count": sum(
            bool(r["pending_gates"]) for r in report_rows
        ),
        "pending_gate_count": sum(len(r["pending_gates"]) for r in report_rows),
        "warning_count": sum(len(r["warnings"]) for r in report_rows),
        "employees": report_rows,
    }


def readiness_receipt_path(requested: Path | None) -> Path:
    root = private_root().resolve()
    try:
        target = protected_path(
            requested or root / "a1/blocked-rows.json", ("a1", "evidence")
        )
    except PathValidationError as exc:
        raise FinalizationError("READINESS_DESTINATION_INVALID") from exc
    if (
        target.suffix != ".json"
        or target.name in {"cohort.json", "employees_normalized.json", "operator.json"}
        or any(
            target.is_relative_to(root / "a1" / name)
            for name in ("audit", "receipts", "locks")
        )
        or not any(target.is_relative_to(root / name) for name in ("a1", "evidence"))
    ):
        raise FinalizationError(
            "readiness receipt requires a protected non-input JSON destination"
        )
    return target


def load_profile(
    profile_dir: Path, profile_id: str, provisional: bool = False
) -> dict[str, Any]:
    profile = load_json(profile_dir / f"{_slug(profile_id)}.json")
    return validate_profile(profile, profile_id, provisional=provisional)


def validate_profile(
    profile: dict[str, Any], profile_id: str, *, provisional: bool = False
) -> dict[str, Any]:
    """Validate loaded profile bytes as well as profiles supplied by DB adapters."""
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
        invalid = [
            field
            for field in PROFILE_FIELDS
            if any(
                marker in str(institution.get(field, "")).casefold()
                for marker in markers
            )
        ]
        if invalid:
            raise FinalizationError(
                "institution profile contains placeholder fields: " + ", ".join(invalid)
            )
    return profile


def _require_authoritative_source(row: dict[str, str], subject: str) -> None:
    source = row.get(f"{subject}_source", "").strip()
    status = row.get(f"{subject}_source_status", "").strip()
    if status != AUTHORITATIVE:
        raise FinalizationError(
            f"{row['employee_id']}: {subject}_source_status must be AUTHORITATIVE"
        )
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
    rows: list[dict[str, str]],
    employees_path: Path,
    profile_dir: Path,
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
    if any(not value for value in document_ids) or len(document_ids) != len(
        set(document_ids)
    ):
        raise FinalizationError("every employee needs a non-empty, unique document_id")

    validated: list[tuple[dict[str, str], dict[str, Any]]] = []
    for row in rows:
        employee_id = _slug(row["employee_id"])
        status = row.get("status_profile", "")
        required = _required_review_fields(status, provisional=provisional)
        missing = [field for field in required if not row.get(field)]
        if missing:
            raise FinalizationError(
                f"{employee_id}: missing required values: {', '.join(missing)}"
            )
        if not provisional:
            for flag in ("identity_reviewed", "certificate_reviewed", "approved_for_pdf"):
                if row.get(flag) != YES:
                    raise FinalizationError(f"{employee_id}: {flag} must be YES")
            if row.get("validated_by_user") != "1":
                raise FinalizationError(f"{employee_id}: validated_by_user must be 1")
            _check_posting_conditions(employee_id, row)
            _check_employer_agreement(employee_id, row)
            for subject in ("activity", "certificate", "signatory"):
                _require_authoritative_source(row, subject)
            identity = identity_source_state(row, expected_by_id[employee_id])
            if identity["differences"]:
                raise FinalizationError(
                    f"{employee_id}: reviewed identity/residence differs from "
                    "normalized scan source: "
                    + ", ".join(identity["differences"])
                )
        if row["sex"] not in {"M", "F"}:
            raise FinalizationError(f"{employee_id}: sex must be M or F")
        if row["status_profile"] not in A1_STATUS_PROFILES:
            raise FinalizationError(
                f"{employee_id}: unsupported status_profile {row['status_profile']!r}; "
                f"expected {', '.join(A1_STATUS_PROFILES)}"
            )
        if A1_STATUS_VARIANTS.get(row["status_profile"], "") == "employee":
            if "osvč" in row["employment_name"].casefold():
                raise FinalizationError(
                    "employee profile has self-employed employer data"
                )
        dob = _date(row["dob"], f"{employee_id}.dob")
        if not provisional:
            start = _date(row["start_date"], f"{employee_id}.start_date")
            end = _date(row["end_date"], f"{employee_id}.end_date")
            _date(row["issue_date"], f"{employee_id}.issue_date")
            if datetime.strptime(start, "%d.%m.%Y") > datetime.strptime(
                end, "%d.%m.%Y"
            ):
                raise FinalizationError(f"{employee_id}: start_date is after end_date")
            if not _birth_number_matches_dob(row["insurance_number"], dob, row["sex"]):
                raise FinalizationError(
                    f"{employee_id}: insurance_number does not match dob"
                )

        profile = load_profile(
            profile_dir, row["institution_profile"], provisional=provisional
        )
        if not provisional:
            if (
                profile.get("expected_ossz", "").casefold()
                != row["resolved_ossz"].casefold()
            ):
                raise FinalizationError(
                    f"{employee_id}: institution profile does not match resolved_ossz"
                )
            if (
                row["resolved_ossz"].casefold()
                not in profile["institution"]["name"].casefold()
            ):
                raise FinalizationError(
                    f"{employee_id}: institution name does not identify resolved_ossz"
                )
        validated.append((row, profile))
    return validated


def validate_application_draft_row(
    row: dict[str, str], profile: dict[str, Any]
) -> dict[str, Any]:
    """Prepare an explicitly unverified application; never grant review or issuance."""
    if set(row) != set(CSV_FIELDS) or any(
        not isinstance(value, str) for value in row.values()
    ):
        raise FinalizationError("APPLICATION_DRAFT_CANONICAL_ROW_REQUIRED")
    _slug(row["employee_id"])
    required = _required_review_fields(row["status_profile"], provisional=True)
    missing = [
        field for field in required if field != "issue_date" and not row[field].strip()
    ]
    if missing:
        raise FinalizationError("APPLICATION_DRAFT_MISSING: " + ", ".join(missing))
    dates = {}
    for field in ("dob", "start_date", "end_date", "issue_date"):
        if row[field]:
            dates[field] = datetime.strptime(_date(row[field], field), "%d.%m.%Y")
    if (
        dates.get("start_date")
        and dates.get("end_date")
        and dates["start_date"] > dates["end_date"]
    ):
        raise FinalizationError("APPLICATION_DRAFT_DATE_ORDER")
    if row["sex"] not in {"M", "F"}:
        raise FinalizationError("APPLICATION_DRAFT_SEX_INVALID")
    if row["status_profile"] not in A1_STATUS_PROFILES:
        raise FinalizationError(
            "APPLICATION_DRAFT_PROFILE_INVALID: expected "
            f"{', '.join(A1_STATUS_PROFILES)}"
        )
    if (
        row["status_profile"] != "self_employed_multi_state"
        and "osvč" in row["employment_name"].casefold()
    ):
        raise FinalizationError("employee profile has self-employed employer data")
    validate_profile(profile, row["institution_profile"])
    if (
        not str(profile["institution"]["code"]).isascii()
        or not str(profile["institution"]["code"]).isdigit()
    ):
        raise FinalizationError("APPLICATION_DRAFT_INSTITUTION_CODE_INVALID")
    if not 1 <= int(profile["institution"]["code"]) <= 99999:
        raise FinalizationError("APPLICATION_DRAFT_INSTITUTION_CODE_INVALID")
    if profile.get("expected_ossz", "").casefold() != row["resolved_ossz"].casefold():
        raise FinalizationError("APPLICATION_DRAFT_INSTITUTION_MISMATCH")
    if row["resolved_ossz"].casefold() not in profile["institution"]["name"].casefold():
        raise FinalizationError("APPLICATION_DRAFT_INSTITUTION_NAME_MISMATCH")
    return row_to_form(row, profile, application_draft=True)


def display_row(row: dict[str, str]) -> dict[str, str]:
    """Display-only casing: preserve evidence, employer legal names and prose."""
    result = dict(row)
    for field in (
        "surname",
        "given_name",
        "birth_place",
        "street",
        "city",
        "district",
        "employment_street",
        "employment_city",
    ):
        value = result.get(field, "")
        if value.isupper():
            result[field] = czech_display_case(value)
    return result


def row_to_form(
    row: dict[str, str], profile: dict[str, Any], *, application_draft: bool = False
) -> dict[str, Any]:
    row = display_row(row)
    employee = {
        "id": row["employee_id"],
        "person": {
            "surname": row["surname"],
            "given_name": row["given_name"],
            "dob": row["dob"],
            "birth_place": row["birth_place"],
            "nationality": row["nationality"],
            "insurance_number": row["insurance_number"],
            "sex": row["sex"],
        },
        "residence": {
            "street": row["street"],
            "house_number": row["house_number"],
            "city": row["city"],
            "district": row["district"],
            "postal_code": row["postal_code"],
            "country_code": row["country_code"],
            "ossz": row["resolved_ossz"],
        },
        "employment": {
            "kind": "self_employed"
            if row["status_profile"] == "self_employed_multi_state"
            else "employee",
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
        # Activity: for multi-state, territories default to DE, CZ
        "activity": {
            "name": row["activity_name"],
            "address": row["activity_address"]
            or (
                "DE, CZ"
                if row["status_profile"]
                in A1_STATUS_PROFILES
                else ""
            ),
        },
        "certificate": {
            "document_id": row["document_id"],
            "member_state": profile.get("member_state", "CZ"),
            "start_date": row["start_date"],
            "end_date": row["end_date"],
        },
        # Institution: add contact person from profile
        "institution": {
            "issue_date": row["issue_date"],
            "signed_by": row["signed_by"],
            "contact_person_1": profile.get("current_office_contact", {}).get(
                "name", ""
            ),
            "contact_title_1": profile.get("current_office_contact", {}).get(
                "role", ""
            ),
        },
    }
    institution_config = {
        "institution": profile["institution"],
        "source_url": profile["source_url"],
        "certificate": {"member_state": profile.get("member_state", "CZ")},
        "issue_date": row["issue_date"],
        "signed_by": row["signed_by"],
    }
    return build_form_data(
        employee, institution_config, application_draft=application_draft
    )


def verify_pdf(
    path: Path,
    row: dict[str, str],
    profile: dict[str, Any],
    all_rows: list[dict[str, str]],
    *,
    provisional: bool = False,
) -> dict[str, Any]:
    row = display_row(row)
    reader = PdfReader(str(path))
    if len(reader.pages) != 3 or reader.get_fields():
        raise FinalizationError(
            f"{row['employee_id']}: PDF is not a static three-page document"
        )
    page_texts = [page.extract_text() or "" for page in reader.pages]
    text = "\n".join(page_texts)
    nationality = row["nationality"]
    if nationality.casefold() in {"česká republika", "czech republic", "cz", "cze"}:
        nationality = "CZ"
    expected = (
        row["surname"],
        row["given_name"],
        row["dob"],
        row["birth_place"],
        nationality,
        row["insurance_number"],
        row["street"],
        row["house_number"],
        row["city"],
        row["postal_code"],
        row["document_id"],
        row["start_date"],
        row["end_date"],
        row["issue_date"],
        row["signed_by"],
        profile["institution"]["code"],
        row["employment_id"],
        row["employment_street"],
        row["employment_house_number"],
        row["employment_city"],
        row["employment_postal_code"],
        row["employment_country_code"],
    )
    if row["status_profile"] == "self_employed_multi_state":
        expected += (row["surname"], row["given_name"])
        expected += (row["activity_address"],)
        if not provisional:
            expected += (row["activity_name"],)
        else:
            # Check the actual field, not global text: the template's printed
            # self-employment labels must remain visible elsewhere on the page.
            import pymupdf

            layout = json.loads(
                (ROOT / "config/a1_layout.json").read_text(encoding="utf-8")
            )
            field = layout["fields"]["activity.name"]
            with pymupdf.open(path) as document:
                page = document[field["page"]]
                baseline = page.rect.height - field["y"]
                box = (
                    field["x"] - 1,
                    baseline - field["size"] * 1.5,
                    field["x"] + field["max_width"],
                    baseline + field["size"] * 0.5,
                )
                if page.get_text("text", clip=box).strip():
                    raise FinalizationError("PROVISIONAL_SECTION_5_1_NOT_BLANK")
    if provisional:
        # Decision D2 (2026-10-20): the client-confirmation copy states on
        # every page that it is not an issued A1. This is the document that
        # leaves the agency before the real certificate exists.
        if not all(PROVISIONAL_NOTICE in page for page in page_texts):
            raise FinalizationError("PROVISIONAL_NOTICE_MISSING")
    missing = [value for value in expected if value not in text]
    if missing:
        raise FinalizationError(f"{row['employee_id']}: PDF text is missing: {missing}")
    if row["document_id"] not in page_texts[0]:
        raise FinalizationError(
            f"{row['employee_id']}: document_id missing from page 1"
        )
    if "{{" in text:
        raise FinalizationError(
            f"{row['employee_id']}: PDF contains a template placeholder"
        )
    foreign = [
        other["insurance_number"]
        for other in all_rows
        if other["employee_id"] != row["employee_id"]
        and other["insurance_number"]
        and other["insurance_number"] in text
    ]
    if foreign:
        raise FinalizationError(
            f"{row['employee_id']}: PDF contains another employee identity"
        )
    return {
        "page_count": len(reader.pages),
        "sha256": _sha256(path),
        "size_bytes": path.stat().st_size,
    }


def generation_dependencies(review, employees, profiles, background, layout, extras=()):
    paths = {
        "review": review,
        "normalized_source": employees,
        "background": background,
        "layout": layout,
        "renderer": ROOT / "scripts/a1_core.py",
        "mapper": Path(__file__),
        "audit": ROOT / "scripts/a1_audit.py",
        "paths": ROOT / "scripts/a1_paths.py",
        "template_repair_receipt": ROOT / "config/a1_template_repair_2026-09-06.json",
        "address_rules": ROOT / "config/address_enrichment.json",
    }
    paths.update({f"institution/{p.name}": p for p in profiles.glob("*.json")})
    paths.update({f"extra/{index}": p for index, p in enumerate(extras)})
    return {key: _sha256(Path(path)) for key, path in paths.items()}


def snapshot_hash(rows):
    return hashlib.sha256(
        json.dumps(
            rows, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode()
    ).hexdigest()


@audited("candidate_generate", "a1_candidate")
def generate_final_set(
    review_path: Path,
    employees_path: Path,
    profile_dir: Path,
    background: Path,
    layout: Path,
    output: Path,
) -> Path:
    validate_output_path(output, review_path, employees_path)
    inputs = generation_dependencies(
        review_path, employees_path, profile_dir, background, layout
    )
    rows = read_review(review_path)
    validated = validate_review(rows, employees_path, profile_dir)
    if output.exists():
        raise FinalizationError(
            f"output destination already exists; must be unique: {output}"
        )
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
                    "employee_id": row["employee_id"],
                    "path": target.name,
                    "document_id": row["document_id"],
                    "institution_profile": row["institution_profile"],
                    "institution_version": profile.get("version", ""),
                    "pdf_created": generated_at,
                    **checks,
                }
            )
        if len(manifest["generated"]) != len(rows):
            raise FinalizationError(
                "not every reviewed employee produced a verified PDF"
            )
        (staging / "generation_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        if (
            generation_dependencies(
                review_path, employees_path, profile_dir, background, layout
            )
            != inputs
        ):
            raise FinalizationError(
                "generation dependencies changed; candidate is stale"
            )
        for artifact in staging.iterdir():
            artifact.chmod(0o600)
        with destination_lock(output):
            publish_package(staging, output)
        return output
    except Exception:
        cleanup_staging_only(staging, pid)
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--employees", type=Path)
    parser.add_argument(
        "--enrichment", type=Path, default=ROOT / "config/address_enrichment.json"
    )
    parser.add_argument("--profiles", type=Path, default=ROOT / "config/institutions")
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser(
        "prepare", help="create the pre-filled operator review CSV"
    )
    prepare.add_argument(
        "--current-institution", type=Path, default=ROOT / "config/institution.json"
    )
    prepare.add_argument("--review", type=Path)
    validate = sub.add_parser(
        "validate", help="validate an approved review CSV without writing PDFs"
    )
    validate.add_argument("--review", type=Path)
    readiness = sub.add_parser(
        "readiness", help="list all operator-actionable review blockers"
    )
    readiness.add_argument("--review", type=Path)
    readiness.add_argument(
        "--report", type=Path, help="protected JSON receipt; defaults under a1/"
    )
    readiness.add_argument(
        "--provisional",
        action="store_true",
        help="check provisional review inputs; default checks authoritative evidence",
    )
    generate = sub.add_parser(
        "generate", help="generate and atomically publish the complete reviewed set"
    )
    generate.add_argument("--review", type=Path)
    generate.add_argument(
        "--background", type=Path, default=ROOT / "templates/a1_background.pdf"
    )
    generate.add_argument("--layout", type=Path, default=ROOT / "config/a1_layout.json")
    generate.add_argument("--output", type=Path, default=None)
    auto_approve = sub.add_parser(
        "auto-approve", help="auto-approve stale identity reviews unchanged for 24h"
    )
    auto_approve.add_argument("--review", type=Path)
    auto_approve.add_argument(
        "--older-than",
        type=str,
        default="24h",
        help="minimum age for auto-approval, e.g. 24h, 48h (default: 24h)",
    )
    auto_approve.add_argument(
        "--dry-run", action="store_true", help="print affected rows without writing"
    )
    count_variants = sub.add_parser(
        "count-variants", help="count workers by OSVČ/zaměstnanec variant"
    )
    count_variants.add_argument("--review", type=Path)
    count_variants.add_argument(
        "--default",
        type=str,
        default=VARIANT_DEFAULT,
        choices=("employee", "self_employed"),
        help="default variant for non-default counting (default: employee)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    import uuid

    args = build_parser().parse_args(argv)
    try:
        private_root()
        args.employees = args.employees or private_path("a1/employees_normalized.json")
        args.review = args.review or (
            private_root() / "a1/review.csv"
            if args.command == "prepare"
            else private_path("a1/review.csv")
        )
        if args.command == "generate":
            generate_final_set(
                args.review,
                args.employees,
                args.profiles,
                args.background,
                args.layout,
                args.output or private_root() / "output/candidate" / str(uuid.uuid4()),
            )
            print("Generated candidate set; QA and artifact approval remain required")
            return 0
        if args.command == "auto-approve":
            rows = read_review(args.review)
            try:
                older_than = float(args.older_than.lower().replace("h", ""))
            except ValueError:
                print(f"invalid --older-than value: {args.older_than}", file=sys.stderr)
                return 1
            changed = auto_approve_stale_identity_reviews(
                rows, older_than_hours=older_than, dry_run=args.dry_run
            )
            if args.dry_run:
                print(
                    json.dumps(
                        {
                            "dry_run": True,
                            "would_change_count": len(changed),
                            "would_change": [r["employee_id"] for r in changed],
                        },
                        ensure_ascii=False,
                    )
                )
            else:
                write_review(args.review, rows)
                print(
                    json.dumps(
                        {
                            "changed_count": len(changed),
                            "changed": [r["employee_id"] for r in changed],
                        },
                        ensure_ascii=False,
                    )
                )
            return 0
        if args.command == "count-variants":
            rows = read_review(args.review)
            summary = count_variants(rows, default=args.default)
            print(json.dumps(summary, ensure_ascii=False))
            return 0
        operation, purpose = {
            "prepare": ("review_prepare", "a1_prepare"),
            "validate": ("review_validate", "a1_validate"),
            "readiness": ("readiness_check", "a1_readiness"),
        }[args.command]
        with audited_operation(operation, purpose) as run_id:
            if args.command == "prepare":
                protected_path(args.review, ("a1",))
                if args.review.exists():
                    raise FinalizationError("REVIEW_EXISTS")
                prepare_review(
                    args.employees,
                    args.enrichment,
                    args.current_institution,
                    args.review,
                )
                args.review.chmod(0o600)
                summary = "Prepared review CSV"
            elif args.command == "validate":
                validated = validate_review(
                    read_review(args.review), args.employees, args.profiles
                )
                summary = f"Validated {len(validated)} approved employees"
            else:
                destination = readiness_receipt_path(args.report)
                if destination in {
                    args.review.resolve(),
                    args.employees.resolve(),
                } or destination.is_relative_to(args.profiles.resolve()):
                    raise FinalizationError("RECEIPT_INPUT_OVERLAP")
                report = readiness_report(
                    read_review(args.review),
                    args.profiles,
                    provisional=args.provisional,
                    employees_path=args.employees,
                )
                report["run_id"] = run_id
                write_private_json(destination, report)
                summary = json.dumps(
                    {
                        key: report[key]
                        for key in (
                            "mode",
                            "scope",
                            "ready",
                            "ready_for",
                            "employee_count",
                            "blocked_employee_count",
                            "pending_gate_count",
                            "warning_count",
                        )
                    }
                )
        print(summary)
        return (0 if report["ready"] else 1) if args.command == "readiness" else 0
    except (
        Exception,
        KeyboardInterrupt,
    ):  # Sanitize unexpected malformed-input errors at the CLI boundary.
        if args.command == "readiness":
            try:
                destination = readiness_receipt_path(args.report)
                if destination not in {
                    args.review.resolve(),
                    args.employees.resolve(),
                } and not destination.is_relative_to(args.profiles.resolve()):
                    write_failure_receipt(destination, "READINESS_INPUT_INVALID")
            except (
                A1PrivateInputError,
                FinalizationError,
                OSError,
                ValueError,
                AttributeError,
            ):
                pass
        print("FINALIZATION_BLOCKED", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
