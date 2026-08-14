#!/usr/bin/env python3
"""Tests for Plan AC research tooling (schema v1.2 envelope).

Covers empty/partial/complete/accepted runs, adversarial inputs, completeness
exit codes, derived counts, calculated (not copied) scores, normalizer
envelope preservation + deterministic replacement, and cockpit safety/--check
parity.

Every script runs against a temporary project-shaped root (see ``_research_tmp``)
so canonical research outputs are never mutated.
"""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from _research_tmp import (REPO, build_tmp_root, run_script, load, write_input,
                           processed, raw_dir)

FIX = REPO / "tests" / "fixtures" / "research"
EMPTY = FIX / "envelope_empty.json"
PARTIAL = FIX / "envelope_partial.json"
INVALID = FIX / "envelope_invalid_accepted.json"

SCRIPTS = REPO / "scripts"


@pytest.fixture
def root(tmp_path):
    return build_tmp_root(tmp_path)


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------
def test_empty_envelope_validates(root):
    write_input(root, load(EMPTY))
    r = run_script(root, "validate_research_schema.py")
    assert r.returncode == 0, r.stderr


def test_partial_envelope_validates(root):
    write_input(root, load(PARTIAL))
    r = run_script(root, "validate_research_schema.py")
    assert r.returncode == 0, r.stderr


def test_invalid_accepted_envelope_fails_completeness(root):
    write_input(root, load(INVALID))
    r = run_script(root, "validate_research_schema.py")
    c = run_script(root, "check_research_completeness.py")
    # accepted with unmet quota + dangling evidence_ref + scores.calculated=false
    assert r.returncode == 1, r.stderr
    assert c.returncode == 1, c.stderr


def test_malformed_date_rejected(root):
    bad = load(EMPTY)
    bad["as_of"] = "2026-13-99"
    write_input(root, bad)
    r = run_script(root, "validate_research_schema.py")
    assert r.returncode == 1


def test_non_http_evidence_url_rejected(root):
    bad = load(PARTIAL)
    bad["entities"][0]["source_links"] = ["javascript:alert(1)"]
    write_input(root, bad)
    r = run_script(root, "validate_research_schema.py")
    assert r.returncode == 1


def test_duplicate_entity_id_rejected(root):
    bad = load(PARTIAL)
    e2 = dict(bad["entities"][0])
    e2["id"] = bad["entities"][1]["id"]  # force collision
    bad["entities"].append(e2)
    write_input(root, bad)
    r = run_script(root, "validate_research_schema.py")
    assert r.returncode == 1


def test_dangling_evidence_ref_detected_by_completeness(root):
    bad = load(PARTIAL)
    bad["evidence"] = []
    write_input(root, bad)
    c = run_script(root, "check_research_completeness.py")
    assert c.returncode == 1
    assert "evidence" in c.stderr.lower()


# ---------------------------------------------------------------------------
# Completeness (derived counts)
# ---------------------------------------------------------------------------
def test_completeness_fails_on_empty(root):
    write_input(root, load(EMPTY))
    c = run_script(root, "check_research_completeness.py")
    assert c.returncode == 1


def test_completeness_derives_counts_not_self_reported(root):
    partial = load(PARTIAL)
    write_input(root, partial)
    c = run_script(root, "check_research_completeness.py")
    report = load(processed(root) / "completeness_report.json")
    assert report["derived_counts"]["oss_invoice"] == 1
    assert report["derived_counts"]["czech_invoice_software"] == 1
    assert c.returncode == 1  # quotas (10) unmet


def test_pilot_review_gate_reports_unreviewed_entities(root):
    write_input(root, load(PARTIAL))
    c = run_script(root, "check_research_completeness.py", "--min-reviews-per-entity", "2")
    report = load(processed(root) / "completeness_report.json")
    assert c.returncode == 1
    assert set(report["review_shortfall"]) == {e["id"] for e in load(PARTIAL)["entities"]}
    assert report["minimum_reviews_per_entity"] == 2


# ---------------------------------------------------------------------------
# Scoring calculates, does not copy
# ---------------------------------------------------------------------------
def test_score_calculates_from_evidence(root):
    partial = load(PARTIAL)
    write_input(root, partial)
    output = processed(root) / "scored.json"
    before = (processed(root) / "entities.json").read_bytes()
    r = run_script(root, "score_research_results.py",
                   "--as-of", "2026-08-14", "--output", str(output))
    assert r.returncode == 0, r.stderr
    scored = load(output)
    assert scored["schema_version"] == "1.2"
    for entity in scored["entities"]:
        assert entity["scores"]["calculated"] is True
        assert isinstance(entity["scores"]["overall"], (int, float))
        assert 0 <= entity["scores"]["overall"] <= 100
    assert (processed(root) / "entities.json").read_bytes() == before


def test_score_unproven_without_evidence(root):
    one = load(EMPTY)
    entity = load(PARTIAL)["entities"][0]
    entity["claims"] = []
    for capability in entity["offerings"].values():
        if isinstance(capability, dict):
            capability.pop("evidence_ref", None)
            if capability.get("state") == "confirmed":
                capability["state"] = "unknown"
    for tier in entity["pricing"].get("tiers", []):
        tier.pop("evidence_ref", None)
    one["entities"] = [entity]
    write_input(root, one)
    output = processed(root) / "scored.json"
    r = run_script(root, "score_research_results.py",
                   "--as-of", "2026-08-14", "--output", str(output))
    assert r.returncode == 0, r.stderr
    scored = load(output)
    assert scored["entities"][0]["scores"]["overall"] == "unproven"


def test_score_requires_explicit_as_of_and_output(root):
    write_input(root, load(PARTIAL))
    canonical = processed(root) / "entities.json"
    before = canonical.read_bytes()
    r = run_script(root, "score_research_results.py")
    assert r.returncode != 0
    assert canonical.read_bytes() == before


def test_score_refuses_invalid_input_without_writing(root):
    bad = load(PARTIAL)
    bad["entities"][0]["source_links"] = ["file:///etc/passwd"]
    write_input(root, bad)
    output = processed(root) / "must-not-exist.json"
    r = run_script(root, "score_research_results.py",
                   "--as-of", "2026-08-14", "--output", str(output))
    assert r.returncode == 1
    assert not output.exists()


# ---------------------------------------------------------------------------
# Normalizer preserves envelope + deterministic replacement
# ---------------------------------------------------------------------------
def test_normalizer_preserves_envelope_fields(root):
    write_input(root, load(EMPTY))
    r = run_script(root, "normalize_datasets.py")
    assert r.returncode == 0, r.stderr
    out = load(processed(root) / "entities.normalized.json")
    assert out["schema_version"] == "1.2"
    assert "as_of" in out and "run_id" in out
    assert "entities" in out and "evidence" in out and "reviews" in out


def test_normalizer_accepts_explicit_candidate_identity(root):
    write_input(root, load(EMPTY))
    r = run_script(
        root,
        "normalize_datasets.py",
        "--run-id", "research-ac-pilot-2026-08-14",
        "--run-status", "schema_valid",
        "--as-of", "2026-08-14",
    )
    assert r.returncode == 0, r.stderr
    out = load(processed(root) / "entities.normalized.json")
    assert out["run_id"] == "research-ac-pilot-2026-08-14"
    assert out["run_status"] == "schema_valid"


def test_normalizer_replace_replaces_by_id(root):
    base = load(EMPTY)
    base["entities"] = [{
        "id": "oss-x", "kind": "oss_project", "title": "Old", "cohort": "oss_invoice",
        "source_links": ["https://example.com/old"], "last_verified": "2026-08-14",
        "offerings": {"received_invoice_processing": {"state": "unknown"},
                      "issued_invoice_generation": {"state": "unknown"}},
        "pricing": {"public_status": "unknown"}, "claims": [],
        "github_metrics": {},
        "scores": {"source_authority": 1, "recency": 1, "corroboration": 1,
                   "completeness": 1, "accounting_fit": 1, "overall": 1,
                   "calculated": True, "calculated_at": "2026-08-14T00:00:00Z"},
    }]
    base["evidence"] = [{"id": "ev-x", "entity_id": "oss-x", "claim_field": "f",
                         "canonical_url": "https://example.com/old", "publisher": "Old",
                         "source_type": "other", "retrieval_date": "2026-08-14",
                         "confidence": "low", "corroboration_status": "single_source"}]
    write_input(root, base)

    replacement = {
        "lane": "oss_invoice", "as_of": "2026-08-14", "collector_version": "1.0.0",
        "records": [{"id": "oss-x", "kind": "oss_project", "title": "New", "cohort": "oss_invoice",
                     "source_links": ["https://example.com/new"], "last_verified": "2026-08-14",
                     "offerings": {"received_invoice_processing": {"state": "unknown"},
                                   "issued_invoice_generation": {"state": "unknown"}},
                     "pricing": {"public_status": "unknown"}, "claims": [],
                     "github_metrics": {},
                     "scores": {"source_authority": 2, "recency": 2, "corroboration": 2,
                                "completeness": 2, "accounting_fit": 2, "overall": 2,
                                "calculated": True, "calculated_at": "2026-08-14T00:00:00Z"}}],
        "evidence": [{"id": "ev-y", "entity_id": "oss-x", "claim_field": "f",
                      "canonical_url": "https://example.com/new", "publisher": "New",
                      "source_type": "other", "retrieval_date": "2026-08-14",
                      "confidence": "low", "corroboration_status": "single_source"}],
    }
    (raw_dir(root) / "oss_invoice.json").write_text(json.dumps(replacement, indent=2), encoding="utf-8")

    r = run_script(root, "normalize_datasets.py", "--replace")
    assert r.returncode == 0, r.stderr
    out = load(processed(root) / "entities.normalized.json")
    ents = [e for e in out["entities"] if e["id"] == "oss-x"]
    assert len(ents) == 1, "entity must be replaced, not duplicated"
    assert ents[0]["title"] == "New"
    evs = [e for e in out["evidence"] if e["entity_id"] == "oss-x"]
    assert len(evs) == 1 and evs[0]["id"] == "ev-y", "dependent evidence must be replaced"

    v = run_script(root, "validate_research_schema.py",
                   "--input", str(processed(root) / "entities.normalized.json"))
    assert v.returncode == 0, v.stderr


# ---------------------------------------------------------------------------
# Cockpit safety + --check parity
# ---------------------------------------------------------------------------
def test_cockpit_check_passes_on_valid_envelope(root):
    write_input(root, load(EMPTY))
    g = run_script(root, "generate_research_cockpit.py")
    assert g.returncode == 0, g.stderr
    c = run_script(root, "generate_research_cockpit.py", "--check")
    assert c.returncode == 0, c.stderr


def test_cockpit_no_innerhtml_injection(root):
    partial = load(PARTIAL)
    partial["entities"][0]["title"] = "<img src=x onerror=alert(1)>"
    write_input(root, partial)
    r = run_script(root, "generate_research_cockpit.py")
    assert r.returncode == 0, r.stderr
    html = (root / "docs" / "prototypes" / "research-cockpit" / "index.html").read_text()
    assert "__DATA_JSON__" not in html
    assert "<img src=x onerror=alert(1)>" not in html.split("<body>")[-1].split("<script>")[0]


def test_cockpit_renders_partial_with_rows(root):
    write_input(root, load(PARTIAL))
    r = run_script(root, "generate_research_cockpit.py")
    assert r.returncode == 0, r.stderr
    html = (root / "docs" / "prototypes" / "research-cockpit" / "index.html").read_text()
    assert "Docling" in html and "Fakturoid" in html


# ---------------------------------------------------------------------------
# Collector does not touch canonical output
# ---------------------------------------------------------------------------
def test_collector_writes_raw_not_canonical(root):
    before = (processed(root) / "entities.json").read_text()
    r = run_script(root, "collect_market_evidence.py")
    assert r.returncode == 0, r.stderr
    after = (processed(root) / "entities.json").read_text()
    assert before == after
    assert (raw_dir(root) / "oss_invoice.json").is_file()


# ---------------------------------------------------------------------------
# URL checker honesty
# ---------------------------------------------------------------------------
def test_url_check_fixture_only_no_fabrication(root):
    write_input(root, load(PARTIAL))
    output = processed(root) / "evidence_checks.json"
    r = run_script(root, "check_evidence_url.py", "--output", str(output))
    assert r.returncode == 2, r.stderr
    out = load(output)
    for res in out["results"]:
        assert res["mode"] == "fixture-only"
        if res["verdict"] == "verified":
            assert False, "unexpected verified without fixture"


# ---------------------------------------------------------------------------
# Synthetic benchmark ground-truth gate
# ---------------------------------------------------------------------------
def test_benchmark_ground_truth_fiscally_correct(root):
    gt_path = root / "research" / "synthetic" / "ground_truth.json"
    if not gt_path.is_file():
        pytest.skip("run benchmark_groundtruth.py first")
    gt = load(gt_path)
    assert gt["count"] >= 20
    for inv in gt["invoices"]:
        assert inv["requires_accountant_review"] is True
        if not inv["is_historical_rate"]:
            assert inv["vat_rate_key"] in ("standard_21", "reduced_12")
        ico = inv["supplier_ico"]
        if ico:
            base, check = ico[:7], ico[7]
            spec = importlib.util.spec_from_file_location("bt_mod", SCRIPTS / "benchmark_groundtruth.py")
            bt = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(bt)
            assert bt.ico_checksum(base) == check


def test_benchmark_artifacts_rendered(root):
    man = root / "research" / "synthetic" / "artifact_manifest.json"
    if not man.is_file():
        pytest.skip("run create_synthetic_benchmark.py first")
    m = load(man)
    assert len(m["artifacts"]) >= 20
    for a in m["artifacts"]:
        p = root / a["artifacts"]["clean_pdf"]
        assert p.is_file()


# ---------------------------------------------------------------------------
# Adversarial: run-level acceptance + evidence laundering (Gate 1A §3)
# ---------------------------------------------------------------------------
def test_accepted_empty_run_fails(root):
    env = load(EMPTY)
    env["run_status"] = "accepted"
    write_input(root, env)
    assert run_script(root, "validate_research_schema.py").returncode == 1
    assert run_script(root, "check_research_completeness.py").returncode == 1


def test_accepted_without_reviewer_fails(root):
    env = load(PARTIAL)
    env["run_status"] = "accepted"
    env["reviews"] = []
    write_input(root, env)
    assert run_script(root, "validate_research_schema.py").returncode == 1


def test_accepted_without_calculated_scores_fails(root):
    env = load(PARTIAL)
    env["run_status"] = "accepted"
    for e in env["entities"]:
        e["scores"]["calculated"] = False
    write_input(root, env)
    assert run_script(root, "validate_research_schema.py").returncode == 1


def test_cross_entity_evidence_reuse_fails(root):
    env = load(PARTIAL)
    # point fakturoid's claim evidence to ev-1 (belongs to docling)
    env["entities"][1]["claims"][0]["evidence_ref"] = "ev-1"
    write_input(root, env)
    assert run_script(root, "validate_research_schema.py").returncode == 1


def test_duplicate_evidence_id_fails(root):
    env = load(PARTIAL)
    ev2 = dict(env["evidence"][1])
    ev2["id"] = env["evidence"][0]["id"]
    env["evidence"].append(ev2)
    write_input(root, env)
    assert run_script(root, "validate_research_schema.py").returncode == 1


def test_duplicate_review_id_fails(root):
    env = load(PARTIAL)
    env["reviews"].append(dict(env["reviews"][0]))
    write_input(root, env)
    assert run_script(root, "validate_research_schema.py").returncode == 1


def test_claim_field_mismatch_fails(root):
    env = load(PARTIAL)
    env["entities"][0]["claims"][0]["field"] = "wrong_field"
    write_input(root, env)
    assert run_script(root, "validate_research_schema.py").returncode == 1


def test_unsupported_schema_version_rejected(root):
    env = load(EMPTY)
    env["schema_version"] = "1.1"
    env["schema_version_tool"] = "1.1"
    write_input(root, env)
    assert run_script(root, "validate_research_schema.py").returncode == 1
