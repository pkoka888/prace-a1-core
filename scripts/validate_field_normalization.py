#!/usr/bin/env python3
"""Validate and deterministically evaluate Plan AC normalization proposals.

The rules never establish evidence or accepted values.  A match produces only a
typed proposal whose ``operator_review_required`` flag is always true.

Exit codes: 0 valid, 1 invalid, 2 required file/dependency unavailable.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any


DEFAULT_RULES = "research/query-packs/field-normalization-1.0.json"
DEFAULT_SCHEMA = "research/query-packs/field-normalization-1.0.schema.json"
DENIED_ROOTS = {
    "a1", "scans", "evidence", "ocr", "data", "output", "runtime",
    "secrets", ".history-remediation",
}
SPDX_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.-]*(?:-only|-or-later)?$")
FROZEN_SPDX_VERSION = "plan-ac-spdx-subset-1.0"
FROZEN_SPDX_IDENTIFIERS = {
    "Apache-2.0", "GPL-2.0-only", "GPL-3.0-only", "MIT", "MPL-2.0",
}
SAFE_REGEX_ALTERNATION = re.compile(
    r"^\^\(([a-z0-9_ -]+(?:\|[a-z0-9_ -]+)*)\)\$$"
)


class InvalidRules(ValueError):
    """The rules or their binding are invalid."""


class Unavailable(RuntimeError):
    """A required local file or dependency is unavailable."""


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def canonical_pack_hash(pack: dict[str, Any]) -> str:
    candidate = dict(pack)
    candidate.pop("query_pack_hash", None)
    return hashlib.sha256(canonical_json(candidate)).hexdigest()


def canonical_ruleset_hash(rules: dict[str, Any]) -> str:
    candidate = dict(rules)
    candidate.pop("ruleset_hash", None)
    return hashlib.sha256(canonical_json(candidate)).hexdigest()


def contained_file(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise InvalidRules("file reference must be a non-empty relative path")
    given = Path(relative)
    if given.is_absolute():
        raise InvalidRules(f"absolute file reference is denied: {relative}")
    candidate = (root / given).resolve()
    try:
        within = candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise InvalidRules(f"file reference escapes --root: {relative}") from exc
    if not within.parts or within.parts[0] in DENIED_ROOTS or within.name == ".env":
        raise InvalidRules(f"sensitive/runtime file reference is denied: {relative}")
    if not candidate.is_file():
        raise Unavailable(f"required file is unavailable: {relative}")
    return candidate


def read_json(path: Path) -> tuple[Any, bytes]:
    try:
        raw = path.read_bytes()
    except (FileNotFoundError, PermissionError, OSError) as exc:
        raise Unavailable(f"cannot read {path}: {exc}") from exc
    try:
        return json.loads(raw), raw
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InvalidRules(f"invalid JSON in {path}: {exc}") from exc


def validate_json_schema(instance: Any, schema: Any) -> None:
    try:
        from jsonschema import Draft7Validator, FormatChecker
    except ImportError as exc:
        raise Unavailable("jsonschema dependency is unavailable") from exc
    try:
        Draft7Validator.check_schema(schema)
    except Exception as exc:
        raise InvalidRules(f"normalization schema is invalid: {exc}") from exc
    errors = sorted(
        Draft7Validator(schema, format_checker=FormatChecker()).iter_errors(instance),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        error = errors[0]
        where = "/".join(str(part) for part in error.absolute_path) or "<root>"
        raise InvalidRules(f"schema {where}: {error.message}")


def normalize(value: str, profile: str) -> str:
    result = unicodedata.normalize("NFKC", value)
    if profile == "text_casefold":
        result = result.casefold()
        result = " ".join(result.split())
    elif profile != "exact_trim":
        raise InvalidRules(f"unsupported normalization profile: {profile}")
    return result.strip()


def safe_regex_values(pattern: str) -> tuple[str, ...]:
    """Accept only anchored literal alternations, returning their exact domain.

    This deliberately excludes wildcards, lookarounds, backreferences,
    character classes, and quantifiers.  A future contract can add constructs
    only with an overlap proof; Python's general regex language is not used as a
    normalization DSL.
    """
    match = SAFE_REGEX_ALTERNATION.fullmatch(pattern)
    if not match:
        raise InvalidRules(
            f"unsafe or non-enumerable regex {pattern!r}; only ^(literal|literal)$ is allowed"
        )
    values = tuple(match.group(1).split("|"))
    if len(values) != len(set(values)):
        raise InvalidRules(f"regex contains duplicate alternatives: {pattern!r}")
    try:
        compiled = re.compile(pattern)
    except re.error as exc:
        raise InvalidRules(f"invalid regex {pattern!r}: {exc}") from exc
    if any(compiled.fullmatch(value) is None for value in values):
        raise InvalidRules(f"regex domain cannot be enumerated exactly: {pattern!r}")
    return values


def input_domain(rule: dict[str, Any]) -> tuple[str, ...]:
    spec = rule["input"]
    profile = spec["normalization_profile"]
    if spec["match_mode"] == "exact_value":
        values = tuple(spec["values"])
    else:
        values = tuple(
            value for pattern in spec["patterns"] for value in safe_regex_values(pattern)
        )
    normalized = tuple(normalize(value, profile) for value in values)
    if any(not value for value in normalized):
        raise InvalidRules(f"{rule['id']}: empty normalized input")
    if normalized != values:
        raise InvalidRules(
            f"{rule['id']}: inputs must already be exact normalized values for {profile}"
        )
    if len(normalized) != len(set(normalized)):
        raise InvalidRules(f"{rule['id']}: duplicate normalized input")
    return normalized


def output_key(rule: dict[str, Any], matched: str) -> tuple[str, Any]:
    output = rule["output"]
    if output["kind"] == "fixed_typed_value":
        return "fixed", output["value"]
    if output["name"] == "identity_exact":
        return "identity", matched
    raise InvalidRules(f"{rule['id']}: unsupported mapping function")


def validate_output(rule: dict[str, Any], field: dict[str, Any], domain: tuple[str, ...]) -> None:
    field_type = field["value_type"]
    output = rule["output"]
    behavior = rule["enumeration_behavior"]
    expected_behavior = {
        "boolean": "scalar_proposal",
        "string": "scalar_proposal",
        "string_list": "append_unique_partial_proposal",
        "pricing": "pricing_component_proposal",
    }.get(field_type)
    if behavior != expected_behavior:
        raise InvalidRules(
            f"{rule['id']}: {behavior} is invalid for {field_type} field"
        )

    if field_type == "pricing":
        required = rule.get("required_pricing_context")
        expected = {
            "vat_status": ["included", "excluded", "not_disclosed"],
            "billing_period": ["one_time", "monthly", "annual", "other"],
            "unit": ["document", "invoice", "user", "organization", "flat_rate", "other"],
        }
        if required != expected:
            raise InvalidRules(
                f"{rule['id']}: pricing proposal requires the frozen VAT status, billing period, and unit contract"
            )
        if output != {"kind": "fixed_typed_value", "value": "CZK"}:
            raise InvalidRules(f"{rule['id']}: v1.0 pricing may only normalize Kč/CZK to CZK")
        if set(domain) != {"czk", "kč"}:
            raise InvalidRules(f"{rule['id']}: currency inputs must be exactly Kč/CZK after normalization")
        return
    if "required_pricing_context" in rule:
        raise InvalidRules(f"{rule['id']}: pricing context is forbidden on a non-pricing field")

    if output["kind"] == "fixed_typed_value":
        value = output["value"]
        if field_type == "boolean":
            if type(value) is not bool:
                raise InvalidRules(f"{rule['id']}: invented/non-boolean output")
        elif field_type in {"string", "string_list"}:
            if not isinstance(value, str) or not value:
                raise InvalidRules(f"{rule['id']}: invented/non-string output")
            allowed = field.get("allowed_values")
            if allowed is None or value not in allowed:
                raise InvalidRules(f"{rule['id']}: output is outside the bound controlled vocabulary")
        else:
            raise InvalidRules(f"{rule['id']}: fixed normalization is unsupported for {field_type}")
    else:
        if output != {"kind": "mapping_function", "name": "identity_exact", "result_type": "string"}:
            raise InvalidRules(f"{rule['id']}: unapproved mapping function")
        if field_type == "string_list":
            allowed = set(field.get("allowed_values", []))
            if not allowed or any(value not in allowed for value in domain):
                raise InvalidRules(f"{rule['id']}: identity output could invent an uncontrolled value")
        elif field_type == "string" and field["id"] == "license_spdx":
            if any(SPDX_TOKEN.fullmatch(value) is None for value in domain):
                raise InvalidRules(f"{rule['id']}: malformed SPDX token")
        else:
            raise InvalidRules(f"{rule['id']}: identity mapping is not authorized for this field")


def validate_rules(root: Path, rules: dict[str, Any], rules_raw: bytes) -> dict[str, Any]:
    del rules_raw  # reserved for future signed-rule bindings
    if canonical_ruleset_hash(rules) != rules["ruleset_hash"]:
        raise InvalidRules("ruleset canonical hash mismatch")
    proposal_contract = rules["proposal_contract"]
    proposal_schema_path = contained_file(root, proposal_contract["schema_path"])
    proposal_schema, proposal_schema_raw = read_json(proposal_schema_path)
    if hashlib.sha256(proposal_schema_raw).hexdigest() != proposal_contract["schema_byte_sha256"]:
        raise InvalidRules("proposal schema byte hash binding mismatch")
    try:
        from jsonschema import Draft7Validator
        Draft7Validator.check_schema(proposal_schema)
    except ImportError as exc:
        raise Unavailable("jsonschema dependency is unavailable") from exc
    except Exception as exc:
        raise InvalidRules(f"proposal schema is invalid: {exc}") from exc
    binding = rules["query_pack_binding"]
    pack_path = contained_file(root, binding["path"])
    pack, pack_raw = read_json(pack_path)
    if not isinstance(pack, dict):
        raise InvalidRules("bound query pack must be an object")
    if hashlib.sha256(pack_raw).hexdigest() != binding["byte_sha256"]:
        raise InvalidRules("query-pack byte hash binding mismatch")
    if pack.get("query_pack_version") != binding["query_pack_version"]:
        raise InvalidRules("query-pack version binding mismatch")
    declared_hash = pack.get("query_pack_hash")
    if declared_hash != binding["query_pack_hash"] or canonical_pack_hash(pack) != declared_hash:
        raise InvalidRules("query-pack canonical hash binding mismatch")

    entities: dict[str, str] = {}
    fields: dict[tuple[str, str], dict[str, Any]] = {}
    for lane, lane_doc in pack.get("lanes", {}).items():
        for entity in lane_doc.get("entities", []):
            if entity["id"] in entities:
                raise InvalidRules(f"query pack duplicates entity {entity['id']}")
            entities[entity["id"]] = lane
        for field in lane_doc.get("fields", []):
            fields[(lane, field["id"])] = field

    coverage = rules["coverage"]
    if coverage["coverage_mode"] != "sparse":
        raise InvalidRules("v1.0 ruleset must explicitly declare sparse coverage")
    for lane, lane_doc in pack["lanes"].items():
        universe = {field["id"] for field in lane_doc["fields"]}
        covered = set(coverage["covered_fields"][lane])
        uncovered = set(coverage["uncovered_fields"][lane])
        if covered & uncovered or covered | uncovered != universe:
            raise InvalidRules(f"coverage partition is incomplete or overlapping for lane {lane}")

    rule_ids: set[str] = set()
    occupied: dict[tuple[str, str, str, str], str] = {}
    profiles: dict[tuple[str, str, str], str] = {}
    domains: dict[str, tuple[str, ...]] = {}
    actual_covered: dict[str, set[str]] = {lane: set() for lane in pack["lanes"]}
    for rule in rules["rules"]:
        rule_id = rule["id"]
        if rule_id in rule_ids:
            raise InvalidRules(f"duplicate rule ID: {rule_id}")
        rule_ids.add(rule_id)
        if rule.get("requires_operator_review") is not True:
            raise InvalidRules(f"{rule_id}: operator review must be required")
        scope = rule["scope"]
        lane, field_id = scope["lane"], scope["field_id"]
        field = fields.get((lane, field_id))
        if field is None:
            raise InvalidRules(f"{rule_id}: unscoped field {lane}/{field_id}")
        for entity_id in scope["entity_ids"]:
            if entities.get(entity_id) != lane:
                raise InvalidRules(f"{rule_id}: unscoped entity {entity_id} for lane {lane}")
            profile_key = lane, entity_id, field_id
            profile = rule["input"]["normalization_profile"]
            previous_profile = profiles.get(profile_key)
            if previous_profile is not None and previous_profile != profile:
                raise InvalidRules(
                    f"{rule_id}: mixed normalization profiles create raw-input ambiguity "
                    f"for {lane}/{entity_id}/{field_id}"
                )
            profiles[profile_key] = profile
        domain = input_domain(rule)
        domains[rule_id] = domain
        validate_output(rule, field, domain)
        actual_covered[lane].add(field_id)
        for entity_id in scope["entity_ids"]:
            for token in domain:
                key = lane, entity_id, field_id, token
                previous = occupied.get(key)
                if previous is not None:
                    raise InvalidRules(
                        f"ambiguous/overlapping match for {lane}/{entity_id}/{field_id}/{token!r}: "
                        f"{previous} and {rule_id}"
                    )
                occupied[key] = rule_id

    for lane, fields_in_rules in actual_covered.items():
        if fields_in_rules != set(coverage["covered_fields"][lane]):
            raise InvalidRules(f"declared covered fields do not match rules for lane {lane}")

    spdx = rules["spdx_allowlist"]
    if (
        spdx["version"] != FROZEN_SPDX_VERSION
        or set(spdx["identifiers"]) != FROZEN_SPDX_IDENTIFIERS
    ):
        raise InvalidRules("SPDX allowlist differs from frozen Plan AC subset/version")
    spdx_rules = [
        rule for rule in rules["rules"]
        if rule["scope"]["lane"] == "oss_invoice"
        and rule["scope"]["field_id"] == "license_spdx"
    ]
    if len(spdx_rules) != 1 or set(input_domain(spdx_rules[0])) != set(spdx["identifiers"]):
        raise InvalidRules("SPDX rule must exactly equal the frozen versioned allowlist")

    return {
        "result": "pass",
        "normalization_version": rules["normalization_version"],
        "ruleset_hash": rules["ruleset_hash"],
        "authority": rules["authority"],
        "query_pack_hash": binding["query_pack_hash"],
        "rules": len(rule_ids),
        "expanded_matches": len(occupied),
        "operator_review_required": True,
        "domains": domains,
    }


def proposal_for(
    rules: dict[str, Any], *, lane: str, entity_id: str, field_id: str,
    raw_value: str, evidence: dict[str, str] | None = None,
    pricing_context: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Return hash-bound review proposals; absent context yields no action."""
    if not isinstance(raw_value, str):
        raise InvalidRules("raw normalization input must be a string")
    if evidence is None:
        return []
    if set(evidence) != {"evidence_id", "source_url", "locator", "context"}:
        raise InvalidRules("complete evidence ID, HTTPS URL, locator, and context are required")
    if not evidence["source_url"].startswith("https://") or not evidence["locator"] or not evidence["context"]:
        raise InvalidRules("evidence locator and context must be non-empty and use HTTPS")
    proposals: list[dict[str, Any]] = []
    for rule in rules["rules"]:
        scope = rule["scope"]
        if (
            scope["lane"] != lane
            or entity_id not in scope["entity_ids"]
            or scope["field_id"] != field_id
        ):
            continue
        profile = rule["input"]["normalization_profile"]
        candidate = normalize(raw_value, profile)
        if candidate not in input_domain(rule):
            continue
        if rule["enumeration_behavior"] == "pricing_component_proposal":
            contract = rule["required_pricing_context"]
            if (
                pricing_context is None
                or set(pricing_context) != set(contract)
                or any(pricing_context[key] not in contract[key] for key in contract)
            ):
                continue
        elif pricing_context is not None:
            raise InvalidRules("pricing context is forbidden for a non-pricing proposal")
        _, value = output_key(rule, candidate)
        proposal = {
            "proposal_version": "1.0.0",
            "status": "awaiting_operator_review",
            "authority": "proposal-only-non-authoritative",
            "operator_review_required": True,
            "ruleset_version": rules["normalization_version"],
            "ruleset_hash": rules["ruleset_hash"],
            "query_pack_hash": rules["query_pack_binding"]["query_pack_hash"],
            "rule_id": rule["id"],
            "lane": lane,
            "entity_id": entity_id,
            "field_id": field_id,
            "raw_value_sha256": hashlib.sha256(raw_value.encode("utf-8")).hexdigest(),
            "evidence_locator": {
                "evidence_id": evidence["evidence_id"],
                "source_url": evidence["source_url"],
                "locator": evidence["locator"],
                "context_sha256": hashlib.sha256(evidence["context"].encode("utf-8")).hexdigest(),
            },
            "proposed_value": value,
            "enumeration_behavior": rule["enumeration_behavior"],
        }
        if pricing_context is not None:
            proposal["pricing_context"] = dict(pricing_context)
        proposals.append(proposal)
    if len(proposals) > 1:
        raise InvalidRules("ruleset produced ambiguous proposals")
    return proposals


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    parser.add_argument("--input", default=DEFAULT_RULES)
    parser.add_argument("--schema", default=DEFAULT_SCHEMA)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def emit(payload: dict[str, Any], *, json_mode: bool, error: bool = False) -> None:
    stream = sys.stderr if error else sys.stdout
    if json_mode:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True), file=stream)
    elif error:
        print(f"{payload['result'].upper()} — {payload['message']}", file=stream)
    else:
        print(
            f"PASS — {payload['rules']} proposal-only rules; "
            f"{payload['expanded_matches']} scoped matches",
            file=stream,
        )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = Path(args.root).resolve()
    try:
        rules_path = contained_file(root, args.input)
        schema_path = contained_file(root, args.schema)
        rules, rules_raw = read_json(rules_path)
        schema, _ = read_json(schema_path)
        validate_json_schema(rules, schema)
        result = validate_rules(root, rules, rules_raw)
    except Unavailable as exc:
        emit({"result": "unproven", "message": str(exc)}, json_mode=args.json, error=True)
        return 2
    except (InvalidRules, KeyError, TypeError) as exc:
        emit({"result": "fail", "message": str(exc)}, json_mode=args.json, error=True)
        return 1
    emit(result, json_mode=args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
