#!/usr/bin/env python3
"""Validate the single machine-readable approval register (CLI)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from planning.approval_register import validate, ApprovalRegisterError


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--require-clean", action="store_true",
                        help="Fail if the review scope is dirty")
    args = parser.parse_args()

    try:
        result = validate(args.root.resolve(), require_clean=args.require_clean)
    except ApprovalRegisterError as e:
        if args.json:
            print(json.dumps({"result": "fail", "records": 0, "errors": [str(e)], "warnings": []}))
        else:
            print(f"approval register: FAIL — {e}")
        return 1

    if args.json:
        print(
            json.dumps(result, ensure_ascii=False, indent=2)
        )
    else:
        status = result["result"].upper()
        n = result["records"]
        errs = result["errors"]
        warns = result["warnings"]
        if errs:
            print(f"approval register: {status} ({n} records), {len(errs)} error(s)")
            for e in errs:
                print(f"  {e}")
        else:
            print(f"approval register: {status} ({n} records)")
        if warns:
            for w in warns:
                print(f"  [warning] {w}")
    return 0 if result["result"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
