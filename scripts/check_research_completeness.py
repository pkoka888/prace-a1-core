#!/usr/bin/env python3
"""Validate research cohort completeness against minimum thresholds (derived).

Counts are DERIVED from valid entities, never trusted from self-reported fields.
Also enforces the canonical run-level acceptance rules (verified/accepted) via
``validate_research_schema.validate_envelope`` so the completeness gate cannot
be satisfied by an envelope that fails schema or state invariants.

Exit codes:
  0  cohort quotas met AND all coverage/acceptance checks pass
  1  cohort quotas, coverage, or acceptance checks fail
  2  environment error (missing file / unparseable JSON / missing deps)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INPUT_PATH = ROOT / "research" / "processed" / "entities.json"
REPORT_PATH = ROOT / "research" / "processed" / "completeness_report.json"

LANES = ["oss_invoice", "czech_invoice_software", "czech_accounting_firms", "czech_individual", "studies_comprehensive"]
MIN_PER_COHORT = 10


def main():
    parser = argparse.ArgumentParser(description="Check research completeness")
    parser.add_argument("--root", default=".", help="Repository root directory")
    parser.add_argument("--input", default=None, help="Envelope input path")
    parser.add_argument("--as-of", default=None, help="Explicit as_of (informational)")
    parser.add_argument(
        "--min-reviews-per-entity",
        type=int,
        default=0,
        help="Require this many distinct reviewers to cover every entity (pilot acceptance gate)",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    input_path = Path(args.input).resolve() if args.input else (root / "research" / "processed" / "entities.json")
    if not input_path.is_file():
        print("ERROR: envelope not found", file=sys.stderr)
        sys.exit(2)
    try:
        env = json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"ERROR: invalid JSON: {exc}", file=sys.stderr)
        sys.exit(2)

    # Canonical schema + relationship/state gate (rejects unsupported versions).
    try:
        from scripts.validate_research_schema import validate_envelope
    except Exception:
        sys.path.insert(0, str(ROOT))
        from scripts.validate_research_schema import validate_envelope
    env_ok, env_detail, _ = validate_envelope(root, env)
    if not env_ok:
        print("FAIL — envelope invalid: " + env_detail, file=sys.stderr)
        sys.exit(1)

    entities = env.get("entities", []) or []
    evidence = env.get("evidence", []) or []
    reviews = env.get("reviews", []) or []
    targets = env.get("cohort_targets", {lane: MIN_PER_COHORT for lane in LANES})

    # Derive counts from valid entities
    counts = {lane: 0 for lane in LANES}
    invalid_entities = 0
    for e in entities:
        if not isinstance(e, dict) or "id" not in e:
            invalid_entities += 1
            continue
        c = e.get("cohort")
        if c in counts:
            counts[c] += 1

    # Quota check
    quota_failures = []
    for lane in LANES:
        target = targets.get(lane, MIN_PER_COHORT)
        if counts[lane] < target:
            quota_failures.append(f"{lane}: {counts[lane]}/{target}")

    # Coverage checks (only meaningful if entities exist)
    evidence_ids = {e.get("id") for e in evidence if isinstance(e, dict)}
    missing_evidence = []
    for e in entities:
        if not isinstance(e, dict):
            continue
        for c in e.get("claims", []) or []:
            ref = c.get("evidence_ref") if isinstance(c, dict) else None
            if ref and ref not in evidence_ids:
                missing_evidence.append(e["id"])
                break
    # Also flag entities that have no claims at all
    for e in entities:
        if isinstance(e, dict) and not e.get("claims"):
            if e["id"] not in missing_evidence:
                missing_evidence.append(e["id"])
    missing_pricing = [
        e["id"]
        for e in entities
        if isinstance(e, dict)
        and e.get("pricing", {}).get("public_status") in (None, "unknown")
        and not any(
            isinstance(claim, dict)
            and claim.get("field") == "pricing_disclosure"
            and claim.get("evidence_ref") in evidence_ids
            for claim in (e.get("claims", []) or [])
        )
    ]
    missing_scores = [e["id"] for e in entities if isinstance(e, dict) and not e.get("scores", {}).get("calculated")]
    unverified_scores = any(e.get("scores", {}).get("calculated") is not True for e in entities if isinstance(e, dict))
    reviewers_by_entity = {e.get("id"): set() for e in entities if isinstance(e, dict)}
    for review in reviews:
        if not isinstance(review, dict):
            continue
        reviewer_id = review.get("reviewer_id")
        if not reviewer_id:
            continue
        for entity_id in review.get("verified_entities", []) or []:
            if entity_id in reviewers_by_entity:
                reviewers_by_entity[entity_id].add(reviewer_id)
    review_shortfall = [
        entity_id
        for entity_id, reviewer_ids in reviewers_by_entity.items()
        if len(reviewer_ids) < args.min_reviews_per_entity
    ]

    problems = []
    if quota_failures:
        problems.append("Quota unmet: " + "; ".join(quota_failures))
    if invalid_entities:
        problems.append(f"{invalid_entities} invalid entity records")
    if entities and missing_evidence:
        problems.append(f"{len(missing_evidence)} entities lack claims/evidence linkage")
    if entities and missing_pricing:
        problems.append(f"{len(missing_pricing)} entities lack pricing disclosure")
    if entities and (missing_scores or unverified_scores):
        problems.append("scores not calculated from documented rubric")
    if review_shortfall:
        problems.append(
            f"{len(review_shortfall)} entities lack {args.min_reviews_per_entity} distinct reviewer(s)"
        )

    report = {
        "run_id": env.get("run_id"),
        "as_of": env.get("as_of"),
        "run_status": env.get("run_status"),
        "derived_counts": counts,
        "targets": targets,
        "quota_met": not quota_failures,
        "invalid_entities": invalid_entities,
        "missing_evidence": missing_evidence,
        "missing_pricing": missing_pricing,
        "unverified_scores": unverified_scores,
        "review_count": len(reviews),
        "minimum_reviews_per_entity": args.min_reviews_per_entity,
        "review_shortfall": review_shortfall,
        "problems": problems,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    if problems:
        print("FAIL — completeness problems:", file=sys.stderr)
        for p in problems:
            print("  - " + p, file=sys.stderr)
        print(f"Report: {REPORT_PATH}")
        sys.exit(1)

    print(f"PASS — all cohort quotas met and coverage checks pass")
    print(f"Report: {REPORT_PATH}")
    sys.exit(0)


if __name__ == "__main__":
    sys.exit(main())
