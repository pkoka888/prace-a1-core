#!/usr/bin/env python3
"""Strict offline benchmark validator and human-label-only scorer.

Exit codes: 0 proven scoring-ready/scored, 1 deterministic invalidity, 2 unproven.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft7Validator, FormatChecker

DEFAULT_DIR = Path(__file__).resolve().parent
PUBLIC_COUNT, HOLDOUT_COUNT = 18, 7
STATUSES = {"draft-invalid-for-scoring", "verification-in-progress", "scoring-ready"}


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{path.name}: {exc}") from exc


def schema_errors(instance, schema, label: str) -> list[str]:
    validator = Draft7Validator(schema, format_checker=FormatChecker())
    return [f"{label}{'/' + '/'.join(map(str, e.absolute_path)) if e.absolute_path else ''}: {e.message}" for e in sorted(validator.iter_errors(instance), key=lambda x: list(x.absolute_path))]


def duplicate_values(values):
    counts = Counter(values)
    return sorted(value for value, count in counts.items() if count > 1)


def validate(bench: Path) -> tuple[list[str], list[str], dict]:
    errors, unproven = [], []
    try:
        status = read_json(bench / "STATUS.json")
        questions = read_json(bench / "questions.json")
        holdout = read_json(bench / "holdout.json")
        gold = read_json(bench / "gold-answers/merged-answers.json")
        corpus_schema = read_json(bench / "schemas/benchmark_corpus_schema.json")
        evidence_schema = read_json(bench / "schemas/evidence_schema.json")
        review_schema = read_json(bench / "schemas/review_schema.json")
    except ValueError as exc:
        return [str(exc)], [], {}

    if set(status) - {"status", "version", "last_updated", "reason", "repair_required"}:
        errors.append("STATUS.json has unknown properties")
    current = status.get("status")
    if current not in STATUSES:
        errors.append(f"STATUS.json: unsupported status {current!r}")
    errors += schema_errors(questions, corpus_schema, "questions.json")
    if "status" in questions or "status" in questions.get("metadata", {}):
        errors.append("questions.json duplicates the authoritative STATUS.json status")

    public = questions.get("public_questions", [])
    public_ids = [q.get("id") for q in public if isinstance(q, dict)]
    if len(public_ids) != PUBLIC_COUNT:
        errors.append(f"expected {PUBLIC_COUNT} public IDs, got {len(public_ids)}")
    if dup := duplicate_values(public_ids):
        errors.append(f"duplicate public IDs: {dup}")
    for q in public:
        if isinstance(q, dict) and any(key in q for key in ("gold_answer", "answer", "atomic_claims", "evidence_refs")):
            errors.append(f"{q.get('id', '?')}: public runner input embeds gold/evidence")

    hset = holdout.get("holdout_set", {})
    holdout_questions = hset.get("questions", [])
    holdout_ids = [q.get("id") for q in holdout_questions if isinstance(q, dict)]
    if len(holdout_ids) != HOLDOUT_COUNT or len(set(holdout_ids)) != HOLDOUT_COUNT:
        errors.append(f"expected {HOLDOUT_COUNT} unique holdout IDs")
    if set(public_ids) & set(holdout_ids):
        errors.append("public and holdout IDs overlap")

    answers = gold.get("answers", {})
    expected_ids = set(public_ids) | set(holdout_ids)
    answer_ids = set(answers) if isinstance(answers, dict) else set()
    if answer_ids != expected_ids:
        errors.append(f"gold IDs mismatch: missing={sorted(expected_ids-answer_ids)}, extra={sorted(answer_ids-expected_ids)}")
    claim_owner, evidence_refs = {}, set()
    placeholders = False
    for qid, answer in answers.items() if isinstance(answers, dict) else []:
        if not isinstance(answer, dict):
            errors.append(f"gold {qid} must be an object"); continue
        claims = answer.get("atomic_claims", [])
        evidence = answer.get("evidence", [])
        if not claims:
            errors.append(f"gold {qid} has no atomic claims")
        for claim in claims:
            cid = claim.get("claim_id") if isinstance(claim, dict) else None
            if not cid or cid in claim_owner:
                errors.append(f"gold {qid} has missing/duplicate claim ID {cid!r}")
            else:
                claim_owner[cid] = qid
        for item in evidence:
            if not isinstance(item, dict):
                errors.append(f"gold {qid} evidence entry must be an object"); continue
            eid = item.get("evidence_id")
            if not eid or eid in evidence_refs:
                errors.append(f"gold {qid} has missing/duplicate evidence ID {eid!r}")
            evidence_refs.add(eid)
            if "PLACEHOLDER" in json.dumps(item):
                placeholders = True

    raw_dir = bench / "evidence/raw"
    raw_evidence = {}
    for path in sorted(raw_dir.glob("*.json")) if raw_dir.exists() else []:
        try:
            item = read_json(path)
            errors += schema_errors(item, evidence_schema, str(path.relative_to(bench)))
            eid = item.get("evidence_id")
            if eid in raw_evidence:
                errors.append(f"duplicate evidence artifact {eid}")
            raw_evidence[eid] = item
            if item.get("question_id") not in expected_ids:
                errors.append(f"evidence {eid} has dangling question_id")
            for cid in item.get("claim_ids", []):
                if claim_owner.get(cid) != item.get("question_id"):
                    errors.append(f"evidence {eid} has dangling/cross-question claim {cid}")
        except ValueError as exc:
            errors.append(str(exc))
    if evidence_refs - set(raw_evidence):
        unproven.append(f"missing evidence artifacts: {len(evidence_refs-set(raw_evidence))}")
    if set(raw_evidence) - evidence_refs:
        errors.append(f"unreferenced evidence artifacts: {sorted(set(raw_evidence)-evidence_refs)}")
    if placeholders:
        unproven.append("gold evidence contains placeholder hashes")

    reviews = []
    for path in sorted((bench / "reviewers").glob("review-*.json")):
        try:
            review = read_json(path); reviews.append(review)
            errors += schema_errors(review, review_schema, str(path.relative_to(bench)))
        except ValueError as exc:
            errors.append(str(exc))
    reviewed_pairs = {(r.get("question_id"), r.get("reviewer_id")) for r in reviews}
    for review in reviews:
        qid = review.get("question_id")
        if qid not in expected_ids:
            errors.append(f"review {review.get('review_id')} has dangling question_id")
        if review.get("review_kind") == "gold-verification":
            for label in review.get("claim_labels", []):
                if claim_owner.get(label.get("claim_id")) != qid:
                    errors.append(f"review {review.get('review_id')} has dangling/cross-question gold claim")
    for qid in expected_ids:
        if len({rid for qq, rid in reviewed_pairs if qq == qid and rid in {"reviewer-a", "reviewer-b"}}) < 2:
            unproven.append(f"{qid}: two independent reviews missing")

    commitment = hset.get("metadata", {}).get("commitment_hash", "")
    if not isinstance(commitment, str) or len(commitment) != 64 or any(c not in "0123456789abcdef" for c in commitment):
        unproven.append("holdout commitment hash is not finalized")
    if current != "scoring-ready":
        unproven.append(f"authoritative status is {current}")
    if current == "scoring-ready" and unproven:
        errors.append("scoring-ready status contradicts incomplete evidence/review gates")
    return errors, sorted(set(unproven)), {"status": current, "question_ids": expected_ids}


def score(bench: Path, result_path: Path, review_paths: list[Path]) -> tuple[int, dict]:
    errors, unproven, context = validate(bench)
    if errors:
        return 1, {"status": "invalid", "issues": errors}
    if unproven:
        return 2, {"status": "unproven", "issues": unproven}
    result = read_json(result_path)
    result_schema = read_json(bench / "schemas/system_results_schema.json")
    errs = schema_errors(result, result_schema, result_path.name)
    result_ids = [r.get("question_id") for r in result.get("results", [])]
    if set(result_ids) - context["question_ids"] or set(result.get("questions_processed", [])) != set(result_ids):
        errs.append("result question IDs are dangling or disagree with questions_processed")
    claim_ids = {c.get("claim_id") for r in result.get("results", []) for c in r.get("claims", [])}
    labels = []
    review_schema = read_json(bench / "schemas/review_schema.json")
    for path in review_paths:
        review = read_json(path); errs += schema_errors(review, review_schema, path.name)
        labels.extend(review.get("claim_labels", []))
    labelled = {label.get("claim_id") for label in labels if label.get("claim_id", "").startswith("sc-")}
    if errs:
        return 1, {"status": "invalid", "issues": errs}
    system_labels = [l for l in labels if l.get("claim_id", "").startswith("sc-")]
    if not claim_ids or claim_ids - labelled or any(l.get("correctness") == "unproven" or l.get("citation_support") == "unproven" for l in system_labels):
        return 2, {"status": "unproven", "issues": ["complete explicit human labels are required"]}
    correctness = {"correct": 1.0, "partial": 0.5, "incorrect": 0.0}
    factual = sum(correctness[l["correctness"]] for l in system_labels) / len(system_labels)
    citation = sum(l["citation_support"] == "supported" for l in system_labels) / len(system_labels)
    report = {"report_id": f"score-{result['result_id']}", "result_id": result["result_id"], "status": "scored", "metrics": {"factual_accuracy": factual, "citation_precision": citation}, "label_counts": dict(Counter(l["correctness"] for l in system_labels)), "generated_at": datetime.now(timezone.utc).isoformat(), "issues": []}
    errs = schema_errors(report, read_json(bench / "schemas/score_report_schema.json"), "score report")
    return (1, {"status": "invalid", "issues": errs}) if errs else (0, report)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark-dir", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--score", type=Path)
    parser.add_argument("--reviews", type=Path, nargs="*", default=[])
    args = parser.parse_args()
    if args.score:
        code, payload = score(args.benchmark_dir.resolve(), args.score.resolve(), [p.resolve() for p in args.reviews])
    else:
        errors, unproven, _ = validate(args.benchmark_dir.resolve())
        code = 1 if errors else 2 if unproven else 0
        payload = {"status": "invalid" if errors else "unproven" if unproven else "scoring-ready", "errors": errors, "unproven": unproven}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
