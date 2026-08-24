#!/usr/bin/env python3
"""Generate the file:// compatible approval dashboard asset."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def render(data: dict) -> str:
    return "window.APPROVAL_REGISTER = " + json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + ";\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    source = root / "planning/approvals.json"
    target = root / "docs/prototypes/roadmap-portal/approval-data.js"
    expected = render(json.loads(source.read_text(encoding="utf-8")))
    if args.check:
        if not target.is_file() or target.read_text(encoding="utf-8") != expected:
            print("approval asset is stale", file=sys.stderr)
            return 1
        print("Approval asset is current:", target)
        return 0
    target.write_text(expected, encoding="utf-8")
    print("Wrote", target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
