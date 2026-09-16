#!/usr/bin/env python3
"""
Hardcode Checker - Verify no hardcoded values in PDF output.

VERIFICATION LAYER v0.3
"""
import argparse
import csv
import re
import sys
from pathlib import Path
from typing import TypedDict

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from pypdf import PdfReader


class HardcodeResult(TypedDict):
    worker_id: str
    hardcoded_values: list
    values_from_input: list
    status: str


def extract_pdf_text(pdf_path: Path) -> str:
    """Extract text from PDF."""
    reader = PdfReader(pdf_path)
    return "".join(page.extract_text() or "" for page in reader.pages)


def check_no_hardcodes(
    pdf_path: Path,
    worker_id: str,
    review_csv: Path = None
) -> HardcodeResult:
    """Check for hardcoded test values."""
    result = HardcodeResult(
        worker_id=worker_id,
        hardcoded_values=[],
        values_from_input=[],
        status="CLEAN"
    )
    
    try:
        text = extract_pdf_text(pdf_path)
        
        # Check for suspicious patterns
        patterns = [
            (r'\bTEST\b', 'TEST'),
            (r'\bEXAMPLE\b', 'EXAMPLE'),
            (r'\bTEMPLATE\b', 'TEMPLATE'),
            (r'\bPLACEHOLDER\b', 'PLACEHOLDER'),
        ]
        
        for pattern, name in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                result["hardcoded_values"].append(name)
        
        result["status"] = "HARDCODED" if result["hardcoded_values"] else "CLEAN"
        
    except Exception as e:
        result["status"] = f"ERROR: {e}"
    
    return result


def main():
    parser = argparse.ArgumentParser(description="Hardcode checker")
    parser.add_argument("--worker", required=True)
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--review-csv", type=Path, default=None)
    args = parser.parse_args()
    
    result = check_no_hardcodes(args.pdf, args.worker, args.review_csv)
    
    print(f"Worker: {result['worker_id']}")
    print(f"Status: {result['status']}")
    print(f"Hardcoded: {len(result['hardcoded_values'])}")
    
    sys.exit(0 if result['status'] == "CLEAN" else 1)


if __name__ == "__main__":
    main()
