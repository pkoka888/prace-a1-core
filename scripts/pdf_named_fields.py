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
        if not re.fullmatch(r"[a-z][a-z0-9_.]*", field["name"]):
            raise ValueError("INVALID_FIELD_NAME")
        key = (field["page"], field["name"])
        if key in seen:
            raise ValueError("DUPLICATE_FIELD_BINDING")
        seen.add(key)
        if field["max_width"] <= 0:
            raise ValueError("INVALID_FIELD_WIDTH")


CHECKBOX_X_MARKS = {
    # page: {token: (rect top-left coords, border rgb, width)}
    # geometry measured from output/A1 2025.pdf drawings; X inset 1.2 inside.
    "gender_female": {"page": 0, "rect": [402, 379, 412, 389], "color": (0.047, 0.427, 0.569)},
    "gender_male": {"page": 0, "rect": [459, 379, 469, 389], "color": (0.047, 0.427, 0.569)},
    "valid_duration": {"page": 0, "rect": [83, 653, 91, 661], "color": (0, 0, 0)},
    "no_fixed_address": {"page": 2, "rect": [76, 425, 84, 433], "color": (0, 0, 0)},
}
SECTION3_BOXES = {
    "3.1": [76, 220, 84, 227], "3.2": [296, 220, 304, 227],
    "3.3": [76, 236, 84, 244], "3.4": [296, 236, 304, 244],
    "3.5": [76, 263, 84, 271], "3.6": [296, 263, 304, 271],
    "3.7": [76, 280, 84, 287], "3.8": [296, 280, 304, 287],
    "3.9": [76, 307, 84, 314], "3.10": [296, 307, 304, 314],
    "3.11": [76, 343, 84, 351], "3.12": [296, 343, 304, 351],
}
SECTION4_BOXES = {
    "4.1.1": [76, 424, 84, 432], "4.1.2": [296, 424, 304, 432],
}


def draw_checkbox_x(page, rect, color, width=0.8, inset=1.2) -> None:
    """Draw X inside empty box; default unchecked, caller selects per worker."""
    x0, y0, x1, y1 = rect
    shape = page.new_shape()
    shape.draw_line(pymupdf.Point(x0 + inset, y0 + inset),
                    pymupdf.Point(x1 - inset, y1 - inset))
    shape.draw_line(pymupdf.Point(x1 - inset, y0 + inset),
                    pymupdf.Point(x0 + inset, y1 - inset))
    shape.finish(color=color, width=width)
    shape.commit()


WRAP_FIELDS = frozenset({"institution.name", "employment.employer_name",
                         "activity.address", "residence.address",
                         "employment.address", "institution.address"})


def _wrap_lines(font, value: str, size: float, max_width: float) -> list[str] | None:
    """Greedy word-wrap; None when a single word exceeds max_width."""
    words = value.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if font.text_length(candidate, fontsize=size) <= max_width:
            current = candidate
        else:
            if not current:
                return None
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _insert(page, field: Mapping, value: str, font_path: str, *, placeholder=False) -> None:
    font = pymupdf.Font(fontfile=font_path)
    size = float(field.get("size", 9))
    minimum = 3 if placeholder else 6
    lines = [value]
    while font.text_length(value, fontsize=size) > field["max_width"] and size > minimum:
        size = max(minimum, size - 0.25)
    if font.text_length(value, fontsize=size) > field["max_width"]:
        raise ValueError("FIELD_OVERFLOW")
    page.insert_font(fontname="NamedFieldSans", fontfile=font_path)
    x, y = field["origin"]
    for index, line in enumerate(lines):
        page.insert_text((x, y + index * size * 1.25), line, fontname="NamedFieldSans",
                         fontsize=size, color=(0, 0, 0))


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
            actual = re.findall(r"\{\{([a-z][a-z0-9_.]*)\}\}", page.get_text())
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
