#!/usr/bin/env python3
"""Validate that every dirty path belongs to exactly one review package.

The catalog is JSON-compatible YAML so this safety gate needs no optional YAML
parser. It reads path names and eligible text files only; ignored/protected
directories are never enumerated or opened.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import sys
import subprocess
import time
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


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _tail(text: str | None, max_chars: int) -> str:
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    return "...[truncated]...\n" + text[-max_chars:]


def _per_check_timeout(check: str) -> int:
    """Per-check timeout proportional to the workload class.

    A `manage.py test` command covering ~24 test files with real OCR
    and PDF generation routinely needs 5–10 minutes; the previous
    blanket 300s was insufficient. Fast single-file pytest runs get
    a much smaller budget so a stuck command is caught quickly.

    ``VALIDATE_CHANGE_PACKAGES_TIMEOUT`` overrides the per-class
    budget for tests that need a deterministic value (it is the single
    timeout applied to every check, not a multiplier).
    """
    override = os.environ.get("VALIDATE_CHANGE_PACKAGES_TIMEOUT", "").strip()
    if override.isdigit():
        return int(override)
    if "manage.py test" in check:
        return 900
    if "pytest tests/" in check and "tests/test_" in check:
        return 120
    return 600


def load_catalog(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or not isinstance(data.get("packages"), dict):
        raise ValueError("unsupported or incomplete change-package catalog")
    return data


def validate(root: Path, catalog_path: Path, *, staged: bool = False) -> tuple[dict, int]:
    if staged:
        catalog = json.loads(git(root, "show", ":" + catalog_path.relative_to(root).as_posix()))
        if catalog.get("schema_version") != 1 or not isinstance(catalog.get("packages"), dict):
            raise ValueError("invalid staged catalog")
    else:
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

    dirty = sorted(nul_paths(git(root, "diff", "--cached", "--name-only", "--no-renames", "-z"))) if staged else dirty_paths(root)
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
        if staged and any(part in {"a1", "scans", "evidence", "ocr", "data", "output", "runtime", "secrets", ".history-remediation", "private", "reports"} for part in PurePosixPath(path).parts):
            denied.append("protected-path")
        if staged and (PurePosixPath(path).name == ".env" or PurePosixPath(path).name.startswith(".env.") and PurePosixPath(path).name != ".env.example"):
            denied.append("environment-file")
        if denied:
            problems.append(f"dirty forbidden path: {path}")
        if len(owners) != 1:
            problems.append(f"path must have exactly one package ({len(owners)}): {path}")
        package = catalog["packages"].get(owners[0], {}) if len(owners) == 1 else {}
        eligible = package.get("eligible_for_staging", True) and not denied
        indicators = []
        if staged and not eligible:
            problems.append(f"staged path is ineligible: {path}")
        candidate = root / path
        payload = None
        if eligible and staged:
            entry = git(root, "ls-files", "--stage", "-z", "--", path)
            if entry:
                mode, oid, stage = entry.split(b"\t", 1)[0].split()
                if mode not in (b"100644", b"100755") or stage != b"0":
                    indicators.append("unsupported-index-entry")
                else:
                    size = int(git(root, "cat-file", "-s", oid.decode()))
                    if size > 5_000_000:
                        indicators.append("oversize-review-required")
                    else:
                        payload = git(root, "cat-file", "blob", oid.decode())
        elif eligible and candidate.is_file() and not candidate.is_symlink():
            if candidate.stat().st_size <= 5_000_000:
                payload = candidate.read_bytes()
        if payload is not None:
            if path.lower().endswith(ARCHIVE_SUFFIXES):
                indicators.append("archive")
            if any(pattern.search(payload) for pattern in SECRET_PATTERNS):
                indicators.append("credential-pattern")
            if (candidate.suffix.lower() in {".md", ".json", ".html"}
                and not path.startswith(("tests/", "scripts/"))
                and PERSONAL_HOST_PATH.search(payload)):
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
    parser.add_argument("--staged", action="store_true")
    parser.add_argument("--run-checks", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        report, status = validate(root, root / args.catalog, staged=args.staged)
    except (OSError, ValueError, RuntimeError, KeyError, TypeError):
        print("CHANGE_PACKAGE_VALIDATION_FAILED", file=sys.stderr)
        return 1
    check_run_receipt = {"started_at": now_iso(),
                          "finished_at": None,
                          "checks": []}
    if args.run_checks:
        if not args.staged or status:
            return 1
        # Build (package, check, timeout) tuples. Per-check timeout scales
        # with the command class: a `manage.py test` covering ~24 test
        # files needs a long budget; a fast pytest run of a single file
        # does not. The blanket 300s timeout was the cause of the
        # recent commit-hooks failing without diagnostic detail.
        selected = []
        seen = set()
        for receipt in report["package_receipts"]:
            if not receipt["path_count"]:
                continue
            for check in receipt["checks"]:
                key = (receipt["package"], check)
                if key in seen:
                    continue
                seen.add(key)
                selected.append(key)

        # Some checks are dispatch stubs that emit the actual command
        # list at run time (e.g. ``scripts/select_*.py``). Resolve those
        # first; an empty list means the package contributes no test
        # command for the staged set (e.g. doc-only change).
        resolved = []
        for package_id, check in selected:
            if check.startswith("scripts/select_") and check.endswith(".py"):
                proc = subprocess.run(
                    [sys.executable, str(root / check)],
                    cwd=root, check=False, capture_output=True,
                    text=True, timeout=30,
                )
                for line in (proc.stdout or "").splitlines():
                    line = line.strip()
                    if line:
                        resolved.append((package_id, line))
                if proc.returncode != 0 and not resolved:
                    check_run_receipt["checks"].append({
                        "package": package_id,
                        "check": check,
                        "command": [sys.executable, str(root / check)],
                        "timeout_s": 30,
                        "elapsed_s": 0.0,
                        "status": "FAIL",
                        "exit_code": proc.returncode,
                        "error": (proc.stderr or "").strip()[:2000],
                        "stdout_tail": "",
                        "stderr_tail": "",
                    })
                    break
            else:
                resolved.append((package_id, check))

        for package_id, check in resolved:
            if not check.strip():
                # Dispatcher emitted no command (e.g. doc-only change).
                continue
            command = shlex.split(check)
            command = shlex.split(check)
            if not command or any(token in {"|", ";", "&&", "||", ">"} for token in command):
                print(f"ERROR: refused unsafe check command: {check!r}",
                      file=sys.stderr)
                return 1
            budget = _per_check_timeout(check)
            t0 = time.monotonic()
            outcome = {"package": package_id, "check": check,
                       "command": command, "timeout_s": budget,
                       "elapsed_s": 0.0, "status": "FAIL", "exit_code": None,
                       "error": None, "stdout_tail": "", "stderr_tail": ""}
            try:
                proc = subprocess.run(command, cwd=root, check=False,
                                      capture_output=True, text=True, timeout=budget)
                outcome["exit_code"] = proc.returncode
                outcome["stdout_tail"] = _tail(proc.stdout, 2000)
                outcome["stderr_tail"] = _tail(proc.stderr, 2000)
                outcome["status"] = "PASS" if proc.returncode == 0 else "FAIL"
            except subprocess.TimeoutExpired as exc:
                outcome["status"] = "TIMEOUT"
                outcome["elapsed_s"] = time.monotonic() - t0
                outcome["error"] = f"timeout after {budget}s"
                # Capture whatever partial output the subprocess produced
                # so the failure is not a single opaque TIMEOUT line.
                if exc.stdout:
                    if isinstance(exc.stdout, bytes):
                        exc.stdout = exc.stdout.decode("utf-8", "replace")
                    outcome["stdout_tail"] = _tail(exc.stdout, 2000)
                if exc.stderr:
                    if isinstance(exc.stderr, bytes):
                        exc.stderr = exc.stderr.decode("utf-8", "replace")
                    outcome["stderr_tail"] = _tail(exc.stderr, 2000)
            except (OSError, subprocess.SubprocessError) as exc:
                outcome["error"] = f"{type(exc).__name__}: {exc}"
            finally:
                outcome["elapsed_s"] = round(time.monotonic() - t0, 3)
            check_run_receipt["checks"].append(outcome)
            print(f"  [{package_id}] {outcome['status']:7s} "
                  f"{outcome['elapsed_s']:6.1f}s/{budget}s  {check[:80]}",
                  file=sys.stderr)
            if outcome["status"] != "PASS":
                print(f"PACKAGE_CHECK_FAILED ({outcome['status']}): "
                      f"{package_id} :: {check}", file=sys.stderr)
                if outcome["stdout_tail"]:
                    print(f"--- stdout tail ({package_id}) ---\n"
                          f"{outcome['stdout_tail']}", file=sys.stderr)
                if outcome["stderr_tail"]:
                    print(f"--- stderr tail ({package_id}) ---\n"
                          f"{outcome['stderr_tail']}", file=sys.stderr)
                break
        check_run_receipt["finished_at"] = now_iso()
    report["check_run"] = check_run_receipt
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
    if args.run_checks and check_run_receipt["checks"]:
        # Report even on failure; gate exit on the actual outcome.
        any_failed = any(c["status"] != "PASS" for c in check_run_receipt["checks"])
        if any_failed and not report["problems"]:
            return 1
    return status


if __name__ == "__main__":
    raise SystemExit(main())
