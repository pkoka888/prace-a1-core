#!/usr/bin/env python3
"""Generate non-final A1 client-confirmation copies pending OSSZ evidence."""

from __future__ import annotations

import csv
import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

try:
    from .a1_core import (
        czech_display_case,
        generate_a1_pdf,
        mark_provisional,
        provisional_one_year_period,
        validate_provisional_issue_date,
    )
    from .finalize_a1 import (
        DEFAULT_REVIEW, ROOT, FinalizationError, load_profile, read_review,
        row_to_form, verify_pdf,
    )
    from .a1_private import A1PrivateInputError, private_path
except ImportError:  # Direct CLI execution.
    from a1_core import (
        czech_display_case,
        generate_a1_pdf,
        mark_provisional,
        provisional_one_year_period,
        validate_provisional_issue_date,
    )
    from finalize_a1 import (
        DEFAULT_REVIEW, ROOT, FinalizationError, load_profile, read_review,
        row_to_form, verify_pdf,
    )
    from a1_private import A1PrivateInputError, private_path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def document_id_for_issue_year(document_id: str, issue_date: str) -> str:
    """Bind a certificate number to its 6.10 issue-date year.

    The certificate number stays constant across all three pages of a person's
    PDF and unique per person.  Its embedded ``/YYYY/`` year must reflect the
    year shown in section 6.10: a ``{year}`` token is substituted with the issue
    year, otherwise an explicit ``/YYYY/`` is validated and left untouched so
    the same number is reused verbatim on every page.
    """
    issue_year = int(issue_date[-4:])
    if "{year}" in document_id:
        return document_id.replace("{year}", f"{issue_year:04d}")
    match = re.search(r"/(\d{4})/", document_id)
    if match and int(match.group(1)) != issue_year:
        raise FinalizationError(
            f"document_id {document_id} year does not reflect 6.10 issue year {issue_year}"
        )
    return document_id


def build_provisional_rows(
    review_path: Path, profiles: Path, config_path: Path, cohort_path: Path
):
    rows = read_review(review_path)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    cohort = json.loads(cohort_path.read_text(encoding="utf-8"))
    rows.extend(cohort.get("additional_people", []))
    built = []
    for source in rows:
        row = dict(source)
        profile = load_profile(profiles, row["institution_profile"])
        contact = profile["current_office_contact"]
        issue_date = validate_provisional_issue_date(
            cohort["issue_dates"][row["employee_id"]], config["issue_date_reference"]
        )
        start_date, end_date = provisional_one_year_period(issue_date)
        document_id = document_id_for_issue_year(
            cohort["document_ids"][row["employee_id"]], issue_date
        )
        row.update(
            activity_name=config["activity_name"],
            activity_address=config["activity_address"],
            document_id=document_id,
            start_date=start_date,
            end_date=end_date,
            issue_date=issue_date,
            signed_by=contact["name"],
        )
        for field in ("surname", "given_name", "birth_place", "street", "city", "district", "employment_name", "employment_street", "employment_city"):
            row[field] = czech_display_case(row.get(field))
        built.append((row, profile, contact))
    document_ids = [item[0]["document_id"] for item in built]
    if any(not value for value in document_ids) or len(document_ids) != len(set(document_ids)):
        raise FinalizationError("every employee needs a non-empty, unique document_id")
    return built, config


def generate(
    review: Path, profiles: Path, config_path: Path, cohort_path: Path, output: Path
) -> Path:
    built, config = build_provisional_rows(review, profiles, config_path, cohort_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".a1-provisional-", dir=output.parent))
    generated_at = datetime.now(timezone.utc).isoformat()
    manifest = {
        "status": "PROVISIONAL_NOT_FOR_OFFICIAL_USE",
        "notice": config["notice"],
        "generated_at": generated_at,
        "review_sha256": sha256(review),
        "placeholder_config_sha256": sha256(config_path),
        "private_cohort_sha256": sha256(cohort_path),
        "generated": [],
    }
    verification_rows = []
    all_rows = [row for row, _, _ in built]
    try:
        for row, profile, contact in built:
            form = row_to_form(row, profile)
            if config.get("employment_mode") != "self_employed_multi_state":
                raise ValueError("provisional generator currently supports only self_employed_multi_state")
            form = mark_provisional(
                form,
                "Certificate/activity/date/signatory fields await authoritative OSSZ confirmation",
            )
            target = staging / f"A1_{row['employee_id']}.pdf"
            generate_a1_pdf(form, ROOT / "templates/a1_background.pdf", ROOT / "config/a1_layout.json", target)
            checks = verify_pdf(target, row, profile, all_rows)
            manifest["generated"].append({"employee_id": row["employee_id"], "path": target.name, **checks})
            verification_rows.append({
                "employee_id": row["employee_id"],
                "identity": "CONFIRMED_FROM_SCANS_AND_USER_TRANSCRIPTION",
                "responsible_ossz": row["resolved_ossz"],
                "institution": profile["institution"]["name"],
                "institution_code": profile["institution"]["code"],
                "institution_source": profile["source_url"],
                "current_office_contact": contact["name"],
                "contact_role": contact["role"],
                "contact_as_signatory": "PLACEHOLDER_NOT_CONFIRMED",
                "employment_status": "SELF_EMPLOYED_MULTI_STATE_TO_CONFIRM",
                "employer_details": "PERSON_DATA_USED_AS_SELF_EMPLOYED_TO_CONFIRM",
                "activity": "PLACEHOLDER",
                "document_id": "PLACEHOLDER",
                "certificate_dates": "PLACEHOLDER",
                "issue_date": "PLACEHOLDER",
                "user_final_validation": "PENDING",
            })
        with (staging / "verification_table.csv").open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=verification_rows[0].keys())
            writer.writeheader()
            writer.writerows(verification_rows)
        checklist = [
            "# Client confirmation checklist",
            "",
            "These PDFs are confirmation copies. Tick every item before authoritative finalization.",
            "",
        ]
        for row, profile, contact in built:
            checklist.extend([
                f"## {row['given_name']} {row['surname']} ({row['employee_id']})",
                "",
                "- [ ] Identity, personal number, birth data and residence match the source scan",
                "- [ ] Status is self-employed in two or more states (3.4 and 4.1.2)",
                "- [ ] Self-employed ID, name and business address match the client record",
                f"- [ ] Responsible office confirmed: {row['resolved_ossz']} / code {profile['institution']['code']}",
                f"- [ ] Current office contact checked: {contact['name']} (not yet confirmed as signatory)",
                "- [ ] German activity name and address confirmed",
                f"- [ ] Certificate number confirmed (current PDF placeholder: {row['document_id']})",
                f"- [ ] Period confirmed: {row['start_date']}–{row['end_date']}",
                f"- [ ] Provisional 6.10 date confirmed: {row['issue_date']} (Monday/Thursday, 2–6 months back)",
                "- [ ] OSSZ-authorized signatory confirmed",
                "- [ ] All three rendered pages visually approved",
                "",
            ])
        (staging / "CLIENT_CONFIRMATION_CHECKLIST.md").write_text(
            "\n".join(checklist) + "\n", encoding="utf-8"
        )
        (staging / "generation_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        backup = None
        if output.exists():
            backup = output.with_name(output.name + ".backup-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
            os.replace(output, backup)
        os.replace(staging, output)
        return output
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", type=Path)
    parser.add_argument("--profiles", type=Path, default=ROOT / "config/institutions")
    parser.add_argument("--config", type=Path, default=ROOT / "config/a1_provisional.json")
    parser.add_argument("--cohort", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "output/provisional")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        review = args.review or private_path("a1/review.csv")
        cohort = args.cohort or private_path("a1/cohort.json")
        result = generate(review, args.profiles, args.config, cohort, args.output)
        print(f"Generated provisional set: {result}")
        return 0
    except (
        A1PrivateInputError, FinalizationError, ValueError, FileNotFoundError,
        json.JSONDecodeError,
    ) as exc:
        print(f"PROVISIONAL GENERATION BLOCKED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
