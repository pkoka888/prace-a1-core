#!/usr/bin/env python3
"""Normalize and deduplicate research entities into a canonical, schema-valid envelope.

Reads raw lane files from `research/acquisition/raw/`, merges verified records
into the canonical run envelope, and writes a candidate envelope that is
validated against the frozen research-model schema BEFORE the process exits 0.

Fail-closed behaviour (Gate 1):
  * a raw record with no `id` is a hard error (never silently skipped);
  * an ID collision between the existing envelope and a raw lane is an
    unresolved conflict and fails the run unless `--replace` is given for the
    offending lane;
  * `--replace` deterministically replaces the prior entity (and all of its
    dependent evidence) by ID with the incoming record and that lane's evidence
    for the same entity;
  * any merged record that does not satisfy the entity schema fails the run;
  * the candidate envelope is validated (schema + relationship/state invariants,
    including run-level acceptance rules) before exit 0. If validation fails,
    the process exits 1 and the previous canonical output is NOT overwritten.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "research" / "acquisition" / "raw"
INPUT_PATH = ROOT / "research" / "processed" / "entities.json"
OUTPUT_PATH = ROOT / "research" / "processed" / "entities.normalized.json"
REPORT_PATH = ROOT / "research" / "processed" / "normalization_report.json"

LANES = ["oss_invoice", "czech_invoice_software", "czech_accounting_firms",
         "czech_individual", "studies_comprehensive"]


def load_envelope(path: Path) -> dict | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def merge_lanes(envelope: dict, raw_dir: Path, replace: bool):
    """Return (merged_entities, merged_evidence, problems_dict, normalized_count)."""
    merged_entities = list(envelope.get("entities", []) or [])
    merged_evidence = list(envelope.get("evidence", []) or [])
    seen_ids = {e.get("id") for e in merged_entities if isinstance(e, dict) and e.get("id")}

    missing_ids: list[str] = []
    conflicts: list[str] = []
    invalid_records: list[str] = []
    normalized_count = 0

    for lane in LANES:
        lane_file = raw_dir / f"{lane}.json"
        if not lane_file.is_file():
            continue
        lane_data = json.loads(lane_file.read_text(encoding="utf-8"))
        lane_ev_by_entity: dict = defaultdict(list)
        for ev in lane_data.get("evidence", []) or []:
            if isinstance(ev, dict):
                lane_ev_by_entity[ev.get("entity_id")].append(ev)

        for rec in lane_data.get("records", []) or []:
            if not isinstance(rec, dict):
                invalid_records.append("non-object record in lane %s" % lane)
                continue
            rid = rec.get("id")
            if rid is None:
                missing_ids.append("record without id in lane %s" % lane)
                continue
            if rid in seen_ids:
                conflicts.append(rid)
                if not replace:
                    continue
                # Deterministic replacement: drop the prior entity and all of
                # its evidence, then insert the incoming record + its evidence.
                merged_entities = [e for e in merged_entities
                                   if not (isinstance(e, dict) and e.get("id") == rid)]
                merged_evidence = [ev for ev in merged_evidence
                                   if not (isinstance(ev, dict) and ev.get("entity_id") == rid)]
            seen_ids.add(rid)
            merged_entities.append(rec)
            for ev in lane_ev_by_entity.get(rid, []):
                merged_evidence.append(ev)
            normalized_count += 1

    problems = {}
    if missing_ids:
        problems["missing_ids"] = missing_ids
    if conflicts and not replace:
        problems["conflicts"] = sorted(set(conflicts))
    if invalid_records:
        problems["invalid_records"] = invalid_records
    return merged_entities, merged_evidence, problems, normalized_count


def main(argv=None):
    parser = argparse.ArgumentParser(description="Normalize research entities into canonical envelope")
    parser.add_argument("--root", default=".", help="Repository root directory")
    parser.add_argument("--input", default=None, help="Canonical envelope input (default research/processed/entities.json)")
    parser.add_argument("--output", default=None, help="Normalized envelope output")
    parser.add_argument("--as-of", default=None, help="Override as_of timestamp")
    parser.add_argument("--run-id", default=None, help="Override candidate run_id")
    parser.add_argument(
        "--run-status",
        choices=["collecting", "schema_valid"],
        default=None,
        help="Set the provisional candidate status; later states require separate review gates",
    )
    parser.add_argument("--replace", action="store_true", help="Replace conflicting lane records by ID (and their evidence)")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    raw_dir = root / "research" / "acquisition" / "raw"
    input_path = Path(args.input).resolve() if args.input else (root / "research" / "processed" / "entities.json")
    output_path = Path(args.output).resolve() if args.output else (root / "research" / "processed" / "entities.normalized.json")

    envelope = load_envelope(input_path)
    if envelope is None:
        print("ERROR: canonical envelope not found", file=sys.stderr)
        sys.exit(2)

    merged_entities, merged_evidence, problems, normalized_count = merge_lanes(envelope, raw_dir, args.replace)

    if problems:
        report = {
            "status": "failed",
            "missing_ids": problems.get("missing_ids", []),
            "conflicts": problems.get("conflicts", []),
            "invalid_records": problems.get("invalid_records", []),
            "normalized_count": normalized_count,
        }
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print("FAIL — normalization problems:", file=sys.stderr)
        if problems.get("missing_ids"):
            print("  - %d record(s) missing id" % len(problems["missing_ids"]), file=sys.stderr)
            for p in problems["missing_ids"]:
                print("    * " + p, file=sys.stderr)
        if problems.get("conflicts"):
            print("  - %d unresolved ID conflict(s): %s"
                  % (len(problems["conflicts"]), ", ".join(problems["conflicts"])), file=sys.stderr)
        if problems.get("invalid_records"):
            print("  - %d invalid raw record(s)" % len(problems["invalid_records"]), file=sys.stderr)
        print("Report: %s" % REPORT_PATH, file=sys.stderr)
        sys.exit(1)

    candidate = dict(envelope)
    candidate["entities"] = merged_entities
    candidate["evidence"] = merged_evidence
    if args.as_of:
        candidate["as_of"] = args.as_of
    if args.run_id:
        candidate["run_id"] = args.run_id
    if args.run_status:
        candidate["run_status"] = args.run_status

    # Validate the candidate before writing (every producer must self-validate
    # against the canonical library).
    try:
        from scripts.validate_research_schema import validate_envelope
    except Exception:
        sys.path.insert(0, str(ROOT))
        from scripts.validate_research_schema import validate_envelope

    ok, detail, _ = validate_envelope(root, candidate)
    if not ok:
        print("FAIL — candidate envelope invalid: " + detail, file=sys.stderr)
        sys.exit(1)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(candidate, indent=2, ensure_ascii=False), encoding="utf-8")
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps({
        "status": "ok",
        "normalized_count": normalized_count,
        "entity_total": len(merged_entities),
        "schema_version": candidate.get("schema_version"),
        "validated": detail,
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    print("Normalized envelope: %d entities (%d merged from raw), schema-valid" % (len(merged_entities), normalized_count))
    print("Output: %s" % output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
