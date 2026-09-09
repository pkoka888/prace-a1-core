#!/usr/bin/env python3
"""Execute a fixed synthetic corpus only; no document/manifest path input.

Run under an offline network namespace and an outer timeout. Results are smoke
measurements, never document accuracy certification or invoice benchmark PASS.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
from importlib.metadata import version
import json
import os
from pathlib import Path
import resource
import re
import subprocess
import sys
import time
import unicodedata
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
CANDIDATES = ["rapidocr", "tesseract", "docling", "paddleocr", "invoice2data", "ocrmypdf_tesseract"]


def fixed_cases():
    from PIL import Image, ImageDraw, ImageFont
    from document_core.images import decode_pages, png_bytes
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
    values = {
        "czech": ["SYNTHETIC TEST ONLY", "Příjmení: Zkušební", "Datum: 15.03.1990", "Doklad: TEST123456"],
        "german": ["SYNTHETIC TEST ONLY", "Straße: Prüfstraße", "Geburt: 15.03.1990", "Nummer: TEST654321"],
        "mixed": ["SYNTHETIC TEST ONLY", "Příjmení: Zkušební", "Straße: Prüfstraße", "Platnost: 31.12.2099"],
    }
    for name in ("czech", "german", "mixed", "skew", "pdf_raster"):
        lines = values.get(name, values["mixed"])
        image = Image.new("RGB", (1100, 360), "white")
        draw = ImageDraw.Draw(image)
        for index, line in enumerate(lines):
            draw.text((40, 30+index*70), line, fill="black", font=font)
        if name == "skew":
            image = image.rotate(3, expand=True, fillcolor="white")
        if name == "pdf_raster":
            import pymupdf
            with pymupdf.open() as pdf:
                page = pdf.new_page(width=image.width/2, height=image.height/2)
                page.insert_image(page.rect, stream=png_bytes(image))
                source = pdf.tobytes(no_new_id=True)
            image = decode_pages(source)[0].image
        else:
            source = png_bytes(image)
        yield name, png_bytes(image), lines, sha256(source).hexdigest()


def normalized(text):
    return " ".join(unicodedata.normalize("NFC", text).split())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", required=True, choices=("rapidocr", "tesseract"))
    args = parser.parse_args()
    os.umask(0o077)
    out = ROOT / "runtime" / "portal" / ("infra-ocr-"+str(uuid4()))
    out.mkdir(parents=True, exist_ok=False)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    started = time.monotonic()
    if args.engine == "rapidocr":
        import rapidocr
        from document_core.adapters.rapidocr import RapidOCRAdapter
        adapter = RapidOCRAdapter()
        base = Path(rapidocr.__file__).parent / "models"
        model_names = ("PP-OCRv6_det_small.onnx", "PP-OCRv6_rec_small.onnx", "ch_ppocr_mobile_v2.0_cls_mobile.onnx")
    else:
        from document_core.adapters.tesseract import TesseractAdapter
        adapter = TesseractAdapter()
        base = Path("/usr/share/tesseract-ocr/5/tessdata")
        model_names = ("ces.traineddata", "deu.traineddata", "eng.traineddata")
    initialization = time.monotonic()-started
    cases = []
    for name, content, expected, source_hash in fixed_cases():
        started = time.monotonic()
        result = adapter.process(content)
        observed = normalized(" ".join(result.txts))
        # Complete labeled synthetic fields must occur exactly, retaining case and accents.
        fields = [{"expected": field, "exact": bool(re.search(r"(?<!\w)"+re.escape(normalized(field))+r"(?!\w)", observed))} for field in expected[1:]]
        cases.append({"case": name, "source_sha256": source_hash, "raster_sha256": sha256(content).hexdigest(),
                      "seconds": time.monotonic()-started, "engine_elapse_ms": result.elapse_ms,
                      "engine_version": result.engine_version, "fields": fields,
                      "field_errors": sum(not f["exact"] for f in fields), "synthetic_observed": observed,
                      "review_required": True})
    manifest = {
        "status": "EXECUTED", "quality_acceptance": "NOT_ESTABLISHED", "synthetic_only": True,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(), "engine": args.engine,
        "head": head,
        "script_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "adapter_sha256": sha256((ROOT/"src/document_core/adapters"/(args.engine+".py")).read_bytes()).hexdigest(),
        "decoder_sha256": sha256((ROOT/"src/document_core/images.py").read_bytes()).hexdigest(),
        "font_sha256": sha256(Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf").read_bytes()).hexdigest(),
        "python": sys.version.split()[0], "rapidocr_version": version("rapidocr"),
        "onnxruntime_version": version("onnxruntime"),
        "models": {name: sha256((base/name).read_bytes()).hexdigest() for name in model_names},
        "initialization_seconds": initialization,
        "parent_peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "children_peak_rss_kib": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
        "candidates": {name: "EXECUTED" if name == args.engine else "NOT_RUN" for name in CANDIDATES},
        "cases": cases,
    }
    (out/"receipt.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps({"receipt": str((out/"receipt.json").relative_to(ROOT)),
                      "cases": len(cases), "field_errors": sum(c["field_errors"] for c in cases)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
