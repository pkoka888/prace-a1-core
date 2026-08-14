#!/usr/bin/env python3
"""Build a non-authoritative collector-execution from frozen capture decisions.

The command performs no network access. It binds immutable live or fixture
capture manifests and exact field decisions to the frozen Plan AC v1.1 pack.
Generated executions always have ``collector_proposed`` authority, so the
canonical execution validator must return exit 2 even when every slot has a
typed proposal. Exit 0 from this command means only that generation/checking
succeeded; it never promotes research evidence.
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


ROOT = Path(__file__).resolve().parent.parent
PACK_REF = "research/query-packs/plan-ac-core-1.1.json"
PROTOCOL_REF = "research/query-packs/plan-ac-collector-protocol-1.1.json"
EXECUTION_SCHEMA_REF = "research/query-packs/collector-execution-1.1.schema.json"
INPUT_SCHEMA_REF = "research/query-packs/collector-proposal-input-1.0.schema.json"
CAPTURE_SCHEMA_REF = "research/query-packs/source-capture-result-1.1.schema.json"
IMPLEMENTATION_REF = "scripts/run_collector_proposals.py"
INPUT_PREFIX = "research/acquisition/collector-proposals"
OUTPUT_PREFIX = "research/acquisition/collector-executions"
DENIED_TOP_LEVEL = {
    "a1", "scans", "evidence", "ocr", "data", "output", "runtime",
    "secrets", ".history-remediation",
}


class InvalidProposal(ValueError):
    """The proposal or one of its exact bindings is invalid."""


class Unavailable(RuntimeError):
    """A required immutable input or dependency is unavailable."""


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def semantic_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except (FileNotFoundError, PermissionError, OSError) as exc:
        raise Unavailable(f"cannot read {path}: {exc}") from exc
    return digest.hexdigest()


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, PermissionError, OSError) as exc:
        raise Unavailable(f"cannot read {path}: {exc}") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InvalidProposal(f"invalid JSON in {path}: {exc}") from exc


def contained(
    root: Path, value: str | Path, *, prefix: str | None = None, must_exist: bool = True
) -> Path:
    raw = Path(value)
    if raw.is_absolute():
        raise InvalidProposal(f"path must be relative to --root: {value}")
    path = (root / raw).resolve()
    try:
        relative = path.relative_to(root.resolve())
    except ValueError as exc:
        raise InvalidProposal(f"path escapes --root: {value}") from exc
    if not relative.parts or relative.parts[0] in DENIED_TOP_LEVEL or relative.name == ".env":
        raise InvalidProposal(f"sensitive or runtime path is denied: {value}")
    if prefix:
        expected = Path(prefix)
        try:
            relative.relative_to(expected)
        except ValueError as exc:
            raise InvalidProposal(f"path must be below {prefix}: {value}") from exc
    if must_exist and not path.is_file():
        raise Unavailable(f"required file is unavailable: {relative.as_posix()}")
    return path


def validate_schema(instance: Any, schema: Any, label: str) -> None:
    errors = sorted(
        Draft7Validator(schema, format_checker=FormatChecker()).iter_errors(instance),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        error = errors[0]
        location = "/".join(str(part) for part in error.absolute_path) or "<root>"
        raise InvalidProposal(f"{label} {location}: {error.message}")


def binding(root: Path, ref: str, *, semantic: bool) -> dict[str, str]:
    path = contained(root, ref)
    result = {"path": ref, "byte_sha256": file_sha256(path)}
    if semantic:
        result["semantic_sha256"] = semantic_sha256(read_json(path))
    return result


def normalized(value: str) -> str:
    return " ".join(value.casefold().split())


def _phrase_present(text: str, phrase: str) -> bool:
    """Match a complete Unicode word/identifier phrase, never a substring."""
    candidate = normalized(phrase)
    if not candidate:
        return False
    return re.search(rf"(?<![\w]){re.escape(candidate)}(?![\w])", normalized(text)) is not None


def _numeric_present(text: str, value: int | float) -> bool:
    """Match the exact JSON numeric token (10 != 100; 1 != 1.0)."""
    token = str(value).casefold()
    variants = {token}
    if "." in token:
        variants.add(token.replace(".", ","))
    folded = normalized(text)
    return any(
        re.search(
            rf"(?<![\d.,]){re.escape(candidate)}(?!\d)(?![.,]\d)", folded
        ) is not None
        for candidate in variants
    )


def _one_of(text: str, phrases: tuple[str, ...]) -> bool:
    return any(_phrase_present(text, phrase) for phrase in phrases)


PRICING_PERIOD_ANCHORS = {
    "month": ("month", "monthly", "per month", "měsíc", "měsíčně", "za měsíc"),
    "year": ("year", "yearly", "annual", "annually", "rok", "ročně", "za rok"),
    "one_time": ("one time", "one-time", "jednorázově", "jednorázový"),
    "usage": ("usage", "per use", "využití", "spotřeba"),
    "mixed": ("mixed", "kombinované", "kombinace"),
    "not_disclosed": ("not disclosed", "neuvedeno", "nezveřejněno"),
    "not_applicable": ("not applicable", "nevztahuje se"),
}
PRICING_UNIT_ANCHORS = {
    "document": ("document", "doklad", "dokument"),
    "extraction": ("extraction", "vytěžení"),
    "user": ("user", "uživatel"),
    "organisation": ("organisation", "organization", "organizace", "firma"),
    "subscription": ("subscription", "předplatné", "tarif"),
    "custom": ("custom", "na míru", "individuální"),
    "not_disclosed": ("not disclosed", "neuvedeno", "nezveřejněno"),
    "not_applicable": ("not applicable", "nevztahuje se"),
}
PRICING_VAT_ANCHORS = {
    "included": ("vat included", "including vat", "včetně dph", "s dph"),
    "excluded": ("vat excluded", "excluding vat", "bez dph"),
    "not_registered": ("not vat registered", "neplátce dph"),
    "not_disclosed": ("vat not disclosed", "dph neuvedeno"),
    "not_applicable": ("vat not applicable", "dph se nevztahuje"),
}


def _pricing_has_anchors(text: str, value: dict[str, Any]) -> bool:
    disclosure = value["disclosure_status"]
    disclosure_anchors = {
        "public_from": ("from", "starting at", "od"),
        "public_custom": ("custom", "na míru", "individuální"),
        "not_publicly_disclosed": ("not publicly disclosed", "veřejně neuvedeno"),
        "not_reliably_exposed": ("not reliably exposed", "nelze spolehlivě zjistit"),
    }
    if disclosure in disclosure_anchors and not _one_of(text, disclosure_anchors[disclosure]):
        return False
    currency = value.get("currency")
    if currency is not None and not _phrase_present(text, currency):
        return False
    period = value["billing_period"]
    if not _one_of(text, PRICING_PERIOD_ANCHORS[period]):
        return False
    unit = value["unit"]
    if not _one_of(text, PRICING_UNIT_ANCHORS[unit]):
        return False
    vat = value["vat_status"]
    if not _one_of(text, PRICING_VAT_ANCHORS[vat]):
        return False
    for tier in value["tiers"]:
        if not _phrase_present(text, tier["name"]):
            return False
        for key in ("amount", "included_units", "overage_amount"):
            number = tier.get(key)
            if number is not None and not _numeric_present(text, number):
                return False
    return True


def value_has_exact_lexical_anchor(text: str, value: Any, value_type: str) -> bool:
    """Require the complete proposed scalar/list tokens in the exact byte span.

    The canonical execution validator deliberately supplies only a necessary
    lexical check. This deterministic proposal builder is stricter so adding a
    plausible word to an otherwise fabricated string cannot pass generation.
    """
    folded = normalized(text)
    if value_type == "string":
        return _phrase_present(folded, value)
    if value_type == "string_list":
        return all(_phrase_present(folded, item) for item in value)
    if value_type == "integer":
        return _numeric_present(folded, value)
    if value_type == "date":
        return _phrase_present(folded, value)
    if value_type == "boolean":
        markers = (
            ("true", "supports", "supported", "available", "enabled", "ano")
            if value
            else ("false", "unsupported", "unavailable", "disabled", "does not", "ne")
        )
        return _one_of(folded, markers)
    if value_type == "pricing":
        return _pricing_has_anchors(folded, value)
    return False


def public_url_allowed(url: str, allowed_roots: list[str]) -> bool:
    try:
        from scripts.check_evidence_url import UnsafeURL, validate_public_https_url
        from scripts.compare_research_runs import url_within_root
    except ImportError:
        from check_evidence_url import UnsafeURL, validate_public_https_url
        from compare_research_runs import url_within_root
    try:
        validate_public_https_url(url)
    except UnsafeURL as exc:
        raise InvalidProposal(f"unsafe capture URL {url}: {exc}") from exc
    return any(url_within_root(url, root) for root in allowed_roots)


def render_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _pack_slots(pack: dict[str, Any]) -> tuple[
    dict[str, dict[str, Any]], dict[tuple[str, str], dict[str, Any]], set[tuple[str, str]]
]:
    entities: dict[str, dict[str, Any]] = {}
    fields: dict[tuple[str, str], dict[str, Any]] = {}
    slots: set[tuple[str, str]] = set()
    for lane in pack["lanes"].values():
        for entity in lane["entities"]:
            if entity["id"] in entities:
                raise InvalidProposal(f"duplicate entity in canonical pack: {entity['id']}")
            entities[entity["id"]] = entity
            for field in lane["fields"]:
                slot = (entity["id"], field["id"])
                if slot in slots:
                    raise InvalidProposal(f"duplicate slot in canonical pack: {slot}")
                slots.add(slot)
                fields[slot] = field
    return entities, fields, slots


def _load_capture_manifests(
    root: Path, proposal: dict[str, Any], capture_schema: dict[str, Any]
) -> tuple[dict[str, dict[str, Any]], dict[tuple[str, str], dict[str, Any]]]:
    manifests: dict[str, dict[str, Any]] = {}
    results: dict[tuple[str, str], dict[str, Any]] = {}
    for declared in proposal["capture"]["manifests"]:
        ref = declared["path"]
        if ref in manifests:
            raise InvalidProposal(f"duplicate capture manifest binding: {ref}")
        path = contained(root, ref, prefix="research/acquisition/source-captures")
        manifest = read_json(path)
        validate_schema(manifest, capture_schema, f"capture manifest {ref}")
        if file_sha256(path) != declared["byte_sha256"]:
            raise InvalidProposal(f"capture manifest byte hash mismatch: {ref}")
        if semantic_sha256(manifest) != declared["semantic_sha256"]:
            raise InvalidProposal(f"capture manifest semantic hash mismatch: {ref}")
        if path.parent.name != manifest["run_id"]:
            raise InvalidProposal(f"capture manifest directory/run_id mismatch: {ref}")
        counts = {
            state: sum(row["state"] == state for row in manifest["results"])
            for state in ("captured", "unproven", "invalid")
        }
        if manifest["summary"] != counts:
            raise InvalidProposal(f"capture manifest summary mismatch: {ref}")
        for row in manifest["results"]:
            key = (ref, row["id"])
            if key in results:
                raise InvalidProposal(f"duplicate capture result id in {ref}: {row['id']}")
            results[key] = row
        manifests[ref] = manifest
    return manifests, results


def _capture_source(
    root: Path,
    manifest_ref: str,
    manifest: dict[str, Any],
    row: dict[str, Any],
    entity: dict[str, Any],
) -> tuple[dict[str, Any], bytes]:
    if row["state"] != "captured" or not row.get("excerpt"):
        raise InvalidProposal(f"{manifest_ref}/{row['id']}: captured excerpt required")
    urls = [row["requested_url"]]
    for hop in row["redirect_chain"]:
        urls.extend((hop["from"], hop["to"]))
    urls.append(row["final_url"])
    for url in urls:
        if not public_url_allowed(url, entity["allowed_official_source_roots"]):
            raise InvalidProposal(
                f"{manifest_ref}/{row['id']}: URL is outside {entity['id']} allowed roots: {url}"
            )
    excerpt_ref = (Path(manifest_ref).parent / row["excerpt"]["path"]).as_posix()
    excerpt_path = contained(root, excerpt_ref, prefix="research/acquisition/source-captures")
    raw = excerpt_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != row["excerpt"]["sha256"]:
        raise InvalidProposal(f"{manifest_ref}/{row['id']}: excerpt hash mismatch")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise InvalidProposal(f"{manifest_ref}/{row['id']}: excerpt is not UTF-8") from exc
    if not text.strip() or "\x00" in text:
        raise InvalidProposal(f"{manifest_ref}/{row['id']}: excerpt is empty or unsafe")
    content_type = row.get("content_type")
    if content_type not in {"text/html", "text/plain", "application/json", "application/xhtml+xml"}:
        raise InvalidProposal(f"{manifest_ref}/{row['id']}: unsupported content type")
    source_key = canonical_json([manifest_ref, row["id"], entity["id"]])
    source_id = f"src-{hashlib.sha256(source_key).hexdigest()[:24]}"
    source = {
        "id": source_id,
        "entity_id": entity["id"],
        "capture_manifest_ref": manifest_ref,
        "capture_manifest_sha256": file_sha256(root / manifest_ref),
        "capture_run_id": manifest["run_id"],
        "capture_mode": manifest["mode"],
        "capture_result_id": row["id"],
        "capture_result_sha256": semantic_sha256(row),
        "requested_url": row["requested_url"],
        "final_url": row["final_url"],
        "redirect_chain": row["redirect_chain"],
        "http_status": row["http_status"],
        "retrieved_at": row["retrieved_at"],
        "content_type": content_type,
        "verification_status": "verified" if 200 <= row["http_status"] < 300 else "unverified",
        "response_sha256": row["response_sha256"],
        "excerpt_sha256": row["excerpt"]["sha256"],
        "excerpt_ref": excerpt_ref,
    }
    return source, raw


def build_execution(root: Path, input_ref: str) -> dict[str, Any]:
    input_path = contained(root, input_ref, prefix=INPUT_PREFIX)
    proposal = read_json(input_path)
    validate_schema(proposal, read_json(root / INPUT_SCHEMA_REF), "proposal input")

    pack = read_json(root / PACK_REF)
    protocol = read_json(root / PROTOCOL_REF)
    try:
        from scripts.compare_research_runs import canonical_pack_hash, load_query_pack
    except ImportError:
        from compare_research_runs import canonical_pack_hash, load_query_pack
    load_query_pack(root, root / PACK_REF)
    if canonical_pack_hash(pack) != pack.get("query_pack_hash"):
        raise InvalidProposal("canonical query-pack hash is invalid")
    unsigned_protocol = dict(protocol)
    declared_protocol_digest = unsigned_protocol.pop("config_digest", None)
    if semantic_sha256(unsigned_protocol) != declared_protocol_digest:
        raise InvalidProposal("canonical protocol config_digest is invalid")
    if protocol.get("query_pack_hash") != pack["query_pack_hash"]:
        raise InvalidProposal("canonical protocol is not bound to the query pack")

    entities, fields, expected_slots = _pack_slots(pack)
    capture_schema = read_json(root / CAPTURE_SCHEMA_REF)
    manifests, capture_results = _load_capture_manifests(root, proposal, capture_schema)

    decisions: dict[tuple[str, str], dict[str, Any]] = {}
    for decision in proposal["decisions"]:
        slot = (decision["entity_id"], decision["field_id"])
        if slot not in expected_slots:
            raise InvalidProposal(f"unknown frozen slot: {slot[0]}/{slot[1]}")
        if slot in decisions:
            raise InvalidProposal(f"duplicate field decision: {slot[0]}/{slot[1]}")
        decisions[slot] = decision
    missing = expected_slots - set(decisions)
    if missing:
        first = sorted(missing)[0]
        raise InvalidProposal(
            f"missing decisions for {len(missing)} frozen slots; first: {first[0]}/{first[1]}"
        )
    if len(decisions) != len(expected_slots):
        raise InvalidProposal("decision map does not exactly cover the frozen slots")

    sources: dict[tuple[str, str, str], dict[str, Any]] = {}
    source_raw: dict[tuple[str, str, str], bytes] = {}
    capture_owners: dict[tuple[str, str], str] = {}
    inspections: list[dict[str, Any]] = []
    for slot in sorted(expected_slots):
        decision = decisions[slot]
        entity = entities[slot[0]]
        status = decision["decision"]
        evidence_refs = [
            (item["capture_manifest_ref"], item["capture_result_id"])
            for item in decision["captured_evidence"]
        ]
        if len(evidence_refs) != len(set(evidence_refs)):
            raise InvalidProposal(f"{slot[0]}/{slot[1]}: duplicate captured evidence ref")
        unresolved_refs = [
            (item["capture_manifest_ref"], item["capture_result_id"])
            for item in decision["unproven_capture_refs"]
        ]
        if len(unresolved_refs) != len(set(unresolved_refs)):
            raise InvalidProposal(f"{slot[0]}/{slot[1]}: duplicate unproven capture ref")

        source_ids: list[str] = []
        locators: list[dict[str, str]] = []
        observations: list[dict[str, Any]] = []
        anchors: list[str] = []
        for item in decision["captured_evidence"]:
            ref = (item["capture_manifest_ref"], item["capture_result_id"])
            row = capture_results.get(ref)
            if row is None:
                raise InvalidProposal(f"{slot[0]}/{slot[1]}: capture ref is not bound: {ref}")
            if row["state"] != "captured":
                raise InvalidProposal(f"{slot[0]}/{slot[1]}: captured_evidence points to {row['state']}")
            owner = capture_owners.setdefault(ref, entity["id"])
            if owner != entity["id"]:
                raise InvalidProposal(f"{slot[0]}/{slot[1]}: capture result reused across entities")
            source_key = (ref[0], ref[1], entity["id"])
            if source_key not in sources:
                source, raw = _capture_source(root, ref[0], manifests[ref[0]], row, entity)
                sources[source_key] = source
                source_raw[source_key] = raw
            source = sources[source_key]
            raw = source_raw[source_key]
            start, end = item["excerpt_span"]
            if not 0 <= start < end <= len(raw):
                raise InvalidProposal(f"{slot[0]}/{slot[1]}: excerpt span is out of bounds")
            try:
                selected = raw[start:end].decode("utf-8")
            except UnicodeDecodeError as exc:
                raise InvalidProposal(f"{slot[0]}/{slot[1]}: excerpt span splits UTF-8") from exc
            if selected != item["supporting_text"]:
                raise InvalidProposal(f"{slot[0]}/{slot[1]}: supporting_text is not the exact byte span")
            anchor = normalized(item["lexical_anchor"])
            if not anchor or anchor not in normalized(selected):
                raise InvalidProposal(f"{slot[0]}/{slot[1]}: lexical anchor is absent from exact span")
            if status == "does_not_establish" and "value" in item:
                raise InvalidProposal(f"{slot[0]}/{slot[1]}: does_not_establish cannot propose a value")
            if status != "does_not_establish" and "value" not in item:
                raise InvalidProposal(f"{slot[0]}/{slot[1]}: {status} requires a typed value per source")
            if status != "does_not_establish" and not value_has_exact_lexical_anchor(
                selected, item["value"], fields[slot]["value_type"]
            ):
                raise InvalidProposal(
                    f"{slot[0]}/{slot[1]}: exact excerpt does not contain the complete proposed value"
                )
            source_ids.append(source["id"])
            locators.append({"source_id": source["id"], "locator": item["lexical_anchor"]})
            anchors.append(item["lexical_anchor"])
            if status != "does_not_establish":
                observations.append({
                    "source_id": source["id"],
                    "value": item["value"],
                    "excerpt_span": item["excerpt_span"],
                    "supporting_text": item["supporting_text"],
                })

        unproven_urls: list[str] = []
        for ref in unresolved_refs:
            row = capture_results.get(ref)
            if row is None:
                raise InvalidProposal(f"{slot[0]}/{slot[1]}: unproven capture ref is not bound: {ref}")
            if row["state"] not in {"unproven", "invalid"}:
                raise InvalidProposal(f"{slot[0]}/{slot[1]}: unproven ref points to captured result")
            if not public_url_allowed(row["requested_url"], entity["allowed_official_source_roots"]):
                raise InvalidProposal(
                    f"{slot[0]}/{slot[1]}: unproven URL is outside entity allowed roots"
                )
            unproven_urls.append(row["requested_url"])

        reason = decision["reason"]
        if unproven_urls:
            reason += " Unproven capture requests: " + ", ".join(sorted(unproven_urls)) + "."
        fallback_anchor = f"field {slot[1].replace('_', ' ')} inspection"
        terms = list(dict.fromkeys(anchors)) or [fallback_anchor]
        inspections.append({
            "entity_id": slot[0],
            "field_id": slot[1],
            "source_ids": source_ids,
            "locators": locators,
            "observations": observations,
            "inspected_sections": terms,
            "query_terms": terms,
            "support_status": {
                "supports": "proven",
                "does_not_establish": "does_not_establish",
                "conflict": "conflicted",
            }[status],
            "reason": reason,
        })

    collector = proposal["collector"]
    if (collector["provider"] is None) != (collector["model"] is None):
        raise InvalidProposal("collector provider and model must both be set or both be null")
    input_relative = input_path.relative_to(root).as_posix()
    execution = {
        "format_version": "collector-execution-1.1",
        "evidence_scope": "collector_proposal_not_market_evidence",
        "run_id": proposal["run_id"],
        "execution_instance_id": proposal["execution_instance_id"],
        "authority_classification": "collector_proposed",
        "operator_attestation": None,
        "query_pack": binding(root, PACK_REF, semantic=True),
        "protocol": binding(root, PROTOCOL_REF, semantic=True),
        "contract_schema": binding(root, EXECUTION_SCHEMA_REF, semantic=True),
        "collector": {
            "collector_id": collector["collector_id"],
            "provider": collector["provider"],
            "model": collector["model"],
            "identity_verification": "unverified",
            "config_digest": semantic_sha256(proposal),
            "implementation": binding(root, IMPLEMENTATION_REF, semantic=False),
            "prompt": {**binding(root, PROTOCOL_REF, semantic=False), "version": "protocol-1.1"},
            "config": {
                **binding(root, input_relative, semantic=False),
                "version": "collector-proposal-input-1.0",
            },
            "tools": collector["tools"],
        },
        "capture": {
            "started_at": proposal["capture"]["started_at"],
            "completed_at": proposal["capture"]["completed_at"],
        },
        "sources": [sources[key] for key in sorted(sources)],
        "inspections": inspections,
    }
    try:
        from scripts.validate_collector_execution import validate_execution
    except ImportError:
        from validate_collector_execution import validate_execution
    try:
        remains_unproven = validate_execution(
            root, execution, read_json(root / EXECUTION_SCHEMA_REF)
        )
    except ValueError as exc:
        raise InvalidProposal(f"generated execution contract: {exc}") from exc
    except RuntimeError as exc:
        raise Unavailable(f"generated execution could not be verified: {exc}") from exc
    if remains_unproven is not True:
        raise InvalidProposal("collector-proposed execution unexpectedly reached authoritative exit 0")
    return execution


def run(root: Path, input_ref: str, output_ref: str, *, check: bool) -> Path:
    root = root.resolve()
    output = contained(root, output_ref, prefix=OUTPUT_PREFIX, must_exist=check)
    expected = render_bytes(build_execution(root, input_ref))
    if check:
        try:
            actual = output.read_bytes()
        except (PermissionError, OSError) as exc:
            raise Unavailable(f"cannot read output {output}: {exc}") from exc
        if actual != expected:
            raise InvalidProposal("output is stale or does not match the exact proposal rendering")
        return output
    if output.exists():
        raise InvalidProposal(f"output already exists; refusing overwrite: {output.relative_to(root)}")
    atomic_write(output, expected)
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--input", required=True, help=f"input below {INPUT_PREFIX}/")
    parser.add_argument("--output", required=True, help=f"output below {OUTPUT_PREFIX}/")
    parser.add_argument("--check", action="store_true", help="read-only exact freshness check")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        output = run(args.root, args.input, args.output, check=args.check)
    except Unavailable as exc:
        payload = {"status": "unproven", "exit_code": 2, "detail": str(exc)}
        code = 2
    except (InvalidProposal, OSError) as exc:
        payload = {"status": "invalid", "exit_code": 1, "detail": str(exc)}
        code = 1
    else:
        payload = {
            "status": "current" if args.check else "generated",
            "exit_code": 0,
            "detail": output.relative_to(args.root.resolve()).as_posix(),
            "execution_validator_expected_exit": 2,
        }
        code = 0
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    else:
        print(f"{payload['status'].upper()} — {payload['detail']}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
