#!/usr/bin/env python3
"""Extract exact checkbox positions from the original A1 2025.pdf template.

Reads vector rects (checkbox outlines) and line drawings (X marks) using PyMuPDF,
converts from PDF display-coordinate system (top-left origin) to ReportLab
bottom-left origin for use in config/a1_layout.json, and outputs a JSON
structure compatible with the layout checker and generator.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_TEMPLATE = ROOT / "output" / "A1 2025.pdf"
PAGE_SIZE = (595.2, 841.92)

# Map known checkbox rect positions to their semantic names.
# These are determined by locating each checkbox rect near its text label
# in the original A1 2025.pdf using get_text("words").
CHECKBOX_MAP = {
    "gender_female": "Žena",
    "gender_male": "Muž",
    "valid_duration": "Osvědčení",
    "status_posted_employee": "3.1",
    "status_employee_multistate": "3.2",
    "status_posted_self_employed": "3.3",
    "status_osv_c_multistate": "3.4",
    "employer_type_employee": "4.1.1",
    "employer_type_self_employed": "4.1.2",
    "no_fixed_address": "5.3",
}


def extract_positions(template_path: Path = ORIGINAL_TEMPLATE) -> dict:
    doc = pymupdf.open(str(template_path))
    result = {
        "source_sha256": None,
        "page_count": len(doc),
        "page_size": {"width": PAGE_SIZE[0], "height": PAGE_SIZE[1]},
        "coordinate_system": "ReportLab bottom-left points on 595.2 x 841.92",
        "checkboxes": {},
    }
    result["source_sha256"] = (
        __import__("hashlib").sha256(template_path.read_bytes()).hexdigest()
    )

    for page_index, page in enumerate(doc):
        # Collect small rects (checkbox outlines) from vector drawings
        rects = []
        drawings = page.get_drawings()
        for d in drawings:
            for item in d.get("items", []):
                if item[0] == "re":
                    rect = item[1]
                    if 3 < rect.width < 15 and 3 < rect.height < 15:
                        rects.append(
                            {
                                "x0": rect.x0,
                                "y0": rect.y0,
                                "x1": rect.x1,
                                "y1": rect.y1,
                                "width": rect.width,
                                "height": rect.height,
                            }
                        )

        # Collect line drawings (X marks)
        x_lines = []
        for d in drawings:
            for item in d.get("items", []):
                if item[0] == "l":
                    pt1, pt2 = item[1], item[2]
                    dx = abs(pt2.x - pt1.x)
                    dy = abs(pt2.y - pt1.y)
                    if 5 < dx < 20 and 5 < dy < 20:
                        x_lines.append(
                            {
                                "x1": pt1.x,
                                "y1": pt1.y,
                                "x2": pt2.x,
                                "y2": pt2.y,
                            }
                        )

        # Collect text words to match labels to rects
        words = page.get_text("words")

        # Match each checkbox rect to a label text
        for name, label_text in CHECKBOX_MAP.items():
            for word in words:
                w_text, w_x0, w_y0, _w_x1, _w_y1 = (
                    word[4],
                    word[0],
                    word[1],
                    word[2],
                    word[3],
                )
                if w_text.strip() == label_text:
                    # Find the rect closest to this label
                    best_rect = None
                    best_dist = float("inf")
                    for r in rects:
                        # Distance from label's top-left to rect's top-right corner
                        dx = abs(r["x1"] - w_x0)
                        dy = abs(r["y0"] - w_y0)
                        dist = (dx**2 + dy**2) ** 0.5
                        if dist < best_dist:
                            best_dist = dist
                            best_rect = r

                    if best_rect and best_dist < 50:
                        # Convert from display (top-left) to ReportLab (bottom-left)
                        y_bl = PAGE_SIZE[1] - best_rect["y0"] - best_rect["height"]
                        result["checkboxes"][name] = {
                            "page": page_index + 1,
                            "x": round(best_rect["x0"], 2),
                            "y": round(y_bl, 2),
                            "size": round(best_rect["height"], 2),
                        }
                        break

    doc.close()
    return result


def main():
    output_path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if output_path is None:
        output_path = ROOT / "config" / "checkbox_reference.json"
    positions = extract_positions()
    output_path.write_text(json.dumps(positions, indent=2) + "\n", encoding="utf-8")
    print(
        f"Extracted {len(positions['checkboxes'])} checkbox positions to {output_path}"
    )
    print(f"Source SHA256: {positions['source_sha256']}")
    for name, cfg in positions["checkboxes"].items():
        print(
            f"  {name}: page={cfg['page']}, x={cfg['x']}, y={cfg['y']}, size={cfg['size']}"
        )


if __name__ == "__main__":
    main()
