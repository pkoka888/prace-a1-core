"""
Shared approval register loader and validator.

Used by both the CLI validator (scripts/validate_approvals.py) and Django
(portal.release1a.views). All gate-state decisions flow through this module.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Optional

from jsonschema import Draft7Validator


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
    for error in sorted(Draft7Validator(schema).iter_errors(register), key=lambda e: list(e.path)):
        errors.append("schema: " + "/".join(map(str, error.path)) + ": " + error.message)
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
    errors: list[str] = []
    warnings: list[str] = []

    try:
        register = load_register(root)
    except ApprovalRegisterError as e:
        return {"result": "fail", "records": 0, "errors": [str(e)], "warnings": []}

    schema_errors = validate_schema(register)
    errors.extend(schema_errors)
    if schema_errors:
        return {"result": "fail", "records": len(register.get("records", [])), "errors": errors, "warnings": warnings}

    records = register.get("records", [])
    record_by_id = {r["id"]: r for r in records}
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
            "failed" if "failed" in statuses
            else ("passed" if checks and statuses <= {"passed", "not-required"} else "pending")
        )
        if validation != derived:
            errors.append(f"{rid}: validation is {validation} but checks derive {derived}")

        # Gate transition rules
        if impl_gate == "open":
            if human != "approved":
                errors.append(f"{rid}: implementation_gate is open but human_decision is {human} (must be approved)")
            if derived != "passed":
                errors.append(f"{rid}: implementation_gate is open but checks derive {derived} (must be passed)")
        if act_gate == "open":
            if impl_gate != "open":
                errors.append(f"{rid}: activation_gate is open but implementation_gate is {impl_gate}")
        if impl_gate == "blocked" and not record.get("implementation_gate_reason"):
            errors.append(f"{rid}: implementation_gate is blocked but has no reason")
        if impl_gate == "open" and (human != "approved" or derived != "passed"):
            errors.append(f"{rid}: implementation gate cannot open without approval and passed checks")
        if act_gate == "open" and impl_gate != "open":
            errors.append(f"{rid}: activation gate cannot open before implementation gate")

        # Human decision rules
        if human == "approved":
            if not approver or not approved_at or not approval_evidence:
                errors.append(f"{rid}: approved record lacks approver/date/evidence")
            if any(c.get("approval") != "approved" for c in choices):
                errors.append(f"{rid}: approved but a choice is not approved")
        elif human == "proposed":
            if validation == "passed":
                errors.append(f"{rid}: human_decision is proposed but validation is passed (must be approved or checks must be re-run)")

        # Deviation rules
        for choice in choices:
            if choice.get("selected") != choice.get("recommended") and not choice.get("deviation_reason"):
                errors.append(f"{rid}/{choice.get('id')}: deviation lacks reason")

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
    if require_clean:
        try:
            import subprocess
            tracked = subprocess.check_output(
                ["git", "status", "--porcelain",
                 "--", "portal/", "planning/", "scripts/verify_synthetic_review_readiness.sh",
                 "scripts/seed_release1a_dev.py"],
                text=True, stderr=subprocess.DEVNULL,
            ).strip()
            untracked = subprocess.check_output(
                ["git", "ls-files", "--others", "--exclude-standard",
                 "--", "portal/", "planning/", "scripts/verify_synthetic_review_readiness.sh",
                 "scripts/seed_release1a_dev.py"],
                text=True, stderr=subprocess.DEVNULL,
            ).strip()
            if tracked or untracked:
                warnings.append(f"review scope is dirty: tracked={bool(tracked)} untracked={bool(untracked)}")
        except subprocess.CalledProcessError:
            warnings.append("could not check git status for cleanliness")

    # Optional HEAD commit check
    if expected_commit:
        try:
            head = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
            ).strip()
            if head != expected_commit:
                warnings.append(f"HEAD {head[:8]} does not match expected {expected_commit[:8]}")
        except subprocess.CalledProcessError:
            warnings.append("could not read HEAD")

    # Optional approvals hash check
    if expected_approvals_hash:
        register_bytes = json.dumps(register, sort_keys=True, ensure_ascii=False).encode()
        actual = hashlib.sha256(register_bytes).hexdigest()
        if actual != expected_approvals_hash:
            warnings.append(f"approvals hash {actual[:8]} does not match expected {expected_approvals_hash[:8]}")

    return {
        "result": "fail" if errors else "pass",
        "records": len(records),
        "errors": errors,
        "warnings": warnings,
    }


def check_gate(
    root: Path,
    record_id: str,
    gate: str = "implementation_gate",
) -> tuple[bool, str]:
    """
    Check whether a specific gate is open for a record.

    Args:
        root: repository root
        record_id: e.g. "ENG-001"
        gate: "implementation_gate" or "activation_gate"

    Returns:
        (is_open, reason)
    """
    try:
        register = load_register(root)
    except ApprovalRegisterError as e:
        return False, f"cannot load register: {e}"

    record = next((r for r in register.get("records", []) if r.get("id") == record_id), None)
    if not record:
        return False, f"{record_id} not found in approvals register"

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
