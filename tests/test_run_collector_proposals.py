"""Clean-root tests for deterministic, non-authoritative collector proposals."""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.run_collector_proposals import value_has_exact_lexical_anchor


REPO = Path(__file__).resolve().parents[1]
SCRIPTS = (
    "run_collector_proposals.py",
    "validate_collector_execution.py",
    "compare_research_runs.py",
    "check_evidence_url.py",
)
QUERY_FILES = (
    "plan-ac-core-1.1.json",
    "atomic-query-pack-1.1.schema.json",
    "plan-ac-collector-protocol-1.1.json",
    "collector-protocol-1.1.schema.json",
    "collector-execution-1.1.schema.json",
    "collector-proposal-input-1.0.schema.json",
    "source-capture-result-1.0.schema.json", "source-capture-result-1.1.schema.json",
)
INPUT_REF = "research/acquisition/collector-proposals/proposal.json"
OUTPUT_REF = "research/acquisition/collector-executions/proposal.json"
CAPTURE_REF = "research/acquisition/source-captures/proposal-capture/manifest.json"


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def semantic(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return sha_bytes(raw)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def clean_root(tmp_path: Path) -> tuple[Path, dict, dict]:
    root = tmp_path / "project"
    (root / "scripts").mkdir(parents=True)
    (root / "research/query-packs").mkdir(parents=True)
    for name in SCRIPTS:
        (root / "scripts" / name).write_bytes((REPO / "scripts" / name).read_bytes())
    for name in QUERY_FILES:
        (root / "research/query-packs" / name).write_bytes(
            (REPO / "research/query-packs" / name).read_bytes()
        )

    pack = json.loads((root / "research/query-packs/plan-ac-core-1.1.json").read_text())
    results = []
    decisions = []
    capture_dir = root / "research/acquisition/source-captures/proposal-capture"
    (capture_dir / "excerpts").mkdir(parents=True)
    for lane in pack["lanes"].values():
        for entity in lane["entities"]:
            capture_id = f"page-{entity['id']}"
            url = entity["allowed_official_source_roots"][0].rstrip("/") + "/proposal-test"
            anchors = [f"field {field['id'].replace('_', ' ')}" for field in lane["fields"]]
            text = "; ".join(anchors) + "."
            if entity["id"] == "oss-deepdoctection":
                text = f"{anchors[0]} Apache-2.0; " + "; ".join(anchors[1:]) + "."
            raw = text.encode("utf-8")
            excerpt_rel = f"excerpts/{capture_id}.txt"
            (capture_dir / excerpt_rel).write_bytes(raw)
            results.append({
                "id": capture_id,
                "requested_url": url,
                "state": "captured",
                "reason": None,
                "field_targets": [{"entity_id": entity["id"], "field_id": field["id"]}
                                  for field in lane["fields"]],
                "final_url": url,
                "redirect_chain": [],
                "requested_method": "GET",
                "performed_methods": ["GET"],
                "http_status": 200,
                "retrieved_at": "2026-08-14T12:00:00Z",
                "content_type": "text/plain",
                "response_sha256": sha_bytes(("response:" + entity["id"]).encode()),
                "response_bytes": len(raw),
                "excerpt": {
                    "selector": "term-window",
                    "terms": [anchors[0]],
                    "matched_terms": [anchors[0]],
                    "span": [0, len(text)],
                    "sha256": sha_bytes(raw),
                    "characters": len(text),
                    "truncated": False,
                    "path": excerpt_rel,
                },
            })
            for field, anchor in zip(lane["fields"], anchors):
                start = text.index(anchor)
                end = text.find(";", start)
                if end == -1:
                    end = len(text)
                evidence = {
                    "capture_manifest_ref": CAPTURE_REF,
                    "capture_result_id": capture_id,
                    "lexical_anchor": anchor,
                    "excerpt_span": [len(text[:start].encode()), len(text[:end].encode())],
                    "supporting_text": text[start:end],
                }
                decision = "does_not_establish"
                if (entity["id"], field["id"]) == ("oss-deepdoctection", "license_spdx"):
                    decision = "supports"
                    evidence["value"] = "Apache-2.0"
                decisions.append({
                    "entity_id": entity["id"],
                    "field_id": field["id"],
                    "decision": decision,
                    "captured_evidence": [evidence],
                    "unproven_capture_refs": [],
                    "reason": "The exact bounded excerpt was inspected for this frozen field.",
                })

    # One failed source is intentionally retained so does_not_establish decisions
    # can bind a truthful URL even when no excerpt exists.
    unproven_url = pack["lanes"]["czech_invoice_software"]["entities"][0][
        "allowed_official_source_roots"
    ][0].rstrip("/") + "/unreachable-test"
    results.append({
        "id": "unproven-vendor-alice",
        "requested_url": unproven_url,
        "state": "unproven",
        "reason": "Synthetic capture transport was unavailable.",
        "field_targets": [{"entity_id": "vendor-alice-redque", "field_id": field["id"]}
                          for field in pack["lanes"]["czech_invoice_software"]["fields"]],
    })
    manifest = {
        "schema_version": "source-capture-result-1.1",
        "run_id": "proposal-capture",
        "mode": "fixture",
        "query_pack_version": pack["query_pack_version"],
        "query_pack_hash": pack["query_pack_hash"],
        "request_sha256": "1" * 64,
        "results": results,
        "summary": {"captured": len(results) - 1, "unproven": 1, "invalid": 0},
    }
    manifest_path = root / CAPTURE_REF
    write_json(manifest_path, manifest)
    proposal = {
        "format_version": "collector-proposal-input-1.0",
        "run_id": "proposal-run-1",
        "execution_instance_id": "proposal-instance-1",
        "collector": {
            "collector_id": "deterministic-proposal-test",
            "provider": None,
            "model": None,
            "identity_verification": "unverified",
            "tools": [{"name": "bounded-capture-map", "version": "1.0"}],
        },
        "capture": {
            "started_at": "2026-08-14T11:00:00Z",
            "completed_at": "2026-08-14T13:00:00Z",
            "manifests": [{
                "path": CAPTURE_REF,
                "byte_sha256": sha_bytes(manifest_path.read_bytes()),
                "semantic_sha256": semantic(manifest),
            }],
        },
        "decisions": decisions,
    }
    write_json(root / INPUT_REF, proposal)
    return root, proposal, manifest


def rebind(root: Path, proposal: dict, manifest: dict) -> None:
    write_json(root / CAPTURE_REF, manifest)
    proposal["capture"]["manifests"][0].update({
        "byte_sha256": sha_bytes((root / CAPTURE_REF).read_bytes()),
        "semantic_sha256": semantic(manifest),
    })
    write_json(root / INPUT_REF, proposal)


def configure_numeric_conflict(
    root: Path,
    proposal: dict,
    manifest: dict,
    *,
    same_url: bool = False,
    same_content: bool = False,
    same_value: bool = False,
) -> None:
    """Create two exact sources for the Docling github_stars frozen slot."""
    target = next(
        row for row in proposal["decisions"]
        if row["entity_id"] == "oss-docling" and row["field_id"] == "github_stars"
    )
    original = next(row for row in manifest["results"] if row["id"] == "page-oss-docling")
    anchor = "field github stars"
    text_a = f"{anchor} 100 101 source alpha"
    text_b = text_a if same_content else f"{anchor} 100 101 source beta"
    first = copy.deepcopy(original)
    first["id"] = "page-oss-docling-conflict-a"
    first["requested_url"] = original["requested_url"] + "/conflict-a"
    first["final_url"] = first["requested_url"]
    second = copy.deepcopy(original)
    second["id"] = "page-oss-docling-conflict-b"
    second["requested_url"] = first["requested_url"] if same_url else original["requested_url"] + "/conflict-b"
    second["final_url"] = second["requested_url"]
    for row, text, excerpt_name in (
        (first, text_a, "conflict-docling-a.txt"),
        (second, text_b, "conflict-docling-b.txt"),
    ):
        raw = text.encode()
        row["excerpt"].update({
            "path": f"excerpts/{excerpt_name}",
            "sha256": sha_bytes(raw),
            "characters": len(text),
            "span": [0, len(text)],
            "terms": [anchor],
            "matched_terms": [anchor],
        })
        row["response_bytes"] = len(raw)
        (root / Path(CAPTURE_REF).parent / row["excerpt"]["path"]).write_bytes(raw)
    first["response_sha256"] = sha_bytes(b"response:docling-conflict-a")
    second["response_sha256"] = sha_bytes(b"response:docling-conflict")
    manifest["results"].extend((first, second))
    manifest["summary"]["captured"] += 2
    target.update({
        "decision": "conflict",
        "captured_evidence": [
            {
                "capture_manifest_ref": CAPTURE_REF,
                "capture_result_id": first["id"],
                "lexical_anchor": anchor,
                "excerpt_span": [0, len(text_a.encode())],
                "supporting_text": text_a,
                "value": 100,
            },
            {
                "capture_manifest_ref": CAPTURE_REF,
                "capture_result_id": second["id"],
                "lexical_anchor": anchor,
                "excerpt_span": [0, len(text_b.encode())],
                "supporting_text": text_b,
                "value": 100 if same_value else 101,
            },
        ],
        "unproven_capture_refs": [],
        "reason": "Two bounded source captures propose conflicting repository metrics.",
    })
    rebind(root, proposal, manifest)


def execute(root: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            "scripts/run_collector_proposals.py",
            "--root", ".",
            "--input", INPUT_REF,
            "--output", OUTPUT_REF,
            "--json",
            *extra,
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )


def validate_execution(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            "scripts/validate_collector_execution.py",
            "--root", ".",
            "--input", OUTPUT_REF,
            "--json",
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )


def test_generates_exact_hash_bound_non_authoritative_execution(tmp_path):
    root, proposal, _manifest = clean_root(tmp_path)
    result = execute(root)
    assert result.returncode == 0, result.stdout + result.stderr
    execution = json.loads((root / OUTPUT_REF).read_text())
    assert len(execution["inspections"]) == 230
    assert len({(row["entity_id"], row["field_id"]) for row in execution["inspections"]}) == 230
    assert execution["authority_classification"] == "collector_proposed"
    assert execution["evidence_scope"] == "collector_proposal_not_market_evidence"
    assert execution["operator_attestation"] is None
    assert execution["collector"]["identity_verification"] == "unverified"
    assert execution["collector"]["config_digest"] == semantic(proposal)
    for name in ("query_pack", "protocol", "contract_schema"):
        target = root / execution[name]["path"]
        assert execution[name]["byte_sha256"] == sha_bytes(target.read_bytes())
    assert execution["collector"]["implementation"]["path"] == "scripts/run_collector_proposals.py"
    checked = validate_execution(root)
    assert checked.returncode == 2, checked.stdout + checked.stderr
    assert json.loads(checked.stdout)["status"] == "valid-unproven"


def test_check_is_read_only_exact_and_generation_never_overwrites(tmp_path):
    root, _proposal, _manifest = clean_root(tmp_path)
    assert execute(root).returncode == 0
    before = {path.relative_to(root): sha_bytes(path.read_bytes()) for path in root.rglob("*") if path.is_file()}
    checked = execute(root, "--check")
    assert checked.returncode == 0, checked.stdout + checked.stderr
    after = {path.relative_to(root): sha_bytes(path.read_bytes()) for path in root.rglob("*") if path.is_file()}
    assert after == before
    second = execute(root)
    assert second.returncode == 1
    assert "refusing overwrite" in second.stdout
    output = root / OUTPUT_REF
    output.write_bytes(output.read_bytes() + b" ")
    stale = execute(root, "--check")
    assert stale.returncode == 1
    assert "stale" in stale.stdout


def test_unproven_capture_link_is_allowed_without_laundering_support(tmp_path):
    root, proposal, manifest = clean_root(tmp_path)
    target = next(
        row for row in proposal["decisions"]
        if row["entity_id"] == "vendor-alice-redque" and row["field_id"] == "public_api"
    )
    target["captured_evidence"] = []
    target["unproven_capture_refs"] = [{
        "capture_manifest_ref": CAPTURE_REF,
        "capture_result_id": "unproven-vendor-alice",
    }]
    rebind(root, proposal, manifest)
    result = execute(root)
    assert result.returncode == 0, result.stdout + result.stderr
    execution = json.loads((root / OUTPUT_REF).read_text())
    inspection = next(
        row for row in execution["inspections"]
        if row["entity_id"] == "vendor-alice-redque" and row["field_id"] == "public_api"
    )
    assert inspection["support_status"] == "does_not_establish"
    assert inspection["source_ids"] == [] and inspection["observations"] == []
    assert "Unproven capture requests: https://" in inspection["reason"]
    assert validate_execution(root).returncode == 2


def test_unattempted_slot_remains_explicit_does_not_establish(tmp_path):
    root, proposal, manifest = clean_root(tmp_path)
    target = next(
        row for row in proposal["decisions"]
        if row["entity_id"] == "vendor-alice-redque" and row["field_id"] == "public_api"
    )
    target["captured_evidence"] = []
    target["unproven_capture_refs"] = []
    target["reason"] = "No bounded source capture was assigned to this frozen slot."
    rebind(root, proposal, manifest)
    result = execute(root)
    assert result.returncode == 0, result.stdout + result.stderr
    execution = json.loads((root / OUTPUT_REF).read_text())
    inspection = next(
        row for row in execution["inspections"]
        if row["entity_id"] == "vendor-alice-redque" and row["field_id"] == "public_api"
    )
    assert inspection["support_status"] == "does_not_establish"
    assert inspection["source_ids"] == []
    assert validate_execution(root).returncode == 2


def test_fabricated_typed_value_is_rejected_before_output(tmp_path):
    root, proposal, manifest = clean_root(tmp_path)
    target = next(
        row for row in proposal["decisions"]
        if row["entity_id"] == "oss-deepdoctection" and row["field_id"] == "license_spdx"
    )
    target["captured_evidence"][0]["value"] = "Fabricated-Proprietary-License"
    rebind(root, proposal, manifest)
    result = execute(root)
    assert result.returncode == 1
    assert "does not contain the complete proposed value" in result.stdout
    assert not (root / OUTPUT_REF).exists()


def test_boundary_matcher_rejects_substrings_and_numeric_prefixes():
    assert value_has_exact_lexical_anchor("SPDX licence: MIT.", "MIT", "string")
    assert not value_has_exact_lexical_anchor("This is a limited licence.", "MIT", "string")
    assert value_has_exact_lexical_anchor("There are exactly 10 stars.", 10, "integer")
    assert not value_has_exact_lexical_anchor("There are exactly 100 stars.", 10, "integer")


def test_structured_pricing_requires_currency_amount_period_unit_and_vat_anchors():
    pricing = {
        "disclosure_status": "public_exact",
        "currency": "CZK",
        "vat_status": "excluded",
        "billing_period": "month",
        "unit": "subscription",
        "tiers": [{
            "name": "Basic",
            "amount": 1.0,
            "included_units": 10,
            "overage_amount": None,
        }],
    }
    complete = "Public exact Basic CZK 1.0, 10 units per month subscription, VAT excluded."
    assert value_has_exact_lexical_anchor(complete, pricing, "pricing")
    assert not value_has_exact_lexical_anchor(complete.replace("1.0", "1"), pricing, "pricing")
    assert not value_has_exact_lexical_anchor(complete.replace("CZK", "EUR"), pricing, "pricing")
    assert not value_has_exact_lexical_anchor(complete.replace("per month", "weekly"), pricing, "pricing")


@pytest.mark.parametrize(
    ("argument", "value"),
    (("--input", "../proposal.json"), ("--output", "../execution.json")),
)
def test_cli_rejects_path_escape_without_writes(tmp_path, argument, value):
    root, _proposal, _manifest = clean_root(tmp_path)
    command = [
        sys.executable,
        "scripts/run_collector_proposals.py",
        "--root", ".",
        "--input", INPUT_REF,
        "--output", OUTPUT_REF,
        argument, value,
        "--json",
    ]
    result = subprocess.run(command, cwd=root, text=True, capture_output=True, check=False)
    assert result.returncode == 1
    assert "path" in result.stdout and ("escapes" in result.stdout or "relative" in result.stdout)
    assert not (root / OUTPUT_REF).exists()


def test_missing_and_duplicate_slots_fail_closed(tmp_path):
    root, proposal, manifest = clean_root(tmp_path)
    proposal["decisions"].pop()
    rebind(root, proposal, manifest)
    missing = execute(root)
    assert missing.returncode == 1
    assert "missing decisions" in missing.stdout
    root, proposal, manifest = clean_root(tmp_path / "again")
    proposal["decisions"].append(copy.deepcopy(proposal["decisions"][0]))
    rebind(root, proposal, manifest)
    duplicate = execute(root)
    assert duplicate.returncode == 1
    assert "duplicate field decision" in duplicate.stdout


def test_conflict_requires_two_distinct_captured_sources(tmp_path):
    root, proposal, manifest = clean_root(tmp_path)
    target = next(
        row for row in proposal["decisions"]
        if row["entity_id"] == "vendor-alice-redque"
        and row["field_id"] == "received_invoice_extraction"
    )
    target["decision"] = "conflict"
    target["captured_evidence"][0]["value"] = True
    rebind(root, proposal, manifest)
    result = execute(root)
    assert result.returncode == 1
    assert "too short" in result.stdout or "at least two" in result.stdout
    assert not (root / OUTPUT_REF).exists()


def test_capture_binding_and_exact_span_tampering_fail_closed(tmp_path):
    root, proposal, manifest = clean_root(tmp_path)
    proposal["capture"]["manifests"][0]["byte_sha256"] = "0" * 64
    write_json(root / INPUT_REF, proposal)
    result = execute(root)
    assert result.returncode == 1
    assert "byte hash mismatch" in result.stdout
    root, proposal, manifest = clean_root(tmp_path / "span")
    proposal["decisions"][0]["captured_evidence"][0]["supporting_text"] += " fabricated"
    rebind(root, proposal, manifest)
    result = execute(root)
    assert result.returncode == 1
    assert "exact byte span" in result.stdout


def test_execution_detects_implementation_and_config_tampering(tmp_path):
    root, proposal, manifest = clean_root(tmp_path)
    assert execute(root).returncode == 0
    implementation = root / "scripts/run_collector_proposals.py"
    implementation.write_bytes(implementation.read_bytes() + b"\n# tampered after execution\n")
    result = validate_execution(root)
    assert result.returncode == 1
    assert "byte hash mismatch" in result.stdout

    root, proposal, manifest = clean_root(tmp_path / "config")
    assert execute(root).returncode == 0
    proposal["decisions"][1]["reason"] = "A changed proposal reason invalidates the exact config binding."
    rebind(root, proposal, manifest)
    result = validate_execution(root)
    assert result.returncode == 1
    assert "byte hash mismatch" in result.stdout
    check = execute(root, "--check")
    assert check.returncode == 1 and "stale" in check.stdout


@pytest.mark.parametrize(
    ("variant", "expected"),
    (
        ("same_url", "distinct source URLs"),
        ("same_content", "distinct content hashes"),
        ("same_value", "opposing typed values"),
    ),
)
def test_e2e_conflict_rejects_laundered_sources(tmp_path, variant, expected):
    root, proposal, manifest = clean_root(tmp_path)
    configure_numeric_conflict(
        root,
        proposal,
        manifest,
        same_url=variant == "same_url",
        same_content=variant == "same_content",
        same_value=variant == "same_value",
    )
    result = execute(root)
    assert result.returncode == 1
    assert expected in result.stdout
    assert not (root / OUTPUT_REF).exists()
