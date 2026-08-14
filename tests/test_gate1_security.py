#!/usr/bin/env python3
"""Lock-in tests for Gate 1 security/validation repairs (Plan AC/AD).

Targets:
  * cockpit: `</script>` and Unicode-separator escaping, CSP (no unsafe-inline),
    no executable injection of raw JSON;
  * validator: honors `--input`, runs indexed relationship/state invariants,
    rejects unsupported schema versions;
  * normalizer: fail-closed on missing id / unresolved conflict (never silently
    drops, never overwrites canonical with invalid data), deterministic replace.

All scripts run against a temporary project-shaped root so canonical research
outputs are never mutated.
"""
import json
import sys
from pathlib import Path

import pytest

from _research_tmp import REPO, build_tmp_root, run_script, load, write_input, raw_dir

SCRIPTS = REPO / "scripts"
EMPTY = REPO / "tests" / "fixtures" / "research" / "envelope_empty.json"


@pytest.fixture
def root(tmp_path):
    return build_tmp_root(tmp_path)


# Make `scripts` importable as a namespace package (read-only unit imports).
sys.path.insert(0, str(REPO))
from scripts.generate_research_cockpit import render_html, safe_json_payload  # noqa: E402
from scripts.validate_research_schema import relationship_checks, SUPPORTED_VERSIONS  # noqa: E402


EMPTY_ENV = {
    "schema_version": "1.2", "run_id": "x", "as_of": "2026-08-14",
    "run_status": "collecting", "entities": [], "evidence": [], "reviews": [],
}


# ---------------------------------------------------------------------------
# Cockpit safety
# ---------------------------------------------------------------------------
def test_cockpit_escapes_closing_script_and_unicode():
    data = dict(EMPTY_ENV)
    data["entities"] = [{
        "id": "e1", "kind": "oss_project",
        "title": "</script><img src=x onerror=alert(1)>\u2028",
        "cohort": "oss_invoice", "source_links": ["https://example.com"],
        "scores": {"overall": 0},
    }]
    html = render_html(data)
    block = html.split('id="research-data">')[1].split("</script>")[0]
    assert "</script>" not in block
    assert "\u2028" not in block  # escaped
    payload = json.loads(block)
    assert payload["entities"][0]["title"] == "</script><img src=x onerror=alert(1)>\u2028"


def test_cockpit_csp_present_and_restrictive():
    html = render_html(EMPTY_ENV)
    assert "Content-Security-Policy" in html
    assert "object-src 'none'" in html
    assert "base-uri 'none'" in html
    assert "frame-ancestors 'none'" in html
    # No unrestricted inline script execution.
    assert "'unsafe-inline'" not in html


def test_cockpit_data_in_non_executable_block():
    html = render_html(EMPTY_ENV)
    assert "__DATA_JSON__" not in html
    assert '<script type="application/json" id="research-data">' in html


# ---------------------------------------------------------------------------
# Validator --input + relationship invariants
# ---------------------------------------------------------------------------
def test_validator_honors_input_path(tmp_path):
    root = build_tmp_root(tmp_path)
    env = load(EMPTY)
    alt = tmp_path / "alt_envelope.json"
    alt.write_text(json.dumps(env), encoding="utf-8")
    r = run_script(root, "validate_research_schema.py", "--input", str(alt))
    # Honors --input (reads the alt file, not the default root envelope).
    assert r.returncode == 0, r.stderr
    assert "alt_envelope.json" in r.stdout


def test_relationship_dangling_evidence_ref_fails():
    data = dict(EMPTY_ENV)
    data["entities"] = [{
        "id": "e1", "kind": "oss_project", "title": "X", "cohort": "oss_invoice",
        "source_links": ["https://example.com"], "last_verified": "2026-08-14",
        "offerings": {"received_invoice_processing": {"state": "unknown"}},
        "pricing": {"public_status": "unknown"},
        "claims": [{"field": "x", "value": "y", "evidence_ref": "ev-missing", "confidence": "unverified"}],
        "github_metrics": {}, "scores": {"overall": 0},
    }]
    res = relationship_checks(data)
    names = {r["name"]: r for r in res}
    assert not names["claim.evidence_ref resolves to evidence"]["passed"]


def test_relationship_nonhttp_url_fails():
    data = dict(EMPTY_ENV)
    data["entities"] = [{
        "id": "e1", "kind": "oss_project", "title": "X", "cohort": "oss_invoice",
        "source_links": ["javascript:alert(1)"], "last_verified": "2026-08-14",
        "offerings": {"received_invoice_processing": {"state": "unknown"}},
        "pricing": {"public_status": "unknown"},
        "claims": [], "github_metrics": {}, "scores": {"overall": 0},
    }]
    res = relationship_checks(data)
    names = {r["name"]: r for r in res}
    assert not names["all URLs are http/https"]["passed"]


def test_relationship_duplicate_entity_id_fails():
    e = {
        "id": "e1", "kind": "oss_project", "title": "X", "cohort": "oss_invoice",
        "source_links": ["https://example.com"], "last_verified": "2026-08-14",
        "offerings": {"received_invoice_processing": {"state": "unknown"}},
        "pricing": {"public_status": "unknown"},
        "claims": [], "github_metrics": {}, "scores": {"overall": 0},
    }
    data = dict(EMPTY_ENV)
    data["entities"] = [dict(e), dict(e)]
    res = relationship_checks(data)
    names = {r["name"]: r for r in res}
    assert not names["unique entity IDs"]["passed"]


def test_validator_rejects_unsupported_schema_version(root):
    env = load(EMPTY)
    env["schema_version"] = "1.1"
    env["schema_version_tool"] = "1.1"
    write_input(root, env)
    r = run_script(root, "validate_research_schema.py")
    assert r.returncode == 1, r.stderr
    assert "unsupported schema_version" in r.stdout


# ---------------------------------------------------------------------------
# Normalizer fail-closed
# ---------------------------------------------------------------------------
def _valid_entity(eid, title, link):
    return {
        "id": eid, "kind": "oss_project", "title": title, "cohort": "oss_invoice",
        "source_links": [link], "last_verified": "2026-08-14",
        "offerings": {"received_invoice_processing": {"state": "unknown"},
                      "issued_invoice_generation": {"state": "unknown"}},
        "pricing": {"public_status": "unknown"}, "claims": [],
        "github_metrics": {},
        "scores": {"source_authority": 1, "recency": 1, "corroboration": 1,
                   "completeness": 1, "accounting_fit": 1, "overall": 1,
                   "calculated": True, "calculated_at": "2026-08-14T00:00:00Z"},
    }


def test_normalizer_fails_on_missing_id(root):
    (raw_dir(root) / "oss_invoice.json").write_text(json.dumps({
        "lane": "oss_invoice", "as_of": "2026-08-14", "collector_version": "1.0.0",
        "records": [{"title": "no id"}], "note": "test",
    }), encoding="utf-8")
    r = run_script(root, "normalize_datasets.py")
    assert r.returncode == 1
    assert "missing id" in r.stderr.lower()


def test_normalizer_fails_on_unresolved_conflict(root):
    base = load(EMPTY)
    base["entities"] = [_valid_entity("dup-1", "A", "https://example.com")]
    write_input(root, base)
    (raw_dir(root) / "oss_invoice.json").write_text(json.dumps({
        "lane": "oss_invoice", "as_of": "2026-08-14", "collector_version": "1.0.0",
        "records": [_valid_entity("dup-1", "B", "https://example.com")],
        "note": "test",
    }), encoding="utf-8")
    r = run_script(root, "normalize_datasets.py")
    assert r.returncode == 1
    assert "conflict" in r.stderr.lower()


def test_normalizer_replace_resolves_conflict(root):
    base = load(EMPTY)
    base["entities"] = [_valid_entity("dup-1", "A", "https://example.com/a")]
    write_input(root, base)
    (raw_dir(root) / "oss_invoice.json").write_text(json.dumps({
        "lane": "oss_invoice", "as_of": "2026-08-14", "collector_version": "1.0.0",
        "records": [_valid_entity("dup-1", "B", "https://example.com/b")],
        "note": "test",
    }), encoding="utf-8")
    r = run_script(root, "normalize_datasets.py", "--replace")
    assert r.returncode == 0, r.stderr
    out = load(root / "research" / "processed" / "entities.normalized.json")
    assert [e["title"] for e in out["entities"] if e["id"] == "dup-1"] == ["B"]
