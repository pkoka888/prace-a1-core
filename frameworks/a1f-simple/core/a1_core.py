#!/usr/bin/env python3
"""A1 PDF placeholder replacement engine for a1f-simple framework.

MISSION: Replace placeholders in templates/a1_template_v1.pdf ONLY.
NO STYLING, NO WATERMARKS, NO POSITIONING CHANGES.

This is the framework core - self-contained, no parent imports.
"""

from __future__ import annotations

import io
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import pymupdf

CORE_ROOT = Path(__file__).resolve().parent
FRAMEWORK_ROOT = CORE_ROOT.parent
TEMPLATES_DIR = FRAMEWORK_ROOT / "templates"
TEMPLATE_PATH = TEMPLATES_DIR / "a1_template_v1.pdf"


class A1ValidationError(ValueError):
    """Raised when unreviewed or incomplete data would enter a final A1."""


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def normalize_date(value: str | None) -> str:
    if not value:
        return ""
    value = value.strip().replace("/", ".").replace("-", ".")
    match = re.fullmatch(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", value)
    if not match:
        raise A1ValidationError(f"Unsupported date format: {value!r}")
    day, month, year = (int(part) for part in match.groups())
    try:
        datetime(year, month, day)
    except ValueError:
        raise A1ValidationError(f"Invalid date: {value!r}") from None
    return f"{day:02d}.{month:02d}.{year:04d}"


def validate_form_data(form: dict[str, Any]) -> None:
    required = {
        "person": (
            "insurance_number",
            "surname",
            "given_name",
            "dob",
            "birth_place",
            "nationality",
            "sex",
        ),
        "residence": ("street", "house_number", "city", "postal_code", "country_code"),
        "certificate": ("member_state", "start_date", "end_date", "document_id"),
    }
    missing = [
        f"{section}.{field}"
        for section, fields in required.items()
        for field in fields
        if not form.get(section, {}).get(field)
    ]
    if missing:
        raise A1ValidationError("Missing required A1 fields: " + ", ".join(sorted(missing)))


def display_value(source: str, value: str) -> str:
    if not value:
        return ""
    key = value.casefold()
    if key in {"ceska republika", "czech republic", "cz", "cze"}:
        return "CZ"
    return value




def flatten_form_data(form: dict[str, Any]) -> dict[str, str]:
    """Flatten the nested form into flat keys matching template tokens."""
    values: dict[str, str] = {}
    person = form.get("person", {})
    values["person.insurance_number"] = person.get("insurance_number", "")
    values["person.surname"] = person.get("surname", "")
    values["person.given_name"] = person.get("given_name", "")
    values["person.maiden_name"] = person.get("maiden_name", "")
    values["person.dob"] = person.get("dob", "")
    values["person.nationality"] = display_value("person.nationality", person.get("nationality", ""))
    values["person.birth_place"] = person.get("birth_place", "")

    residence = form.get("residence", {})
    address = residence.get("street", "")
    if residence.get("house_number"):
        address = f"{address} {residence['house_number']}".strip()
    values["residence.address"] = address
    values["residence.city"] = residence.get("city", "")
    values["residence.postal_code"] = residence.get("postal_code", "")
    values["residence.country_code"] = display_value("residence.country_code", residence.get("country_code", ""))

    cert = form.get("certificate", {})
    values["certificate.member_state"] = display_value("certificate.member_state", cert.get("member_state", ""))
    values["certificate.start_date"] = cert.get("start_date", "")
    values["certificate.end_date"] = cert.get("end_date", "")
    values["certificate.document_id"] = cert.get("document_id", "")

    emp = form.get("employment", {})
    values["employment.employer_id"] = emp.get("employer_id", "")
    values["employment.employer_name"] = emp.get("employer_name", "")
    emp_addr = emp.get("street", "")
    if emp.get("house_number"):
        emp_addr = f"{emp_addr} {emp['house_number']}".strip()
    values["employment.address"] = emp_addr
    values["employment.country_code"] = display_value("employment.country_code", emp.get("country_code", ""))
    values["employment.city"] = emp.get("city", "")
    values["employment.postal_code"] = emp.get("postal_code", "")

    inst = form.get("institution", {})
    inst_addr = inst.get("street", "")
    if inst.get("house_number"):
        inst_addr = f"{inst_addr} {inst['house_number']}".strip()
    values["institution.name"] = inst.get("name", "")
    values["institution.address"] = inst_addr
    values["institution.city"] = inst.get("city", "")
    values["institution.postal_code"] = inst.get("postal_code", "")
    values["institution.country_code"] = inst.get("country_code", "")
    values["institution.code"] = inst.get("code", "")
    values["institution.issue_date"] = inst.get("issue_date", "")
    values["institution.signed_by"] = inst.get("signed_by", "")
    values["institution.email"] = inst.get("email", "")
    values["institution.phone_fax"] = inst.get("phone_fax", "")
    values["institution.phone_tel"] = inst.get("phone_tel", "")
    
    return values


def _tokens_for(field: str, value: str) -> dict[str, str]:
    if field == "certificate.document_id":
        return {
            "{{document_id_p1}}": value,
            "{{document_id_p2}}": value,
            "{{document_id_p3}}": value,
        }
    return {f"{{{{{field}}}}}": value}


def _ensure_dejavu(page) -> None:
    pass


def _replace_text_spans(
    page, replacements: dict[str, str], *, erase_empty: bool = False
) -> int:
    replaced = 0
    stamps: list[tuple[pymupdf.Rect, str, float]] = []
    for block in page.get_text("dict")["blocks"]:
        if block.get("type", 0) != 0:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                token = span["text"].strip()
                if not token.startswith("{{") or not token.endswith("}}"):
                    continue
                value = replacements.get(token)
                if value is None:
                    if not erase_empty:
                        continue
                    value = ""
                rect = pymupdf.Rect(span["bbox"])
                page.add_redact_annot(rect, fill=(1, 1, 1))
                stamps.append((rect, value, span.get("size", 9.0)))
                replaced += 1
    page.apply_redactions(
        images=pymupdf.PDF_REDACT_IMAGE_NONE,
        graphics=pymupdf.PDF_REDACT_IMAGE_NONE,
    )
    for rect, value, size in stamps:
        page.insert_text(
            (rect.x0, rect.y1 - 2.0),
            value,
            fontsize=size,
            fill=(0, 0, 0),
            overlay=True,
        )
    return replaced


def _stamp_check_x(page, x: float, y: float, size: float) -> None:
    """Stamp X mark for checkbox - the ONLY allowed modification beyond placeholder replacement."""
    inset = 1.0
    top = page.rect.height - y
    shape = page.new_shape()
    shape.draw_line(
        (x + inset, top - size + inset), (x + size - inset, top - inset)
    )
    shape.draw_line(
        (x + size - inset, top - size + inset), (x + inset, top - inset)
    )
    shape.finish(color=(0.05, 0.35, 0.48), width=0.8)
    shape.commit()


def _stamp_checkboxes_for_page(page, layout: dict[str, Any], form: dict[str, Any]) -> None:
    """Toggle checkbox states ONLY - do NOT reposition or redraw checkboxes."""
    page_number = page.number
    for field, cfg in layout.get("checkboxes", {}).items():
        if int(cfg.get("page", -1)) != page_number:
            continue
        if not form.get(field):
            continue
        x = float(cfg["x"])
        y = float(cfg["y"])
        size = float(cfg.get("size", 7.4))
        _stamp_check_x(page, x, y, size)


def generate_a1_pdf(
    form: dict[str, Any],
    output_pdf: str | Path,
    *,
    layout_json: str | Path | None = None,
    erase_empty: bool = False,
) -> Path:
    """Generate PDF by replacing placeholders only.

    RULES FOR THIS FRAMEWORK:
    - Uses ONLY templates/a1_template_v1.pdf
    - Replaces {{placeholder}} tokens with worker values
    - Toggled checkboxes if specified (no repositioning)
    - NO notices/watermarks/styling
    """
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"Template not found: {TEMPLATE_PATH}")

    layout = None
    if layout_json:
        layout = load_json(layout_json)

    doc = pymupdf.open(TEMPLATE_PATH)
    _ensure_dejavu(doc)
    values = flatten_form_data(form)
    replacements = {}
    for field, value in values.items():
        if not value:
            continue
        replacements.update(_tokens_for(field, value))

    for page in doc:
        _replace_text_spans(page, replacements, erase_empty=erase_empty)
        if layout:
            _stamp_checkboxes_for_page(page, layout, form)

    buffer = io.BytesIO()
    doc.save(buffer, garbage=4, deflate=True, no_new_id=1)
    doc.close()
    
    output = Path(output_pdf)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(buffer.getvalue())
    output.chmod(0o600)
    return output
