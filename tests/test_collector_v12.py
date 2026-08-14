"""Adversarial tests for the proposal-only collector v1.2 contract."""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.run_collector_proposals_v12 import InvalidProposal, semantic_sha256, validate_and_build
from scripts.validate_collector_execution_v12 import validate_execution


PROJECT = Path(__file__).resolve().parent.parent


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def binding(path: Path, root: Path, semantic: bool = True) -> dict[str, str]:
    result = {"path": path.relative_to(root).as_posix(), "byte_sha256": sha(path)}
    if semantic:
        result["semantic_sha256"] = semantic_sha256(json.loads(path.read_text(encoding="utf-8")))
    return result


@pytest.fixture()
def proposal(tmp_path: Path) -> tuple[Path, dict]:
    root = tmp_path / "project"
    qp = root / "research/query-packs"
    qp.mkdir(parents=True)
    for name in (
        "plan-ac-core-1.1.json", "atomic-query-pack-1.1.schema.json",
        "plan-ac-collector-protocol-1.1.json", "collector-protocol-1.1.schema.json",
        "field-normalization-1.0.json", "field-normalization-1.0.schema.json",
        "field-normalization-proposal-1.0.schema.json",
        "source-capture-result-1.1.schema.json", "collector-proposal-input-1.1.schema.json",
        "collector-execution-1.2.schema.json",
    ):
        (qp / name).write_bytes((PROJECT / "research/query-packs" / name).read_bytes())
    scripts = root / "scripts"
    scripts.mkdir()
    (scripts / "run_collector_proposals_v12.py").write_bytes((PROJECT / "scripts/run_collector_proposals_v12.py").read_bytes())
    config = qp / "synthetic-collector-config.json"
    write_json(config, {"fixture": True, "network": False, "version": "1.0"})

    pack = json.loads((qp / "plan-ac-core-1.1.json").read_text(encoding="utf-8"))
    vendor_lane = pack["lanes"]["czech_invoice_software"]
    fakturoid = next(entity for entity in vendor_lane["entities"] if entity["id"] == "vendor-fakturoid")
    excerpt_text = "SYNTHETIC: veřejné API; ceny 100 Kč; formáty csv; účetní produkt fakturoid."
    capture_dir = root / "research/acquisition/source-captures/synthetic-v12"
    excerpt = capture_dir / "excerpts/fakturoid.txt"
    excerpt.parent.mkdir(parents=True)
    excerpt.write_text(excerpt_text, encoding="utf-8")
    capture_row = {
        "id": "fakturoid-source", "requested_url": fakturoid["canonical_root_url"],
        "field_targets": [{"entity_id": "vendor-fakturoid", "field_id": field["id"]} for field in vendor_lane["fields"]],
        "state": "captured", "reason": None, "final_url": fakturoid["canonical_root_url"],
        "redirect_chain": [], "requested_method": "GET", "performed_methods": ["GET"],
        "http_status": 200, "retrieved_at": "2026-08-14T12:00:00Z", "content_type": "text/plain",
        "response_sha256": hashlib.sha256(excerpt_text.encode()).hexdigest(),
        "response_bytes": len(excerpt_text.encode()),
        "excerpt": {"selector": "term-window", "terms": ["fakturoid"], "matched_terms": ["fakturoid"],
                    "span": [0, len(excerpt_text)], "sha256": sha(excerpt), "characters": len(excerpt_text),
                    "truncated": False, "path": "excerpts/fakturoid.txt"},
    }
    capture = {
        "schema_version": "source-capture-result-1.1", "run_id": "synthetic-v12", "mode": "fixture",
        "query_pack_version": "1.1.0", "query_pack_hash": pack["query_pack_hash"],
        "request_sha256": "1" * 64, "results": [capture_row],
        "summary": {"captured": 1, "unproven": 0, "invalid": 0},
    }
    capture_path = capture_dir / "manifest.json"
    write_json(capture_path, capture)
    source = {"capture_manifest_path": capture_path.relative_to(root).as_posix(), "capture_result_id": "fakturoid-source"}

    rule_for = {
        "public_api": ("public-api-positive-phrases", "veřejné api", True),
        "pricing": ("czech-pricing-currency-czk", "Kč", "CZK"),
        "accounting_system_ids": ("fakturoid-accounting-product-aliases", "fakturoid", "fakturoid"),
        "export_format_ids": ("export-format-csv", "csv", "csv"),
    }
    inspections = []
    for lane_id, lane in pack["lanes"].items():
        for entity in lane["entities"]:
            for field in lane["fields"]:
                slot = (entity["id"], field["id"])
                if entity["id"] != "vendor-fakturoid":
                    inspections.append({"entity_id": slot[0], "field_id": slot[1], "inspection_status": "not_inspected", "not_inspected_reason": "out_of_scope", "sources": [], "observations": [], "reason": "This slot is outside the bounded synthetic inspection."})
                elif field["id"] in rule_for:
                    rule, raw, value = rule_for[field["id"]]
                    item = {"entity_id": slot[0], "field_id": slot[1], "inspection_status": "proven", "sources": [source],
                            "observations": [{"source": source, "mapping_rule_id": rule, "raw_value": raw,
                                              "proposed_value": value, "supporting_text": excerpt_text}],
                            "reason": "The synthetic capture contains the exact normalization token."}
                    if field["value_type"] == "string_list":
                        item["enumeration_scope"] = {"completeness": "complete", "captured_enumerands": [raw],
                                                     "mapped_enumerands": [{"raw_value": raw, "mapped_value": value, "mapping_rule_id": rule}],
                                                     "unmapped_enumerands": []}
                    inspections.append(item)
                else:
                    inspections.append({"entity_id": slot[0], "field_id": slot[1], "inspection_status": "does_not_establish",
                                        "sources": [source], "observations": [],
                                        "reason": "The attempted synthetic source does not establish this field."})

    list_slots = {
        (entity["id"], field["id"])
        for lane in pack["lanes"].values()
        for entity in lane["entities"]
        for field in lane["fields"]
        if field["value_type"] == "string_list"
    }
    for inspection in inspections:
        if (inspection["entity_id"], inspection["field_id"]) in list_slots and "enumeration_scope" not in inspection:
            inspection["enumeration_scope"] = {
                "completeness": "partial", "captured_enumerands": [],
                "mapped_enumerands": [], "unmapped_enumerands": [],
            }

    value = {
        "format_version": "collector-proposal-input-1.1", "run_id": "synthetic-v12-run",
        "execution_instance_id": "synthetic-v12-instance",
        "query_pack": binding(qp / "plan-ac-core-1.1.json", root),
        "protocol": binding(qp / "plan-ac-collector-protocol-1.1.json", root),
        "normalization_rules": binding(qp / "field-normalization-1.0.json", root),
        "capture_manifests": [binding(capture_path, root)],
        "collector": {"collector_id": "synthetic-v12", "provider": None, "model": None,
                      "identity_verification": "unverified",
                      "implementation": binding(scripts / "run_collector_proposals_v12.py", root, False),
                      "config": binding(config, root), "tools": [{"name": "fixture", "version": "1.0"}]},
        "inspections": inspections,
    }
    return root, value


def test_216_not_inspected_are_explicit_and_never_complete_authority(proposal):
    root, value = proposal
    execution, unproven = validate_and_build(root, value)
    assert execution["summary"] == {"total": 230, "proven": 4, "conflicted": 0, "does_not_establish": 10, "not_inspected": 216}
    assert unproven is True
    assert execution["authority_classification"] == "collector_proposed"


def test_cross_field_evidence_laundering_is_rejected(proposal):
    root, value = proposal
    capture_path = root / value["capture_manifests"][0]["path"]
    capture = json.loads(capture_path.read_text())
    capture["results"][0]["field_targets"] = [target for target in capture["results"][0]["field_targets"] if target["field_id"] != "public_api"]
    write_json(capture_path, capture)
    value["capture_manifests"][0] = binding(capture_path, root)
    with pytest.raises(InvalidProposal, match="field_targets do not authorize"):
        validate_and_build(root, value)


def test_does_not_establish_requires_attempt_and_not_inspected_forbids_one(proposal):
    root, value = proposal
    dne = next(row for row in value["inspections"] if row["inspection_status"] == "does_not_establish")
    dne["sources"] = []
    with pytest.raises(InvalidProposal, match="proposal|requires a bound attempted"):
        validate_and_build(root, value)
    root, value = proposal
    untouched = next(row for row in value["inspections"] if row["inspection_status"] == "not_inspected")
    source = next(row for row in value["inspections"] if row["sources"])["sources"][0]
    untouched["sources"] = [source]
    with pytest.raises(InvalidProposal, match="proposal|must not bind"):
        validate_and_build(root, value)


def test_mapping_rule_scope_input_and_output_are_enforced(proposal):
    root, value = proposal
    public_api = next(row for row in value["inspections"] if row["entity_id"] == "vendor-fakturoid" and row["field_id"] == "public_api")
    public_api["observations"][0]["mapping_rule_id"] = "export-format-csv"
    with pytest.raises(InvalidProposal, match="rule scope"):
        validate_and_build(root, value)


def test_kc_is_normalized_only_to_czk_proposal(proposal):
    root, value = proposal
    execution, _ = validate_and_build(root, value)
    pricing = next(row for row in execution["inspections"] if row["entity_id"] == "vendor-fakturoid" and row["field_id"] == "pricing")
    assert pricing["observations"][0]["raw_value"] == "Kč"
    assert pricing["observations"][0]["proposed_value"] == "CZK"
    assert pricing["observations"][0]["authority_classification"] == "collector_proposed"


def test_incomplete_fakturoid_list_cannot_claim_complete(proposal):
    root, value = proposal
    item = next(row for row in value["inspections"] if row["entity_id"] == "vendor-fakturoid" and row["field_id"] == "accounting_system_ids")
    item["enumeration_scope"]["captured_enumerands"].append("pohoda")
    with pytest.raises(InvalidProposal, match="classify every captured|absent from bound excerpts"):
        validate_and_build(root, value)


def test_partial_list_never_masquerades_as_exhaustive(proposal):
    root, value = proposal
    item = next(row for row in value["inspections"] if row["entity_id"] == "vendor-fakturoid" and row["field_id"] == "accounting_system_ids")
    item["enumeration_scope"]["completeness"] = "partial"
    execution, unproven = validate_and_build(root, value)
    assert unproven is True
    assert next(row for row in execution["inspections"] if row["field_id"] == "accounting_system_ids")["enumeration_scope"]["completeness"] == "partial"


def test_exact_binding_tampering_is_rejected(proposal):
    root, value = proposal
    for key in ("query_pack", "protocol", "normalization_rules"):
        altered = copy.deepcopy(value)
        altered[key]["byte_sha256"] = "0" * 64
        with pytest.raises(InvalidProposal, match="hash mismatch"):
            validate_and_build(root, altered)
    value["collector"]["implementation"]["byte_sha256"] = "0" * 64
    with pytest.raises(InvalidProposal, match="implementation hash"):
        validate_and_build(root, value)


def test_validator_is_read_only_and_returns_two_for_valid_proposal(proposal):
    root, value = proposal
    execution, _ = validate_and_build(root, value)
    path = root / "research/acquisition/collector-executions/synthetic-v12.json"
    write_json(path, execution)
    before = {p.relative_to(root): sha(p) for p in root.rglob("*") if p.is_file()}
    command = [sys.executable, str(PROJECT / "scripts/validate_collector_execution_v12.py"), "--root", str(root), "--input", path.relative_to(root).as_posix(), "--json"]
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    assert result.returncode == 2, result.stdout + result.stderr
    assert json.loads(result.stdout)["status"] == "valid-provisional"
    after = {p.relative_to(root): sha(p) for p in root.rglob("*") if p.is_file()}
    assert before == after
    validate_execution(root, execution)


def test_execution_cannot_promote_authority(proposal):
    root, value = proposal
    execution, _ = validate_and_build(root, value)
    execution["authority_classification"] = "operator_verified"
    with pytest.raises(InvalidProposal, match="authority_classification|collector_proposed"):
        validate_execution(root, execution)
