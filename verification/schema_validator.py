#!/usr/bin/env python3
"""
Schema Validator - Verify output matches expected schema.

Validates:
1. PDF structure (page count, encryption)
2. JSON outputs (manifest, receipts)
3. CSV outputs (verification tables)
"""
import argparse
import csv
import json
import sys
from pathlib import Path
from typing import TypedDict

sys.path.insert(0, str(Path(__file__).parent.parent))

from pypdf import PdfReader


class SchemaValidationResult(TypedDict):
    file_path: str
    file_type: str  # pdf, json, csv
    schema_valid: bool
    errors: list[str]
    warnings: list[str]
    status: str  # VALID, INVALID, WARNING, ERROR


def validate_pdf_schema(pdf_path: Path) -> SchemaValidationResult:
    """Validate PDF meets expected schema."""
    result = SchemaValidationResult(
        file_path=str(pdf_path),
        file_type="pdf",
        schema_valid=False,
        errors=[],
        warnings=[],
        status="ERROR"
    )
    
    try:
        reader = PdfReader(pdf_path)
        
        # Check page count (A1 should be 3 pages)
        if len(reader.pages) != 3:
            result["errors"].append(f"Expected 3 pages, got {len(reader.pages)}")
        else:
            result["warnings"].append("Page count: 3 ✓")
        
        # Check not encrypted
        if reader.is_encrypted:
            result["errors"].append("PDF is encrypted (should not be)")
        else:
            result["warnings"].append("Not encrypted ✓")
        
        # Check can extract text
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        if not text.strip():
            result["warnings"].append("PDF may be image-only (no extractable text)")
        
        # Check required content markers
        required_markers = ["N650", "S558"]  # Document ID pattern
        for marker in required_markers:
            if marker in text:
                result["warnings"].append(f"Found marker: {marker} ✓")
        
        result["schema_valid"] = len(result["errors"]) == 0
        result["status"] = "INVALID" if result["errors"] else ("WARNING" if result["warnings"] else "VALID")
        
    except Exception as e:
        result["errors"].append(f"PDF read error: {e}")
        result["status"] = "ERROR"
    
    return result


def validate_json_schema(json_path: Path, schema: dict = None) -> SchemaValidationResult:
    """Validate JSON meets expected schema."""
    result = SchemaValidationResult(
        file_path=str(json_path),
        file_type="json",
        schema_valid=False,
        errors=[],
        warnings=[],
        status="ERROR"
    )
    
    try:
        with json_path.open() as f:
            data = json.load(f)
        
        # Basic schema checks for generation manifest
        if "status" in data:
            result["warnings"].append(f"Status: {data['status']} ✓")
        
        if "generated" in data:
            result["warnings"].append(f"Generated count: {len(data['generated'])} ✓")
        
        if "generated_at" in data:
            result["warnings"].append("Has timestamp ✓")
        
        if "run_id" in data:
            result["warnings"].append("Has run_id ✓")
        
        # Check for required fields in generated entries
        for entry in data.get("generated", []):
            required = ["employee_id", "path", "page_count", "sha256"]
            for field in required:
                if field not in entry:
                    result["errors"].append(f"Generated entry missing: {field}")
        
        result["schema_valid"] = len(result["errors"]) == 0
        result["status"] = "INVALID" if result["errors"] else ("WARNING" if result["warnings"] else "VALID")
        
    except json.JSONDecodeError as e:
        result["errors"].append(f"JSON parse error: {e}")
        result["status"] = "ERROR"
    except Exception as e:
        result["errors"].append(f"Error: {e}")
        result["status"] = "ERROR"
    
    return result


def validate_csv_schema(csv_path: Path, required_columns: list = None) -> SchemaValidationResult:
    """Validate CSV meets expected schema."""
    result = SchemaValidationResult(
        file_path=str(csv_path),
        file_type="csv",
        schema_valid=False,
        errors=[],
        warnings=[],
        status="ERROR"
    )
    
    if required_columns is None:
        # Default for verification_table.csv
        required_columns = [
            "employee_id", "status_profile", "identity",
            "institution", "certificate_source_status", "signatory_source_status"
        ]
    
    try:
        with csv_path.open() as f:
            reader = csv.DictReader(f)
            
            # Check required columns
            if not reader.fieldnames:
                result["errors"].append("No columns found")
            else:
                missing = [col for col in required_columns if col not in reader.fieldnames]
                if missing:
                    result["errors"].append(f"Missing columns: {missing}")
                else:
                    result["warnings"].append(f"All {len(required_columns)} required columns present ✓")
            
            # Check rows
            rows = list(reader)
            if rows:
                result["warnings"].append(f"Row count: {len(rows)} ✓")
            else:
                result["errors"].append("No data rows")
            
            result["schema_valid"] = len(result["errors"]) == 0
            result["status"] = "INVALID" if result["errors"] else ("WARNING" if result["warnings"] else "VALID")
        
    except Exception as e:
        result["errors"].append(f"Error: {e}")
        result["status"] = "ERROR"
    
    return result


def main():
    parser = argparse.ArgumentParser(description="Validate output schema")
    parser.add_argument("--file", type=Path, required=True, help="File to validate")
    parser.add_argument("--type", choices=["pdf", "json", "csv"], help="File type (auto-detect if not provided)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()
    
    if not args.file.exists():
        print(f"ERROR: File not found: {args.file}")
        sys.exit(1)
    
    # Auto-detect type
    if not args.type:
        suffix = args.file.suffix.lower()
        if suffix == ".pdf":
            args.type = "pdf"
        elif suffix == ".json":
            args.type = "json"
        elif suffix == ".csv":
            args.type = "csv"
        else:
            print(f"ERROR: Cannot auto-detect type for: {args.file}")
            sys.exit(1)
    
    # Validate
    if args.type == "pdf":
        result = validate_pdf_schema(args.file)
    elif args.type == "json":
        result = validate_json_schema(args.file)
    else:
        result = validate_csv_schema(args.file)
    
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"File: {result['file_path']}")
        print(f"Type: {result['file_type']}")
        print(f"Status: {result['status']}")
        
        if result['warnings']:
            print(f"\nWarnings:")
            for w in result['warnings']:
                print(f"  ✓ {w}")
        
        if result['errors']:
            print(f"\nErrors:")
            for e in result['errors']:
                print(f"  ✗ {e}")
    
    sys.exit(0 if result['status'] in ('VALID', 'WARNING') else 1)


if __name__ == "__main__":
    main()
