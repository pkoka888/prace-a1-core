#!/usr/bin/env python3
"""Create one explicitly unverified, incomplete A1 for operator completion."""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import uuid

import pymupdf
from pypdf import PdfReader

try:
    from scripts.a1_core import (A1_STATUS_PROFILES, A1_STATUS_VARIANTS,
                              APPLICATION_DRAFT_NOTICE, ROOT, build_form_data,
                              generate_a1_pdf)
    from scripts.a1_audit import audited
    from scripts.a1_paths import (protected_path, protected_root, validate_output_path,
                                  unique_staging_path, cleanup_staging_only,
                                  destination_lock, publish_package)
except ImportError:  # Direct CLI execution.
    from a1_core import (A1_STATUS_PROFILES, A1_STATUS_VARIANTS,
                       APPLICATION_DRAFT_NOTICE, ROOT, build_form_data,
                       generate_a1_pdf)
    from a1_audit import audited
    from a1_paths import (protected_path, protected_root, validate_output_path,
                          unique_staging_path, cleanup_staging_only,
                          destination_lock, publish_package)

DEFAULT_VARIANT = "self_employed"
PROFILES = dict(A1_STATUS_VARIANTS)
# A coarse activity_profile that leaked into the fine A1 field fixes the
# variant but never the situation: posted vs multi-state stays undecided.
COARSE_VARIANTS = {
    "employee": "employee", "zaměstnanec": "employee", "zamestnanec": "employee",
    "self_employed": "self_employed", "osvc": "self_employed", "osvč": "self_employed",
    "živnostník": "self_employed", "zivnostnik": "self_employed",
}
STATUS_PROFILE_CHOICES = list(A1_STATUS_PROFILES)


def build_preview(source: dict, *, variant: str | None = None,
                  posting_scenario: str | None = None, shared_defaults: dict | None = None) -> dict:
    """Keep supplied status; defaults are only for new, unclassified previews."""
    employee = deepcopy(source)
    # Only form sections enter the preview. Provenance/scans stay in the source.
    employee = {key: employee[key] for key in
                ("id", "person", "residence", "employment", "activity", "a1") if key in employee}
    a1 = employee.setdefault("a1", {})
    status = a1.get("status_profile", "")
    if variant is not None and variant not in {"employee", "self_employed"}:
        raise ValueError("UNSUPPORTED_VARIANT")
    undecided_status = False
    if status and status not in PROFILES:
        coarse = status.strip().casefold()
        if coarse in COARSE_VARIANTS:
            if variant is not None and variant != COARSE_VARIANTS[coarse]:
                raise ValueError("VARIANT_CONFLICT_WITH_SOURCE")
            variant = COARSE_VARIANTS[coarse]
            a1["status_profile"] = status = ""
            undecided_status = True
        else:
            raise ValueError("UNSUPPORTED_STATUS_PROFILE")
    if status and variant and PROFILES[status] != variant:
        raise ValueError("VARIANT_CONFLICT_WITH_SOURCE")
    if not status:
        # A missing status is an undecided situation, never a default. The
        # variant says which application form applies; it does not say whether
        # the person is posted or works in two or more States, and those
        # carry different legal consequences. Article 16(2) of Regulation
        # 987/2009 provides for this case by making the institution's initial
        # determination provisional, not by defaulting the applicant.
        variant = variant or DEFAULT_VARIANT
        a1["status_profile"] = ""
        undecided_status = True
        # The role is known from the variant even when the situation is not,
        # so Section 4.1 stays exactly-one. The situation alone is undecided.
        employee.setdefault("employment", {})["kind"] = variant
    omitted = []
    def clean(value, path=""):
        if isinstance(value, dict):
            return {key: clean(item, f"{path}.{key}".strip(".")) for key, item in value.items()}
        if isinstance(value, str) and ("<" in value or "{{" in value or value.strip().upper() in {"TBD", "UNKNOWN"}):
            omitted.append(path)
            return ""
        return value
    employee = clean(employee)
    # This is a completion worksheet, so there are no issuance claims or copied office details.
    employee["certificate"] = {}
    if posting_scenario is not None:
        if posting_scenario != "cz_employee_to_de" or employee["a1"]["status_profile"] != "posted_employee":
            raise ValueError("POSTING_SCENARIO_PROFILE_CONFLICT")
        # Explicit operator-selected scenario, never a global employee default.
        employee["certificate"]["member_state"] = "CZ"
        employee.setdefault("employment", {})["country_code"] = "CZ"
        if not employee.setdefault("activity", {}).get("address"):
            employee["activity"]["address"] = "DE"
    employee["a1"].pop("institution_profile", None)
    institution_config = {}
    if shared_defaults is not None:
        institution_config = {
            "institution": {key: value for key, value in shared_defaults.get("institution", {}).items()
                            if key in {"name", "street", "house_number", "city", "postal_code",
                                       "country_code", "code", "phone", "fax", "email"}},
            "certificate": {key: value for key, value in shared_defaults.get("certificate", {}).items()
                            if key in {"member_state", "start_date", "end_date"}},
        }
    form = build_form_data(employee, institution_config, application_draft=True, completion_preview=True)
    if shared_defaults is not None:
        form["meta"]["shared_defaults"] = "operator_requested_osvc_baseline_unverified"

    missing = set(form["meta"]["missing_fields"])
    missing.update(omitted)
    if undecided_status:
        # Report the reviewed choice the worksheet still needs instead of guessing it.
        missing.add("a1.status_profile")
    missing.update(f"activity.{field}" for field in ("name", "address")
                   if not form["activity"].get(field))
    missing.update(("certificate.issue_date", "institution.signed_by"))
    if not form["institution"].get("name"):
        missing.add("institution")
    for field in ("start_date", "end_date"):
        if not form["certificate"].get(field):
            missing.add("certificate." + field)
    if posting_scenario:
        form["meta"]["posting_scenario"] = posting_scenario
        form["meta"]["scenario_source"] = "explicit_operator_selection"
        if form["activity"].get("address") == "DE":
            missing.add("activity.workplace_address")
    form["meta"]["missing_fields"] = sorted(missing)
    form["meta"]["variant"] = PROFILES.get(employee["a1"]["status_profile"]) or variant
    if undecided_status:
        form["meta"]["status_profile_undecided"] = True
        form["meta"]["status_profile_choices"] = list(STATUS_PROFILE_CHOICES)
    return form


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@audited("provisional_generate", "a1_provisional")
def generate(source_path: Path, employee_id: str, output: Path, *, variant=None, posting_scenario=None, shared_defaults_path: Path | None = None):
    source_path = protected_path(source_path, ("a1",))
    validate_output_path(output, source_employees=source_path)
    if not output.resolve().is_relative_to(protected_root() / "output/provisional"):
        raise ValueError("PREVIEW_REQUIRES_PROVISIONAL_DESTINATION")
    dependencies = [source_path, ROOT / "templates/a1_background.pdf", ROOT / "config/a1_layout.json",
                    ROOT / "config/address_enrichment.json", Path(__file__), ROOT / "scripts/a1_core.py",
                    ROOT / "scripts/pdf_named_fields.py"]
    if shared_defaults_path is not None:
        shared_defaults_path = shared_defaults_path.resolve()
        if shared_defaults_path != ROOT / "config/institution.json":
            raise ValueError("SHARED_BASELINE_MUST_BE_CANONICAL_CONFIG")
        dependencies.append(shared_defaults_path)
    before = [digest(path) for path in dependencies]
    shared_defaults = json.loads(shared_defaults_path.read_text()) if shared_defaults_path else None
    sources = json.loads(source_path.read_text())["employees"]
    selected = [source for source in sources if source.get("id") == employee_id]
    if len(selected) != 1:
        raise ValueError("EXACTLY_ONE_SELECTED_SOURCE_REQUIRED")
    form = build_preview(selected[0], variant=variant, posting_scenario=posting_scenario, shared_defaults=shared_defaults)
    staging = unique_staging_path(output.parent, "completion-preview")
    try:
        pdf = staging / "A1_completion_preview.pdf"
        pdf.touch(mode=0o600)
        generate_a1_pdf(form, dependencies[1], dependencies[2], pdf)
        pages = PdfReader(pdf).pages
        if len(pages) != 3 or any(APPLICATION_DRAFT_NOTICE not in page.extract_text() for page in pages):
            raise ValueError("PREVIEW_NOTICE_OR_PAGE_COUNT_FAILED")
        if PdfReader(pdf).get_fields():
            raise ValueError("INTERACTIVE_FORM_NOT_ALLOWED")
        previews = []
        with pymupdf.open(pdf) as document:
            for index, page in enumerate(document):
                target = staging / f"page-{index + 1}.png"
                page.get_pixmap(dpi=110).save(target)
                previews.append({"path": target.name, "sha256": digest(target)})
        # Rendering revalidates the form; build again to retain the fuller completion list.
        form = build_preview(selected[0], variant=variant, posting_scenario=posting_scenario, shared_defaults=shared_defaults)
        status_note = ""
        if form["meta"].get("status_profile_undecided"):
            status_note = ("Doplnit: a1.status_profile = posted_employee nebo employee_multi_state "
                           "(pracovní list zatím nevybírá 3.1/3.2; zaměstnanecká kategorie to "
                           "nerozhoduje)\n\n")
        (staging / "missing-fields.txt").write_text(
            "NEOVĚŘENÝ NÁVRH: prázdné údaje je nutné doplnit a ověřit.\n\n" + status_note +
            "\n".join(form["meta"]["missing_fields"]) + "\n")
        (staging / "form.json").write_text(json.dumps(form, ensure_ascii=False, indent=2) + "\n")
        manifest = {"status": "INCOMPLETE_UNVERIFIED_PREVIEW", "issued": False,
                    "review_flags_changed": False, "employee_count": 1,
                    "variant": form["meta"]["variant"],
                    "status_profile": form["meta"]["status_profile"],
                    "status_profile_choices": form["meta"].get("status_profile_choices"),
                    "posting_scenario": posting_scenario,
                    "shared_defaults": "config/institution.json" if shared_defaults_path else None,
                    "visual_review": "pending", "source_selection": "explicit_single_record",
                    "dependencies": [{"name": path.name, "sha256": sha} for path, sha in zip(dependencies, before)],
                    "pdf_sha256": digest(pdf), "previews": previews,
                    "missing_fields": form["meta"]["missing_fields"]}
        manifest["artifacts"] = {path.name: digest(path) for path in staging.iterdir()}
        (staging / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        if before != [digest(path) for path in dependencies]:
            raise ValueError("PREVIEW_INPUTS_CHANGED")
        for path in staging.iterdir():
            path.chmod(0o600)
        with destination_lock(output):
            publish_package(staging, output)
        return output
    except BaseException:
        cleanup_staging_only(staging, os.getpid())
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--employee-id", required=True)
    parser.add_argument("--variant", choices=("employee", "self_employed"))
    parser.add_argument("--posting-scenario", choices=("cz_employee_to_de",))
    parser.add_argument("--use-osvc-shared-defaults", action="store_true")
    args = parser.parse_args()
    root = protected_root()
    result = generate(root / "a1/employees_normalized.json", args.employee_id,
                      root / "output/provisional" / str(uuid.uuid4()), variant=args.variant,
                      posting_scenario=args.posting_scenario,
                      shared_defaults_path=ROOT / "config/institution.json" if args.use_osvc_shared_defaults else None)
    print(result)


if __name__ == "__main__":
    main()
