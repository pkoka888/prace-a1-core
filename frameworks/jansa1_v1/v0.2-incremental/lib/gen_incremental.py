#!/usr/bin/env python3
"""
Incremental A1 Generator - Generate only missing PDFs.

GENERATION LAYER v0.2

Usage:
    python gen_incremental.py [--review CSV] [--profiles DIR] [--output DIR] \
                              [--worker ID] [--all] [--dry-run]

Examples:
    python gen_incremental.py                    # Generate all missing
    python gen_incremental.py --worker jiri-stembera  # Specific worker
    python gen_incremental.py --dry-run           # Preview without generating
"""
import argparse
import csv
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))


def get_generated_workers(output_dir: Path) -> set:
    """Find workers with existing PDFs."""
    generated = set()
    if not output_dir.exists():
        return generated
    
    for pkg_dir in output_dir.iterdir():
        if pkg_dir.is_dir():
            for pdf in pkg_dir.glob("A1_*.pdf"):
                generated.add(pdf.stem.replace("A1_", ""))
    return generated


def read_review_csv(csv_path: Path) -> list:
    """Read review CSV."""
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return [{k: (v.strip() if v else "") for k, v in row.items()} for row in reader]


def generate_incremental(
    review_csv: Path,
    profiles_dir: Path,
    output_dir: Path,
    workers: list = None,
    dry_run: bool = False
) -> list:
    """Generate missing PDFs. Returns list of generated worker IDs."""
    # Import core modules here to allow --help without imports
    from scripts.a1_core import (
        build_form_data,
        generate_a1_pdf,
        provisional_one_year_period,
    )
    from scripts.finalize_a1 import (
        display_row,
        validate_profile,
    )
    
    os.environ.setdefault("A1_PRIVATE_DIR", str(ROOT))
    
    all_workers = read_review_csv(review_csv)
    all_ids = {row["employee_id"] for row in all_workers}
    existing = get_generated_workers(output_dir)
    
    # Determine what to generate
    if workers:
        to_generate = set(workers) & all_ids
    else:
        to_generate = all_ids - existing
    
    if dry_run:
        print(f"Would generate: {len(to_generate)} workers")
        for w in sorted(to_generate):
            print(f"  - {w}")
        return []
    
    if not to_generate:
        print(f"✓ All {len(all_ids)} workers already have PDFs")
        return []
    
    print(f"Generating {len(to_generate)} workers: {sorted(to_generate)}")
    
    # Create staging
    run_id = str(uuid.uuid4())
    staging = output_dir / f"provisional-{run_id}"
    staging.mkdir(parents=True, exist_ok=True)
    
    generated = []
    errors = []
    
    for worker_id in sorted(to_generate):
        row = next(r for r in all_workers if r["employee_id"] == worker_id)
        
        try:
            profile_id = row.get("institution_profile", "")
            profile_path = profiles_dir / f"{profile_id}.json"
            
            if not profile_path.exists():
                errors.append(f"{worker_id}: Profile not found: {profile_id}")
                continue
            
            profile = json.loads(profile_path.read_text())
            validate_profile(profile, profile_id, provisional=True)
            
            # Process data
            displayed = display_row(row)
            if not displayed.get("start_date") and displayed.get("issue_date"):
                displayed["start_date"], displayed["end_date"] = provisional_one_year_period(
                    displayed["issue_date"]
                )
            
            # Build form and generate PDF
            form = build_form_data(displayed, profile, provisional=True)
            pdf_path = staging / f"A1_{worker_id}.pdf"
            
            generate_a1_pdf(
                form,
                ROOT / "templates" / "a1_background.pdf",
                ROOT / "config" / "a1_layout.json",
                pdf_path
            )
            
            generated.append(worker_id)
            print(f"✓ {worker_id}: {pdf_path.stat().st_size // 1024}KB")
            
        except Exception as e:
            errors.append(f"{worker_id}: {e}")
    
    # Write manifest
    manifest = {
        "status": "PROVISIONAL_NOT_FOR_OFFICIAL_USE",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "generated": generated,
        "errors": errors,
    }
    (staging / "generation_manifest.json").write_text(json.dumps(manifest, indent=2))
    
    print(f"\n✓ Generated {len(generated)} PDFs to {staging}")
    if errors:
        print(f"✗ {len(errors)} errors:")
        for e in errors:
            print(f"  - {e}")
    
    return generated


def main():
    parser = argparse.ArgumentParser(
        description="Incremental A1 generator - generates only missing PDFs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python gen_incremental.py                    # Generate all missing
  python gen_incremental.py --worker jiri-stembera  # Specific worker
  python gen_incremental.py --dry-run           # Preview without generating
        """
    )
    parser.add_argument("--review", type=Path, default=ROOT / "a1" / "review.csv")
    parser.add_argument("--profiles", type=Path, default=ROOT / "config" / "institutions")
    parser.add_argument("--output", type=Path, default=ROOT / "output" / "provisional")
    parser.add_argument("--worker", action="append", default=[],
                        help="Specific worker ID (can repeat)")
    parser.add_argument("--all", action="store_true",
                        help="Regenerate all (ignore existing)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be generated")
    args = parser.parse_args()
    
    try:
        result = generate_incremental(
            args.review, args.profiles, args.output,
            args.worker or None, args.dry_run
        )
        # Exit with error if no PDFs generated (unless dry-run or all missing)
        if not args.dry_run and not result:
            print("WARNING: No PDFs generated. Check errors above.")
            sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
