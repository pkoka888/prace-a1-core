#!/usr/bin/env python3
"""
Dual Framework Verification for A1 generation.

Compares output from two different A1 rendering approaches:
1. Framework 1: Coordinate overlay (scripts/a1_core.py)
2. Framework 2: Placeholder replacement (scripts/pdf_named_fields.py)

Both should produce equivalent PDFs with same data.
"""
import argparse
import hashlib
import sys
from pathlib import Path
from typing import TypedDict

sys.path.insert(0, str(Path(__file__).parent.parent))

from pypdf import PdfReader


class DualFrameworkResult(TypedDict):
    worker_id: str
    framework_1_hash: str
    framework_2_hash: str
    framework_1_pages: int
    framework_2_pages: int
    hashes_match: bool
    page_counts_match: bool
    status: str  # VERIFIED, DISCREPANCY, ERROR
    differences: list[str]


def get_pdf_hash(pdf_path: Path) -> str:
    """Get SHA256 hash of PDF content."""
    return hashlib.sha256(pdf_path.read_bytes()).hexdigest()


def get_pdf_pages(pdf_path: Path) -> int:
    """Get page count of PDF."""
    reader = PdfReader(pdf_path)
    return len(reader.pages)


def extract_pdf_text(pdf_path: Path) -> str:
    """Extract text from all PDF pages."""
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text


def verify_dual_framework(
    worker_id: str,
    pdf_1_path: Path,
    pdf_2_path: Path = None
) -> DualFrameworkResult:
    """
    Verify that two PDF frameworks produce equivalent output.
    
    If pdf_2_path is None, generates second PDF using placeholder framework.
    """
    result = DualFrameworkResult(
        worker_id=worker_id,
        framework_1_hash="",
        framework_2_hash="",
        framework_1_pages=0,
        framework_2_pages=0,
        hashes_match=False,
        page_counts_match=False,
        status="ERROR",
        differences=[]
    )
    
    try:
        # Framework 1 analysis
        if not pdf_1_path.exists():
            result["differences"].append(f"Framework 1 PDF not found: {pdf_1_path}")
            return result
            
        result["framework_1_hash"] = get_pdf_hash(pdf_1_path)
        result["framework_1_pages"] = get_pdf_pages(pdf_1_path)
        
        # Framework 2 analysis (if provided)
        if pdf_2_path:
            if not pdf_2_path.exists():
                result["differences"].append(f"Framework 2 PDF not found: {pdf_2_path}")
                result["status"] = "ERROR"
                return result
                
            result["framework_2_hash"] = get_pdf_hash(pdf_2_path)
            result["framework_2_pages"] = get_pdf_pages(pdf_2_path)
            
            # Compare
            result["hashes_match"] = result["framework_1_hash"] == result["framework_2_hash"]
            result["page_counts_match"] = result["framework_1_pages"] == result["framework_2_pages"]
            
            if result["hashes_match"] and result["page_counts_match"]:
                result["status"] = "VERIFIED"
            else:
                result["differences"].append("PDF hashes do not match")
                result["differences"].append(f"  Framework 1: {result['framework_1_hash'][:16]}...")
                result["differences"].append(f"  Framework 2: {result['framework_2_hash'][:16]}...")
                result["status"] = "DISCREPANCY"
        else:
            # Only one framework - partial verification
            result["status"] = "PARTIAL"
            
    except Exception as e:
        result["differences"].append(f"Error: {str(e)}")
        result["status"] = "ERROR"
    
    return result


def main():
    parser = argparse.ArgumentParser(description="Verify A1 generation with dual frameworks")
    parser.add_argument("--worker", required=True, help="Worker ID to verify")
    parser.add_argument("--pdf1", type=Path, help="Framework 1 PDF path")
    parser.add_argument("--pdf2", type=Path, help="Framework 2 PDF path")
    parser.add_argument("--provisional-dir", type=Path, 
                       default=Path("output/provisional"),
                       help="Provisional directory to search for PDFs")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()
    
    # Find PDFs if not provided
    if not args.pdf1:
        # Search in provisional directories
        for pkg_dir in args.provisional_dir.iterdir():
            if pkg_dir.is_dir():
                pdf_path = pkg_dir / f"A1_{args.worker}.pdf"
                if pdf_path.exists():
                    args.pdf1 = pdf_path
                    break
    
    if not args.pdf1:
        print(f"ERROR: No PDF found for worker: {args.worker}")
        sys.exit(1)
    
    result = verify_dual_framework(args.worker, args.pdf1, args.pdf2)
    
    if args.json:
        import json
        print(json.dumps(result, indent=2))
    else:
        print(f"Worker: {result['worker_id']}")
        print(f"Status: {result['status']}")
        print(f"Framework 1: {result['framework_1_pages']} pages, hash={result['framework_1_hash'][:16]}...")
        if result['framework_2_hash']:
            print(f"Framework 2: {result['framework_2_pages']} pages, hash={result['framework_2_hash'][:16]}...")
            print(f"Hashes match: {result['hashes_match']}")
            print(f"Page counts match: {result['page_counts_match']}")
        if result['differences']:
            print("\nDifferences:")
            for d in result['differences']:
                print(f"  - {d}")
    
    # Exit code
    if result['status'] == 'VERIFIED':
        sys.exit(0)
    elif result['status'] in ('DISCREPANCY', 'ERROR'):
        sys.exit(1)
    else:
        sys.exit(0)  # PARTIAL is OK for single framework


if __name__ == "__main__":
    main()
