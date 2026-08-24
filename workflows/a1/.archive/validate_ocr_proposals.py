#!/usr/bin/env python3
"""Post-OCR validation gate for proposed employee rows.

Checks a proposed review CSV (as produced from OCR results) for missing and
malformed fields BEFORE they are promoted to the canonical `a1/review.csv` and
fed to the A1 generator, so generation never dies on a "Missing required A1
fields: ..." blocker.

Reads a CSV with columns matching the OCR merge (see ocr/new_people_review.csv).
Prints a per-person report. Exit code 0 = no blockers, 1 = missing/invalid
required values (blocker), 2 = only warnings.

Run:
    ./venv/bin/python scripts/validate_ocr_proposals.py [--csv ocr/new_people_review.csv]
"""

import argparse
import csv
import re
import sys

REQUIRED = [
    "employee_id", "surname", "given_name", "dob", "birth_place",
    "nationality", "sex", "rodne_cislo",
    "op_valid_from", "op_valid_to",
    "city", "district", "country_code",
]
REQUIRED_IF_USED = {
    "postal_code": "leave literal 'doplnit' if unknown so generation is not silently wrong",
}
# Fields that must be non-empty only when an address/street exists.
OPTIONAL = ["street", "house_number", "institution_profile", "resolved_ossz"]

MONTHS = {
    "01": "January", "02": "February", "03": "March", "04": "April",
    "05": "May", "06": "June", "07": "July", "08": "August", "09": "September",
    "10": "October", "11": "November", "12": "December",
}


def rodne_sex(rodne: str) -> str | None:
    """Sex encoded in a Czech rodné číslo: month+50 => female."""
    digits = re.sub(r"\D", "", rodne)
    if len(digits) < 4:
        return None
    month = int(digits[2:4])
    if 1 <= month <= 12:
        return "M"
    if 50 <= month <= 62:
        return "F"
    return None


def rodne_dob(rodne: str) -> str | None:
    """Return DD.MM.YYYY birth date from a rodné číslo, or None if unparseable."""
    digits = re.sub(r"\D", "", rodne)
    if len(digits) < 6:
        return None
    yy = int(digits[0:2])
    month = int(digits[2:4])
    day = int(digits[4:6])
    if 50 <= month <= 62:
        month -= 50
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return None
    year = 1900 + yy if yy >= 54 else 2000 + yy
    return f"{day:02d}.{month:02d}.{year}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="ocr/new_people_review.csv")
    ap.add_argument("--strict", action="store_true",
                    help="treat warnings as blockers (non-zero exit)")
    ap.add_argument("--fix", action="store_true",
                    help="write back deterministically derivable values: "
                         "sex from rodne_cislo, country_code CZE->CZ")
    args = ap.parse_args()

    try:
        rows = list(csv.DictReader(open(args.csv, encoding="utf-8-sig")))
    except FileNotFoundError:
        print(f"ERROR: {args.csv} not found")
        return 1

    if args.fix:
        changed = 0
        for r in rows:
            rodne = (r.get("rodne_cislo") or "").strip()
            sex = (r.get("sex") or "").strip()
            if not sex and rodne:
                dsex = rodne_sex(rodne)
                if dsex:
                    r["sex"] = dsex
                    changed += 1
            cc = (r.get("country_code") or "").strip().upper()
            if cc in ("CZE", "CZECH REPUBLIC"):
                r["country_code"] = "CZ"
                changed += 1
        if changed:
            keys = rows[0].keys()
            with open(args.csv, "w", encoding="utf-8-sig", newline="") as f:
                w = csv.DictWriter(f, fieldnames=keys)
                w.writeheader()
                w.writerows(rows)
            print(f"--fix applied {changed} correction(s) to {args.csv}\n")

    blockers, warnings = 0, 0
    print(f"Validating {len(rows)} rows from {args.csv}\n")
    for r in rows:
        name = r.get("employee_id", "?").strip() or "?"
        print(f"== {name} ==")
        row_block, row_warn = 0, 0

        for field in REQUIRED:
            val = (r.get(field) or "").strip()
            if not val:
                print(f"  MISSING  {field}")
                row_block += 1

        for field, hint in REQUIRED_IF_USED.items():
            val = (r.get(field) or "").strip()
            if not val:
                print(f"  MISSING  {field}  ({hint})")
                row_block += 1

        dob = (r.get("dob") or "").strip()
        if not re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", dob):
            print(f"  FORMAT   dob={dob!r} (expected DD.MM.YYYY)")
            row_block += 1

        sex = (r.get("sex") or "").strip()
        if sex and sex not in ("M", "F"):
            print(f"  FORMAT   sex={sex!r} (expected M or F)")
            row_block += 1

        rodne = (r.get("rodne_cislo") or "").strip()
        if rodne:
            dsex = rodne_sex(rodne)
            if dsex is None:
                print(f"  FORMAT   rodne_cislo={rodne!r} unparseable")
                row_block += 1
            elif sex and dsex != sex:
                print(f"  MISMATCH rodne_cislo={rodne} implies sex={dsex} but csv has {sex}")
                row_warn += 1
            elif not sex and dsex:
                print(f"  SUGGEST  sex={dsex} (derived from rodne_cislo)")
                row_warn += 1
            rdob = rodne_dob(rodne)
            if rdob and dob and rdob != dob:
                print(f"  MISMATCH dob={dob} vs rodne_cislo-derived {rdob}")
                row_warn += 1

        postal = (r.get("postal_code") or "").strip()
        if postal and postal != "doplnit" and not re.fullmatch(r"\d{3} ?\d{2}", postal):
            print(f"  FORMAT   postal_code={postal!r} (expected 5 digits)")
            row_warn += 1

        cc = (r.get("country_code") or "").strip()
        if cc and cc not in ("CZ", "DE"):
            print(f"  FORMAT   country_code={cc!r} (expected CZ or DE)")
            row_warn += 1

        for f in ("op_valid_from", "op_valid_to"):
            val = (r.get(f) or "").strip()
            if val and not re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", val):
                print(f"  FORMAT   {f}={val!r} (expected DD.MM.YYYY)")
                row_warn += 1

        print()
        blockers += row_block
        warnings += row_warn

    print(f"SUMMARY: {len(rows)} rows, {blockers} blocker(s), {warnings} warning(s)")
    if blockers:
        return 1
    if warnings and args.strict:
        return 1
    return 2 if warnings else 0


if __name__ == "__main__":
    sys.exit(main())
