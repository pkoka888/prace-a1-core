from __future__ import annotations

import json
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/compare_research_runs.py"


def run(tmp_path: Path, mutate=None):
    project = tmp_path / "project"
    (project / "research/acquisition").mkdir(parents=True)
    shutil.copytree(ROOT / "research/schemas", project / "research/schemas")
    shutil.copytree(ROOT / "scripts", project / "scripts")
    (project / "research/processed").mkdir(parents=True)
    shutil.copy2(ROOT / "research/processed/entities.json", project / "research/processed/entities.json")
    for name in ("left", "right"):
        shutil.copytree(ROOT / "research/acquisition/raw", project / f"research/acquisition/{name}")
    if mutate:
        mutate(project)
    result = subprocess.run([
        sys.executable, str(project / "scripts/compare_research_runs.py"),
        "--root", str(project), "--left-dir", "research/acquisition/left",
        "--right-dir", "research/acquisition/right", "--output", "research/processed/comparison.json",
    ], text=True, capture_output=True)
    return result, project


def test_identical_runs_compare_cleanly(tmp_path: Path):
    result, project = run(tmp_path)
    assert result.returncode == 0, result.stderr
    report = json.loads((project / "research/processed/comparison.json").read_text())
    assert all(lane["entity_jaccard"] == 1.0 for lane in report["lanes"].values())
    assert report["interpretation"].startswith("Agreement measures")


def test_lane_mismatch_fails(tmp_path: Path):
    def mutate(project: Path):
        path = project / "research/acquisition/right/oss_invoice.json"
        data = json.loads(path.read_text())
        data["lane"] = "czech_invoice_software"
        path.write_text(json.dumps(data))
    result, _ = run(tmp_path, mutate)
    assert result.returncode == 1
    assert "lane metadata mismatch" in result.stderr


def test_missing_run_is_unproven(tmp_path: Path):
    def mutate(project: Path):
        (project / "research/acquisition/right/studies_comprehensive.json").unlink()
    result, _ = run(tmp_path, mutate)
    assert result.returncode == 2


def atomic_project(tmp_path: Path) -> tuple[Path, dict, dict]:
    project = tmp_path / "atomic-project"
    shutil.copytree(ROOT / "research/query-packs", project / "research/query-packs")
    (project / "scripts").mkdir(parents=True)
    shutil.copy2(SCRIPT, project / "scripts/compare_research_runs.py")
    shutil.copy2(ROOT / "scripts/check_evidence_url.py", project / "scripts/check_evidence_url.py")
    pack = json.loads((project / "research/query-packs/plan-ac-core-1.0.json").read_text())
    evidence = []
    results = []
    for lane, lane_def in pack["lanes"].items():
        for entity_id in lane_def["expected_entity_ids"]:
            for field in lane_def["fields"]:
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
                values = {
                    "boolean": True,
                    "date": "2026-08-01",
                    "integer": 100,
                    "number": 1.5,
                    "string": "documented-value",
                    "string_list": ["CSV", "JSON"],
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
    base = {
        "format_version": "atomic-results-1.0",
        "query_pack_version": pack["query_pack_version"],
        "query_pack_hash": pack["query_pack_hash"],
        "run_id": "left-run",
        "as_of": "2026-08-14",
        "results": results,
        "evidence": evidence,
    }
    (project / "runs").mkdir()
    (project / "runs/left.json").write_text(json.dumps(base))
    right = json.loads(json.dumps(base))
    right["run_id"] = "right-run"
    (project / "runs/right.json").write_text(json.dumps(right))
    return project, pack, base


def run_atomic(project: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([
        sys.executable, str(project / "scripts/compare_research_runs.py"),
        "--root", str(project), "--mode", "atomic",
        "--query-pack", "research/query-packs/plan-ac-core-1.0.json",
        "--left-results", "runs/left.json", "--right-results", "runs/right.json",
        "--output", "runs/comparison.json",
    ], text=True, capture_output=True)


def test_atomic_identical_results_compare_by_rule(tmp_path: Path):
    project, _, _ = atomic_project(tmp_path)
    result = run_atomic(project)
    assert result.returncode == 0, result.stderr
    report = json.loads((project / "runs/comparison.json").read_text())
    comparison = report["comparison"]
    assert comparison["critical_gate_passed"] is True
    assert comparison["critical"]["agreement"] == 1.0
    assert comparison["noncritical"]["agreement"] == 1.0
    assert comparison["pricing"]["agreement"] == 1.0
    assert report["query_pack_hash"]


def test_atomic_reports_critical_and_pricing_disagreements(tmp_path: Path):
    project, _, _ = atomic_project(tmp_path)
    path = project / "runs/right.json"
    right = json.loads(path.read_text())
    for item in right["results"]:
        if item["field_id"] == "czech_ocr_support":
            item["value"] = False
        if item["field_id"] == "pricing":
            item["pricing_status"] = "public_custom"
    path.write_text(json.dumps(right))
    result = run_atomic(project)
    assert result.returncode == 0, result.stderr
    comparison = json.loads((project / "runs/comparison.json").read_text())["comparison"]
    assert comparison["critical_gate_passed"] is False
    assert comparison["critical"]["disagreements"][0]["field_id"] == "czech_ocr_support"
    assert len(comparison["pricing"]["disagreements"]) == 20


def test_atomic_normalized_set_ignores_order_and_case(tmp_path: Path):
    project, _, _ = atomic_project(tmp_path)
    path = project / "runs/right.json"
    right = json.loads(path.read_text())
    for item in right["results"]:
        if item["field_id"] in {"structured_outputs", "accounting_systems"}:
            item["value"] = ["json", "csv"]
    path.write_text(json.dumps(right))
    result = run_atomic(project)
    assert result.returncode == 0, result.stderr
    report = json.loads((project / "runs/comparison.json").read_text())
    assert report["comparison"]["noncritical"]["agreement"] == 1.0


def test_atomic_matching_unproven_critical_answers_do_not_pass_gate(tmp_path: Path):
    project, _, _ = atomic_project(tmp_path)
    for name in ("left.json", "right.json"):
        path = project / "runs" / name
        payload = json.loads(path.read_text())
        item = next(result for result in payload["results"] if result["field_id"] == "czech_ocr_support")
        evidence_id = item["evidence_refs"][0]
        item.update({"result_status": "unproven", "value": None, "evidence_refs": [], "verification_status": "unverified"})
        payload["evidence"] = [evidence for evidence in payload["evidence"] if evidence["id"] != evidence_id]
        path.write_text(json.dumps(payload))
    result = run_atomic(project)
    assert result.returncode == 0, result.stderr
    comparison = json.loads((project / "runs/comparison.json").read_text())["comparison"]
    assert comparison["critical"]["agreement"] == 1.0
    assert comparison["critical"]["unresolved"][0]["field_id"] == "czech_ocr_support"
    assert comparison["critical_gate_passed"] is False


def test_atomic_rejects_missing_required_field(tmp_path: Path):
    project, _, _ = atomic_project(tmp_path)
    path = project / "runs/right.json"
    right = json.loads(path.read_text())
    right["results"] = [item for item in right["results"] if not (
        item["entity_id"] == "oss-docling" and item["field_id"] == "license_spdx"
    )]
    path.write_text(json.dumps(right))
    result = run_atomic(project)
    assert result.returncode == 1
    assert "missing required fields: license_spdx" in result.stderr


def test_atomic_rejects_missing_frozen_roster_entity(tmp_path: Path):
    project, _, _ = atomic_project(tmp_path)
    path = project / "runs/right.json"
    right = json.loads(path.read_text())
    right["results"] = [item for item in right["results"] if item["entity_id"] != "oss-docling"]
    right["evidence"] = [item for item in right["evidence"] if item["entity_id"] != "oss-docling"]
    path.write_text(json.dumps(right))
    result = run_atomic(project)
    assert result.returncode == 1
    assert "oss_invoice roster mismatch" in result.stderr
    assert "missing entities: oss-docling" in result.stderr


def test_atomic_rejects_substituted_roster_entity(tmp_path: Path):
    project, _, _ = atomic_project(tmp_path)
    path = project / "runs/right.json"
    right = json.loads(path.read_text())
    for item in right["results"]:
        if item["entity_id"] == "oss-docling":
            item["entity_id"] = "oss-substitute"
    for item in right["evidence"]:
        if item["entity_id"] == "oss-docling":
            item["entity_id"] = "oss-substitute"
    path.write_text(json.dumps(right))
    result = run_atomic(project)
    assert result.returncode == 1
    assert "missing entities: oss-docling" in result.stderr
    assert "unexpected entities: oss-substitute" in result.stderr


def test_atomic_rejects_stale_result_pack_hash(tmp_path: Path):
    project, _, _ = atomic_project(tmp_path)
    path = project / "runs/right.json"
    right = json.loads(path.read_text())
    right["query_pack_hash"] = "0" * 64
    path.write_text(json.dumps(right))
    result = run_atomic(project)
    assert result.returncode == 1
    assert "query pack hash mismatch" in result.stderr


def test_atomic_rejects_mutated_pack_even_if_declared_hash_is_stale(tmp_path: Path):
    project, _, _ = atomic_project(tmp_path)
    path = project / "research/query-packs/plan-ac-core-1.0.json"
    pack = json.loads(path.read_text())
    pack["lanes"]["oss_invoice"]["fields"][0]["question"] = "mutated"
    path.write_text(json.dumps(pack))
    result = run_atomic(project)
    assert result.returncode == 1
    assert "query pack hash mismatch" in result.stderr


def test_atomic_rejects_unknown_vocabulary_and_evidence_laundering(tmp_path: Path):
    project, _, _ = atomic_project(tmp_path)
    path = project / "runs/right.json"
    right = json.loads(path.read_text())
    right["results"][0]["result_status"] = "probably"
    path.write_text(json.dumps(right))
    result = run_atomic(project)
    assert result.returncode == 1
    assert "unknown result_status" in result.stderr

    right["results"][0]["result_status"] = "proven"
    right["results"][0]["evidence_refs"] = [right["evidence"][-1]["id"]]
    path.write_text(json.dumps(right))
    result = run_atomic(project)
    assert result.returncode == 1
    assert "evidence ownership mismatch" in result.stderr


def test_atomic_proven_result_requires_verified_evidence(tmp_path: Path):
    project, _, _ = atomic_project(tmp_path)
    path = project / "runs/right.json"
    right = json.loads(path.read_text())
    evidence_id = right["results"][0]["evidence_refs"][0]
    next(item for item in right["evidence"] if item["id"] == evidence_id)["verification_status"] = "unreachable"
    path.write_text(json.dumps(right))
    result = run_atomic(project)
    assert result.returncode == 1
    assert "proven result lacks verified evidence" in result.stderr


def test_atomic_rejects_invalid_date_value(tmp_path: Path):
    project, _, _ = atomic_project(tmp_path)
    path = project / "runs/right.json"
    right = json.loads(path.read_text())
    next(item for item in right["results"] if item["field_id"] == "latest_release_date")["value"] = "2026-02-31"
    path.write_text(json.dumps(right))
    result = run_atomic(project)
    assert result.returncode == 1
    assert "wrong value type" in result.stderr


def test_pack_hash_algorithm_is_documented_and_exact():
    pack = json.loads((ROOT / "research/query-packs/plan-ac-core-1.0.json").read_text())
    declared = pack.pop("query_pack_hash")
    canonical = json.dumps(pack, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    assert hashlib.sha256(canonical).hexdigest() == declared


def atomic_v11_project(tmp_path: Path) -> tuple[Path, dict]:
    project = tmp_path / "atomic-v11-project"
    shutil.copytree(ROOT / "research/query-packs", project / "research/query-packs")
    (project / "scripts").mkdir(parents=True)
    shutil.copy2(SCRIPT, project / "scripts/compare_research_runs.py")
    shutil.copy2(ROOT / "scripts/check_evidence_url.py", project / "scripts/check_evidence_url.py")
    pack = json.loads((project / "research/query-packs/plan-ac-core-1.1.json").read_text())
    results, evidence = [], []
    values = {
        "boolean": True, "date": "2026-08-01", "integer": 100,
        "string": "documented-value", "string_list": ["json"],
        "pricing": {
            "disclosure_status": "public_exact", "currency": "CZK",
            "vat_status": "excluded", "billing_period": "month", "unit": "document",
            "tiers": [{"name": "Start", "amount": 100, "included_units": 20, "overage_amount": 5}],
        },
    }
    controlled = {
        "czech_ocr_support_level": "native_documented",
        "invoice_extraction_level": "native_invoice_fields",
        "business_use_evidence_level": "named_customer_or_deployment",
        "structured_output_ids": ["json"],
        "accounting_system_ids": ["pohoda"],
        "export_format_ids": ["csv"],
        "target_customer_segments": ["smb"],
    }
    for lane, lane_def in pack["lanes"].items():
        for entity in lane_def["entities"]:
            for field in lane_def["fields"]:
                not_applicable = lane == "oss_invoice" and field["id"] == "pricing"
                evidence_id = f"ev-{entity['id']}-{field['id']}"
                refs = [] if not_applicable else [evidence_id]
                if not not_applicable:
                    evidence.append({
                        "id": evidence_id, "entity_id": entity["id"], "field_id": field["id"],
                        "url": entity["canonical_root_url"],
                        "evidence_class": "official_primary", "verification_status": "verified",
                        "retrieved_at": "2026-08-14T08:00:00Z",
                    })
                value = controlled.get(field["id"], values[field["value_type"]])
                results.append({
                    "entity_id": entity["id"], "lane": lane, "field_id": field["id"],
                    "result_status": "not_applicable" if not_applicable else "proven",
                    "value": None if not_applicable else value, "evidence_refs": refs,
                    "verification_status": "verified",
                    "applicability": "not_applicable" if not_applicable else "direct",
                    "claim_confidence": "not_applicable" if not_applicable else "source_verified_self_reported",
                    "enumeration_scope": (
                        "not_applicable" if not field.get("requires_enumeration_scope") else "complete_for_frozen_sources"
                    ),
                    **({"captured_at": "2026-08-14T08:30:00Z"} if field["comparison_rule"] == "snapshot" else {}),
                })
    base = {
        "format_version": "atomic-results-1.1", "query_pack_version": "1.1.0",
        "query_pack_hash": pack["query_pack_hash"], "run_id": "left-v11", "as_of": "2026-08-14",
        "provenance": {
            "collector_id": "collector-a", "collection_method": "agent_assisted",
            "collector_kind": "agent", "execution_instance_id": "instance-a",
            "identity_verification": "operator_attested", "config_digest": "a" * 64,
            "source_policy_version": pack["source_policy_version"],
            "started_at": "2026-08-14T08:00:00Z", "completed_at": "2026-08-14T09:00:00Z",
        },
        "results": results, "evidence": evidence,
    }
    (project / "runs").mkdir()
    (project / "runs/left.json").write_text(json.dumps(base))
    right = json.loads(json.dumps(base)); right["run_id"] = "right-v11"
    right["provenance"]["collector_id"] = "collector-b"
    right["provenance"]["execution_instance_id"] = "instance-b"
    (project / "runs/right.json").write_text(json.dumps(right))
    return project, pack


def run_atomic_v11(project: Path, pack="research/query-packs/plan-ac-core-1.1.json"):
    return subprocess.run([
        sys.executable, str(project / "scripts/compare_research_runs.py"), "--root", str(project),
        "--mode", "atomic", "--query-pack", pack, "--left-results", "runs/left.json",
        "--right-results", "runs/right.json", "--output", "runs/comparison.json",
    ], text=True, capture_output=True)


def mutate_result(project: Path, side: str, field_id: str, **changes):
    path = project / f"runs/{side}.json"; payload = json.loads(path.read_text())
    item = next(result for result in payload["results"] if result["field_id"] == field_id)
    item.update(changes); path.write_text(json.dumps(payload))


def test_v11_identical_facts_reconcile_and_na_is_resolved(tmp_path: Path):
    project, _ = atomic_v11_project(tmp_path)
    result = run_atomic_v11(project)
    assert result.returncode == 0, result.stderr
    report = json.loads((project / "runs/comparison.json").read_text())["comparison"]
    for bucket in ("critical", "noncritical", "pricing"):
        section = report[bucket]
        outcomes = sum(section[name] for name in (
            "semantic_match", "semantic_conflict", "coverage_difference", "both_unproven",
            "resolved_not_applicable", "snapshot_drift",
        ))
        assert outcomes == section["total_slots"]
    assert report["pricing"]["resolved_not_applicable"] == 10
    assert report["structural_repeatability_passed"] is True
    assert report["independence"]["verified"] is True
    assert report["acceptance_signal_passed"] is False  # critical vendor/official self-report remains separate from acceptance


def test_v11_matching_unproven_is_not_agreement(tmp_path: Path):
    project, _ = atomic_v11_project(tmp_path)
    for side in ("left", "right"):
        path = project / f"runs/{side}.json"; payload = json.loads(path.read_text())
        item = next(x for x in payload["results"] if x["field_id"] == "local_execution")
        evidence_id = item["evidence_refs"][0]
        item.update(result_status="unproven", value=None, evidence_refs=[], verification_status="unverified", claim_confidence="unproven")
        payload["evidence"] = [x for x in payload["evidence"] if x["id"] != evidence_id]
        path.write_text(json.dumps(payload))
    result = run_atomic_v11(project); assert result.returncode == 0, result.stderr
    critical = json.loads((project / "runs/comparison.json").read_text())["comparison"]["critical"]
    assert critical["both_unproven"] == 1
    assert critical["unresolved_any"] == 1
    assert critical["resolved_semantic_agreement"] == 1.0


def test_v11_applicability_drift_is_nonsemantic(tmp_path: Path):
    project, _ = atomic_v11_project(tmp_path)
    mutate_result(project, "right", "received_invoice_extraction", applicability="workflow")
    result = run_atomic_v11(project); assert result.returncode == 0, result.stderr
    critical = json.loads((project / "runs/comparison.json").read_text())["comparison"]["critical"]
    assert critical["semantic_conflict"] == 0
    assert critical["applicability_difference_count"] == 1


def test_v11_partial_set_difference_is_coverage_not_conflict(tmp_path: Path):
    project, _ = atomic_v11_project(tmp_path)
    mutate_result(project, "right", "structured_output_ids", value=["json", "xml"], enumeration_scope="partial")
    result = run_atomic_v11(project); assert result.returncode == 0, result.stderr
    section = json.loads((project / "runs/comparison.json").read_text())["comparison"]["noncritical"]
    assert section["coverage_difference"] == 1
    assert section["semantic_conflict"] == 0


def test_v11_pricing_order_notes_and_extra_tier_are_not_prose_conflicts(tmp_path: Path):
    project, _ = atomic_v11_project(tmp_path)
    path = project / "runs/right.json"; payload = json.loads(path.read_text())
    item = next(x for x in payload["results"] if x["lane"] == "czech_invoice_software" and x["field_id"] == "pricing")
    item["value"]["notes"] = "Different prose is intentionally ignored."
    item["value"]["tiers"].append({"name": "Business", "amount": 200, "included_units": 50, "overage_amount": 4})
    path.write_text(json.dumps(payload))
    result = run_atomic_v11(project); assert result.returncode == 0, result.stderr
    pricing = json.loads((project / "runs/comparison.json").read_text())["comparison"]["pricing"]
    assert pricing["coverage_difference"] == 1
    assert pricing["semantic_conflict"] == 0


def test_v11_snapshot_delta_is_reported_not_factual_conflict(tmp_path: Path):
    project, _ = atomic_v11_project(tmp_path)
    mutate_result(project, "right", "github_stars", value=101, captured_at="2026-08-14T08:31:00Z")
    result = run_atomic_v11(project); assert result.returncode == 0, result.stderr
    section = json.loads((project / "runs/comparison.json").read_text())["comparison"]["noncritical"]
    assert section["snapshot_drift"] == 1
    assert section["semantic_conflict"] == 0


def test_v11_confidence_difference_is_reported_not_factual_conflict(tmp_path: Path):
    project, _ = atomic_v11_project(tmp_path)
    path = project / "runs/right.json"; payload = json.loads(path.read_text())
    item = next(x for x in payload["results"] if x["field_id"] == "received_invoice_extraction")
    item["claim_confidence"] = "independently_corroborated"
    evidence_id = item["evidence_refs"][0]
    independent = next(x for x in payload["evidence"] if x["id"] == evidence_id)
    independent["evidence_class"] = "independent_secondary"
    independent["url"] = "https://independent.example.org/vendor-alice-redque/review"
    path.write_text(json.dumps(payload))
    result = run_atomic_v11(project); assert result.returncode == 0, result.stderr
    critical = json.loads((project / "runs/comparison.json").read_text())["comparison"]["critical"]
    assert critical["confidence_difference_count"] == 1
    assert critical["semantic_conflict"] == 0


def test_v11_rejects_laundered_independent_confidence(tmp_path: Path):
    project, _ = atomic_v11_project(tmp_path)
    mutate_result(project, "right", "received_invoice_extraction", claim_confidence="independently_corroborated")
    result = run_atomic_v11(project)
    assert result.returncode == 1
    assert "corroborated confidence lacks verified independent evidence" in result.stderr


def test_v11_rejects_same_collector_and_v10_payload(tmp_path: Path):
    project, _ = atomic_v11_project(tmp_path)
    right = json.loads((project / "runs/right.json").read_text())
    right["provenance"]["collector_id"] = "collector-a"
    (project / "runs/right.json").write_text(json.dumps(right))
    result = run_atomic_v11(project)
    assert result.returncode == 0, result.stderr
    report = json.loads((project / "runs/comparison.json").read_text())["comparison"]
    assert report["independence"]["verified"] is False
    assert report["acceptance_signal_passed"] is False
    left = json.loads((project / "runs/left.json").read_text())
    left["format_version"] = "atomic-results-1.0"
    (project / "runs/left.json").write_text(json.dumps(left))
    result = run_atomic_v11(project)
    assert result.returncode == 1


def test_v11_rejects_official_evidence_outside_entity_roots(tmp_path: Path):
    project, _ = atomic_v11_project(tmp_path)
    path = project / "runs/right.json"
    payload = json.loads(path.read_text())
    payload["evidence"][0]["url"] = "https://example.com/not-the-frozen-entity"
    path.write_text(json.dumps(payload))
    result = run_atomic_v11(project)
    assert result.returncode == 1
    assert "outside the frozen official roots" in result.stderr


@pytest.mark.parametrize("timestamp_field", ["started_at", "completed_at"])
def test_v11_rejects_collection_timestamp_outside_window(tmp_path: Path, timestamp_field: str):
    project, _ = atomic_v11_project(tmp_path)
    path = project / "runs/right.json"
    payload = json.loads(path.read_text())
    payload["provenance"][timestamp_field] = "2026-08-15T08:00:00Z"
    path.write_text(json.dumps(payload))
    result = run_atomic_v11(project)
    assert result.returncode == 1
    assert "outside the frozen capture window" in result.stderr or "precedes" in result.stderr


def test_v11_rejects_evidence_and_snapshot_outside_run_interval(tmp_path: Path):
    project, _ = atomic_v11_project(tmp_path)
    path = project / "runs/right.json"
    payload = json.loads(path.read_text())
    payload["evidence"][0]["retrieved_at"] = "2026-08-14T07:59:59Z"
    path.write_text(json.dumps(payload))
    result = run_atomic_v11(project)
    assert result.returncode == 1 and "outside the collection interval" in result.stderr
    project, _ = atomic_v11_project(tmp_path / "snapshot")
    mutate_result(project, "right", "github_stars", captured_at="2026-08-14T09:00:01Z")
    result = run_atomic_v11(project)
    assert result.returncode == 1 and "snapshot capture falls outside" in result.stderr


def test_v11_rejects_ambiguous_pricing_and_duplicate_tier_names(tmp_path: Path):
    project, _ = atomic_v11_project(tmp_path)
    path = project / "runs/right.json"
    payload = json.loads(path.read_text())
    price = next(x for x in payload["results"] if x["lane"] == "czech_invoice_software" and x["field_id"] == "pricing")
    price["value"]["tiers"].append(dict(price["value"]["tiers"][0], name=" start "))
    path.write_text(json.dumps(payload))
    result = run_atomic_v11(project)
    assert result.returncode == 1 and "tier names collide" in result.stderr


def test_v11_critical_applicability_drift_blocks_structural_signal(tmp_path: Path):
    project, _ = atomic_v11_project(tmp_path)
    mutate_result(project, "right", "received_invoice_extraction", applicability="workflow")
    result = run_atomic_v11(project)
    assert result.returncode == 0, result.stderr
    comparison = json.loads((project / "runs/comparison.json").read_text())["comparison"]
    assert comparison["structural_repeatability_passed"] is False
    assert comparison["acceptance_signal_passed"] is False


def test_v11_refuses_to_overwrite_comparison_inputs(tmp_path: Path):
    project, _ = atomic_v11_project(tmp_path)
    result = subprocess.run([
        sys.executable, str(project / "scripts/compare_research_runs.py"), "--root", str(project),
        "--mode", "atomic", "--query-pack", "research/query-packs/plan-ac-core-1.1.json",
        "--left-results", "runs/left.json", "--right-results", "runs/right.json",
        "--output", "runs/left.json",
    ], text=True, capture_output=True)
    assert result.returncode == 1
    assert "cannot overwrite" in result.stderr


def run_atomic_v11_check(project: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([
        sys.executable, str(project / "scripts/compare_research_runs.py"), "--root", str(project),
        "--mode", "atomic", "--query-pack", "research/query-packs/plan-ac-core-1.1.json",
        "--left-results", "runs/left.json", "--right-results", "runs/right.json",
        "--output", "runs/comparison.json", "--check",
    ], text=True, capture_output=True)


def test_v11_report_binds_exact_input_and_pack_bytes_and_check_is_read_only(tmp_path: Path):
    project, pack = atomic_v11_project(tmp_path)
    generated = run_atomic_v11(project)
    assert generated.returncode == 0, generated.stderr
    output = project / "runs/comparison.json"
    report = json.loads(output.read_text())
    bindings = report["input_bindings"]
    assert bindings["query_pack"]["file_sha256"] == hashlib.sha256(
        (project / "research/query-packs/plan-ac-core-1.1.json").read_bytes()
    ).hexdigest()
    assert bindings["query_pack"]["semantic_hash"] == pack["query_pack_hash"]
    for key, name in (("left_results", "left.json"), ("right_results", "right.json")):
        assert bindings[key]["sha256"] == hashlib.sha256(
            (project / f"runs/{name}").read_bytes()
        ).hexdigest()
    before = output.read_bytes()
    checked = run_atomic_v11_check(project)
    assert checked.returncode == 0, checked.stderr
    assert output.read_bytes() == before
    assert json.loads(checked.stdout)["action"] == "current"


def test_v11_check_fails_closed_for_missing_stale_or_rebound_output(tmp_path: Path):
    project, _ = atomic_v11_project(tmp_path)
    missing = run_atomic_v11_check(project)
    assert missing.returncode == 1 and "missing" in missing.stderr

    assert run_atomic_v11(project).returncode == 0
    output = project / "runs/comparison.json"
    original = output.read_bytes()
    output.write_bytes(original + b" ")
    modified_before = output.read_bytes()
    stale = run_atomic_v11_check(project)
    assert stale.returncode == 1 and "stale" in stale.stderr
    assert output.read_bytes() == modified_before

    output.write_bytes(original)
    left = project / "runs/left.json"
    left.write_bytes(left.read_bytes() + b"\n")
    rebound = run_atomic_v11_check(project)
    assert rebound.returncode == 1 and "stale" in rebound.stderr
    assert output.read_bytes() == original


def test_v11_check_detects_query_pack_file_byte_change_even_when_semantics_match(tmp_path: Path):
    project, _ = atomic_v11_project(tmp_path)
    assert run_atomic_v11(project).returncode == 0
    output = project / "runs/comparison.json"
    before = output.read_bytes()
    pack_path = project / "research/query-packs/plan-ac-core-1.1.json"
    pack_path.write_bytes(pack_path.read_bytes() + b"\n")
    checked = run_atomic_v11_check(project)
    assert checked.returncode == 1 and "stale" in checked.stderr
    assert output.read_bytes() == before


def test_v11_rejects_unknown_controlled_value_and_missing_snapshot_time(tmp_path: Path):
    project, _ = atomic_v11_project(tmp_path)
    mutate_result(project, "right", "czech_ocr_support_level", value="some_backend")
    result = run_atomic_v11(project)
    assert result.returncode == 1 and "unknown controlled value" in result.stderr
    project, _ = atomic_v11_project(tmp_path / "second")
    path = project / "runs/right.json"; payload = json.loads(path.read_text())
    next(x for x in payload["results"] if x["field_id"] == "github_stars").pop("captured_at")
    path.write_text(json.dumps(payload))
    result = run_atomic_v11(project)
    assert result.returncode == 1 and "snapshot lacks captured_at" in result.stderr


def test_v11_pack_hash_is_exact():
    pack = json.loads((ROOT / "research/query-packs/plan-ac-core-1.1.json").read_text())
    declared = pack.pop("query_pack_hash")
    canonical = json.dumps(pack, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    assert hashlib.sha256(canonical).hexdigest() == declared


def test_v11_pack_validates_schema_and_roster_is_hash_bound():
    from jsonschema import Draft7Validator, FormatChecker
    pack_path = ROOT / "research/query-packs/plan-ac-core-1.1.json"
    pack = json.loads(pack_path.read_text())
    schema = json.loads((ROOT / "research/query-packs/atomic-query-pack-1.1.schema.json").read_text())
    assert not list(Draft7Validator(schema, format_checker=FormatChecker()).iter_errors(pack))
    ids = [entity["id"] for lane in pack["lanes"].values() for entity in lane["entities"]]
    roots = [entity["canonical_root_url"] for lane in pack["lanes"].values() for entity in lane["entities"]]
    assert len(ids) == len(set(ids)) == 20
    assert len(roots) == len(set(roots)) == 20
    pack["lanes"]["oss_invoice"]["entities"][0]["canonical_root_url"] += "/changed"
    declared = pack.pop("query_pack_hash")
    mutated = hashlib.sha256(json.dumps(pack, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert mutated != declared


def test_v11_rejects_unsafe_canonical_root_even_with_fresh_hash(tmp_path: Path):
    project, _ = atomic_v11_project(tmp_path)
    path = project / "research/query-packs/plan-ac-core-1.1.json"
    pack = json.loads(path.read_text())
    pack["lanes"]["oss_invoice"]["entities"][0]["canonical_root_url"] = "https://127.0.0.1/project"
    candidate = dict(pack); candidate.pop("query_pack_hash")
    pack["query_pack_hash"] = hashlib.sha256(
        json.dumps(candidate, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    path.write_text(json.dumps(pack))
    for side in ("left", "right"):
        run_path = project / f"runs/{side}.json"; run = json.loads(run_path.read_text())
        run["query_pack_hash"] = pack["query_pack_hash"]; run_path.write_text(json.dumps(run))
    result = run_atomic_v11(project)
    assert result.returncode == 1
    assert "unsafe canonical root URL" in result.stderr

def test_frozen_collector_protocol_schema_and_digest() -> None:
    root = Path(__file__).resolve().parents[1]
    protocol_path = root / "research/query-packs/plan-ac-collector-protocol-1.0.json"
    schema_path = root / "research/query-packs/collector-protocol-1.0.schema.json"
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    from jsonschema import Draft7Validator

    Draft7Validator.check_schema(schema)
    assert list(Draft7Validator(schema).iter_errors(protocol)) == []
    declared = protocol.pop("config_digest")
    canonical = json.dumps(
        protocol, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    assert hashlib.sha256(canonical).hexdigest() == declared


def test_atomic_errata_schema_and_target_bindings() -> None:
    root = Path(__file__).resolve().parents[1]
    errata = json.loads(
        (root / "research/acquisition/atomic-v1.1-errata-2026-08-14.json").read_text(
            encoding="utf-8"
        )
    )
    schema = json.loads(
        (root / "research/query-packs/atomic-errata-1.0.schema.json").read_text(
            encoding="utf-8"
        )
    )

    from jsonschema import Draft7Validator, FormatChecker

    Draft7Validator.check_schema(schema)
    assert list(Draft7Validator(schema, format_checker=FormatChecker()).iter_errors(errata)) == []
    for binding in errata["target_bindings"]:
        payload = (root / binding["path"]).read_bytes()
        assert hashlib.sha256(payload).hexdigest() == binding["sha256"]
