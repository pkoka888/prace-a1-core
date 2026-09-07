#!/usr/bin/env python3
"""Safe adapter boundary for benchmark prompt preparation and manual result import.

This file never executes a skill document or calls a model/provider. A draft corpus
may be previewed with ``dry-run``; preparation/import refuse until scoring-ready.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import ipaddress
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from jsonschema import Draft7Validator, FormatChecker
from validate_and_score import validate as validate_benchmark

DEFAULT_DIR = Path(__file__).resolve().parent


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_bytes(value: object) -> bytes:
    """Return the one serialization used for all detached canonical hashes."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def contained(path: Path, root: Path) -> Path:
    resolved, allowed = path.resolve(), (root / "comparative-runs").resolve()
    if resolved != allowed and allowed not in resolved.parents:
        raise ValueError("output must remain under benchmark comparative-runs/")
    return resolved


def schema_failures(instance: object, schema: object) -> list[str]:
    validator = Draft7Validator(schema, format_checker=FormatChecker())
    return [
        f"{'/'.join(map(str, error.absolute_path)) or '<root>'}: {error.message}"
        for error in sorted(validator.iter_errors(instance), key=lambda item: list(item.absolute_path))
    ]


def prompts(bench: Path) -> list[dict]:
    corpus = read(bench / "questions.json")
    result = []
    for q in corpus["public_questions"]:
        if any(k in q for k in ("gold_answer", "answer", "atomic_claims", "evidence_refs")):
            raise ValueError(f"{q.get('id')}: embedded gold is forbidden")
        result.append({"question_id": q["id"], "prompt": q["prompt"], "expected_fields": q["expected_fields"], "instructions": ["Use public sources only.", "Return atomic claims with HTTPS citations.", "Abstain rather than infer unavailable facts."]})
    return result


def readiness(bench: Path) -> tuple[int, str]:
    """Use the canonical benchmark validator; STATUS.json alone is never a gate."""
    errors, unproven, context = validate_benchmark(bench)
    if errors:
        return 1, "invalid: " + "; ".join(errors)
    if unproven or context.get("status") != "scoring-ready":
        return 2, "unproven: " + "; ".join(unproven or ["benchmark is not scoring-ready"])
    return 0, "scoring-ready"


def prepared_payload(public_prompts: list[dict]) -> dict:
    return {"benchmark_version": "0.2.0", "prompts": public_prompts}


def validate_result_semantics(payload: dict, expected_ids: set[str]) -> list[str]:
    errors: list[str] = []
    result_ids = [item["question_id"] for item in payload["results"]]
    processed = payload["questions_processed"]
    if set(result_ids) != expected_ids or len(result_ids) != len(expected_ids):
        errors.append(f"results must contain exactly all {len(expected_ids)} public question IDs")
    if set(processed) != expected_ids or len(processed) != len(expected_ids):
        errors.append(f"questions_processed must contain exactly all {len(expected_ids)} public question IDs")
    if result_ids != processed:
        errors.append("results and questions_processed must use the same deterministic order")
    claim_ids: list[str] = []
    for result in payload["results"]:
        claims = result["claims"]
        if result["abstained"] and claims:
            errors.append(f"{result['question_id']}: an abstention cannot contain claims")
        if not result["abstained"] and not claims:
            errors.append(f"{result['question_id']}: a non-abstention must contain at least one claim")
        claim_ids.extend(claim["claim_id"] for claim in claims)
    duplicates = sorted({claim_id for claim_id in claim_ids if claim_ids.count(claim_id) > 1})
    if duplicates:
        errors.append(f"duplicate system claim IDs: {duplicates}")
    return errors


def detached_result_hash(payload: dict) -> str:
    """Hash a result with its self-referential output_hash member removed."""
    detached = copy.deepcopy(payload)
    detached["processing_metadata"].pop("output_hash", None)
    return sha256(canonical_bytes(detached))


def public_https_error(url: str) -> str | None:
    """Reject credential-bearing and plainly local/private citation targets offline."""
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname:
        return "must be an absolute HTTPS URL"
    if parsed.username is not None or parsed.password is not None:
        return "must not contain credentials"
    hostname = parsed.hostname.rstrip(".").lower()
    if hostname == "localhost" or hostname.endswith(".localhost"):
        return "must not target localhost"
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return None
    if not address.is_global:
        return "must not target a non-global IP address"
    return None


def validate_import(
    bench: Path,
    source: Path,
    manifest_path: Path,
    prepared_path: Path,
    public_prompts: list[dict],
) -> tuple[dict, bytes]:
    source = contained(source, bench)
    manifest_path = contained(manifest_path, bench)
    prepared_path = contained(prepared_path, bench)
    if len({source, manifest_path, prepared_path}) != 3:
        raise ValueError("input, manifest, and prepared prompt paths must be distinct")

    expected_prepared = prepared_payload(public_prompts)
    actual_prepared = read(prepared_path)
    if actual_prepared != expected_prepared:
        raise ValueError("prepared prompt package is stale or does not match the current public corpus")
    prompt_hash = sha256(canonical_bytes(actual_prepared))

    payload = read(source)
    result_schema = read(bench / "schemas/system_results_schema.json")
    failures = schema_failures(payload, result_schema)
    if failures:
        raise ValueError("invalid system result: " + "; ".join(failures))
    failures = validate_result_semantics(payload, {item["question_id"] for item in public_prompts})
    for result in payload["results"]:
        for claim in result["claims"]:
            for url in claim["citation_urls"]:
                if issue := public_https_error(url):
                    failures.append(f"{result['question_id']}/{claim['claim_id']}: citation URL {issue}")
    if failures:
        raise ValueError("invalid system result: " + "; ".join(failures))

    manifest = read(manifest_path)
    manifest_schema = read(bench / "comparative-runs/run-manifest.schema.json")
    failures = schema_failures(manifest, manifest_schema)
    if failures:
        raise ValueError("invalid completed run manifest: " + "; ".join(failures))
    if manifest["record_state"] != "completed":
        raise ValueError("run manifest must be completed")
    if manifest["run_id"] != payload["result_id"]:
        raise ValueError("manifest run_id must equal result_id")
    info = payload["system_info"]
    if info["provider"] != manifest["provider"] or info["system_name"] != manifest["product"]:
        raise ValueError("manifest provider/product do not match system_info")
    if info["mode"] != "manual-export" or info["model"] != manifest["model"]:
        raise ValueError("manifest operation/model do not match system_info")
    if manifest["access_basis"]["verified_on"] != manifest["run_date"]:
        raise ValueError("zero-cost access must be verified on the run date")
    if date.fromisoformat(manifest["run_date"]) > datetime.now(tz=timezone.utc).date():
        raise ValueError("run date cannot be in the future")
    for source_item in manifest["inputs"]["source_bundle"]:
        if issue := public_https_error(source_item["url"]):
            raise ValueError(f"source bundle URL {issue}")

    metadata = payload["processing_metadata"]
    if metadata["input_hash"] != prompt_hash or manifest["inputs"]["public_prompt_sha256"] != prompt_hash:
        raise ValueError("prepared prompt hash does not match result and manifest")
    detached_hash = detached_result_hash(payload)
    if metadata["output_hash"] != detached_hash:
        raise ValueError("result output_hash does not match detached canonical result")
    raw_hash = sha256(source.read_bytes())
    encoded = canonical_bytes(payload)
    canonical_hash = sha256(encoded)
    if manifest["outputs"]["raw_export_sha256"] != raw_hash:
        raise ValueError("manifest raw export hash does not match input bytes")
    if manifest["outputs"]["canonical_result_sha256"] != canonical_hash:
        raise ValueError("manifest canonical result hash does not match normalized output")
    return payload, encoded


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare or import benchmark runs without executing agents/models")
    parser.add_argument("command", nargs="?", choices=["dry-run", "prepare", "import"])
    parser.add_argument("--dry-run", action="store_true", help="Compatibility alias for the dry-run command")
    parser.add_argument("--benchmark-dir", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--prepared", type=Path)
    args = parser.parse_args()
    if args.dry_run:
        if args.command and args.command != "dry-run":
            parser.error("--dry-run cannot be combined with prepare/import")
        args.command = "dry-run"
    if not args.command:
        parser.error("a command is required")
    bench = args.benchmark_dir.resolve()
    try:
        prepared = prompts(bench)
        ready_code, ready_message = readiness(bench)
        if args.command == "dry-run":
            public_status = "scoring-ready" if ready_code == 0 else "invalid" if ready_code == 1 else "unproven"
            print(json.dumps({"status": public_status, "prompts": prepared}, ensure_ascii=False, indent=2))
            return ready_code
        if ready_code:
            print(f"REFUSE: {ready_message}", file=sys.stderr)
            return ready_code
        if args.command == "prepare":
            if not args.output:
                raise ValueError("prepare requires --output")
            target = contained(args.output, bench); target.parent.mkdir(parents=True, exist_ok=True)
            payload = prepared_payload(prepared)
            encoded = canonical_bytes(payload)
            target.write_bytes(encoded + b"\n")
            print(json.dumps({"prepared": str(target), "sha256": sha256(encoded), "question_count": len(prepared)}))
            return 0
        if not args.input or not args.output or not args.manifest or not args.prepared:
            raise ValueError("import requires --input, --output, --manifest, and --prepared")
        source = contained(args.input, bench)
        target = contained(args.output, bench)
        if target in {source, contained(args.manifest, bench), contained(args.prepared, bench)}:
            raise ValueError("output must be distinct from input, manifest, and prepared prompt package")
        _, encoded = validate_import(bench, source, args.manifest, args.prepared, prepared)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(encoded + b"\n")
        print(json.dumps({"imported": str(target), "sha256": sha256(encoded)}))
        return 0
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
