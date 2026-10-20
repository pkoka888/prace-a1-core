#!/usr/bin/env python3
"""Generate A1 forms. Output goes to output/provisional/."""

from __future__ import annotations

import csv
import argparse
import hashlib
import json
import os
import tempfile
import uuid
import sys

import pymupdf

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from .a1_core import (
        FONT_CANDIDATES,
        APPLICATION_DRAFT_NOTICE,
        PROVISIONAL_NOTICE,
        generate_a1_pdf,
        mark_provisional,
        provisional_one_year_period,
    )
    from .finalize_a1 import (
        ROOT,
        FinalizationError,
        read_review,
        row_to_form,
        verify_pdf,
        validate_review,
        generation_dependencies,
        snapshot_hash,
        validate_application_draft_row,
        derive_variant,
        VARIANT_PARAMETERS,
        VARIANT_DEFAULT,
    )
    from .a1_paths import (
        validate_output_path,
        unique_staging_path,
        cleanup_staging_only,
        destination_lock,
        publish_package,
    )
    from .a1_audit import audited, current_run_id
    from .a1_private import private_path, private_root
    from .generate_a1_placeholder import extract_field_positions, flatten_form_data
    from .pdf_named_fields import replace_placeholders
except ImportError:  # Direct CLI execution.
    from a1_core import (
        FONT_CANDIDATES,
        APPLICATION_DRAFT_NOTICE,
        generate_a1_pdf,
        mark_provisional,
        provisional_one_year_period,
    )
    from finalize_a1 import (
        ROOT,
        FinalizationError,
        read_review,
        row_to_form,
        verify_pdf,
        validate_review,
        generation_dependencies,
        snapshot_hash,
        validate_application_draft_row,
        derive_variant,
        VARIANT_PARAMETERS,
        VARIANT_DEFAULT,
    )
    from a1_paths import (
        validate_output_path,
        unique_staging_path,
        cleanup_staging_only,
        destination_lock,
        publish_package,
    )
    from a1_audit import audited, current_run_id
    from generate_a1_placeholder import extract_field_positions, flatten_form_data
    from pdf_named_fields import replace_placeholders
    from a1_private import private_path, private_root


def generate_a1_placeholder_technique(
    form: dict[str, Any],
    output_pdf: Path,
) -> None:
    """Generate A1 PDF using placeholder technique (fixes Czech character rendering)."""
    template_pdf = Path(__file__).parent.parent / "templates" / "a1_template.pdf"

    # Load template and extract positions
    template_bytes = template_pdf.read_bytes()
    fields = extract_field_positions(template_bytes)

    # Flatten form data
    values = flatten_form_data(form)

    # Get font
    font = str(next(p for p in FONT_CANDIDATES if p.exists()))

    # Replace placeholders
    result = replace_placeholders(template_bytes, fields, values, font)

    # Save
    output_pdf.write_bytes(result)


def render_application_draft(
    row: dict[str, str], profile: dict, workspace: Path
) -> tuple[bytes, dict]:
    """Render a DB-authorized pending input in caller-owned protected staging.

    This has no CLI/cohort side effects and does not claim visual acceptance.
    """
    from pypdf import PdfReader

    try:
        from .a1_quality_gate import validate_pdf
    except ImportError:
        from a1_quality_gate import validate_pdf

    workspace = Path(workspace)
    if (
        not workspace.is_dir()
        or workspace.is_symlink()
        or workspace.stat().st_mode & 0o077
    ):
        raise FinalizationError("APPLICATION_DRAFT_PROTECTED_WORKSPACE_REQUIRED")
    form = validate_application_draft_row(row, profile)
    with tempfile.TemporaryDirectory(
        prefix="application-draft-", dir=workspace
    ) as staging:
        path = Path(staging) / "draft.pdf"
        # Reserve the file privately before the renderer opens it for writing.
        path.touch(mode=0o600, exist_ok=False)
        # The canonical overlay renderer is the one that stamps
        # APPLICATION_DRAFT_NOTICE on every page and pins the current font for
        # drafts. The placeholder technique draws no notice, so an
        # application draft rendered through it would carry no visible marker.
        generate_a1_pdf(
            form,
            ROOT / "templates/a1_background.pdf",
            ROOT / "config/a1_layout.json",
            path,
        )
        checks = verify_pdf(path, row, profile, [row])
        pages = PdfReader(str(path)).pages
        if not all(
            APPLICATION_DRAFT_NOTICE in (page.extract_text() or "") for page in pages
        ):
            raise FinalizationError("APPLICATION_DRAFT_NOTICE_MISSING")
        qa = validate_pdf(
            path,
            row,
            {row["employee_id"]: row},
            ROOT / "templates/a1_background.pdf",
            24,
        )
        if not qa.passed or qa.checks.get("ghostscript") is not True:
            raise FinalizationError("APPLICATION_DRAFT_CANONICAL_QA_FAILED")
        checks["canonical_qa"] = {
            "sha256": qa.sha256,
            "checks": qa.checks,
            "passed": qa.passed,
        }
        checks.update(
            {
                "application_draft": True,
                "notice_on_all_pages": True,
                "visual_review": "pending",
                "issued": False,
            }
        )
        return path.read_bytes(), checks


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_provisional_rows(
    review_path: Path,
    profiles: Path,
    config_path: Path,
    cohort_path: Path,
    employees_path: Path | None = None,
):
    """Validate accepted inputs; policy/cohort placeholders never replace evidence."""
    rows = read_review(review_path)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    cohort = json.loads(cohort_path.read_text(encoding="utf-8"))
    if (
        not isinstance(config, dict)
        or not isinstance(config.get("notice"), str)
        or not config["notice"].strip()
    ):
        raise FinalizationError("PROVISIONAL_POLICY_INVALID")
    if not isinstance(cohort, dict):
        raise FinalizationError("COHORT_INVALID")
    validated = validate_review(
        rows,
        employees_path or private_path("a1/employees_normalized.json"),
        profiles,
        provisional=True,
    )
    if cohort.get("additional_people"):
        raise FinalizationError(
            "cohort additions must first be reconciled with reviewed normalized sources"
        )
    ids = {row["employee_id"] for row in rows}
    for mapping, field in (
        ("issue_dates", "issue_date"),
        ("document_ids", "document_id"),
    ):
        values = cohort.get(mapping, {})
        if set(values) != ids:
            raise FinalizationError(
                f"cohort {mapping} differs from reviewed employee set"
            )
        if any(values[row["employee_id"]] != row[field] for row in rows):
            raise FinalizationError(
                f"cohort {mapping} differs from authoritative review values"
            )
    built = [
        (dict(row), profile, profile.get("current_office_contact", {}))
        for row, profile in validated
    ]
    return built, config


@audited("provisional_generate", "a1_provisional")
def generate(
    review: Path,
    profiles: Path,
    config_path: Path,
    cohort_path: Path,
    output: Path,
    employees_path: Path | None = None,
    variant: str | None = None,
) -> Path:
    employees_path = employees_path or private_path("a1/employees_normalized.json")
    validate_output_path(
        output, review, employees_path, config_path, cohort_path, allow_existing=False
    )
    background, layout = (
        ROOT / "templates/a1_background.pdf",
        ROOT / "config/a1_layout.json",
    )
    extras = (config_path, cohort_path, Path(__file__))
    inputs = generation_dependencies(
        review, employees_path, profiles, background, layout, extras
    )
    built, config = build_provisional_rows(
        review, profiles, config_path, cohort_path, employees_path
    )
    if variant is None:
        variant = (
            derive_variant(built[0][0].get("status_profile", ""))
            if built
            else VARIANT_DEFAULT
        )
    variant_params = VARIANT_PARAMETERS.get(
        variant, VARIANT_PARAMETERS[VARIANT_DEFAULT]
    )
    for row, _, _ in built:
        if not row.get("activity_name"):
            row["activity_name"] = variant_params["section5_activity_name_default"]
        if not row.get("activity_address"):
            row["activity_address"] = variant_params[
                "section5_activity_address_default"
            ]
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
                row["start_date"], row["end_date"] = provisional_one_year_period(
                    row["issue_date"]
                )
            form = row_to_form(row, profile)
            # Decision D2 (2026-10-20): the client-confirmation copy carries a
            # visible document-status mark on every page. It is not official
            # field 2.5 -- that field states that the legal determination is
            # provisional, which is a different thing from this document not
            # being an issued A1. The package keeps its own marking as well:
            # the manifest status, the manifest notice and the client
            # confirmation checklist.
            form = mark_provisional(
                form,
                "Client confirmation copy; publication and visual acceptance remain separate",
                visible_notice=True,
            )
            target = staging / f"A1_{row['employee_id']}.pdf"
            # The coordinate renderer is the canonical path: it draws the
            # document-status notice itself and stays inside the quality
            # gate's background-damage threshold. The placeholder framework
            # remains the documented vector-template alternative, but the
            # client copy is not rendered with it: that route erased more
            # template pixels than the gate allows, so the copy failed its own
            # quality gate.
            generate_a1_pdf(
                form,
                ROOT / "templates/a1_background.pdf",
                ROOT / "config/a1_layout.json",
                target,
            )
            checks = verify_pdf(target, row, profile, all_rows, provisional=True)
            manifest["generated"].append(
                {"employee_id": row["employee_id"], "path": target.name, **checks}
            )
            verification_rows.append(
                {
                    "employee_id": row["employee_id"],
                    "status_profile": row["status_profile"],
                    "identity": "ACCEPTED_SOURCE_MATCHED",
                    "institution": "VERIFIED_PROFILE",
                    "certificate_source_status": row["certificate_source_status"],
                    "signatory_source_status": row["signatory_source_status"],
                    "visual_review": "PENDING",
                    "publication": "NOT_FINAL",
                }
            )
        with (staging / "verification_table.csv").open(
            "w", encoding="utf-8-sig", newline=""
        ) as stream:
            writer = csv.DictWriter(stream, fieldnames=verification_rows[0].keys())
            writer.writeheader()
            writer.writerows(verification_rows)
        checklist = [
            "# Client confirmation checklist",
            "",
            "Accepted input evidence does not itself approve these rendered bytes.",
            "",
            "- [ ] Selected employment profile and employer data match source evidence",
            "- [ ] Section 5 omission on employee copies matches requested presentation",
            "- [ ] All pages and checkboxes visually reviewed against current source hashes",
            "- [ ] Current artifact has separate authorized publication approval",
            "",
        ]
        (staging / "CLIENT_CONFIRMATION_CHECKLIST.md").write_text(
            "\n".join(checklist), encoding="utf-8"
        )
        (staging / "generation_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        if (
            generation_dependencies(
                review, employees_path, profiles, background, layout, extras
            )
            != inputs
        ):
            raise FinalizationError(
                "generation dependencies changed; provisional package is stale"
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
    parser.add_argument("--review", type=Path)
    parser.add_argument("--employees", type=Path)
    parser.add_argument("--profiles", type=Path, default=ROOT / "config/institutions")
    parser.add_argument(
        "--config", type=Path, default=ROOT / "config/a1_provisional.json"
    )
    parser.add_argument("--cohort", type=Path)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument(
        "--variant",
        type=str,
        default=None,
        choices=("employee", "self_employed"),
        help="worker variant; if omitted, inferred from status_profile",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        private_root()
        review = args.review or private_path("a1/review.csv")
        cohort = args.cohort or private_path("a1/cohort.json")
        generate(
            review,
            args.profiles,
            args.config,
            cohort,
            (args.output or private_root() / "output/provisional" / str(uuid.uuid4())),
            args.employees,
            variant=args.variant,
        )
        print(
            "Generated provisional candidate set; QA and artifact approval remain required"
        )
        return 0
    except (
        Exception,
        KeyboardInterrupt,
    ):  # CLI boundary: protected receipts retain non-content failure evidence.
        import traceback

        traceback.print_exc()
        print("PROVISIONAL_GENERATION_BLOCKED", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
