#!/usr/bin/env python3
"""Tests for the deterministic planning validator and catalog.

Positive cases run against a faithful working-tree copy of the authorized
repository (no real data, no secrets). Negative cases mutate a copy of the
valid catalog and re-run the validator by subprocess, asserting exact exit
codes and that the targeted check is reported. The missing-jsonschema case is
exercised in-process by blocking the import.
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
VALIDATOR = REPO / "scripts" / "validate_planning.py"
GENERATOR = REPO / "scripts" / "generate_planning_asset.py"
VALID_CATALOG = REPO / "planning" / "catalog.json"
VALID_SCHEMA = REPO / "planning" / "catalog.schema.json"
FIX = REPO / "tests" / "fixtures" / "planning"

# Directories / files never copied into the test root (secrets, runtime data,
# large ignored artifacts, VCS).
IGNORE_DIRS = {
    ".git", "venv", ".venv", "node_modules", "__pycache__", ".pytest_cache",
    ".playwright-mcp", "archive", "build", "dist", "output", "data",
    "employees", "a1", "scans", "ocr", "evidence", ".history-remediation",
    "public-site", "templates",
}
IGNORE_FILES = {".env", "práce-v-německu.zip", "pytest.ini"}

# Import the validator module for in-process unit checks.
spec = importlib.util.spec_from_file_location("validate_planning", VALIDATOR)
vp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vp)


def load_valid():
    return json.loads(VALID_CATALOG.read_text(encoding="utf-8"))


def copy_repo(root: Path):
    root.mkdir(parents=True, exist_ok=True)
    for path in REPO.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(REPO)
        if any(part in IGNORE_DIRS for part in rel.parts):
            continue
        if rel.name in IGNORE_FILES:
            continue
        dest = root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dest)
    # Planning artifacts under test (overwrite any stale copies).
    (root / "planning").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(VALID_CATALOG, root / "planning" / "catalog.json")
    shutil.copyfile(VALID_SCHEMA, root / "planning" / "catalog.schema.json")


def git_init_commit(root: Path):
    subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    subprocess.run(["git", "-C", str(root), "commit", "-q", "-m", "test base"],
                   check=True, env=env)


@pytest.fixture
def root(tmp_path):
    r = tmp_path / "repo"
    copy_repo(r)
    git_init_commit(r)
    return r


def run(root, catalog="planning/catalog.json", schema="planning/catalog.schema.json", json_out=False):
    args = [sys.executable, str(VALIDATOR), "--root", str(root),
            "--catalog", catalog, "--schema", schema]
    if json_out:
        args.append("--json")
    return subprocess.run(args, capture_output=True, text=True)


def mutate(root, fn):
    catalog_path = root / "planning" / "catalog.json"
    data = json.loads(catalog_path.read_text(encoding="utf-8"))
    fn(data)
    catalog_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return data


def failures(json_text):
    payload = json.loads(json_text)
    return {c["name"]: c["detail"] for c in payload["checks"] if not c["passed"]}


# --------------------------------------------------------------------------
# Positive
# --------------------------------------------------------------------------
def test_valid_full_catalog_passes(root):
    p = run(root)
    assert p.returncode == 0, p.stdout + p.stderr


def test_valid_full_catalog_json(root):
    p = run(root, json_out=True)
    assert p.returncode == 0
    payload = json.loads(p.stdout)
    # The validator is the authoritative source of the live check count; do not
    # hard-code a brittle number here (Gate 0). Assert all checks pass and that
    # the named checks we expect are present.
    assert payload["summary"]["passed"] == payload["summary"]["checks"]
    assert payload["summary"]["failed"] == 0
    assert payload["next_actions"] == []
    names = {c["name"] for c in payload["checks"]}
    for expected in (
        "schema validity",
        "exact required ID coverage",
        "accepted decision_state approver/date/evidence",
        "active plans claimed in INDEX",
        "specialist-gate dependency targets",
    ):
        assert expected in names, "missing expected check: %s" % expected
    assert payload["summary"]["checks"] >= 19


def test_exact_required_ids_coverage():
    ids = {i["id"] for i in load_valid()["items"]}
    assert ids == set(vp.REQUIRED_IDS)
    assert len(vp.REQUIRED_IDS) == 48  # AD/AE plans + DEC-015/DEC-016


def test_each_required_id_present_individually():
    ids = {i["id"] for i in load_valid()["items"]}
    for rid in vp.REQUIRED_IDS:
        assert rid in ids, "missing required id %s" % rid


# --------------------------------------------------------------------------
# Schema / catalog load contract
# --------------------------------------------------------------------------
def test_invalid_schema_exit_1(root):
    (root / "planning" / "catalog.schema.json").write_text(
        json.dumps({"type": "object", "properties": {"items": {"type": "nope"}}}))
    p = run(root)
    assert p.returncode == 1


def test_broken_json_catalog_exit_1(root):
    (root / "planning" / "catalog.json").write_text("{not json")
    p = run(root)
    assert p.returncode == 1


def test_missing_catalog_exit_2(root):
    p = run(root, catalog="planning/does-not-exist.json")
    assert p.returncode == 2


def test_missing_jsonschema_exit_2(root):
    saved = sys.modules.get("jsonschema")
    sys.modules["jsonschema"] = None
    try:
        code = vp.main(["--root", str(root)])
    finally:
        if saved is None:
            sys.modules.pop("jsonschema", None)
        else:
            sys.modules["jsonschema"] = saved
    assert code == 2


# --------------------------------------------------------------------------
# Targeted negative cases (each asserts exit 1 and the named check)
# --------------------------------------------------------------------------
def test_missing_required_id(root):
    mutate(root, lambda d: d["items"].__delitem__(0))
    p = run(root, json_out=True)
    assert p.returncode == 1
    assert "exact required ID coverage" in failures(p.stdout)


def test_duplicate_id(root):
    def fn(d):
        first = dict(d["items"][0])
        d["items"].append(first)
    mutate(root, fn)
    p = run(root, json_out=True)
    assert p.returncode == 1
    assert "duplicate IDs" in failures(p.stdout)


def test_invalid_status_vocabulary(root):
    mutate(root, lambda d: d["items"].__setitem__(0, {**d["items"][0], "status": "bogus"}))
    p = run(root, json_out=True)
    assert p.returncode == 1
    assert "controlled vocabularies" in failures(p.stdout)


def test_invalid_dependency_gate(root):
    def fn(d):
        d["items"][0]["dependencies"] = [{"id": "M1A", "gate": "not-a-gate"}]
    mutate(root, fn)
    p = run(root, json_out=True)
    assert p.returncode == 1
    assert "controlled vocabularies" in failures(p.stdout)


def test_self_dependency(root):
    def fn(d):
        iid = d["items"][0]["id"]
        d["items"][0]["dependencies"] = [{"id": iid, "gate": "may-begin"}]
    mutate(root, fn)
    p = run(root, json_out=True)
    assert p.returncode == 1
    assert "self-dependencies" in failures(p.stdout)


def test_prohibited_cycle(root):
    def fn(d):
        by = {i["id"]: i for i in d["items"]}
        by["M1A"]["dependencies"] = [{"id": "M2", "gate": "may-be-accepted"}]
        by["M2"]["dependencies"] = [{"id": "M1A", "gate": "may-be-accepted"}]
    mutate(root, fn)
    p = run(root, json_out=True)
    assert p.returncode == 1
    assert "gate-aware cycle rules" in failures(p.stdout)


def test_plan_header_index_mismatch(root):
    def fn(d):
        for it in d["items"]:
            if it["id"] == "E":
                it["status"] = "blocked"
    mutate(root, fn)
    p = run(root, json_out=True)
    assert p.returncode == 1
    assert "plan header/index/catalog coherence" in failures(p.stdout)


def test_decision_register_mismatch(root):
    def fn(d):
        for it in d["items"]:
            if it["id"] == "DEC-001":
                it["decision_state"] = "rejected"
    mutate(root, fn)
    p = run(root, json_out=True)
    assert p.returncode == 1
    assert "decision register/catalog coherence" in failures(p.stdout)


def test_accepted_decision_missing_approver(root):
    def fn(d):
        for it in d["items"]:
            if it["id"] == "DEC-001":
                it["approver"] = None
                it["decision_date"] = None
                it["decision_evidence"] = None
    mutate(root, fn)
    p = run(root, json_out=True)
    assert p.returncode == 1
    assert "accepted-decision approver/date/evidence" in failures(p.stdout)


def test_broken_source_link(root):
    def fn(d):
        d["items"][0]["source_links"] = ["docs/does-not-exist-xyz.md"]
    mutate(root, fn)
    p = run(root, json_out=True)
    assert p.returncode == 1
    assert "actual source-link existence" in failures(p.stdout)


def test_broken_markdown_link(root):
    fixture = FIX / "broken_markdown.md"
    dest = root / "docs" / "fixtures_broken.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(fixture, dest)

    def fn(d):
        d["items"][0]["source_links"] = ["docs/fixtures_broken.md"]
    mutate(root, fn)
    p = run(root, json_out=True)
    assert p.returncode == 1
    assert "Markdown relative-link validation" in failures(p.stdout)


def test_historical_executable(root):
    def fn(d):
        for it in d["items"]:
            if it["id"] == "D":
                it["executable"] = True
    mutate(root, fn)
    p = run(root, json_out=True)
    assert p.returncode == 1
    assert "historical/superseded policy" in failures(p.stdout)


def test_historical_missing_successor(root):
    def fn(d):
        for it in d["items"]:
            if it["id"] == "D":
                it["successor"] = None
    mutate(root, fn)
    p = run(root, json_out=True)
    assert p.returncode == 1
    assert "historical/superseded policy" in failures(p.stdout)


def test_missing_referenced_file(root):
    def fn(d):
        for it in d["items"]:
            if it["id"] == "M":
                it.setdefault("referenced_files", []).append("scripts/missing_xyz.py")
    mutate(root, fn)
    p = run(root, json_out=True)
    assert p.returncode == 1
    assert "referenced command/file existence" in failures(p.stdout)


def test_malformed_skill_reference(root):
    skill_dir = root / ".agents" / "skills" / "broken-skill"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text("see [missing](missing-ref.md)\n")

    def fn(d):
        d["items"][0]["source_links"] = ["docs/decisions/decision-register.md"]
    mutate(root, fn)
    p = run(root, json_out=True)
    assert p.returncode == 1
    assert "skill metadata and one-level references" in failures(p.stdout)


def test_forbidden_stale_path(root):
    def fn(d):
        d["items"][0]["source_links"] = ["config/a1_provisional.json"]
    mutate(root, fn)
    p = run(root, json_out=True)
    assert p.returncode == 1
    assert "forbidden stale paths and prototype-source links" in failures(p.stdout)


def test_prototype_item_without_authority(root):
    def fn(d):
        d["items"].append({
            "id": "proto-x", "kind": "plan", "title": "Prototype only",
            "owner": "product design", "milestone": "M1A", "status": "planned",
            "decision_state": "prototype-required", "evidence_state": "none",
            "dependencies": [], "risks": [], "quality_gates": ["x"],
            "source_links": ["docs/prototypes/roadmap-portal/index.html"],
            "exit_evidence": "x", "last_reviewed": "2026-08-13",
            "executable": False, "successor": "M",
        })
    mutate(root, fn)
    p = run(root, json_out=True)
    assert p.returncode == 1
    assert "forbidden stale paths and prototype-source links" in failures(p.stdout)


def test_unsafe_staged_path(root):
    staged = root / "credentials.txt"
    staged.write_text("do not print me\n")
    subprocess.run(["git", "-C", str(root), "add", "credentials.txt"], check=True)
    p = run(root, json_out=True)
    assert p.returncode == 1
    assert "staged forbidden-path and PII/secret indicators" in failures(p.stdout)
    # Never leak the staged path content.
    assert "credentials.txt" not in (p.stdout + p.stderr)


# --------------------------------------------------------------------------
# Cycle logic unit checks
# --------------------------------------------------------------------------
def test_allowed_evidence_only_cycle():
    catalog = {"items": [
        {"id": "A", "dependencies": [{"id": "B", "gate": "evidence-only"}]},
        {"id": "B", "dependencies": [{"id": "A", "gate": "evidence-only"}]},
    ]}
    ok, _ = vp.check_gate_aware_cycles(catalog)
    assert ok is True


def test_blocking_cycle_detected():
    catalog = {"items": [
        {"id": "A", "dependencies": [{"id": "B", "gate": "may-be-accepted"}]},
        {"id": "B", "dependencies": [{"id": "A", "gate": "may-be-accepted"}]},
    ]}
    ok, _ = vp.check_gate_aware_cycles(catalog)
    assert ok is False


# --------------------------------------------------------------------------
# Determinism and next_actions
# --------------------------------------------------------------------------
def test_json_deterministic(root):
    a = run(root, json_out=True).stdout
    b = run(root, json_out=True).stdout
    assert a == b


def test_next_actions_present_on_failure(root):
    def fn(d):
        d["items"][0]["source_links"] = ["docs/missing-xyz.md"]
    mutate(root, fn)
    p = run(root, json_out=True)
    payload = json.loads(p.stdout)
    assert payload["next_actions"]
    for na in payload["next_actions"]:
        assert set(na.keys()) == {"when", "command", "purpose", "severity"}


def test_next_actions_deterministic_on_failure(root):
    def fn(d):
        d["items"][0]["source_links"] = ["docs/missing-xyz.md"]
    mutate(root, fn)
    a = json.loads(run(root, json_out=True).stdout)["next_actions"]
    b = json.loads(run(root, json_out=True).stdout)["next_actions"]
    assert a == b


# --------------------------------------------------------------------------
# Cockpit asset
# --------------------------------------------------------------------------
def test_asset_generates_and_is_deterministic(root):
    out = root / "docs" / "prototypes" / "roadmap-portal" / "planning-data.js"
    subprocess.run([sys.executable, str(GENERATOR), "--root", str(root)], cwd=str(root), check=True,
                   capture_output=True, text=True)
    assert out.is_file()
    first = out.read_text(encoding="utf-8")
    subprocess.run([sys.executable, str(GENERATOR), "--root", str(root)], cwd=str(root), check=True,
                   capture_output=True, text=True)
    second = out.read_text(encoding="utf-8")
    assert first == second
    assert first.startswith("window.PLANNING_CATALOG = ")
    assert "DEC-014" in first
    assert "critical-path" in first


def test_asset_test_entrypoint():
    proc = subprocess.run([sys.executable, str(GENERATOR)], capture_output=True, text=True)
    assert proc.returncode == 0
    asset = REPO / "docs" / "prototypes" / "roadmap-portal" / "planning-data.js"
    assert asset.is_file()


def test_asset_check_is_read_only_and_detects_staleness(root):
    out = root / "docs" / "prototypes" / "roadmap-portal" / "planning-data.js"
    subprocess.run([sys.executable, str(GENERATOR), "--root", str(root)], cwd=str(root), check=True,
                   capture_output=True, text=True)
    before = out.stat().st_mtime_ns
    current = subprocess.run(
        [sys.executable, str(GENERATOR), "--root", str(root), "--check"], cwd=str(root),
        capture_output=True, text=True,
    )
    assert current.returncode == 0
    assert out.stat().st_mtime_ns == before
    out.write_text(out.read_text(encoding="utf-8") + "// stale\n", encoding="utf-8")
    stale = subprocess.run(
        [sys.executable, str(GENERATOR), "--root", str(root), "--check"], cwd=str(root),
        capture_output=True, text=True,
    )
    assert stale.returncode == 1
    assert "stale" in stale.stderr


# --------------------------------------------------------------------------
# PII / secret scan over changed textual paths (no real names)
# --------------------------------------------------------------------------
def test_no_real_names_in_changed_paths():
    changed = [
        VALID_CATALOG, VALID_SCHEMA, VALIDATOR, GENERATOR,
        REPO / "docs" / "operations" / "agent-tooling-ledger.md",
        REPO / "docs" / "prototypes" / "roadmap-portal" / "index.html",
        REPO / "docs" / "prototypes" / "roadmap-portal" / "app.js",
    ]
    forbidden = ["Kašpar", "Kotľár"]
    for path in changed:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for token in forbidden:
            assert token not in text, "%s contains real name %s" % (path, token)
