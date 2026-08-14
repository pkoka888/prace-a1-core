#!/usr/bin/env python3
"""Run the canonical synthetic Plan AC collector mini-pilot.

This creates immutable source-capture artifacts and a collector execution. It
is synthetic verification only and never produces market evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path

from jsonschema import Draft7Validator, FormatChecker

ROOT = Path(__file__).resolve().parent.parent
FIXTURE_REF = "research/acquisition/synthetic-mini-pilot/fixture-set.json"
FIXTURE_SCHEMA_REF = "research/acquisition/synthetic-mini-pilot/fixture-set.schema.json"
PACK_REF = "research/query-packs/plan-ac-core-1.1.json"
PROTOCOL_REF = "research/query-packs/plan-ac-collector-protocol-1.1.json"
CONTRACT_REF = "research/query-packs/collector-execution-1.1.schema.json"
MARKER = "SYNTHETIC_PLAN_AC_MINI_PILOT_DO_NOT_USE_AS_MARKET_EVIDENCE"
FIXTURE_DIGEST = "236e6fc3bc6f1ec78c8e7b36cbc41aa25a186e2f93851b6ad84a1a62af442e05"
RUN_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,79}$")


def canonical_digest(value: object, omitted: str | None = None) -> str:
    candidate = dict(value) if isinstance(value, dict) else value
    if omitted and isinstance(candidate, dict):
        candidate.pop(omitted, None)
    raw = json.dumps(candidate, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def contained(root: Path, value: str, *, expected_prefix: str | None = None) -> Path:
    raw = Path(value)
    if raw.is_absolute():
        raise ValueError("paths must be relative to --root")
    path = (root / raw).resolve()
    try:
        relative = path.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError("path escapes --root") from exc
    if expected_prefix and not relative.as_posix().startswith(expected_prefix.rstrip("/") + "/"):
        raise ValueError(f"path must be below {expected_prefix}")
    return path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def binding(root: Path, ref: str, *, semantic: bool = True) -> dict:
    path = root / ref
    result = {"path": ref, "byte_sha256": file_sha(path)}
    if semantic:
        result["semantic_sha256"] = canonical_digest(load_json(path))
    return result


def validate_fixture(root: Path, fixture_ref: str) -> tuple[dict, dict, dict]:
    if fixture_ref != FIXTURE_REF:
        raise ValueError(f"fixture set must be canonical path {FIXTURE_REF}")
    fixture = load_json(root / fixture_ref)
    schema = load_json(root / FIXTURE_SCHEMA_REF)
    errors = sorted(Draft7Validator(schema, format_checker=FormatChecker()).iter_errors(fixture),
                    key=lambda error: list(error.absolute_path))
    if errors:
        raise ValueError(f"fixture schema: {list(errors[0].absolute_path)}: {errors[0].message}")
    if fixture["synthetic_marker"] != MARKER:
        raise ValueError("canonical synthetic marker is missing")
    if fixture["fixture_set_hash"] != FIXTURE_DIGEST or canonical_digest(fixture, "fixture_set_hash") != FIXTURE_DIGEST:
        raise ValueError("fixture-set digest mismatch")
    pack = load_json(root / PACK_REF)
    protocol = load_json(root / PROTOCOL_REF)
    if fixture["query_pack_hash"] != pack["query_pack_hash"]:
        raise ValueError("fixture set is not bound to canonical query pack")
    if fixture["protocol_config_digest"] != protocol["config_digest"]:
        raise ValueError("fixture set is not bound to canonical protocol")
    roster = {entity["id"]: (lane_id, entity) for lane_id, lane in pack["lanes"].items()
              for entity in lane["entities"]}
    source_ids = [row["entity_id"] for row in fixture["sources"]]
    if len(source_ids) != len(set(source_ids)) or set(source_ids) != set(roster):
        raise ValueError("fixture sources must equal the frozen 20-entity roster")
    expanded = 0
    for lane_id, lane in pack["lanes"].items():
        expected_fields = [field["id"] for field in lane["fields"]]
        actual_fields = [row["field_id"] for row in fixture["decision_templates"][lane_id]]
        if len(actual_fields) != len(set(actual_fields)) or actual_fields != expected_fields:
            raise ValueError(f"fixture decision templates do not match frozen field order for {lane_id}")
        expanded += len(lane["entities"]) * len(actual_fields)
    if expanded != 230:
        raise ValueError(f"fixture decision matrix expands to {expanded}, expected 230")
    return fixture, pack, protocol


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush(); os.fsync(stream.fileno())
        os.replace(name, path)
    except BaseException:
        try: os.unlink(name)
        except FileNotFoundError: pass
        raise


def run(root: Path, run_id: str, output_ref: str, fixture_ref: str = FIXTURE_REF) -> Path:
    if not RUN_RE.fullmatch(run_id):
        raise ValueError("invalid run ID")
    output = contained(root, output_ref, expected_prefix="research/acquisition/synthetic-mini-pilot/runs")
    if output.exists():
        raise ValueError("execution output already exists")
    fixture, pack, protocol = validate_fixture(root, fixture_ref)
    capture_ref = f"research/acquisition/source-captures/{run_id}"
    capture_dir = contained(root, capture_ref, expected_prefix="research/acquisition/source-captures")
    if capture_dir.exists():
        raise ValueError("capture output already exists")
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from scripts import capture_research_sources as capture
    records, excerpts, request_items = [], {}, []
    roster = {entity["id"]: (lane_id, entity) for lane_id, lane in pack["lanes"].items()
              for entity in lane["entities"]}
    for source in fixture["sources"]:
        lane_id, entity = roster[source["entity_id"]]
        field_targets = [{"entity_id": source["entity_id"], "field_id": field["id"]}
                         for field in pack["lanes"][lane_id]["fields"]]
        item = {"id": source["source_id"], "url": entity["canonical_root_url"], "method": "GET",
                "field_targets": field_targets,
                "excerpt": {"selector": "term-window",
                            "terms": ["synthetic support detail"], "max_chars": 500}}
        request_items.append(item)
        record, excerpt = capture._response_record(
            item, status=200, final_url=item["url"], chain=[],
            retrieved_at=fixture["retrieved_at"], content_type="text/plain",
            body=source["body_text"].encode(), methods=["GET"])
        records.append(record); excerpts[source["source_id"]] = excerpt
    request = {"schema_version": "source-capture-1.1", "run_id": run_id,
               "query_pack_version": pack["query_pack_version"],
               "query_pack_hash": pack["query_pack_hash"], "requests": request_items}
    capture_manifest = {
        "schema_version": "source-capture-result-1.1", "run_id": run_id, "mode": "fixture",
        "query_pack_version": pack["query_pack_version"], "query_pack_hash": pack["query_pack_hash"],
        "request_sha256": capture.sha256(capture.canonical_bytes(request)), "results": records,
        "summary": {"captured": 20, "unproven": 0, "invalid": 0},
    }
    capture.validate_result(root, capture_manifest, request)
    capture.publish_atomic(root, capture_dir, capture.expected_files(capture_manifest, excerpts), request)
    capture_manifest_path = capture_dir / "manifest.json"
    capture_manifest_sha = file_sha(capture_manifest_path)
    result_by_id = {row["id"]: row for row in records}
    sources, inspections = [], []
    for fixture_source in fixture["sources"]:
        entity_id, source_id = fixture_source["entity_id"], fixture_source["source_id"]
        lane_id, _entity = roster[entity_id]
        row = result_by_id[source_id]
        excerpt_ref = f"{capture_ref}/{row['excerpt']['path']}"
        sources.append({
            "id": source_id, "entity_id": entity_id,
            "capture_manifest_ref": f"{capture_ref}/manifest.json",
            "capture_manifest_sha256": capture_manifest_sha, "capture_run_id": run_id,
            "capture_mode": "fixture", "capture_result_id": source_id,
            "capture_result_sha256": canonical_digest(row), "requested_url": row["requested_url"],
            "final_url": row["final_url"], "redirect_chain": row["redirect_chain"],
            "http_status": row["http_status"], "retrieved_at": row["retrieved_at"],
            "content_type": row["content_type"], "verification_status": "verified",
            "response_sha256": row["response_sha256"], "excerpt_sha256": row["excerpt"]["sha256"],
            "excerpt_ref": excerpt_ref,
        })
        supporting = (root / excerpt_ref).read_text(encoding="utf-8")
        span = [0, len(supporting.encode())]
        for decision in fixture["decision_templates"][lane_id]:
            inspections.append({
                "entity_id": entity_id, "field_id": decision["field_id"], "source_ids": [source_id],
                "locators": [{"source_id": source_id, "locator": decision["locator"]}],
                "observations": [{"source_id": source_id, "value": decision["value"],
                                  "excerpt_span": span, "supporting_text": supporting}],
                "inspected_sections": [decision["locator"]], "query_terms": [decision["query_term"]],
                "support_status": decision["support_status"],
                "reason": "Canonical synthetic fixture explicitly encodes this typed decision.",
            })
    script_ref = "scripts/run_collector_fixture.py"
    manifest = {
        "format_version": "collector-execution-1.1",
        "evidence_scope": "synthetic_fixture_only_not_market_evidence",
        "run_id": run_id, "execution_instance_id": f"fixture-{run_id}",
        "authority_classification": "synthetic_fixture_verified", "operator_attestation": None,
        "query_pack": binding(root, PACK_REF), "protocol": binding(root, PROTOCOL_REF),
        "contract_schema": binding(root, CONTRACT_REF),
        "collector": {
            "collector_id": "canonical-synthetic-mini-pilot", "provider": None, "model": None,
            "identity_verification": "unverified", "config_digest": fixture["fixture_set_hash"],
            "implementation": binding(root, script_ref, semantic=False),
            "prompt": {**binding(root, PROTOCOL_REF, semantic=False), "version": "protocol-1.1"},
            "config": {**binding(root, FIXTURE_REF, semantic=False), "version": "fixture-set-1.0"},
            "tools": [{"name": "capture_research_sources", "version": "1.1"},
                      {"name": "run_collector_fixture", "version": "1.1"}],
        },
        "capture": {"started_at": "2026-08-14T11:59:00Z", "completed_at": "2026-08-14T12:01:00Z"},
        "sources": sources, "inspections": inspections,
    }
    from scripts.validate_collector_execution import validate_execution
    if validate_execution(root, manifest, load_json(root / CONTRACT_REF)):
        raise ValueError("canonical synthetic execution did not reach verified completeness")
    atomic_json(output, manifest)
    return output


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--fixture-set", default=FIXTURE_REF)
    args = parser.parse_args(argv)
    try:
        output = run(Path(args.root).resolve(), args.run_id, args.output, args.fixture_set)
        print(f"PASS — synthetic-only collector execution: {output}")
        return 0
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"FAIL — {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
