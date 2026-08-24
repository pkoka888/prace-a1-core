#!/usr/bin/env python3
"""Validate the single machine-readable approval register."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from jsonschema import Draft7Validator

ROOT = Path(__file__).resolve().parent.parent


def validate(root: Path) -> dict:
    errors: list[str] = []
    schema = json.loads((root / "planning/approvals.schema.json").read_text(encoding="utf-8"))
    data = json.loads((root / "planning/approvals.json").read_text(encoding="utf-8"))
    for error in sorted(Draft7Validator(schema).iter_errors(data), key=lambda e: list(e.path)):
        errors.append("schema: " + "/".join(map(str, error.path)) + ": " + error.message)
    records = data.get("records", [])
    catalog = json.loads((root / "planning/catalog.json").read_text(encoding="utf-8"))
    catalog_by_id = {item.get("id"): item for item in catalog.get("items", [])}
    ids = [record.get("id") for record in records]
    if len(ids) != len(set(ids)):
        errors.append("duplicate approval record id")
    known = set(ids)
    for record in records:
        rid = record.get("id", "?")
        choices = record.get("choices", [])
        checks = record.get("checks", [])
        if record.get("human_decision") == "approved":
            if not record.get("approver") or not record.get("approved_at") or not record.get("approval_evidence"):
                errors.append(f"{rid}: approved decision lacks approver/date/evidence")
            if any(choice.get("approval") != "approved" for choice in choices):
                errors.append(f"{rid}: overall approval conflicts with a non-approved choice")
        for choice in choices:
            if choice.get("selected") != choice.get("recommended") and not choice.get("deviation_reason"):
                errors.append(f"{rid}/{choice.get('id')}: deviation lacks reason")
            catalog_item = catalog_by_id.get(choice.get("id"))
            expected_state = "accepted" if choice.get("approval") == "approved" else choice.get("approval")
            if not catalog_item:
                errors.append(f"{rid}/{choice.get('id')}: missing catalog decision")
            elif catalog_item.get("decision_state") != expected_state:
                errors.append(f"{rid}/{choice.get('id')}: approval conflicts with catalog state")
            elif choice.get("approval") == "approved" and catalog_item.get("decision_date") != record.get("approved_at"):
                errors.append(f"{rid}/{choice.get('id')}: approval date conflicts with catalog")
        statuses = {check.get("status") for check in checks}
        derived = "failed" if "failed" in statuses else ("passed" if checks and statuses <= {"passed", "not-required"} else "pending")
        if record.get("validation") != derived:
            errors.append(f"{rid}: validation is {record.get('validation')} but checks derive {derived}")
        if record.get("implementation_gate") == "open" and (record.get("human_decision") != "approved" or derived != "passed"):
            errors.append(f"{rid}: implementation gate cannot open without approval and passed checks")
        if record.get("activation_gate") == "open" and record.get("implementation_gate") != "open":
            errors.append(f"{rid}: activation gate cannot open before implementation gate")
        if record.get("implementation_gate") == "blocked" and not record.get("implementation_gate_reason"):
            errors.append(f"{rid}: blocked implementation gate lacks reason")
        for dependency in record.get("dependencies", []):
            if dependency.get("id") not in known:
                errors.append(f"{rid}: missing dependency {dependency.get('id')}")
        if not (root / record.get("source", "")).is_file():
            errors.append(f"{rid}: source does not exist")
    return {"result": "pass" if not errors else "fail", "records": len(records), "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = validate(args.root.resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else ("approval register: " + result["result"]))
    return 0 if result["result"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
