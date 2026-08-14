"""Synthetic and adversarial tests for the capture-bound collector contract."""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.validate_collector_execution import (
    semantic_sha256, typed_lexical_support_matches, validate_execution,
)


PROJECT = Path(__file__).resolve().parent.parent


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def binding(path: Path, root: Path, *, semantic: bool = False) -> dict[str, str]:
    result = {"path": path.relative_to(root).as_posix(), "byte_sha256": sha(path)}
    if semantic:
        result["semantic_sha256"] = semantic_sha256(json.loads(path.read_text(encoding="utf-8")))
    return result


def sample_value(field: dict) -> object:
    kind = field["value_type"]
    if field["id"] == "license_spdx":
        return "MIT"
    if kind == "boolean":
        return True
    if kind == "date":
        return "2026-08-14"
    if kind == "integer":
        return 1
    if kind == "string_list":
        return [field.get("allowed_values", ["synthetic"])[0]]
    if kind == "pricing":
        return {
            "disclosure_status": "public_custom", "currency": None,
            "vat_status": "not_disclosed", "billing_period": "not_disclosed",
            "unit": "custom", "tiers": [], "notes": "Synthetic fixture only",
        }
    return field.get("allowed_values", ["synthetic_value"])[0]


@pytest.fixture()
def execution(tmp_path: Path) -> tuple[Path, dict, dict]:
    root = tmp_path / "project"
    qp = root / "research/query-packs"
    qp.mkdir(parents=True)
    for name in (
        "plan-ac-core-1.1.json", "atomic-query-pack-1.1.schema.json",
        "plan-ac-collector-protocol-1.1.json", "collector-protocol-1.1.schema.json",
        "collector-execution-1.1.schema.json",
        "source-capture-result-1.0.schema.json", "source-capture-1.0.schema.json",
        "source-capture-result-1.1.schema.json", "source-capture-1.1.schema.json",
    ):
        (qp / name).write_bytes((PROJECT / "research/query-packs" / name).read_bytes())
    fixture_dir = root / "research/acquisition/synthetic-mini-pilot"
    fixture_dir.mkdir(parents=True)
    for name in ("fixture-set.json", "fixture-set.schema.json"):
        (fixture_dir / name).write_bytes((PROJECT / "research/acquisition/synthetic-mini-pilot" / name).read_bytes())
    schema = json.loads((qp / "collector-execution-1.1.schema.json").read_text(encoding="utf-8"))
    pack = json.loads((qp / "plan-ac-core-1.1.json").read_text(encoding="utf-8"))

    implementation = root / "scripts/run_collector_fixture.py"
    prompt = qp / "plan-ac-collector-protocol-1.1.json"
    config = fixture_dir / "fixture-set.json"
    implementation.parent.mkdir(parents=True)
    implementation.write_bytes((PROJECT / "scripts/run_collector_fixture.py").read_bytes())

    capture_dir = root / "research/acquisition/source-captures/synthetic-capture"
    excerpts_dir = capture_dir / "excerpts"
    excerpts_dir.mkdir(parents=True)
    results, sources, inspections = [], [], []
    for lane in pack["lanes"].values():
        fixture_values = [sample_value(field) for field in lane["fields"]]
        lexical_values = []
        for value in fixture_values:
            if isinstance(value, dict):
                lexical_values.append(value["disclosure_status"].replace("_", " "))
            elif isinstance(value, list):
                lexical_values.extend(str(item).replace("_", " ") for item in value)
            else:
                lexical_values.append(str(value).replace("_", " "))
        for entity in lane["entities"]:
            capture_id = f"capture-{entity['id']}"
            excerpt_text = "support detail supports true " + " ".join(lexical_values) + "\n"
            excerpt = excerpts_dir / f"{capture_id}.txt"
            excerpt.write_text(excerpt_text, encoding="utf-8")
            url = entity["canonical_root_url"]
            row = {
                "id": capture_id, "requested_url": url, "state": "captured", "reason": None,
                "field_targets": [{"entity_id": entity["id"], "field_id": field["id"]}
                                  for field in lane["fields"]],
                "final_url": url, "redirect_chain": [], "requested_method": "GET",
                "performed_methods": ["GET"], "http_status": 200,
                "retrieved_at": "2026-08-14T12:00:00Z", "content_type": "text/plain",
                "response_sha256": hashlib.sha256(("response-" + entity["id"]).encode()).hexdigest(),
                "response_bytes": len(excerpt_text.encode()),
                "excerpt": {
                    "selector": "term-window",
                    "terms": ["support detail"], "matched_terms": ["support detail"],
                    "span": [0, len(excerpt_text.strip())], "sha256": sha(excerpt),
                    "characters": len(excerpt_text.strip()), "truncated": False,
                    "path": f"excerpts/{capture_id}.txt",
                },
            }
            results.append(row)
            source_id = f"src-{entity['id']}"
            sources.append({
                "id": source_id, "entity_id": entity["id"],
                "capture_manifest_ref": "research/acquisition/source-captures/synthetic-capture/manifest.json",
                "capture_manifest_sha256": "0" * 64,
                "capture_run_id": "synthetic-capture", "capture_mode": "fixture",
                "capture_result_id": capture_id, "capture_result_sha256": semantic_sha256(row),
                "requested_url": url, "final_url": url, "redirect_chain": [],
                "http_status": 200, "retrieved_at": "2026-08-14T12:00:00Z",
                "content_type": "text/plain", "verification_status": "verified",
                "response_sha256": row["response_sha256"], "excerpt_sha256": sha(excerpt),
                "excerpt_ref": excerpt.relative_to(root).as_posix(),
            })
            for field in lane["fields"]:
                inspections.append({
                    "entity_id": entity["id"], "field_id": field["id"],
                    "source_ids": [source_id],
                    "locators": [{"source_id": source_id, "locator": "support detail"}],
                    "observations": [{"source_id": source_id, "value": sample_value(field),
                                      "excerpt_span": [0, len(excerpt_text.encode())],
                                      "supporting_text": excerpt_text}],
                    "inspected_sections": ["support detail"], "query_terms": ["support detail"],
                    "support_status": "proven", "reason": "Synthetic excerpt directly supports the typed value.",
                })
    capture_manifest = {
        "schema_version": "source-capture-result-1.1", "run_id": "synthetic-capture",
        "mode": "fixture", "query_pack_version": pack["query_pack_version"],
        "query_pack_hash": pack["query_pack_hash"],
        "request_sha256": "1" * 64, "results": results,
        "summary": {"captured": len(results), "unproven": 0, "invalid": 0},
    }
    capture_manifest_path = capture_dir / "manifest.json"
    write_json(capture_manifest_path, capture_manifest)
    for source in sources:
        source["capture_manifest_sha256"] = sha(capture_manifest_path)

    manifest = {
        "format_version": "collector-execution-1.1",
        "evidence_scope": "synthetic_fixture_only_not_market_evidence",
        "run_id": "synthetic-contract-run",
        "execution_instance_id": "synthetic-instance-1",
        "authority_classification": "synthetic_fixture_verified", "operator_attestation": None,
        "query_pack": binding(qp / "plan-ac-core-1.1.json", root, semantic=True),
        "protocol": binding(qp / "plan-ac-collector-protocol-1.1.json", root, semantic=True),
        "contract_schema": binding(qp / "collector-execution-1.1.schema.json", root, semantic=True),
        "collector": {
            "collector_id": "synthetic-test-collector", "provider": None, "model": None,
            "identity_verification": "unverified",
            "config_digest": json.loads(config.read_text())["fixture_set_hash"],
            "implementation": binding(implementation, root),
            "prompt": {**binding(prompt, root), "version": "prompt-1.0"},
            "config": {**binding(config, root), "version": "config-1.0"},
            "tools": [{"name": "synthetic-fetch", "version": "1.0.0"}],
        },
        "capture": {"started_at": "2026-08-14T11:00:00Z", "completed_at": "2026-08-14T13:00:00Z"},
        "sources": sources, "inspections": inspections,
    }
    return root, manifest, schema


def test_complete_capture_bound_execution_is_valid(execution):
    root, manifest, schema = execution
    assert validate_execution(root, manifest, schema) is False


def test_h_missing_unknown_slot_is_rejected_not_silently_unproven(execution):
    root, manifest, schema = execution
    manifest["inspections"].pop()
    with pytest.raises(ValueError, match="missing inspections"):
        validate_execution(root, manifest, schema)


def test_i_generic_locator_is_rejected(execution):
    root, manifest, schema = execution
    manifest["inspections"][0]["locators"][0]["locator"] = "page title"
    with pytest.raises(ValueError, match="generic title-only"):
        validate_execution(root, manifest, schema)


def test_locator_and_terms_must_occur_in_captured_excerpt(execution):
    root, manifest, schema = execution
    manifest["inspections"][0]["query_terms"] = ["absent phrase"]
    with pytest.raises(ValueError, match="does not occur"):
        validate_execution(root, manifest, schema)


def test_capture_manifest_result_and_excerpt_hashes_are_bound(execution):
    root, manifest, schema = execution
    for key, pattern in (
        ("capture_manifest_sha256", "capture manifest hash mismatch"),
        ("capture_result_sha256", "capture result hash mismatch"),
        ("excerpt_sha256", "differs from capture result"),
    ):
        altered = copy.deepcopy(manifest)
        altered["sources"][0][key] = "f" * 64
        with pytest.raises(ValueError, match=pattern):
            validate_execution(root, altered, schema)


def test_canonical_pack_protocol_and_schema_cannot_be_substituted(execution):
    root, manifest, schema = execution
    for key in ("query_pack", "protocol", "contract_schema"):
        altered = copy.deepcopy(manifest)
        altered[key]["path"] = "tests/fixtures/substitute.json"
        with pytest.raises(ValueError, match="schema|canonical path"):
            validate_execution(root, altered, schema)


def test_sensitive_artifact_refs_are_denied(execution):
    root, manifest, schema = execution
    manifest["collector"]["config"]["path"] = "a1/synthetic.json"
    with pytest.raises(ValueError, match="sensitive or runtime"):
        validate_execution(root, manifest, schema)


def test_403_never_becomes_verified(execution):
    root, manifest, schema = execution
    manifest["sources"][0]["http_status"] = 403
    with pytest.raises(ValueError, match="differs from capture result|cannot be verified"):
        validate_execution(root, manifest, schema)


def test_unproven_is_explicit_and_carries_no_laundered_support(execution):
    root, manifest, schema = execution
    item = manifest["inspections"][0]
    item.update({"support_status": "does_not_establish", "observations": [],
                 "reason": "The bounded inspection did not establish this field."})
    assert validate_execution(root, manifest, schema) is True
    item["observations"] = [{"source_id": item["source_ids"][0], "value": True,
                             "excerpt_span": [0, 1], "supporting_text": "s"}]
    with pytest.raises(ValueError, match="does_not_establish|wrong value type|captured text"):
        validate_execution(root, manifest, schema)


def test_conflict_requires_distinct_content_and_opposing_typed_values(execution):
    root, manifest, schema = execution
    item = manifest["inspections"][0]
    item["support_status"] = "conflicted"
    with pytest.raises(ValueError, match="at least two verified"):
        validate_execution(root, manifest, schema)


def test_wrong_typed_observation_is_rejected(execution):
    root, manifest, schema = execution
    boolean_item = next(item for item in manifest["inspections"] if item["field_id"] == "local_execution")
    boolean_item["observations"][0]["value"] = "yes"
    with pytest.raises(ValueError, match="wrong value type"):
        validate_execution(root, manifest, schema)


def test_fabricated_value_is_not_supported_by_generic_excerpt(execution):
    root, manifest, schema = execution
    item = next(item for item in manifest["inspections"] if item["field_id"] == "license_spdx")
    item["observations"][0]["value"] = "Apache-2.0-fabricated"
    with pytest.raises(ValueError, match="does not support the proposed typed value"):
        validate_execution(root, manifest, schema)


def test_lexical_matcher_rejects_identifier_and_number_substrings():
    assert not typed_lexical_support_matches("This feature is limited.", "MIT", "string", "license_spdx")
    assert typed_lexical_support_matches("SPDX-License-Identifier: MIT", "MIT", "string", "license_spdx")
    assert not typed_lexical_support_matches("The snapshot reports 100 stars.", 10, "integer", "github_stars")
    assert typed_lexical_support_matches("The snapshot reports 10 stars.", 10, "integer", "github_stars")


def test_phrase_boundary_accepts_sentence_dot_but_rejects_dotted_identifier():
    assert typed_lexical_support_matches("The documented export is CSV.", ["csv"], "string_list", "export_format_ids")
    assert not typed_lexical_support_matches("The documented export is CSV.xlsx", ["csv"], "string_list", "export_format_ids")
    assert not typed_lexical_support_matches("Use format.CSV for this value", ["csv"], "string_list", "export_format_ids")


def test_pricing_matcher_uses_structured_decimal_anchors():
    value = {
        "disclosure_status": "public_exact", "currency": "CZK", "vat_status": "excluded",
        "billing_period": "month", "unit": "subscription",
        "tiers": [{"name": "Basic", "amount": 10, "included_units": 5, "overage_amount": 2}],
    }
    assert not typed_lexical_support_matches("Exact price is 100 CZK; includes 5, overage 2.", value, "pricing", "pricing")
    assert typed_lexical_support_matches("Exact price is 10 CZK; includes 5, overage 2.", value, "pricing", "pricing")


def test_collector_proposed_complete_execution_remains_exit_two(execution):
    root, manifest, schema = execution
    manifest["authority_classification"] = "collector_proposed"
    manifest["evidence_scope"] = "collector_proposal_not_market_evidence"
    config_path = root / manifest["collector"]["config"]["path"]
    manifest["collector"]["config_digest"] = semantic_sha256(json.loads(config_path.read_text()))
    assert validate_execution(root, manifest, schema) is True


def test_collector_proposed_config_digest_must_bind_config_semantics(execution):
    root, manifest, schema = execution
    manifest["authority_classification"] = "collector_proposed"
    manifest["evidence_scope"] = "collector_proposal_not_market_evidence"
    manifest["collector"]["config_digest"] = "0" * 64
    with pytest.raises(ValueError, match="config_digest does not match bound config semantics"):
        validate_execution(root, manifest, schema)


def test_duplicate_slot_source_and_excerpt_reuse_are_rejected(execution):
    root, manifest, schema = execution
    duplicate = copy.deepcopy(manifest["inspections"][0])
    manifest["inspections"].append(duplicate)
    with pytest.raises(ValueError, match="duplicate inspection"):
        validate_execution(root, manifest, schema)
    manifest["inspections"].pop()
    manifest["sources"][1]["excerpt_ref"] = manifest["sources"][0]["excerpt_ref"]
    with pytest.raises(ValueError, match="differs from capture result|reused"):
        validate_execution(root, manifest, schema)


def test_cli_exit_codes_and_read_only_behavior(execution):
    root, manifest, _schema = execution
    manifest_path = root / "execution.json"
    write_json(manifest_path, manifest)
    before = {path.relative_to(root): sha(path) for path in root.rglob("*") if path.is_file()}
    command = [sys.executable, str(PROJECT / "scripts/validate_collector_execution.py"),
               "--root", str(root), "--input", "execution.json", "--json"]
    complete = subprocess.run(command, text=True, capture_output=True, check=False)
    assert complete.returncode == 0, complete.stdout + complete.stderr
    assert json.loads(complete.stdout)["status"] == "valid-complete"
    after = {path.relative_to(root): sha(path) for path in root.rglob("*") if path.is_file()}
    assert after == before
    manifest["inspections"][0].update({
        "support_status": "does_not_establish", "observations": [],
        "reason": "The bounded inspection did not establish this field.",
    })
    write_json(manifest_path, manifest)
    assert subprocess.run(command, capture_output=True, check=False).returncode == 2
    manifest["inspections"].pop()
    write_json(manifest_path, manifest)
    assert subprocess.run(command, capture_output=True, check=False).returncode == 1


def test_cli_input_must_be_contained_by_root(execution, tmp_path):
    root, _manifest, _schema = execution
    outside = tmp_path / "outside.json"
    write_json(outside, {})
    command = [sys.executable, str(PROJECT / "scripts/validate_collector_execution.py"),
               "--root", str(root), "--input", str(outside), "--json"]
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    assert result.returncode == 1
    assert "escapes project root" in result.stdout


def test_end_to_end_synthetic_capture_output_can_feed_collector(execution):
    root, manifest, schema = execution
    capture_script = root / "scripts/capture_research_sources.py"
    capture_script.write_bytes((PROJECT / "scripts/capture_research_sources.py").read_bytes())
    source = manifest["sources"][0]
    original_capture = json.loads((root / source["capture_manifest_ref"]).read_text())
    row = next(row for row in original_capture["results"] if row["id"] == source["capture_result_id"])
    request = {
        "schema_version": "source-capture-1.1", "run_id": "capture-e2e",
        "query_pack_version": original_capture["query_pack_version"],
        "query_pack_hash": original_capture["query_pack_hash"],
        "requests": [{"id": "page", "url": source["requested_url"], "method": "GET",
                      "field_targets": row["field_targets"],
                      "excerpt": {"selector": "term-window",
                                  "terms": ["support detail"], "max_chars": 500}}],
    }
    request_path = root / "research/acquisition/requests/capture-e2e.json"
    write_json(request_path, request)
    fixtures = root / "tests/fixtures/capture-e2e"
    fixtures.mkdir(parents=True)
    excerpt_text = (root / source["excerpt_ref"]).read_text().strip()
    write_json(fixtures / "page.json", {
        "requested_url": source["requested_url"], "final_url": source["requested_url"],
        "redirect_chain": [], "http_status": 200, "retrieved_at": "2026-08-14T12:00:00Z",
        "content_type": "text/plain", "body_text": excerpt_text,
    })
    output = root / "research/acquisition/source-captures/capture-e2e"
    run = subprocess.run([sys.executable, str(capture_script), "--root", str(root),
                          "--input", request_path.relative_to(root).as_posix(),
                          "--output", output.relative_to(root).as_posix(),
                          "--fixture-dir", fixtures.relative_to(root).as_posix()],
                         text=True, capture_output=True)
    assert run.returncode == 0, run.stdout + run.stderr
    captured_manifest_path = output / "manifest.json"
    captured_manifest = json.loads(captured_manifest_path.read_text())
    captured = captured_manifest["results"][0]
    source.update({
        "capture_manifest_ref": captured_manifest_path.relative_to(root).as_posix(),
        "capture_manifest_sha256": sha(captured_manifest_path), "capture_run_id": "capture-e2e",
        "capture_mode": "fixture", "capture_result_id": "page",
        "capture_result_sha256": semantic_sha256(captured), "requested_url": captured["requested_url"],
        "final_url": captured["final_url"], "redirect_chain": captured["redirect_chain"],
        "http_status": captured["http_status"], "retrieved_at": captured["retrieved_at"],
        "content_type": captured["content_type"], "response_sha256": captured["response_sha256"],
        "excerpt_sha256": captured["excerpt"]["sha256"],
        "excerpt_ref": (output / captured["excerpt"]["path"]).relative_to(root).as_posix(),
    })
    assert validate_execution(root, manifest, schema) is False
