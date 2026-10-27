#!/usr/bin/env python3
"""Merge private scan, OCR and operator-review sources into retained CSV exports.

The export is a proposal package, not an A1 acceptance or issuance record. It
records source precedence, per-field provenance, conflicts and scan hashes while
writing only into a private retained runtime directory.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
SCAN_DIRS = ("scans/processed", "scans/incoming")
A1_REVIEW = "a1/review.csv"
PEOPLE_REVIEW = "ocr/new_people_review.csv"
OCR2 = "ocr/new_scans_ocr2.json"
OCR1_MERGED = "ocr/new_scans_merged.json"
OCR1_RAW = "ocr/new_scans_ocr.json"
INSTITUTIONS_DIR = "config/institutions"
RESEARCH_GLOB = "runtime/portal/temporary/ossz-research-*/report.json"
# Local OCR proposals produced by the research extractor
# (runtime/portal/temporary/retained/ocr-scanonly-cache/). Absent by default so
# the export stays deterministic; present only where that cache exists.
OCR_PROPOSALS_DIR = "runtime/portal/temporary/retained/ocr-scanonly-cache"
OCR_PROPOSAL_FIELD_MAP = {
    "family_name": "surname",
    "given_name": "given_name",
    "birth_date": "dob",
    "birth_place": "birth_place",
    "nationality": "nationality",
    "sex": "sex",
    "document_number": "op_document_number_raw",
    "personal_identifier": "rodne_cislo",
    "insurance_number": "insurance_number",
    "insurer": "insurer",
    "issuing_authority": "issuing_authority",
    "issue_date": "issue_date",
    "expiry_date": "op_valid_to",
}
# Findings that mean the value itself is unusable. Source-level findings
# (unlabelled card, pass disagreement) are advisory: the value is still the
# best available reading and must not be silently dropped.
OCR_VALUE_INVALID_FINDINGS = {
    "invalid_date", "invalid_identifier", "invalid_ocr",
    "mrz_checksum_or_date_invalid", "classification_unresolved",
}

CORE_FIELDS = (
    "surname", "given_name", "dob", "rodne_cislo", "street", "house_number",
    "city", "postal_code", "country_code",
)
INSURANCE_FIELDS = {
    "insurance_number", "insurer", "insurer_code", "zp_card_valid_until",
}
OP_FIELDS = {
    "rodne_cislo", "op_valid_from", "op_valid_to", "op_document_number_raw",
    "issuing_authority",
}

WORKER_FIELDS = (
    "surname", "given_name", "dob", "birth_place", "nationality", "sex",
    "rodne_cislo", "insurance_number", "insurer", "insurer_code",
    "op_valid_from", "op_valid_to", "op_document_number_raw",
    "zp_card_valid_until", "birth_district",
    "street", "house_number", "city", "district", "postal_code",
    "postal_code_source", "country_code", "issuing_authority",
    "status_profile", "activity_name", "activity_address",
    "employment_id", "employment_name", "employment_street",
    "employment_house_number", "employment_city", "employment_postal_code",
    "employment_country_code", "emp_data_verified",
    "resolved_ossz", "institution_profile",
    "document_id", "start_date", "end_date", "issue_date", "signed_by",
    "identity_reviewed", "certificate_reviewed", "approved_for_pdf",
    "pdf_created", "validated_by_user",
    "activity_source", "activity_source_status",
    "certificate_source", "certificate_source_status",
    "signatory_source", "signatory_source_status",
)

WORKER_COLUMNS = (
    ("employee_id",)
    + WORKER_FIELDS
    + ("comments",)
    + (
        "data_status", "has_scan", "scan_count", "has_ocr",
        "has_a1_review", "has_people_review", "missing_core_fields",
        "field_sources", "source_scans", "review_source_scans_declared",
        "review_source_scan_status", "has_ocr_proposal", "ocr_proposal_count",
    )
)

A1_FIELDS = (
    "surname", "given_name", "dob", "birth_place", "nationality", "sex",
    "insurance_number", "street", "house_number", "city", "district",
    "postal_code", "country_code", "status_profile", "activity_name",
    "activity_address", "employment_id", "employment_name",
    "employment_street", "employment_house_number", "employment_city",
    "employment_postal_code", "employment_country_code", "emp_data_verified",
    "resolved_ossz", "institution_profile", "document_id", "start_date",
    "end_date", "issue_date", "signed_by", "identity_reviewed",
    "certificate_reviewed", "approved_for_pdf", "pdf_created",
    "validated_by_user", "activity_source", "activity_source_status",
    "certificate_source", "certificate_source_status", "signatory_source",
    "signatory_source_status",
)

PEOPLE_FIELDS = (
    "surname", "given_name", "dob", "birth_place", "nationality", "sex",
    "rodne_cislo", "insurer", "op_valid_from", "op_valid_to", "street",
    "house_number", "city", "district", "postal_code", "country_code",
    "issuing_authority", "resolved_ossz", "institution_profile",
)

OCR_ALIASES = {
    "personal_id_number": "op_document_number_raw",
    "document_id": "op_document_number_raw",
    "address_street": "street",
    "address_house": "house_number",
    "address_city": "city",
    "address_district": "district",
    "birth_district": "birth_district",
    "card_valid_until": "zp_card_valid_until",
    "insurer_code": "insurer_code",
    "postal_code_source": "postal_code_source",
}

DOC_SUFFIX = re.compile(
    r"-(op_rp|op|zp|firmy)((?:[-_]?zp)?)(?:[-_]?(\d+))?$", re.IGNORECASE
)
DOC_LABELS = {"op": "OP", "zp": "ZP", "firmy": "FIRMY", "op_rp": "OP_RP"}
SCAN_SUFFIXES = {".jpeg", ".jpg", ".png", ".pdf"}
NON_ALNUM = re.compile(r"[^a-z0-9]+")


class ExportError(RuntimeError):
    """A private export precondition failed without exposing values."""


@dataclass(frozen=True)
class Record:
    employee_id: str
    source: str
    label: str
    source_rank: int
    doc_index: int
    doc_name: str
    doc_type: str
    fields: dict[str, str] = field(default_factory=dict)


def clean(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"none", "null"} else text


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def read_json(path: Path) -> Any:
    return json.loads(read_text(path))


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def split_scan_name(name: str) -> tuple[str, str, str]:
    stem = Path(name).stem
    if stem == "zamestnanec-differences-against-osvc-at-a1_form":
        return "_reference", "REFERENCE", "reference"
    match = DOC_SUFFIX.search(stem)
    if not match:
        return "", "OTHER", ""
    worker_id = stem[: match.start()]
    base = match.group(1).lower()
    label = DOC_LABELS[base]
    if match.group(2):
        label += "+ZP"
    suffix = f"{base}{match.group(2) or ''}{match.group(3) or ''}"
    return worker_id, label, suffix


def iter_scan_files(root: Path = REPO_ROOT) -> Iterable[Path]:
    for relative in SCAN_DIRS:
        scan_root = root / relative
        if not scan_root.is_dir():
            continue
        for path in sorted(scan_root.rglob("*")):
            if path.is_file():
                yield path


def name_from_worker_id(employee_id: str) -> tuple[str, str]:
    """Split a scan-derived worker id into (surname, given_name).

    The scan filename is the only declared identity source for scan-only
    workers, so the name recorded here is machine-derived, not reviewed.
    """
    if not employee_id or employee_id.startswith("_"):
        return "", ""
    parts = employee_id.split("-")
    if len(parts) < 2:
        return "", ""
    return parts[0].title(), "-".join(parts[1:-1]).title() if len(parts) > 2 else parts[1].title()


def normalize_for_compare(field_name: str, value: str) -> str:
    text = " ".join(value.strip().split())
    if field_name == "country_code":
        upper = text.upper().replace(" ", "")
        return "CZ" if upper == "CZE" else upper
    if field_name in {
        "insurance_number", "rodne_cislo", "op_document_number_raw",
        "employment_id",
    }:
        return re.sub(r"\s+", "", text).casefold()
    return text.casefold()


def doc_preference(field_name: str, doc_type: str) -> int:
    if field_name in INSURANCE_FIELDS:
        return 0 if "ZP" in doc_type else 1
    if field_name in OP_FIELDS:
        return 0 if "OP" in doc_type else 1
    return 0


def selection_key(record: Record, field_name: str) -> tuple[Any, ...]:
    return (
        record.source_rank,
        doc_preference(field_name, record.doc_type),
        record.doc_name,
        record.doc_index,
    )


def load_ocr_proposals(root: Path) -> tuple[
    dict[str, list[Record]], dict[str, list[dict[str, str]]]]:
    """Load local OCR proposals as low-precedence records.

    Each proposal is a machine reading with confidence and findings. Values
    whose findings say the value itself is unusable are dropped and recorded
    in the second return value so they stay visible; source-level findings
    (unlabelled card, pass disagreement) are advisory and the value is kept.
    The cache is optional and absent by default.
    """
    directory = root / OCR_PROPOSALS_DIR
    records: dict[str, list[Record]] = {}
    dropped: dict[str, list[dict[str, str]]] = {}
    if not directory.is_dir():
        return records, dropped
    for path in sorted(directory.glob("*.json")):
        try:
            data = json.loads(read_text(path))
        except (OSError, ValueError):
            continue
        employee_id = clean(data.get("employee_id"))
        scan = clean(data.get("scan"))
        if not employee_id or not scan:
            continue
        fields: dict[str, str] = {}
        worker_dropped: list[dict[str, str]] = []
        for proposal in data.get("fields", []):
            if not isinstance(proposal, dict):
                continue
            findings = [f for f in (proposal.get("findings") or []) if f]
            col = OCR_PROPOSAL_FIELD_MAP.get(proposal.get("field"))
            if not col:
                continue
            value = clean(proposal.get("value"))
            if not value:
                continue
            if set(findings) & OCR_VALUE_INVALID_FINDINGS:
                worker_dropped.append({
                    "employee_id": employee_id,
                    "scan": scan,
                    "field": proposal.get("field"),
                    "value": value,
                    "findings": ";".join(findings),
                })
                continue
            if fields.get(col):
                continue
            fields[col] = value
        if not fields:
            continue
        records.setdefault(employee_id, []).append(Record(
            employee_id, "ocr_proposal", f"ocr_proposal:{scan}", 5, 0, scan,
            "OCR_PROPOSAL", fields,
        ))
        if worker_dropped:
            dropped.setdefault(employee_id, []).extend(worker_dropped)
    return records, dropped


def collect_records(root: Path = REPO_ROOT) -> tuple[
    dict[str, list[Record]], dict[str, dict[str, str]],
    dict[str, dict[str, str]], dict[str, list[str]], dict[str, list[str]],
    list[dict[str, str]], dict[str, Path],
]:
    records: dict[str, list[Record]] = {}
    a1_rows: dict[str, dict[str, str]] = {}
    people_rows: dict[str, dict[str, str]] = {}
    declared: dict[str, list[str]] = {}
    declared_by: dict[str, list[str]] = {}
    unmapped: list[dict[str, str]] = []
    inputs: dict[str, Path] = {}

    def add_record(record: Record) -> None:
        if not record.employee_id:
            return
        if not any(record.fields.values()):
            return
        records.setdefault(record.employee_id, []).append(record)

    a1_path = root / A1_REVIEW
    if a1_path.is_file():
        inputs[A1_REVIEW] = a1_path
        for row in read_rows(a1_path):
            employee_id = clean(row.get("employee_id"))
            if not employee_id:
                continue
            a1_rows[employee_id] = row
            fields = {name: clean(row.get(name)) for name in A1_FIELDS}
            add_record(Record(
                employee_id, "a1_review", "a1_review", 0, 0, "", "REVIEW", fields
            ))
            scans = [part.strip() for part in clean(row.get("source_scans")).split(";") if part.strip()]
            if scans:
                declared.setdefault(employee_id, []).extend(scans)
                declared_by.setdefault(employee_id, []).extend([A1_REVIEW] * len(scans))

    people_path = root / PEOPLE_REVIEW
    if people_path.is_file():
        inputs[PEOPLE_REVIEW] = people_path
        for row in read_rows(people_path):
            employee_id = clean(row.get("employee_id"))
            if not employee_id:
                continue
            people_rows[employee_id] = row
            fields = {name: clean(row.get(name)) for name in PEOPLE_FIELDS}
            fields["insurance_number"] = clean(row.get("health_insurance_number"))
            fields["comments"] = clean(row.get("comments"))
            add_record(Record(
                employee_id, "people_review", "people_review", 1, 0, "", "REVIEW", fields
            ))
            scans = [part.strip() for part in clean(row.get("source_scans")).split(";") if part.strip()]
            if scans:
                declared.setdefault(employee_id, []).extend(scans)
                declared_by.setdefault(employee_id, []).extend([PEOPLE_REVIEW] * len(scans))

    ocr_specs = (
        (OCR2, 2, "ocr2"),
        (OCR1_MERGED, 3, "ocr1_merged"),
        (OCR1_RAW, 4, "ocr1_raw"),
    )
    for relative, rank, source in ocr_specs:
        path = root / relative
        if not path.is_file():
            continue
        inputs[relative] = path
        data = read_json(path)
        if not isinstance(data, dict):
            raise ExportError(f"Unexpected OCR structure in {relative}")
        index = 0
        for key in sorted(data):
            payload = data[key]
            if source == "ocr1_merged":
                if not isinstance(payload, list):
                    raise ExportError(f"Unexpected OCR merge structure in {relative}")
                for item in payload:
                    if not isinstance(item, list) or len(item) != 2:
                        raise ExportError(f"Unexpected OCR merge entry in {relative}")
                    filename, raw_fields = item
                    if not isinstance(raw_fields, dict):
                        continue
                    employee_id, doc_type, _ = split_scan_name(str(filename))
                    fields = map_ocr_fields(raw_fields)
                    add_record(Record(
                        employee_id, source, f"{source}:{filename}", rank, index,
                        str(filename), doc_type, fields,
                    ))
                    index += 1
                continue
            if not isinstance(payload, dict):
                continue
            raw_fields = payload.get("fields")
            if not isinstance(raw_fields, dict):
                continue
            employee_id, doc_type, _ = split_scan_name(str(key))
            fields = map_ocr_fields(raw_fields)
            add_record(Record(
                employee_id, source, f"{source}:{key}", rank, index,
                str(key), doc_type, fields,
            ))
            index += 1

    for record in records.values():
        for current in record:
            for raw_key in current.fields.get("_unmapped", "").split(","):
                if raw_key:
                    unmapped.append({
                        "employee_id": current.employee_id,
                        "source": current.label,
                        "raw_field": raw_key,
                    })
    return records, a1_rows, people_rows, declared, declared_by, unmapped, inputs


def map_ocr_fields(raw_fields: dict[str, Any]) -> dict[str, str]:
    fields: dict[str, str] = {}
    unknown: list[str] = []
    for key, value in raw_fields.items():
        name = OCR_ALIASES.get(key, key)
        if name in WORKER_FIELDS or name == "comments":
            candidate = clean(value)
            if candidate and not fields.get(name):
                fields[name] = candidate
            continue
        if key not in {"model", "cost", "raw"}:
            unknown.append(key)
    if unknown:
        fields["_unmapped"] = ",".join(sorted(unknown))
    return fields


def build_scan_inventory(
    root: Path = REPO_ROOT,
) -> tuple[list[dict[str, str]], dict[str, list[str]], str]:
    rows: list[dict[str, str]] = []
    worker_scans: dict[str, list[str]] = {}
    file_hashes: list[str] = []
    for path in iter_scan_files(root):
        relative = path.relative_to(root).as_posix()
        name = path.name
        suffix = path.suffix.lower()
        worker_id, doc_type, doc_suffix = split_scan_name(name)
        parent = path.parent
        if not worker_id and parent.name not in {"processed", "incoming"}:
            worker_id = parent.name
        if not worker_id:
            worker_id = "_unassigned"
        if suffix in SCAN_SUFFIXES and doc_type != "REFERENCE":
            kind = "SCAN"
            is_scan = "1"
        elif suffix in {".json"}:
            kind = "OCR_OUTPUT"
            is_scan = "0"
        elif suffix in {".md", ".txt"}:
            kind = "NOTE"
            is_scan = "0"
        else:
            kind = "OTHER"
            is_scan = "0"
        if doc_type == "REFERENCE":
            is_scan = "0"
        digest = sha256_file(path)
        file_hashes.append(f"{digest}:{path.stat().st_size}")
        modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
        rows.append({
            "path": relative,
            "filename": name,
            "worker_id": worker_id,
            "doc_type": doc_type,
            "doc_suffix": doc_suffix,
            "kind": kind,
            "is_scan": is_scan,
            "bytes": str(path.stat().st_size),
            "sha256": digest,
            "modified_at": modified,
            "duplicate_basename": "NO",
            "duplicate_sha_of": "",
        })
        if is_scan == "1" and not worker_id.startswith("_"):
            worker_scans.setdefault(worker_id, []).append(relative)
    basename_counts: dict[str, int] = {}
    for row in rows:
        basename_counts[row["filename"]] = basename_counts.get(row["filename"], 0) + 1
    first_by_sha: dict[str, str] = {}
    for row in sorted(rows, key=lambda item: item["path"]):
        row["duplicate_basename"] = "YES" if basename_counts[row["filename"]] > 1 else "NO"
        previous = first_by_sha.get(row["sha256"])
        if previous:
            row["duplicate_sha_of"] = previous
        else:
            first_by_sha[row["sha256"]] = row["path"]
    tree_hash = sha256_bytes("\n".join(sorted(file_hashes)).encode("utf-8"))
    return rows, worker_scans, tree_hash


def build_worker_rows(
    records: dict[str, list[Record]],
    worker_scans: dict[str, list[str]],
    declared: dict[str, list[str]],
    declared_by: dict[str, list[str]],
    scan_status: dict[str, set[str]],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    worker_ids = sorted(set(worker_scans) | set(records))
    rows: list[dict[str, str]] = []
    conflicts: list[dict[str, str]] = []
    for employee_id in worker_ids:
        worker_records = sorted(
            records.get(employee_id, []),
            key=lambda record: (record.source_rank, record.doc_index, record.doc_name),
        )
        values: dict[str, str] = {}
        sources: dict[str, str] = {}
        for name in WORKER_FIELDS:
            candidates = [
                (record.fields.get(name, ""), record)
                for record in worker_records
                if clean(record.fields.get(name))
            ]
            if not candidates:
                continue
            value, record = min(candidates, key=lambda item: selection_key(item[1], name))
            values[name] = clean(value)
            sources[name] = record.label
            groups: dict[str, list[tuple[str, str]]] = {}
            for candidate, candidate_record in candidates:
                key = normalize_for_compare(name, clean(candidate))
                groups.setdefault(key, []).append(
                    (clean(candidate), candidate_record.label)
                )
            if len(groups) > 1:
                alternatives = [
                    {"value": candidate, "source": label}
                    for key, group in sorted(groups.items())
                    if key != normalize_for_compare(name, values[name])
                    for candidate, label in group
                ]
                conflicts.append({
                    "employee_id": employee_id,
                    "field": name,
                    "chosen_value": values[name],
                    "chosen_source": sources[name],
                    "alternative_count": str(len(groups) - 1),
                    "alternatives": json.dumps(
                        alternatives, ensure_ascii=False, sort_keys=True
                    ),
                })
        for name in ("surname", "given_name"):
            if values.get(name) and name not in sources:
                sources[name] = "scan_filename"
            elif not values.get(name) and name not in sources:
                derived = name_from_worker_id(employee_id)[0 if name == "surname" else 1]
                if derived:
                    values[name] = derived
                    sources[name] = "scan_filename"
        comments = []
        for record in worker_records:
            if record.source in {"a1_review", "people_review"}:
                comment = clean(record.fields.get("comments"))
                if comment and comment not in comments:
                    comments.append(comment)
        scans = sorted(worker_scans.get(employee_id, []))
        declared_paths = declared.get(employee_id, [])
        declared_labels = declared_by.get(employee_id, [])
        statuses = scan_status.get(employee_id, set())
        if not declared_paths:
            review_status = "NONE"
        elif statuses <= {"RESOLVED_BY_BASENAME"}:
            review_status = "RESOLVED"
        else:
            review_status = "MISMATCH"
        has_a1 = any(record.source == "a1_review" for record in worker_records)
        has_people = any(record.source == "people_review" for record in worker_records)
        has_ocr = any(record.source.startswith("ocr1") or record.source == "ocr2" for record in worker_records)
        if has_a1:
            data_status = "REVIEWED"
        elif has_people:
            data_status = "OCR_REVIEWED"
        elif has_ocr:
            data_status = "OCR_ONLY"
        elif scans:
            data_status = "SCAN_ONLY"
        else:
            data_status = "UNKNOWN"
        missing = [name for name in CORE_FIELDS if not values.get(name)]
        row: dict[str, str] = {"employee_id": employee_id}
        for name in WORKER_FIELDS:
            row[name] = values.get(name, "")
        row["comments"] = " | ".join(comments)
        row["data_status"] = data_status
        row["has_scan"] = "YES" if scans else "NO"
        row["scan_count"] = str(len(scans))
        row["has_ocr"] = "YES" if has_ocr else "NO"
        row["has_a1_review"] = "YES" if has_a1 else "NO"
        row["has_people_review"] = "YES" if has_people else "NO"
        row["missing_core_fields"] = ";".join(missing)
        row["field_sources"] = json.dumps(
            {name: sources[name] for name in sorted(sources)},
            ensure_ascii=False, sort_keys=True,
        )
        proposal_records = [r for r in worker_records if r.source == "ocr_proposal"]
        row["has_ocr_proposal"] = "YES" if proposal_records else "NO"
        row["ocr_proposal_count"] = str(len(proposal_records))
        row["source_scans"] = ";".join(scans)
        row["review_source_scans_declared"] = ";".join(declared_paths)
        row["review_source_scan_status"] = review_status
        rows.append(row)
    return rows, conflicts


def build_scan_status(
    inventory: list[dict[str, str]],
    declared: dict[str, list[str]],
    declared_by: dict[str, list[str]],
) -> tuple[dict[str, set[str]], list[dict[str, str]]]:
    by_basename: dict[str, list[str]] = {}
    for row in inventory:
        by_basename.setdefault(row["filename"], []).append(row["path"])
    status_by_worker: dict[str, set[str]] = {}
    mismatches: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for employee_id in sorted(declared):
        for declared_path, source in zip(declared[employee_id], declared_by[employee_id]):
            basename = Path(declared_path).name
            matches = sorted(by_basename.get(basename, []))
            if len(matches) == 1:
                status = "RESOLVED_BY_BASENAME"
                resolved = matches[0]
            elif len(matches) > 1:
                status = "AMBIGUOUS"
                resolved = ";".join(matches)
            else:
                status = "MISSING"
                resolved = ""
            key = (employee_id, declared_path, source)
            if key in seen:
                continue
            seen.add(key)
            status_by_worker.setdefault(employee_id, set()).add(status)
            mismatches.append({
                "employee_id": employee_id,
                "declared_by": source,
                "declared_path": declared_path,
                "resolved_path": resolved,
                "status": status,
            })
    return status_by_worker, mismatches


def build_duplicates(inventory: list[dict[str, str]]) -> list[dict[str, str]]:
    pairs: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    by_sha: dict[str, list[str]] = {}
    by_name: dict[str, list[str]] = {}
    for row in inventory:
        if row["is_scan"] != "1":
            continue
        by_sha.setdefault(row["sha256"], []).append(row["path"])
        by_name.setdefault(row["filename"], []).append(row["path"])
    for paths in by_sha.values():
        for other in sorted(paths)[1:]:
            key = (sorted(paths)[0], other, "SHA256")
            if key not in seen:
                seen.add(key)
                pairs.append({
                    "path_a": key[0], "path_b": key[1], "reason": "SHA256",
                })
    for paths in by_name.values():
        for other in sorted(paths)[1:]:
            key = (sorted(paths)[0], other, "BASENAME")
            if key not in seen:
                seen.add(key)
                pairs.append({
                    "path_a": key[0], "path_b": key[1], "reason": "BASENAME",
                })
    return pairs


def placeholder_fields(value: Any, prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).startswith("_"):
                continue
            child = f"{prefix}.{key}" if prefix else str(key)
            found.extend(placeholder_fields(item, child))
    elif isinstance(value, str):
        text = value.strip()
        if "(doplnit" in text.casefold() or text.upper() in {"TBD", "TO_BE_DETERMINED"}:
            found.append(prefix)
    return found


def build_offices(
    root: Path = REPO_ROOT,
) -> tuple[list[dict[str, str]], dict[str, dict[str, str]], list[Path]]:
    rows: list[dict[str, str]] = []
    by_profile: dict[str, dict[str, str]] = {}
    paths: list[Path] = []
    directory = root / INSTITUTIONS_DIR
    if not directory.is_dir():
        return rows, by_profile, paths
    for path in sorted(directory.glob("*.json")):
        paths.append(path)
        data = read_json(path)
        institution = data.get("institution") or {}
        contact = data.get("current_office_contact") or {}
        profile = path.stem
        row = {
            "institution_profile": profile,
            "expected_ossz": clean(data.get("expected_ossz")),
            "review_status": clean(data.get("review_status")),
            "institution_name": clean(institution.get("name")),
            "street": clean(institution.get("street")),
            "house_number": clean(institution.get("house_number")),
            "city": clean(institution.get("city")),
            "postal_code": clean(institution.get("postal_code")),
            "country_code": clean(institution.get("country_code")),
            "institution_code": clean(institution.get("code")),
            "member_state": clean(data.get("member_state")),
            "contact_name": clean(contact.get("name")),
            "contact_role": clean(contact.get("role")),
            "contact_status": clean(contact.get("status")),
            "signed_by": clean(data.get("signed_by")),
            "source_url": clean(data.get("source_url")),
            "verified_on": clean(data.get("verified_on")),
            "version": clean(data.get("version")),
            "profile_path": path.relative_to(root).as_posix(),
            "profile_sha256": sha256_file(path),
            "placeholder_fields": ";".join(
                placeholder_fields({
                    "institution": institution,
                    "current_office_contact": contact,
                })
            ),
        }
        rows.append(row)
        by_profile[profile] = row
    return rows, by_profile, paths


def build_employers(
    workers: list[dict[str, str]],
    root: Path = REPO_ROOT,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Merge employment ids across workers, ARES registry reads and the
    normalized employee record, and flag review-source conflicts.

    `a1/review.csv` and `a1/<worker>/review.csv` may disagree about the same
    worker's employer. Where the per-worker review matches an ARES record it
    wins; otherwise the conflict is recorded instead of silently resolved.
    """
    ARES_DIR = "runtime/portal/temporary/ares-review"
    NORMALIZED = "a1/employees_normalized.json"
    by_id: dict[str, dict[str, str]] = {}
    for worker in workers:
        eid = clean(worker.get("employment_id"))
        if not eid:
            continue
        entry = by_id.setdefault(eid, {
            "employment_id": eid,
            "employment_name": clean(worker.get("employment_name")),
            "country_code": clean(worker.get("employment_country_code")),
            "kind": "",
            "workers": [],
            "street": clean(worker.get("employment_street")),
            "house_number": clean(worker.get("employment_house_number")),
            "city": clean(worker.get("employment_city")),
            "postal_code": clean(worker.get("employment_postal_code")),
        })
        entry["workers"].append(worker["employee_id"])
        if worker["data_status"] == "REVIEWED":
            entry["kind"] = "reviewed"

    normalized_path = root / NORMALIZED
    if normalized_path.is_file():
        try:
            data = json.loads(read_text(normalized_path))
        except (OSError, ValueError):
            data = {}
        for record in data.get("employees", []) if isinstance(data, dict) else []:
            emp = record.get("employment") or {}
            eid = clean(emp.get("employer_id"))
            if not eid or eid == "<PENDING_OPERATOR_REVIEW>":
                continue
            entry = by_id.setdefault(eid, {
                "employment_id": eid, "employment_name": "", "country_code": "",
                "kind": "normalized", "workers": [],
                "street": "", "house_number": "", "city": "", "postal_code": "",
            })
            entry["employment_name"] = entry["employment_name"] or clean(emp.get("employer_name"))
            entry["country_code"] = entry["country_code"] or clean(emp.get("country_code"))
            entry["street"] = entry["street"] or clean(emp.get("street"))
            entry["house_number"] = entry["house_number"] or clean(emp.get("house_number"))
            entry["city"] = entry["city"] or clean(emp.get("city"))
            entry["postal_code"] = entry["postal_code"] or clean(emp.get("postal_code"))
            entry["workers"].append(clean(record.get("id")))

    ares: dict[str, dict[str, Any]] = {}
    ares_dir = root / "runtime/portal/temporary/ares-review"
    if ares_dir.is_dir():
        for path in sorted(ares_dir.glob("*.json")):
            try:
                data = read_json(path)
            except (OSError, ValueError):
                continue
            rid = clean(data.get("registration_id"))
            if rid:
                ares[rid] = data

    conflicts: list[dict[str, str]] = []
    # A worker can appear under two employment ids when `a1/review.csv` and
    # the per-worker review disagree. Prefer the id that matches ARES; drop
    # the other and record it instead of silently keeping both.
    by_worker: dict[str, list[str]] = {}
    for eid, entry in by_id.items():
        for wid in entry["workers"]:
            by_worker.setdefault(wid, []).append(eid)
    for wid, eids in by_worker.items():
        if len(eids) < 2:
            continue
        matches = [e for e in eids if e in ares]
        keep = matches[0] if matches else sorted(eids)[0]
        for other in eids:
            if other == keep:
                continue
            other_entry = by_id.pop(other, {})
            entry = by_id[keep]
            entry["workers"].extend(other_entry.get("workers", []))
            entry["workers"] = sorted(set(entry["workers"]))
            entry["employment_name"] = entry["employment_name"] or other_entry.get("employment_name", "")
            entry["country_code"] = entry["country_code"] or other_entry.get("country_code", "")
            entry["kind"] = entry["kind"] or other_entry.get("kind", "")
            conflicts.append({
                "employee_id": wid,
                "a1_review_value": f"{other} / {other_entry.get('employment_name', '')}",
                "a1_worker_review_value": f"{keep} / {entry.get('employment_name', '')}",
                "ares_match": keep if keep in ares else "",
                "resolution": (
                    f"dropped {other}; kept {keep} (matches ARES)"
                    if keep in ares else
                    f"dropped {other}; kept {keep} (no ARES record for either id)"
                ),
            })

    rows: list[dict[str, str]] = []
    for eid, entry in sorted(by_id.items()):
        a = ares.get(eid, {})
        addr = a.get("registered_address", {}) or {}
        rows.append({
            "employment_id": eid,
            "employment_name": entry["employment_name"],
            "kind": entry["kind"],
            "country_code": entry["country_code"],
            "workers": ";".join(sorted(set(entry["workers"]))),
            "street": entry["street"] or clean(addr.get("street")),
            "house_number": entry["house_number"] or clean(addr.get("house_number")),
            "city": entry["city"] or clean(addr.get("city")),
            "postal_code": entry["postal_code"] or clean(addr.get("postal_code")),
            "ares_legal_name": clean(a.get("legal_name")),
            "ares_legal_form": clean(a.get("legal_form")),
            "ares_nace": ",".join(a.get("nace_codes", [])),
            "ares_founded_on": clean(a.get("founded_on")),
            "ares_registry_updated_on": clean(a.get("registry_updated_on")),
            "ares_verified_on": clean(a.get("verified_on")),
            "ares_source_url": clean(a.get("source")),
            "ares_content_sha256": clean(a.get("content_sha256")),
            "review_status": "ARES_VERIFIED" if a else "NO_ARES_RECORD",
        })
    return rows, conflicts


def build_worker_ossz(
    workers: list[dict[str, str]],
    offices: dict[str, dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for worker in workers:
        resolved = worker.get("resolved_ossz", "")
        profile = worker.get("institution_profile", "")
        if not resolved and not profile:
            continue
        office = offices.get(profile)
        source = ""
        sources = json.loads(worker.get("field_sources") or "{}")
        for name in ("institution_profile", "resolved_ossz"):
            if sources.get(name):
                source = sources[name]
                break
        notes = []
        if not office:
            notes.append("UNMATCHED_PROFILE")
        elif office.get("review_status") != "VERIFIED":
            notes.append("PROFILE_NOT_VERIFIED")
        rows.append({
            "employee_id": worker["employee_id"],
            "resolved_ossz": resolved,
            "institution_profile": profile,
            "expected_ossz": clean(office.get("expected_ossz")) if office else "",
            "office_match": "YES" if office else "NO",
            "review_status": clean(office.get("review_status")) if office else "",
            "contact_name": clean(office.get("contact_name")) if office else "",
            "contact_status": clean(office.get("contact_status")) if office else "",
            "signed_by": clean(office.get("signed_by")) if office else "",
            "source_url": clean(office.get("source_url")) if office else "",
            "verified_on": clean(office.get("verified_on")) if office else "",
            "source": source,
            "notes": ";".join(notes),
        })
    return rows


def build_research_rows(
    root: Path = REPO_ROOT,
) -> tuple[list[dict[str, str]], list[Path]]:
    rows: list[dict[str, str]] = []
    paths: list[Path] = []
    for path in sorted(root.glob(RESEARCH_GLOB)):
        paths.append(path)
        data = read_json(path)
        fields = data.get("fields") or {}
        address = fields.get("address") or {}
        parsed = address.get("parsed") or {}
        phone = fields.get("phone") or {}
        institution_code = data.get("institution_code") or {}
        sickness = data.get("sickness_insurance_rate") or {}
        sources = data.get("sources") or []
        rows.append({
            "report_path": path.relative_to(root).as_posix(),
            "report_sha256": sha256_file(path),
            "started_at": clean(data.get("started_at")),
            "finished_at": clean(data.get("finished_at")),
            "status": clean(data.get("status")),
            "office": clean(data.get("office")),
            "error_type": clean(data.get("error_type")),
            "error": clean(data.get("error")),
            "address_value": clean(address.get("value")),
            "address_street": clean(parsed.get("street")),
            "address_house_number": clean(parsed.get("house_number")),
            "address_postal_code": clean(parsed.get("postal_code")),
            "address_city": clean(parsed.get("city")),
            "address_status": clean(address.get("status")),
            "phone_value": clean(phone.get("value")),
            "phone_status": clean(phone.get("status")),
            "institution_code_status": clean(institution_code.get("status")),
            "sickness_insurance_rate_status": clean(sickness.get("status")),
            "human_confirmed": "YES" if data.get("human_confirmed") else "NO",
            "source_urls": ";".join(clean(source.get("url")) for source in sources),
            "limitations": " | ".join(clean(item) for item in data.get("limitations") or []),
            "retention_review_due": clean(data.get("retention_review_due")),
        })
    return rows, paths


def write_private_text(path: Path, text: str) -> None:
    fd = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600
    )
    try:
        os.fchmod(fd, 0o600)
    except Exception:
        os.close(fd)
        raise
    with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
        handle.write(text)


def write_csv(path: Path, columns: Iterable[str], rows: list[dict[str, str]]) -> None:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(
        buffer, fieldnames=list(columns), extrasaction="raise", lineterminator="\n"
    )
    writer.writeheader()
    writer.writerows(rows)
    write_private_text(path, buffer.getvalue())


def write_json(path: Path, payload: Any) -> None:
    write_private_text(
        path, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )


def output_details(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "file": path.name,
        "sha256": sha256_file(path),
        "bytes": stat.st_size,
        "mode": oct(stat.st_mode & 0o777),
    }


def _path_relative_to(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.name


def input_details(path: Path, root: Path = REPO_ROOT) -> dict[str, Any]:
    return {
        "path": _path_relative_to(path, root),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }


def choose_output_dir(root: Path, requested: str | None) -> Path:
    if requested:
        outdir = Path(requested).expanduser()
        if not outdir.is_absolute():
            outdir = root / outdir
        outdir = outdir.resolve()
        if not outdir.is_relative_to(root.resolve()):
            raise ExportError("Output directory must remain inside the repository")
        if outdir.exists() and not outdir.is_dir():
            raise ExportError("Output path exists and is not a directory")
        if outdir.exists() and (outdir.stat().st_mode & 0o077):
            raise ExportError(
                "Existing output directory is not private (expected mode 0700)"
            )
        if not outdir.exists():
            outdir.mkdir(mode=0o700, parents=True)
            os.chmod(outdir, 0o700)
        return outdir
    retained = root / "runtime/portal/temporary/retained"
    if not retained.exists():
        retained.mkdir(mode=0o700, parents=True)
        os.chmod(retained, 0o700)
    outdir = retained / uuid.uuid4().hex
    outdir.mkdir(mode=0o700)
    os.chmod(outdir, 0o700)
    return outdir


def limitations_text(counts: dict[str, int]) -> str:
    return f"""# Scan/worker merge limitations

- Export is a private proposal package, not an A1 acceptance, issuance or
  release-accepted record.
- Worker roster contains {counts['workers']} scan-derived workers.
  {counts['reviewed']} have operator A1 review data, {counts['ocr_reviewed']} have
  operator-corrected OCR review data, {counts['ocr_only']} have OCR proposals
  only, and {counts['scan_only']} have scans but no reviewed values.
  {counts['ocr_proposal_workers']} of those carry local OCR proposals
  ({counts['ocr_proposal_fields']} fields) recorded as machine readings, not
  reviewed facts.
- Blank fields are unknown. They are not placeholders and must not be read as
  confirmed facts.
- `a1/review.csv` is authoritative only for the fields and workers it contains.
  It does not carry `rodne_cislo` or OP validity dates.
- OCR values remain proposals. `new_people_review.csv` reflects operator
  corrections but is not an A1 issuance approval. Local OCR proposals in
  `ocr-scanonly-cache/` are machine readings with confidence and findings; they
  are never treated as reviewed facts and are absent by default. Proposals
  whose reading itself is unusable are recorded in
  `ocr_proposal_dropped.csv` rather than silently discarded.
- `op_document_number_raw` preserves ambiguous OCR `personal_id_number` /
  `document_id` values. It is not `rodne_cislo`.
- Conflicts are recorded in `conflicts.csv`; the highest-precedence source wins.
  Conflict alternatives are preserved, not adjudicated.
- Worker-to-OSSZ mapping exists only where a review source states it
  ({counts['worker_ossz']} workers).
- OSSZ office profiles come from `{INSTITUTIONS_DIR}`. Non-VERIFIED profiles
  (including PROVISIONAL and NEEDS_VERIFICATION) are not final approval.
- OSSZ research run reports are contact/address probes, not institution profile
  approval. A FAILED run is retained for provenance only.
- Some `a1/review.csv` source scan paths are stale; `scan_source_mismatches.csv`
  resolves them by basename where possible and marks missing or ambiguous links.
- Worker identity comes from scan filenames and declared rosters. Page content is
  not re-inspected, so a swapped or misfiled page cannot be detected here. Scan-only
  workers carry a machine-derived name from the filename; it is not reviewed.
- Outputs are private retained runtime artifacts with a 90-day retention review.
  They must not be committed, published or attached to tickets.
- Next owner: operator/Jan for review of scan-only workers, conflict adjudication,
  and verification of non-VERIFIED OSSZ profiles.
  - {counts['employers']} employers are recorded in `employers.csv`;
    {counts['employers_ares_verified']} match an ARES registry read. Employer
    identity is not reviewed here: an employment id that has no ARES record
    (or a review-source conflict in `employer_source_conflicts.csv`) must be
    resolved before any A1 activity is issued.
"""


def run(root: Path, output_dir: str | None, retention_days: int) -> Path:
    if not root.is_dir():
        raise ExportError("Repository root is unavailable")
    records, a1_rows, people_rows, declared, declared_by, unmapped, inputs = collect_records(root)
    ocr_proposal_records, dropped_proposals = load_ocr_proposals(root)
    for employee_id, proposal_records in ocr_proposal_records.items():
        records.setdefault(employee_id, []).extend(proposal_records)
    inventory, worker_scans, scans_tree_hash = build_scan_inventory(root)
    scan_status, mismatches = build_scan_status(inventory, declared, declared_by)
    workers, conflicts = build_worker_rows(
        records, worker_scans, declared, declared_by, scan_status
    )
    duplicates = build_duplicates(inventory)
    offices, offices_by_profile, office_paths = build_offices(root)
    worker_ossz = build_worker_ossz(workers, offices_by_profile)
    research, research_paths = build_research_rows(root)
    employers, employer_conflicts = build_employers(workers, root)

    outdir = choose_output_dir(root, output_dir)
    os.umask(0o077)
    generated_at = datetime.now(timezone.utc)
    retention_due = (generated_at + timedelta(days=retention_days)).date().isoformat()

    write_csv(outdir / "workers.csv", WORKER_COLUMNS, workers)
    write_csv(
        outdir / "scan_inventory.csv",
        (
            "path", "filename", "worker_id", "doc_type", "doc_suffix", "kind",
            "is_scan", "bytes", "sha256", "modified_at", "duplicate_basename",
            "duplicate_sha_of",
        ),
        inventory,
    )
    write_csv(
        outdir / "worker_ossz.csv",
        (
            "employee_id", "resolved_ossz", "institution_profile", "expected_ossz",
            "office_match", "review_status", "contact_name", "contact_status",
            "signed_by", "source_url", "verified_on", "source", "notes",
        ),
        worker_ossz,
    )
    write_csv(
        outdir / "ossz_offices.csv",
        (
            "institution_profile", "expected_ossz", "review_status",
            "institution_name", "street", "house_number", "city", "postal_code",
            "country_code", "institution_code", "member_state", "contact_name",
            "contact_role", "contact_status", "signed_by", "source_url",
            "verified_on", "version", "profile_path", "profile_sha256",
            "placeholder_fields",
        ),
        offices,
    )
    write_csv(
        outdir / "ossz_research_runs.csv",
        (
            "report_path", "report_sha256", "started_at", "finished_at", "status",
            "office", "error_type", "error", "address_value", "address_street",
            "address_house_number", "address_postal_code", "address_city",
            "address_status", "phone_value", "phone_status",
            "institution_code_status", "sickness_insurance_rate_status",
            "human_confirmed", "source_urls", "limitations",
            "retention_review_due",
        ),
        research,
    )
    write_csv(
        outdir / "conflicts.csv",
        (
            "employee_id", "field", "chosen_value", "chosen_source",
            "alternative_count", "alternatives",
        ),
        conflicts,
    )
    write_csv(
        outdir / "duplicates.csv",
        ("path_a", "path_b", "reason"),
        duplicates,
    )
    write_csv(
        outdir / "scan_source_mismatches.csv",
        ("employee_id", "declared_by", "declared_path", "resolved_path", "status"),
        mismatches,
    )
    write_csv(
        outdir / "employers.csv",
        (
            "employment_id", "employment_name", "kind", "country_code", "workers",
            "street", "house_number", "city", "postal_code", "ares_legal_name",
            "ares_legal_form", "ares_nace", "ares_founded_on",
            "ares_registry_updated_on", "ares_verified_on", "ares_source_url",
            "ares_content_sha256", "review_status",
        ),
        employers,
    )
    write_csv(
        outdir / "employer_source_conflicts.csv",
        ("employee_id", "a1_review_value", "a1_worker_review_value",
         "ares_match", "resolution"),
        employer_conflicts,
    )
    write_csv(
        outdir / "ocr_proposal_dropped.csv",
        ("employee_id", "scan", "field", "value", "findings"),
        [row for rows in dropped_proposals.values() for row in rows],
    )
    write_csv(
        outdir / "unmapped_ocr_fields.csv",
        ("employee_id", "source", "raw_field"),
        unmapped,
    )

    counts = {
        "workers": len(workers),
        "reviewed": sum(1 for row in workers if row["data_status"] == "REVIEWED"),
        "ocr_reviewed": sum(1 for row in workers if row["data_status"] == "OCR_REVIEWED"),
        "ocr_only": sum(1 for row in workers if row["data_status"] == "OCR_ONLY"),
        "scan_only": sum(1 for row in workers if row["data_status"] == "SCAN_ONLY"),
        "worker_ossz": len(worker_ossz),
        "ossz_offices": len(offices),
        "research_runs": len(research),
        "scans": len(inventory),
        "scan_documents": sum(1 for row in inventory if row["is_scan"] == "1"),
        "conflicts": len(conflicts),
        "duplicates": len(duplicates),
        "scan_source_mismatches": len(mismatches),
        "ocr_proposal_workers": sum(1 for row in workers if row["has_ocr_proposal"] == "YES"),
        "ocr_proposal_fields": sum(
            int(row["ocr_proposal_count"]) for row in workers
        ),
        "ocr_proposal_dropped": sum(len(rows) for rows in dropped_proposals.values()),
        "employers": len(employers),
        "employers_ares_verified": sum(
            1 for row in employers if row["review_status"] == "ARES_VERIFIED"
        ),
        "employer_source_conflicts": len(employer_conflicts),
    }

    write_private_text(outdir / "LIMITATIONS.md", limitations_text(counts))

    inputs_payload: list[dict[str, Any]] = [
        input_details(path, root) for path in sorted(set(inputs.values()))
    ]
    inputs_payload.extend(input_details(path, root) for path in office_paths)
    inputs_payload.extend(input_details(path, root) for path in research_paths)
    ares_dir = root / "runtime/portal/temporary/ares-review"
    if ares_dir.is_dir():
        ares_files = sorted(p for p in ares_dir.glob("*.json") if p.is_file())
        inputs_payload.append({
            "path": "runtime/portal/temporary/ares-review",
            "file_count": len(ares_files),
            "tree_sha256": sha256_bytes(
                "\n".join(f"{sha256_file(p)}:{p.name}" for p in ares_files).encode("utf-8")
            ) if ares_files else "",
            "note": "ARES registry reads; not an acceptance record",
        })
    normalized_path = root / "a1/employees_normalized.json"
    if normalized_path.is_file():
        inputs_payload.append(input_details(normalized_path, root))
    cache = root / OCR_PROPOSALS_DIR
    if cache.is_dir():
        cache_files = sorted(p for p in cache.glob("*.json") if p.is_file())
        cache_hash = sha256_bytes(
            "\n".join(f"{sha256_file(p)}:{p.name}" for p in cache_files).encode("utf-8")
        ) if cache_files else ""
        inputs_payload.append({
            "path": OCR_PROPOSALS_DIR,
            "file_count": len(cache_files),
            "tree_sha256": cache_hash,
            "note": "local OCR proposals; absent by default",
        })
    inputs_payload.append({
        "path": "scans",
        "file_count": len(inventory),
        "tree_sha256": scans_tree_hash,
    })

    outputs = [
        path for path in sorted(outdir.iterdir())
        if path.is_file() and path.name not in {"manifest.json"}
    ]
    manifest = {
        "generated_at": generated_at.isoformat(),
        "generator": {
            "path": _path_relative_to(Path(__file__).resolve(), root),
            "sha256": sha256_file(Path(__file__).resolve()),
        },
        "retention": {
            "days": retention_days,
            "review_due": retention_due,
        },
        "counts": counts,
        "inputs": inputs_payload,
        "outputs": [output_details(path) for path in outputs],
        "limitations": "LIMITATIONS.md",
    }
    write_json(outdir / "manifest.json", manifest)

    print(
        f"Wrote {counts['workers']} workers, {counts['worker_ossz']} worker-OSSZ mappings, "
        f"{counts['ossz_offices']} OSSZ offices, {counts['scans']} scan files, "
        f"{counts['conflicts']} conflicts."
    )
    print(f"Private retained output: {outdir}")
    print("Open LIMITATIONS.md before using any value.")
    return outdir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Merge private scan, OCR and review sources into retained CSVs."
    )
    parser.add_argument(
        "--root", default=str(REPO_ROOT), help="Repository root (default: script parent)"
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Explicit private output directory inside the repository",
    )
    parser.add_argument(
        "--retention-days", type=int, default=90,
        help="Retention review interval in days (default: 90)",
    )
    args = parser.parse_args(argv)
    if args.retention_days < 1:
        parser.error("--retention-days must be positive")
    try:
        run(Path(args.root).expanduser().resolve(), args.output_dir, args.retention_days)
    except (ExportError, OSError, json.JSONDecodeError) as error:
        print(f"Export failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
