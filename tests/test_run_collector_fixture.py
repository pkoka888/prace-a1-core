"""Clean-room tests for the canonical synthetic collector mini-pilot."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPTS = (
    "run_collector_fixture.py", "validate_collector_execution.py",
    "capture_research_sources.py", "compare_research_runs.py", "check_evidence_url.py",
)
QUERY_FILES = (
    "plan-ac-core-1.1.json", "atomic-query-pack-1.1.schema.json",
    "plan-ac-collector-protocol-1.1.json", "collector-protocol-1.1.schema.json",
    "collector-execution-1.1.schema.json", "source-capture-1.0.schema.json",
    "source-capture-result-1.0.schema.json", "source-capture-1.1.schema.json",
    "source-capture-result-1.1.schema.json",
)


def clean_root(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    (root / "scripts").mkdir(parents=True)
    (root / "research/query-packs").mkdir(parents=True)
    (root / "research/acquisition/synthetic-mini-pilot").mkdir(parents=True)
    for name in SCRIPTS:
        (root / "scripts" / name).write_bytes((REPO / "scripts" / name).read_bytes())
    for name in QUERY_FILES:
        (root / "research/query-packs" / name).write_bytes((REPO / "research/query-packs" / name).read_bytes())
    for name in ("fixture-set.json", "fixture-set.schema.json"):
        target = root / "research/acquisition/synthetic-mini-pilot" / name
        target.write_bytes((REPO / "research/acquisition/synthetic-mini-pilot" / name).read_bytes())
    return root


def run(root: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(root / "scripts/run_collector_fixture.py"),
         "--root", str(root), "--run-id", "clean-room-1",
         "--output", "research/acquisition/synthetic-mini-pilot/runs/clean-room-1.json", *extra],
        text=True, capture_output=True, check=False,
    )


def test_clean_room_generates_capture_and_exact_230_decisions_then_validates(tmp_path):
    root = clean_root(tmp_path)
    output = root / "research/acquisition/synthetic-mini-pilot/runs/clean-room-1.json"
    capture = root / "research/acquisition/source-captures/clean-room-1"
    assert not output.exists() and not capture.exists()
    result = run(root)
    assert result.returncode == 0, result.stdout + result.stderr
    execution = json.loads(output.read_text())
    assert execution["evidence_scope"] == "synthetic_fixture_only_not_market_evidence"
    assert execution["authority_classification"] == "synthetic_fixture_verified"
    assert len(execution["inspections"]) == 230
    assert len({(row["entity_id"], row["field_id"]) for row in execution["inspections"]}) == 230
    assert len(execution["sources"]) == 20
    assert (capture / "manifest.json").is_file()
    capture_manifest = json.loads((capture / "manifest.json").read_text())
    assert capture_manifest["schema_version"] == "source-capture-result-1.1"
    assert all(row["field_targets"] for row in capture_manifest["results"])
    assert len(list((capture / "excerpts").glob("*.txt"))) == 20
    check = subprocess.run(
        [sys.executable, str(root / "scripts/validate_collector_execution.py"),
         "--root", str(root), "--input", output.relative_to(root).as_posix(), "--json"],
        text=True, capture_output=True, check=False,
    )
    assert check.returncode == 0, check.stdout + check.stderr
    assert json.loads(check.stdout)["status"] == "valid-complete"


def test_noncanonical_fixture_path_is_refused(tmp_path):
    root = clean_root(tmp_path)
    result = run(root, "--fixture-set", "tests/fixtures/other.json")
    assert result.returncode == 1
    assert "canonical path" in result.stderr
    assert not (root / "research/acquisition/source-captures/clean-room-1").exists()


def test_tampered_marker_is_refused_before_output(tmp_path):
    root = clean_root(tmp_path)
    path = root / "research/acquisition/synthetic-mini-pilot/fixture-set.json"
    fixture = json.loads(path.read_text())
    fixture["synthetic_marker"] = "NOT_SYNTHETIC"
    path.write_text(json.dumps(fixture), encoding="utf-8")
    result = run(root)
    assert result.returncode == 1
    assert "fixture schema" in result.stderr or "marker" in result.stderr
    assert not (root / "research/acquisition/source-captures/clean-room-1").exists()


def test_tampered_fixture_hash_is_refused_before_output(tmp_path):
    root = clean_root(tmp_path)
    path = root / "research/acquisition/synthetic-mini-pilot/fixture-set.json"
    fixture = json.loads(path.read_text())
    fixture["fixture_set_hash"] = "0" * 64
    path.write_text(json.dumps(fixture), encoding="utf-8")
    result = run(root)
    assert result.returncode == 1
    assert "digest mismatch" in result.stderr
    assert not (root / "research/acquisition/source-captures/clean-room-1").exists()


def test_rehashed_modified_fixture_is_still_refused(tmp_path):
    root = clean_root(tmp_path)
    path = root / "research/acquisition/synthetic-mini-pilot/fixture-set.json"
    fixture = json.loads(path.read_text())
    fixture["sources"][0]["body_text"] += " fabricated"
    unsigned = dict(fixture); unsigned.pop("fixture_set_hash")
    fixture["fixture_set_hash"] = hashlib.sha256(json.dumps(
        unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    path.write_text(json.dumps(fixture), encoding="utf-8")
    result = run(root)
    assert result.returncode == 1
    assert "digest mismatch" in result.stderr


def test_generated_execution_cannot_swap_runner_binding(tmp_path):
    root = clean_root(tmp_path)
    assert run(root).returncode == 0
    output = root / "research/acquisition/synthetic-mini-pilot/runs/clean-room-1.json"
    execution = json.loads(output.read_text())
    execution["collector"]["implementation"]["path"] = "scripts/compare_research_runs.py"
    execution["collector"]["implementation"]["byte_sha256"] = hashlib.sha256(
        (root / "scripts/compare_research_runs.py").read_bytes()).hexdigest()
    output.write_text(json.dumps(execution), encoding="utf-8")
    check = subprocess.run(
        [sys.executable, str(root / "scripts/validate_collector_execution.py"),
         "--root", str(root), "--input", output.relative_to(root).as_posix()],
        text=True, capture_output=True, check=False,
    )
    assert check.returncode == 1
    assert "canonical fixture runner" in check.stdout + check.stderr


def test_output_is_immutable_and_second_run_refuses_overwrite(tmp_path):
    root = clean_root(tmp_path)
    assert run(root).returncode == 0
    second = run(root)
    assert second.returncode == 1
    assert "already exists" in second.stderr
