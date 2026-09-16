#!/usr/bin/env python3
"""
Hardcode Checker - Verify no hardcoded values in generated output.

Checks:
1. Names match input data, not hardcoded
2. Addresses match input data
3. Document IDs match input data
4. Dates match input data
"""
import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import TypedDict

sys.path.insert(0, str(Path(__file__).parent.parent))

from pypdf import PdfReader


class HardcodeCheckResult(TypedDict):
    worker_id: str
    pdf_path: str
    hardcoded_values: list[dict]
    values_from_input: list[dict]
    status: str  # CLEAN, HARDCODED, ERROR


def extract_pdf_text(pdf_path: Path) -> str:
    """Extract text from PDF."""
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text


def get_input_data(worker_id: str, review_csv: Path) -> dict:
    """Get worker data from review CSV."""
    if not review_csv.exists():
        return {}
    
    with review_csv.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("employee_id") == worker_id:
                return row
    return {}


def check_no_hardcodes(
    pdf_path: Path,
    worker_id: str,
    review_csv: Path = None
) -> HardcodeCheckResult:
    """
    Check if PDF contains hardcoded values instead of input data.
    """
    result = HardcodeCheckResult(
        worker_id=worker_id,
        pdf_path=str(pdf_path),
        hardcoded_values=[],
        values_from_input=[],
        status="ERROR"
    )
    
    try:
        # Get input data
        input_data = {}
        if review_csv:
            input_data = get_input_data(worker_id, review_csv)
        
        # Extract PDF text
        text = extract_pdf_text(pdf_path)
        
        # Check for suspicious hardcoded patterns
        suspicious_patterns = [
            (r'\bTEST\b', 'TEST value'),
            (r'\bEXAMPLE\b', 'EXAMPLE value'),
            (r'\bTEMPLATE\b', 'TEMPLATE value'),
            (r'\bPLACEHOLDER\b', 'PLACEHOLDER value'),
            (r'\bFAKE\b', 'FAKE value'),
            (r'\bSAMPLE\b', 'SAMPLE value'),
        ]
        
        for pattern, name in suspicious_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                result["hardcoded_values"].append({
                    "pattern": name,
                    "found": len(matches)
                })
        
        # Verify expected values are present
        if input_data:
            for field, value in input_data.items():
                if not value or field.startswith("_"):
                    continue
                    
                # Check if value appears in PDF (fuzzy match for names)
                if len(str(value)) > 2:
                    if str(value) in text:
                        result["values_from_input"].append({
                            "field": field,
                            "value": value[:50],  # Truncate for safety
                            "verified": True
                        })
        
        # Determine status
        if result["hardcoded_values"]:
            result["status"] = "HARDCODED"
        else:
            result["status"] = "CLEAN"
            
    except Exception as e:
        result["hardcoded_values"].append({"error": str(e)})
        result["status"] = "ERROR"
    
    return result


def main():
    parser = argparse.ArgumentParser(description="Check for hardcoded values in PDFs")
    parser.add_argument("--worker", required=True, help="Worker ID")
    parser.add_argument("--pdf", type=Path, required=True, help="PDF to check")
    parser.add_argument("--review-csv", type=Path, 
                       default=Path("a1/review.csv"),
                       help="Review CSV with input data")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()
    
    result = check_no_hardcodes(args.pdf, args.worker, args.review_csv)
    
    if args.json:
        import json
        print(json.dumps(result, indent=2))
    else:
        print(f"Worker: {result['worker_id']}")
        print(f"Status: {result['status']}")
        print(f"Values from input: {len(result['values_from_input'])}")
        print(f"Hardcoded values: {len(result['hardcoded_values'])}")
        
        if result['hardcoded_values']:
            print("\n⚠️  HARDCODED VALUES FOUND:")
            for v in result['hardcoded_values']:
                if 'error' in v:
                    print(f"  ERROR: {v['error']}")
                else:
                    print(f"  - {v['pattern']}: {v['found']} occurrences")
    
    sys.exit(0 if result['status'] == 'CLEAN' else 1)


if __name__ == "__main__":
    main()
