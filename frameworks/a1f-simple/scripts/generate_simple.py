#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

# Add framework to path
FRAMEWORK_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(FRAMEWORK_ROOT))

from core import generate


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate A1 form from template with placeholder replacement only")
    parser.add_argument("--form", required=True, help="Path to form JSON")
    parser.add_argument("--output", required=True, help="Output PDF path")
    parser.add_argument("--erase-empty", action="store_true", help="Erase empty placeholders")
    args = parser.parse_args()
    
    form = json.loads(Path(args.form).read_text(encoding="utf-8"))
    out = generate.generate(form, args.output, erase_empty=args.erase_empty)
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
