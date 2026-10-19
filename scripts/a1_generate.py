#!/usr/bin/env python3
"""One routine: worker bundle in -> complete A1 PDF out (v1 token template).

Reads review row + cohort + institution profile, composes form data through
the shared core, fills the v1 token template copy renamed per worker.
No checkboxes are marked (original majority: unchecked). Provisional
validity derives from issue_date like the canonical publisher.

Usage:
  export A1_PRIVATE_DIR="$(git rev-parse --show-toplevel)"
  venv/bin/python scripts/a1_generate.py --worker tomas-nistor --output <dir>
"""
from __future__ import annotations
import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from finalize_a1 import row_to_form, load_profile  # noqa: E402
from generate_a1_placeholder import flatten_form_data  # noqa: E402
from pdf_named_fields import (  # noqa: E402
    replace_placeholders, draw_checkbox_x, CHECKBOX_X_MARKS,
    SECTION3_BOXES, SECTION4_BOXES,
)
from a1_core import (  # noqa: E402
    FONT_CANDIDATES, provisional_one_year_period,
)

TEMPLATE = ROOT / "templates" / "a1_template_v1.pdf"
FIELDS = ROOT / "templates" / "a1_template_v1_fields.json"


def generate_worker(worker_id: str, output_dir: Path) -> Path:
    review_path = ROOT / "a1" / worker_id / "review.csv"
    row = next(csv.DictReader(open(review_path, encoding="utf-8-sig")))
    if not row.get("start_date") and row.get("issue_date"):
        row["start_date"], row["end_date"] = provisional_one_year_period(
            row["issue_date"])
    profile = load_profile(ROOT / "config" / "institutions",
                           row["institution_profile"], provisional=True)
    form = row_to_form(row, profile)
    values = flatten_form_data(form)
    # v1-only tokens not covered by legacy flatten
    values["institution.phone_fax"] = form.get("institution", {}).get(
        "phone_fax", "")
    values["institution.phone_tel"] = form.get("institution", {}).get(
        "phone_tel", "")
    values["institution.email"] = form.get("institution", {}).get("email", "")
    values.setdefault("activity.address",
                      row.get("activity_address", "") or "")
    font = str(next(p for p in FONT_CANDIDATES if p.exists()))
    fields = json.loads(FIELDS.read_text(encoding="utf-8"))
    result = replace_placeholders(TEMPLATE.read_bytes(), fields, values, font)
    # self-employed: gender + 3.4 + 4.1.2 (original majority: unchecked boxes)
    import pymupdf
    sex = (row.get("sex", "") or "").strip().upper()
    marks = []
    if row.get("status_profile") == "self_employed_multi_state":
        marks += [("3.4", 1), ("4.1.2", 1)]
    if sex == "M":
        marks.append(("gender_male", 0))
    elif sex == "F":
        marks.append(("gender_female", 0))
    if marks:
        doc = pymupdf.open(stream=result, filetype="pdf")
        for key, _ in marks:
            if key in CHECKBOX_X_MARKS:
                cfg = CHECKBOX_X_MARKS[key]
                draw_checkbox_x(doc[cfg["page"]], cfg["rect"],
                                cfg["color"])
            elif key in SECTION3_BOXES:
                draw_checkbox_x(doc[1], SECTION3_BOXES[key], (0, 0, 0))
            elif key in SECTION4_BOXES:
                draw_checkbox_x(doc[1], SECTION4_BOXES[key], (0, 0, 0))
        result = doc.tobytes(garbage=4, deflate=True)
        doc.close()
    output_dir.mkdir(parents=True, exist_ok=True)
    out = output_dir / f"A1_{worker_id}.pdf"
    out.write_bytes(result)
    out.chmod(0o600)
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    out = generate_worker(args.worker, args.output)
    print(f"Generated: {out} ({out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
