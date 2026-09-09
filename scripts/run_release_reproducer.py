"""Reproduce committed source, with exact-tree integrity and isolated receipts.

This is a selected synthetic acceptance run, not deployment or real-data approval.
The invoking runner and installed venv are recorded separately from tested source.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone


def digest(data):
    return hashlib.sha256(data).hexdigest()


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], stderr=subprocess.PIPE)


def tree(repo, sha):
    entries = {}
    for row in git(repo, "ls-tree", "-rz", sha).split(b"\0"):
        if not row:
            continue
        meta, name = row.split(b"\t", 1)
        mode, kind, oid = meta.decode().split()
        path = os.fsdecode(name)
        if kind != "blob" or mode not in {"100644", "100755"}:
            raise ValueError("Unsupported Git entry (symlinks/submodules are not exported)")
        if Path(path).is_absolute() or ".." in Path(path).parts:
            raise ValueError("Unsafe Git path")
        if Path(path).parts[0] in {"a1", "scans", "evidence", "ocr", "data", "output", "runtime", "secrets", ".env", ".history-remediation"} or path.startswith("employees/scans/"):
            raise ValueError("Protected data path present in requested Git tree; content review required")
        entries[path] = (mode, git(repo, "cat-file", "blob", oid))
    return entries


def verify_export(export, entries, *, test_copy=False):
    if export.is_symlink() or not export.is_dir():
        raise ValueError("Export integrity: invalid root")
    expected_dir_mode = 0o700 if test_copy else 0o500
    if stat.S_IMODE(export.stat().st_mode) != expected_dir_mode or export.stat().st_uid != os.getuid():
        raise ValueError("Export integrity: root permissions or ownership")
    expected_dirs = {str(p) for name in entries for p in Path(name).parents if str(p) != "."}
    found = set()
    for directory, dirs, files in os.walk(export, followlinks=False):
        for name in dirs + files:
            path = Path(directory) / name
            rel = path.relative_to(export).as_posix()
            if path.is_symlink():
                raise ValueError("Export integrity: symlink")
            if path.is_dir():
                if test_copy and (rel == "runtime" or rel.startswith("runtime/")):
                    dirs.remove(name)
                    continue
                if stat.S_IMODE(path.stat().st_mode) != expected_dir_mode or path.stat().st_uid != os.getuid():
                    raise ValueError("Export integrity: directory permissions or ownership")
                if rel not in expected_dirs:
                    raise ValueError("Export integrity: unexpected directory")
                continue
            if not stat.S_ISREG(path.stat().st_mode) or rel not in entries:
                raise ValueError("Export integrity: unexpected entry")
            mode, data = entries[rel]
            expected_mode = (0o700 if mode == "100755" else 0o600) if test_copy else (0o500 if mode == "100755" else 0o400)
            if path.read_bytes() != data or stat.S_IMODE(path.stat().st_mode) != expected_mode or path.stat().st_uid != os.getuid():
                raise ValueError("Export integrity: changed bytes or permissions")
            found.add(rel)
    if found != set(entries):
        raise ValueError("Export integrity: missing entry")


def private_dir(path):
    if path.is_symlink():
        raise ValueError("Private directory must not be a symlink")
    if not path.exists():
        path.mkdir(mode=0o700)
        path.chmod(0o700)  # Clear inherited setgid on directories created by this run.
    if not path.is_dir():
        raise ValueError("Private directory is not a directory")


def export_tree(repo, sha, entries):
    runtime = repo / "runtime"
    private_dir(runtime)
    export = runtime / f"s-{sha}"
    if export.exists() or export.is_symlink():
        verify_export(export, entries)
        return export
    stage = Path(tempfile.mkdtemp(prefix=".source-export-", dir=runtime))
    try:
        for name, (mode, data) in entries.items():
            dest = stage / name
            dest.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            dest.write_bytes(data)
            dest.chmod(0o500 if mode == "100755" else 0o400)
        for directory, _, _ in os.walk(stage, topdown=False):
            Path(directory).chmod(0o500)
        verify_export(stage, entries)
        # rename is atomic; concurrent nonempty exports cannot be overwritten.
        stage.rename(export)
    finally:
        if stage.exists():
            for directory, _, _ in os.walk(stage):
                Path(directory).chmod(0o700)
            shutil.rmtree(stage)
    return export


PLANNING_CHECK = '''import json, pathlib, jsonschema
from scripts import validate_planning as v
root=pathlib.Path.cwd()
checks=v.build_checks(json.loads((root/v.DEFAULT_CATALOG).read_text()),root,jsonschema,json.loads((root/v.DEFAULT_SCHEMA).read_text()))
failed=[]
for name, check in checks:
    if name == "staged forbidden-path and PII/secret indicators":
        continue
    ok, detail=check()
    print(name, ok, detail)
    if not ok: failed.append(name)
raise SystemExit(bool(failed))
'''


def acceptance_commands(python, state):
    return [
        [python, "-c", PLANNING_CHECK],
        [python, "-m", "pytest", "-p", "no:cacheprovider", "--basetemp", str(state / "pytest"),
         "tests/m2/test_synthetic_containment.py", "tests/test_release_reproducer.py",
         "tests/test_finalize_a1.py", "tests/test_a1_stabilization.py", "-q"],
        [python, "manage.py", "test", "tests.document_web.test_inbox", "tests.document_web.test_identity", "--noinput", "--verbosity", "1"],
    ]


def reproduce(repo, revision, *, commands=None):
    """commands is an internal injection seam for synthetic unit fixtures only."""
    os.umask(0o077)
    started_at = datetime.now(timezone.utc).isoformat()
    repo = Path(repo).resolve()
    try:
        sha = git(repo, "rev-parse", "--verify", "--end-of-options", revision + "^{commit}").decode().strip()
    except subprocess.CalledProcessError as exc:
        raise ValueError("cannot resolve requested revision to a commit") from exc
    entries = tree(repo, sha)
    export = export_tree(repo, sha, entries)
    parent = repo / "runtime"
    for segment in ("portal", "temporary", "release-reproducer"):
        parent = parent / segment
        private_dir(parent)
    state = parent / uuid.uuid4().hex
    private_dir(state)
    for name in ("tmp", "home"):
        private_dir(state / name)
    work = state / "source"
    shutil.copytree(export, work)
    for directory, _, files in os.walk(work):
        Path(directory).chmod(0o700)
        for name in files:
            path = Path(directory) / name
            mode = entries[path.relative_to(work).as_posix()][0]
            path.chmod(0o700 if mode == "100755" else 0o600)
    verify_export(work, entries, test_copy=True)
    env = {"PATH": str(Path(sys.executable).parent) + ":/usr/bin:/bin", "HOME": str(state / "home"),
           "TMPDIR": str(state / "tmp"), "PYTHONPATH": str(work), "PYTHONDONTWRITEBYTECODE": "1",
           "DJANGO_SETTINGS_MODULE": "portal.settings_document_tests",
           "GIT_CEILING_DIRECTORIES": str(work.parent), "LC_ALL": "C.UTF-8"}
    commands = commands if commands is not None else acceptance_commands(sys.executable, state)
    receipt = {"schema_version": "2.0", "commit_sha": sha, "git_tree": git(repo, "rev-parse", sha + "^{tree}").decode().strip(),
               "started_at": started_at,
               "export_dir": str(export), "test_cwd": str(work), "runner_sha256": digest(Path(__file__).read_bytes()),
               "python": {"executable": sys.executable, "executable_sha256": digest(Path(sys.executable).read_bytes()), "version": sys.version},
               "dependencies": sorted(f"{d.metadata['Name']}=={d.version}" for d in importlib.metadata.distributions()),
               "environment": env, "checks": [],
               "omitted_checks": {"staged forbidden-path and PII/secret indicators": "Index-only check; plain committed export has no index. Source publication hooks remain required."}}
    for index, argv in enumerate(commands, 1):
        start = time.monotonic()
        stdout, stderr = state / f"check-{index}.stdout", state / f"check-{index}.stderr"
        with stdout.open("wb") as out, stderr.open("wb") as err:
            try:
                result = subprocess.run(argv, cwd=work, env=env, stdout=out, stderr=err, check=False, timeout=600)
                exit_code = result.returncode
            except subprocess.TimeoutExpired:
                err.write(b"Acceptance command exceeded 600 seconds.\n")
                exit_code = 124
            except OSError as exc:
                err.write((str(exc) + "\n").encode())
                exit_code = 127
        receipt["checks"].append({"argv": argv, "exit_code": exit_code,
            "duration_seconds": time.monotonic() - start,
            "stdout_log": stdout.name, "stdout_sha256": digest(stdout.read_bytes()),
            "stderr_log": stderr.name, "stderr_sha256": digest(stderr.read_bytes())})
    try:
        verify_export(export, entries)
        verify_export(work, entries, test_copy=True)
        receipt["source_integrity_after_checks"] = True
    except ValueError:
        receipt["source_integrity_after_checks"] = False
    receipt["passed"] = receipt["source_integrity_after_checks"] and all(c["exit_code"] == 0 for c in receipt["checks"])
    receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
    receipt_path = state / "receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt_path, receipt


def main():
    if len(sys.argv) != 2:
        print("Usage: release_reproducer.sh <commit-sha>", file=sys.stderr)
        return 2
    try:
        path, receipt = reproduce(Path(__file__).resolve().parents[1], sys.argv[1])
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"Receipt: {path}")
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
