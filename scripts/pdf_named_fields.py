"""Named PDF fields for local template experiments; no employee release entry point.

The caller owns storage, source authorization and publication gates. PDF text is
replaced through located spans, never by modifying compressed bytes or guessing
which person's text to replace. Layout uses top-left PDF points.
"""
from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping, Sequence

import pymupdf

PERSON_NAME_FIELDS = frozenset({"person.surname", "person.given_name", "person.maiden_name"})


def display_value(source: str, value: str) -> str:
    """Format personal names for display without changing OCR evidence or codes."""
    if source in PERSON_NAME_FIELDS:
        return unicodedata.normalize("NFC", " ".join(value.split())).title()
    return value


def _check_fields(fields: Sequence[Mapping]) -> None:
    seen = set()
    for field in fields:
        if not re.fullmatch(r"[a-z][a-z0-9_]*", field["name"]):
            raise ValueError("INVALID_FIELD_NAME")
        key = (field["page"], field["name"])
        if key in seen:
            raise ValueError("DUPLICATE_FIELD_BINDING")
        seen.add(key)
        if field["max_width"] <= 0:
            raise ValueError("INVALID_FIELD_WIDTH")


def _insert(page, field: Mapping, value: str, font_path: str, *, placeholder=False) -> None:
    font = pymupdf.Font(fontfile=font_path)
    size = float(field.get("size", 9))
    minimum = 3 if placeholder else 6
    while font.text_length(value, fontsize=size) > field["max_width"] and size > minimum:
        size = max(minimum, size - 0.25)
    if font.text_length(value, fontsize=size) > field["max_width"]:
        raise ValueError("FIELD_OVERFLOW")
    page.insert_font(fontname="NamedFieldSans", fontfile=font_path)
    page.insert_text(field["origin"], value, fontname="NamedFieldSans", fontsize=size,
                     color=(0.2, 0.2, 0.2))


def placeholder_template(blank_pdf: bytes, fields: Sequence[Mapping], font_path: str) -> bytes:
    """Insert searchable {{surname}}-style tokens into an already cleaned PDF."""
    _check_fields(fields)
    with pymupdf.open(stream=blank_pdf, filetype="pdf") as document:
        for field in fields:
            token = "{{" + field["name"] + "}}"
            _insert(document[field["page"]], field, token, font_path, placeholder=True)
        return document.tobytes(garbage=4, deflate=True)


def replace_placeholders(template_pdf: bytes, fields: Sequence[Mapping], values: Mapping[str, str],
                         font_path: str) -> bytes:
    """Replace every declared token, including repeated IDs; reject missing/extra tokens.

    Explicit empty values are allowed for a template experiment. Acceptance of
    required business facts belongs to the canonical A1 validation pipeline.
    """
    _check_fields(fields)
    if any(field["source"] not in values for field in fields):
        raise ValueError("MISSING_FIELD_VALUE")
    with pymupdf.open(stream=template_pdf, filetype="pdf") as document:
        for page_number, page in enumerate(document):
            expected = [f for f in fields if f["page"] == page_number]
            actual = re.findall(r"\{\{([a-z][a-z0-9_]*)\}\}", page.get_text())
            if sorted(actual) != sorted(f["name"] for f in expected):
                raise ValueError("PLACEHOLDER_CONTRACT_MISMATCH")
            for field in expected:
                hits = page.search_for("{{" + field["name"] + "}}")
                if len(hits) != 1:
                    raise ValueError("AMBIGUOUS_PLACEHOLDER")
                rect = hits[0]
                # Keep redaction inside the token's glyph box to avoid touching
                # an adjacent static label with an almost shared boundary.
                rect = pymupdf.Rect(rect.x0 + .02, rect.y0 + .2, rect.x1 - .02, rect.y1 - .2)
                page.add_redact_annot(rect, fill=False)
            if expected:
                page.apply_redactions(images=0, graphics=0)
            for field in expected:
                value = display_value(field["source"], values[field["source"]])
                if "{{" in value or "}}" in value:
                    raise ValueError("RESERVED_PLACEHOLDER_TEXT")
                if value:
                    _insert(page, field, value, font_path)
        if any("{{" in p.get_text() or "}}" in p.get_text() for p in document):
            raise ValueError("UNRESOLVED_PLACEHOLDER")
        return document.tobytes(garbage=4, deflate=True)
