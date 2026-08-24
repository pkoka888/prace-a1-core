#!/usr/bin/env python3
"""Machine-readable, fail-closed M2 scaffold gate."""
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def evaluate(root: Path) -> dict:
    reasons = []
    try:
        approvals = json.loads((root / "planning/approvals.json").read_text())
        catalog = json.loads((root / "docs/architecture/release-1a-catalog.json").read_text())
    except (OSError, json.JSONDecodeError) as exc:
        return {"gate": "blocked", "reasons": [f"gate input unavailable: {exc.__class__.__name__}"]}
    records = {r["id"]: r for r in approvals.get("records", [])}
    adr1 = records.get("ADR-001", {})
    if {c.get("id") for c in adr1.get("checks", [])} != {"E-MFA","E-TENANT","E-JOBS","E-STORAGE","E-AUDIT","E-A1","E-DEPS","E-ROLLBACK"} or any(c.get("status") != "passed" for c in adr1.get("checks", [])):
        reasons.append("all eight ADR-001 checks must pass")
    if catalog.get("status") != "frozen-for-synthetic-m2": reasons.append("Release 1A catalog is not frozen")
    for rid in ("ADR-002", "REV-001"):
        record = records.get(rid, {})
        if record.get("human_decision") != "approved" or record.get("validation") not in {"passed", "not-required"}:
            reasons.append(f"{rid} is not approved and validated")
    manifest = root / "docs/architecture/adr-001-evidence/manifest.json"
    commands = [
        [str(root / "venv/bin/python"), str(root / "scripts/validate_approvals.py"), "--json"],
        [str(root / "venv/bin/python"), str(root / "scripts/validate_planning.py"), "--json"],
        [str(root / "venv/bin/python"), str(root / "scripts/run_architecture_proofs.py"), "preflight", "--json"],
        [str(root / "venv/bin/python"), str(root / "scripts/run_architecture_proofs.py"), "verify", "--manifest", str(manifest.relative_to(root)), "--json"],
        [str(root / "venv/bin/python"), str(root / "scripts/generate_approval_asset.py"), "--check"],
        [str(root / "venv/bin/python"), str(root / "scripts/generate_planning_asset.py"), "--check"],
    ]
    results = []
    for command in commands:
        completed = subprocess.run(command, cwd=root, capture_output=True, text=True)
        results.append({"command": " ".join(Path(x).name if i == 0 else x for i, x in enumerate(command)), "passed": completed.returncode == 0})
        if completed.returncode: reasons.append(f"command failed: {Path(command[1]).name}")
    return {"gate": "open" if not reasons else "blocked", "reasons": reasons, "checks": results}

def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--root", type=Path, default=ROOT); parser.add_argument("--json", action="store_true")
    args = parser.parse_args(); result = evaluate(args.root.resolve())
    print(json.dumps(result, indent=2) if args.json else f"M2 scaffold gate: {result['gate']}")
    return 0 if result["gate"] == "open" else 1
if __name__ == "__main__": raise SystemExit(main())

