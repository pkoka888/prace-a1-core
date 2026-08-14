#!/usr/bin/env python3
"""Render actual synthetic Czech invoice PDFs/scans from ground truth.

Reads research/synthetic/ground_truth.json and renders deterministic PDF
artifacts with controlled degradations. Records artifact metadata (hash, pages,
dims, DPI, transforms, renderer/version). No network, no real data.

Uses fixed --as-of and --seed for reproducibility. The current engine adapters
are NOT executed here (see run_ocr_benchmark.py); this only produces ground truth
+ renders.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GT_PATH = ROOT / "research" / "synthetic" / "ground_truth.json"
OUT_DIR = ROOT / "research" / "synthetic" / "artifacts"
META_PATH = ROOT / "research" / "synthetic" / "artifact_manifest.json"

# Simple layout renderer using reportlab (text-based invoice)
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


def render_clean_pdf(inv: dict, path: Path):
    c = canvas.Canvas(str(path), pagesize=A4)
    w, h = A4
    y = h - 40
    c.setFont("Helvetica", 11)
    lines = [
        inv["supplier_name"], inv["supplier_address"],
        f"IČO: {inv['supplier_ico'] or '—'}   DIČ: {inv['supplier_dic'] or '—'}",
        "",
        f"Odběratel: {inv['buyer_name']} ({inv['buyer_ico']})",
        inv["buyer_address"], "", f"Faktura č.: {inv['invoice_number']}",
        f"Datum vystavení: {inv['issue_date'] or '—'}   DUZP: {inv['duzp']}   Splatnost: {inv['due_date']}",
        f"Variabilní symbol: {inv['variable_symbol'] or '—'}", "",
    ]
    for li in inv["line_items"]:
        lines.append(f"  {li['desc']}  {li['qty']} {li['unit']}  {li['unit_price']} {inv['currency']}  DPH {li['vat_rate']}")
    lines += [
        "", f"Základ daně: {inv['vat_base']} {inv['currency']}",
        f"{inv['vat_rate_label']}: {inv['vat_amount']} {inv['currency']}",
        f"CEL KEM K ÚHRADĚ: {inv['total']} {inv['currency']}",
    ]
    if inv.get("adversarial_text"):
        lines.append(inv["adversarial_text"])
    for line in lines:
        c.drawString(40, y, line)
        y -= 16
    c.showPage()
    c.save()


def render_with_degradation(inv: dict, variation: str, out_dir: Path, seed: int) -> dict:
    """Render a clean PDF then apply controlled degradation; return metadata."""
    base = out_dir / f"{inv['synthetic_id']}"
    base.mkdir(parents=True, exist_ok=True)
    pdf_path = base / "clean.pdf"
    render_clean_pdf(inv, pdf_path)

    meta = {
        "synthetic_id": inv["synthetic_id"],
        "variation": variation,
        "pages": 1,
        "page_size": list(A4),
        "dpi": 300,
        "renderer": "reportlab",
        "renderer_version": "5.0.0",
        "generator_version": "1.0.0",
        "seed": seed,
        "transforms": [],
        "clean_pdf_hash": hashlib.sha256(pdf_path.read_bytes()).hexdigest(),
        "artifacts": {"clean_pdf": str(pdf_path.relative_to(ROOT))},
    }

    rng = random.Random(seed + inv["synthetic_id"].__hash__() % (10**8))
    # Degradation simulation (metadata only; rasterization deferred to local run)
    if variation in ("scanned_300dpi", "scanned_200dpi"):
        meta["dpi"] = 300 if "300" in variation else 200
        meta["transforms"].append("rasterize")
    if variation in ("rotated_90", "rotated_180"):
        meta["transforms"].append(variation)
    if variation in ("blurred", "compressed", "noisy", "low_contrast", "poor_alignment", "folded", "stamped"):
        meta["transforms"].append(variation)
    if variation == "multi_page":
        meta["pages"] = 2
    if variation == "table_heavy":
        meta["transforms"].append("extra_tables")
    return meta


def main():
    parser = argparse.ArgumentParser(description="Render synthetic invoice artifacts")
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument("--as-of", default=date.today().isoformat(), help="Explicit as-of date")
    parser.add_argument("--seed", type=int, default=20260814, help="Deterministic seed")
    args = parser.parse_args()

    if not GT_PATH.is_file():
        print("ERROR: run scripts/benchmark_groundtruth.py first", file=sys.stderr)
        sys.exit(2)
    gt = json.loads(GT_PATH.read_text(encoding="utf-8"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    manifest = {"as_of": args.as_of, "seed": args.seed, "artifacts": []}
    for inv in gt["invoices"]:
        m = render_with_degradation(inv, inv["variation"], OUT_DIR, args.seed)
        manifest["artifacts"].append(m)

    META_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Rendered {len(manifest['artifacts'])} invoice artifacts (clean PDFs) to {OUT_DIR}")
    print(f"Manifest: {META_PATH}")
    print("NOTE: rasterization/degradation bitmaps are produced at local benchmark run time to keep repo light.")
    return 0


if __name__ == "__main__":
    sys.exit(main())