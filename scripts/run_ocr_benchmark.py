#!/usr/bin/env python3
"""Run synthetic OCR benchmark over local candidate engines (honest, no execution here).

This script does NOT download models or execute heavy OCR engines. It reads the
artifact manifest and records each candidate engine as `unproven` with an exact
reason (engine not executed in this lightweight pass). Actual local engine runs
are a separate, explicitly authorized step that binds to immutable confirmed
invoice versions (Plan AD) and records versions, hardware, latency, memory.

Exit codes: 0 ok; 2 environment error.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "research" / "synthetic" / "artifact_manifest.json"
OUT_PATH = ROOT / "research" / "synthetic" / "benchmark_results.json"

CANDIDATES = ["docling", "paddleocr", "invoice2data", "ocrmypdf_tesseract"]


def main():
    parser = argparse.ArgumentParser(description="Run synthetic OCR benchmark (honest probe)")
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument("--input", default=None, help="Artifact manifest path")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    manifest_path = Path(args.input).resolve() if args.input else (root / "research" / "synthetic" / "artifact_manifest.json")
    if not manifest_path.is_file():
        print("ERROR: run create_synthetic_benchmark.py first", file=sys.stderr)
        sys.exit(2)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    results = {
        "schema_version": "1.1",
        "as_of": manifest.get("as_of"),
        "seed": manifest.get("seed"),
        "artifact_count": len(manifest.get("artifacts", [])),
        "engines": {},
        "note": "Engine execution deferred. Actual runs bind to immutable confirmed invoice versions (Plan AD) and record versions/hardware/latency/memory.",
    }
    for cand in CANDIDATES:
        results["engines"][cand] = {
            "status": "unproven",
            "reason": "engine not executed in lightweight benchmark pass; actual run requires explicit local authorization",
            "metrics": None,
        }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Benchmark probe: {results['artifact_count']} artifacts, all engines unproven (not executed)")
    print(f"Results: {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())