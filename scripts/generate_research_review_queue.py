#!/usr/bin/env python3
"""Generate or check a deterministic, non-authoritative Plan AC review queue.

The command validates either a research-model-1.2 candidate or a supported
pack-bound atomic-results candidate, binds the exact candidate and frozen query
pack bytes by SHA-256, and creates blank operator tasks for entities, claims,
and unique evidence URLs. It never infers a verdict, imports a review, or
modifies the candidate.

Exit status: 0 generated/current; 1 invalid, unsafe, or stale; 2 unavailable
input/dependency (unproven).  ``--check`` is read-only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


SENSITIVE_PARTS = {
    "a1", "scans", "evidence", "ocr", "data", "output", "runtime",
    "secrets", ".env", ".history-remediation",
}


class InvalidInput(ValueError):
    """Deterministic validation or policy failure (exit 1)."""


class Unavailable(RuntimeError):
    """Missing input/dependency that leaves generation unproven (exit 2)."""


def contained(root: Path, value: str, *, output: bool = False) -> Path:
    path = Path(value)
    path = path.resolve() if path.is_absolute() else (root / path).resolve()
    if path != root and root not in path.parents:
        raise InvalidInput("path must remain inside project root")
    relative = path.relative_to(root)
    if any(part.lower() in SENSITIVE_PARTS for part in relative.parts):
        raise InvalidInput("private or runtime path is not allowed")
    if output:
        review_root = (root / "research" / "review").resolve()
        if path == review_root or review_root not in path.parents:
            raise InvalidInput("output must remain under research/review")
    return path


def read_json(path: Path) -> tuple[dict[str, Any], bytes]:
    try:
        raw = path.read_bytes()
    except FileNotFoundError as exc:
        raise Unavailable(f"missing input: {path}") from exc
    except OSError as exc:
        raise Unavailable(f"cannot read input: {path}: {exc}") from exc
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InvalidInput(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise InvalidInput(f"JSON root must be an object: {path}")
    return value, raw


def relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def binding(root: Path, path: Path, raw: bytes, **metadata: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": relative(root, path),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }
    result.update(metadata)
    return result


def empty_operator(template: dict[str, Any]) -> dict[str, None]:
    required = {
        "reviewer_id", "reviewed_at", "verdict", "notes",
        "replacement_source_url",
    }
    if set(template) != required or any(value is not None for value in template.values()):
        raise InvalidInput("operator review template must contain only blank operator fields")
    return deepcopy(template)


def source_task_id(url: str) -> str:
    return f"source-integrity::{hashlib.sha256(url.encode('utf-8')).hexdigest()}"


def public_https(url: str) -> str:
    try:
        from scripts.check_evidence_url import UnsafeURL, validate_public_https_url
    except ImportError:
        try:
            from check_evidence_url import UnsafeURL, validate_public_https_url
        except ImportError as exc:
            raise Unavailable("offline public-URL validator is unavailable") from exc
    try:
        return validate_public_https_url(url)
    except UnsafeURL as exc:
        raise InvalidInput(f"unsafe public evidence URL {url!r}: {exc}") from exc


def title_from_canonical_url(entity_id: str, url: str) -> str:
    parsed = urlsplit(url)
    path_name = next((part for part in reversed(parsed.path.split("/")) if part), "")
    if parsed.hostname and parsed.hostname.lower() == "github.com" and path_name:
        return path_name
    host = (parsed.hostname or "").lower()
    return host[4:] if host.startswith("www.") else (host or entity_id)


def load_and_validate_pack(root: Path, path: Path) -> tuple[dict[str, Any], bytes]:
    """Use the same frozen-pack validator as the atomic comparison gate."""
    _, raw = read_json(path)
    try:
        from scripts.compare_research_runs import load_query_pack
    except ImportError:
        sys.path.insert(0, str(root))
        try:
            from scripts.compare_research_runs import load_query_pack
        except ImportError as exc:
            raise Unavailable("atomic query-pack validator is unavailable") from exc
    try:
        return load_query_pack(root, path), raw
    except RuntimeError as exc:
        raise Unavailable(str(exc)) from exc
    except ValueError as exc:
        raise InvalidInput(str(exc)) from exc


def validate_atomic(root: Path, path: Path, pack: dict[str, Any]) -> dict[str, Any]:
    """Validate schema, pack binding, vocabularies, FKs, and field coverage."""
    try:
        from scripts.compare_research_runs import load_atomic_results
    except ImportError:
        sys.path.insert(0, str(root))
        try:
            from scripts.compare_research_runs import load_atomic_results
        except ImportError as exc:
            raise Unavailable("atomic result validator is unavailable") from exc
    try:
        payload, _ = load_atomic_results(root, path, pack)
        return payload
    except RuntimeError as exc:
        raise Unavailable(str(exc)) from exc
    except ValueError as exc:
        raise InvalidInput(str(exc)) from exc


def build_queue(
    root: Path,
    candidate: dict[str, Any],
    candidate_path: Path,
    candidate_raw: bytes,
    query_pack: dict[str, Any],
    query_path: Path,
    query_raw: bytes,
    operator_template: dict[str, Any],
) -> dict[str, Any]:
    if candidate.get("format_version") in {"atomic-results-1.0", "atomic-results-1.1"}:
        return build_atomic_queue(
            root, validate_atomic(root, candidate_path, query_pack), candidate_path,
            candidate_raw, query_pack, query_path, query_raw, operator_template,
        )
    if candidate.get("schema_version") != "1.2":
        raise InvalidInput(
            "input must be research-model-1.2, atomic-results-1.0, or atomic-results-1.1"
        )
    try:
        from scripts.validate_research_schema import validate_envelope
    except ImportError:
        sys.path.insert(0, str(root))
        try:
            from scripts.validate_research_schema import validate_envelope
        except ImportError as exc:
            raise Unavailable("canonical research validator is unavailable") from exc

    valid, detail, _ = validate_envelope(root, candidate)
    if not valid:
        raise InvalidInput(f"candidate refused: {detail}")
    candidate_query = candidate.get("query_version")
    pack_version = query_pack["query_pack_version"]
    if candidate_query is not None and candidate_query != pack_version:
        raise InvalidInput(
            f"query version mismatch: candidate={candidate_query!r}, pack={pack_version!r}"
        )

    evidence_by_id = {item["id"]: item for item in candidate["evidence"]}
    tasks: list[dict[str, Any]] = []
    counts = {"entity": 0, "claim": 0, "source_integrity": 0}

    def add(task: dict[str, Any]) -> None:
        task["operator"] = empty_operator(operator_template)
        tasks.append(task)
        counts[task["task_type"]] += 1

    for entity in sorted(candidate["entities"], key=lambda item: item["id"]):
        entity_url = public_https(entity["source_links"][0])
        base = {
            "entity_id": entity["id"],
            "entity_title": entity["title"],
            "cohort": entity["cohort"],
        }
        add({
            "task_id": f"entity::{entity['id']}",
            "task_type": "entity",
            **base,
            "source_url": entity_url,
            "source_publication_date": None,
            "source_access_date": entity["last_verified"],
            "claim_field": None,
            "claim_value": None,
            "claim_confidence": None,
            "result_status": None,
            "evidence_id": None,
            "evidence_ids": [],
            "source_task_ids": ([source_task_id(entity_url)]
                                if any(ev["canonical_url"] == entity_url for ev in candidate["evidence"])
                                else []),
            "references": [],
            "instructions": [
                "Confirm that the public sources identify the intended entity.",
                "Do not infer approval from collection, scoring, or this queue.",
            ],
        })
        ordered_claims = sorted(
            enumerate(entity.get("claims", [])),
            key=lambda pair: (pair[1]["field"], pair[1]["evidence_ref"], pair[0]),
        )
        for original_index, claim in ordered_claims:
            ev = evidence_by_id[claim["evidence_ref"]]
            add({
                "task_id": f"claim::{entity['id']}::{original_index}::{claim['evidence_ref']}",
                "task_type": "claim",
                **base,
                "source_url": ev["canonical_url"],
                "source_publication_date": ev.get("publication_date"),
                "source_access_date": ev["retrieval_date"],
                "claim_field": claim["field"],
                "claim_value": claim.get("value"),
                "claim_confidence": claim["confidence"],
                "result_status": None,
                "evidence_id": ev["id"],
                "evidence_ids": [ev["id"]],
                "source_task_ids": [source_task_id(public_https(ev["canonical_url"]))],
                "references": [],
                "instructions": [
                    "Compare the claim value with the cited public evidence.",
                    "Record uncertainty or contradictions; do not repair source data here.",
                ],
            })

    entity_by_id = {item["id"]: item for item in candidate["entities"]}
    grouped: dict[str, list[dict[str, Any]]] = {}
    for ev in candidate["evidence"]:
        grouped.setdefault(public_https(ev["canonical_url"]), []).append(ev)
    for url, linked in sorted(grouped.items()):
        ev = sorted(linked, key=lambda item: item["id"])[0]
        entity = entity_by_id[ev["entity_id"]]
        add({
            "task_id": source_task_id(url),
            "task_type": "source_integrity",
            "entity_id": entity["id"],
            "entity_title": entity["title"],
            "cohort": entity["cohort"],
            "source_url": url,
            "source_publication_date": ev.get("publication_date"),
            "source_access_date": ev["retrieval_date"],
            "claim_field": ev["claim_field"],
            "claim_value": None,
            "claim_confidence": ev["confidence"],
            "result_status": None,
            "evidence_id": ev["id"],
            "evidence_ids": sorted(item["id"] for item in linked),
            "source_task_ids": [],
            "references": sorted(
                ({"entity_id": item["entity_id"], "claim_field": item["claim_field"],
                  "evidence_id": item["id"]} for item in linked),
                key=lambda item: (item["entity_id"], item["claim_field"], item["evidence_id"]),
            ),
            "instructions": [
                "Open the cited public URL and assess publisher, date, and field relevance.",
                "A reachable URL is not proof that the associated claim is correct.",
            ],
        })

    counts["total"] = len(tasks)
    return {
        "queue_version": "1.1",
        "authority": "non_authoritative_operator_work_queue",
        "queue_status": "awaiting_operator_review",
        "generated_as_of": candidate["as_of"],
        "input_binding": binding(
            root, candidate_path, candidate_raw,
            run_id=candidate["run_id"], schema_version=candidate["schema_version"],
        ),
        "query_pack_binding": binding(
            root, query_path, query_raw,
            query_pack_version=pack_version,
            query_pack_hash=query_pack["query_pack_hash"],
        ),
        "task_counts": counts,
        "tasks": tasks,
    }


def build_atomic_queue(
    root: Path,
    candidate: dict[str, Any],
    candidate_path: Path,
    candidate_raw: bytes,
    query_pack: dict[str, Any],
    query_path: Path,
    query_raw: bytes,
    operator_template: dict[str, Any],
) -> dict[str, Any]:
    """Build review work directly from a validated atomic-results document."""
    is_v11 = candidate["format_version"] == "atomic-results-1.1"
    evidence_by_id = {item["id"]: item for item in candidate["evidence"]}
    entity_lanes = {item["entity_id"]: item["lane"] for item in candidate["results"]}
    results_by_key = {
        (item["entity_id"], item["field_id"]): item for item in candidate["results"]
    }
    legacy_canonical_field = {
        "oss_invoice": "canonical_repository",
        "czech_invoice_software": "canonical_product_url",
    }
    frozen_entities = {
        entity["id"]: (lane, entity["canonical_root_url"])
        for lane, definition in query_pack["lanes"].items()
        for entity in definition.get("entities", [])
    }
    evidence_source_task = {
        evidence_id: source_task_id(public_https(item["url"]))
        for evidence_id, item in evidence_by_id.items()
    }
    tasks: list[dict[str, Any]] = []
    counts = {"entity": 0, "claim": 0, "source_integrity": 0}

    def add(task: dict[str, Any]) -> None:
        task["operator"] = empty_operator(operator_template)
        tasks.append(task)
        counts[task["task_type"]] += 1

    for entity_id in sorted(entity_lanes):
        lane = entity_lanes[entity_id]
        if is_v11:
            frozen = frozen_entities.get(entity_id)
            if frozen is None or frozen[0] != lane:
                raise InvalidInput(f"{entity_id}: missing or mismatched frozen roster entry")
            canonical_url = public_https(frozen[1])
            canonical_refs = sorted(
                item["id"] for item in candidate["evidence"]
                if item["entity_id"] == entity_id
                and public_https(item["url"]) == canonical_url
            )
        else:
            canonical = results_by_key[(entity_id, legacy_canonical_field[lane])]
            if canonical["result_status"] != "proven" or not isinstance(canonical.get("value"), str):
                raise InvalidInput(f"{entity_id}: canonical URL must be a proven string")
            canonical_url = public_https(canonical["value"])
            canonical_refs = list(canonical["evidence_refs"])
        add({
            "task_id": f"entity::{entity_id}", "task_type": "entity",
            "entity_id": entity_id,
            "entity_title": title_from_canonical_url(entity_id, canonical_url),
            "cohort": lane, "source_url": canonical_url,
            "source_publication_date": None, "source_access_date": candidate["as_of"],
            "claim_field": None, "claim_value": None, "claim_confidence": None,
            "result_status": None, "evidence_id": None,
            "evidence_ids": canonical_refs,
            "source_task_ids": sorted({evidence_source_task[ref] for ref in canonical_refs}),
            "references": [],
            "instructions": [
                "Confirm that cited evidence identifies the intended entity.",
                "Do not infer approval from collection, comparison, or this queue.",
            ],
        })

    for result in sorted(candidate["results"], key=lambda item: (item["entity_id"], item["field_id"])):
        linked = [evidence_by_id[ref] for ref in result["evidence_refs"]]
        first = linked[0] if linked else None
        task = {
            "task_id": f"claim::{result['entity_id']}::{result['field_id']}",
            "task_type": "claim", "entity_id": result["entity_id"],
            "entity_title": result["entity_id"], "cohort": result["lane"],
            "source_url": first["url"] if first else None,
            "source_publication_date": None,
            "source_access_date": (first["retrieved_at"].split("T", 1)[0]
                                   if first else candidate["as_of"]),
            "claim_field": result["field_id"], "claim_value": result.get("value"),
            "claim_confidence": (result["claim_confidence"] if is_v11
                                 else result["verification_status"]),
            "result_status": result["result_status"],
            "evidence_id": first["id"] if first else None,
            "evidence_ids": list(result["evidence_refs"]),
            "source_task_ids": sorted({evidence_source_task[ref]
                                       for ref in result["evidence_refs"]}),
            "references": [],
            "instructions": [
                "Compare the atomic result with every evidence reference attached to it.",
                "An unproven or conflicted result is not an automatic rejection or approval.",
            ],
        }
        if is_v11:
            task["claim_provenance"] = {
                "applicability": result["applicability"],
                "enumeration_scope": result["enumeration_scope"],
                "captured_at": result.get("captured_at"),
            }
        add(task)

    grouped: dict[str, list[dict[str, Any]]] = {}
    for ev in candidate["evidence"]:
        grouped.setdefault(public_https(ev["url"]), []).append(ev)
    for url, linked in sorted(grouped.items()):
        ev = sorted(linked, key=lambda item: item["id"])[0]
        references = []
        for item in sorted(linked, key=lambda value: value["id"]):
            reference = {
                "entity_id": item["entity_id"], "claim_field": item["field_id"],
                "evidence_id": item["id"],
            }
            if is_v11:
                reference.update({
                    "evidence_class": item["evidence_class"],
                    "verification_status": item["verification_status"],
                    "retrieved_at": item["retrieved_at"],
                    "locator": item.get("locator"),
                })
            references.append(reference)
        add({
            "task_id": source_task_id(url), "task_type": "source_integrity",
            "entity_id": ev["entity_id"], "entity_title": ev["entity_id"],
            "cohort": entity_lanes[ev["entity_id"]], "source_url": url,
            "source_publication_date": None,
            "source_access_date": ev["retrieved_at"].split("T", 1)[0],
            "claim_field": ev["field_id"], "claim_value": None,
            "claim_confidence": ev["verification_status"], "result_status": None,
            "evidence_id": ev["id"],
            "evidence_ids": sorted(item["id"] for item in linked),
            "source_task_ids": [],
            "references": references,
            "instructions": [
                "Open the cited public URL and assess source identity and field relevance.",
                "A reachable URL is not proof that the associated result is correct.",
            ],
        })
    counts["total"] = len(tasks)
    queue = {
        "queue_version": "1.1",
        "authority": "non_authoritative_operator_work_queue",
        "queue_status": "awaiting_operator_review",
        "generated_as_of": candidate["as_of"],
        "input_binding": binding(
            root, candidate_path, candidate_raw,
            run_id=candidate["run_id"], format_version=candidate["format_version"],
        ),
        "query_pack_binding": binding(
            root, query_path, query_raw,
            query_pack_version=query_pack["query_pack_version"],
            query_pack_hash=query_pack["query_pack_hash"],
        ),
        "task_counts": counts,
        "tasks": tasks,
    }
    if is_v11:
        # Preserve only schema-governed collector provenance. Environment and
        # credential state can never enter an operator handoff through this path.
        queue["collection_provenance"] = deepcopy(candidate["provenance"])
    return queue


def validate_queue(root: Path, queue: dict[str, Any]) -> None:
    try:
        import jsonschema
    except ImportError as exc:
        raise Unavailable("jsonschema is unavailable") from exc
    schema, _ = read_json(root / "research" / "review" / "review-queue.schema.json")
    try:
        jsonschema.Draft7Validator.check_schema(schema)
        validator = jsonschema.Draft7Validator(schema, format_checker=jsonschema.FormatChecker())
    except Exception as exc:
        raise Unavailable(f"review queue schema is unavailable or invalid: {exc}") from exc
    errors = sorted(validator.iter_errors(queue), key=lambda item: list(item.path))
    if errors:
        detail = " | ".join(
            f"{'/'.join(map(str, err.path)) or '<root>'}: {err.message}"
            for err in errors[:8]
        )
        raise InvalidInput(f"generated queue failed schema validation: {detail}")
    ids = [task["task_id"] for task in queue["tasks"]]
    if len(ids) != len(set(ids)):
        raise InvalidInput("generated queue contains duplicate task IDs")
    derived = {kind: 0 for kind in ("entity", "claim", "source_integrity")}
    source_ids = {task["task_id"] for task in queue["tasks"]
                  if task["task_type"] == "source_integrity"}
    evidence_owners: dict[str, str] = {}
    for task in queue["tasks"]:
        derived[task["task_type"]] += 1
        if any(value is not None for value in task["operator"].values()):
            raise InvalidInput("generator attempted to populate an operator verdict")
        if not set(task["source_task_ids"]).issubset(source_ids):
            raise InvalidInput(f"{task['task_id']}: dangling source task reference")
        if task["task_type"] == "source_integrity":
            if task["source_task_ids"]:
                raise InvalidInput(f"{task['task_id']}: source task cannot reference itself")
            for evidence_id in task["evidence_ids"]:
                if evidence_id in evidence_owners:
                    raise InvalidInput(f"evidence {evidence_id} belongs to multiple source tasks")
                evidence_owners[evidence_id] = task["task_id"]
    # The source tasks are generated after claims, so prove linkage once the
    # complete ownership index exists.
    for task in queue["tasks"]:
        if task["task_type"] != "source_integrity":
            for evidence_id in task["evidence_ids"]:
                if evidence_owners.get(evidence_id) not in task["source_task_ids"]:
                    raise InvalidInput(f"{task['task_id']}: evidence/source task mismatch")
    derived["total"] = len(queue["tasks"])
    if derived != queue["task_counts"]:
        raise InvalidInput("task_counts do not match generated tasks")


def render(queue: dict[str, Any]) -> bytes:
    return (json.dumps(queue, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--input", default="research/processed/entities.scored.json")
    parser.add_argument("--query-pack", default="research/query-packs/plan-ac-core-1.0.json")
    parser.add_argument("--template", default="research/review/operator-review.template.json")
    parser.add_argument("--output", default="research/review/queue.json")
    parser.add_argument("--check", action="store_true", help="Read-only freshness and validity check")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    try:
        candidate_path = contained(root, args.input)
        query_path = contained(root, args.query_pack)
        template_path = contained(root, args.template)
        output_path = contained(root, args.output, output=True)
        protected = {
            (root / "research" / "review" / "review-queue.schema.json").resolve(),
            (root / "research" / "review" / "operator-review.template.json").resolve(),
            query_path,
            candidate_path,
        }
        if output_path in protected:
            raise InvalidInput("output cannot overwrite an input, schema, or template")
        candidate, candidate_raw = read_json(candidate_path)
        query_pack, query_raw = load_and_validate_pack(root, query_path)
        template, _ = read_json(template_path)
        queue = build_queue(
            root, candidate, candidate_path, candidate_raw,
            query_pack, query_path, query_raw, template,
        )
        validate_queue(root, queue)
        expected = render(queue)
        if args.check:
            try:
                actual = output_path.read_bytes()
            except FileNotFoundError as exc:
                raise InvalidInput(f"review queue is missing: {output_path}") from exc
            if actual != expected:
                raise InvalidInput("review queue is stale or modified")
            action = "current"
        else:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(expected)
            action = "generated"
        result = {
            "result": "pass", "action": action,
            "output": relative(root, output_path),
            "task_counts": queue["task_counts"], "exit": 0,
        }
        print(json.dumps(result, ensure_ascii=False) if args.json else
              f"PASS — {action} {result['output']} ({queue['task_counts']['total']} tasks)")
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
