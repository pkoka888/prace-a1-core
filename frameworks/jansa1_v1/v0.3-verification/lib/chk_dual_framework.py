#!/usr/bin/env python3
"""
Dual Framework Checker - Compare outputs from two implementations.

VERIFICATION LAYER v0.3
"""
import argparse
import hashlib
import sys
from pathlib import Path
from typing import TypedDict

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from pypdf import PdfReader


class DualFrameworkResult(TypedDict):
    worker_id: str
    framework_1_hash: str
    framework_2_hash: str
    hashes_match: bool
    status: str


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
        framework_1_hash="",
        framework_2_hash="",
        hashes_match=False,
        status="ERROR"
    )
    
    try:
        if not pdf_1_path.exists():
            result["status"] = "ERROR: PDF1 not found"
            return result
            
        result["framework_1_hash"] = get_pdf_hash(pdf_1_path)
        
        if pdf_2_path and pdf_2_path.exists():
            result["framework_2_hash"] = get_pdf_hash(pdf_2_path)
            result["hashes_match"] = (
                result["framework_1_hash"] == result["framework_2_hash"]
            )
            result["status"] = "VERIFIED" if result["hashes_match"] else "DISCREPANCY"
        else:
            result["status"] = "PARTIAL"
            
    except Exception as e:
        result["status"] = f"ERROR: {e}"
    
    return result


def main():
    parser = argparse.ArgumentParser(description="Dual framework verification")
    parser.add_argument("--worker", required=True)
    parser.add_argument("--pdf1", type=Path, required=True)
    parser.add_argument("--pdf2", type=Path, default=None)
    args = parser.parse_args()
    
    result = verify_dual_framework(args.worker, args.pdf1, args.pdf2)
    
    print(f"Worker: {result['worker_id']}")
    print(f"Status: {result['status']}")
    print(f"Hash 1: {result['framework_1_hash'][:16]}...")
    if result['framework_2_hash']:
        print(f"Hash 2: {result['framework_2_hash'][:16]}...")
        print(f"Match: {result['hashes_match']}")
    
    sys.exit(0 if "VERIFIED" in result['status'] else 1)


if __name__ == "__main__":
    main()
