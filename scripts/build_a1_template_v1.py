#!/usr/bin/env python3
"""Build v1 blank A1 background + token template from the original example PDF."""
from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path
import pymupdf
ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / "output" / "A1 2025.pdf"
ORIGINAL_SHA256 = "12fe1d3ab12f93407858d1f4daca09ff84f8e7e37d08376a487e840073e34bac"
BG_OUT = ROOT / "templates" / "a1_background_v1.pdf"
TPL_OUT = ROOT / "templates" / "a1_template_v1.pdf"
FIELDS_OUT = ROOT / "templates" / "a1_template_v1_fields.json"
RECEIPT_OUT = ROOT / "config" / "a1_template_v1_receipt.json"
CHECKBOX_BORDERS = {
    0: [(pymupdf.Rect(459, 379, 469, 389), (0.0471, 0.431, 0.569)),
        pymupdf.Rect(83, 653, 91, 661)],
    1: [pymupdf.Rect(296, 236, 304, 244),
        pymupdf.Rect(296, 424, 304, 432)],
}
CHECKBOX_REDRAW = {
    0: [(pymupdf.Rect(459, 379, 469, 389), (0.0471, 0.431, 0.569), 0.72),
        (pymupdf.Rect(83, 653, 91, 661), (0, 0, 0), 0.72)],
    1: [(pymupdf.Rect(296, 236, 304, 244), (0, 0, 0), 0.72),
        (pymupdf.Rect(296, 424, 304, 432), (0.2, 0.2, 0.2), 0.72)],
}
TOKEN_MAP = {
    (0, 0): "person.insurance_number", (0, 1): "person.surname",
    (0, 2): "person.given_name", (0, 3): "person.maiden_name",
    (0, 4): "person.dob", (0, 5): "person.nationality",
    (0, 6): "person.birth_place", (0, 7): "residence.address",
    (0, 8): "residence.postal_code", (0, 9): "residence.city",
    (0, 10): "residence.country_code", (0, 11): "certificate.member_state",
    (0, 12): "certificate.start_date", (0, 13): "certificate.end_date",
    (0, 14): "document_id_p1",
    (1, 0): "employment.employer_id", (1, 1): "employment.employer_name",
    (1, 2): "employment.address", (1, 3): "employment.country_code",
    (1, 4): "employment.city", (1, 5): "employment.postal_code",
    (1, 6): "document_id_p2",
    (2, 0): "activity.address", (2, 1): "institution.name",
    (2, 2): "institution.address", (2, 3): "institution.city",
    (2, 4): "institution.postal_code", (2, 5): "institution.country_code",
    (2, 6): "institution.code", (2, 7): "institution.phone_fax",
    (2, 8): "institution.phone_tel", (2, 9): "institution.email",
    (2, 10): "institution.issue_date", (2, 11): "institution.signed_by",
    (2, 12): "document_id_p3",
}
STATIC_KEEP = ("Tento dokument byl vyd", "This document was issued")
def main() -> int:
    raw = ORIGINAL.read_bytes()
    if hashlib.sha256(raw).hexdigest() != ORIGINAL_SHA256:
        print("UNRECOGNIZED_TEMPLATE_VERSION", file=sys.stderr)
        return 1
    sys.path.insert(0, str(ROOT / "scripts"))
    from pdf_named_fields import placeholder_template
    import a1_core as core
    font = str(next(p for p in core.FONT_CANDIDATES if p.exists()))
    doc = pymupdf.open(stream=raw, filetype="pdf")
    redacted = []
    token_rects = {}
    for pno, page in enumerate(doc):
        idx = 0
        for b in page.get_text("dict")["blocks"]:
            if b.get("type", 0) != 0:
                continue
            for line in b["lines"]:
                for s in line["spans"]:
                    t = s["text"].strip()
                    if not t or s["font"] != "ArialMT" or t == "\u2022":
                        continue
                    if any(t.startswith(k) for k in STATIC_KEEP):
                        continue
                    r = pymupdf.Rect(s["bbox"])
                    # Tight ink box: glyph bbox includes descender padding that
                    # overlaps the raster ruled line below. Shrink vertically to
                    # cap-height core so the underline pixels survive.
                    ink = pymupdf.Rect(r.x0, r.y0 + (r.y1 - r.y0) * 0.12,
                                       r.x1, r.y1 - (r.y1 - r.y0) * 0.28)
                    redacted.append({"page": pno, "text": t,
                                     "rect": [round(v, 1) for v in r]})
                    page.add_redact_annot(ink, fill=(0.99, 0.99, 0.99))
                    if (pno, idx) in TOKEN_MAP:
                        token_rects[(pno, idx)] = list(r)
                    idx += 1
        for brect in CHECKBOX_BORDERS.get(pno, []):
            r = brect[0] if isinstance(brect, tuple) else brect
            page.add_redact_annot(pymupdf.Rect(r), fill=(1, 1, 1))
            redacted.append({"page": pno, "text": "CHECKBOX_X",
                             "rect": [round(v, 1) for v in r]})
        # borders redrawn after apply_redactions below
        page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_PIXELS,
                              graphics=pymupdf.PDF_REDACT_IMAGE_NONE)
        for brect, color, width in CHECKBOX_REDRAW.get(pno, []):
            shape = page.new_shape()
            shape.draw_rect(brect)
            shape.finish(color=color, width=width)
            shape.commit()
    blank = doc.tobytes(garbage=4, deflate=True)
    doc.close()
    check = pymupdf.open(stream=blank, filetype="pdf")
    leftover = []
    for pno, page in enumerate(check):
        for b in page.get_text("dict")["blocks"]:
            if b.get("type", 0) != 0:
                continue
            for line in b["lines"]:
                for s in line["spans"]:
                    t = s["text"].strip()
                    if (s["font"] == "ArialMT" and t and t != "\u2022"
                            and not any(t.startswith(k) for k in STATIC_KEEP)):
                        leftover.append((pno, t))
    check.close()
    if leftover:
        print(f"LEFTOVER_VARIABLE_SPANS: {leftover}", file=sys.stderr)
        return 1
    BG_OUT.write_bytes(blank)
    fields = []
    for (pno, idx), name in sorted(TOKEN_MAP.items()):
        if (pno, idx) not in token_rects:
            print(f"MISSING_RECT for {name}", file=sys.stderr)
            return 1
        r = token_rects[(pno, idx)]
        # Single line as in original: width extends to the row's right edge
        # (right margin ~540), never wraps into the row below.
        fields.append({"name": name, "source": name, "page": pno,
                       "origin": [round(r[0], 1), round(r[3] - 1.0, 1)],
                       "max_width": round(540.0 - r[0], 1),
                       "size": 9})
    FIELDS_OUT.write_text(json.dumps(fields, ensure_ascii=False, indent=2)
                          + "\n", encoding="utf-8")
    template = placeholder_template(blank, fields, font)
    TPL_OUT.write_bytes(template)
    receipt = {
        "original_sha256": ORIGINAL_SHA256,
        "background_v1_sha256": hashlib.sha256(blank).hexdigest(),
        "template_v1_sha256": hashlib.sha256(template).hexdigest(),
        "fields_v1_sha256": hashlib.sha256(FIELDS_OUT.read_bytes()).hexdigest(),
        "redacted_spans": redacted,
        "token_count": len(fields),
    }
    RECEIPT_OUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2)
                           + "\n", encoding="utf-8")
    for p in (BG_OUT, TPL_OUT, FIELDS_OUT, RECEIPT_OUT):
        p.chmod(0o600)
    print(f"OK background={BG_OUT.name} template={TPL_OUT.name} "
          f"fields={len(fields)} redacted={len(redacted)}")
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
