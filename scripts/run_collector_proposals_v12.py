#!/usr/bin/env python3
"""Create a capture-bound, proposal-only Plan AC collector execution v1.2.

This command performs no network access and cannot promote observations to
research evidence.  It combines the frozen v1.1 source-capture contract with
the v1.0 normalization rules.  Exit 0 means that the proposal was generated;
exit 1 means invalid input; exit 2 means a required local dependency is absent.
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
from typing import Any

from jsonschema import Draft7Validator, FormatChecker

try:
    from scripts.validate_field_normalization import (
        InvalidRules, Unavailable, normalize, safe_regex_values, validate_rules,
    )
except ModuleNotFoundError:  # direct ``python scripts/...`` execution
    from validate_field_normalization import (  # type: ignore[no-redef]
        InvalidRules, Unavailable, normalize, safe_regex_values, validate_rules,
    )


ROOT = Path(__file__).resolve().parent.parent
PACK_REF = "research/query-packs/plan-ac-core-1.1.json"
PROTOCOL_REF = "research/query-packs/plan-ac-collector-protocol-1.1.json"
RULES_REF = "research/query-packs/field-normalization-1.0.json"
CAPTURE_SCHEMA_REF = "research/query-packs/source-capture-result-1.1.schema.json"
INPUT_SCHEMA_REF = "research/query-packs/collector-proposal-input-1.1.schema.json"
OUTPUT_SCHEMA_REF = "research/query-packs/collector-execution-1.2.schema.json"
IMPLEMENTATION_REF = "scripts/run_collector_proposals_v12.py"
DENIED = {"a1", "scans", "evidence", "ocr", "data", "output", "runtime", "secrets", ".history-remediation"}


class InvalidProposal(ValueError):
    pass


class MissingDependency(RuntimeError):
    pass


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def semantic_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def file_sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except (OSError, PermissionError) as exc:
        raise MissingDependency(f"cannot read {path}: {exc}") from exc


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise MissingDependency(f"missing file: {path}") from exc
    except (OSError, UnicodeDecodeError) as exc:
        raise MissingDependency(f"cannot read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise InvalidProposal(f"invalid JSON in {path}: {exc}") from exc


def contained(root: Path, ref: str, *, must_exist: bool = True) -> Path:
    raw = Path(ref)
    if raw.is_absolute():
        raise InvalidProposal(f"absolute path is denied: {ref}")
    path = (root / raw).resolve()
    try:
        rel = path.relative_to(root.resolve())
    except ValueError as exc:
        raise InvalidProposal(f"path escapes --root: {ref}") from exc
    if not rel.parts or rel.parts[0] in DENIED or rel.name == ".env":
        raise InvalidProposal(f"sensitive/runtime path is denied: {ref}")
    if must_exist and not path.is_file():
        raise MissingDependency(f"required file unavailable: {ref}")
    return path


def validate_schema(value: Any, schema: Any, label: str) -> None:
    errors = sorted(Draft7Validator(schema, format_checker=FormatChecker()).iter_errors(value), key=lambda e: tuple(map(str, e.absolute_path)))
    if errors:
        e = errors[0]
        where = "/".join(map(str, e.absolute_path)) or "<root>"
        raise InvalidProposal(f"{label} {where}: {e.message}")


def check_binding(root: Path, binding: dict[str, str], expected: str | None = None) -> tuple[Path, Any]:
    if expected is not None and binding["path"] != expected:
        raise InvalidProposal(f"binding must use {expected}")
    path = contained(root, binding["path"])
    value = read_json(path)
    if file_sha256(path) != binding["byte_sha256"]:
        raise InvalidProposal(f"byte hash mismatch: {binding['path']}")
    if semantic_sha256(value) != binding["semantic_sha256"]:
        raise InvalidProposal(f"semantic hash mismatch: {binding['path']}")
    return path, value


def make_binding(root: Path, ref: str) -> dict[str, str]:
    path = contained(root, ref)
    value = read_json(path)
    return {"path": ref, "byte_sha256": file_sha256(path), "semantic_sha256": semantic_sha256(value)}


def pack_index(pack: dict[str, Any]) -> tuple[dict[tuple[str, str], tuple[str, dict[str, Any]]], set[tuple[str, str]]]:
    fields: dict[tuple[str, str], tuple[str, dict[str, Any]]] = {}
    for lane_id, lane in pack["lanes"].items():
        for entity in lane["entities"]:
            for field in lane["fields"]:
                fields[(entity["id"], field["id"])] = (lane_id, field)
    return fields, set(fields)


def rule_matches(rule: dict[str, Any], raw: Any) -> tuple[bool, Any]:
    if not isinstance(raw, str):
        return False, None
    spec = rule["input"]
    candidate = normalize(raw, spec["normalization_profile"])
    if spec["match_mode"] == "exact_value":
        matched = candidate if candidate in spec["values"] else None
    else:
        domain = [item for pattern in spec["patterns"] for item in safe_regex_values(pattern)]
        matched = candidate if candidate in domain else None
    if matched is None:
        return False, None
    output = rule["output"]
    return True, output["value"] if output["kind"] == "fixed_typed_value" else matched


def validate_enumeration(scope: dict[str, Any], observations: list[dict[str, Any]], excerpt_truncated: bool) -> bool:
    captured = scope["captured_enumerands"]
    mapped = scope["mapped_enumerands"]
    unmapped = scope["unmapped_enumerands"]
    mapped_raw = [row["raw_value"] for row in mapped]
    if len(captured) != len(set(captured)) or len(mapped_raw) != len(set(mapped_raw)):
        raise InvalidProposal("enumeration contains duplicate raw values")
    if set(mapped_raw) & set(unmapped):
        raise InvalidProposal("an enumerand cannot be both mapped and unmapped")
    if not (set(mapped_raw) | set(unmapped)).issubset(set(captured)):
        raise InvalidProposal("mapped/unmapped enumerands must be captured")
    observed_pairs = {(row["raw_value"], row["proposed_value"], row["mapping_rule_id"]) for row in observations}
    for row in mapped:
        if (row["raw_value"], row["mapped_value"], row["mapping_rule_id"]) not in observed_pairs:
            raise InvalidProposal("mapped enumerand lacks a matching observation")
    complete = scope["completeness"] == "complete"
    if complete and excerpt_truncated:
        raise InvalidProposal("truncated capture cannot establish complete enumeration")
    if complete and set(captured) != set(mapped_raw) | set(unmapped):
        raise InvalidProposal("complete enumeration must explicitly classify every captured enumerand")
    # A partial result is intentionally unproven even when every currently seen
    # token was mapped; its declared scope prevents an exhaustive-list claim.
    return not complete


def validate_and_build(root: Path, proposal: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    validate_schema(proposal, read_json(contained(root, INPUT_SCHEMA_REF)), "proposal")
    _, pack = check_binding(root, proposal["query_pack"], PACK_REF)
    check_binding(root, proposal["protocol"], PROTOCOL_REF)
    rules_path, rules_doc = check_binding(root, proposal["normalization_rules"], RULES_REF)
    try:
        rules_report = validate_rules(root, rules_doc, rules_path.read_bytes())
    except Unavailable as exc:
        raise MissingDependency(str(exc)) from exc
    except InvalidRules as exc:
        raise InvalidProposal(str(exc)) from exc
    if rules_report["query_pack_hash"] != pack["query_pack_hash"]:
        raise InvalidProposal("normalization rules resolve a different query pack")

    implementation = proposal["collector"]["implementation"]
    if implementation["path"] != IMPLEMENTATION_REF or file_sha256(contained(root, IMPLEMENTATION_REF)) != implementation["byte_sha256"]:
        raise InvalidProposal("collector implementation hash/path mismatch")
    check_binding(root, proposal["collector"]["config"])
    if (proposal["collector"]["provider"] is None) != (proposal["collector"]["model"] is None):
        raise InvalidProposal("provider and model must both be set or both null")

    capture_schema = read_json(contained(root, CAPTURE_SCHEMA_REF))
    captures: dict[tuple[str, str], dict[str, Any]] = {}
    capture_bindings: dict[str, dict[str, str]] = {}
    for binding in proposal["capture_manifests"]:
        path, manifest = check_binding(root, binding)
        validate_schema(manifest, capture_schema, f"capture {binding['path']}")
        if manifest["query_pack_hash"] != pack["query_pack_hash"]:
            raise InvalidProposal("capture query-pack hash mismatch")
        expected_summary = {name: sum(row["state"] == name for row in manifest["results"]) for name in ("captured", "unproven", "invalid")}
        if manifest["summary"] != expected_summary:
            raise InvalidProposal("capture summary mismatch")
        for row in manifest["results"]:
            key = (binding["path"], row["id"])
            if key in captures:
                raise InvalidProposal("duplicate capture result binding")
            captures[key] = row
        capture_bindings[binding["path"]] = binding

    fields, expected_slots = pack_index(pack)
    rules = {rule["id"]: rule for rule in rules_doc["rules"]}
    seen: set[tuple[str, str]] = set()
    output_inspections: list[dict[str, Any]] = []
    remains_unproven = False
    for inspection in proposal["inspections"]:
        slot = (inspection["entity_id"], inspection["field_id"])
        if slot not in expected_slots:
            raise InvalidProposal(f"unknown entity-field slot: {slot}")
        if slot in seen:
            raise InvalidProposal(f"duplicate entity-field inspection: {slot}")
        seen.add(slot)
        lane_id, field = fields[slot]
        refs = {(row["capture_manifest_path"], row["capture_result_id"]) for row in inspection["sources"]}
        if len(refs) != len(inspection["sources"]):
            raise InvalidProposal("duplicate source reference")
        for ref in refs:
            if ref not in captures:
                raise InvalidProposal(f"unknown capture reference: {ref}")
            target = {"entity_id": slot[0], "field_id": slot[1]}
            if target not in captures[ref]["field_targets"]:
                raise InvalidProposal(f"capture field_targets do not authorize {slot}")
        status = inspection["inspection_status"]
        if status == "not_inspected" and refs:
            raise InvalidProposal("not_inspected must not bind a source")
        if status == "does_not_establish" and not refs:
            raise InvalidProposal("does_not_establish requires a bound attempted source")
        if status in {"proven", "conflicted"} and any(captures[ref]["state"] != "captured" or captures[ref].get("excerpt") is None for ref in refs):
            raise InvalidProposal(f"{status} requires captured excerpt sources")

        output_observations = []
        for observation in inspection["observations"]:
            source_key = (observation["source"]["capture_manifest_path"], observation["source"]["capture_result_id"])
            if source_key not in refs:
                raise InvalidProposal("observation source is not inspection-bound")
            rule = rules.get(observation["mapping_rule_id"])
            if rule is None:
                raise InvalidProposal("unknown mapping_rule_id")
            scope = rule["scope"]
            if scope["lane"] != lane_id or slot[0] not in scope["entity_ids"] or scope["field_id"] != slot[1]:
                raise InvalidProposal("mapping rule scope does not authorize entity-field observation")
            matched, expected = rule_matches(rule, observation["raw_value"])
            if not matched or observation["proposed_value"] != expected:
                raise InvalidProposal("mapping rule input/output mismatch")
            excerpt_path = contained(root, str(Path(source_key[0]).parent / captures[source_key]["excerpt"]["path"]))
            excerpt = excerpt_path.read_text(encoding="utf-8")
            if observation["supporting_text"] not in excerpt or normalize(str(observation["raw_value"]), rule["input"]["normalization_profile"]) not in normalize(excerpt, rule["input"]["normalization_profile"]):
                raise InvalidProposal("observation is not anchored in the bound excerpt")
            output_observations.append({**observation, "authority_classification": "collector_proposed"})

        proposed_values = {semantic_sha256(row["proposed_value"]) for row in inspection["observations"]}
        observation_sources = {
            (row["source"]["capture_manifest_path"], row["source"]["capture_result_id"])
            for row in inspection["observations"]
        }
        if status == "proven" and len(proposed_values) != 1:
            raise InvalidProposal("proven inspection must contain exactly one proposed value")
        if status == "conflicted" and (len(proposed_values) < 2 or len(observation_sources) < 2):
            raise InvalidProposal("conflicted inspection requires distinct sources and proposed values")

        if field["value_type"] == "string_list":
            if "enumeration_scope" not in inspection:
                raise InvalidProposal("list field requires enumeration_scope")
            truncated = any(captures[ref].get("excerpt", {}).get("truncated", False) for ref in refs if captures[ref]["state"] == "captured")
            captured_text = "\n".join(
                contained(root, str(Path(ref[0]).parent / captures[ref]["excerpt"]["path"])).read_text(encoding="utf-8")
                for ref in refs if captures[ref]["state"] == "captured"
            )
            folded_capture = normalize(captured_text, "text_casefold")
            if any(normalize(item, "text_casefold") not in folded_capture for item in inspection["enumeration_scope"]["captured_enumerands"]):
                raise InvalidProposal("captured_enumerand is absent from bound excerpts")
            remains_unproven |= validate_enumeration(inspection["enumeration_scope"], inspection["observations"], truncated)
        elif "enumeration_scope" in inspection:
            raise InvalidProposal("enumeration_scope is allowed only for list fields")
        remains_unproven |= status != "proven"
        output_inspections.append({**inspection, "observations": output_observations})

    missing = expected_slots - seen
    if missing:
        raise InvalidProposal(f"missing entity-field inspections: {len(missing)}")
    if len(seen) != len(expected_slots):
        raise InvalidProposal("inspection coverage differs from frozen query pack")

    counts = {name: sum(row["inspection_status"] == name for row in output_inspections) for name in ("proven", "conflicted", "does_not_establish", "not_inspected")}
    execution = {
        "format_version": "collector-execution-1.2",
        "run_id": proposal["run_id"],
        "execution_instance_id": proposal["execution_instance_id"],
        "authority_classification": "collector_proposed",
        "query_pack": proposal["query_pack"],
        "protocol": proposal["protocol"],
        "normalization_rules": proposal["normalization_rules"],
        "contract_schema": make_binding(root, OUTPUT_SCHEMA_REF),
        "capture_manifests": proposal["capture_manifests"],
        "collector": proposal["collector"],
        "inspections": output_inspections,
        "summary": {"total": len(output_inspections), **counts},
    }
    validate_schema(execution, read_json(contained(root, OUTPUT_SCHEMA_REF)), "execution")
    return execution, True  # proposal authority is necessarily unproven


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except Exception:
        try: os.unlink(temporary)
        except FileNotFoundError: pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--check", action="store_true", help="validate/render in memory without writing")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        root = args.root.resolve()
        proposal = read_json(contained(root, args.input))
        execution, _ = validate_and_build(root, proposal)
        output = contained(root, args.output, must_exist=args.check)
        payload = json.dumps(execution, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n"
        if args.check:
            if output.read_bytes() != payload:
                raise InvalidProposal("output is missing or stale")
        else:
            atomic_write(output, payload)
        result = {"status": "generated-provisional", "authority_classification": "collector_proposed", "inspections": execution["summary"]}
        print(json.dumps(result) if args.json else f"PASS — generated collector proposal ({execution['summary']['total']} slots; no authority promotion)")
        return 0
    except InvalidProposal as exc:
        print(json.dumps({"status": "invalid", "error": str(exc)}) if args.json else f"FAIL — {exc}")
        return 1
    except (MissingDependency, OSError) as exc:
        print(json.dumps({"status": "unavailable", "error": str(exc)}) if args.json else f"UNPROVEN — {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
