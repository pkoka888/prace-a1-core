#!/usr/bin/env python3
"""Validate a completed response against an immutable Plan AC review queue.

The command is read-only. It validates exact queue-byte binding, one response
per queue task, controlled verdicts and public replacement URLs. It never
changes the queue, candidate, catalog, evidence states, or plan authority.

Exit status: 0 valid and exactly complete; 1 invalid/stale/unsafe; 2 unavailable.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

from generate_research_review_queue import (
    InvalidInput, Unavailable, build_queue, contained, load_and_validate_pack,
    read_json, relative, render, validate_queue,
)


def validate_schema(root: Path, value: dict[str, Any]) -> None:
    try:
        import jsonschema
    except ImportError as exc:
        raise Unavailable("jsonschema is unavailable") from exc
    schema, _ = read_json(root / "research/review/review-response.schema.json")
    try:
        jsonschema.Draft7Validator.check_schema(schema)
        validator = jsonschema.Draft7Validator(
            schema, format_checker=jsonschema.FormatChecker()
        )
    except Exception as exc:
        raise Unavailable(f"review response schema unavailable: {exc}") from exc
    errors = sorted(validator.iter_errors(value), key=lambda item: list(item.path))
    if errors:
        detail = " | ".join(
            f"{'/'.join(map(str, err.path)) or '<root>'}: {err.message}"
            for err in errors[:8]
        )
        raise InvalidInput(f"response failed schema validation: {detail}")


def validate_response(
    root: Path, queue_path: Path, queue: dict[str, Any], queue_raw: bytes,
    response: dict[str, Any],
) -> dict[str, int]:
    validate_queue(root, queue)
    candidate_path = contained(root, queue["input_binding"]["path"])
    query_path = contained(root, queue["query_pack_binding"]["path"])
    candidate, candidate_raw = read_json(candidate_path)
    query_pack, query_raw = load_and_validate_pack(root, query_path)
    template, _ = read_json(root / "research/review/operator-review.template.json")
    expected_queue = build_queue(
        root, candidate, candidate_path, candidate_raw, query_pack, query_path,
        query_raw, template,
    )
    validate_queue(root, expected_queue)
    if render(expected_queue) != queue_raw:
        raise InvalidInput("queue is stale or was not generated from its bound inputs")
    validate_schema(root, response)
    binding = response["queue_binding"]
    if binding["path"] != relative(root, queue_path):
        raise InvalidInput("response queue path does not match --queue")
    actual_hash = hashlib.sha256(queue_raw).hexdigest()
    if binding["sha256"] != actual_hash:
        raise InvalidInput("response queue hash is stale or incorrect")
    if binding["queue_version"] != queue["queue_version"]:
        raise InvalidInput("response queue version mismatch")

    expected = {task["task_id"] for task in queue["tasks"]}
    response_ids = [item["task_id"] for item in response["responses"]]
    if len(response_ids) != len(set(response_ids)):
        raise InvalidInput("response contains duplicate task IDs")
    missing = sorted(expected - set(response_ids))
    extra = sorted(set(response_ids) - expected)
    if missing or extra:
        detail = []
        if missing:
            detail.append(f"missing {len(missing)} task responses")
        if extra:
            detail.append(f"unknown {len(extra)} task responses")
        raise InvalidInput("response coverage is not exact: " + "; ".join(detail))

    try:
        from check_evidence_url import UnsafeURL, validate_public_https_url
    except ImportError as exc:
        raise Unavailable("offline public-URL validator unavailable") from exc
    generated_floor = datetime.combine(
        datetime.fromisoformat(queue["generated_as_of"]).date(), time.min, tzinfo=timezone.utc
    )
    provenance = queue.get("collection_provenance")
    if provenance:
        completed = datetime.fromisoformat(provenance["completed_at"].replace("Z", "+00:00"))
        generated_floor = max(generated_floor, completed.astimezone(timezone.utc))
    future_limit = datetime.now(timezone.utc) + timedelta(minutes=5)
    for item in response["responses"]:
        try:
            reviewed_at = datetime.fromisoformat(item["reviewed_at"].replace("Z", "+00:00"))
        except (TypeError, ValueError) as exc:
            raise InvalidInput(f"{item['task_id']}: reviewed_at is not RFC3339") from exc
        if reviewed_at.tzinfo is None:
            raise InvalidInput(f"{item['task_id']}: reviewed_at must include a timezone")
        reviewed_at = reviewed_at.astimezone(timezone.utc)
        if reviewed_at < generated_floor:
            raise InvalidInput(f"{item['task_id']}: reviewed_at predates the bound collection/queue")
        if reviewed_at > future_limit:
            raise InvalidInput(f"{item['task_id']}: reviewed_at is in the future")
        replacement = item["replacement_source_url"]
        if item["verdict"] == "replacement_proposed" and replacement is None:
            raise InvalidInput(
                f"{item['task_id']}: replacement_proposed requires a replacement URL"
            )
        if item["verdict"] != "replacement_proposed" and replacement is not None:
            raise InvalidInput(
                f"{item['task_id']}: replacement URL requires replacement_proposed verdict"
            )
        if replacement is not None:
            try:
                validate_public_https_url(replacement)
            except UnsafeURL as exc:
                raise InvalidInput(
                    f"{item['task_id']}: unsafe replacement URL: {exc}"
                ) from exc
    return {"tasks": len(expected), "responses": len(response_ids)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--queue", required=True)
    parser.add_argument("--input", required=True, help="Completed response JSON")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    try:
        queue_path = contained(root, args.queue)
        response_path = contained(root, args.input)
        if queue_path == response_path:
            raise InvalidInput("response must be separate from the immutable queue")
        queue, queue_raw = read_json(queue_path)
        response, _ = read_json(response_path)
        counts = validate_response(root, queue_path, queue, queue_raw, response)
        result = {
            "result": "pass", "authority": response["authority"],
            "queue": relative(root, queue_path), **counts, "exit": 0,
        }
        print(json.dumps(result) if args.json else
              f"PASS — {counts['responses']}/{counts['tasks']} bound responses; no import performed")
        return 0
    except InvalidInput as exc:
        result = {"result": "fail", "error": str(exc), "exit": 1}
        print(json.dumps(result) if args.json else f"FAIL — {exc}", file=sys.stderr)
        return 1
    except (Unavailable, OSError) as exc:
        result = {"result": "unproven", "error": str(exc), "exit": 2}
        print(json.dumps(result) if args.json else f"UNPROVEN — {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
