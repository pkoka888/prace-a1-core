"""
Shared approval register loader and validator.

Used by both the CLI validator (scripts/validate_approvals.py) and Django
(portal.release1a.views). All gate-state decisions flow through this module.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Optional

from jsonschema import Draft7Validator


def _git_environment():
    # Local root-bound inspections must not inherit a hook/caller's repository.
    return {
        key: value for key, value in os.environ.items() if not key.startswith("GIT_")
    }


class ApprovalRegisterError(Exception):
    """Raised when the approval register is invalid."""

    pass


class GateTransitionError(ApprovalRegisterError):
    """Raised when a gate transition is not allowed."""

    pass


def load_register(root: Path) -> dict:
    """Load and parse the approval register. Raises ApprovalRegisterError on IO/JSON errors."""
    path = root / "planning" / "approvals.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (IOError, json.JSONDecodeError) as e:
        raise ApprovalRegisterError(f"cannot load {path}: {e}")


def validate_schema(register: dict) -> list[str]:
    """Return list of schema errors (empty = valid). Does not raise."""
    errors = []
    schema_path = Path(__file__).parent.parent / "planning" / "approvals.schema.json"
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (IOError, json.JSONDecodeError) as e:
        return [f"cannot load schema: {e}"]
    for error in sorted(
        Draft7Validator(schema).iter_errors(register), key=lambda e: list(e.path)
    ):
        errors.append(
            "schema: " + "/".join(map(str, error.path)) + ": " + error.message
        )
    return errors


def validate(
    root: Path,
    require_clean: bool = False,
    expected_commit: Optional[str] = None,
    expected_approvals_hash: Optional[str] = None,
) -> dict:
    """
    Full validation of the approval register.

    Args:
        root: repository root
        require_clean: if True, reject a dirty git tree in the review scope
        expected_commit: if set, reject if HEAD does not match
        expected_approvals_hash: if set, reject if approvals.json SHA-256 does not match

    Returns:
        {"result": "pass"|"fail", "records": N, "errors": [...], "warnings": [...]}
    """
    try:
        register = load_register(root)
    except ApprovalRegisterError as e:
        return {"result": "fail", "records": 0, "errors": [str(e)], "warnings": []}

    return _validate_register(
        root, register, require_clean, expected_commit, expected_approvals_hash
    )


def _validate_register(
    root,
    register,
    require_clean=False,
    expected_commit=None,
    expected_approvals_hash=None,
):
    """Validate the same in-memory snapshot that will be used for a gate decision."""
    errors: list[str] = []
    warnings: list[str] = []
    schema_errors = validate_schema(register)
    errors.extend(schema_errors)
    if schema_errors:
        return {
            "result": "fail",
            "records": (
                len(register["records"])
                if isinstance(register, dict)
                and isinstance(register.get("records"), list)
                else 0
            ),
            "errors": errors,
            "warnings": warnings,
        }

    try:
        catalog = json.loads(
            (root / "planning/catalog.json").read_text(encoding="utf-8")
        )
        catalog_by_id = {item["id"]: item for item in catalog["items"]}
    except (OSError, ValueError, KeyError, TypeError):
        return {
            "result": "fail",
            "records": len(register["records"]),
            "errors": ["cannot load planning catalog"],
            "warnings": [],
        }

    records = register.get("records", [])
    ids = [r.get("id") for r in records]
    known = set(ids)

    # Duplicate ID check
    if len(ids) != len(set(ids)):
        errors.append("duplicate approval record id")

    # Source file existence
    for record in records:
        source = record.get("source", "")
        if source and not (root / source).is_file():
            errors.append(f"{record['id']}: source does not exist: {source}")

    # Cycle detection via DFS
    graph = {r["id"]: [d["id"] for d in r.get("dependencies", [])] for r in records}
    visited = set()
    stack = set()

    def has_cycle(node: str) -> bool:
        visited.add(node)
        stack.add(node)
        for dep in graph.get(node, []):
            if dep not in known:
                continue
            if dep in stack:
                return True
            if dep not in visited and has_cycle(dep):
                return True
        stack.remove(node)
        return False

    for rid in graph:
        if rid not in visited and has_cycle(rid):
            errors.append(f"dependency cycle detected involving {rid}")

    # Per-record validation
    for record in records:
        rid = record["id"]
        choices = record.get("choices", [])
        checks = record.get("checks", [])
        human = record.get("human_decision", "unknown")
        impl_gate = record.get("implementation_gate", "blocked")
        act_gate = record.get("activation_gate", "blocked")
        validation = record.get("validation", "pending")
        approver = record.get("approver")
        approved_at = record.get("approved_at")
        approval_evidence = record.get("approval_evidence")

        # Check statuses
        statuses = {c.get("status") for c in checks}
        derived = (
            "failed"
            if "failed" in statuses
            else (
                "passed"
                if checks and statuses <= {"passed", "not-required"}
                else "pending"
            )
        )
        if validation != derived:
            errors.append(
                f"{rid}: validation is {validation} but checks derive {derived}"
            )

        # Gate transition rules
        if impl_gate == "open":
            if human != "approved":
                errors.append(
                    f"{rid}: implementation_gate is open but human_decision is {human} (must be approved)"
                )
            if derived != "passed":
                errors.append(
                    f"{rid}: implementation_gate is open but checks derive {derived} (must be passed)"
                )
        if act_gate == "open":
            if impl_gate != "open":
                errors.append(
                    f"{rid}: activation_gate is open but implementation_gate is {impl_gate}"
                )
        if impl_gate == "blocked" and not record.get("implementation_gate_reason"):
            errors.append(f"{rid}: implementation_gate is blocked but has no reason")
        if impl_gate == "open" and (human != "approved" or derived != "passed"):
            errors.append(
                f"{rid}: implementation gate cannot open without approval and passed checks"
            )
        if act_gate == "open" and impl_gate != "open":
            errors.append(
                f"{rid}: activation gate cannot open before implementation gate"
            )

        # Human decision rules
        if human == "approved":
            if not approver or not approved_at or not approval_evidence:
                errors.append(f"{rid}: approved record lacks approver/date/evidence")
            if any(c.get("approval") != "approved" for c in choices):
                errors.append(f"{rid}: approved but a choice is not approved")
            # Reject placeholder approver strings after human approval
            if approver and approver.startswith("pending — "):
                errors.append(f"{rid}: approved but approver is a placeholder string")

        # Deviation rules
        for choice in choices:
            if choice.get("selected") != choice.get("recommended") and not choice.get(
                "deviation_reason"
            ):
                errors.append(f"{rid}/{choice.get('id')}: deviation lacks reason")

            catalog_item = catalog_by_id.get(choice.get("id"))
            expected_state = (
                "accepted"
                if choice.get("approval") == "approved"
                else choice.get("approval")
            )
            if not catalog_item:
                errors.append(f"{rid}/{choice.get('id')}: missing catalog decision")
            elif catalog_item.get("decision_state") != expected_state:
                errors.append(
                    f"{rid}/{choice.get('id')}: approval conflicts with catalog state"
                )
            elif (
                choice.get("approval") == "approved"
                and catalog_item.get("decision_date") != approved_at
            ):
                errors.append(
                    f"{rid}/{choice.get('id')}: approval date conflicts with catalog"
                )

        # Dependencies exist (informational — unmet dependencies in initial state are expected)
        for dep in record.get("dependencies", []):
            dep_id = dep.get("id")
            if dep_id not in known:
                errors.append(f"{rid}: missing dependency {dep_id}")

        # Source file existence
        source_path = record.get("source", "")
        if source_path and not (root / source_path).is_file():
            errors.append(f"{rid}: source does not exist: {source_path}")

    # Git tree cleanliness check (optional)
    # When require_clean=True: dirty scope is an ERROR, not a warning.
    REVIEW_SCOPE_PATTERNS = [
        "portal/",
        "src/document_core/",
        "config/",
        "templates/",
        "scripts/test_document_intake.py",
        "scripts/a1_core.py",
        "scripts/a1_private.py",
        "scripts/a1_audit.py",
        "scripts/a1_paths.py",
        "scripts/finalize_a1.py",
        "scripts/generate_provisional_a1.py",
        "scripts/a1_quality_gate.py",
        "scripts/repair_a1_template_checkboxes.py",
        "requirements.txt",
        "requirements-dev.txt",
        "planning/",
        "plans/",
        "docs/prototypes/",
        "scripts/verify_synthetic_review_readiness.sh",
        "scripts/seed_release1a_dev.py",
        "scripts/release_verifier.py",
        "scripts/seed_verification_db.py",
        "scripts/validate_approvals.py",
        "scripts/validate_planning.py",
        "tests/",
        "runtime/portal/verification/",
        "runtime/portal/synthetic-review/",
        "roadmap.md",
    ]
    if require_clean or expected_commit:
        try:
            git_root = subprocess.check_output(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=root,
                text=True,
                stderr=subprocess.DEVNULL,
                env=_git_environment(),
            ).strip()
            if Path(git_root).resolve() != root.resolve():
                errors.append("review root is not the Git repository root")
        except (subprocess.CalledProcessError, OSError):
            errors.append("could not verify Git repository root")
    if require_clean:
        try:
            tracked = subprocess.check_output(
                ["git", "status", "--porcelain", "--"] + REVIEW_SCOPE_PATTERNS,
                text=True,
                stderr=subprocess.DEVNULL,
                cwd=root,
                env=_git_environment(),
            ).strip()
            untracked = subprocess.check_output(
                ["git", "ls-files", "--others", "--exclude-standard", "--"]
                + REVIEW_SCOPE_PATTERNS,
                text=True,
                stderr=subprocess.DEVNULL,
                cwd=root,
                env=_git_environment(),
            ).strip()
            if tracked or untracked:
                errors.append(
                    f"review scope is dirty: tracked={bool(tracked)} untracked={bool(untracked)}"
                )
        except (subprocess.CalledProcessError, OSError):
            errors.append("could not check git status for cleanliness")

    # Optional HEAD commit check — treated as error for runtime gate decisions
    if expected_commit:
        try:
            head = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                text=True,
                stderr=subprocess.DEVNULL,
                cwd=root,
                env=_git_environment(),
            ).strip()
            if head != expected_commit:
                errors.append(
                    f"HEAD {head[:8]} does not match expected commit {expected_commit[:8]}"
                )
        except (subprocess.CalledProcessError, OSError):
            errors.append("could not read HEAD for commit verification")

    # Optional approvals hash check — treated as error for runtime gate decisions
    if expected_approvals_hash:
        register_bytes = json.dumps(
            register, sort_keys=True, ensure_ascii=False
        ).encode()
        actual = hashlib.sha256(register_bytes).hexdigest()
        if actual != expected_approvals_hash:
            errors.append(
                f"approvals hash {actual[:8]} does not match expected {expected_approvals_hash[:8]}"
            )

    return {
        "result": "fail" if errors else "pass",
        "records": len(records),
        "errors": errors,
        "warnings": warnings,
    }


def _derive_validation(record: dict) -> str:
    """Derive validation state from checks."""
    checks = record.get("checks", [])
    if not checks:
        return "pending"
    statuses = {c.get("status") for c in checks}
    if "failed" in statuses:
        return "failed"
    if statuses <= {"passed", "not-required"}:
        return "passed"
    return "pending"


def _dep_state_met(dep: dict, dep_record: dict) -> tuple[bool, str]:
    """
    Check whether a dependency record satisfies its required gate state.

    Returns (met, detail).
    """
    required = dep.get("required_gate", "approved")
    human = dep_record.get("human_decision", "proposed")
    derived = _derive_validation(dep_record)
    impl = dep_record.get("implementation_gate", "blocked")
    act = dep_record.get("activation_gate", "blocked")

    if required == "approved":
        ok = human == "approved"
        return ok, f"requires approved, human_decision={human}"
    if required == "validated":
        ok = derived == "passed"
        return ok, f"requires validated, validation={derived}"
    if required == "implementation-open":
        ok = impl == "open"
        return ok, f"requires implementation_gate=open, currently {impl}"
    if required == "activation-open":
        ok = act == "open"
        return ok, f"requires activation_gate=open, currently {act}"
    return False, f"unknown required_gate: {required}"


def check_gate(
    root: Path,
    record_id: str,
    gate: str = "implementation_gate",
    require_clean: bool = False,
    expected_commit: str | None = None,
    expected_approvals_hash: str | None = None,
) -> tuple[bool, str]:
    """
    Check whether a specific gate is open for a record.

    Runtime-safety: this function calls full validation and enforces all dependency
    states before returning open. A dirty tree, wrong HEAD, or approval hash
    mismatch will cause it to return closed.

    Args:
        root: repository root
        record_id: e.g. "ENG-001"
        gate: "implementation_gate" or "activation_gate"
        require_clean: if True, treat dirty tree as an error
        expected_commit: if set, treat HEAD mismatch as an error
        expected_approvals_hash: if set, treat hash mismatch as an error

    Returns:
        (is_open, reason)
    """
    if gate not in {"implementation_gate", "activation_gate"}:
        return False, "unsupported gate"
    try:
        register = load_register(root)
    except ApprovalRegisterError as e:
        return False, f"cannot load register: {e}"
    validation = _validate_register(
        root,
        register,
        require_clean,
        expected_commit,
        expected_approvals_hash,
    )
    if validation["result"] == "fail":
        errors = "; ".join(validation["errors"][:3])
        return False, f"{record_id}: register validation failed — {errors}"

    record = next(
        (r for r in register.get("records", []) if r.get("id") == record_id), None
    )
    if not record:
        return False, f"{record_id} not found in approvals register"

    record_by_id = {r["id"]: r for r in register["records"]}

    def unmet_dependency(candidate):
        for dep in candidate.get("dependencies", []):
            dep_id = dep["id"]
            dep_record = record_by_id[dep_id]
            met, detail = _dep_state_met(dep, dep_record)
            if not met:
                return (
                    f"{candidate['id']}: dependency {dep_id} not satisfied — {detail}"
                )
            if dep.get("required_gate") in {"implementation-open", "activation-open"}:
                reason = unmet_dependency(dep_record)
                if reason:
                    return reason
        return None

    reason = unmet_dependency(record)
    if reason:
        return False, reason

    gate_value = record.get(gate, "blocked")
    if gate_value == "open":
        return True, f"{record_id} {gate} is open"

    reason = record.get(f"{gate}_reason") or gate_value
    return False, f"{record_id} {gate} is {reason}"


def approvals_hash(root: Path) -> str:
    """SHA-256 of the approvals register JSON (sorted keys)."""
    register = load_register(root)
    return hashlib.sha256(
        json.dumps(register, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
