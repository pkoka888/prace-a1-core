#!/usr/bin/env python3
"""Write a PII-safe inventory of tracked repository paths.

The report records path metadata and reachability only. It never reads file
contents, enumerates ignored/private files, or includes hashes of PII artifacts.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRIVATE_INPUT_CONTRACT = "$A1_PRIVATE_DIR/a1/review.csv"
CANONICAL = {
    "scripts/generate_provisional_a1.py": "production-runtime",
    "scripts/finalize_a1.py": "production-runtime",
    "scripts/a1_core.py": "production-runtime",
    "scripts/a1_quality_gate.py": "production-runtime",
    "templates/a1_background.pdf": "production-template",
    "config/a1_layout.json": "production-config",
    "config/a1_provisional.json": "production-config-sensitive",
}
LEGACY_ACTIVE_SCRIPTS = set()


def git_lines(*args: str) -> list[str]:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    )
    return [line for line in result.stdout.splitlines() if line]


def classify(path: str) -> tuple[str, str]:
    if path in CANONICAL:
        return CANONICAL[path], "retain"
    if path in LEGACY_ACTIVE_SCRIPTS:
        return "experimental-or-recovery-utility", "manual-review-before-archive"
    if path.startswith("archive/"):
        return "archived", "retain-as-history"
    if path.startswith("tests/") or path == "pytest.ini":
        return "production-test", "retain"
    if path.startswith("config/institutions/"):
        return "production-config", "retain"
    if path.startswith("config/"):
        return "supporting-or-legacy-config", "manual-review"
    if path.startswith("plans/") or path.startswith("reports/") or path.startswith("research/"):
        return "documentation", "retain-or-supersede-explicitly"
    if path.endswith(".md"):
        return "documentation", "retain"
    return "supporting", "manual-review"


def build() -> dict:
    tracked = sorted(git_lines("ls-files"))
    untracked = sorted(git_lines("ls-files", "--others", "--exclude-standard"))
    entries = []
    redacted_groups: dict[str, int] = {}
    for path in [*tracked, *untracked]:
        group = None
        if path.startswith("archive/"):
            group = "archive/**"
        elif path.startswith("data/employees/"):
            group = "data/employees/**"
        elif path.startswith("output/"):
            group = "output/**"
        if group:
            redacted_groups[group] = redacted_groups.get(group, 0) + 1
            continue
        category, action = classify(path)
        entries.append({
            "path": path,
            "tracked": path in tracked,
            "classification": category,
            "recommended_action": action,
        })
    return {
        "schema_version": 1,
        "scope": "tracked and nonignored-untracked paths; ignored/private paths deliberately excluded",
        "private_input_contract": PRIVATE_INPUT_CONTRACT,
        "head": git_lines("rev-parse", "HEAD")[0],
        "branch": git_lines("branch", "--show-current")[0],
        "tracked_path_count": len(tracked),
        "untracked_nonignored_path_count": len(untracked),
        "redacted_path_groups": redacted_groups,
        "entries": entries,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "reports/repository-inventory.json"
    )
    args = parser.parse_args()
    payload = build()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {payload['tracked_path_count']} tracked paths to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
