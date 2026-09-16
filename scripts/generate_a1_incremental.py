#!/usr/bin/env python3
"""
Incremental A1 generation - generates only missing PDFs.

Uses the same core logic as generate_provisional_a1.py:
  - display_row() for Czech casing (ALL-CAPS → Proper case)
  - row_to_form() for CSV → nested structure
  - build_form_data() for enrichment and validation
  - PDF renderer for final output

Usage:
  python scripts/generate_a1_incremental.py           # Generate all missing
  python scripts/generate_a1_incremental.py --worker jiri-stembera  # Specific worker
  python scripts/generate_a1_incremental.py --all     # Force regenerate all

Output goes to output/provisional/
"""
import argparse
import csv
import hashlib
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.a1_core import (
    APPLICATION_DRAFT_NOTICE,
    build_form_data,
    generate_a1_pdf,
    load_json,
    provisional_one_year_period,
)
from scripts.finalize_a1 import (
    CSV_FIELDS,
    display_row,
    load_profile,
    validate_profile,
    validate_review,
    row_to_form,
    FinalizationError,
)
from scripts.a1_paths import (
    protected_root,
    unique_staging_path,
    destination_lock,
    publish_package,
)


def get_generated_workers(provisional_dir: Path) -> set[str]:
    """Find all workers that already have PDFs generated."""
    generated = set()
    
    if not provisional_dir.exists():
        return generated
    
    # Check existing manifests
    for pkg_dir in provisional_dir.iterdir():
        if not pkg_dir.is_dir():
            continue
        manifest_path = pkg_dir / "generation_manifest.json"
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text())
                for entry in manifest.get("generated", []):
                    generated.add(entry.get("employee_id", ""))
            except Exception:
                pass
        
        # Also check for loose PDF files
        for pdf in pkg_dir.glob("A1_*.pdf"):
            worker_id = pdf.stem.replace("A1_", "")
            generated.add(worker_id)
    
    return generated


def read_review_csv(csv_path: Path) -> list[dict]:
    """Read review CSV and return list of row dicts."""
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            # Clean None values
            rows.append({k: (v.strip() if v else "") for k, v in row.items()})
        return rows


def main():
    parser = argparse.ArgumentParser(description="Generate A1 forms incrementally")
    parser.add_argument("--review", type=Path, default=ROOT / "a1" / "review.csv",
                        help="Review CSV file")
    parser.add_argument("--cohort", type=Path, default=ROOT / "a1" / "cohort.json",
                        help="Cohort JSON file")
    parser.add_argument("--profiles", type=Path, default=ROOT / "config" / "institutions",
                        help="Institution profiles directory")
    parser.add_argument("--config", type=Path, default=ROOT / "config" / "a1_provisional.json",
                        help="Provisional config file")
    parser.add_argument("--output", type=Path, default=ROOT / "output" / "provisional",
                        help="Output directory")
    parser.add_argument("--worker", action="append", default=[],
                        help="Specific worker ID to generate (can repeat)")
    parser.add_argument("--all", action="store_true",
                        help="Regenerate all (ignore existing)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be generated without generating")
    args = parser.parse_args()

    # Ensure A1_PRIVATE_DIR is set
    os.environ.setdefault("A1_PRIVATE_DIR", str(ROOT))

    # Read review CSV
    if not args.review.exists():
        print(f"ERROR: Review CSV not found: {args.review}")
        sys.exit(1)

    all_workers = read_review_csv(args.review)
    all_worker_ids = {row["employee_id"] for row in all_workers}

    # Find already generated
    already_generated = get_generated_workers(args.output)

    # Determine what to generate
    if args.worker:
        # Specific workers requested
        to_generate = set(args.worker) & all_worker_ids
        missing = to_generate - already_generated
        extra = set(args.worker) - all_worker_ids
        if extra:
            print(f"WARNING: Unknown workers: {extra}")
        to_generate = missing if not args.all else to_generate
    else:
        # All missing workers
        to_generate = all_worker_ids - already_generated

    if not to_generate:
        print(f"✓ All {len(all_worker_ids)} workers already have PDFs")
        return 0

    print(f"Workers to generate: {len(to_generate)}")
    for wid in sorted(to_generate):
        print(f"  - {wid}")

    if args.dry_run:
        print("\n[Dry run - no files generated]")
        return 0

    # Load cohort and config
    cohort = json.loads(args.cohort.read_text()) if args.cohort.exists() else {}
    prov_config = json.loads(args.config.read_text()) if args.config.exists() else {}
    notice = prov_config.get("notice", "CLIENT_CONFIRMATION_COPY")

    # Generate for each worker
    run_id = str(uuid.uuid4())
    staging = unique_staging_path(args.output, f"provisional-{run_id}")
    staging.mkdir(parents=True, exist_ok=True)

    generated = []
    errors = []

    for worker_id in sorted(to_generate):
        row = next(r for r in all_workers if r["employee_id"] == worker_id)
        
        try:
            # Get profile
            profile_id = row.get("institution_profile", "")
            if not profile_id:
                raise ValueError("Missing institution_profile")
            
            profile_path = args.profiles / f"{profile_id}.json"
            if not profile_path.exists():
                raise ValueError(f"Profile not found: {profile_id}")
            
            profile = json.loads(profile_path.read_text())
            validate_profile(profile, profile_id, provisional=True)

            # Use core logic: display_row → row_to_form → build_form_data
            # This handles ALL-CAPS conversion, Czech casing, enrichment
            displayed_row = display_row(row)
            
            # Derive start/end dates from issue_date if missing (same as main script)
            if not displayed_row.get("start_date") and displayed_row.get("issue_date"):
                displayed_row["start_date"], displayed_row["end_date"] = provisional_one_year_period(
                    displayed_row["issue_date"]
                )
            employee_data = row_to_form(displayed_row, profile, application_draft=False)

            # Generate PDF using core logic
            pdf_path = staging / f"A1_{worker_id}.pdf"
            template = ROOT / "templates" / "a1_background.pdf"
            layout = ROOT / "config" / "a1_layout.json"

            generate_a1_pdf(employee_data, template, layout, pdf_path)

            # Get PDF info
            sha256 = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
            from pypdf import PdfReader
            pdf = PdfReader(pdf_path)
            page_count = len(pdf.pages)

            generated.append({
                "employee_id": worker_id,
                "path": pdf_path.name,
                "page_count": page_count,
                "sha256": sha256,
                "size_bytes": pdf_path.stat().st_size,
            })
            print(f"✓ {worker_id}: {page_count} pages")

        except Exception as e:
            errors.append({"employee_id": worker_id, "error": str(e)})
            print(f"✗ {worker_id}: {e}")

    # Write manifest
    manifest = {
        "status": "PROVISIONAL_NOT_FOR_OFFICIAL_USE",
        "notice": notice,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "generated": generated,
        "errors": errors,
    }
    (staging / "generation_manifest.json").write_text(json.dumps(manifest, indent=2))

    print(f"\n✓ Generated {len(generated)} PDFs")
    if errors:
        print(f"✗ {len(errors)} errors")
        return 1

    # Publish the package (rename staging to final)
    import shutil
    import stat
    
    # The staging dir is already the final destination, just set permissions
    for root, dirs, files in os.walk(staging):
        os.chmod(root, stat.S_IRWXU)
        for f in files:
            os.chmod(os.path.join(root, f), stat.S_IRUSR | stat.S_IWUSR)
    
    print(f"✓ Saved to: {staging}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
