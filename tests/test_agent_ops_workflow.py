"""Optional LangGraph experiment: run with the isolated pinned interpreter.

No skipping when dependencies are absent: this suite requires the documented
research environment. Use a private in-repository --basetemp (see runbook).
"""
from __future__ import annotations

import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.research_agent_ops_workflow import (
    Harness, ROOT, SYNTHETIC_REVISIONS, SYNTHETIC_TARGETS, SyntheticAuthority,
    load_config, private_directory, request, run_demo,
)


@pytest.fixture(autouse=True)
def private_umask():
    previous = os.umask(0o077)
    yield
    os.umask(previous)


@pytest.fixture
def harness(tmp_path):
    authority = SyntheticAuthority()
    return Harness(tmp_path, authority)


def test_pinned_experiment_dependencies():
    for name, expected in load_config()["dependencies"].items():
        assert importlib.metadata.version(name) == expected


def test_pause_has_no_effect_then_valid_decision_and_duplicate(harness):
    state = request()
    paused = harness.start(state)
    assert paused["status"] == "waiting_operator"
    assert harness.count_effects() == 0
    ref = harness.authority.issue(paused)
    result = harness.resume(state["run_id"], ref)
    assert result["status"] == "passed"
    assert result["effects"] == dict.fromkeys(SYNTHETIC_TARGETS, "created")
    assert harness.resume(state["run_id"], ref)["reason"] == "already_complete"
    assert harness.count_effects() == 2


@pytest.mark.parametrize(("condition", "reason"), [
    ("rejected", "decision_rejected"),
    ("expired", "decision_expired"),
    ("revoked", "decision_revoked"),
    ("actor", "decision_actor"),
    ("cross_run", "decision_scope"),
    ("stale_decision", "decision_scope"),
    ("changed_revision", "source_drift"),
    ("changed_targets", "target_drift"),
    ("changed_decision_targets", "decision_scope"),
    ("unknown_decision", "decision_missing"),
])
def test_refusal_cannot_reach_effect(harness, condition, reason):
    state = request()
    paused = harness.start(state)
    decision_state = dict(paused)
    options = {}
    if condition == "rejected":
        options["approved"] = False
    elif condition == "expired":
        options["ttl"] = -1
    elif condition == "actor":
        options["actor"] = "synthetic-unprivileged"
    elif condition == "cross_run":
        decision_state["run_id"] = request()["run_id"]
    elif condition == "stale_decision":
        decision_state["revision"] = SYNTHETIC_REVISIONS[1]
    elif condition == "changed_revision":
        harness.revision = SYNTHETIC_REVISIONS[1]
    elif condition == "changed_targets":
        harness.targets = (SYNTHETIC_TARGETS[0],)
    elif condition == "changed_decision_targets":
        decision_state["targets"] = [SYNTHETIC_TARGETS[0]]
        decision_state["checks"] = {SYNTHETIC_TARGETS[0]: paused["checks"][SYNTHETIC_TARGETS[0]]}
    ref = harness.authority.issue(decision_state, **options)
    if condition == "revoked":
        harness.authority.revoked.add(ref)
    elif condition == "unknown_decision":
        ref = "decision-" + "0" * 32
    result = harness.resume(state["run_id"], ref)
    assert result["status"] == "refused"
    assert result["reason"] == reason
    assert harness.count_effects() == 0


@pytest.mark.parametrize("status", ["failed", "blocked", "untested"])
@pytest.mark.parametrize("check", ["source_identity", "task_safety", "target_health"])
def test_each_required_check_must_pass(harness, status, check):
    state = request()
    state["checks"][SYNTHETIC_TARGETS[1]][check] = status
    result = harness.start(state)
    assert result["status"] == "refused"
    assert result["reason"] == "required_check_not_passed"
    assert result["checks"][SYNTHETIC_TARGETS[0]][check] == "passed"
    assert harness.count_effects() == 0


@pytest.mark.parametrize("mutation", ["schema", "missing_check", "target", "claimed_approval", "claimed_effect", "extra_field"])
def test_invalid_input_is_refused_before_checkpoint(harness, mutation):
    state = request()
    if mutation == "schema":
        state["schema_version"] = 2
    elif mutation == "missing_check":
        del state["checks"][SYNTHETIC_TARGETS[0]]["task_safety"]
    elif mutation == "target":
        state["targets"] = ["not-a-synthetic-target"]
    elif mutation == "claimed_approval":
        state["status"] = "approved"
    elif mutation == "claimed_effect":
        state["effects"] = {SYNTHETIC_TARGETS[0]: "created"}
    elif mutation == "extra_field":
        state["secret"] = "SYNTHETIC-SECRET-CANARY"
    with pytest.raises(ValueError):
        harness.start(state)
    assert harness.count_effects() == 0
    assert b"SYNTHETIC-SECRET-CANARY" not in harness.checkpoint.read_bytes()


def test_arbitrary_resume_payload_is_not_checkpointed(harness):
    state = request()
    harness.start(state)
    for payload in (True, {"approved": True}, "SYNTHETIC-SECRET-CANARY"):
        with pytest.raises(ValueError):
            harness.resume(state["run_id"], payload)
    assert harness.count_effects() == 0
    assert b"SYNTHETIC-SECRET-CANARY" not in harness.checkpoint.read_bytes()


@pytest.mark.parametrize("fault", ["before_effect", "after_effect"])
def test_reopen_after_fault_reconciles_durable_effect(harness, fault):
    state = request()
    paused = harness.start(state)
    ref = harness.authority.issue(paused)
    harness.fault = fault
    with pytest.raises(RuntimeError, match="synthetic_crash_" + fault):
        harness.resume(state["run_id"], ref)
    assert harness.count_effects() == (0 if fault == "before_effect" else 2)
    reopened = Harness(harness.directory, harness.authority)
    result = reopened.resume(state["run_id"])
    assert result["status"] == "passed"
    assert set(result["effects"].values()) == ({"created"} if fault == "before_effect" else {"reconciled"})
    assert reopened.count_effects() == 2


def test_revocation_checked_again_during_recovery(harness):
    state = request()
    paused = harness.start(state)
    ref = harness.authority.issue(paused)
    harness.fault = "before_effect"
    with pytest.raises(RuntimeError):
        harness.resume(state["run_id"], ref)
    harness.authority.revoked.add(ref)
    reopened = Harness(harness.directory, harness.authority)
    result = reopened.resume(state["run_id"])
    assert result["reason"] == "decision_revoked"
    assert reopened.count_effects() == 0


def test_effect_owned_by_another_run_is_not_adopted(harness):
    first = request()
    paused = harness.start(first)
    harness.resume(first["run_id"], harness.authority.issue(paused))
    second = request()
    paused = harness.start(second)
    result = harness.resume(second["run_id"], harness.authority.issue(paused))
    assert result["reason"] == "effect_scope"
    assert harness.count_effects() == 2


def test_checkpoint_resumes_in_fresh_interpreter(harness):
    state = request()
    harness.start(state)
    program = """
import json, sys
from pathlib import Path
from scripts.research_agent_ops_workflow import Harness, SyntheticAuthority
authority = SyntheticAuthority()
harness = Harness(Path(sys.argv[1]), authority)
paused = harness.snapshot(sys.argv[2])
assert paused['status'] == 'waiting_operator'
result = harness.resume(sys.argv[2], authority.issue(paused))
print(json.dumps({'status': result['status'], 'count': harness.count_effects()}))
"""
    result = subprocess.run(
        [sys.executable, "-c", program, str(harness.directory), state["run_id"]],
        cwd=ROOT, env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "PYTHONNOUSERSITE": "1",
                       "LANGSMITH_TRACING": "false", "LANGCHAIN_TRACING_V2": "false"},
        text=True, capture_output=True, timeout=30, check=True,
    )
    assert json.loads(result.stdout) == {"status": "passed", "count": 2}
    assert harness.snapshot(state["run_id"])["status"] == "passed"


def test_permissions_and_nonprivate_target_refusal(harness, tmp_path):
    assert harness.directory.stat().st_mode & 0o777 == 0o700
    assert harness.checkpoint.stat().st_mode & 0o777 == 0o600
    assert harness.ledger.stat().st_mode & 0o777 == 0o600
    with pytest.raises(ValueError):
        private_directory(Path("/tmp/agent-ops-demo-disallowed"))
    link = tmp_path / "linked"
    link.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError):
        private_directory(link)


def test_parent_traversal_and_shared_base_create_nothing(tmp_path):
    base = ROOT / "runtime/portal/temporary"
    escaped_name = "synthetic-must-not-exist-" + request()["run_id"]
    escaped = base.parent / escaped_name
    assert not escaped.exists()
    for path in (base, base / ".." / escaped_name, tmp_path / ".." / escaped_name):
        with pytest.raises(ValueError):
            private_directory(path, create=True)
    assert not escaped.exists()
    assert not (tmp_path.parent / escaped_name).exists()


def test_existing_hardlinked_ledger_is_refused_without_overwrite(tmp_path):
    sentinel = tmp_path / "synthetic-sentinel.txt"
    sentinel.write_text("synthetic unchanged sentinel")
    os.link(sentinel, tmp_path / "synthetic-effects.sqlite3")
    with pytest.raises(ValueError, match="unsafe existing demo file"):
        Harness(tmp_path, SyntheticAuthority())
    assert sentinel.read_text() == "synthetic unchanged sentinel"


def test_demo_receipt_and_reuse_refusal(tmp_path):
    directory = tmp_path / "demo"
    result = run_demo(directory)
    assert result["initial_status"] == "waiting_operator"
    assert result["final_status"] == "passed"
    assert result["effects"] == dict.fromkeys(SYNTHETIC_TARGETS, "reconciled")
    assert result["effect_count"] == 2
    assert result["host_actions"] == result["provider_calls"] == 0
    assert json.loads((directory / "receipt.json").read_text()) == result
    with pytest.raises(FileExistsError):
        run_demo(directory)
