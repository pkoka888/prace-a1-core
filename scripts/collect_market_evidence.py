#!/usr/bin/env python3
"""Collect market evidence for invoice/accounting tools (raw lane writer).

This collector NEVER writes canonical processed output
(`research/processed/entities.json`). It writes lane-specific raw evidence
under `research/acquisition/raw/<lane>.json` for later verification and
normalization by the primary agent.

All collection is fixture-based and deterministic. External request failures are
recorded as explicit `unproven`/`error` states, never as zero stars/forks or
absent functionality.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "research" / "acquisition" / "raw"

LANES = ["oss_invoice", "czech_invoice_software", "czech_accounting_firms", "czech_individual", "studies_comprehensive"]


def collect_lane(lane: str, as_of: str) -> dict:
    """Return a raw lane envelope. Empty by default; subagents populate verified records."""
    return {
        "lane": lane,
        "as_of": as_of,
        "collector_version": "1.0.0",
        "records": [],
        "note": "Raw lane skeleton. Populated by verified subagent collection; never canonical.",
    }


def main():
    parser = argparse.ArgumentParser(description="Collect raw research lane evidence")
    parser.add_argument("--root", default=".", help="Repository root directory")
    parser.add_argument("--as-of", default=date.today().isoformat(), help="Explicit collection date (YYYY-MM-DD)")
    parser.add_argument("--lane", default=None, help="Single lane to (re)initialize; default all")
    parser.add_argument("--output", default=None, help="Override raw output directory")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    raw_dir = Path(args.output).resolve() if args.output else (root / "research" / "acquisition" / "raw")
    raw_dir.mkdir(parents=True, exist_ok=True)

    lanes = [args.lane] if args.lane else LANES
    for lane in lanes:
        if lane not in LANES:
            print(f"ERROR: unknown lane {lane}", file=sys.stderr)
            sys.exit(1)
        payload = collect_lane(lane, args.as_of)
        out = raw_dir / f"{lane}.json"
        out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Wrote raw lane skeleton: {out}")

    print(f"Collector wrote {len(lanes)} raw lane file(s) under {raw_dir}")
    print("Canonical processed output is NOT modified by the collector.")
    return 0


if __name__ == "__main__":
    sys.exit(main())