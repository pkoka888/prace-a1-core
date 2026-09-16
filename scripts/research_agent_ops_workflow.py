#!/usr/bin/env python3
"""Local LangGraph research demo. Synthetic decisions/effects; no live executor.

Install optional pinned dependencies in an isolated environment, then use --demo.
The graph contains no shell, network, model, SSH, Ansible, or host service adapter.
SyntheticAuthority is a test fixture, NEVER an authentication implementation.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import time
from typing import TypedDict
import uuid


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config/agent_ops_workflow.v1.json"
SYNTHETIC_TARGETS = ("synthetic-app-a", "synthetic-app-b")
SYNTHETIC_REVISIONS = ("synthetic-revision-a", "synthetic-revision-b")
CHECKS = ("source_identity", "task_safety", "target_health")
CHECK_STATUSES = ("passed", "failed", "blocked", "untested")
WORKFLOW_ID = "agent-ops-synthetic-v1"
ACTION_ID = "record-synthetic-effect"


class State(TypedDict):
    schema_version: int
    workflow_id: str
    run_id: str
    revision: str
    targets: list[str]
    checks: dict[str, dict[str, str]]
    status: str
    reason: str
    decision_ref: str
    effects: dict[str, str]


def load_config() -> dict:
    config = json.loads(CONFIG_PATH.read_text())
    expected = {
        "schema_version": 1, "workflow_id": WORKFLOW_ID, "mode": "synthetic-only",
        "targets": list(SYNTHETIC_TARGETS), "revisions": list(SYNTHETIC_REVISIONS),
        "action_id": ACTION_ID, "required_checks": list(CHECKS),
        "check_statuses": list(CHECK_STATUSES), "max_transitions": 30,
        "approval_ttl_seconds": 60,
    }
    if any(config.get(key) != value for key, value in expected.items()):
        raise ValueError("synthetic policy contract mismatch")
    if set(config) != set(expected) | {"dependencies", "dependency_sources"}:
        raise ValueError("unknown synthetic policy fields")
    if config["dependencies"] != {
        "langgraph": "1.2.11", "langgraph-checkpoint-sqlite": "3.1.1", "pytest": "9.1.1",
    }:
        raise ValueError("unreviewed experiment dependencies")
    if config["dependency_sources"] != {
        name: f"https://pypi.org/pypi/{name}/{version}/json"
        for name, version in config["dependencies"].items()
    }:
        raise ValueError("invalid dependency source references")
    return config


def validate_request(state: dict) -> None:
    """Reject unbounded input before checkpointing; values are synthetic enums."""
    if set(state) != set(State.__annotations__):
        raise ValueError("invalid state fields")
    if state["schema_version"] != 1 or state["workflow_id"] != WORKFLOW_ID:
        raise ValueError("unsupported workflow version")
    if not isinstance(state["run_id"], str) or not re.fullmatch(r"demo-[0-9a-f]{32}", state["run_id"]):
        raise ValueError("invalid synthetic run id")
    if state["revision"] not in SYNTHETIC_REVISIONS:
        raise ValueError("non-synthetic revision")
    targets = state["targets"]
    if not isinstance(targets, list) or not targets or len(set(targets)) != len(targets):
        raise ValueError("invalid synthetic targets")
    if any(target not in SYNTHETIC_TARGETS for target in targets):
        raise ValueError("non-synthetic target")
    if not isinstance(state["checks"], dict) or set(state["checks"]) != set(targets):
        raise ValueError("target coverage mismatch")
    for target in targets:
        row = state["checks"][target]
        if not isinstance(row, dict) or set(row) != set(CHECKS):
            raise ValueError("required check coverage mismatch")
        if any(value not in CHECK_STATUSES for value in row.values()):
            raise ValueError("unknown check status")
    if state["status"] not in {"new", "ready", "waiting_operator", "approved", "refused", "passed"}:
        raise ValueError("invalid status")
    if state["reason"] not in {
        "", "required_check_not_passed", "decision_missing", "decision_rejected",
        "decision_expired", "decision_revoked", "decision_actor", "decision_scope",
        "source_drift", "target_drift", "effect_scope", "already_complete",
    }:
        raise ValueError("invalid reason")
    ref = state["decision_ref"]
    if ref and (not isinstance(ref, str) or not re.fullmatch(r"decision-[0-9a-f]{32}", ref)):
        raise ValueError("invalid decision reference")
    if not isinstance(state["effects"], dict) or not set(state["effects"]).issubset(targets):
        raise ValueError("invalid effect coverage")
    if any(value not in {"created", "reconciled"} for value in state["effects"].values()):
        raise ValueError("invalid effect result")


def request(*, revision=SYNTHETIC_REVISIONS[0], targets=SYNTHETIC_TARGETS) -> State:
    value: State = {
        "schema_version": 1, "workflow_id": WORKFLOW_ID,
        "run_id": "demo-" + uuid.uuid4().hex, "revision": revision,
        "targets": list(targets),
        "checks": {target: {check: "passed" for check in CHECKS} for target in targets},
        "status": "new", "reason": "", "decision_ref": "", "effects": {},
    }
    validate_request(value)
    return value


@dataclass(frozen=True)
class SyntheticDecision:
    run_id: str
    revision: str
    targets: tuple[str, ...]
    actor: str
    approved: bool
    expires_at: float


class SyntheticAuthority:
    """Process-local fixture. IDs and actor strings are NOT real authorization."""

    def __init__(self, *, clock=time.time):
        self.clock = clock
        self.decisions: dict[str, SyntheticDecision] = {}
        self.revoked: set[str] = set()

    def issue(self, state: State, *, approved=True, actor="synthetic-operator", ttl=60) -> str:
        validate_request(state)
        ref = "decision-" + uuid.uuid4().hex
        self.decisions[ref] = SyntheticDecision(
            state["run_id"], state["revision"], tuple(state["targets"]), actor,
            approved, self.clock() + ttl,
        )
        return ref

    def check(self, state: State, revision: str, targets: tuple[str, ...]) -> str:
        ref = state["decision_ref"]
        decision = self.decisions.get(ref)
        if decision is None:
            return "decision_missing"
        if ref in self.revoked:
            return "decision_revoked"
        if not decision.approved:
            return "decision_rejected"
        if decision.expires_at <= self.clock():
            return "decision_expired"
        if decision.actor != "synthetic-operator":
            return "decision_actor"
        if (decision.run_id, decision.revision, decision.targets) != (
            state["run_id"], state["revision"], tuple(state["targets"]),
        ):
            return "decision_scope"
        if state["revision"] != revision:
            return "source_drift"
        if tuple(state["targets"]) != targets:
            return "target_drift"
        return ""


def private_directory(path: Path, *, create=False) -> None:
    """The research harness accepts only an owned private repository directory."""
    base = ROOT / "runtime/portal/temporary"
    path = Path(path).absolute()
    if ".." in path.parts or path == base or not path.is_relative_to(base):
        raise ValueError("demo directory must remain in repository private runtime")
    for item in (path, *path.parents):
        if item.is_symlink():
            raise ValueError("symlink in demo path")
    if create:
        path.mkdir(mode=0o700, exist_ok=False)
    stat = path.stat()
    if not path.is_dir() or stat.st_uid != os.getuid() or stat.st_mode & 0o077:
        raise ValueError("demo directory must be owned and mode 0700")


def private_file(path: Path) -> None:
    if path.exists():
        stat = path.lstat()
        if (path.is_symlink() or not path.is_file() or stat.st_uid != os.getuid()
                or stat.st_mode & 0o077 or stat.st_nlink != 1):
            raise ValueError("unsafe existing demo file")
    else:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.close(descriptor)


class Harness:
    """All effects are rows in this demo's local SQLite ledger."""

    def __init__(self, directory: Path, authority: SyntheticAuthority, *,
                 revision=SYNTHETIC_REVISIONS[0], targets=SYNTHETIC_TARGETS, fault=""):
        private_directory(directory)
        self.directory, self.authority = directory, authority
        self.revision, self.targets, self.fault = revision, tuple(targets), fault
        self.policy = load_config()
        self.checkpoint = directory / "checkpoints.sqlite3"
        self.ledger = directory / "synthetic-effects.sqlite3"
        private_file(self.checkpoint)
        private_file(self.ledger)
        with sqlite3.connect(self.ledger) as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS effects (
                action TEXT NOT NULL, revision TEXT NOT NULL, target TEXT NOT NULL,
                run_id TEXT NOT NULL, PRIMARY KEY(action, revision, target))""")

    def count_effects(self) -> int:
        with sqlite3.connect(self.ledger) as connection:
            return connection.execute("SELECT COUNT(*) FROM effects").fetchone()[0]

    def _preflight(self, state):
        if any(status != "passed" for row in state["checks"].values() for status in row.values()):
            return {"status": "refused", "reason": "required_check_not_passed"}
        return {"status": "ready"}

    def _approve(self, state):
        from langgraph.types import interrupt
        ref = interrupt({"simulation": True, "run_id": state["run_id"],
                         "revision": state["revision"], "targets": state["targets"],
                         "action_id": ACTION_ID})
        # Never checkpoint arbitrary supplied text or objects.
        if not isinstance(ref, str) or not re.fullmatch(r"decision-[0-9a-f]{32}", ref):
            return {"status": "refused", "reason": "decision_missing"}
        return {"decision_ref": ref}

    def _validate_decision(self, state):
        reason = self.authority.check(state, self.revision, self.targets)
        return {"status": "refused" if reason else "approved", "reason": reason}

    def _effect(self, state):
        # Check again immediately before the effect; graph state cannot approve it.
        verdict = self._validate_decision(state)
        if verdict["status"] != "approved":
            return verdict
        if self.fault == "before_effect":
            self.fault = ""
            raise RuntimeError("synthetic_crash_before_effect")
        effects = {}
        with sqlite3.connect(self.ledger) as connection:
            connection.execute("BEGIN IMMEDIATE")
            for target in state["targets"]:
                key = (ACTION_ID, state["revision"], target)
                existing = connection.execute(
                    "SELECT run_id FROM effects WHERE action=? AND revision=? AND target=?", key,
                ).fetchone()
                if existing and existing[0] != state["run_id"]:
                    connection.rollback()
                    return {"status": "refused", "reason": "effect_scope"}
                if existing:
                    effects[target] = "reconciled"
                else:
                    connection.execute("INSERT INTO effects VALUES (?, ?, ?, ?)", (*key, state["run_id"]))
                    effects[target] = "created"
        if self.fault == "after_effect":
            self.fault = ""
            raise RuntimeError("synthetic_crash_after_effect")
        return {"effects": effects}

    def _verify(self, state):
        with sqlite3.connect(self.ledger) as connection:
            rows = connection.execute("SELECT target FROM effects WHERE run_id=? AND revision=? AND action=?",
                                      (state["run_id"], state["revision"], ACTION_ID)).fetchall()
        if {row[0] for row in rows} != set(state["targets"]):
            return {"status": "refused", "reason": "effect_scope"}
        return {"status": "passed"}

    @contextmanager
    def graph(self):
        # Tracing is explicitly disabled; no provider credentials are required.
        os.environ["LANGSMITH_TRACING"] = "false"
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
        from langgraph.checkpoint.sqlite import SqliteSaver
        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
        from langgraph.graph import END, START, StateGraph
        def checked(function):
            def node(state):
                validate_request(state)
                update = function(state)
                validate_request({**state, **update})
                return update
            return node
        builder = StateGraph(State)
        for name, node in (("preflight", self._preflight), ("approval", self._approve),
                           ("validate_decision", self._validate_decision),
                           ("effect", self._effect), ("verify", self._verify)):
            builder.add_node(name, checked(node))
        builder.add_edge(START, "preflight")
        builder.add_conditional_edges("preflight", lambda s: END if s["status"] == "refused" else "approval")
        builder.add_conditional_edges("approval", lambda s: END if s["status"] == "refused" else "validate_decision")
        builder.add_conditional_edges("validate_decision", lambda s: END if s["status"] == "refused" else "effect")
        builder.add_conditional_edges("effect", lambda s: END if s["status"] == "refused" else "verify")
        builder.add_edge("verify", END)
        connection = sqlite3.connect(self.checkpoint, check_same_thread=False)
        try:
            saver = SqliteSaver(connection, serde=JsonPlusSerializer(pickle_fallback=False))
            yield builder.compile(checkpointer=saver)
        finally:
            connection.close()

    def config(self, run_id):
        if not isinstance(run_id, str) or not re.fullmatch(r"demo-[0-9a-f]{32}", run_id):
            raise ValueError("invalid run id")
        return {"configurable": {"thread_id": run_id}, "recursion_limit": self.policy["max_transitions"]}

    def start(self, state: State) -> dict:
        validate_request(state)
        if state["status"] != "new" or state["decision_ref"] or state["effects"]:
            raise ValueError("cannot start with claimed approval or effects")
        with self.graph() as graph:
            config = self.config(state["run_id"])
            if graph.get_state(config).values:
                raise ValueError("run already exists")
            graph.invoke(state, config, durability="sync")
        return self.snapshot(state["run_id"])

    def snapshot(self, run_id: str) -> dict:
        with self.graph() as graph:
            snapshot = graph.get_state(self.config(run_id))
        if not snapshot.values:
            raise ValueError("unknown run")
        state = dict(snapshot.values)
        validate_request(state)
        if snapshot.next == ("approval",):
            state["status"] = "waiting_operator"
        return state

    def resume(self, run_id: str, decision_ref: str | None = None) -> dict:
        from langgraph.types import Command
        if decision_ref is not None and (not isinstance(decision_ref, str) or
                                        not re.fullmatch(r"decision-[0-9a-f]{32}", decision_ref)):
            raise ValueError("invalid decision reference")
        with self.graph() as graph:
            config = self.config(run_id)
            snapshot = graph.get_state(config)
            if not snapshot.values:
                raise ValueError("unknown run")
            validate_request(snapshot.values)
            if not snapshot.next:
                return {**snapshot.values, "reason": "already_complete"}
            if snapshot.next == ("approval",):
                if decision_ref is None:
                    raise ValueError("synthetic decision reference required")
                command = Command(resume=decision_ref)
            else:
                if decision_ref is not None:
                    raise ValueError("unexpected decision on recovery")
                command = None
            graph.invoke(command, config, durability="sync")
        return self.snapshot(run_id)


def run_demo(directory: Path) -> dict:
    """Close/reopen graph and reconcile a simulated crash after the local commit."""
    private_directory(directory, create=True)
    authority = SyntheticAuthority()
    state = request()
    first = Harness(directory, authority)
    paused = first.start(state)
    del first
    restarted = Harness(directory, authority, fault="after_effect")
    ref = authority.issue(paused)
    crash = ""
    try:
        restarted.resume(state["run_id"], ref)
    except RuntimeError as error:
        if str(error) != "synthetic_crash_after_effect":
            raise
        crash = str(error)
    del restarted
    recovered = Harness(directory, authority)
    result = recovered.resume(state["run_id"])
    duplicate = recovered.resume(state["run_id"], ref)
    summary = {
        "schema_version": 1, "simulation": True, "workflow_id": WORKFLOW_ID,
        "run_id": state["run_id"], "initial_status": paused["status"],
        "crash": crash, "final_status": result["status"],
        "effects": result["effects"], "effect_count": recovered.count_effects(),
        "duplicate_resume": duplicate["reason"],
        "checkpoint_reopened": True, "process_restart": False,
        "host_actions": 0, "provider_calls": 0,
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "config_sha256": hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest(),
        "dependencies": {name: importlib.metadata.version(name) for name in load_config()["dependencies"]},
        "receipt": str(directory / "receipt.json"),
    }
    private_file(directory / "receipt.json")
    (directory / "receipt.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--demo", action="store_true", help="run local synthetic demonstration only")
    mode.add_argument("--validate-contract", action="store_true", help="stdlib-only structural check; does not execute LangGraph")
    parser.add_argument("--directory", type=Path, help="new private runtime directory; existing directory is refused")
    args = parser.parse_args()
    if args.validate_contract:
        if args.directory is not None:
            parser.error("--directory only applies to --demo")
        try:
            config = load_config()
        except (ValueError, OSError):
            print(json.dumps({"status": "failed", "kind": "structure"}))
            return 1
        print(json.dumps({"status": "passed", "kind": "structure", "simulation": True,
                          "workflow_id": config["workflow_id"], "runtime_tested": False}))
        return 0
    os.umask(0o077)
    directory = args.directory or ROOT / "runtime/portal/temporary" / (
        "agent-ops-demo-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex
    )
    try:
        print(json.dumps(run_demo(directory), sort_keys=True))
    except (ValueError, FileExistsError, ImportError):
        print(json.dumps({"simulation": True, "status": "blocked", "reason": "invalid_demo_setup"}))
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
