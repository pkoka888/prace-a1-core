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
import signal
import tempfile
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


def _per_check_timeout(check: str) -> int:
    """Measured integration budget; recognize pytest arguments independent of order."""
    override = os.environ.get("VALIDATE_CHANGE_PACKAGES_TIMEOUT", "").strip()
    if override:
        if not override.isdigit() or int(override) <= 0:
            raise ValueError("VALIDATE_CHANGE_PACKAGES_TIMEOUT must be a positive integer")
        return int(override)
    tokens = shlex.split(check)
    if any(Path(t).name == "manage.py" and tokens[i + 1:i + 2] == ["test"]
           for i, t in enumerate(tokens)):
        return 900
    if "pytest" in tokens:
        targets = [t.split("::", 1)[0] for t in tokens[tokens.index("pytest") + 1:]
                   if not t.startswith("-") and t.startswith("tests/")]
        if len(targets) == 1 and targets[0].endswith(".py"):
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
        if ".runtime-config" in PurePosixPath(path).parts:
            denied.append("protected-runtime-configuration")
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


def _write_report(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(path.name + ".pending")
    with temporary.open("w", encoding="utf-8") as stream:
        temporary.chmod(0o600)
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    temporary.replace(path)


def _log_tail(path: Path) -> str:
    with path.open("rb") as stream:
        stream.seek(max(0, path.stat().st_size - 2000))
        return stream.read().decode("utf-8", "replace")


def _run_command(root: Path, outcome: dict, directory: Path, number: int) -> None:
    """Bound the entire process group; keep full output without buffering it in RAM."""
    started = time.monotonic()
    proc = None
    stdout = directory / f"check-{number}.stdout"
    stderr = directory / f"check-{number}.stderr"
    outcome.update(stdout_log=str(stdout), stderr_log=str(stderr))
    print(f"START [{outcome['package']}] budget={outcome['timeout_s']}s "
          f"{outcome['check']}\n  log: {stdout}", file=sys.stderr, flush=True)
    try:
        with stdout.open("wb") as out, stderr.open("wb") as err:
            stdout.chmod(0o600)
            stderr.chmod(0o600)
            proc = subprocess.Popen(outcome["command"], cwd=root, stdout=out, stderr=err,
                                    start_new_session=True,
                                    env={**os.environ, "PYTHONUNBUFFERED": "1"})
            while True:
                remaining = outcome["timeout_s"] - (time.monotonic() - started)
                if remaining <= 0:
                    outcome.update(status="TIMEOUT", error=f"timeout after {outcome['timeout_s']}s")
                    break
                try:
                    code = proc.wait(timeout=min(15, remaining))
                    outcome.update(exit_code=code, status="PASS" if code == 0 else "FAIL")
                    break
                except subprocess.TimeoutExpired:
                    print(f"RUNNING [{outcome['package']}] {time.monotonic() - started:.1f}s "
                          f"(budget {outcome['timeout_s']}s)", file=sys.stderr, flush=True)
    except KeyboardInterrupt:
        outcome.update(status="INTERRUPTED", error="validation interrupted by signal")
    except OSError as exc:
        outcome.update(status="ERROR", error=f"{type(exc).__name__}: {exc}")
    finally:
        if proc is not None:
            # Also stop descendants left behind after a wrapper exits.
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait()
            outcome["exit_code"] = proc.returncode
        outcome["elapsed_s"] = round(time.monotonic() - started, 3)
        outcome["stdout_tail"] = _log_tail(stdout) if stdout.exists() else ""
        outcome["stderr_tail"] = _log_tail(stderr) if stderr.exists() else ""
    print(f"{outcome['status']} [{outcome['package']}] {outcome['elapsed_s']:.2f}s "
          f"exit={outcome['exit_code']}", file=sys.stderr, flush=True)


def _execute_checks(root: Path, report: dict, directory: Path, output: Path) -> bool:
    receipt = report["check_run"]

    def execute(package, check, *, selector=False, paths=None):
        outcome = dict(package=package, check=check, kind="selector" if selector else "check",
                       command=[], timeout_s=30 if selector else None, elapsed_s=0.0,
                       status="RUNNING", exit_code=None, error=None,
                       stdout_tail="", stderr_tail="")
        receipt["checks"].append(outcome)
        try:
            command = shlex.split(check)
            if not command or any(t in {"|", ";", "&&", "||", ">"} for t in command):
                raise ValueError("unsafe or empty check command")
            if selector:
                if not safe_rule(check):
                    raise ValueError("unsafe selector path")
                command = [sys.executable, str(root / check), "--root", str(root),
                           "--paths-json", json.dumps(paths)]
            outcome["command"] = command
            if not selector:
                outcome["timeout_s"] = _per_check_timeout(check)
            _write_report(output, report)
            _run_command(root, outcome, directory, len(receipt["checks"]))
        except (ValueError, OSError) as exc:
            outcome.update(status="ERROR", error=f"{type(exc).__name__}: {exc}")
        _write_report(output, report)
        if outcome["status"] != "PASS":
            print(f"PACKAGE_CHECK_FAILED ({outcome['status']}): {package} :: {check}\n"
                  f"{outcome['error'] or ''}\n{outcome['stdout_tail']}\n{outcome['stderr_tail']}",
                  file=sys.stderr, flush=True)
        return outcome

    resolved = []
    for package in report["package_receipts"]:
        if not package["path_count"]:
            continue
        for check in package["checks"]:
            if check.startswith("scripts/select_") and check.endswith(".py"):
                outcome = execute(package["package"], check, selector=True, paths=package["exact_paths"])
                if outcome["status"] != "PASS":
                    return False  # Never consume partial output from a failed selector.
                commands = Path(outcome["stdout_log"]).read_text().splitlines()
                resolved.extend((package["package"], c.strip()) for c in commands if c.strip())
            else:
                resolved.append((package["package"], check))
    seen = set()
    for package, check in resolved:
        # Deduplicate actual commands across packages, after selector expansion.
        try:
            key = tuple(shlex.split(check))
        except ValueError:
            key = (check,)
        if key in seen:
            continue
        seen.add(key)
        if execute(package, check)["status"] != "PASS":
            return False
    return True


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
    report["check_run"] = dict(started_at=now_iso(), finished_at=None, checks=[])
    output = (root / args.output) if args.output else None
    if args.run_checks:
        parent = root / "runtime/portal/temporary"
        parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        directory = Path(tempfile.mkdtemp(prefix="change-checks-", dir=parent))
        directory.chmod(0o700)
        output = output or directory / "report.json"
        print(f"VALIDATION_REPORT: {output}", file=sys.stderr, flush=True)
        _write_report(output, report)
        previous = {}

        def interrupt(signum, frame):
            raise KeyboardInterrupt

        try:
            for signum in (signal.SIGTERM, signal.SIGINT):
                previous[signum] = signal.signal(signum, interrupt)
            if not args.staged or status:
                status = 1
            elif not _execute_checks(root, report, directory, output):
                status = 1
        except KeyboardInterrupt:
            report["problems"].append("validation interrupted")
            status = 1
        finally:
            for signum, handler in previous.items():
                signal.signal(signum, handler)
            report["check_run"]["finished_at"] = now_iso()
    if output:
        _write_report(output, report)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"dirty={report['dirty_path_count']} classified={report['classified_path_count']} "
              f"eligible={report['eligible_path_count']} quarantined={report['quarantined_path_count']}")
        for problem in report["problems"]:
            print(f"ERROR: {problem}")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
