#!/usr/bin/env python3
"""Compare two A1 renderer versions page by page, pixel by pixel.

The acceptance receipt in ``config/a1_checkbox_fix_receipt.json`` pins the
exact renderer that was reviewed, and each regression block records a pixel
comparison against the renderer before it. That comparison has to be
reproducible, otherwise the receipt is a claim rather than evidence.

This script renders the same synthetic inputs with two versions of
``scripts/a1_core.py`` and reports the changed pixels per page. It is
read-only with respect to the repository: it writes nothing outside the
directory it is given, and it reads no private data.

Usage::

    venv/bin/python scripts/compare_a1_renderer.py \
        --previous /path/to/previous/a1_core.py \
        --out /tmp/comparison.json
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
# The renderer falls back to a flat import of its sibling modules, so the
# scripts directory has to be importable however this script is invoked.
sys.path.insert(0, str(ROOT / "scripts"))

from scripts.a1_core import A1_STATUS_PROFILES  # noqa: E402
from scripts.finalize_a1 import row_to_form  # noqa: E402

DPI = 110
PAGE_COUNT = 3

# The profiles are read from the shared constant, so a profile added later is
# compared automatically rather than silently left out of the evidence.
SYNTHETIC_PROFILES = A1_STATUS_PROFILES


def _load_renderer(path: Path, name: str):
    """Import a specific a1_core.py under a private module name."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _synthetic_row(profile: str) -> dict:
    return {
        "employee_id": f"synthetic-{profile}",
        "surname": "TESTOVÁ",
        "given_name": "ALENA",
        "dob": "01.01.1990",
        "birth_place": "TESTOV",
        "nationality": "CZ",
        "sex": "F",
        "insurance_number": "9001010007",
        "street": "TESTOVACÍ",
        "house_number": "1",
        "city": "TEPLICE",
        "district": "TEPLICE",
        "postal_code": "415 01",
        "country_code": "CZ",
        "status_profile": profile,
        "document_id": f"SYNTHETIC-{profile}",
        "start_date": "01.01.2026",
        "end_date": "31.12.2026",
        "issue_date": "01.02.2026",
        "signed_by": "SYNTETICKÝ PODPIS",
        "employment_id": "SYNTHETIC-001",
        "employment_name": "Synthetic Engineering s.r.o.",
        "employment_street": "SYNTHETICKÁ",
        "employment_house_number": "2",
        "employment_city": "TEPLICE",
        "employment_postal_code": "415 01",
        "employment_country_code": "CZ",
        "activity_name": "SYNTHETIC ACTIVITY",
        "activity_address": "DE, CZ",
        "resolved_ossz": "SYNTHETICKA",
        "institution_profile": "teplice",
    }


def _synthetic_profile() -> dict:
    return {
        "institution": {
            "code": "558",
            "name": "SYNTHETICKÁ INSTITUCE",
            "street": "SYNTHETICKÁ",
            "house_number": "1",
            "city": "TEPLICE",
            "postal_code": "415 01",
            "country_code": "CZ",
        },
        "source_url": "https://example.invalid/synthetic",
        "verified_on": "2026-01-01",
        "office_contact": {},
    }


def _render(renderer, profile: str, out_dir: Path) -> Path:
    row = _synthetic_row(profile)
    form = row_to_form(row, _synthetic_profile())
    target = out_dir / f"{profile}.pdf"
    renderer.generate_a1_pdf(
        form,
        ROOT / "templates/a1_background.pdf",
        ROOT / "config/a1_layout.json",
        target,
    )
    return target


def _changed_pixels(left: Path, right: Path) -> list[int]:
    with pymupdf.open(left) as a, pymupdf.open(right) as b:
        counts = []
        for index in range(min(len(a), len(b))):
            pa = a[index].get_pixmap(dpi=DPI)
            pb = b[index].get_pixmap(dpi=DPI)
            if (pa.width, pa.height) != (pb.width, pb.height):
                counts.append(-1)
                continue
            counts.append(sum(1 for x, y in zip(pa.samples, pb.samples) if x != y))
        return counts


def compare(previous: Path, current: Path) -> dict:
    previous_module = _load_renderer(previous, "a1_core_previous")
    current_module = _load_renderer(current, "a1_core_current")
    comparisons = []
    with tempfile.TemporaryDirectory(prefix="a1-renderer-") as temporary:
        root = Path(temporary)
        for profile in SYNTHETIC_PROFILES:
            left = _render(previous_module, profile, root / "previous")
            right = _render(current_module, profile, root / "current")
            changed = _changed_pixels(left, right)
            comparisons.append(
                {
                    "profile": profile,
                    "pages": len(changed),
                    "dpi": DPI,
                    "changed_pixels": changed,
                }
            )
    return {
        "previous_renderer_sha256": _sha256(previous),
        "current_renderer_sha256": _sha256(current),
        "comparisons": comparisons,
        "identical": all(
            not any(c["changed_pixels"]) for c in comparisons
        ),
    }


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--previous", required=True, type=Path)
    parser.add_argument("--current", type=Path, default=ROOT / "scripts/a1_core.py")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    if not args.previous.is_file():
        print(f"previous renderer not found: {args.previous}", file=sys.stderr)
        return 2
    result = compare(args.previous, args.current)
    payload = json.dumps(result, indent=2)
    if args.out:
        args.out.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0 if result["identical"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
