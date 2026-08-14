#!/usr/bin/env python3
"""Replay synthetic field decisions bound to the final Plan AC v1.1 pack.

This deterministic, offline inspection gate is not market evidence. Exit 0 is
an exact valid replay, 1 is invalid input/configuration or stale output, and 2
means a required fixture/output/dependency is unavailable.
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


class InvalidFixture(ValueError):
    pass


class Unavailable(RuntimeError):
    pass


GENERIC_TITLES = {"home", "homepage", "pricing", "cenik", "ceník", "features", "documentation", "docs", "product", "overview"}
REPOSITORY_HOSTS = {"github.com", "api.github.com", "raw.githubusercontent.com"}


def read_json(path: Path, *, configuration: bool = False) -> tuple[Any, bytes]:
    try:
        raw = path.read_bytes()
    except (FileNotFoundError, PermissionError, OSError) as exc:
        error = f"cannot read {path}: {exc}"
        if configuration:
            raise InvalidFixture(error) from exc
        raise Unavailable(error) from exc
    try:
        return json.loads(raw), raw
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InvalidFixture(f"invalid JSON in {path}: {exc}") from exc


def contained(root: Path, value: str) -> Path:
    path = (root / value).resolve() if not Path(value).is_absolute() else Path(value).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise InvalidFixture(f"path escapes --root: {value}") from exc
    return path


def validator(schema: Any, *, configuration: bool = False):
    try:
        import jsonschema
    except ImportError as exc:
        raise Unavailable("jsonschema is unavailable") from exc
    try:
        jsonschema.Draft7Validator.check_schema(schema)
        return jsonschema.Draft7Validator(schema, format_checker=jsonschema.FormatChecker())
    except Exception as exc:
        error = f"schema is unusable: {exc}"
        if configuration:
            raise InvalidFixture(error) from exc
        raise Unavailable(error) from exc


def validate_schema(instance: Any, schema: Any, label: str) -> None:
    errors = sorted(validator(schema, configuration=True).iter_errors(instance), key=lambda error: list(error.path))
    if errors:
        error = errors[0]
        where = "/".join(map(str, error.path)) or "<root>"
        raise InvalidFixture(f"{label}: {where}: {error.message}")


def canonical_pack_hash(pack: dict[str, Any]) -> str:
    value = dict(pack)
    value.pop("query_pack_hash", None)
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def parsed_time(value: str, label: str) -> datetime:
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise InvalidFixture(f"{label}: invalid timestamp") from exc
    if result.tzinfo is None:
        raise InvalidFixture(f"{label}: timezone required")
    return result.astimezone(timezone.utc)


def within_root(url: str, root: str) -> bool:
    candidate, allowed = urlsplit(url), urlsplit(root)
    if (candidate.scheme.lower(), candidate.hostname, candidate.port) != (allowed.scheme.lower(), allowed.hostname, allowed.port):
        return False
    base, path = allowed.path.rstrip("/"), candidate.path.rstrip("/")
    return not base or path == base or path.startswith(base + "/")


def field_value(value: Any, definition: dict[str, Any], pricing_schema: dict[str, Any], label: str) -> Any:
    kind = definition["value_type"]
    if kind == "boolean":
        if type(value) is not bool:
            raise InvalidFixture(f"{label}: boolean required by v1.1 field definition")
        return value
    if kind == "integer":
        if type(value) is not int or value < 0:
            raise InvalidFixture(f"{label}: non-negative integer required by v1.1 field definition")
        return value
    if kind == "date":
        if not isinstance(value, str):
            raise InvalidFixture(f"{label}: ISO date required")
        try:
            date.fromisoformat(value)
        except ValueError as exc:
            raise InvalidFixture(f"{label}: invalid ISO date") from exc
        return value
    if kind == "string":
        if not isinstance(value, str) or not value:
            raise InvalidFixture(f"{label}: non-empty string required by v1.1 field definition")
        allowed = definition.get("allowed_values")
        if allowed is not None and value not in allowed:
            raise InvalidFixture(f"{label}: value is outside v1.1 controlled vocabulary")
        return value
    if kind == "string_list":
        if not isinstance(value, list) or not value or any(not isinstance(item, str) or not item for item in value):
            raise InvalidFixture(f"{label}: non-empty string list required by v1.1 field definition")
        if len(value) != len(set(value)):
            raise InvalidFixture(f"{label}: duplicate list value")
        allowed = definition.get("allowed_values")
        if allowed is not None and any(item not in allowed for item in value):
            raise InvalidFixture(f"{label}: list value is outside v1.1 controlled vocabulary")
        return sorted(value)
    if kind == "pricing":
        errors = sorted(validator(pricing_schema, configuration=True).iter_errors(value), key=lambda error: list(error.path))
        if errors:
            error = errors[0]
            where = "/".join(map(str, error.path)) or "<root>"
            raise InvalidFixture(f"{label}: malformed v1.1 pricing at {where}: {error.message}")
        return json.loads(json.dumps(value, sort_keys=True))
    raise InvalidFixture(f"{label}: unsupported v1.1 value_type {kind}")


def evaluate_fixture(root: Path, fixture: dict[str, Any], fixture_raw: bytes) -> dict[str, Any]:
    binding = fixture["query_pack_binding"]
    pack_path = contained(root, binding["path"])
    pack, pack_raw = read_json(pack_path, configuration=True)
    pack_file_hash = hashlib.sha256(pack_raw).hexdigest()
    if pack_file_hash != binding["file_sha256"]:
        raise InvalidFixture("query-pack file hash binding mismatch")
    if pack.get("query_pack_version") != binding["query_pack_version"]:
        raise InvalidFixture("query-pack version binding mismatch")
    if pack.get("query_pack_hash") != binding["query_pack_hash"] or canonical_pack_hash(pack) != binding["query_pack_hash"]:
        raise InvalidFixture("query-pack semantic hash binding mismatch")
    results_schema, _ = read_json(root / "research/query-packs/atomic-results-1.1.schema.json", configuration=True)
    pricing_schema = results_schema["definitions"]["pricing"]
    starts = parsed_time(pack["capture_window"]["starts_at"], "pack capture start")
    ends = parsed_time(pack["capture_window"]["ends_at"], "pack capture end")

    entities: dict[str, tuple[str, dict[str, Any]]] = {}
    fields: dict[tuple[str, str], dict[str, Any]] = {}
    for lane, lane_data in pack["lanes"].items():
        for entity in lane_data["entities"]:
            entities[entity["id"]] = (lane, entity)
        for definition in lane_data["fields"]:
            fields[(lane, definition["id"])] = definition
    if len(fixture["cases"]) != 8:
        raise InvalidFixture("fixture must contain exactly eight cases")
    selected = fixture["entity_ids"]
    if len(selected) != 4 or len(set(selected)) != 4 or any(entity_id not in entities for entity_id in selected):
        raise InvalidFixture("fixture must bind exactly four distinct v1.1 entities")
    lane_counts = {"oss_invoice": 0, "czech_invoice_software": 0}
    for entity_id in selected:
        lane_counts[entities[entity_id][0]] += 1
    if lane_counts != {"oss_invoice": 2, "czech_invoice_software": 2}:
        raise InvalidFixture("fixture must bind exactly two OSS and two Czech-vendor entities")

    try:
        from check_evidence_url import UnsafeURL, validate_public_https_url
    except ImportError as exc:
        raise Unavailable("canonical public HTTPS validator unavailable") from exc
    case_ids: set[str] = set()
    evidence_ids: set[str] = set()
    used_entities: set[str] = set()
    decisions: list[dict[str, str]] = []
    counts = {key: 0 for key in ("supports", "does_not_establish", "conflicts")}
    for case in fixture["cases"]:
        case_id, entity_id, lane, field_id = case["id"], case["entity_id"], case["lane"], case["field_id"]
        if case_id in case_ids:
            raise InvalidFixture(f"duplicate case ID: {case_id}")
        case_ids.add(case_id)
        if entity_id not in selected or entities.get(entity_id, (None,))[0] != lane:
            raise InvalidFixture(f"{case_id}: entity/lane is not bound to the selected v1.1 roster")
        used_entities.add(entity_id)
        definition = fields.get((lane, field_id))
        if definition is None:
            raise InvalidFixture(f"{case_id}: field is not defined in the bound v1.1 lane")
        candidate = field_value(case["candidate_value"], definition, pricing_schema, f"{case_id}/candidate")
        roots = entities[entity_id][1]["allowed_official_source_roots"]
        supporting = contradicting = False
        for evidence in case["evidence"]:
            evidence_id = evidence["id"]
            if evidence_id in evidence_ids:
                raise InvalidFixture(f"duplicate evidence ID: {evidence_id}")
            evidence_ids.add(evidence_id)
            if evidence["entity_id"] != entity_id or evidence["field_id"] != field_id:
                raise InvalidFixture(f"{case_id}/{evidence_id}: evidence ownership or field mismatch")
            title = " ".join(evidence["page_title"].lower().split()).strip(" .:-")
            if title in GENERIC_TITLES:
                raise InvalidFixture(f"{case_id}/{evidence_id}: generic page title is not inspectable evidence")
            try:
                validate_public_https_url(evidence["url"])
            except UnsafeURL as exc:
                raise InvalidFixture(f"{case_id}/{evidence_id}: unsafe evidence URL: {exc}") from exc
            official = any(within_root(evidence["url"], allowed) for allowed in roots)
            role = evidence["evidence_class"]
            if role.startswith("official_") and not official:
                raise InvalidFixture(f"{case_id}/{evidence_id}: official evidence is outside entity roots")
            if role.startswith("independent_") and official:
                raise InvalidFixture(f"{case_id}/{evidence_id}: official evidence laundered as independent")
            if role == "repository_metadata":
                if lane != "oss_invoice" or not official or (urlsplit(evidence["url"]).hostname or "").lower() not in REPOSITORY_HOSTS:
                    raise InvalidFixture(f"{case_id}/{evidence_id}: repository role requires the entity repository root")
            captured = parsed_time(evidence["captured_at"], f"{case_id}/{evidence_id}/captured_at")
            if not starts <= captured <= ends:
                raise InvalidFixture(f"{case_id}/{evidence_id}: capture timestamp is outside the bound pack window")
            capture = evidence["synthetic_capture"]
            excerpt = evidence["synthetic_excerpt"]
            if not capture.lower().startswith("synthetic") or not excerpt.lower().startswith("synthetic"):
                raise InvalidFixture(f"{case_id}/{evidence_id}: capture/excerpt is not explicitly synthetic")
            if hashlib.sha256(capture.encode()).hexdigest() != evidence["capture_sha256"]:
                raise InvalidFixture(f"{case_id}/{evidence_id}: capture hash mismatch")
            if hashlib.sha256(excerpt.encode()).hexdigest() != evidence["excerpt_sha256"]:
                raise InvalidFixture(f"{case_id}/{evidence_id}: excerpt hash mismatch")
            locator_kind, locator_number = evidence["locator"].split(":")[1:]
            segments = capture.splitlines() if locator_kind == "line" else capture.split("\n\n")
            index = int(locator_number) - 1
            if index >= len(segments) or segments[index] != excerpt:
                raise InvalidFixture(f"{case_id}/{evidence_id}: locator does not bind the excerpt to the capture")
            for assertion in evidence["assertions"]:
                if assertion["field_id"] != field_id:
                    raise InvalidFixture(f"{case_id}/{evidence_id}: assertion field mismatch")
                asserted = field_value(assertion["value"], definition, pricing_schema, f"{case_id}/{evidence_id}/assertion")
                equal = asserted == candidate
                if assertion["effect"] == "supports":
                    if not equal:
                        raise InvalidFixture(f"{case_id}/{evidence_id}: support assertion value differs from candidate")
                    supporting = True
                else:
                    if equal:
                        raise InvalidFixture(f"{case_id}/{evidence_id}: same-value contradiction is invalid")
                    contradicting = True
        verdict = "conflicts" if contradicting else "supports" if supporting else "does_not_establish"
        if verdict != case["expected"]:
            raise InvalidFixture(f"{case_id}: expected {case['expected']}, replay produced {verdict}")
        counts[verdict] += 1
        decisions.append({"case_id": case_id, "entity_id": entity_id, "field_id": field_id, "decision": verdict})
    if used_entities != set(selected):
        raise InvalidFixture("every selected entity must have at least one case")
    return {
        "replay_version": "field-decision-replay-1.0", "fixture_version": fixture["fixture_version"],
        "fixture_sha256": hashlib.sha256(fixture_raw).hexdigest(),
        "query_pack_binding": binding, "authority": fixture["purpose"],
        "counts": {"cases": len(decisions), **counts}, "decisions": decisions,
    }


def render(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data); handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try: os.unlink(temporary)
        except FileNotFoundError: pass
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--fixture", default="research/query-packs/field-decision-fixtures-1.0.json")
    parser.add_argument("--schema", default="research/query-packs/field-decision-fixtures-1.0.schema.json")
    parser.add_argument("--output", required=True)
    parser.add_argument("--check", action="store_true", help="read-only exact-byte output verification")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    try:
        fixture_path, schema_path, output_path = (contained(root, value) for value in (args.fixture, args.schema, args.output))
        fixture, fixture_raw = read_json(fixture_path)
        schema, _ = read_json(schema_path, configuration=True)
        validate_schema(fixture, schema, "fixture schema")
        report = evaluate_fixture(root, fixture, fixture_raw)
        expected = render(report)
        if args.check:
            try: actual = output_path.read_bytes()
            except (FileNotFoundError, PermissionError, OSError) as exc: raise Unavailable(f"cannot read replay output {output_path}: {exc}") from exc
            if actual != expected: raise InvalidFixture("replay output is missing, stale, or not byte-exact")
        else: atomic_write(output_path, expected)
        result = {"result": "pass", "cases": report["counts"]["cases"], "output": str(output_path.relative_to(root)), "exit": 0}
        print(json.dumps(result) if args.json else f"PASS — replayed {result['cases']} synthetic cases")
        return 0
    except InvalidFixture as exc:
        print(json.dumps({"result": "fail", "error": str(exc), "exit": 1}) if args.json else f"FAIL — {exc}", file=sys.stderr); return 1
    except (Unavailable, OSError) as exc:
        print(json.dumps({"result": "unproven", "error": str(exc), "exit": 2}) if args.json else f"UNPROVEN — {exc}", file=sys.stderr); return 2


if __name__ == "__main__": raise SystemExit(main())
