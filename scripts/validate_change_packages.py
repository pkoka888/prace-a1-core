#!/usr/bin/env python3
"""Validate that every dirty path belongs to exactly one review package.

The catalog is JSON-compatible YAML so this safety gate needs no optional YAML
parser. It reads path names and eligible text files only; ignored/protected
directories are never enumerated or opened.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


SECRET_PATTERNS = (
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(rb"(?i)(?:api[_-]?key|secret[_-]?key|password)\s*[:=]\s*['\"]?[A-Za-z0-9_./+-]{20,}"),
    re.compile(rb"\bsk-[A-Za-z0-9_-]{20,}\b"),
)
ARCHIVE_SUFFIXES = (".zip", ".tar", ".tar.gz", ".tgz", ".7z")
PERSONAL_HOST_PATH = re.compile(rb"/(?:home|root)/[A-Za-z0-9._-]+/")


def git(root: Path, *args: str, check: bool = True) -> bytes:
    proc = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, check=False
    )
    if check and proc.returncode:
        raise RuntimeError(proc.stderr.decode("utf-8", "replace").strip())
    return proc.stdout


def nul_paths(raw: bytes) -> set[str]:
    return {part.decode("utf-8", "surrogateescape") for part in raw.split(b"\0") if part}


def dirty_paths(root: Path) -> list[str]:
    changed = nul_paths(git(root, "diff", "--name-only", "-z", "HEAD"))
    untracked = nul_paths(git(root, "ls-files", "--others", "--exclude-standard", "-z"))
    return sorted(changed | untracked)


def safe_rule(rule: str) -> bool:
    path = PurePosixPath(rule.rstrip("/"))
    return bool(rule) and not path.is_absolute() and ".." not in path.parts


def matches(path: str, exact_or_dir: str, *, prefix: bool = False) -> bool:
    if prefix:
        return path.startswith(exact_or_dir)
    if exact_or_dir.endswith("/"):
        return path.startswith(exact_or_dir)
    return path == exact_or_dir


def load_catalog(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or not isinstance(data.get("packages"), dict):
        raise ValueError("unsupported or incomplete change-package catalog")
    return data


def validate(root: Path, catalog_path: Path) -> tuple[dict, int]:
    catalog = load_catalog(catalog_path)
    problems: list[str] = []
    declarations: dict[tuple[str, bool], str] = {}
    for package_id, package in catalog["packages"].items():
        for key, is_prefix in (("paths", False), ("prefixes", True)):
            for rule in package.get(key, []):
                if not safe_rule(rule):
                    problems.append(f"unsafe rule in {package_id}: {rule!r}")
                prior = declarations.get((rule, is_prefix))
                if prior:
                    problems.append(f"duplicate rule {rule!r}: {prior}, {package_id}")
                declarations[(rule, is_prefix)] = package_id

    dirty = dirty_paths(root)
    tracked = nul_paths(git(root, "ls-files", "-z"))
    forbidden = catalog.get("forbidden_paths", [])
    entries = []
    for path in dirty:
        owners = []
        for package_id, package in catalog["packages"].items():
            if any(matches(path, rule) for rule in package.get("paths", [])) or any(
                matches(path, rule, prefix=True) for rule in package.get("prefixes", [])
            ):
                owners.append(package_id)
        denied = [rule for rule in forbidden if matches(path, rule)]
        if denied:
            problems.append(f"dirty forbidden path: {path}")
        if len(owners) != 1:
            problems.append(f"path must have exactly one package ({len(owners)}): {path}")
        package = catalog["packages"].get(owners[0], {}) if len(owners) == 1 else {}
        eligible = package.get("eligible_for_staging", True) and not denied
        indicators = []
        candidate = root / path
        if eligible and candidate.is_file() and not candidate.is_symlink():
            if path.lower().endswith(ARCHIVE_SUFFIXES):
                indicators.append("archive")
            if candidate.stat().st_size <= 5_000_000:
                payload = candidate.read_bytes()
                if any(pattern.search(payload) for pattern in SECRET_PATTERNS):
                    indicators.append("credential-pattern")
                if (
                    candidate.suffix.lower() in {".md", ".json", ".html"}
                    and not path.startswith(("tests/", "scripts/"))
                    and PERSONAL_HOST_PATH.search(payload)
                ):
                    indicators.append("personal-host-path")
        if indicators:
            problems.append(f"eligible path requires privacy review ({','.join(indicators)}): {path}")
        entries.append({
            "path": path,
            "package": owners[0] if len(owners) == 1 else None,
            "eligible_for_staging": bool(eligible),
            "privacy_indicators": indicators,
        })

    checkpoint = catalog.get("accepted_checkpoint", "")
    commits = []
    if checkpoint:
        proc = subprocess.run(
            ["git", "-C", str(root), "log", "--format=%H%x09%s", f"{checkpoint}..HEAD"],
            capture_output=True, text=True, check=False,
        )
        if proc.returncode:
            problems.append(f"accepted checkpoint cannot be resolved: {checkpoint}")
        else:
            commits = [line for line in proc.stdout.splitlines() if line]

    package_receipts = []
    for package_id, package in catalog["packages"].items():
        package_entries = [item for item in entries if item["package"] == package_id]
        package_receipts.append({
            "package": package_id,
            "purpose": package.get("purpose"),
            "eligible_for_staging": package.get("eligible_for_staging", True),
            "exact_paths": [item["path"] for item in package_entries],
            "path_count": len(package_entries),
            "tracked_path_count": sum(1 for item in package_entries if item["path"] in tracked),
            "untracked_path_count": sum(1 for item in package_entries if item["path"] not in tracked),
            "privacy_review": "pass" if not any(item["privacy_indicators"] for item in package_entries) else "blocked",
            "checks": package.get("checks", []),
            "dependencies": package.get("dependencies", []),
            "excluded_paths": forbidden,
            "rollback": package.get("rollback"),
            "intended_commit": package.get("intended_commit"),
        })

    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repository": str(root),
        "head": git(root, "rev-parse", "HEAD").decode().strip(),
        "accepted_checkpoint": checkpoint,
        "commits_after_checkpoint": commits,
        "dirty_path_count": len(dirty),
        "classified_path_count": sum(1 for item in entries if item["package"]),
        "eligible_path_count": sum(1 for item in entries if item["eligible_for_staging"]),
        "quarantined_path_count": sum(1 for item in entries if item["package"] and not item["eligible_for_staging"]),
        "problems": problems,
        "package_receipts": package_receipts,
        "entries": entries,
    }
    return report, 0 if not problems else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--catalog", default="change-packages.yml")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    report, status = validate(root, root / args.catalog)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        output = args.output if args.output.is_absolute() else root / args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    if args.json:
        print(rendered, end="")
    else:
        print(f"dirty={report['dirty_path_count']} classified={report['classified_path_count']} "
              f"eligible={report['eligible_path_count']} quarantined={report['quarantined_path_count']}")
        for problem in report["problems"]:
            print(f"ERROR: {problem}")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
