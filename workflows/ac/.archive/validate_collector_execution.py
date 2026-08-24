#!/usr/bin/env python3
"""Read-only validator for a Plan AC collector-execution v1.1 manifest.

Exit 0: valid and every frozen slot is proven or evidenced as conflicted.
Exit 1: invalid contract, binding, source, or inspection.
Exit 2: valid execution, but at least one frozen slot remains unproven.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CANONICAL_QUERY_PACK = "research/query-packs/plan-ac-core-1.1.json"
CANONICAL_PROTOCOL = "research/query-packs/plan-ac-collector-protocol-1.1.json"
CANONICAL_PROTOCOL_SCHEMA = "research/query-packs/collector-protocol-1.1.schema.json"
CANONICAL_SCHEMA = "research/query-packs/collector-execution-1.1.schema.json"
CAPTURE_RESULT_SCHEMA = "research/query-packs/source-capture-result-1.1.schema.json"
CANONICAL_FIXTURE_RUNNER = "scripts/run_collector_fixture.py"
CANONICAL_FIXTURE_SET = "research/acquisition/synthetic-mini-pilot/fixture-set.json"
SYNTHETIC_MARKER = "SYNTHETIC_PLAN_AC_MINI_PILOT_DO_NOT_USE_AS_MARKET_EVIDENCE"
CANONICAL_FIXTURE_DIGEST = "236e6fc3bc6f1ec78c8e7b36cbc41aa25a186e2f93851b6ad84a1a62af442e05"
DENIED_TOP_LEVEL = {
    "a1", "scans", "evidence", "ocr", "data", "output", "runtime",
    "secrets", ".history-remediation",
}


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"missing file: {path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read JSON {path}: {exc}") from exc


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def semantic_sha256(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def resolve_ref(root: Path, ref: str) -> Path:
    candidate = (root / ref).resolve()
    try:
        relative = candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"reference escapes project root: {ref}") from exc
    if not relative.parts or relative.parts[0] in DENIED_TOP_LEVEL or relative.name == ".env":
        raise ValueError(f"sensitive or runtime reference is denied: {ref}")
    if not candidate.is_file():
        raise RuntimeError(f"referenced file is unavailable: {ref}")
    return candidate


def parse_time(value: str, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label}: invalid RFC3339 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{label}: timezone is required")
    return parsed.astimezone(timezone.utc)


def validate_schema(instance: Any, schema: dict[str, Any]) -> None:
    try:
        from jsonschema import Draft7Validator, FormatChecker
    except ImportError as exc:
        raise RuntimeError("jsonschema dependency unavailable") from exc
    errors = sorted(
        Draft7Validator(schema, format_checker=FormatChecker()).iter_errors(instance),
        key=lambda item: tuple(str(part) for part in item.absolute_path),
    )
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path) or "<root>"
        raise ValueError(f"schema {location}: {first.message}")


def within_allowed_root(url: str, root_url: str) -> bool:
    try:
        from scripts.compare_research_runs import url_within_root
    except ImportError:
        from compare_research_runs import url_within_root
    return url_within_root(url, root_url)


def validate_binding(root: Path, binding: dict[str, str], *, semantic: bool) -> Any:
    path = resolve_ref(root, binding["path"])
    actual = sha256_file(path)
    if actual != binding["byte_sha256"]:
        raise ValueError(f"{binding['path']}: byte hash mismatch")
    if semantic:
        value = load_json(path)
        actual_semantic = semantic_sha256(value)
        if actual_semantic != binding["semantic_sha256"]:
            raise ValueError(f"{binding['path']}: semantic hash mismatch")
        return value
    return path


GENERIC_LOCATORS = {
    "title", "page title", "homepage", "home page", "header", "main page",
    "website", "web page", "page", "document", "readme", "pricing page",
}


def _bounded_phrase(text: str, phrase: str) -> bool:
    """Match text tokens, allowing sentence dots but not dotted identifiers.

    A trailing ``.`` is punctuation when followed by whitespace/end, while
    ``CSV.xlsx`` remains one dotted identifier. The symmetric lookbehind also
    rejects matching ``CSV`` inside ``format.CSV``.
    """
    pattern = (
        rf"(?<![\w-])(?<!\w\.){re.escape(phrase.casefold())}"
        rf"(?![\w-])(?!\.\w)"
    )
    return re.search(pattern, text.casefold()) is not None


def _identifier_phrase(value: str) -> str:
    return " ".join(value.casefold().replace("_", " ").split())


def _decimal_tokens(text: str) -> list[Decimal]:
    values: list[Decimal] = []
    for token in re.findall(r"(?<!\w)[-+]?\d+(?:[.,]\d+)?(?!\w)", text):
        try:
            values.append(Decimal(token.replace(",", ".")))
        except InvalidOperation:
            pass
    return values


def typed_lexical_support_matches(text: str, value: Any, value_type: str,
                                  field_id: str | None = None) -> bool:
    """Reject typed proposals with no deterministic lexical anchor in evidence.

    This is deliberately a necessary, not sufficient, support test. Semantic
    correctness remains collector-proposed until fixture or operator review.
    """
    folded = " ".join(text.casefold().split())
    if value_type == "boolean":
        positive = ("true", "supports", "supported", "available", "enabled", "includes", "ano")
        negative = ("false", "unsupported", "unavailable", "disabled", "cannot", "does not", "ne")
        return any(_bounded_phrase(folded, marker) for marker in (positive if value else negative))
    if value_type == "integer":
        return Decimal(value) in _decimal_tokens(folded)
    if value_type == "date":
        return _bounded_phrase(folded, str(value))
    if value_type == "string":
        if field_id == "license_spdx":
            return _bounded_phrase(folded, value)
        phrase = _identifier_phrase(value)
        return bool(phrase) and _bounded_phrase(folded, phrase)
    if value_type == "string_list":
        return bool(value) and all(_bounded_phrase(folded, _identifier_phrase(item)) for item in value)
    if value_type == "pricing":
        disclosure_phrases = {
            "public_exact": ("public exact", "exact price"),
            "public_from": ("public from", "from price", "starting at"),
            "public_custom": ("public custom", "custom pricing", "contact for pricing"),
            "not_publicly_disclosed": ("not publicly disclosed",),
            "not_reliably_exposed": ("not reliably exposed",),
        }
        if not any(_bounded_phrase(folded, phrase)
                   for phrase in disclosure_phrases.get(value.get("disclosure_status"), ())):
            return False
        currency = value.get("currency")
        if currency and not _bounded_phrase(folded, currency):
            return False
        numbers = _decimal_tokens(folded)
        for tier in value.get("tiers", []):
            for key in ("amount", "overage_amount", "included_units"):
                if tier.get(key) is not None and Decimal(str(tier[key])) not in numbers:
                    return False
        return True
    return False


# Compatibility alias for callers that do not yet pass field identity.
def supporting_text_matches_value(text: str, value: Any, value_type: str) -> bool:
    return typed_lexical_support_matches(text, value, value_type)


def validate_execution(root: Path, manifest: dict[str, Any], schema: dict[str, Any]) -> bool:
    """Validate and return True when at least one slot remains unproven."""
    validate_schema(manifest, schema)
    canonical = {
        "query_pack": CANONICAL_QUERY_PACK,
        "protocol": CANONICAL_PROTOCOL,
        "contract_schema": CANONICAL_SCHEMA,
    }
    for key, expected in canonical.items():
        if manifest[key]["path"] != expected:
            raise ValueError(f"{key} must bind canonical path {expected}")
    pack = validate_binding(root, manifest["query_pack"], semantic=True)
    protocol = validate_binding(root, manifest["protocol"], semantic=True)
    validate_binding(root, manifest["contract_schema"], semantic=True)
    bound_collector_files = {
        key: validate_binding(root, manifest["collector"][key], semantic=False)
        for key in ("implementation", "prompt", "config")
    }
    collector_config = load_json(bound_collector_files["config"])
    if (manifest["authority_classification"] != "synthetic_fixture_verified" and
            semantic_sha256(collector_config) != manifest["collector"]["config_digest"]):
        raise ValueError("collector config_digest does not match bound config semantics")

    if pack.get("query_pack_version") != "1.1.0" or pack.get("result_format_version") != "atomic-results-1.1":
        raise ValueError("query pack is not the frozen v1.1 contract")
    try:
        from scripts.compare_research_runs import canonical_pack_hash, load_query_pack
    except ImportError:
        from compare_research_runs import canonical_pack_hash, load_query_pack
    pack_path = resolve_ref(root, manifest["query_pack"]["path"])
    load_query_pack(root, pack_path)
    if canonical_pack_hash(pack) != pack["query_pack_hash"]:
        raise ValueError("query pack declared semantic identity is invalid")
    protocol_without_digest = dict(protocol)
    declared_protocol_digest = protocol_without_digest.pop("config_digest", None)
    if semantic_sha256(protocol_without_digest) != declared_protocol_digest:
        raise ValueError("canonical collector protocol config_digest is invalid")
    if protocol.get("query_pack_hash") != pack["query_pack_hash"]:
        raise ValueError("collector protocol is not bound to the canonical query pack")
    validate_schema(protocol, load_json(resolve_ref(root, CANONICAL_PROTOCOL_SCHEMA)))
    if protocol["evidence_contract"]["response_body_hash_required"] is not True:
        raise ValueError("collector protocol must require response-body hashes")
    collector = manifest["collector"]
    if (collector["provider"] is None) != (collector["model"] is None):
        raise ValueError("collector provider and model must both be set or both be null")

    started = parse_time(manifest["capture"]["started_at"], "capture.started_at")
    completed = parse_time(manifest["capture"]["completed_at"], "capture.completed_at")
    window_start = parse_time(pack["capture_window"]["starts_at"], "query pack window start")
    window_end = parse_time(pack["capture_window"]["ends_at"], "query pack window end")
    if not (window_start <= started <= completed <= window_end):
        raise ValueError("capture timestamps are outside the frozen window or reversed")

    entities: dict[str, dict[str, Any]] = {}
    fields: dict[tuple[str, str], dict[str, Any]] = {}
    expected_slots: set[tuple[str, str]] = set()
    for lane in pack["lanes"].values():
        for entity in lane["entities"]:
            entities[entity["id"]] = entity
            for field in lane["fields"]:
                slot = (entity["id"], field["id"])
                expected_slots.add(slot)
                fields[slot] = field

    try:
        from scripts.check_evidence_url import UnsafeURL, validate_public_https_url
    except ImportError:
        from check_evidence_url import UnsafeURL, validate_public_https_url
    capture_schema = load_json(resolve_ref(root, CAPTURE_RESULT_SCHEMA))
    sources: dict[str, dict[str, Any]] = {}
    excerpt_refs: set[str] = set()
    excerpt_texts: dict[str, str] = {}
    excerpt_bytes: dict[str, bytes] = {}
    for source in manifest["sources"]:
        sid = source["id"]
        if sid in sources:
            raise ValueError(f"duplicate source id: {sid}")
        entity = entities.get(source["entity_id"])
        if entity is None:
            raise ValueError(f"{sid}: unknown entity {source['entity_id']}")
        capture_manifest_path = resolve_ref(root, source["capture_manifest_ref"])
        if sha256_file(capture_manifest_path) != source["capture_manifest_sha256"]:
            raise ValueError(f"{sid}: capture manifest hash mismatch")
        capture_manifest = load_json(capture_manifest_path)
        validate_schema(capture_manifest, capture_schema)
        capture_ids = [row["id"] for row in capture_manifest["results"]]
        if len(capture_ids) != len(set(capture_ids)):
            raise ValueError(f"{sid}: capture manifest contains duplicate result IDs")
        capture_counts = {
            state: sum(row["state"] == state for row in capture_manifest["results"])
            for state in ("captured", "unproven", "invalid")
        }
        if capture_manifest["summary"] != capture_counts:
            raise ValueError(f"{sid}: capture manifest summary is inconsistent")
        if capture_manifest["run_id"] != source["capture_run_id"] or capture_manifest["mode"] != source["capture_mode"]:
            raise ValueError(f"{sid}: capture run ID or mode mismatch")
        if capture_manifest_path.parent.name != source["capture_run_id"]:
            raise ValueError(f"{sid}: capture run directory does not match run ID")
        matching = [row for row in capture_manifest["results"] if row["id"] == source["capture_result_id"]]
        if len(matching) != 1:
            raise ValueError(f"{sid}: capture result ID is missing or ambiguous")
        captured = matching[0]
        if semantic_sha256(captured) != source["capture_result_sha256"]:
            raise ValueError(f"{sid}: capture result hash mismatch")
        if captured.get("state") != "captured" or not captured.get("excerpt"):
            raise ValueError(f"{sid}: source must bind a captured result with an excerpt")
        derived = {
            "requested_url": captured["requested_url"], "final_url": captured["final_url"],
            "redirect_chain": captured["redirect_chain"], "http_status": captured["http_status"],
            "retrieved_at": captured["retrieved_at"], "content_type": captured["content_type"],
            "response_sha256": captured["response_sha256"],
            "excerpt_sha256": captured["excerpt"]["sha256"],
        }
        for key, value in derived.items():
            if source[key] != value:
                raise ValueError(f"{sid}: {key} differs from capture result")
        expected_excerpt_ref = (Path(source["capture_manifest_ref"]).parent / captured["excerpt"]["path"]).as_posix()
        if source["excerpt_ref"] != expected_excerpt_ref:
            raise ValueError(f"{sid}: excerpt_ref differs from capture result")
        if source["excerpt_ref"] in excerpt_refs:
            raise ValueError(f"{sid}: excerpt artifact is reused by multiple sources")
        excerpt_refs.add(source["excerpt_ref"])
        urls = [source["requested_url"]]
        for hop in source["redirect_chain"]:
            urls.extend((hop["from"], hop["to"]))
        urls.append(source["final_url"])
        for url in urls:
            try:
                validate_public_https_url(url)
            except UnsafeURL as exc:
                raise ValueError(f"{sid}: unsafe URL: {exc}") from exc
            if not any(within_allowed_root(url, allowed) for allowed in entity["allowed_official_source_roots"]):
                raise ValueError(f"{sid}: URL is outside entity allowed roots: {url}")
        chain = source["redirect_chain"]
        expected_url = source["requested_url"]
        for hop in chain:
            if hop["from"] != expected_url:
                raise ValueError(f"{sid}: redirect chain is discontinuous")
            expected_url = hop["to"]
        if expected_url != source["final_url"]:
            raise ValueError(f"{sid}: redirect chain must end at final_url")
        retrieved = parse_time(source["retrieved_at"], f"{sid}.retrieved_at")
        if not (started <= retrieved <= completed):
            raise ValueError(f"{sid}: retrieved_at is outside execution timestamps")
        status = source["http_status"]
        verification = source["verification_status"]
        if verification == "verified" and not 200 <= status < 300:
            raise ValueError(f"{sid}: HTTP {status} cannot be verified")
        if status == 403 and verification == "verified":
            raise ValueError(f"{sid}: HTTP 403 is not verified evidence")
        excerpt = resolve_ref(root, source["excerpt_ref"])
        if sha256_file(excerpt) != source["excerpt_sha256"]:
            raise ValueError(f"{sid}: excerpt hash mismatch")
        try:
            raw_excerpt = excerpt.read_bytes()
            excerpt_text = raw_excerpt.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(f"{sid}: excerpt is not UTF-8 text") from exc
        if not excerpt_text.strip() or "\x00" in excerpt_text:
            raise ValueError(f"{sid}: excerpt must be nonempty safe text")
        if source["content_type"] not in {"text/html", "text/plain", "application/json", "application/xhtml+xml"}:
            raise ValueError(f"{sid}: unsupported or empty content type")
        excerpt_texts[sid] = " ".join(excerpt_text.casefold().split())
        excerpt_bytes[sid] = raw_excerpt
        sources[sid] = source

    seen_slots: set[tuple[str, str]] = set()
    has_unproven = False
    for inspection in manifest["inspections"]:
        slot = (inspection["entity_id"], inspection["field_id"])
        if slot not in expected_slots:
            raise ValueError(f"unknown frozen slot: {slot[0]}/{slot[1]}")
        if slot in seen_slots:
            raise ValueError(f"duplicate inspection for slot: {slot[0]}/{slot[1]}")
        seen_slots.add(slot)
        source_ids = inspection["source_ids"]
        locators = inspection["locators"]
        observations = inspection["observations"]
        support = inspection["support_status"]
        locator_ids = [item["source_id"] for item in locators]
        if len(locator_ids) != len(set(locator_ids)) or set(locator_ids) != set(source_ids):
            raise ValueError(f"{slot[0]}/{slot[1]}: locators must map exactly once to source_ids")
        observation_ids = [item["source_id"] for item in observations]
        if len(observation_ids) != len(set(observation_ids)) or (
            support != "does_not_establish" and set(observation_ids) != set(source_ids)
        ):
            raise ValueError(f"{slot[0]}/{slot[1]}: observations must map exactly once to source_ids")
        for sid in source_ids:
            source = sources.get(sid)
            if source is None or source["entity_id"] != slot[0]:
                raise ValueError(f"{slot[0]}/{slot[1]}: missing or cross-entity source {sid}")
        for locator in locators:
            normalized = " ".join(locator["locator"].lower().split()).strip(" .:#")
            if normalized in GENERIC_LOCATORS:
                raise ValueError(f"{slot[0]}/{slot[1]}: generic title-only locator")
            if normalized not in excerpt_texts[locator["source_id"]]:
                raise ValueError(f"{slot[0]}/{slot[1]}: locator does not occur in captured excerpt")
        for term in [*inspection["inspected_sections"], *inspection["query_terms"]]:
            normalized = " ".join(term.casefold().split())
            if source_ids and not any(normalized in excerpt_texts[sid] for sid in source_ids):
                raise ValueError(f"{slot[0]}/{slot[1]}: inspected term does not occur in captured excerpt: {term}")
        try:
            from scripts.compare_research_runs import validate_pricing, value_matches_type
        except ImportError:
            from compare_research_runs import validate_pricing, value_matches_type
        for observation in observations:
            value = observation["value"]
            start, end = observation["excerpt_span"]
            raw = excerpt_bytes[observation["source_id"]]
            if not 0 <= start < end <= len(raw):
                raise ValueError(f"{slot[0]}/{slot[1]}: observation excerpt span is out of bounds")
            try:
                selected = raw[start:end].decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ValueError(f"{slot[0]}/{slot[1]}: observation span splits UTF-8 text") from exc
            if selected != observation["supporting_text"]:
                raise ValueError(f"{slot[0]}/{slot[1]}: supporting_text does not match exact excerpt bytes")
            if fields[slot]["value_type"] == "pricing":
                validate_pricing(value, f"{slot[0]}/{slot[1]} observation")
            elif not value_matches_type(value, fields[slot]["value_type"]):
                raise ValueError(f"{slot[0]}/{slot[1]}: observation has wrong value type")
            if not typed_lexical_support_matches(
                selected, value, fields[slot]["value_type"], fields[slot]["id"]
            ):
                raise ValueError(f"{slot[0]}/{slot[1]}: captured text does not support the proposed typed value")
        verified = [sources[sid] for sid in source_ids if sources[sid]["verification_status"] == "verified"]
        if support == "proven":
            if not source_ids or len(verified) != len(source_ids):
                raise ValueError(f"{slot[0]}/{slot[1]}: proven requires verified sources")
        elif support == "conflicted":
            if len(source_ids) < 2 or len(verified) != len(source_ids):
                raise ValueError(f"{slot[0]}/{slot[1]}: conflicted requires at least two verified sources")
            if len({source["final_url"] for source in verified}) < 2:
                raise ValueError(f"{slot[0]}/{slot[1]}: conflicted requires distinct source URLs")
        else:
            if observations:
                raise ValueError(f"{slot[0]}/{slot[1]}: does_not_establish must not carry typed observations")
            has_unproven = True
        if support == "proven" and len({semantic_sha256(row["value"]) for row in observations}) != 1:
            raise ValueError(f"{slot[0]}/{slot[1]}: proven observations disagree")
        if support == "conflicted":
            if len({sources[sid]["excerpt_sha256"] for sid in source_ids}) < 2:
                raise ValueError(f"{slot[0]}/{slot[1]}: conflicted sources require distinct content hashes")
            if len({semantic_sha256(row["value"]) for row in observations}) < 2:
                raise ValueError(f"{slot[0]}/{slot[1]}: conflicted observations require opposing typed values")

    missing = expected_slots - seen_slots
    if missing:
        sample = sorted(missing)[0]
        raise ValueError(f"missing inspections for {len(missing)} frozen slots; first: {sample[0]}/{sample[1]}")
    authority = manifest["authority_classification"]
    attestation = manifest["operator_attestation"]
    if authority == "collector_proposed":
        if attestation is not None:
            raise ValueError("collector_proposed output cannot carry operator attestation")
        if manifest["evidence_scope"] != "collector_proposal_not_market_evidence":
            raise ValueError("collector_proposed output has invalid evidence scope")
        return True
    if authority == "synthetic_fixture_verified":
        if attestation is not None or any(source["capture_mode"] != "fixture" for source in sources.values()):
            raise ValueError("synthetic_fixture_verified requires fixture-only captures and no operator attestation")
        if manifest["evidence_scope"] != "synthetic_fixture_only_not_market_evidence":
            raise ValueError("synthetic fixture output cannot claim market-evidence scope")
        if manifest["collector"]["implementation"]["path"] != CANONICAL_FIXTURE_RUNNER:
            raise ValueError("synthetic_fixture_verified requires the canonical fixture runner")
        if manifest["collector"]["config"]["path"] != CANONICAL_FIXTURE_SET:
            raise ValueError("synthetic_fixture_verified requires the canonical fixture set")
        if manifest["collector"]["prompt"]["path"] != CANONICAL_PROTOCOL:
            raise ValueError("synthetic_fixture_verified requires the canonical protocol as prompt")
        fixture_set = load_json(resolve_ref(root, CANONICAL_FIXTURE_SET))
        declared = fixture_set.get("fixture_set_hash")
        fixture_without_hash = dict(fixture_set)
        fixture_without_hash.pop("fixture_set_hash", None)
        if fixture_set.get("synthetic_marker") != SYNTHETIC_MARKER:
            raise ValueError("canonical synthetic marker is missing")
        if declared != CANONICAL_FIXTURE_DIGEST or semantic_sha256(fixture_without_hash) != CANONICAL_FIXTURE_DIGEST:
            raise ValueError("canonical fixture-set digest is invalid")
        if manifest["collector"]["config_digest"] != declared:
            raise ValueError("collector config_digest does not bind the canonical fixture set")
        return has_unproven
    if manifest["collector"]["identity_verification"] != "operator_attested" or not isinstance(attestation, dict):
        raise ValueError("operator_verified requires an operator-attested identity and decision binding")
    decision_path = resolve_ref(root, attestation["decision_ref"])
    if sha256_file(decision_path) != attestation["decision_sha256"]:
        raise ValueError("operator decision hash mismatch")
    decision = load_json(decision_path)
    expected = {
        "schema_version": "collector-operator-decision-1.0",
        "decision_id": attestation["decision_id"],
        "execution_instance_id": manifest["execution_instance_id"],
        "run_id": manifest["run_id"],
        "decision": "verified",
    }
    if not isinstance(decision, dict) or any(decision.get(key) != value for key, value in expected.items()):
        raise ValueError("operator decision does not bind this execution")
    if set(decision) != {*expected, "reviewer_id", "decided_at"}:
        raise ValueError("operator decision has an unexpected shape")
    if not isinstance(decision["reviewer_id"], str) or len(decision["reviewer_id"]) < 2:
        raise ValueError("operator decision reviewer_id is invalid")
    if parse_time(decision["decided_at"], "operator decision decided_at") < completed:
        raise ValueError("operator decision predates collection completion")
    if manifest["evidence_scope"] != "operator_reviewed_research":
        raise ValueError("operator_verified output has invalid evidence scope")
    return has_unproven


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    schema_path = root / CANONICAL_SCHEMA
    try:
        input_path = resolve_ref(root, str(args.input))
        manifest = load_json(input_path)
        schema = load_json(schema_path)
        unproven = validate_execution(root, manifest, schema)
    except RuntimeError as exc:
        payload = {"status": "unproven", "exit_code": 2, "detail": str(exc)}
        code = 2
    except ValueError as exc:
        payload = {"status": "invalid", "exit_code": 1, "detail": str(exc)}
        code = 1
    else:
        code = 2 if unproven else 0
        payload = {
            "status": "valid-unproven" if unproven else "valid-complete",
            "exit_code": code,
            "detail": "all frozen slots inspected; unproven slots remain" if unproven else "all frozen slots inspected",
        }
    if args.json:
        print(json.dumps(payload, sort_keys=True))
    else:
        print(f"{payload['status'].upper()} — {payload['detail']}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
