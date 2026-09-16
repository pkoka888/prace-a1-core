#!/usr/bin/env python3
"""
Dual Framework Checker - Compare outputs from two implementations.

VERIFICATION LAYER v0.3

Compares PDFs from two different frameworks to ensure they produce
identical output. Both inputs must be valid PDFs.
"""
import argparse
import hashlib
import sys
from pathlib import Path
from typing import TypedDict

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from pypdf import PdfReader
from pypdf.errors import PdfReadError


class DualFrameworkResult(TypedDict):
    worker_id: str
    pdf1_valid: bool
    pdf2_valid: bool
    framework_1_hash: str
    framework_2_hash: str
    hashes_match: bool
    status: str
    errors: list


def is_valid_pdf(pdf_path: Path) -> tuple[bool, str]:
    """Check if file is a valid PDF. Returns (is_valid, error_message)."""
    if not pdf_path.exists():
        return False, "File does not exist"
    if pdf_path.suffix.lower() != ".pdf":
        return False, "File does not have .pdf extension"
    try:
        reader = PdfReader(pdf_path)
        # Try to read at least one page
        if len(reader.pages) == 0:
            return False, "PDF has no pages"
        return True, ""
    except PdfReadError as e:
        return False, f"Not a valid PDF: {e}"
    except Exception as e:
        return False, f"Error reading PDF: {e}"


def get_pdf_hash(pdf_path: Path) -> str:
    """Get SHA256 hash of PDF content."""
    return hashlib.sha256(pdf_path.read_bytes()).hexdigest()


def verify_dual_framework(
    worker_id: str,
    pdf_1_path: Path,
    pdf_2_path: Path = None
) -> DualFrameworkResult:
    """Compare PDFs from two different frameworks."""
    result = DualFrameworkResult(
        worker_id=worker_id,
        pdf1_valid=False,
        pdf2_valid=False,
        framework_1_hash="",
        framework_2_hash="",
        hashes_match=False,
        status="ERROR",
        errors=[]
    )
    
    # Validate PDF1
    valid1, error1 = is_valid_pdf(pdf_1_path)
    result["pdf1_valid"] = valid1
    if not valid1:
        result["errors"].append(f"PDF1: {error1}")
        return result
    
    try:
        result["framework_1_hash"] = get_pdf_hash(pdf_1_path)
    except Exception as e:
        result["errors"].append(f"PDF1 hash: {e}")
        return result
    
    # Validate PDF2 if provided
    if pdf_2_path:
        valid2, error2 = is_valid_pdf(pdf_2_path)
        result["pdf2_valid"] = valid2
        
        if not valid2:
            result["errors"].append(f"PDF2: {error2}")
            result["status"] = "ERROR"
            return result
        
        try:
            result["framework_2_hash"] = get_pdf_hash(pdf_2_path)
        except Exception as e:
            result["errors"].append(f"PDF2 hash: {e}")
            result["status"] = "ERROR"
            return result
        
        # Compare hashes
        result["hashes_match"] = (
            result["framework_1_hash"] == result["framework_2_hash"]
        )
        
        if result["hashes_match"]:
            result["status"] = "VERIFIED"
        else:
            result["status"] = "DISCREPANCY"
            result["errors"].append("Hashes do not match - outputs differ")
    else:
        result["status"] = "PARTIAL"
        result["errors"].append("PDF2 not provided - cannot compare")
    
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Dual framework verification",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Compares PDFs from two frameworks to ensure identical output.
Both inputs must be valid PDF files.
        """
    )
    parser.add_argument("--worker", required=True, help="Worker ID")
    parser.add_argument("--pdf1", type=Path, required=True, help="PDF from framework 1")
    parser.add_argument("--pdf2", type=Path, default=None, help="PDF from framework 2 (optional)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()
    
    result = verify_dual_framework(args.worker, args.pdf1, args.pdf2)
    
    if args.json:
        import json
        print(json.dumps(result, indent=2, default=str))
    else:
        print(f"Worker: {result['worker_id']}")
        print(f"Status: {result['status']}")
        print(f"PDF1 Valid: {result['pdf1_valid']}")
        print(f"PDF2 Valid: {result['pdf2_valid']}")
        print(f"Hash 1: {result['framework_1_hash'][:32] if result['framework_1_hash'] else 'N/A'}...")
        
        if result['framework_2_hash']:
            print(f"Hash 2: {result['framework_2_hash'][:32]}...")
            print(f"Match: {result['hashes_match']}")
        
        if result['errors']:
            print("\nErrors:")
            for e in result['errors']:
                print(f"  ✗ {e}")
    
    # Exit with error for ERROR or DISCREPANCY
    if result['status'] in ('ERROR', 'DISCREPANCY'):
        sys.exit(1)
    elif result['status'] == 'PARTIAL':
        sys.exit(2)  # Partial success
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
