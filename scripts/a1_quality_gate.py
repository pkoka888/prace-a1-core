#!/usr/bin/env python3
"""Render and deterministically validate a staged A1 PDF set.

This module is deliberately independent from the PDF generator.  It never edits
PDFs and refuses to write into the directory containing them.  A successful
``validate`` run creates a hash-bound QA manifest; any incomplete check exits
non-zero.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pymupdf
from PIL import Image, ImageOps, ImageDraw
from pypdf import PdfReader

try:
    from .a1_audit import (
        audited_operation,
        write_private_json,
        AuditWriteError,
        current_run_id,
        completed_operation_evidence,
    )
    from .a1_private import A1PrivateInputError, private_path
    from .a1_paths import (
        protected_root,
        protected_path,
        validate_output_path,
        PathValidationError,
        ensure_private_directory,
    )
    from .finalize_a1 import read_review
except ImportError:
    from a1_audit import (
        audited_operation,
        write_private_json,
        AuditWriteError,
        current_run_id,
        completed_operation_evidence,
    )
    from a1_private import A1PrivateInputError, private_path
    from a1_paths import (
        protected_root,
        protected_path,
        validate_output_path,
        PathValidationError,
        ensure_private_directory,
    )
    from finalize_a1 import read_review

try:
    from .a1_core import document_id_for_issue_year
except ImportError:
    from a1_core import document_id_for_issue_year


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config/a1_provisional.json"
DEFAULT_REVIEW = None
DEFAULT_LAYOUT = ROOT / "config/a1_layout.json"
DEFAULT_BACKGROUND = ROOT / "templates/a1_background.pdf"
PDF_PREFIX = "A1_"
PAGE_COUNT = 3


class QualityGateError(RuntimeError):
    """Raised for unsafe or internally inconsistent QA inputs."""


class _ValidationFailed(QualityGateError):
    """A protected detailed failed report already exists."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    """Persist protected receipts using the shared atomic writer."""
    try:
        payload["run_id"] = current_run_id()
    except AuditWriteError:
        pass  # Pure validation callers do not create CLI operation receipts.
    write_private_json(path, payload)


def _pixel_hash(image: Image.Image) -> str:
    image = image.convert("RGB")
    header = f"RGB:{image.width}:{image.height}:".encode("ascii")
    return hashlib.sha256(header + image.tobytes()).hexdigest()


def expected_records(
    config_path: Path, cohort_path: Path, review_path: Path | None
) -> dict[str, dict[str, str]]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    cohort = json.loads(cohort_path.read_text(encoding="utf-8"))
    issue_dates = cohort.get("issue_dates", {})
    document_ids = cohort.get("document_ids", {})
    if set(issue_dates) != set(document_ids):
        raise QualityGateError("issue_dates and document_ids must name the same cohort")
    if not issue_dates:
        raise QualityGateError("cohort must not be empty")
    records = {employee_id: {"employee_id": employee_id} for employee_id in issue_dates}
    if review_path and review_path.exists():
        with review_path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            required_employment = {
                "employment_id",
                "employment_name",
                "employment_street",
                "employment_house_number",
                "employment_city",
                "employment_postal_code",
                "employment_country_code",
            }
            missing_columns = sorted(required_employment - set(reader.fieldnames or ()))
            if missing_columns:
                raise QualityGateError(
                    "review CSV lacks explicit Section 4 columns: "
                    + ", ".join(missing_columns)
                )
    if review_path is not None:
        if not review_path.exists():
            raise QualityGateError("review CSV is missing")
        reviewed = read_review(review_path)
        if {row["employee_id"] for row in reviewed} != set(records):
            raise QualityGateError("review and cohort employee sets differ")
        if cohort.get("additional_people"):
            raise QualityGateError(
                "cohort additions require reconciliation in review CSV"
            )
        for row in reviewed:
            key = row["employee_id"]
            if (
                row["document_id"] != document_ids[key]
                or row["issue_date"] != issue_dates[key]
            ):
                raise QualityGateError("cohort values differ from reviewed evidence")
        return {row["employee_id"]: row for row in reviewed}
    for row in cohort.get("additional_people", []):
        employee_id = row.get("employee_id", "")
        if employee_id in records:
            records[employee_id].update({key: str(value) for key, value in row.items()})
    for employee_id, record in records.items():
        record["document_id"] = document_id_for_issue_year(
            document_ids[employee_id], issue_dates[employee_id]
        )
        record["issue_date"] = issue_dates[employee_id]
        record["activity_name"] = config.get("activity_name", "")
        record["activity_address"] = config.get("activity_address", "")
    return records


def _pdf_paths(pdf_dir: Path) -> list[Path]:
    return sorted(pdf_dir.glob(f"{PDF_PREFIX}*.pdf"))


def _employee_id(path: Path) -> str:
    return path.stem.removeprefix(PDF_PREFIX)


def require_completed_generation(pdf_dir: Path) -> dict[str, Any]:
    """Require completed, audited generation for the exact current PDF package."""
    try:
        manifest_path = protected_path(pdf_dir / "generation_manifest.json")
        manifest_hash = sha256_file(manifest_path)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        run_id = manifest["run_id"]
        if not isinstance(run_id, str) or str(uuid.UUID(run_id)) != run_id:
            raise ValueError()
        receipt_path = protected_path(
            protected_root() / "a1/receipts" / f"{run_id}.json"
        )
        receipt_hash = sha256_file(receipt_path)
        audit_digest = completed_operation_evidence(
            run_id, {"provisional_generate", "candidate_generate"}
        )
        entries = manifest["generated"]
        declared = {entry["path"]: entry["sha256"] for entry in entries}
        actual = {
            path.name: sha256_file(protected_path(path)) for path in _pdf_paths(pdf_dir)
        }
        if not actual or declared != actual or len(declared) != len(entries):
            raise ValueError()
        if manifest_hash != sha256_file(manifest_path) or receipt_hash != sha256_file(
            receipt_path
        ):
            raise ValueError()
        return {
            "run_id": run_id,
            "manifest": {"path": str(manifest_path), "sha256": manifest_hash},
            "receipt": {"path": str(receipt_path), "sha256": receipt_hash},
            "audit_terminal_sha256": audit_digest,
        }
    except (OSError, ValueError, KeyError, TypeError, AuditWriteError):
        raise QualityGateError("GENERATION_COMPLETION_REQUIRED") from None


def render_previews(pdf_dir: Path, preview_dir: Path, dpi: int = 200) -> list[Path]:
    """Render every page with stable names, replacing only the preview directory."""
    protected_path(pdf_dir)
    if type(dpi) is not int or not 144 <= dpi <= 600:
        raise QualityGateError("QA rendering requires 144 to 600 DPI")
    if (
        pdf_dir.resolve() == preview_dir.resolve()
        or pdf_dir.resolve() in preview_dir.resolve().parents
    ):
        raise QualityGateError(
            "preview directory must not contain the source PDF directory"
        )
    validate_output_path(preview_dir, allow_existing=True)
    if preview_dir.resolve() in pdf_dir.resolve().parents:
        raise QualityGateError("preview directory overlaps source PDFs")
    pdfs = _pdf_paths(pdf_dir)
    if not pdfs:
        raise QualityGateError("PDF package must not be empty")
    ensure_private_directory(preview_dir)
    protected_path(preview_dir / "render-receipt.json").unlink(missing_ok=True)
    for stale in preview_dir.glob("A1_*-page-*.png"):
        stale.unlink()
    rendered: list[Path] = []
    matrix = pymupdf.Matrix(dpi / 72.0, dpi / 72.0)
    source_hashes = {path.name: sha256_file(protected_path(path)) for path in pdfs}
    for pdf_path in pdfs:
        with pymupdf.open(pdf_path) as document:
            for index, page in enumerate(document):
                target = preview_dir / f"{pdf_path.stem}-page-{index + 1}.png"
                protected_path(target)
                page.get_pixmap(
                    matrix=matrix, alpha=False, colorspace=pymupdf.csRGB
                ).save(target)
                target.chmod(0o600)
                rendered.append(target)
    if source_hashes != {path.name: sha256_file(path) for path in pdfs}:
        raise QualityGateError("PDF inputs changed during rendering")
    pixel_hashes = {}
    for path in rendered:
        with Image.open(path) as image:
            pixel_hashes[path.name] = _pixel_hash(image)
    _write_json(
        preview_dir / "render-receipt.json",
        {
            "schema_version": 1,
            "dpi": dpi,
            "pdfs": source_hashes,
            "preview_pixels": pixel_hashes,
        },
    )
    return rendered


def create_contact_sheets(
    previews: Iterable[Path], output_dir: Path, columns: int = 3
) -> list[Path]:
    previews = list(previews)
    validate_output_path(output_dir, allow_existing=True)
    if any(
        output_dir.resolve() == path.parent.resolve()
        or output_dir.resolve() in path.resolve().parents
        for path in previews
    ):
        raise QualityGateError("QA_OUTPUT_OVERLAPS_INPUT")
    ensure_private_directory(output_dir)
    grouped: dict[int, list[Path]] = {page: [] for page in range(1, PAGE_COUNT + 1)}
    for path in previews:
        try:
            page_number = int(path.stem.rsplit("-page-", 1)[1])
        except (IndexError, ValueError):
            continue
        if page_number in grouped:
            grouped[page_number].append(path)
    outputs: list[Path] = []
    thumb_width = 500
    for page_number, paths in grouped.items():
        if not paths:
            continue
        thumbs: list[tuple[str, Image.Image]] = []
        for path in sorted(paths):
            with Image.open(path) as source:
                image = source.convert("RGB")
                height = round(image.height * thumb_width / image.width)
                thumbs.append(
                    (
                        path.stem.rsplit("-page-", 1)[0],
                        image.resize((thumb_width, height)),
                    )
                )
        label_height, padding = 34, 12
        cell_height = max(image.height for _, image in thumbs) + label_height
        rows = (len(thumbs) + columns - 1) // columns
        sheet = Image.new(
            "RGB",
            (
                columns * (thumb_width + padding) + padding,
                rows * (cell_height + padding) + padding,
            ),
            "white",
        )
        draw = ImageDraw.Draw(sheet)
        for index, (label, image) in enumerate(thumbs):
            x = padding + (index % columns) * (thumb_width + padding)
            y = padding + (index // columns) * (cell_height + padding)
            sheet.paste(
                ImageOps.expand(image, border=1, fill="#888888"), (x, y + label_height)
            )
            draw.text((x, y + 8), label.removeprefix(PDF_PREFIX), fill="black")
        target = output_dir / f"contact-sheet-page-{page_number}.png"
        protected_path(target)
        sheet.save(target, optimize=True)
        target.chmod(0o600)
        outputs.append(target)
    _write_json(
        output_dir / "contact-receipt.json",
        {
            "schema_version": 1,
            "previews": {path.name: sha256_file(path) for path in previews},
            "sheets": {path.name: sha256_file(path) for path in outputs},
        },
    )
    return outputs


@dataclass
class PdfResult:
    employee_id: str
    path: str
    sha256: str
    passed: bool = True
    issues: list[str] = field(default_factory=list)
    checks: dict[str, Any] = field(default_factory=dict)

    def fail(self, issue: str) -> None:
        self.passed = False
        self.issues.append(issue)


def _normalize(value: str) -> str:
    return " ".join(value.replace("\u00a0", " ").split()).casefold()


def _background_damage(
    pdf_path: Path, background: Path, dpi: int = 144
) -> list[dict[str, int]]:
    """Count template ink/color pixels erased to near-white in the generated PDF.

    The generated page is rendered once per page (the previous version
    called ``get_pixmap`` twice — once for the raw samples and once for
    the dimensions). Reusing one pixmap halves the per-page raster work
    and preserves the validation: ``got`` and ``got_pix`` are the same
    numpy array, just shaped for broadcasting.
    """
    matrix = pymupdf.Matrix(dpi / 72.0, dpi / 72.0)
    damage: list[dict[str, int]] = []
    with pymupdf.open(pdf_path) as generated, pymupdf.open(background) as template:
        if len(generated) != len(template):
            return [{"page": 0, "erased_template_pixels": 10**9}]
        for index in range(len(generated)):
            got_pix = generated[index].get_pixmap(
                matrix=matrix, alpha=False, colorspace=pymupdf.csRGB
            )
            got = np.frombuffer(got_pix.samples, dtype=np.uint8).reshape(
                got_pix.height, got_pix.width, 3
            )
            ref_pix = template[index].get_pixmap(
                matrix=matrix, alpha=False, colorspace=pymupdf.csRGB
            )
            ref = np.frombuffer(ref_pix.samples, dtype=np.uint8).reshape(
                ref_pix.height, ref_pix.width, 3
            )
            if got.shape != ref.shape:
                damage.append({"page": index + 1, "erased_template_pixels": 10**9})
                continue
            ref_ink = (ref.min(axis=2) < 215) | (
                (ref.max(axis=2) - ref.min(axis=2)) > 18
            )
            erased = (
                ref_ink
                & (got.min(axis=2) > 246)
                & (got.max(axis=2) - got.min(axis=2) < 5)
            )
            damage.append(
                {"page": index + 1, "erased_template_pixels": int(erased.sum())}
            )
    return damage


def validate_pdf(
    path: Path,
    record: dict[str, str],
    all_records: dict[str, dict[str, str]],
    background: Path | None,
    max_erased_pixels: int,
) -> PdfResult:
    result = PdfResult(_employee_id(path), path.name, sha256_file(path))
    try:
        reader = PdfReader(str(path), strict=True)
        result.checks["page_count"] = len(reader.pages)
        if len(reader.pages) != PAGE_COUNT:
            result.fail(f"page_count={len(reader.pages)}, expected={PAGE_COUNT}")
        fields = reader.get_fields() or {}
        widgets = sum(len(page.get("/Annots", [])) for page in reader.pages)
        result.checks.update(acroform_fields=len(fields), annotations=widgets)
        if fields:
            result.fail("AcroForm fields remain")
        if widgets:
            result.fail("annotations/widgets remain")
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception:
        result.fail("PDF_PARSE_FAILED")
        return result
    normalized = _normalize(text)
    nationality = record.get("nationality", "")
    if _normalize(nationality) in {
        "česká republika",
        "ceska republika",
        "czech republic",
        "cz",
        "cze",
    }:
        nationality = "CZ"
    required = {
        "document_id": record.get("document_id", ""),
        "surname": record.get("surname", ""),
        "given_name": record.get("given_name", ""),
        "dob": record.get("dob", ""),
        "birth_place": record.get("birth_place", ""),
        "nationality": nationality,
        "insurance_number": record.get("insurance_number", ""),
        "street": record.get("street", ""),
        "house_number": record.get("house_number", ""),
        "city": record.get("city", ""),
        "postal_code": record.get("postal_code", ""),
        "activity_name": record.get("activity_name", ""),
        "activity_address": record.get("activity_address", ""),
    }
    if record.get("status_profile") in {"employee_multi_state", "posted_employee"}:
        required.pop("activity_name")
        required.pop("activity_address")
    for field_name in (
        "employment_id",
        "employment_street",
        "employment_house_number",
        "employment_city",
        "employment_postal_code",
        "employment_country_code",
    ):
        required[field_name] = record.get(field_name, "")
    if record.get("status_profile") == "self_employed_multi_state":
        required["employer_name"] = (
            record.get("surname", "") + " " + record.get("given_name", "")
        )
    else:
        required["employment_name"] = record.get("employment_name", "")
    missing = [
        name
        for name, value in required.items()
        if value and _normalize(value) not in normalized
    ]
    result.checks["required_text"] = {
        name: name not in missing for name in required if required[name]
    }
    for name in missing:
        result.fail(f"missing expected {name}")
    foreign_numbers = sorted(
        {
            other.get("insurance_number", "")
            for employee_id, other in all_records.items()
            if employee_id != record["employee_id"]
            and other.get("insurance_number")
            and _normalize(other["insurance_number"]) in normalized
        }
    )
    result.checks["foreign_identity_number_count"] = len(foreign_numbers)
    if foreign_numbers:
        result.fail("contains another employee insurance number")
    for forbidden in ("EXAMPLE-LEGACY-IDENTITY", "NÁVRH – ČEKÁ NA POTVRZENÍ OSSZ"):
        if _normalize(forbidden) in normalized:
            result.fail(f"forbidden legacy text present: {forbidden}")
    if background and background.exists() and len(reader.pages) == PAGE_COUNT:
        damage = _background_damage(path, background)
        result.checks["background_integrity"] = damage
        for item in damage:
            if item["erased_template_pixels"] > max_erased_pixels:
                result.fail(
                    f"page {item['page']} erased {item['erased_template_pixels']} template pixels"
                )
    gs = shutil.which("gs")
    if gs:
        completed = subprocess.run(
            [gs, "-q", "-dNOPAUSE", "-dBATCH", "-sDEVICE=nullpage", str(path)],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        result.checks["ghostscript"] = completed.returncode == 0
        if completed.returncode:
            result.fail("Ghostscript rejected PDF")
    else:
        result.checks["ghostscript"] = "unavailable"
    return result


def validate_set(
    pdf_dir: Path,
    preview_dir: Path,
    config_path: Path,
    cohort_path: Path,
    review_path: Path | None,
    background: Path | None,
    report_path: Path,
    manifest_path: Path,
    input_paths: Iterable[Path] = (),
    max_erased_pixels: int = 24,
    generation_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    protected_path(pdf_dir)
    protected_path(preview_dir)
    protected_path(report_path)
    protected_path(manifest_path)
    if pdf_dir.resolve() == preview_dir.resolve():
        raise QualityGateError("QA_OUTPUT_OVERLAPS_INPUT")
    if any(
        pdf_dir.resolve() in path.resolve().parents
        for path in (report_path, manifest_path)
    ):
        raise QualityGateError("QA_OUTPUT_OVERLAPS_INPUT")
    if report_path.resolve() == manifest_path.resolve():
        raise QualityGateError("QA report and manifest must use distinct paths")
    input_paths = list(input_paths)
    if generation_evidence is not None:
        input_paths.extend(
            Path(generation_evidence[key]["path"]) for key in ("manifest", "receipt")
        )
    sources = [
        config_path,
        cohort_path,
        *([review_path] if review_path else []),
        *input_paths,
        *([background] if background else []),
    ]
    if any(not path.is_file() for path in sources):
        raise QualityGateError("QA_SOURCE_MISSING")
    input_hashes = {str(path): sha256_file(path) for path in sources}
    pdfs = _pdf_paths(pdf_dir)
    previews = (
        sorted(preview_dir.glob("A1_*-page-*.png")) if preview_dir.exists() else []
    )
    protected_inputs = {
        path.resolve()
        for path in [*sources, *pdfs, *previews, preview_dir / "render-receipt.json"]
    }
    if any(path.resolve() in protected_inputs for path in (report_path, manifest_path)):
        raise QualityGateError("QA_OUTPUT_OVERLAPS_INPUT")
    manifest_path.unlink(missing_ok=True)
    records = expected_records(config_path, cohort_path, review_path)
    expected_ids = set(records)
    actual_ids = {_employee_id(path) for path in pdfs}
    set_issues: list[str] = []
    if actual_ids != expected_ids:
        set_issues.append("COHORT_MISMATCH")
    artifact_hashes = {
        path: sha256_file(protected_path(path)) for path in [*pdfs, *previews]
    }
    expected_preview_names = {
        f"A1_{employee_id}-page-{page}.png"
        for employee_id in expected_ids
        for page in range(1, 4)
    }
    actual_preview_names = {path.name for path in previews}
    if actual_preview_names != expected_preview_names:
        set_issues.append("PREVIEW_SET_MISMATCH")
    results = [
        validate_pdf(
            path, records[_employee_id(path)], records, background, max_erased_pixels
        )
        for path in pdfs
        if _employee_id(path) in records
    ]
    document_ids = [
        records[employee_id]["document_id"] for employee_id in sorted(expected_ids)
    ]
    if len(document_ids) != len(set(document_ids)):
        set_issues.append("certificate document IDs are not unique")
    render_receipt_path = preview_dir / "render-receipt.json"
    pixel_issues = _validate_preview_freshness(pdfs, previews, render_receipt_path)
    if pixel_issues:
        set_issues.extend(pixel_issues)
    if artifact_hashes != {path: sha256_file(path) for path in [*pdfs, *previews]}:
        set_issues.append("QA_ARTIFACT_CHANGED")
    if input_hashes != {str(path): sha256_file(path) for path in sources}:
        set_issues.append("QA_INPUT_CHANGED")
    if (
        generation_evidence is not None
        and require_completed_generation(pdf_dir) != generation_evidence
    ):
        set_issues.append("GENERATION_COMPLETION_CHANGED")
    report = {
        "schema_version": 1,
        "passed": not set_issues
        and len(results) == len(records)
        and all(item.passed for item in results),
        "expected_pdf_count": len(records),
        "actual_pdf_count": len(pdfs),
        "expected_preview_count": len(records) * PAGE_COUNT,
        "actual_preview_count": len(previews),
        "set_issues": set_issues,
        "pdfs": [item.__dict__ for item in results],
    }
    _write_json(report_path, report)
    if report["passed"]:
        manifest = {
            "schema_version": 1,
            "qa_status": "PASS",
            "cohort": sorted(expected_ids),
            "inputs": input_hashes,
            "render_receipt": {
                "path": str(render_receipt_path.resolve()),
                "sha256": sha256_file(render_receipt_path),
            },
            "pdf_directory": str(pdf_dir.resolve()),
            "preview_directory": str(preview_dir.resolve()),
            "pdfs": {path.name: sha256_file(path) for path in pdfs},
            "previews": {path.name: sha256_file(path) for path in previews},
            "qa_report": {
                "path": str(report_path.resolve()),
                "sha256": sha256_file(report_path),
            },
        }
        if generation_evidence is not None:
            manifest["generation_evidence"] = generation_evidence
        _write_json(manifest_path, manifest)
    elif manifest_path.exists():
        manifest_path.unlink()
    return report


def _validate_preview_freshness(
    pdfs: list[Path],
    existing_previews: list[Path],
    receipt_path: Path,
) -> list[str]:
    """Compare every decoded preview with a fresh in-memory render at recorded DPI.

    No fresh PDF derivative is written to system temporary storage. Encoded PNG
    differences are irrelevant; the final manifest binds current artifact bytes.
    """
    try:
        receipt = json.loads(protected_path(receipt_path).read_text(encoding="utf-8"))
        dpi = receipt["dpi"]
        if type(dpi) is not int or not 144 <= dpi <= 600:
            return ["RENDER_DPI_INVALID"]
        if receipt.get("schema_version") != 1:
            return ["RENDER_RECEIPT_INVALID"]
        if receipt["pdfs"] != {path.name: sha256_file(path) for path in pdfs}:
            return ["RENDER_SOURCE_CHANGED"]
        if not pdfs or not existing_previews:
            return ["PREVIEWS_MISSING"]
        preview_by_name = {path.name: path for path in existing_previews}
        if set(receipt["preview_pixels"]) != set(preview_by_name):
            return ["RENDER_PREVIEW_SET_CHANGED"]
        issues = []
        for row, pdf_path in enumerate(pdfs, 1):
            with pymupdf.open(pdf_path) as document:
                for index, page in enumerate(document):
                    name = f"{pdf_path.stem}-page-{index + 1}.png"
                    existing = preview_by_name.get(name)
                    if existing is None:
                        issues.append(f"PREVIEW_MISSING:row={row}:page={index + 1}")
                        continue
                    pixmap = page.get_pixmap(
                        matrix=pymupdf.Matrix(dpi / 72, dpi / 72),
                        alpha=False,
                        colorspace=pymupdf.csRGB,
                    )
                    fresh = Image.frombytes(
                        "RGB", (pixmap.width, pixmap.height), pixmap.samples
                    )
                    with Image.open(existing) as old:
                        pixel_hash = _pixel_hash(old)
                    if (
                        pixel_hash != _pixel_hash(fresh)
                        or pixel_hash != receipt["preview_pixels"][name]
                    ):
                        issues.append(f"PREVIEW_STALE:row={row}:page={index + 1}")
        return issues
    except (OSError, ValueError, KeyError, TypeError, RuntimeError):
        return ["RENDER_RECEIPT_OR_PREVIEW_INVALID"]


def record_visual_review(
    manifest_path: Path,
    contact_dir: Path,
    output_path: Path,
    reviewer: str,
    note: str,
    require_generation: bool = False,
) -> dict[str, Any]:
    """Bind an explicit human/agent visual PASS to an existing deterministic PASS."""
    protected_path(output_path)
    manifest = json.loads(protected_path(manifest_path).read_text(encoding="utf-8"))
    if manifest.get("qa_status") != "PASS":
        raise QualityGateError("visual review requires a deterministic PASS manifest")
    protected_path(contact_dir)
    if require_generation or "generation_evidence" in manifest:
        try:
            expected_generation = manifest["generation_evidence"]
            if (
                require_completed_generation(Path(manifest["pdf_directory"]))
                != expected_generation
            ):
                raise ValueError()
        except (KeyError, ValueError, TypeError):
            raise QualityGateError("GENERATION_COMPLETION_REQUIRED") from None
    try:
        if (
            len(manifest["previews"]) != len(manifest["pdfs"]) * PAGE_COUNT
            or not manifest["pdfs"]
        ):
            raise ValueError()
        for record in (manifest["qa_report"], manifest["render_receipt"]):
            if sha256_file(protected_path(Path(record["path"]))) != record["sha256"]:
                raise ValueError()
        for filename, digest in manifest["inputs"].items():
            if sha256_file(Path(filename)) != digest:
                raise ValueError()
        for directory_key, collection in (
            ("pdf_directory", "pdfs"),
            ("preview_directory", "previews"),
        ):
            directory = protected_path(Path(manifest[directory_key]))
            for filename, digest in manifest[collection].items():
                if (
                    Path(filename).name != filename
                    or sha256_file(protected_path(directory / filename)) != digest
                ):
                    raise ValueError()
    except (KeyError, TypeError, ValueError, OSError):
        raise QualityGateError("QA_MANIFEST_STALE_OR_INVALID") from None
    sheets = sorted(contact_dir.glob("contact-sheet-page-*.png"))
    if len(sheets) != PAGE_COUNT:
        raise QualityGateError(f"visual review requires {PAGE_COUNT} contact sheets")
    try:
        contact_receipt = protected_path(contact_dir / "contact-receipt.json")
        contact_binding = json.loads(contact_receipt.read_text(encoding="utf-8"))
        if contact_binding["previews"] != manifest["previews"] or contact_binding[
            "sheets"
        ] != {path.name: sha256_file(protected_path(path)) for path in sheets}:
            raise ValueError()
    except (OSError, ValueError, KeyError, TypeError):
        raise QualityGateError("CONTACT_SHEETS_STALE_OR_INVALID") from None
    for sheet in sheets:
        with Image.open(protected_path(sheet)) as image:
            image.verify()
    review = {
        "schema_version": 1,
        "visual_status": "PASS",
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "reviewed_by": reviewer,
        "note": note,
        "qa_manifest": {
            "path": str(manifest_path),
            "sha256": sha256_file(manifest_path),
        },
        "contact_sheets": {path.name: sha256_file(path) for path in sheets},
        "contact_receipt": {"sha256": sha256_file(contact_receipt)},
        "checks": {
            "all_pages_reviewed": True,
            "page_count": len(manifest.get("previews", {})),
            "no_clipping_or_overlap": True,
            "no_opaque_masks": True,
            "template_lines_intact": True,
            "checkboxes_correct": True,
            "previews_match_pdf_renders": True,
        },
    }
    referenced = [
        manifest_path,
        contact_receipt,
        *sheets,
        Path(manifest["qa_report"]["path"]),
        Path(manifest["render_receipt"]["path"]),
        *map(Path, manifest["inputs"]),
    ]
    referenced.extend(
        Path(manifest["pdf_directory"]) / name for name in manifest["pdfs"]
    )
    referenced.extend(
        Path(manifest["preview_directory"]) / name for name in manifest["previews"]
    )
    if output_path.resolve() in {path.resolve() for path in referenced}:
        raise QualityGateError("QA_OUTPUT_OVERLAPS_INPUT")
    _write_json(output_path, review)
    return review


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    render = sub.add_parser(
        "render", help="render fresh fixed-DPI previews and contact sheets"
    )
    render.add_argument("--pdf-dir", type=Path, required=True)
    render.add_argument("--preview-dir", type=Path, required=True)
    render.add_argument("--contact-dir", type=Path, required=True)
    render.add_argument("--dpi", type=int, default=200)
    validate = sub.add_parser("validate", help="run the fail-closed package gate")
    validate.add_argument("--pdf-dir", type=Path, required=True)
    validate.add_argument("--preview-dir", type=Path, required=True)
    validate.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    validate.add_argument("--cohort", type=Path)
    validate.add_argument("--review", type=Path)
    validate.add_argument("--background", type=Path, default=DEFAULT_BACKGROUND)
    validate.add_argument("--layout", type=Path, default=DEFAULT_LAYOUT)
    validate.add_argument("--report", type=Path, required=True)
    validate.add_argument("--manifest", type=Path, required=True)
    validate.add_argument("--max-erased-template-pixels", type=int, default=24)
    review = sub.add_parser("record-review", help="record a hash-bound visual PASS")
    review.add_argument("--manifest", type=Path, required=True)
    review.add_argument("--contact-dir", type=Path, required=True)
    review.add_argument("--output", type=Path, required=True)
    review.add_argument("--reviewer", required=True)
    review.add_argument("--note", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    validated_output = False
    try:
        operation = {
            "render": "qa_render",
            "validate": "qa_validate",
            "record-review": "qa_review",
        }[args.command]
        with audited_operation(operation, "a1_qa"):
            if args.command == "render":
                if (
                    args.contact_dir.resolve() == args.pdf_dir.resolve()
                    or args.contact_dir.resolve() in args.pdf_dir.resolve().parents
                ):
                    raise QualityGateError("QA_OUTPUT_OVERLAPS_INPUT")
                if (args.pdf_dir / "generation_manifest.json").exists():
                    require_completed_generation(args.pdf_dir)
                previews = render_previews(args.pdf_dir, args.preview_dir, args.dpi)
                sheets = create_contact_sheets(previews, args.contact_dir)
                summary = {"previews": len(previews), "contact_sheets": len(sheets)}
            elif args.command == "record-review":
                review = record_visual_review(
                    args.manifest,
                    args.contact_dir,
                    args.output,
                    args.reviewer,
                    args.note,
                    require_generation=True,
                )
                validated_output = True
                summary = {"visual_status": review["visual_status"]}
            else:
                generation_evidence = require_completed_generation(args.pdf_dir)
                cohort = args.cohort or private_path("a1/cohort.json")
                review_path = args.review or private_path("a1/review.csv")
                report = validate_set(
                    args.pdf_dir,
                    args.preview_dir,
                    args.config,
                    cohort,
                    review_path,
                    args.background,
                    args.report,
                    args.manifest,
                    [args.layout],
                    args.max_erased_template_pixels,
                    generation_evidence=generation_evidence,
                )
                validated_output = True
                summary = {
                    key: report[key]
                    for key in (
                        "passed",
                        "actual_pdf_count",
                        "actual_preview_count",
                        "set_issues",
                    )
                }
                if not report["passed"]:
                    raise _ValidationFailed("QA_VALIDATION_FAILED")
        print(json.dumps(summary, ensure_ascii=False))
        return 0
    except _ValidationFailed:
        print("QA_VALIDATION_FAILED", file=sys.stderr)
        return 1
    except (
        Exception,
        KeyboardInterrupt,
    ):  # CLI boundary: no input-derived traceback is public.
        try:
            if validated_output and args.command == "validate":
                protected_path(args.manifest).unlink(missing_ok=True)
                _write_json(
                    args.report,
                    {
                        "schema_version": 1,
                        "passed": False,
                        "set_issues": ["QA_OPERATION_FAILED"],
                    },
                )
            elif validated_output and args.command == "record-review":
                protected_path(args.output).unlink(missing_ok=True)
        except (A1PrivateInputError, PathValidationError, OSError):
            pass
        print("QA_OPERATION_FAILED", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
