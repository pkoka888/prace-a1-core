#!/usr/bin/env python3
"""Calculate deterministic research scores from documented evidence (v1.2).

Scores are CALCULATED from the entity's evidence and structure. They are never
copied from arbitrary self-reported entity scores.

Rubric (each 0-100):
  source_authority : weighted by evidence source_type (official/primary higher)
  recency          : based on (as_of - evidence retrieval_date) proximity
  corroboration    : fraction of material claims with corroborated evidence
  completeness     : fraction of required fields/claims present
  accounting_fit   : heuristic from offerings relevant to accounting workflow
  overall          : equal-weighted mean of the above

Entities without evidence produce no score (recorded as unproven), never zero.

Exit codes: 0 ok; 2 environment error.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INPUT_PATH = ROOT / "research" / "processed" / "entities.json"

SOURCE_WEIGHTS = {
    "official_api": 100, "spec": 95, "policy": 95, "legal_text": 95,
    "vendor_documentation": 85, "academic_paper": 90, "research_report": 85,
    "github_repo": 80, "comparison_blog": 55, "synthetic_test": 60, "other": 50,
}
ACCOUNTING_FIELDS = [
    "received_invoice_processing", "issued_invoice_generation",
    "accounting_proposals", "matching_automation", "archive_compliance", "audit_trail",
]


def parse_date(s):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None


def calculate_scores(entity: dict, as_of: str, evidence_by_entity: dict) -> dict:
    evs = evidence_by_entity.get(entity.get("id"), [])
    if not evs:
        return {"source_authority": "unproven", "recency": "unproven",
                "corroboration": "unproven", "completeness": "unproven",
                "accounting_fit": "unproven", "overall": "unproven",
                "calculated": True, "calculated_at": f"{as_of}T00:00:00Z"}

    # source_authority: mean of source weights
    sa = sum(SOURCE_WEIGHTS.get(e.get("source_type"), 50) for e in evs) / max(1, len(evs))

    # recency: closest retrieval_date to as_of
    as_of_d = parse_date(as_of)
    rec_vals = []
    for e in evs:
        rd = parse_date(e.get("retrieval_date"))
        if as_of_d and rd:
            days = abs((as_of_d - rd).days)
            rec_vals.append(max(0, 100 - days / 3.65))  # ~1yr -> 0
    recency = sum(rec_vals) / max(1, len(rec_vals)) if rec_vals else 50

    # corroboration: fraction corroborated
    corr = sum(1 for e in evs if e.get("corroboration_status") in ("corroborated", "partial"))
    corroboration = round(100 * corr / max(1, len(evs)), 1)

    # completeness: required fields present
    req = ["title", "cohort", "source_links", "offerings", "pricing", "claims", "github_metrics"]
    present = sum(1 for f in req if entity.get(f))
    completeness = round(100 * present / len(req), 1)

    # accounting_fit: confirmed relevant offerings
    offs = entity.get("offerings", {})
    confirmed = sum(1 for f in ACCOUNTING_FIELDS if offs.get(f, {}).get("state") == "confirmed")
    accounting_fit = round(100 * confirmed / len(ACCOUNTING_FIELDS), 1)

    overall = round((sa + recency + corroboration + completeness + accounting_fit) / 5, 1)
    return {
        "source_authority": round(sa, 1),
        "recency": round(recency, 1),
        "corroboration": corroboration,
        "completeness": completeness,
        "accounting_fit": accounting_fit,
        "overall": overall,
        "calculated": True,
        "calculated_at": f"{as_of}T00:00:00Z",
    }


def main():
    parser = argparse.ArgumentParser(description="Calculate deterministic research scores")
    parser.add_argument("--root", default=".", help="Repository root directory")
    parser.add_argument("--input", default=None, help="Envelope input path")
    parser.add_argument("--as-of", required=True,
                        help="Explicit scoring date (YYYY-MM-DD); never inferred")
    parser.add_argument("--output", required=True,
                        help="Candidate envelope output path; input is never modified")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    input_path = Path(args.input).resolve() if args.input else (root / "research" / "processed" / "entities.json")
    output_path = Path(args.output).resolve()
    if not input_path.is_file():
        print("ERROR: envelope not found", file=sys.stderr)
        sys.exit(2)
    try:
        env = json.loads(input_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read envelope: {exc}", file=sys.stderr)
        return 2

    if parse_date(args.as_of) is None:
        print("ERROR: --as-of must be a valid YYYY-MM-DD date", file=sys.stderr)
        return 1

    try:
        sys.path.insert(0, str(root))
        from scripts.validate_research_schema import validate_envelope
    except Exception:
        print("ERROR: canonical validator unavailable", file=sys.stderr)
        return 2

    valid, detail, _ = validate_envelope(root, env)
    if not valid:
        print(f"REFUSE: input envelope invalid: {detail}", file=sys.stderr)
        return 1

    as_of = args.as_of

    evidence = env.get("evidence", []) or []
    by_entity = {}
    for e in evidence:
        by_entity.setdefault(e.get("entity_id"), []).append(e)

    candidate = copy.deepcopy(env)
    candidate["as_of"] = as_of
    for ent in candidate.get("entities", []):
        ent["scores"] = calculate_scores(ent, as_of, by_entity)

    valid, detail, _ = validate_envelope(root, candidate)
    if not valid:
        print(f"REFUSE: scored candidate invalid: {detail}", file=sys.stderr)
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(candidate, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")

    entities = candidate.get("entities", [])
    scored = sum(1 for ent in entities
                 if isinstance(ent["scores"].get("overall"), (int, float)))
    print(f"Scored {len(entities)} entities ({scored} with calculated scores; rest unproven)")
    print(f"Output: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
