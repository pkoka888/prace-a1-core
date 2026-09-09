#!/usr/bin/env python3
"""Generate non-final A1 client-confirmation copies from accepted evidence."""

from __future__ import annotations

import csv
import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
import uuid
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from .a1_core import (
        APPLICATION_DRAFT_NOTICE,
        czech_display_case,
        document_id_for_issue_year,
        generate_a1_pdf,
        mark_provisional,
        provisional_one_year_period,
        validate_provisional_issue_date,
    )
    from .finalize_a1 import (
        DEFAULT_REVIEW, ROOT, FinalizationError, load_profile, read_review,
        row_to_form, verify_pdf, validate_review, generation_dependencies, snapshot_hash,
        validate_application_draft_row,
    )
    from .a1_paths import (
        PathValidationError, validate_output_path, unique_staging_path,
        cleanup_staging_only, destination_lock, publish_package,
    )
    from .a1_audit import AuditWriteError, audited, current_run_id
    from .a1_private import A1PrivateInputError, private_path, private_root
except ImportError:  # Direct CLI execution.
    from a1_core import (
        APPLICATION_DRAFT_NOTICE,
        czech_display_case,
        document_id_for_issue_year,
        generate_a1_pdf,
        mark_provisional,
        provisional_one_year_period,
        validate_provisional_issue_date,
    )
    from finalize_a1 import (
        DEFAULT_REVIEW, ROOT, FinalizationError, load_profile, read_review,
        row_to_form, verify_pdf, validate_review, generation_dependencies, snapshot_hash,
        validate_application_draft_row,
    )
    from a1_paths import (
        PathValidationError, validate_output_path, unique_staging_path,
        cleanup_staging_only, destination_lock, publish_package,
    )
    from a1_audit import AuditWriteError, audited, current_run_id
    from a1_private import A1PrivateInputError, private_path, private_root


def render_application_draft(row: dict[str, str], profile: dict, workspace: Path) -> tuple[bytes, dict]:
    """Render a DB-authorized pending input in caller-owned protected staging.

    This has no CLI/cohort side effects and does not claim visual acceptance.
    """
    from pypdf import PdfReader
    try:
        from .a1_quality_gate import validate_pdf
    except ImportError:
        from a1_quality_gate import validate_pdf

    workspace = Path(workspace)
    if not workspace.is_dir() or workspace.is_symlink() or workspace.stat().st_mode & 0o077:
        raise FinalizationError("APPLICATION_DRAFT_PROTECTED_WORKSPACE_REQUIRED")
    form = validate_application_draft_row(row, profile)
    with tempfile.TemporaryDirectory(prefix="application-draft-", dir=workspace) as staging:
        path = Path(staging) / "draft.pdf"
        # Reserve the file privately before the renderer opens it for writing.
        path.touch(mode=0o600, exist_ok=False)
        generate_a1_pdf(form, ROOT / "templates/a1_background.pdf", ROOT / "config/a1_layout.json", path)
        checks = verify_pdf(path, row, profile, [row])
        pages = PdfReader(str(path)).pages
        if not all(APPLICATION_DRAFT_NOTICE in (page.extract_text() or "") for page in pages):
            raise FinalizationError("APPLICATION_DRAFT_NOTICE_MISSING")
        qa = validate_pdf(path, row, {row["employee_id"]: row}, ROOT / "templates/a1_background.pdf", 24)
        if not qa.passed or qa.checks.get("ghostscript") is not True:
            raise FinalizationError("APPLICATION_DRAFT_CANONICAL_QA_FAILED")
        checks["canonical_qa"] = {"sha256": qa.sha256, "checks": qa.checks, "passed": qa.passed}
        checks.update({"application_draft": True, "notice_on_all_pages": True,
                       "visual_review": "pending", "issued": False})
        return path.read_bytes(), checks


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_provisional_rows(
    review_path: Path, profiles: Path, config_path: Path, cohort_path: Path,
    employees_path: Path | None = None,
):
    """Validate accepted inputs; policy/cohort placeholders never replace evidence."""
    rows = read_review(review_path)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    cohort = json.loads(cohort_path.read_text(encoding="utf-8"))
    if not isinstance(config, dict) or not isinstance(config.get("notice"), str) or not config["notice"].strip():
        raise FinalizationError("PROVISIONAL_POLICY_INVALID")
    if not isinstance(cohort, dict):
        raise FinalizationError("COHORT_INVALID")
    validated = validate_review(
        rows, employees_path or private_path("a1/employees_normalized.json"), profiles,
        provisional=True,
    )
    if cohort.get("additional_people"):
        raise FinalizationError("cohort additions must first be reconciled with reviewed normalized sources")
    ids = {row["employee_id"] for row in rows}
    for mapping, field in (("issue_dates", "issue_date"), ("document_ids", "document_id")):
        values = cohort.get(mapping, {})
        if set(values) != ids:
            raise FinalizationError(f"cohort {mapping} differs from reviewed employee set")
        if any(values[row["employee_id"]] != row[field] for row in rows):
            raise FinalizationError(f"cohort {mapping} differs from authoritative review values")
    built = [(dict(row), profile, profile.get("current_office_contact", {}))
             for row, profile in validated]
    return built, config


@audited("provisional_generate", "a1_provisional")
def generate(
    review: Path, profiles: Path, config_path: Path, cohort_path: Path, output: Path,
    employees_path: Path | None = None,
) -> Path:
    employees_path = employees_path or private_path("a1/employees_normalized.json")
    validate_output_path(output, review, employees_path, config_path, cohort_path, allow_existing=False)
    background, layout = ROOT / "templates/a1_background.pdf", ROOT / "config/a1_layout.json"
    extras = (config_path, cohort_path, Path(__file__))
    inputs = generation_dependencies(review, employees_path, profiles, background, layout, extras)
    built, config = build_provisional_rows(review, profiles, config_path, cohort_path, employees_path)
    run_id = current_run_id()
    staging = unique_staging_path(output.parent, f"provisional-{run_id}")
    generated_at = datetime.now(timezone.utc).isoformat()
    manifest = {
        "status": "PROVISIONAL_NOT_FOR_OFFICIAL_USE",
        "notice": config["notice"],
        "generated_at": generated_at,
        "run_id": run_id,
        "inputs": inputs,
        "snapshot_sha256": snapshot_hash([row for row, _, _ in built]),
        "review_sha256": sha256(review),
        "placeholder_config_sha256": sha256(config_path),
        "private_cohort_sha256": sha256(cohort_path),
        "generated": [],
    }
    verification_rows = []
    all_rows = [row for row, _, _ in built]
    pid = os.getpid()
    try:
        for row, profile, contact in built:
            if not row.get("start_date") and row.get("issue_date"):
                row["start_date"], row["end_date"] = provisional_one_year_period(row["issue_date"])
            form = row_to_form(row, profile)
            form = mark_provisional(
                form,
                "Client confirmation copy; publication and visual acceptance remain separate",
            )
            target = staging / f"A1_{row['employee_id']}.pdf"
            generate_a1_pdf(form, ROOT / "templates/a1_background.pdf", ROOT / "config/a1_layout.json", target)
            checks = verify_pdf(target, row, profile, all_rows)
            manifest["generated"].append({"employee_id": row["employee_id"], "path": target.name, **checks})
            verification_rows.append({
                "employee_id": row["employee_id"],
                "status_profile": row["status_profile"],
                "identity": "ACCEPTED_SOURCE_MATCHED",
                "institution": "VERIFIED_PROFILE",
                "certificate_source_status": row["certificate_source_status"],
                "signatory_source_status": row["signatory_source_status"],
                "visual_review": "PENDING",
                "publication": "NOT_FINAL",
            })
        with (staging / "verification_table.csv").open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=verification_rows[0].keys())
            writer.writeheader()
            writer.writerows(verification_rows)
        checklist = [
            "# Client confirmation checklist", "",
            "Accepted input evidence does not itself approve these rendered bytes.", "",
            "- [ ] Selected employment profile and employer data match source evidence",
            "- [ ] Section 5 omission on employee copies matches requested presentation",
            "- [ ] All pages and checkboxes visually reviewed against current source hashes",
            "- [ ] Current artifact has separate authorized publication approval", "",
        ]
        (staging / "CLIENT_CONFIRMATION_CHECKLIST.md").write_text(
            "\n".join(checklist), encoding="utf-8"
        )
        (staging / "generation_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        if generation_dependencies(review, employees_path, profiles, background, layout, extras) != inputs:
            raise FinalizationError("generation dependencies changed; provisional package is stale")
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
    parser.add_argument("--review", type=Path)
    parser.add_argument("--employees", type=Path)
    parser.add_argument("--profiles", type=Path, default=ROOT / "config/institutions")
    parser.add_argument("--config", type=Path, default=ROOT / "config/a1_provisional.json")
    parser.add_argument("--cohort", type=Path)
    parser.add_argument("--output", type=Path, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        private_root()
        review = args.review or private_path("a1/review.csv")
        cohort = args.cohort or private_path("a1/cohort.json")
        result = generate(review, args.profiles, args.config, cohort, (args.output or private_root() / "output/provisional" / str(uuid.uuid4())), args.employees)
        print("Generated provisional candidate set; QA and artifact approval remain required")
        return 0
    except (Exception, KeyboardInterrupt):  # CLI boundary: protected receipts retain non-content failure evidence.
        print("PROVISIONAL_GENERATION_BLOCKED", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
