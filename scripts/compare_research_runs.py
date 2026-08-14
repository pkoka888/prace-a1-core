#!/usr/bin/env python3
"""Validate and compare two Plan AC raw-lane collection runs.

The comparison measures reproducibility without treating agreement as truth.
Both runs are converted to provisional v1.2 envelopes and validated before any
metric is emitted. Exit 0 means both runs are structurally comparable, 1 means
deterministic invalidity, and 2 means an input/environment is unavailable.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
LANES = [
    "oss_invoice",
    "czech_invoice_software",
    "czech_accounting_firms",
    "czech_individual",
    "studies_comprehensive",
]


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"missing input: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}: {exc}") from exc


def load_run(raw_dir: Path, base: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    entities: list[dict[str, Any]] = []
    evidence: list[dict[str, Any]] = []
    seen_entities: set[str] = set()
    seen_evidence: set[str] = set()
    lane_counts: dict[str, int] = {}

    for lane in LANES:
        payload = load_json(raw_dir / f"{lane}.json")
        if payload.get("lane") != lane:
            raise ValueError(f"{lane}: lane metadata mismatch")
        records = payload.get("records")
        lane_evidence = payload.get("evidence", [])
        if not isinstance(records, list) or not isinstance(lane_evidence, list):
            raise ValueError(f"{lane}: records/evidence must be arrays")
        lane_counts[lane] = len(records)
        lane_entity_ids: set[str] = set()
        for entity in records:
            if not isinstance(entity, dict) or not entity.get("id"):
                raise ValueError(f"{lane}: invalid entity record")
            entity_id = entity["id"]
            if entity.get("cohort") != lane:
                raise ValueError(f"{entity_id}: cohort does not match lane {lane}")
            if entity_id in seen_entities:
                raise ValueError(f"duplicate entity id: {entity_id}")
            seen_entities.add(entity_id)
            lane_entity_ids.add(entity_id)
            entities.append(entity)
        for item in lane_evidence:
            if not isinstance(item, dict) or not item.get("id"):
                raise ValueError(f"{lane}: invalid evidence record")
            if item["id"] in seen_evidence:
                raise ValueError(f"duplicate evidence id: {item['id']}")
            if item.get("entity_id") not in lane_entity_ids:
                raise ValueError(f"{item['id']}: orphan or cross-lane evidence")
            seen_evidence.add(item["id"])
            evidence.append(item)

    candidate = dict(base)
    candidate.update({
        "run_id": f"research-ac-comparison-{raw_dir.name.lower().replace('_', '-')}",
        "run_status": "schema_valid",
        "entities": entities,
        "evidence": evidence,
        "reviews": [],
    })
    try:
        from scripts.validate_research_schema import validate_envelope
    except Exception:
        sys.path.insert(0, str(ROOT))
        from scripts.validate_research_schema import validate_envelope
    ok, detail, _ = validate_envelope(ROOT, candidate)
    if not ok:
        raise ValueError(f"{raw_dir}: {detail}")
    return candidate, lane_counts


def stable_value(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def canonical_pack_hash(pack: dict[str, Any]) -> str:
    candidate = dict(pack)
    candidate.pop("query_pack_hash", None)
    encoded = stable_value(candidate).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def parsed_time(value: str, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label}: invalid RFC3339 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{label}: timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def url_within_root(url: str, root: str) -> bool:
    """Match an exact HTTPS origin and a path root on segment boundaries."""
    candidate, allowed = urlsplit(url), urlsplit(root)
    if (candidate.scheme.lower(), candidate.hostname, candidate.port) != (
        allowed.scheme.lower(), allowed.hostname, allowed.port
    ):
        return False
    allowed_path = allowed.path.rstrip("/")
    candidate_path = candidate.path.rstrip("/")
    return not allowed_path or candidate_path == allowed_path or candidate_path.startswith(allowed_path + "/")


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def render_json(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def validate_json_schema(instance: Any, schema: dict[str, Any], label: str) -> None:
    try:
        from jsonschema import Draft7Validator, FormatChecker
    except ImportError as exc:
        raise RuntimeError("jsonschema dependency unavailable") from exc
    errors = sorted(
        Draft7Validator(schema, format_checker=FormatChecker()).iter_errors(instance),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        error = errors[0]
        location = ".".join(str(part) for part in error.absolute_path) or "<root>"
        raise ValueError(f"{label}: {location}: {error.message}")


def load_query_pack(root: Path, path: Path) -> dict[str, Any]:
    pack = load_json(path)
    schema_name = (
        "atomic-query-pack-1.1.schema.json"
        if pack.get("result_format_version") == "atomic-results-1.1"
        else "atomic-query-pack.schema.json"
    )
    schema = load_json(root / f"research/query-packs/{schema_name}")
    validate_json_schema(pack, schema, "query pack")
    actual = canonical_pack_hash(pack)
    if pack["query_pack_hash"] != actual:
        raise ValueError(
            f"query pack hash mismatch: declared {pack['query_pack_hash']}, calculated {actual}"
        )
    if pack.get("result_format_version") == "atomic-results-1.1":
        starts = parsed_time(pack["capture_window"]["starts_at"], "capture_window.starts_at")
        ends = parsed_time(pack["capture_window"]["ends_at"], "capture_window.ends_at")
        if ends < starts:
            raise ValueError("query pack capture window ends before it starts")
    roster_owner: dict[str, str] = {}
    for lane, definition in pack["lanes"].items():
        field_ids = [field["id"] for field in definition["fields"]]
        if len(field_ids) != len(set(field_ids)):
            raise ValueError(f"query pack {lane}: duplicate field id")
        entities = definition.get("entities")
        entity_ids = (
            [entity["id"] for entity in entities]
            if entities is not None
            else definition["expected_entity_ids"]
        )
        if len(entity_ids) != len(set(entity_ids)):
            raise ValueError(f"query pack {lane}: duplicate entity id")
        if entities is not None:
            roots = [entity["canonical_root_url"] for entity in entities]
            if len(roots) != len(set(roots)):
                raise ValueError(f"query pack {lane}: duplicate canonical root URL")
            try:
                from scripts.check_evidence_url import UnsafeURL, validate_public_https_url
            except ImportError:
                from check_evidence_url import UnsafeURL, validate_public_https_url
            for entity in entities:
                root_url = entity["canonical_root_url"]
                try:
                    validate_public_https_url(root_url)
                except UnsafeURL as exc:
                    raise ValueError(f"query pack {lane}: unsafe canonical root URL: {exc}") from exc
                official_roots = entity["allowed_official_source_roots"]
                if root_url not in official_roots:
                    raise ValueError(f"query pack {lane}/{entity['id']}: canonical root is not an allowed official root")
                for official_root in official_roots:
                    try:
                        validate_public_https_url(official_root)
                    except UnsafeURL as exc:
                        raise ValueError(
                            f"query pack {lane}/{entity['id']}: unsafe official source root: {exc}"
                        ) from exc
        for entity_id in entity_ids:
            if entity_id in roster_owner:
                raise ValueError(
                    f"query pack entity {entity_id} belongs to both {roster_owner[entity_id]} and {lane}"
                )
            roster_owner[entity_id] = lane
    return pack


def value_matches_type(value: Any, value_type: str) -> bool:
    if value_type == "boolean":
        return isinstance(value, bool)
    if value_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if value_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if value_type == "date":
        if not isinstance(value, str):
            return False
        try:
            date.fromisoformat(value)
        except ValueError:
            return False
        return True
    if value_type == "string":
        return isinstance(value, str) and bool(value)
    if value_type == "string_list":
        return isinstance(value, list) and all(isinstance(item, str) and item for item in value)
    return False


def validate_pricing(value: Any, label: str) -> None:
    if not isinstance(value, dict):
        raise ValueError(f"{label}: pricing value must be structured")
    status = value["disclosure_status"]
    tiers = value["tiers"]
    normalized_names = [tier["name"].strip().casefold() for tier in tiers]
    if len(normalized_names) != len(set(normalized_names)):
        raise ValueError(f"{label}: pricing tier names collide after normalization")
    if status in {"public_exact", "public_from"}:
        if not value["currency"] or not tiers:
            raise ValueError(f"{label}: public pricing requires currency and at least one tier")
        if status == "public_exact" and any(tier["amount"] is None for tier in tiers):
            raise ValueError(f"{label}: public_exact pricing requires every tier amount")
        if status == "public_from" and not any(tier["amount"] is not None for tier in tiers):
            raise ValueError(f"{label}: public_from pricing requires a documented amount")
    else:
        if value["currency"] is not None or tiers:
            raise ValueError(f"{label}: non-exact/custom pricing cannot carry invented currency or tiers")


def load_atomic_results(
    root: Path, path: Path, pack: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, dict[str, dict[str, Any]]]]:
    payload = load_json(path)
    is_v11 = pack["result_format_version"] == "atomic-results-1.1"
    schema_name = "atomic-results-1.1.schema.json" if is_v11 else "atomic-results-1.0.schema.json"
    schema = load_json(root / f"research/query-packs/{schema_name}")
    validate_json_schema(payload, schema, path.name)
    if payload["format_version"] != pack["result_format_version"]:
        raise ValueError(f"{path.name}: unsupported result format version")
    if payload["query_pack_version"] != pack["query_pack_version"]:
        raise ValueError(f"{path.name}: query pack version mismatch")
    if payload["query_pack_hash"] != pack["query_pack_hash"]:
        raise ValueError(f"{path.name}: query pack hash mismatch")
    if is_v11:
        provenance = payload["provenance"]
        if provenance["source_policy_version"] != pack["source_policy_version"]:
            raise ValueError(f"{path.name}: source policy version mismatch")
        started = parsed_time(provenance["started_at"], f"{path.name}: started_at")
        completed = parsed_time(provenance["completed_at"], f"{path.name}: completed_at")
        if completed < started:
            raise ValueError(f"{path.name}: completed_at precedes started_at")
        window_start = parsed_time(pack["capture_window"]["starts_at"], "capture_window.starts_at")
        window_end = parsed_time(pack["capture_window"]["ends_at"], "capture_window.ends_at")
        if not (window_start <= started <= completed <= window_end):
            raise ValueError(f"{path.name}: collection timestamps fall outside the frozen capture window")
        as_of = date.fromisoformat(payload["as_of"])
        if not (window_start.date() <= as_of <= window_end.date()):
            raise ValueError(f"{path.name}: as_of falls outside the frozen capture window")

    vocab = {key: set(values) for key, values in pack["vocabularies"].items()}
    entity_definitions = {
        (lane_name, entity["id"]): entity
        for lane_name, lane_definition in pack["lanes"].items()
        for entity in lane_definition.get("entities", [])
    }
    evidence_by_id: dict[str, dict[str, Any]] = {}
    try:
        from scripts.check_evidence_url import UnsafeURL, validate_public_https_url
    except ImportError:
        try:
            from check_evidence_url import UnsafeURL, validate_public_https_url
        except ImportError as exc:
            raise RuntimeError("offline public-URL validator unavailable") from exc
    for item in payload["evidence"]:
        evidence_id = item["id"]
        if evidence_id in evidence_by_id:
            raise ValueError(f"{path.name}: duplicate evidence id {evidence_id}")
        if item["evidence_class"] not in vocab["evidence_class"]:
            raise ValueError(f"{path.name}: unknown evidence_class for {evidence_id}")
        if item["verification_status"] not in vocab["verification_status"]:
            raise ValueError(f"{path.name}: unknown evidence verification_status for {evidence_id}")
        try:
            validate_public_https_url(item["url"])
        except UnsafeURL as exc:
            raise ValueError(f"{path.name}: unsafe evidence URL for {evidence_id}: {exc}") from exc
        if is_v11:
            retrieved = parsed_time(item["retrieved_at"], f"{path.name}: {evidence_id}.retrieved_at")
            if not (started <= retrieved <= completed):
                raise ValueError(f"{path.name}: evidence {evidence_id} was retrieved outside the collection interval")
        evidence_by_id[evidence_id] = item

    by_entity: dict[str, dict[str, dict[str, Any]]] = {}
    entity_lane: dict[str, str] = {}
    for result in payload["results"]:
        entity_id, lane, field_id = result["entity_id"], result["lane"], result["field_id"]
        if is_v11 and (lane, entity_id) not in entity_definitions:
            raise ValueError(f"{path.name}: entity {entity_id} is not in frozen lane {lane}")
        if entity_id in entity_lane and entity_lane[entity_id] != lane:
            raise ValueError(f"{path.name}: entity {entity_id} appears in multiple lanes")
        entity_lane[entity_id] = lane
        if field_id in by_entity.setdefault(entity_id, {}):
            raise ValueError(f"{path.name}: duplicate result {entity_id}/{field_id}")
        fields = {field["id"]: field for field in pack["lanes"][lane]["fields"]}
        if field_id not in fields:
            raise ValueError(f"{path.name}: unknown field {lane}/{field_id}")
        if result["result_status"] not in vocab["result_status"]:
            raise ValueError(f"{path.name}: unknown result_status for {entity_id}/{field_id}")
        if result["verification_status"] not in vocab["verification_status"]:
            raise ValueError(f"{path.name}: unknown verification_status for {entity_id}/{field_id}")
        if result["applicability"] not in vocab["applicability"]:
            raise ValueError(f"{path.name}: unknown applicability for {entity_id}/{field_id}")
        if not is_v11:
            pricing_status = result["pricing_status"]
            if fields[field_id]["importance"] == "pricing":
                if pricing_status not in vocab["pricing_status"]:
                    raise ValueError(f"{path.name}: invalid pricing_status for {entity_id}/{field_id}")
            elif pricing_status is not None:
                raise ValueError(f"{path.name}: pricing_status is only valid for pricing fields")

        if result["result_status"] in {"unproven", "not_applicable"}:
            if result["value"] is not None:
                raise ValueError(f"{path.name}: {result['result_status']} result must have null value")
        elif result["result_status"] == "conflicted" and result["value"] is None:
            pass
        elif fields[field_id]["value_type"] != "pricing" and not value_matches_type(result["value"], fields[field_id]["value_type"]):
            raise ValueError(f"{path.name}: wrong value type for {entity_id}/{field_id}")
        if is_v11:
            field = fields[field_id]
            if result["result_status"] == "not_applicable" and not field["not_applicable_allowed"]:
                raise ValueError(f"{path.name}: not_applicable is forbidden for {entity_id}/{field_id}")
            if result["result_status"] in {"proven", "conflicted"}:
                allowed = field.get("allowed_values")
                if allowed:
                    submitted = result["value"] if isinstance(result["value"], list) else [result["value"]]
                    unknown = sorted(set(submitted) - set(allowed))
                    if unknown:
                        raise ValueError(f"{path.name}: unknown controlled value for {entity_id}/{field_id}: {', '.join(unknown)}")
                if field.get("requires_enumeration_scope") and result["enumeration_scope"] == "not_applicable":
                    raise ValueError(f"{path.name}: enumeration scope required for {entity_id}/{field_id}")
            if field["comparison_rule"] == "snapshot" and result["result_status"] == "proven" and not result.get("captured_at"):
                raise ValueError(f"{path.name}: snapshot lacks captured_at for {entity_id}/{field_id}")
            if result.get("captured_at"):
                captured = parsed_time(result["captured_at"], f"{path.name}: {entity_id}/{field_id}.captured_at")
                if not (started <= captured <= completed):
                    raise ValueError(f"{path.name}: snapshot capture falls outside the collection interval for {entity_id}/{field_id}")
        if result["result_status"] == "proven" and fields[field_id]["evidence_required"] and not result["evidence_refs"]:
            raise ValueError(f"{path.name}: proven result lacks evidence for {entity_id}/{field_id}")
        linked_evidence: list[dict[str, Any]] = []
        for evidence_id in result["evidence_refs"]:
            item = evidence_by_id.get(evidence_id)
            if item is None:
                raise ValueError(f"{path.name}: dangling evidence ref {evidence_id}")
            if item["entity_id"] != entity_id or item["field_id"] != field_id:
                raise ValueError(f"{path.name}: evidence ownership mismatch for {evidence_id}")
            linked_evidence.append(item)
        if is_v11:
            entity_definition = entity_definitions[(lane, entity_id)]
            allowed_roots = entity_definition["allowed_official_source_roots"]
            for item in linked_evidence:
                is_official_root = any(url_within_root(item["url"], root_url) for root_url in allowed_roots)
                if item["evidence_class"] in {"official_primary", "official_secondary", "repository_metadata"} and not is_official_root:
                    raise ValueError(
                        f"{path.name}: {item['evidence_class']} evidence is outside the frozen official roots for {entity_id}: {item['id']}"
                    )
                if item["evidence_class"] in {"independent_primary", "independent_secondary"} and is_official_root:
                    raise ValueError(
                        f"{path.name}: official-root evidence cannot masquerade as independent for {entity_id}: {item['id']}"
                    )
        if result["result_status"] == "proven":
            if result["verification_status"] != "verified":
                raise ValueError(f"{path.name}: proven result is not verified for {entity_id}/{field_id}")
            if not any(item["verification_status"] == "verified" for item in linked_evidence):
                raise ValueError(f"{path.name}: proven result lacks verified evidence for {entity_id}/{field_id}")
        if is_v11 and result["result_status"] == "conflicted":
            verified = [item for item in linked_evidence if item["verification_status"] == "verified"]
            if len(verified) < 2:
                raise ValueError(f"{path.name}: conflicted result requires two verified evidence records for {entity_id}/{field_id}")
            if result["verification_status"] != "verified":
                raise ValueError(f"{path.name}: conflicted result must have verified status for {entity_id}/{field_id}")
            if len({item["url"] for item in verified}) < 2:
                raise ValueError(f"{path.name}: conflicted result requires distinct verified evidence URLs for {entity_id}/{field_id}")
            if not result.get("notes") or any(not item.get("locator") for item in verified):
                raise ValueError(f"{path.name}: conflicted result requires conflict notes and evidence locators for {entity_id}/{field_id}")
        if is_v11:
            confidence = result["claim_confidence"]
            expected_terminal = {
                "unproven": "unproven", "conflicted": "conflicted",
                "not_applicable": "not_applicable",
            }.get(result["result_status"])
            if expected_terminal and confidence != expected_terminal:
                raise ValueError(
                    f"{path.name}: {result['result_status']} result requires claim_confidence={expected_terminal} for {entity_id}/{field_id}"
                )
            if result["result_status"] == "proven":
                if confidence not in {
                    "source_verified_self_reported", "independently_corroborated",
                    "repository_metadata_verified",
                }:
                    raise ValueError(f"{path.name}: proven result has invalid claim confidence for {entity_id}/{field_id}")
                verified_classes = {
                    item["evidence_class"] for item in linked_evidence
                    if item["verification_status"] == "verified"
                }
                if confidence == "source_verified_self_reported" and not verified_classes.intersection({"official_primary", "official_secondary"}):
                    raise ValueError(f"{path.name}: self-reported confidence lacks verified official evidence for {entity_id}/{field_id}")
                if confidence == "independently_corroborated" and not verified_classes.intersection({"independent_primary", "independent_secondary"}):
                    raise ValueError(f"{path.name}: corroborated confidence lacks verified independent evidence for {entity_id}/{field_id}")
                if confidence == "repository_metadata_verified" and "repository_metadata" not in verified_classes:
                    raise ValueError(f"{path.name}: repository confidence lacks verified metadata evidence for {entity_id}/{field_id}")
            if field["comparison_rule"] == "pricing" and result["result_status"] in {"proven", "conflicted"}:
                validate_pricing(result["value"], f"{path.name}: {entity_id}/{field_id}")
        by_entity[entity_id][field_id] = result

    if not by_entity:
        raise ValueError(f"{path.name}: atomic results contain no entities")
    for entity_id, fields in by_entity.items():
        lane = entity_lane[entity_id]
        required = {field["id"] for field in pack["lanes"][lane]["fields"]}
        missing = sorted(required - set(fields))
        if missing:
            raise ValueError(f"{path.name}: {entity_id} missing required fields: {', '.join(missing)}")
    for lane, definition in pack["lanes"].items():
        actual = {entity_id for entity_id, actual_lane in entity_lane.items() if actual_lane == lane}
        expected = {
            entity["id"] for entity in definition["entities"]
        } if "entities" in definition else set(definition["expected_entity_ids"])
        missing_entities = sorted(expected - actual)
        unexpected_entities = sorted(actual - expected)
        if missing_entities or unexpected_entities:
            detail = []
            if missing_entities:
                detail.append(f"missing entities: {', '.join(missing_entities)}")
            if unexpected_entities:
                detail.append(f"unexpected entities: {', '.join(unexpected_entities)}")
            raise ValueError(f"{path.name}: {lane} roster mismatch ({'; '.join(detail)})")
    used_evidence = {ref for fields in by_entity.values() for result in fields.values() for ref in result["evidence_refs"]}
    unused = sorted(set(evidence_by_id) - used_evidence)
    if unused:
        raise ValueError(f"{path.name}: unreferenced evidence ids: {', '.join(unused)}")
    return payload, by_entity


def normalized_atomic_value(result: dict[str, Any], rule: str) -> Any:
    value = result["value"]
    if rule == "normalized_set" and isinstance(value, list):
        value = sorted({item.strip().casefold() for item in value})
    return {
        "result_status": result["result_status"],
        "value": value,
        "applicability": result["applicability"],
        "pricing_status": result["pricing_status"] if rule == "pricing" else None,
    }


def compare_atomic(
    left: dict[str, dict[str, dict[str, Any]]],
    right: dict[str, dict[str, dict[str, Any]]],
    pack: dict[str, Any],
) -> dict[str, Any]:
    common = sorted(set(left) & set(right))
    report: dict[str, Any] = {
        "left_entity_count": len(left),
        "right_entity_count": len(right),
        "common_entity_count": len(common),
        "left_only_ids": sorted(set(left) - set(right)),
        "right_only_ids": sorted(set(right) - set(left)),
        "critical": {"compared": 0, "agreed": 0, "disagreements": [], "unresolved": []},
        "noncritical": {"compared": 0, "agreed": 0, "disagreements": [], "unresolved": []},
        "pricing": {"compared": 0, "agreed": 0, "disagreements": [], "unresolved": []},
    }
    for entity_id in common:
        left_lane = next(lane for lane, definition in pack["lanes"].items() if set(left[entity_id]) == {field["id"] for field in definition["fields"]})
        right_lane = next(lane for lane, definition in pack["lanes"].items() if set(right[entity_id]) == {field["id"] for field in definition["fields"]})
        if left_lane != right_lane:
            raise ValueError(f"entity {entity_id} has different lanes across runs")
        for field in pack["lanes"][left_lane]["fields"]:
            bucket = field["importance"]
            lv = normalized_atomic_value(left[entity_id][field["id"]], field["comparison_rule"])
            rv = normalized_atomic_value(right[entity_id][field["id"]], field["comparison_rule"])
            section = report[bucket]
            section["compared"] += 1
            if left[entity_id][field["id"]]["result_status"] != "proven" or right[entity_id][field["id"]]["result_status"] != "proven":
                section["unresolved"].append({
                    "entity_id": entity_id,
                    "field_id": field["id"],
                    "left_status": left[entity_id][field["id"]]["result_status"],
                    "right_status": right[entity_id][field["id"]]["result_status"],
                })
            if lv == rv:
                section["agreed"] += 1
            else:
                section["disagreements"].append({"entity_id": entity_id, "field_id": field["id"], "left": lv, "right": rv})
    for bucket in ("critical", "noncritical", "pricing"):
        section = report[bucket]
        section["agreement"] = round(section["agreed"] / section["compared"], 4) if section["compared"] else None
    report["critical_gate_passed"] = (
        not report["critical"]["disagreements"]
        and not report["critical"]["unresolved"]
        and not report["left_only_ids"]
        and not report["right_only_ids"]
    )
    return report


def _normalized_set(value: Any) -> list[str]:
    return sorted({item.strip().casefold() for item in value})


def _normalized_pricing(value: dict[str, Any]) -> dict[str, Any]:
    """Normalize structured price facts; free-text notes are never compared."""
    normalized = {key: value[key] for key in (
        "disclosure_status", "currency", "vat_status", "billing_period", "unit"
    )}
    normalized["tiers"] = sorted(
        [
            {
                "name": tier["name"].strip().casefold(),
                "amount": tier["amount"],
                "included_units": tier["included_units"],
                "overage_amount": tier["overage_amount"],
            }
            for tier in value["tiers"]
        ],
        key=lambda tier: (tier["name"], stable_value(tier)),
    )
    return normalized


def _pricing_relation(left: dict[str, Any], right: dict[str, Any]) -> str:
    """Return match, coverage, or conflict for two structured pricing claims."""
    left = _normalized_pricing(left)
    right = _normalized_pricing(right)
    for key in ("disclosure_status", "currency", "vat_status", "billing_period", "unit"):
        if left[key] != right[key]:
            return "conflict"
    lm = {tier["name"]: tier for tier in left["tiers"]}
    rm = {tier["name"]: tier for tier in right["tiers"]}
    for name in set(lm) & set(rm):
        if lm[name] != rm[name]:
            return "conflict"
    return "match" if lm == rm else "coverage"


def _v11_relation(left: dict[str, Any], right: dict[str, Any], field: dict[str, Any]) -> tuple[str, str | None]:
    """Classify one slot into exactly one primary outcome plus optional representation drift."""
    ls, rs = left["result_status"], right["result_status"]
    representation = "applicability" if left["applicability"] != right["applicability"] else None
    if ls == rs == "unproven":
        return "both_unproven", representation
    if "unproven" in {ls, rs}:
        return "coverage_difference", representation
    if ls == rs == "not_applicable":
        return "resolved_not_applicable", representation
    if "not_applicable" in {ls, rs}:
        return "semantic_conflict", representation
    if "conflicted" in {ls, rs}:
        return "semantic_conflict", representation
    rule = field["comparison_rule"]
    if rule == "snapshot":
        return ("semantic_match" if left["value"] == right["value"] else "snapshot_drift"), representation
    if rule == "normalized_set":
        lv, rv = _normalized_set(left["value"]), _normalized_set(right["value"])
        if lv == rv:
            return "semantic_match", representation
        if "partial" in {left["enumeration_scope"], right["enumeration_scope"]}:
            return "coverage_difference", representation
        return "semantic_conflict", representation
    if rule == "pricing":
        relation = _pricing_relation(left["value"], right["value"])
        return {
            "match": "semantic_match", "coverage": "coverage_difference", "conflict": "semantic_conflict"
        }[relation], representation
    return ("semantic_match" if left["value"] == right["value"] else "semantic_conflict"), representation


def compare_atomic_v11(
    left: dict[str, dict[str, dict[str, Any]]],
    right: dict[str, dict[str, dict[str, Any]]],
    pack: dict[str, Any],
) -> dict[str, Any]:
    left_ids, right_ids = set(left), set(right)
    common = sorted(left_ids & right_ids)
    outcome_names = (
        "semantic_match", "semantic_conflict", "coverage_difference", "both_unproven",
        "resolved_not_applicable", "snapshot_drift",
    )
    report: dict[str, Any] = {
        "left_entity_count": len(left), "right_entity_count": len(right),
        "common_entity_count": len(common), "left_only_ids": sorted(left_ids - right_ids),
        "right_only_ids": sorted(right_ids - left_ids),
    }
    for importance in ("critical", "noncritical", "pricing"):
        report[importance] = {
            "total_slots": 0, "both_resolved": 0, "unresolved_any": 0,
            "status_concordant": 0, "applicability_difference_count": 0,
            "confidence_difference_count": 0,
            **{name: 0 for name in outcome_names},
            "details": [], "representation_only": [], "confidence_differences": [],
        }
    entity_lane = {
        entity["id"]: lane
        for lane, definition in pack["lanes"].items()
        for entity in definition["entities"]
    }
    fields_by_lane = {
        lane: {field["id"]: field for field in definition["fields"]}
        for lane, definition in pack["lanes"].items()
    }
    for entity_id in common:
        lane = entity_lane[entity_id]
        for field_id, field in fields_by_lane[lane].items():
            lv, rv = left[entity_id][field_id], right[entity_id][field_id]
            section = report[field["importance"]]
            section["total_slots"] += 1
            section["status_concordant"] += lv["result_status"] == rv["result_status"]
            outcome, representation = _v11_relation(lv, rv, field)
            section[outcome] += 1
            if outcome in {"semantic_match", "semantic_conflict", "resolved_not_applicable", "snapshot_drift"}:
                section["both_resolved"] += 1
            else:
                section["unresolved_any"] += 1
            if outcome != "semantic_match":
                section["details"].append({
                    "entity_id": entity_id, "field_id": field_id, "outcome": outcome,
                    "left_status": lv["result_status"], "right_status": rv["result_status"],
                })
            if representation:
                section["applicability_difference_count"] += 1
                section["representation_only"].append({
                    "entity_id": entity_id, "field_id": field_id,
                    "left_applicability": lv["applicability"],
                    "right_applicability": rv["applicability"],
                })
            if lv["claim_confidence"] != rv["claim_confidence"]:
                section["confidence_difference_count"] += 1
                section["confidence_differences"].append({
                    "entity_id": entity_id, "field_id": field_id,
                    "left_confidence": lv["claim_confidence"],
                    "right_confidence": rv["claim_confidence"],
                })
    for importance in ("critical", "noncritical", "pricing"):
        section = report[importance]
        reconciled = sum(section[name] for name in outcome_names)
        if reconciled != section["total_slots"]:
            raise ValueError(f"internal {importance} outcome reconciliation failure")
        factual = section["semantic_match"] + section["semantic_conflict"]
        section["resolved_semantic_agreement"] = (
            round(section["semantic_match"] / factual, 4) if factual else None
        )
        section["independent_proven_coverage"] = round(
            (section["semantic_match"] + section["semantic_conflict"] + section["snapshot_drift"])
            / section["total_slots"], 4
        ) if section["total_slots"] else None
        section["status_concordance"] = round(
            section["status_concordant"] / section["total_slots"], 4
        ) if section["total_slots"] else None
    critical = report["critical"]
    report["structural_repeatability_passed"] = (
        not report["left_only_ids"] and not report["right_only_ids"]
        and critical["semantic_conflict"] == 0
        and critical["coverage_difference"] == 0
        and critical["both_unproven"] == 0
        and critical["applicability_difference_count"] == 0
        and critical["confidence_difference_count"] == 0
    )
    return report


def independence_report(left_payload: dict[str, Any], right_payload: dict[str, Any]) -> dict[str, Any]:
    left, right = left_payload["provenance"], right_payload["provenance"]
    dimensions = {
        "collector_id_distinct": left["collector_id"] != right["collector_id"],
        "execution_instance_id_distinct": left["execution_instance_id"] != right["execution_instance_id"],
        "collector_kind_distinct": left["collector_kind"] != right["collector_kind"],
        "provider_distinct": left.get("provider") != right.get("provider"),
        "model_distinct": left.get("model") != right.get("model"),
        "config_digest_equal": left["config_digest"] == right["config_digest"],
        "left_identity_attested": left["identity_verification"] == "operator_attested",
        "right_identity_attested": right["identity_verification"] == "operator_attested",
    }
    verified = all(dimensions[key] for key in (
        "collector_id_distinct", "execution_instance_id_distinct",
        "config_digest_equal", "left_identity_attested", "right_identity_attested",
    ))
    return {
        "verified": verified,
        "dimensions": dimensions,
        "note": "Distinct labels alone do not prove independence; both identities require operator attestation.",
    }


def critical_self_report_only(
    left: dict[str, dict[str, dict[str, Any]]],
    right: dict[str, dict[str, dict[str, Any]]],
    pack: dict[str, Any],
) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for lane, definition in pack["lanes"].items():
        critical_ids = sorted(
            field["id"] for field in definition["fields"] if field["importance"] == "critical"
        )
        for entity in definition["entities"]:
            entity_id = entity["id"]
            for field_id in critical_ids:
                if (
                    left[entity_id][field_id]["claim_confidence"] == "source_verified_self_reported"
                    and right[entity_id][field_id]["claim_confidence"] == "source_verified_self_reported"
                ):
                    result.append({"entity_id": entity_id, "field_id": field_id})
    return result


def claims(entity: dict[str, Any]) -> dict[str, str]:
    return {
        item["field"]: stable_value(item.get("value"))
        for item in entity.get("claims", [])
        if isinstance(item, dict) and item.get("field")
    }


def compare_lane(left: list[dict[str, Any]], right: list[dict[str, Any]]) -> dict[str, Any]:
    lm = {item["id"]: item for item in left}
    rm = {item["id"]: item for item in right}
    common = sorted(set(lm) & set(rm))
    union = set(lm) | set(rm)
    claim_total = claim_equal = pricing_equal = 0
    source_intersection = source_union = 0
    metric_differences: list[dict[str, Any]] = []

    for entity_id in common:
        lc, rc = claims(lm[entity_id]), claims(rm[entity_id])
        for field in sorted(set(lc) & set(rc)):
            claim_total += 1
            claim_equal += lc[field] == rc[field]
        pricing_equal += (
            lm[entity_id].get("pricing", {}).get("public_status")
            == rm[entity_id].get("pricing", {}).get("public_status")
        )
        ls, rs = set(lm[entity_id].get("source_links", [])), set(rm[entity_id].get("source_links", []))
        source_intersection += len(ls & rs)
        source_union += len(ls | rs)
        lg, rg = lm[entity_id].get("github_metrics", {}), rm[entity_id].get("github_metrics", {})
        changed = {
            key: {"left": lg.get(key), "right": rg.get(key)}
            for key in ("stars", "forks", "latest_release", "last_push", "license")
            if lg.get(key) != rg.get(key)
        }
        if changed:
            metric_differences.append({"entity_id": entity_id, "fields": changed})

    return {
        "left_count": len(lm),
        "right_count": len(rm),
        "common_ids": len(common),
        "entity_jaccard": round(len(common) / len(union), 4) if union else 1.0,
        "left_only_ids": sorted(set(lm) - set(rm)),
        "right_only_ids": sorted(set(rm) - set(lm)),
        "shared_claim_agreement": round(claim_equal / claim_total, 4) if claim_total else None,
        "shared_claims_compared": claim_total,
        "pricing_status_agreement": round(pricing_equal / len(common), 4) if common else None,
        "source_url_jaccard": round(source_intersection / source_union, 4) if source_union else None,
        "dynamic_github_differences": metric_differences,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--mode", choices=("raw", "atomic"), default="raw")
    parser.add_argument("--left-dir")
    parser.add_argument("--right-dir")
    parser.add_argument("--left-results")
    parser.add_argument("--right-results")
    parser.add_argument("--query-pack", default="research/query-packs/plan-ac-core-1.0.json")
    parser.add_argument("--base", default="research/processed/entities.json")
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--check", action="store_true",
        help="Read-only: recompute the report and require exact current output bytes",
    )
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    try:
        if args.mode == "raw":
            if not args.left_dir or not args.right_dir:
                raise ValueError("raw mode requires --left-dir and --right-dir")
            left_dir = (root / args.left_dir).resolve()
            right_dir = (root / args.right_dir).resolve()
            base = load_json((root / args.base).resolve())
            left, left_counts = load_run(left_dir, base)
            right, right_counts = load_run(right_dir, base)
            by_lane: dict[str, Any] = {}
            for lane in LANES:
                by_lane[lane] = compare_lane(
                    [e for e in left["entities"] if e["cohort"] == lane],
                    [e for e in right["entities"] if e["cohort"] == lane],
                )
            report = {
                "comparison_version": "1.0",
                "mode": "legacy_raw",
                "left_dir": str(left_dir.relative_to(root)),
                "right_dir": str(right_dir.relative_to(root)),
                "left_counts": left_counts,
                "right_counts": right_counts,
                "lanes": by_lane,
                "interpretation": "Agreement measures repeatability, not factual correctness.",
            }
        else:
            if not args.left_results or not args.right_results:
                raise ValueError("atomic mode requires --left-results and --right-results")
            pack_path = (root / args.query_pack).resolve()
            left_path = (root / args.left_results).resolve()
            right_path = (root / args.right_results).resolve()
            for label, path in (("query pack", pack_path), ("left results", left_path), ("right results", right_path)):
                if root != path and root not in path.parents:
                    raise ValueError(f"{label} must remain inside project root")
            pack = load_query_pack(root, pack_path)
            left_payload, left = load_atomic_results(root, left_path, pack)
            right_payload, right = load_atomic_results(root, right_path, pack)
            is_v11 = pack["result_format_version"] == "atomic-results-1.1"
            if left_payload["run_id"] == right_payload["run_id"]:
                raise ValueError("independent comparisons require distinct run_id values")
            if is_v11 and left_payload["as_of"] != right_payload["as_of"]:
                raise ValueError("v1.1 reproducibility comparison requires the same frozen as_of date")
            comparison = compare_atomic_v11(left, right, pack) if is_v11 else compare_atomic(left, right, pack)
            if is_v11:
                independence = independence_report(left_payload, right_payload)
                self_report_only = critical_self_report_only(left, right, pack)
                comparison["independence"] = independence
                comparison["critical_self_report_only"] = self_report_only
                comparison["operator_acceptance"] = "not_evaluated"
                comparison["acceptance_signal_passed"] = (
                    comparison["structural_repeatability_passed"]
                    and independence["verified"]
                    and not self_report_only
                )
            report = {
                "comparison_version": "2.2" if is_v11 else "2.0",
                "mode": "atomic",
                "query_pack_version": pack["query_pack_version"],
                "query_pack_hash": pack["query_pack_hash"],
                "left_run_id": left_payload["run_id"],
                "right_run_id": right_payload["run_id"],
                "left_as_of": left_payload["as_of"],
                "right_as_of": right_payload["as_of"],
                "comparison": comparison,
                "interpretation": (
                    "v1.1 reports structural repeatability and independently attested provenance dimensions; operator acceptance remains a separate bound review."
                    if is_v11 else
                    "Agreement measures repeatability, not factual correctness; critical_gate_passed is not research acceptance."
                ),
            }
            if is_v11:
                report["input_bindings"] = {
                    "query_pack": {
                        "path": pack_path.relative_to(root).as_posix(),
                        "file_sha256": file_sha256(pack_path),
                        "semantic_hash": pack["query_pack_hash"],
                    },
                    "left_results": {
                        "path": left_path.relative_to(root).as_posix(),
                        "sha256": file_sha256(left_path),
                    },
                    "right_results": {
                        "path": right_path.relative_to(root).as_posix(),
                        "sha256": file_sha256(right_path),
                    },
                }
        output = (root / args.output).resolve()
        if root != output and root not in output.parents:
            raise ValueError("output must remain inside project root")
        protected_inputs = ({pack_path, left_path, right_path} if args.mode == "atomic" else {left_dir, right_dir, (root / args.base).resolve()})
        if output in protected_inputs or any(path.is_dir() and path in output.parents for path in protected_inputs):
            raise ValueError("output cannot overwrite or be placed inside a comparison input")
        expected = render_json(report)
        if args.check:
            try:
                actual = output.read_bytes()
            except FileNotFoundError as exc:
                raise ValueError(f"comparison output is missing: {output}") from exc
            if actual != expected:
                raise ValueError("comparison output is stale or does not match its bound inputs")
            action = "current"
        else:
            atomic_write_json(output, report)
            action = "written"
        summary = {"result": "pass", "action": action, "output": str(output), "mode": args.mode}
        if args.mode == "raw":
            summary["lanes"] = len(report["lanes"])
        else:
            if is_v11:
                summary["structural_repeatability_passed"] = report["comparison"]["structural_repeatability_passed"]
                summary["independence_verified"] = report["comparison"]["independence"]["verified"]
                summary["acceptance_signal_passed"] = report["comparison"]["acceptance_signal_passed"]
            else:
                summary["critical_gate_passed"] = report["comparison"]["critical_gate_passed"]
        print(json.dumps(summary))
        return 0
    except RuntimeError as exc:
        print(f"UNPROVEN: {exc}", file=sys.stderr)
        return 2
    except (ValueError, OSError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
