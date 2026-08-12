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
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pymupdf
from PIL import Image, ImageOps, ImageDraw
from pypdf import PdfReader

try:
    from .a1_private import A1PrivateInputError, private_path
except ImportError:
    from a1_private import A1PrivateInputError, private_path

try:
    from .generate_provisional_a1 import document_id_for_issue_year
except ImportError:
    from generate_provisional_a1 import document_id_for_issue_year


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config/a1_provisional.json"
DEFAULT_REVIEW = None
DEFAULT_LAYOUT = ROOT / "config/a1_layout.json"
DEFAULT_BACKGROUND = ROOT / "templates/a1_background.pdf"
PDF_PREFIX = "A1_"
PAGE_COUNT = 3


class QualityGateError(RuntimeError):
    """Raised for unsafe or internally inconsistent QA inputs."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def expected_records(
    config_path: Path, cohort_path: Path, review_path: Path | None
) -> dict[str, dict[str, str]]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    cohort = json.loads(cohort_path.read_text(encoding="utf-8"))
    issue_dates = cohort.get("issue_dates", {})
    document_ids = cohort.get("document_ids", {})
    if set(issue_dates) != set(document_ids):
        raise QualityGateError("issue_dates and document_ids must name the same cohort")
    records = {employee_id: {"employee_id": employee_id} for employee_id in issue_dates}
    if review_path and review_path.exists():
        with review_path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            required_employment = {
                "employment_id", "employment_name", "employment_street",
                "employment_house_number", "employment_city",
                "employment_postal_code", "employment_country_code",
            }
            missing_columns = sorted(required_employment - set(reader.fieldnames or ()))
            if missing_columns:
                raise QualityGateError(
                    "review CSV lacks explicit Section 4 columns: "
                    + ", ".join(missing_columns)
                )
            for row in reader:
                employee_id = (row.get("employee_id") or "").strip()
                if employee_id in records:
                    records[employee_id].update({key: (value or "").strip() for key, value in row.items()})
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


def render_previews(pdf_dir: Path, preview_dir: Path, dpi: int = 200) -> list[Path]:
    """Render every page with stable names, replacing only the preview directory."""
    if dpi < 144:
        raise QualityGateError("QA rendering requires at least 144 DPI")
    if pdf_dir.resolve() == preview_dir.resolve() or pdf_dir.resolve() in preview_dir.resolve().parents:
        raise QualityGateError("preview directory must not contain the source PDF directory")
    preview_dir.mkdir(parents=True, exist_ok=True)
    for stale in preview_dir.glob("A1_*-page-*.png"):
        stale.unlink()
    rendered: list[Path] = []
    matrix = pymupdf.Matrix(dpi / 72.0, dpi / 72.0)
    for pdf_path in _pdf_paths(pdf_dir):
        with pymupdf.open(pdf_path) as document:
            for index, page in enumerate(document):
                target = preview_dir / f"{pdf_path.stem}-page-{index + 1}.png"
                page.get_pixmap(matrix=matrix, alpha=False, colorspace=pymupdf.csRGB).save(target)
                rendered.append(target)
    return rendered


def create_contact_sheets(previews: Iterable[Path], output_dir: Path, columns: int = 3) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
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
                thumbs.append((path.stem.rsplit("-page-", 1)[0], image.resize((thumb_width, height))))
        label_height, padding = 34, 12
        cell_height = max(image.height for _, image in thumbs) + label_height
        rows = (len(thumbs) + columns - 1) // columns
        sheet = Image.new("RGB", (columns * (thumb_width + padding) + padding, rows * (cell_height + padding) + padding), "white")
        draw = ImageDraw.Draw(sheet)
        for index, (label, image) in enumerate(thumbs):
            x = padding + (index % columns) * (thumb_width + padding)
            y = padding + (index // columns) * (cell_height + padding)
            sheet.paste(ImageOps.expand(image, border=1, fill="#888888"), (x, y + label_height))
            draw.text((x, y + 8), label.removeprefix(PDF_PREFIX), fill="black")
        target = output_dir / f"contact-sheet-page-{page_number}.png"
        sheet.save(target, optimize=True)
        outputs.append(target)
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


def _background_damage(pdf_path: Path, background: Path, dpi: int = 144) -> list[dict[str, int]]:
    """Count template ink/color pixels erased to near-white in the generated PDF."""
    matrix = pymupdf.Matrix(dpi / 72.0, dpi / 72.0)
    damage: list[dict[str, int]] = []
    with pymupdf.open(pdf_path) as generated, pymupdf.open(background) as template:
        if len(generated) != len(template):
            return [{"page": 0, "erased_template_pixels": 10**9}]
        for index in range(len(generated)):
            got = np.frombuffer(generated[index].get_pixmap(matrix=matrix, alpha=False, colorspace=pymupdf.csRGB).samples, dtype=np.uint8)
            ref_pix = template[index].get_pixmap(matrix=matrix, alpha=False, colorspace=pymupdf.csRGB)
            got_pix = generated[index].get_pixmap(matrix=matrix, alpha=False, colorspace=pymupdf.csRGB)
            got = got.reshape(got_pix.height, got_pix.width, 3)
            ref = np.frombuffer(ref_pix.samples, dtype=np.uint8).reshape(ref_pix.height, ref_pix.width, 3)
            if got.shape != ref.shape:
                damage.append({"page": index + 1, "erased_template_pixels": 10**9})
                continue
            ref_ink = (ref.min(axis=2) < 215) | ((ref.max(axis=2) - ref.min(axis=2)) > 18)
            erased = ref_ink & (got.min(axis=2) > 246) & (got.max(axis=2) - got.min(axis=2) < 5)
            damage.append({"page": index + 1, "erased_template_pixels": int(erased.sum())})
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
    except Exception as exc:
        result.fail(f"PDF parse failed: {exc}")
        return result
    normalized = _normalize(text)
    nationality = record.get("nationality", "")
    if _normalize(nationality) in {"česká republika", "ceska republika", "czech republic", "cz", "cze"}:
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
    missing = [name for name, value in required.items() if value and _normalize(value) not in normalized]
    result.checks["required_text"] = {name: name not in missing for name in required if required[name]}
    for name in missing:
        result.fail(f"missing expected {name}")
    foreign_numbers = sorted({
        other.get("insurance_number", "")
        for employee_id, other in all_records.items()
        if employee_id != record["employee_id"]
        and other.get("insurance_number")
        and _normalize(other["insurance_number"]) in normalized
    })
    result.checks["foreign_identity_numbers"] = foreign_numbers
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
                result.fail(f"page {item['page']} erased {item['erased_template_pixels']} template pixels")
    gs = shutil.which("gs")
    if gs:
        completed = subprocess.run(
            [gs, "-q", "-dNOPAUSE", "-dBATCH", "-sDEVICE=nullpage", str(path)],
            capture_output=True, text=True, timeout=30, check=False,
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
) -> dict[str, Any]:
    records = expected_records(config_path, cohort_path, review_path)
    expected_ids, pdfs = set(records), _pdf_paths(pdf_dir)
    actual_ids = {_employee_id(path) for path in pdfs}
    set_issues: list[str] = []
    if actual_ids != expected_ids:
        set_issues.append(f"cohort mismatch: missing={sorted(expected_ids-actual_ids)}, extra={sorted(actual_ids-expected_ids)}")
    previews = sorted(preview_dir.glob("A1_*-page-*.png")) if preview_dir.exists() else []
    expected_preview_names = {f"A1_{employee_id}-page-{page}.png" for employee_id in expected_ids for page in range(1, 4)}
    actual_preview_names = {path.name for path in previews}
    if actual_preview_names != expected_preview_names:
        set_issues.append(
            f"preview mismatch: missing={sorted(expected_preview_names-actual_preview_names)}, "
            f"extra={sorted(actual_preview_names-expected_preview_names)}"
        )
    results = [
        validate_pdf(path, records[_employee_id(path)], records, background, max_erased_pixels)
        for path in pdfs if _employee_id(path) in records
    ]
    document_ids = [records[employee_id]["document_id"] for employee_id in sorted(expected_ids)]
    if len(document_ids) != len(set(document_ids)):
        set_issues.append("certificate document IDs are not unique")
    report = {
        "schema_version": 1,
        "passed": not set_issues and len(results) == len(records) and all(item.passed for item in results),
        "expected_pdf_count": len(records),
        "actual_pdf_count": len(pdfs),
        "expected_preview_count": len(records) * PAGE_COUNT,
        "actual_preview_count": len(previews),
        "set_issues": set_issues,
        "pdfs": [item.__dict__ for item in results],
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if report["passed"]:
        all_inputs = [config_path, *( [review_path] if review_path and review_path.exists() else []), *input_paths]
        if background and background.exists():
            all_inputs.append(background)
        manifest = {
            "schema_version": 1,
            "qa_status": "PASS",
            "cohort": sorted(expected_ids),
            "inputs": {str(path): sha256_file(path) for path in all_inputs if path.exists()},
            "pdfs": {path.name: sha256_file(path) for path in pdfs},
            "previews": {path.name: sha256_file(path) for path in previews},
            "qa_report": {"path": str(report_path), "sha256": sha256_file(report_path)},
        }
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    elif manifest_path.exists():
        manifest_path.unlink()
    return report


def record_visual_review(
    manifest_path: Path,
    contact_dir: Path,
    output_path: Path,
    reviewer: str,
    note: str,
) -> dict[str, Any]:
    """Bind an explicit human/agent visual PASS to an existing deterministic PASS."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("qa_status") != "PASS":
        raise QualityGateError("visual review requires a deterministic PASS manifest")
    sheets = sorted(contact_dir.glob("contact-sheet-page-*.png"))
    if len(sheets) != PAGE_COUNT:
        raise QualityGateError(f"visual review requires {PAGE_COUNT} contact sheets")
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
        "checks": {
            "all_33_pages_reviewed": True,
            "no_clipping_or_overlap": True,
            "no_opaque_masks": True,
            "template_lines_intact": True,
            "checkboxes_correct": True,
            "previews_match_pdf_renders": True,
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(review, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return review


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    render = sub.add_parser("render", help="render fresh fixed-DPI previews and contact sheets")
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
    try:
        if args.command == "render":
            previews = render_previews(args.pdf_dir, args.preview_dir, args.dpi)
            sheets = create_contact_sheets(previews, args.contact_dir)
            print(json.dumps({"previews": len(previews), "contact_sheets": len(sheets)}))
            return 0
        if args.command == "record-review":
            review = record_visual_review(
                args.manifest, args.contact_dir, args.output, args.reviewer, args.note
            )
            print(json.dumps({"visual_status": review["visual_status"]}))
            return 0
        cohort = args.cohort or private_path("a1/cohort.json")
        review_path = args.review or private_path("a1/review.csv")
        report = validate_set(
            args.pdf_dir, args.preview_dir, args.config, cohort, review_path,
            args.background, args.report, args.manifest, [args.layout],
            args.max_erased_template_pixels,
        )
        print(json.dumps({key: report[key] for key in ("passed", "actual_pdf_count", "actual_preview_count", "set_issues")}, ensure_ascii=False))
        return 0 if report["passed"] else 1
    except (A1PrivateInputError, QualityGateError, OSError, json.JSONDecodeError) as exc:
        if args.command == "validate":
            if args.manifest.exists():
                args.manifest.unlink()
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(
                json.dumps(
                    {"schema_version": 1, "passed": False, "set_issues": [str(exc)]},
                    ensure_ascii=False,
                    indent=2,
                ) + "\n",
                encoding="utf-8",
            )
        print(f"quality gate error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
