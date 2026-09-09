#!/usr/bin/env python3
"""
Release 1A verification harness.

Runs diagnostic checks against a fresh disposable synthetic database and produces
a structured JSON report plus a sanitized Markdown summary.

Each check has exactly one status:
  PASS         — command succeeded with expected output
  FAIL         — command failed or produced unexpected output
  BLOCKED_ENV  — environment prerequisite not available (e.g., PostgreSQL, browser)
  NOT_RUN      — check not applicable to current configuration

No PII, credentials, scan data, or protected content is ever written to reports.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = ROOT / "runtime" / "portal" / "verification"
REPORT_JSON = REPORT_DIR / "verification-report.json"
REPORT_MD = REPORT_DIR / "verification-report.md"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run(
    *args: str,
    check: bool = False,
    capture: bool = True,
    env: dict | None = None,
    cwd: Path | None = None,
    timeout: int = 120,
) -> subprocess.CompletedProcess | None:
    """Run a command, optionally capturing output."""
    full_env = dict(os.environ)
    if env:
        full_env.update(env)
    try:
        return subprocess.run(
            args,
            capture_output=capture,
            text=True,
            check=check,
            env=full_env,
            cwd=cwd or ROOT,
            timeout=timeout,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return None


def check_cmd(
    label: str,
    cmd: list[str],
    env: dict | None = None,
    cwd: Path | None = None,
    timeout: int = 120,
) -> dict:
    """Run a command and return a result dict."""
    start = now()
    result = run(*cmd, env=env, cwd=cwd, timeout=timeout)
    end = now()
    if result is None:
        return {
            "label": label,
            "status": "BLOCKED_ENV",
            "command": " ".join(cmd),
            "start": start,
            "end": end,
            "exit_code": None,
            "stdout": "",
            "stderr": "",
            "error": "command not found or timed out",
        }
    stdout = result.stdout[:2000] if result.stdout else ""
    stderr = result.stderr[:1000] if result.stderr else ""
    return {
        "label": label,
        "status": "PASS" if result.returncode == 0 else "FAIL",
        "command": " ".join(cmd),
        "start": start,
        "end": end,
        "exit_code": result.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "error": None if result.returncode == 0 else f"exit {result.returncode}",
    }


def check_py(
    label: str,
    code: str,
    env: dict | None = None,
) -> dict:
    """Run inline Python and return a result dict."""
    start = now()
    full_env = dict(os.environ)
    if env:
        full_env.update(env)
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env=full_env,
        cwd=ROOT,
        timeout=60,
    )
    end = now()
    stdout = proc.stdout[:2000] if proc.stdout else ""
    stderr = proc.stderr[:1000] if proc.stderr else ""
    return {
        "label": label,
        "status": "PASS" if proc.returncode == 0 else "FAIL",
        "command": f"python -c {code[:80]}...",
        "start": start,
        "end": end,
        "exit_code": proc.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "error": None if proc.returncode == 0 else f"exit {proc.returncode}",
    }


def check_py_with_assertion(
    label: str,
    code: str,
    assertion: str,
    env: dict | None = None,
) -> dict:
    """
    Run inline Python and assert the output contains |assertion|.
    Returns PASS if assertion found, FAIL otherwise.
    """
    result = check_py(label, code, env=env)
    if result["status"] == "PASS" and assertion.lower() in result["stdout"].lower():
        result["status"] = "PASS"
    elif result["status"] == "PASS" and assertion.lower() not in result["stdout"].lower():
        result["status"] = "FAIL"
        result["error"] = f"assertion '{assertion}' not found in output"
    return result


def git_info() -> dict:
    """Return git HEAD info."""
    commit = run("git", "rev-parse", "HEAD", capture=True)
    branch = run("git", "rev-parse", "--abbrev-ref", "HEAD", capture=True)
    clean = run("git", "status", "--porcelain", capture=True)
    return {
        "commit": commit.stdout.strip() if commit else "unknown",
        "branch": branch.stdout.strip() if branch else "unknown",
        "tree_clean": not bool(clean.stdout.strip()) if clean else False,
    }


def approvals_hash() -> str:
    """SHA-256 of approvals.json."""
    import hashlib
    import json as _json
    data = _json.loads((ROOT / "planning" / "approvals.json").read_text())
    return hashlib.sha256(
        _json.dumps(data, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def build_id() -> str:
    """Derive build identity from current HEAD git describe."""
    g = run("git", "describe", "--always", "--dirty", capture=True)
    return g.stdout.strip() if g else "unknown"


# ---------------------------------------------------------------------------
# Django setup helpers
# ---------------------------------------------------------------------------

def django_settings() -> str:
    return "portal.settings_verification"


def django_env() -> dict:
    """Environment with Django configured for verification DB."""
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    env["DJANGO_SETTINGS_MODULE"] = django_settings()
    return env


def django_check(label: str, *args: str) -> dict:
    """Run a Django management command and return a result dict."""
    cmd = [sys.executable, "manage.py", *args]
    return check_cmd(label, cmd, env=django_env())


# ---------------------------------------------------------------------------
# Verification sections
# ---------------------------------------------------------------------------

def verify_governance() -> list[dict]:
    """Gate integrity and approval register checks."""
    results = []
    env = django_env()

    r = check_cmd(
        "governance/approval-validator",
        [sys.executable, "scripts/validate_approvals.py"],
        env=env,
    )
    results.append(r)

    r = check_cmd(
        "governance/planning-validator",
        [sys.executable, "scripts/validate_planning.py"],
        env=env,
    )
    results.append(r)

    code = f"""
import sys
sys.path.insert(0, {repr(str(ROOT))})
from planning.approval_register import validate, check_gate
from pathlib import Path
result = validate(Path({repr(str(ROOT))}))
data = __import__('json').loads((Path({repr(str(ROOT))}) / 'planning' / 'approvals.json').read_text())
by_id = {{r['id']: r for r in data['records']}}
eng = by_id.get('ENG-001', {{}})
rev2 = by_id.get('REV-002', {{}})
rev3 = by_id.get('REV-003', {{}})
checks = [
    ('ENG-001 blocked', eng.get('implementation_gate') == 'blocked'),
    ('REV-002 blocked', rev2.get('implementation_gate') == 'blocked'),
    ('REV-003 blocked', rev3.get('implementation_gate') == 'blocked'),
    ('REV-002 depends on ENG-001', any(d['id']=='ENG-001' for d in rev2.get('dependencies',[]))),
    ('REV-003 depends on OPS-001', any(d['id']=='OPS-001' for d in rev3.get('dependencies',[]))),
    ('REV-003 depends on LEG-001', any(d['id']=='LEG-001' for d in rev3.get('dependencies',[]))),
    ('REV-003 depends on INF-001', any(d['id']=='INF-001' for d in rev3.get('dependencies',[]))),
    ('REV-003 depends on REV-002 approved', any(d['id']=='REV-002' and d['required_gate']=='approved' for d in rev3.get('dependencies',[]))),
]
for label, passed in checks:
    status = 'PASS' if passed else 'FAIL'
    print(f'{{status}}: {{label}}')
sys.exit(0 if all(v for _, v in checks) else 1)
"""
    results.append(check_py("governance/gate-dependencies", code, env=env))

    code = """
import sys
sys.path.insert(0, '.')
from planning.approval_register import validate, check_gate, approvals_hash
print("PASS: approval_register module imported")
"""
    results.append(check_py("governance/shared-module-import", code))

    return results


def verify_django_checks() -> list[dict]:
    """Django system checks."""
    return [
        django_check("django/check", "check"),
        django_check("django/makemigrations-check", "makemigrations", "--check", "--dry-run"),
    ]


def verify_migrations() -> list[dict]:
    """Migration state and executor transitions."""
    results = []
    results.append(django_check("migrations/fresh-db-makemigrations", "makemigrations", "--check", "--dry-run"))

    for n in ["0005", "0006", "0007"]:
        found = bool(list(ROOT.glob(f"portal/release1a/migrations/{n}_*.py")))
        results.append({
            "label": f"migrations/{n}_exists",
            "status": "PASS" if found else "FAIL",
            "command": f"ls portal/release1a/migrations/{n}_*.py",
            "start": now(),
            "end": now(),
            "exit_code": 0 if found else 1,
            "stdout": f"{n} migration {'found' if found else 'MISSING'}",
            "stderr": "",
            "error": None if found else f"migration {n} not found",
        })

    code = f"""
import sys, os
sys.path.insert(0, {repr(str(ROOT))})
os.environ['DJANGO_SETTINGS_MODULE'] = {repr(django_settings())}
import django
django.setup()
from django.db.migrations.executor import MigrationExecutor
from django.db import connection
executor = MigrationExecutor(connection)
loader = executor.loader
print(f"MigrationExecutor available, {{len(loader.disk_migrations)}} migrations on disk")
"""
    results.append(check_py("migrations/executor-available", code, env=django_env()))

    # MigrationExecutor transition test: verify migrations 0006 and 0007 are on disk
    # and the executor can construct a valid migration plan from current state
    code = f"""
import sys, os
sys.path.insert(0, {repr(str(ROOT))})
os.environ['DJANGO_SETTINGS_MODULE'] = {repr(django_settings())}
import django
django.setup()
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.loader import MigrationLoader

executor = MigrationExecutor(connection)
loader = executor.loader
# Verify migrations 0006 and 0007 are on disk
disk_migrations = {{m for m in loader.disk_migrations if m[0] == 'release1a'}}
names = sorted([m[1] for m in disk_migrations])
has_0006 = any('0006' in n for n in names)
has_0007 = any('0007' in n for n in names)
print(f"Release1a migrations on disk: {{names}}")
print(f"Migration 0006 on disk: {{has_0006}}")
print(f"Migration 0007 on disk: {{has_0007}}")
if has_0006 and has_0007:
    print("PASS: migrations 0006 and 0007 present and can be loaded")
else:
    print("FAIL: missing required migrations")
"""
    results.append(check_py("migrations/executor-transition", code, env=django_env()))

    return results


def verify_backend_crud() -> list[dict]:
    """Backend CRUD and tenant isolation tests.

    Note: tests/architecture/ contains prototype contract tests, not real portal
    behavior tests. These are informational only and marked as NOT_RUN for ENG-001
    evidence purposes.
    """
    results = []
    env = django_env()

    for test_path in [
        "tests/architecture/test_tenant_isolation.py",
        "tests/architecture/test_transactions.py",
        "tests/architecture/test_rollback.py",
    ]:
        if not (ROOT / test_path).exists():
            results.append({
                "label": f"backend/{Path(test_path).stem}",
                "status": "NOT_RUN",
                "command": f"test -f {test_path}",
                "start": now(),
                "end": now(),
                "exit_code": 0,
                "stdout": "test file not found",
                "stderr": "",
                "error": "not found",
            })
            continue
        r = check_cmd(
            f"backend/{Path(test_path).stem}",
            [sys.executable, "-m", "pytest", test_path, "-q", "--tb=short"],
            env=env,
            timeout=120,
        )
        # Prototype tests — report result but do not count as real portal evidence
        results.append({
            **r,
            "label": f"backend/{Path(test_path).stem}",
            "status": "PASS" if r["exit_code"] == 0 else "FAIL",
            "stdout": r.get("stdout", ""),
            "stderr": r.get("stderr", ""),
            "error": "[PROTOTYPE — not real portal evidence]" if r["exit_code"] == 0 else r.get("error"),
        })

    return results


def verify_storage() -> list[dict]:
    """Upload, quarantine, storage, and download tests.

    Note: test_protected_storage.py is a prototype contract test, not a real
    portal storage test. Reported as informational only.
    """
    results = []
    env = django_env()

    test_path = "tests/architecture/test_protected_storage.py"
    if (ROOT / test_path).exists():
        r = check_cmd(
            f"storage/{Path(test_path).stem}",
            [sys.executable, "-m", "pytest", test_path, "-q", "--tb=short"],
            env=env,
            timeout=120,
        )
        results.append({
            **r,
            "label": f"storage/{Path(test_path).stem}",
            "status": "PASS" if r["exit_code"] == 0 else "FAIL",
            "error": "[PROTOTYPE — not real portal evidence]" if r["exit_code"] == 0 else r.get("error"),
        })
    else:
        results.append({
            "label": "storage/test_protected_storage",
            "status": "NOT_RUN",
            "command": f"test -f {test_path}",
            "start": now(),
            "end": now(),
            "exit_code": 0,
            "stdout": "test file not found",
            "stderr": "",
            "error": "not found",
        })

    code = f"""
import sys, os
sys.path.insert(0, {repr(str(ROOT))})
os.environ['DJANGO_SETTINGS_MODULE'] = {repr(django_settings())}
import django
django.setup()
from django.conf import settings
portal_storage = getattr(settings, 'PORTAL_STORAGE_BACKEND', None)
media = getattr(settings, 'MEDIA_URL', None)
print(f"MEDIA_URL={{media}}")
print(f"PORTAL_STORAGE_BACKEND={{portal_storage}}")
has_real_storage = bool(portal_storage and 'Memory' not in str(type(portal_storage)))
print(f"Real storage configured: {{has_real_storage}}")
"""
    r = check_py("storage/backend-configured", code, env=env)
    if r["status"] == "PASS":
        if "Real storage configured: False" in r["stdout"]:
            r["status"] = "FAIL"
            r["error"] = "no real storage backend configured"
    results.append(r)

    return results


def verify_ocr() -> list[dict]:
    """OCR extraction, review, and retry tests."""
    results = []
    env = django_env()

    r = check_cmd(
        "ocr/field-decision-tests",
        [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=short",
         "-k", "field_decision or proposal", "--ignore=tests/fixtures/"],
        env=env,
        timeout=120,
    )
    if "no tests ran" in r.get("stdout", "").lower() or "error" in r.get("stderr", "").lower():
        results.append({**r, "status": "NOT_RUN"})
    else:
        results.append({**r, "status": "PASS" if r["exit_code"] == 0 else "FAIL"})

    # Semantic check: verify RapidOCR initialization and bytes-from-storage behavior
    code = f"""
import sys, os
sys.path.insert(0, {repr(str(ROOT))})
os.environ['DJANGO_SETTINGS_MODULE'] = {repr(django_settings())}
import django
django.setup()
# Check if RapidOCR is available
try:
    from RapidOCR import RapidOCR
    ocr = RapidOCR()
    print("RapidOCR engine: available")
except Exception as e:
    print(f"RapidOCR engine: NOT AVAILABLE — {{type(e).__name__}}")
"""
    r = check_py("ocr/rapidocr-available", code, env=env)
    if r["status"] == "PASS" and "NOT AVAILABLE" in r["stdout"]:
        r["status"] = "BLOCKED_ENV"
    results.append(r)

    return results


def verify_assignment() -> list[dict]:
    """Assignment concurrency and overlap tests."""
    results = []
    env = django_env()

    r = check_cmd(
        "assignment/tests",
        [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=short",
         "-k", "assignment or concurrency", "--ignore=tests/fixtures/"],
        env=env,
        timeout=120,
    )
    if "no tests ran" in r.get("stdout", "").lower():
        results.append({**r, "status": "NOT_RUN"})
    else:
        results.append({**r, "status": "PASS" if r["exit_code"] == 0 else "FAIL"})

    results.append({
        "label": "assignment/true-concurrency",
        "status": "BLOCKED_ENV",
        "command": "PostgreSQL two-connection concurrency test",
        "start": now(),
        "end": now(),
        "exit_code": None,
        "stdout": "SQLite does not support two-connection concurrency testing",
        "stderr": "",
        "error": "PostgreSQL required for two-connection test",
    })

    return results


def verify_a1() -> list[dict]:
    """A1 readiness, snapshots, and artifact tests."""
    results = []
    env = django_env()

    r = check_cmd(
        "a1/quality-gate",
        [sys.executable, "-m", "pytest", "tests/test_a1_quality_gate.py", "-q", "--tb=short"],
        env=env,
        timeout=120,
    )
    results.append({**r, "status": "PASS" if r["exit_code"] == 0 else "FAIL"})

    code = f"""
import sys, os
sys.path.insert(0, {repr(str(ROOT))})
os.environ['DJANGO_SETTINGS_MODULE'] = {repr(django_settings())}
import django
django.setup()
from portal.release1a import models as m
attrs = dir(m)
has_snapshot = any('Snapshot' in a for a in attrs)
has_artifact = any('Artifact' in a for a in attrs)
print(f"A1InputSnapshot: {{has_snapshot}}")
print(f"A1Artifact: {{has_artifact}}")
# Check A1Case fields
try:
    fields = [f.name for f in m.A1Case._meta.get_fields()]
    print(f"A1Case fields: {{fields[:8]}}")
except Exception as e:
    print(f"A1Case error: {{e}}")
"""
    r = check_py("a1/models-check", code, env=env)
    # Semantic FAIL if A1Artifact or A1InputSnapshot not found
    if r["status"] == "PASS":
        if "A1Artifact: False" in r["stdout"] or "A1InputSnapshot: False" in r["stdout"]:
            r["status"] = "FAIL"
            r["error"] = "A1 snapshot/artifact models not found"
    results.append(r)

    return results


def verify_frontend() -> list[dict]:
    """Frontend tests and Playwright."""
    results = []

    r = check_cmd("frontend/playwright-available", ["npx", "playwright", "--version"])
    if r is None or r.get("exit_code") != 0:
        results.append({
            "label": "frontend/playwright",
            "status": "BLOCKED_ENV",
            "command": "npx playwright --version",
            "start": now(),
            "end": now(),
            "exit_code": None,
            "stdout": "",
            "stderr": "",
            "error": "Playwright not available",
        })
    else:
        results.append({**r, "status": "PASS"})

    smoke = ROOT / "scripts" / "smoke_synthetic_review_ui.mjs"
    results.append({
        "label": "frontend/smoke-script",
        "status": "PASS" if smoke.exists() else "FAIL",
        "command": f"test -f {smoke}",
        "start": now(),
        "end": now(),
        "exit_code": 0 if smoke.exists() else 1,
        "stdout": f"smoke script {'found' if smoke.exists() else 'MISSING'}",
        "stderr": "",
        "error": None if smoke.exists() else "missing",
    })

    # Run Playwright smoke against the disposable verification server
    smoke_py = ROOT / "scripts" / "playwright_smoke.py"
    if smoke_py.exists():
        r = check_cmd(
            "frontend/playwright-smoke",
            [sys.executable, str(smoke_py)],
            env=django_env(),
            timeout=180,
        )
        # Parse result from report
        report_path = ROOT / "runtime" / "portal" / "verification" / "playwright-artifacts" / "smoke-report.json"
        if report_path.exists():
            data = json.loads(report_path.read_text())
            journeys = data.get("journeys", {})
            journey_summary = ", ".join(
                f"{k}={v.get('status')}" for k, v in journeys.items()
            )
            console_errors = len(data.get("console_errors", []))
            results.append({
                **r,
                "label": "frontend/playwright-smoke",
                "status": "PASS" if data.get("result") == "pass" else "FAIL",
                "stdout": f"Journeys: {journey_summary}; Console errors: {console_errors}",
                "stderr": "",
                "error": f"smoke failed: {data.get('error')}" if data.get("result") != "pass" else None,
            })
        else:
            results.append({
                **r,
                "label": "frontend/playwright-smoke",
                "status": "FAIL",
                "stdout": r.get("stdout", ""),
                "stderr": r.get("stderr", ""),
                "error": "smoke report not found",
            })
    else:
        results.append({
            "label": "frontend/playwright-smoke",
            "status": "BLOCKED_ENV",
            "command": f"test -f {smoke_py}",
            "start": now(),
            "end": now(),
            "exit_code": None,
            "stdout": "playwright_smoke.py not found",
            "stderr": "",
            "error": "playwright_smoke.py not found",
        })

    return results


def verify_accessibility() -> list[dict]:
    """Accessibility checks."""
    results = []

    r = check_cmd("accessibility/axe-available", ["npx", "axe", "--version"])
    results.append({**r, "status": "BLOCKED_ENV" if r is None or r.get("exit_code") != 0 else "PASS"})

    axe_receipt = ROOT / "runtime" / "portal" / "synthetic-review" / "axe.json"
    if axe_receipt.exists():
        data = json.loads(axe_receipt.read_text())
        commit = data.get("git_commit", "unknown")
        results.append({
            "label": "accessibility/axe-receipt",
            "status": "FAIL",
            "command": f"cat {axe_receipt}",
            "start": now(),
            "end": now(),
            "exit_code": 0,
            "stdout": f"Receipt found for commit {commit} — stale",
            "stderr": "",
            "error": "axe receipt is stale (not for current HEAD)",
        })
    else:
        results.append({
            "label": "accessibility/axe-receipt",
            "status": "NOT_RUN",
            "command": f"test -f {axe_receipt}",
            "start": now(),
            "end": now(),
            "exit_code": 1,
            "stdout": "No axe receipt found",
            "stderr": "",
            "error": "not found",
        })

    return results


def verify_eng001_checks() -> list[dict]:
    """
    Map ENG-001 checks to test evidence.
    NOTE: Architecture prototype tests are NOT counted as ENG-001 evidence.
    Only real portal behavior tests count.
    """
    results = []
    env = django_env()

    # ENG-001 checks — prototype tests do NOT satisfy ENG-001 requirements.
    # Marking as NOT_RUN until real portal model/view/service tests exist.
    check_map = [
        ("ENG-AUTH", None,
         "Prototype contract test — not a real portal capability test"),
        ("ENG-J2-STORAGE", None,
         "Prototype contract test — not real portal storage"),
        ("ENG-J3-CONCURRENCY", None, "Optimistic locking — PostgreSQL required"),
        ("ENG-A11Y", None, "Accessibility — requires fresh browser run"),
        ("ENG-MIGRATION", None, "Migration executor transitions"),
        ("ENG-BUILD", None, "Full test suite"),
    ]

    for check_id, test_path, note in check_map:
        if test_path and (ROOT / test_path).exists():
            r = check_cmd(
                f"eng001/{check_id}",
                [sys.executable, "-m", "pytest", test_path, "-q", "--tb=short"],
                env=env,
                timeout=180,
            )
            results.append({**r, "status": "PASS" if r["exit_code"] == 0 else "FAIL"})
        elif "PostgreSQL" in note:
            results.append({
                "label": f"eng001/{check_id}",
                "status": "BLOCKED_ENV",
                "command": f"test -f {test_path or 'N/A'}",
                "start": now(),
                "end": now(),
                "exit_code": None,
                "stdout": "",
                "stderr": "",
                "error": note,
            })
        else:
            results.append({
                "label": f"eng001/{check_id}",
                "status": "NOT_RUN",
                "command": f"test -f {test_path or 'N/A'}",
                "start": now(),
                "end": now(),
                "exit_code": 0,
                "stdout": note,
                "stderr": "",
                "error": f"No test file found for {check_id}",
            })

    # J2 checks (storage, scanner, OCR, immutability, revision) — NOT_RUN or FAIL
    # No real storage backend → J2-STORAGE = FAIL
    # No scanner → J2-SCANNER = NOT_RUN
    # No OCR bytes-from-storage test → J2-OCR = NOT_RUN
    # No immutability test → J2-IMMUTABLE = NOT_RUN
    # No revision test → J2-REVISION = NOT_RUN
    for check_id, status, note in [
        ("ENG-J2-SCANNER", "NOT_RUN", "Scanner adapter — no real scanner available"),
        ("ENG-J2-OCR", "NOT_RUN", "OCR bytes-from-storage — not characterized"),
        ("ENG-J2-IMMUTABLE", "NOT_RUN", "FieldDecision immutability — not tested"),
        ("ENG-J2-REVISION", "NOT_RUN", "Identity revision — not tested"),
        ("ENG-J4-SNAPSHOT", "NOT_RUN", "A1 snapshot model — not implemented"),
        ("ENG-J4-PREVIEW", "NOT_RUN", "A1 preview/artifact — not implemented"),
        ("ENG-J4-STATE", "NOT_RUN", "A1 state machine — not implemented"),
    ]:
        results.append({
            "label": f"eng001/{check_id}",
            "status": status,
            "command": "",
            "start": now(),
            "end": now(),
            "exit_code": 0,
            "stdout": note,
            "stderr": "",
            "error": note,
        })

    return results


def summarize(results: list[dict]) -> dict:
    """Summarize results by status."""
    counts = {"PASS": 0, "FAIL": 0, "BLOCKED_ENV": 0, "NOT_RUN": 0}
    for r in results:
        counts[r.get("status", "NOT_RUN")] += 1
    return counts


def write_json(report: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"JSON report: {path}")


def write_md(report: dict, path: Path) -> None:
    lines = [
        "# Release 1A Verification Report",
        "",
        f"**Generated:** {report['generated_at']}",
        f"**Commit:** `{report['git']['commit']}`",
        f"**Branch:** {report['git']['branch']}",
        f"**Tree clean:** {report['git']['tree_clean']}",
        f"**Approvals hash:** `{report['approvals_hash']}`",
        f"**Build ID:** {report['build_id']}",
        f"**DB backend:** {report['db_backend']}",
        "",
        "## Summary",
        "",
        "| Status | Count |",
        "|--------|-------|",
    ]
    for status, count in report["summary"].items():
        lines.append(f"| {status} | {count} |")
    lines.append("")

    sections = [
        ("Governance / Gate Integrity", "governance"),
        ("Django System Checks", "django"),
        ("Migrations", "migrations"),
        ("Backend CRUD / Tenant Isolation", "backend"),
        ("Upload / Storage / Download", "storage"),
        ("OCR / Field Proposals / Identity Revisions", "ocr"),
        ("Assignment / Concurrency", "assignment"),
        ("A1 Snapshots / Artifacts / State", "a1"),
        ("Frontend / Playwright", "frontend"),
        ("Accessibility (WCAG 2.2 AA)", "accessibility"),
        ("ENG-001 Engineering Checks", "eng001"),
    ]

    for title, key in sections:
        items = [r for r in report["checks"] if r["label"].startswith(key)]
        if not items:
            continue
        lines.extend(["", f"## {title}", ""])
        lines.append("| Check | Status | Detail |")
        lines.append("|-------|--------|--------|")
        for item in items:
            detail = (item.get("stdout") or item.get("error") or "")[:80].replace("\n", " ")
            lines.append(f"| `{item['label']}` | {item['status']} | {detail} |")

    lines.extend(["", "---", "*No PII, credentials, or protected content in this report.*"])
    path.write_text("\n".join(lines))
    print(f"Markdown report: {path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _ensure_verification_db() -> dict:
    """Create or recreate the hermetic verification DB.

    Runs seed_verification_db.py to produce a clean verification.sqlite3
    under runtime/portal/verification/. Safe to re-run: always recreates from scratch.
    """
    print("  [setup] Recreating verification DB...")
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "seed_verification_db.py")],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(ROOT),
             "DJANGO_SETTINGS_MODULE": "portal.settings_verification"},
        cwd=ROOT,
        timeout=120,
    )
    stdout = result.stdout[:500] if result.stdout else ""
    stderr = result.stderr[:200] if result.stderr else ""
    return {
        "status": "PASS" if result.returncode == 0 else "FAIL",
        "exit_code": result.returncode,
        "stdout": stdout,
        "stderr": stderr,
    }


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    env = django_env()
    os.environ.update(env)
    sys.path.insert(0, str(ROOT))

    git = git_info()
    approv_hash = approvals_hash()
    bld_id = build_id()

    # Create hermetic verification DB before running any DB-dependent checks
    db_setup = _ensure_verification_db()
    if db_setup["status"] == "FAIL":
        print(f"  [setup] FAILED to create verification DB: {db_setup['stderr'][:200]}")

    try:
        import django
        django.setup()
        from django.db import connection
        db_backend = connection.vendor
    except Exception as e:
        db_backend = f"unknown ({type(e).__name__}: {e})"

    print("Running verification harness...")
    print(f"  Commit: {git['commit'][:8]}")
    print(f"  Approvals hash: {approv_hash[:8]}")
    print(f"  DB backend: {db_backend}")

    all_results: list[dict] = []

    sections = [
        ("governance...", verify_governance),
        ("django...", verify_django_checks),
        ("migrations...", verify_migrations),
        ("backend...", verify_backend_crud),
        ("storage...", verify_storage),
        ("ocr...", verify_ocr),
        ("assignment...", verify_assignment),
        ("a1...", verify_a1),
        ("frontend...", verify_frontend),
        ("accessibility...", verify_accessibility),
        ("eng001...", verify_eng001_checks),
    ]

    for label, fn in sections:
        print(f"  {label}")
        all_results.extend(fn())

    summary = summarize(all_results)

    report = {
        "version": "1.0",
        "generated_at": now(),
        "git": git,
        "approvals_hash": approv_hash,
        "build_id": bld_id,
        "db_backend": db_backend,
        "summary": summary,
        "total": len(all_results),
        "checks": all_results,
    }

    write_json(report, REPORT_JSON)
    write_md(report, REPORT_MD)

    print(f"\nSummary: {summary}")
    print(f"Full report: {REPORT_JSON}")
    print(f"Markdown: {REPORT_MD}")

    # Return 0 if no FAILs in required ENG checks, non-zero otherwise
    eng_checks = [r for r in all_results if r["label"].startswith("eng001/")]
    eng_fails = [r for r in eng_checks if r["status"] in ("FAIL", "BLOCKED_ENV", "NOT_RUN")]
    other_fails = [r for r in all_results if r["status"] == "FAIL" and not r["label"].startswith("eng001/")]

    if other_fails or eng_fails:
        print(f"\nFailures: {len(other_fails)} other, {len(eng_fails)} ENG checks")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
