#!/usr/bin/env python3
"""
Schema Validator - Verify PDF meets expected schema.

VERIFICATION LAYER v0.3

Validates:
- PDF is a valid PDF file (not just has .pdf extension)
- Has exactly 3 pages
- Is not encrypted
- Contains document ID marker (NxxxxxSxxx/YYYY/DE format)
- Contains worker facts (name, DOB) - not just markers
"""
import argparse
import re
import sys
from pathlib import Path
from typing import TypedDict

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from pypdf import PdfReader
from pypdf.errors import PdfReadError


class SchemaResult(TypedDict):
    file_path: str
    file_type: str
    page_count: int
    is_encrypted: bool
    has_markers: bool
    has_worker_facts: bool
    errors: list
    warnings: list
    status: str


def validate_pdf_schema(pdf_path: Path, require_worker_facts: bool = True) -> SchemaResult:
    """Validate PDF schema."""
    result = SchemaResult(
        file_path=str(pdf_path),
        file_type="pdf",
        page_count=0,
        is_encrypted=False,
        has_markers=False,
        has_worker_facts=False,
        errors=[],
        warnings=[],
        status="INVALID"
    )
    
    # First check if it's a real PDF
    if pdf_path.suffix.lower() != ".pdf":
        result["errors"].append("File does not have .pdf extension")
        result["status"] = "ERROR"
        return result
    
    try:
        # Try to open as PDF - this will fail for non-PDF files
        reader = PdfReader(pdf_path)
        
        result["page_count"] = len(reader.pages)
        result["is_encrypted"] = reader.is_encrypted
        
        # Check if pages are actually blank (less than 100 chars total)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text() or ""
            text += page_text
        
        if len(text.strip()) < 100:
            result["warnings"].append("PDF appears to have minimal text content")
        
        # Check for document markers
        doc_id_pattern = re.compile(r'N\d{5}S\d{3}/\d{4}/DE')
        result["has_markers"] = bool(doc_id_pattern.search(text))
        
        # Check for worker facts (name, DOB)
        name_pattern = re.compile(r'[A-ZČĎĚŘŠŤŮŽ][a-zčďěřšťůž]+ [A-ZČĎĚŘŠŤŮŽ][a-zčďěřšťůž]+')
        dob_pattern = re.compile(r'\d{2}\.\d{2}\.\d{4}')
        
        result["has_worker_facts"] = bool(
            name_pattern.search(text) or 
            (dob_pattern.findall(text) and len(dob_pattern.findall(text)) >= 2)
        )
        
        # Build errors list
        if result["page_count"] != 3:
            result["errors"].append(f"Expected 3 pages, got {result['page_count']}")
        if result["is_encrypted"]:
            result["errors"].append("PDF should not be encrypted")
        if not result["has_markers"]:
            result["errors"].append("Missing NxxxxxSxxx/YYYY/DE document ID")
        if require_worker_facts and not result["has_worker_facts"]:
            result["errors"].append("Missing worker facts (name or DOB)")
        
        result["status"] = "VALID" if not result["errors"] else "INVALID"
        
    except PdfReadError as e:
        result["errors"].append(f"Not a valid PDF: {e}")
        result["status"] = "ERROR"
    except Exception as e:
        result["errors"].append(f"Error reading PDF: {e}")
        result["status"] = "ERROR"
    
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Schema validator for A1 PDFs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Validates:
  - File is a valid PDF (not just .pdf extension)
  - Has exactly 3 pages
  - Is not encrypted
  - Contains document ID (NxxxxxSxxx/YYYY/DE format)
  - Contains worker facts (name or DOB)
        """
    )
    parser.add_argument("--file", type=Path, required=True, help="PDF file to validate")
    parser.add_argument("--no-worker-facts", action="store_true", 
                        help="Don't require worker facts (for marker-only PDFs)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()
    
    result = validate_pdf_schema(args.file, not args.no_worker_facts)
    
    if args.json:
        import json
        print(json.dumps(result, indent=2, default=str))
    else:
        print(f"File: {result['file_path']}")
        print(f"Status: {result['status']}")
        print(f"Pages: {result['page_count']}")
        print(f"Encrypted: {result['is_encrypted']}")
        print(f"Document ID: {result['has_markers']}")
        print(f"Worker Facts: {result['has_worker_facts']}")
        
        if result['warnings']:
            print("\nWarnings:")
            for w in result['warnings']:
                print(f"  ⚠ {w}")
        
        if result['errors']:
            print("\nErrors:")
            for e in result['errors']:
                print(f"  ✗ {e}")
    
    sys.exit(0 if result['status'] == "VALID" else 1)


if __name__ == "__main__":
    main()
