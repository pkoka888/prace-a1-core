from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = "scripts/evaluate_research_field_fixtures.py"
FIXTURE = "research/query-packs/field-decision-fixtures-1.0.json"
SCHEMA = "research/query-packs/field-decision-fixtures-1.0.schema.json"
SUPPORT = (
    "research/query-packs/plan-ac-core-1.1.json",
    "research/query-packs/atomic-results-1.1.schema.json",
    "scripts/check_evidence_url.py",
)


def project(tmp_path: Path) -> Path:
    for relative in (SCRIPT, FIXTURE, SCHEMA, *SUPPORT):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    return tmp_path


def run(root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(root / SCRIPT), "--root", str(root),
         "--output", "research/processed/field-replay.json", *extra],
        text=True, capture_output=True, check=False,
    )


def mutate(root: Path, change) -> None:
    path = root / FIXTURE
    value = json.loads(path.read_text(encoding="utf-8"))
    change(value)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_replay_is_deterministic_and_check_is_read_only(tmp_path: Path) -> None:
    root = project(tmp_path)
    generated = run(root)
    assert generated.returncode == 0, generated.stderr
    output = root / "research/processed/field-replay.json"
    before = hashlib.sha256(output.read_bytes()).hexdigest()
    checked = run(root, "--check", "--json")
    assert checked.returncode == 0, checked.stderr
    assert json.loads(checked.stdout)["cases"] == 8
    assert hashlib.sha256(output.read_bytes()).hexdigest() == before
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["authority"] == "synthetic-replay-only-not-market-evidence"
    assert report["counts"] == {
        "cases": 8, "supports": 4, "does_not_establish": 2, "conflicts": 2
    }


def test_check_rejects_stale_output(tmp_path: Path) -> None:
    root = project(tmp_path)
    assert run(root).returncode == 0
    output = root / "research/processed/field-replay.json"
    output.write_text("{}\n", encoding="utf-8")
    result = run(root, "--check")
    assert result.returncode == 1
    assert "byte-exact" in result.stderr


def test_missing_output_is_unproven(tmp_path: Path) -> None:
    result = run(project(tmp_path), "--check", "--json")
    assert result.returncode == 2
    assert json.loads(result.stderr)["result"] == "unproven"


def test_generic_title_is_rejected(tmp_path: Path) -> None:
    root = project(tmp_path)
    mutate(root, lambda doc: doc["cases"][0]["evidence"][0].__setitem__("page_title", "Homepage"))
    result = run(root)
    assert result.returncode == 1
    assert "generic page title" in result.stderr


def test_wrong_entity_is_rejected(tmp_path: Path) -> None:
    root = project(tmp_path)
    mutate(root, lambda doc: doc["cases"][0]["evidence"][0].__setitem__("entity_id", "oss-paperless-ngx"))
    result = run(root)
    assert result.returncode == 1
    assert "ownership or field mismatch" in result.stderr


def test_wrong_field_is_rejected(tmp_path: Path) -> None:
    root = project(tmp_path)
    mutate(root, lambda doc: doc["cases"][0]["evidence"][0]["assertions"][0].__setitem__("field_id", "local_execution"))
    result = run(root)
    assert result.returncode == 1
    assert "assertion field mismatch" in result.stderr


def test_wrong_official_source_is_rejected(tmp_path: Path) -> None:
    root = project(tmp_path)
    mutate(root, lambda doc: doc["cases"][4]["evidence"][0].__setitem__("url", "https://example.org/not-official"))
    result = run(root)
    assert result.returncode == 1
    assert "outside entity roots" in result.stderr


def test_official_source_cannot_be_laundered_as_independent(tmp_path: Path) -> None:
    root = project(tmp_path)
    mutate(root, lambda doc: doc["cases"][0]["evidence"][0].__setitem__("evidence_class", "independent_secondary"))
    result = run(root)
    assert result.returncode == 1
    assert "laundered as independent" in result.stderr


def test_malformed_pricing_is_rejected(tmp_path: Path) -> None:
    root = project(tmp_path)
    mutate(root, lambda doc: doc["cases"][6]["candidate_value"]["tiers"][0].__setitem__("amount", "300"))
    result = run(root)
    assert result.returncode == 1
    assert "malformed v1.1 pricing" in result.stderr


def test_expected_decision_cannot_override_replay(tmp_path: Path) -> None:
    root = project(tmp_path)
    mutate(root, lambda doc: doc["cases"][0].__setitem__("expected", "does_not_establish"))
    result = run(root)
    assert result.returncode == 1
    assert "replay produced supports" in result.stderr


def test_path_escape_is_rejected(tmp_path: Path) -> None:
    root = project(tmp_path)
    result = subprocess.run(
        [sys.executable, str(root / SCRIPT), "--root", str(root),
         "--fixture", "../outside.json", "--output", "research/processed/out.json"],
        text=True, capture_output=True, check=False,
    )
    assert result.returncode == 1
    assert "escapes --root" in result.stderr


def test_private_ip_url_is_rejected(tmp_path: Path) -> None:
    root = project(tmp_path)
    mutate(root, lambda doc: doc["cases"][7]["evidence"][1].__setitem__("url", "https://127.0.0.1/source"))
    result = run(root)
    assert result.returncode == 1
    assert "unsafe evidence URL" in result.stderr


def test_ninth_case_is_rejected(tmp_path: Path) -> None:
    root = project(tmp_path)
    mutate(root, lambda doc: doc["cases"].append(dict(doc["cases"][0], id="ninth-case")))
    result = run(root)
    assert result.returncode == 1
    assert "too long" in result.stderr or "exactly eight" in result.stderr


def test_boolean_license_is_rejected_by_bound_field_type(tmp_path: Path) -> None:
    root = project(tmp_path)
    mutate(root, lambda doc: doc["cases"][0].__setitem__("candidate_value", True))
    result = run(root)
    assert result.returncode == 1
    assert "non-empty string required" in result.stderr


def test_same_value_contradiction_is_rejected(tmp_path: Path) -> None:
    root = project(tmp_path)
    mutate(root, lambda doc: doc["cases"][0]["evidence"][0]["assertions"][0].__setitem__("effect", "contradicts"))
    result = run(root)
    assert result.returncode == 1
    assert "same-value contradiction" in result.stderr


def test_capture_drift_is_rejected(tmp_path: Path) -> None:
    root = project(tmp_path)
    mutate(root, lambda doc: doc["cases"][0]["evidence"][0].__setitem__("captured_at", "2026-08-15T00:00:00Z"))
    result = run(root)
    assert result.returncode == 1
    assert "outside the bound pack window" in result.stderr


def test_capture_hash_and_locator_are_bound(tmp_path: Path) -> None:
    root = project(tmp_path)
    mutate(root, lambda doc: doc["cases"][0]["evidence"][0].__setitem__("synthetic_capture", "Synthetic capture: changed content invalidates its hash."))
    result = run(root)
    assert result.returncode == 1
    assert "capture hash mismatch" in result.stderr


def test_repository_role_is_limited_to_repository_roots(tmp_path: Path) -> None:
    root = project(tmp_path)
    mutate(root, lambda doc: doc["cases"][4]["evidence"][0].__setitem__("evidence_class", "repository_metadata"))
    result = run(root)
    assert result.returncode == 1
    assert "repository role requires" in result.stderr


def test_missing_schema_is_invalid_configuration(tmp_path: Path) -> None:
    root = project(tmp_path)
    (root / SCHEMA).unlink()
    result = run(root, "--json")
    assert result.returncode == 1
    assert json.loads(result.stderr)["result"] == "fail"
