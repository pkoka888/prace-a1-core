#!/usr/bin/env python3
"""
A1 PDF Generator - Placeholder Framework

Generates A1 PDFs using placeholder search/replace approach.
Template has {{field_name}} tokens that are replaced with actual values.
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import csv
from scripts.pdf_named_fields import replace_placeholders
from scripts.a1_core import FONT_CANDIDATES, build_form_data
from scripts.finalize_a1 import row_to_form, display_row
import pymupdf


def extract_field_positions(template_pdf: bytes) -> list[dict]:
    """Extract placeholder positions from template."""
    doc = pymupdf.open(stream=template_pdf, filetype='pdf')
    fields = []
    
    for page_num, page in enumerate(doc):
        text = page.get_text()
        for line in text.split('\n'):
            line = line.strip()
            if line.startswith('{{') and line.endswith('}}'):
                field_name = line[2:-2]
                hits = page.search_for(line)
                if hits:
                    rect = hits[0]
                    fields.append({
                        "name": field_name,
                        "source": field_name,
                        "page": page_num,
                        "origin": [rect.x0, rect.y0],
                        "max_width": 350,  # Increased for long institution names
                        "size": 9
                    })
    doc.close()
    return fields


def flatten_form_data(form: dict) -> dict:
    """Flatten nested form data to placeholder values."""
    values = {}
    
    # Person
    person = form.get("person", {})
    values["person.insurance_number"] = person.get("insurance_number", "")
    values["person.surname"] = person.get("surname", "")
    values["person.given_name"] = person.get("given_name", "")
    values["person.maiden_name"] = person.get("maiden_name", "")
    values["person.dob"] = person.get("dob", "")
    values["person.nationality"] = person.get("nationality", "")
    values["person.birth_place"] = person.get("birth_place", "")
    
    # Residence
    residence = form.get("residence", {})
    address = residence.get("street", "")
    if residence.get("house_number"):
        address += " " + residence["house_number"]
    values["residence.address"] = address
    values["residence.city"] = residence.get("city", "")
    values["residence.postal_code"] = residence.get("postal_code", "")
    values["residence.country_code"] = residence.get("country_code", "")
    
    # Certificate - document_id is used for all pages
    cert = form.get("certificate", {})
    doc_id = cert.get("document_id", "")
    values["certificate.member_state"] = cert.get("member_state", "")
    values["certificate.start_date"] = cert.get("start_date", "")
    values["certificate.end_date"] = cert.get("end_date", "")
    values["document_id_p1"] = doc_id
    values["document_id_p2"] = doc_id
    values["document_id_p3"] = doc_id
    
    # Employment
    emp = form.get("employment", {})
    values["employment.employer_id"] = emp.get("employer_id", "")
    values["employment.employer_name"] = emp.get("employer_name", "")
    emp_addr = emp.get("street", "")
    if emp.get("house_number"):
        emp_addr += " " + emp["house_number"]
    values["employment.address"] = emp_addr
    values["employment.country_code"] = emp.get("country_code", "")
    values["employment.city"] = emp.get("city", "")
    values["employment.postal_code"] = emp.get("postal_code", "")
    
    # Activity
    act = form.get("activity", {})
    values["activity.name"] = act.get("name", "")
    values["activity.address"] = act.get("address", "")
    
    # Institution
    inst = form.get("institution", {})
    values["institution.name"] = inst.get("name", "")
    inst_addr = inst.get("street", "")
    if inst.get("house_number"):
        inst_addr += " " + inst["house_number"]
    values["institution.address"] = inst_addr
    values["institution.city"] = inst.get("city", "")
    values["institution.postal_code"] = inst.get("postal_code", "")
    values["institution.country_code"] = inst.get("country_code", "")
    values["institution.code"] = inst.get("code", "")
    values["institution.issue_date"] = inst.get("issue_date", "")
    values["institution.signed_by"] = inst.get("signed_by", "")
    
    return values


def generate_a1_placeholder(
    review_csv: Path,
    profile_json: Path,
    output_pdf: Path,
    template_pdf: Path = None,
) -> Path:
    """Generate A1 PDF using placeholder framework."""
    # Defaults
    if template_pdf is None:
        template_pdf = Path(__file__).parent.parent / "templates" / "a1_template.pdf"
    
    # Load data
    profile = json.loads(profile_json.read_text(encoding="utf-8"))
    
    with open(review_csv, encoding="utf-8") as f:
        row = next(csv.DictReader(f))
    
    # Build form - row_to_form returns processed form data
    displayed = display_row(row)
    form = row_to_form(displayed, profile)
    
    # Get font
    font = str(next(p for p in FONT_CANDIDATES if p.exists()))
    
    # Load template and extract positions
    template_bytes = template_pdf.read_bytes()
    fields = extract_field_positions(template_bytes)
    
    # Flatten form data
    values = flatten_form_data(form)
    
    # Replace placeholders
    result = replace_placeholders(template_bytes, fields, values, font)
    
    # Save
    output_pdf.write_bytes(result)
    return output_pdf


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate A1 PDF using placeholder framework")
    parser.add_argument("--review", required=True, help="Review CSV file")
    parser.add_argument("--profile", required=True, help="Institution profile JSON")
    parser.add_argument("--output", required=True, help="Output PDF path")
    parser.add_argument("--template", help="Template PDF (optional)")
    
    args = parser.parse_args()
    
    output = generate_a1_placeholder(
        Path(args.review),
        Path(args.profile),
        Path(args.output),
        Path(args.template) if args.template else None,
    )
    
    print(f"Generated: {output}")
