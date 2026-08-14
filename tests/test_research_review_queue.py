#!/usr/bin/env python3
"""Adversarial tests for the non-authoritative Plan AC review queue."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from _research_tmp import REPO, build_tmp_root, load, processed


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return build_tmp_root(tmp_path)


def candidate(root: Path) -> Path:
    source = load(REPO / "tests" / "fixtures" / "research" / "envelope_partial.json")
    source["query_version"] = "1.0.0"
    path = processed(root) / "candidate.json"
    path.write_text(json.dumps(source, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def query_pack(root: Path) -> Path:
    return root / "research" / "query-packs" / "plan-ac-core-1.0.json"


def run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(root / "scripts" / "generate_research_review_queue.py"),
         "--root", str(root), *args],
        capture_output=True, text=True, timeout=30,
    )


def base_args(root: Path) -> tuple[str, ...]:
    return (
        "--input", str(candidate(root)),
        "--query-pack", str(query_pack(root)),
        "--output", "research/review/generated/queue.json",
    )


def test_generates_one_blank_task_per_entity_claim_and_evidence(root: Path):
    args = base_args(root)
    result = run(root, *args)
    assert result.returncode == 0, result.stderr
    queue = load(root / "research" / "review" / "generated" / "queue.json")
    source = load(processed(root) / "candidate.json")
    assert queue["task_counts"] == {
        "entity": len(source["entities"]),
        "claim": sum(len(entity["claims"]) for entity in source["entities"]),
        "source_integrity": len({item["canonical_url"] for item in source["evidence"]}),
        "total": len(queue["tasks"]),
    }
    assert all(value is None for task in queue["tasks"] for value in task["operator"].values())
    assert all(task["source_access_date"] for task in queue["tasks"])


def test_hashes_bind_exact_candidate_and_query_pack_bytes(root: Path):
    args = base_args(root)
    assert run(root, *args).returncode == 0
    queue = load(root / "research" / "review" / "generated" / "queue.json")
    assert queue["input_binding"]["sha256"] == hashlib.sha256((processed(root) / "candidate.json").read_bytes()).hexdigest()
    assert queue["query_pack_binding"]["sha256"] == hashlib.sha256(query_pack(root).read_bytes()).hexdigest()
    assert queue["query_pack_binding"]["query_pack_hash"]


def test_output_is_deterministic_and_check_is_read_only(root: Path):
    args = base_args(root)
    assert run(root, *args).returncode == 0
    output = root / "research/review/generated/queue.json"
    first = output.read_bytes()
    assert run(root, *args).returncode == 0
    assert output.read_bytes() == first
    before = output.stat().st_mtime_ns
    checked = run(root, *args, "--check")
    assert checked.returncode == 0, checked.stderr
    assert output.read_bytes() == first and output.stat().st_mtime_ns == before


def test_check_rejects_modified_operator_verdict_without_rewriting(root: Path):
    args = base_args(root)
    assert run(root, *args).returncode == 0
    output = root / "research/review/generated/queue.json"
    changed = load(output)
    changed["tasks"][0]["operator"]["verdict"] = "approve"
    output.write_text(json.dumps(changed), encoding="utf-8")
    before = output.read_bytes()
    checked = run(root, *args, "--check")
    assert checked.returncode == 1
    assert output.read_bytes() == before


def test_query_version_mismatch_fails_without_output(root: Path):
    c = candidate(root)
    changed = load(c)
    changed["query_version"] = "9.0.0"
    c.write_text(json.dumps(changed), encoding="utf-8")
    q = query_pack(root)
    output = root / "research/review/generated/queue.json"
    result = run(root, "--input", str(c), "--query-pack", str(q), "--output", str(output))
    assert result.returncode == 1
    assert not output.exists()


def test_missing_query_pack_is_unproven(root: Path):
    c = candidate(root)
    result = run(root, "--input", str(c), "--query-pack", "research/review/missing.json")
    assert result.returncode == 2


@pytest.mark.parametrize("output", ["../escaped.json", "research/processed/queue.json"])
def test_output_containment_is_enforced(root: Path, output: str):
    c = candidate(root)
    q = query_pack(root)
    result = run(root, "--input", str(c), "--query-pack", str(q), "--output", output)
    assert result.returncode == 1


def test_invalid_candidate_refused_and_not_modified(root: Path):
    c = candidate(root)
    bad = load(c)
    bad["schema_version"] = "1.1"
    c.write_text(json.dumps(bad), encoding="utf-8")
    before = c.read_bytes()
    q = query_pack(root)
    result = run(root, "--input", str(c), "--query-pack", str(q), "--output", "research/review/generated/queue.json")
    assert result.returncode == 1
    assert c.read_bytes() == before
    assert not (root / "research/review/generated/queue.json").exists()


def atomic_candidate(root: Path) -> Path:
    pack = load(query_pack(root))
    results = []
    evidence = []
    for lane, lane_definition in pack["lanes"].items():
        for entity_id in lane_definition["expected_entity_ids"]:
            for field in lane_definition["fields"]:
                evidence_id = f"ev-{entity_id}-{field['id']}"
                evidence.append({
                    "id": evidence_id,
                    "entity_id": entity_id,
                    "field_id": field["id"],
                    "url": f"https://example.com/{entity_id}/{field['id']}",
                    "evidence_class": "official_primary",
                    "verification_status": "verified",
                    "retrieved_at": "2026-08-14",
                })
                string_value = (
                    f"https://example.com/{entity_id}"
                    if field["id"] in {"canonical_repository", "canonical_product_url"}
                    else "synthetic-value"
                )
                values = {
                    "boolean": True, "date": "2026-08-01", "integer": 42,
                    "number": 1.5, "string": string_value, "string_list": ["JSON"],
                }
                results.append({
                    "entity_id": entity_id,
                    "lane": lane,
                    "field_id": field["id"],
                    "result_status": "proven",
                    "value": values[field["value_type"]],
                    "evidence_refs": [evidence_id],
                    "verification_status": "verified",
                    "applicability": "direct",
                    "pricing_status": "public_exact" if field["importance"] == "pricing" else None,
                })
    payload = {
        "format_version": "atomic-results-1.0",
        "query_pack_version": pack["query_pack_version"],
        "query_pack_hash": pack["query_pack_hash"],
        "run_id": "synthetic-atomic-review-run",
        "as_of": "2026-08-14",
        "results": results,
        "evidence": evidence,
    }
    path = processed(root) / "atomic-results.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def atomic_v11_candidate(root: Path) -> tuple[Path, Path]:
    """Build the entire frozen 20-entity v1.1 roster using synthetic facts."""
    pack_path = root / "research/query-packs/plan-ac-core-1.1.json"
    pack = load(pack_path)
    results, evidence = [], []
    controlled = {
        "czech_ocr_support_level": "native_documented",
        "invoice_extraction_level": "native_invoice_fields",
        "business_use_evidence_level": "documented_invoice_workflow",
        "structured_output_ids": ["json", "xml"],
        "accounting_system_ids": ["pohoda"],
        "export_format_ids": ["csv", "isdoc"],
        "target_customer_segments": ["accounting_firm", "smb"],
    }
    pricing = {
        "disclosure_status": "public_exact", "currency": "CZK",
        "vat_status": "excluded", "billing_period": "month",
        "unit": "subscription",
        "tiers": [{"name": "Synthetic", "amount": 100, "included_units": 10,
                   "overage_amount": 5}],
        "notes": "Synthetic structured review value",
    }
    defaults = {
        "boolean": True, "integer": 42, "number": 1.5,
        "date": "2026-08-01", "string": "MIT", "string_list": ["other"],
        "pricing": pricing,
    }
    for lane, definition in pack["lanes"].items():
        for entity in definition["entities"]:
            for field in definition["fields"]:
                not_applicable = lane == "oss_invoice" and field["id"] == "pricing"
                evidence_id = f"ev-{entity['id']}-{field['id']}"
                evidence_refs = [] if not_applicable else [evidence_id]
                confidence = "not_applicable" if not_applicable else (
                    "repository_metadata_verified" if field["id"] == "github_stars"
                    else "source_verified_self_reported"
                )
                if not not_applicable:
                    evidence.append({
                        "id": evidence_id, "entity_id": entity["id"],
                        "field_id": field["id"], "url": entity["canonical_root_url"],
                        "evidence_class": ("repository_metadata"
                                           if field["id"] == "github_stars"
                                           else "official_primary"),
                        "verification_status": "verified",
                        "retrieved_at": "2026-08-14T03:00:00Z",
                        "locator": f"synthetic:{field['id']}",
                    })
                result = {
                    "entity_id": entity["id"], "lane": lane,
                    "field_id": field["id"],
                    "result_status": "not_applicable" if not_applicable else "proven",
                    "value": None if not_applicable else controlled.get(
                        field["id"], defaults[field["value_type"]]
                    ),
                    "evidence_refs": evidence_refs,
                    "verification_status": "verified",
                    "applicability": "not_applicable" if not_applicable else "direct",
                    "enumeration_scope": (
                        "not_applicable" if not field.get("requires_enumeration_scope")
                        else "complete_for_frozen_sources"
                    ),
                    "claim_confidence": confidence,
                }
                if field["comparison_rule"] == "snapshot":
                    result["captured_at"] = "2026-08-14T03:30:00Z"
                results.append(result)
    payload = {
        "format_version": "atomic-results-1.1",
        "query_pack_version": pack["query_pack_version"],
        "query_pack_hash": pack["query_pack_hash"],
        "run_id": "synthetic-v11-operator-review",
        "as_of": "2026-08-14",
        "provenance": {
            "collector_id": "synthetic-collector-b",
            "collector_kind": "agent", "execution_instance_id": "synthetic-instance-b",
            "identity_verification": "operator_attested", "config_digest": "b" * 64,
            "collection_method": "agent_assisted",
            "source_policy_version": pack["source_policy_version"],
            "started_at": "2026-08-14T03:00:00Z",
            "completed_at": "2026-08-14T04:00:00Z",
            "provider": "synthetic-test-provider", "model": "synthetic-test-model",
        },
        "results": results, "evidence": evidence,
    }
    path = processed(root) / "atomic-results-v11.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path, pack_path


def test_validated_atomic_results_generate_and_check(root: Path):
    source = atomic_candidate(root)
    output = "research/review/generated/atomic-queue.json"
    args = ("--input", str(source), "--query-pack", str(query_pack(root)), "--output", output)
    generated = run(root, *args)
    assert generated.returncode == 0, generated.stderr
    queue = load(root / output)
    atomic = load(source)
    assert queue["input_binding"]["format_version"] == "atomic-results-1.0"
    assert queue["task_counts"]["entity"] == 20
    assert queue["task_counts"]["claim"] == len(atomic["results"])
    assert queue["task_counts"]["source_integrity"] == len(atomic["evidence"])
    assert all(value is None for task in queue["tasks"] for value in task["operator"].values())
    canonical = processed(root) / "entities.json"
    before = canonical.read_bytes()
    checked = run(root, *args, "--check")
    assert checked.returncode == 0, checked.stderr
    assert canonical.read_bytes() == before


def test_atomic_pack_hash_mismatch_is_refused(root: Path):
    source = atomic_candidate(root)
    payload = load(source)
    payload["query_pack_hash"] = "0" * 64
    source.write_text(json.dumps(payload), encoding="utf-8")
    output = root / "research/review/generated/refused.json"
    result = run(root, "--input", str(source), "--query-pack", str(query_pack(root)),
                 "--output", str(output))
    assert result.returncode == 1
    assert not output.exists()


def test_v11_full_roster_preserves_structured_values_confidence_and_provenance(root: Path):
    source, pack = atomic_v11_candidate(root)
    output = root / "research/review/generated/v11-queue.json"
    generated = run(root, "--input", str(source), "--query-pack", str(pack),
                    "--output", str(output))
    assert generated.returncode == 0, generated.stderr
    queue = load(output)
    payload = load(source)
    assert queue["input_binding"]["format_version"] == "atomic-results-1.1"
    assert queue["collection_provenance"] == payload["provenance"]
    assert queue["task_counts"] == {
        "entity": 20, "claim": len(payload["results"]),
        "source_integrity": 20,
        "total": 20 + len(payload["results"]) + 20,
    }
    pricing = next(task for task in queue["tasks"]
                   if task["task_type"] == "claim"
                   and task["cohort"] == "czech_invoice_software"
                   and task["claim_field"] == "pricing")
    assert pricing["claim_value"]["tiers"][0]["amount"] == 100
    assert pricing["claim_confidence"] == "source_verified_self_reported"
    snapshot = next(task for task in queue["tasks"]
                    if task.get("claim_field") == "github_stars")
    assert snapshot["claim_confidence"] == "repository_metadata_verified"
    assert snapshot["claim_provenance"]["captured_at"] == "2026-08-14T03:30:00Z"
    assert all(value is None for task in queue["tasks"]
               for value in task["operator"].values())
    # One URL per frozen entity is deliberately shared by all its evidence.
    # The URL is deduped while every evidence record remains exactly linked.
    source_tasks = [task for task in queue["tasks"]
                    if task["task_type"] == "source_integrity"]
    linked = [evidence_id for task in source_tasks for evidence_id in task["evidence_ids"]]
    assert sorted(linked) == sorted(item["id"] for item in payload["evidence"])
    assert len(linked) == len(set(linked))
    assert run(root, "--input", str(source), "--query-pack", str(pack),
               "--output", str(output), "--check").returncode == 0


def test_v11_response_exactly_binds_queue_and_candidate_provenance(root: Path):
    source, pack = atomic_v11_candidate(root)
    queue = root / "research/review/generated/v11-response-queue.json"
    assert run(root, "--input", str(source), "--query-pack", str(pack),
               "--output", str(queue)).returncode == 0
    response = response_for(root, queue)
    assert run_response(root, queue, response).returncode == 0
    changed = load(source)
    changed["provenance"]["collector_id"] = "different-collector"
    source.write_text(json.dumps(changed), encoding="utf-8")
    refused = run_response(root, queue, response)
    assert refused.returncode == 1
    assert "stale" in refused.stderr


def test_cross_version_pack_result_pair_is_refused(root: Path):
    source, _ = atomic_v11_candidate(root)
    output = root / "research/review/generated/cross-version.json"
    result = run(root, "--input", str(source), "--query-pack", str(query_pack(root)),
                 "--output", str(output))
    assert result.returncode == 1
    assert not output.exists()


@pytest.mark.parametrize("unsafe", [
    "http://example.com/source", "https://localhost/source",
    "https://127.0.0.1/source", "https://169.254.169.254/latest/meta-data",
    "https://user:pass@example.com/source", "https://2130706433/source",
])
def test_atomic_unsafe_or_non_https_evidence_is_refused(root: Path, unsafe: str):
    source = atomic_candidate(root)
    payload = load(source)
    payload["evidence"][0]["url"] = unsafe
    source.write_text(json.dumps(payload), encoding="utf-8")
    output = root / "research/review/generated/unsafe.json"
    result = run(root, "--input", str(source), "--query-pack", str(query_pack(root)),
                 "--output", str(output))
    assert result.returncode == 1
    assert not output.exists()


def test_atomic_sources_are_deduplicated_and_claims_link_all_evidence(root: Path):
    source = atomic_candidate(root)
    payload = load(source)
    result_row = payload["results"][0]
    original = next(item for item in payload["evidence"]
                    if item["id"] == result_row["evidence_refs"][0])
    second = dict(original, id=original["id"] + "-second")
    payload["evidence"].append(second)
    result_row["evidence_refs"].append(second["id"])
    source.write_text(json.dumps(payload), encoding="utf-8")
    output = "research/review/generated/deduped.json"
    generated = run(root, "--input", str(source), "--query-pack", str(query_pack(root)),
                    "--output", output)
    assert generated.returncode == 0, generated.stderr
    queue = load(root / output)
    source_tasks = [task for task in queue["tasks"] if task["task_type"] == "source_integrity"]
    assert len(source_tasks) == len({item["url"] for item in payload["evidence"]})
    claim = next(task for task in queue["tasks"]
                 if task["task_id"] == f"claim::{result_row['entity_id']}::{result_row['field_id']}")
    assert claim["evidence_ids"] == result_row["evidence_refs"]
    assert len(claim["source_task_ids"]) == 1
    linked = next(task for task in source_tasks if task["task_id"] == claim["source_task_ids"][0])
    assert set(result_row["evidence_refs"]).issubset(linked["evidence_ids"])


def response_for(root: Path, queue_path: Path) -> Path:
    queue = load(queue_path)
    value = {
        "response_version": "1.0",
        "authority": "non_authoritative_operator_review_response",
        "queue_binding": {
            "path": queue_path.relative_to(root).as_posix(),
            "sha256": hashlib.sha256(queue_path.read_bytes()).hexdigest(),
            "queue_version": queue["queue_version"],
        },
        "responses": [{
            "task_id": task["task_id"], "reviewer_id": "operator-01",
            "reviewed_at": datetime.now(timezone.utc).isoformat(), "verdict": "confirmed",
            "notes": None, "replacement_source_url": None,
        } for task in queue["tasks"]],
    }
    path = root / "research/review/generated/response.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def run_response(root: Path, queue: Path, response: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([
        sys.executable, str(root / "scripts/validate_research_review_response.py"),
        "--root", str(root), "--queue", str(queue), "--input", str(response), "--json",
    ], capture_output=True, text=True, timeout=30)


def test_completed_response_is_separate_exact_and_non_authoritative(root: Path):
    source = atomic_candidate(root)
    queue = root / "research/review/generated/atomic.json"
    assert run(root, "--input", str(source), "--query-pack", str(query_pack(root)),
               "--output", str(queue)).returncode == 0
    queue_before, candidate_before = queue.read_bytes(), source.read_bytes()
    response = response_for(root, queue)
    checked = run_response(root, queue, response)
    assert checked.returncode == 0, checked.stderr
    assert json.loads(checked.stdout)["authority"] == "non_authoritative_operator_review_response"
    assert queue.read_bytes() == queue_before and source.read_bytes() == candidate_before


@pytest.mark.parametrize("mutation", [
    "missing", "duplicate", "extra", "stale", "unsafe", "verdict", "date",
])
def test_completed_response_fails_closed(root: Path, mutation: str):
    source = atomic_candidate(root)
    queue = root / "research/review/generated/atomic.json"
    assert run(root, "--input", str(source), "--query-pack", str(query_pack(root)),
               "--output", str(queue)).returncode == 0
    response = response_for(root, queue)
    value = load(response)
    if mutation == "missing":
        value["responses"].pop()
    elif mutation == "duplicate":
        value["responses"].append(dict(value["responses"][0]))
    elif mutation == "extra":
        value["responses"][0]["task_id"] = "unknown-task"
    elif mutation == "stale":
        value["queue_binding"]["sha256"] = "0" * 64
    elif mutation == "unsafe":
        value["responses"][0].update(
            verdict="replacement_proposed", replacement_source_url="https://127.0.0.1/private"
        )
    elif mutation == "verdict":
        value["responses"][0]["verdict"] = "approve"
    else:
        value["responses"][0]["reviewed_at"] = "yesterday"
    response.write_text(json.dumps(value), encoding="utf-8")
    assert run_response(root, queue, response).returncode == 1


@pytest.mark.parametrize("reviewed_at", ["2026-08-14T02:59:59Z", "2999-01-01T00:00:00Z"])
def test_v11_response_rejects_precollection_or_future_review_time(root: Path, reviewed_at: str):
    source, pack = atomic_v11_candidate(root)
    queue = root / "research/review/generated/v11-time-queue.json"
    assert run(root, "--input", str(source), "--query-pack", str(pack),
               "--output", str(queue)).returncode == 0
    response = response_for(root, queue)
    payload = load(response)
    payload["responses"][0]["reviewed_at"] = reviewed_at
    response.write_text(json.dumps(payload), encoding="utf-8")
    checked = run_response(root, queue, response)
    assert checked.returncode == 1
    assert "predates" in checked.stderr or "future" in checked.stderr
