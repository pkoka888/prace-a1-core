#!/usr/bin/env python3
"""
Schema Validator - Verify PDF meets expected schema.

VERIFICATION LAYER v0.3
"""
import argparse
import json
import sys
from pathlib import Path
from typing import TypedDict

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from pypdf import PdfReader


class SchemaResult(TypedDict):
    file_path: str
    file_type: str
    page_count: int
    is_encrypted: bool
    has_markers: bool
    errors: list
    status: str


def validate_pdf_schema(pdf_path: Path) -> SchemaResult:
    """Validate PDF schema."""
    result = SchemaResult(
        file_path=str(pdf_path),
        file_type="pdf",
        page_count=0,
        is_encrypted=False,
        has_markers=False,
        errors=[],
        status="INVALID"
    )
    
    try:
        reader = PdfReader(pdf_path)
        
        result["page_count"] = len(reader.pages)
        result["is_encrypted"] = reader.is_encrypted
        
        # Extract text
        text = "".join(page.extract_text() or "" for page in reader.pages)
        
        # Check for document markers
        result["has_markers"] = "N650" in text and "S558" in text
        
        # Validate
        errors = []
        if result["page_count"] != 3:
            errors.append(f"Expected 3 pages, got {result['page_count']}")
        if result["is_encrypted"]:
            errors.append("PDF should not be encrypted")
        if not result["has_markers"]:
            errors.append("Missing N650/S558 markers")
        
        result["errors"] = errors
        result["status"] = "VALID" if not errors else "INVALID"
        
    except Exception as e:
        result["errors"] = [str(e)]
        result["status"] = "ERROR"
    
    return result


def main():
    parser = argparse.ArgumentParser(description="Schema validator")
    parser.add_argument("--file", type=Path, required=True)
    args = parser.parse_args()
    
    result = validate_pdf_schema(args.file)
    
    print(f"File: {result['file_path']}")
    print(f"Status: {result['status']}")
    print(f"Pages: {result['page_count']}")
    print(f"Encrypted: {result['is_encrypted']}")
    print(f"Markers: {result['has_markers']}")
    
    if result['errors']:
        print("\nErrors:")
        for e in result['errors']:
            print(f"  - {e}")
    
    sys.exit(0 if result['status'] == "VALID" else 1)


if __name__ == "__main__":
    main()
