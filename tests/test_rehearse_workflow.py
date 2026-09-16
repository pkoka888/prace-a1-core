"""End-to-end authenticated workflow test for the rehearsal script.

Bounded exercise of the rehearsal script's lifecycle, the real-browser
authenticated journey, and the restart-survival of the synthetic
record set. The test invokes the canonical workflow command
(``scripts/rehearse_synthetic_site.sh workflow``) so the CLI and
pytest share one outcome contract.

The test:

1. runs ``prepare`` against an isolated runtime root.
2. runs ``provision`` so ``operator.json`` carries the jan_planner
   role and TOTP secret.
3. runs the real-browser journey through ``workflow`` (the
   documented CLI subcommand).
4. restarts gunicorn and confirms the worker and case still
   resolve through the supervised-synthetic database.
5. stops gunicorn before the runtime directory is removed; the
   test-owned process is always stopped even on failure.

The test deliberately does NOT use ``@pytest.mark.django_db`` —
every database action runs in a subprocess against the supervised
SQLite, and the pytest-django test database is unrelated to this
journey. Without ``DJANGO_SETTINGS_MODULE`` the test still runs
because pytest.ini adds the repo root to ``sys.path`` and the
journey script subprocess sets ``DJANGO_SETTINGS_MODULE``
explicitly.

Per AGENTS.md ``Default delivery unit``, the journey is the actual
acceptance path. Service calls, force-login and helper-side admin
membership are explicitly forbidden.
"""
from __future__ import annotations

import json
import os
import secrets
import shutil
import socket
import subprocess
import uuid
from pathlib import Path

import pytest

from scripts.disposable_pg_guard import exclusive_cleanup_sql, psql_env, verify_target


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "rehearse_synthetic_site.sh"
BROWSER_HELPER = REPO_ROOT / "tests" / "_rehearse_workflow_browser.py"
PYTHON_BIN = REPO_ROOT / "venv" / "bin" / "python"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def test_postgres_env_fails_closed_without_explicit_target(monkeypatch):
    monkeypatch.setenv("PRACE_WORKFLOW_PG", "1")
    for name in POSTGRES_TARGET_ENV:
        monkeypatch.delenv(name, raising=False)
    base = {"PATH": "/usr/bin:/bin"}
    with pytest.raises(RuntimeError, match=r"missing: PRACE_DB_NAME"):
        _postgres_env(base)
    monkeypatch.setenv("PRACE_DB_NAME", "prace_synthetic_test")
    monkeypatch.setenv("PRACE_DB_USER", "prace_synth_app")
    monkeypatch.setenv("PRACE_DB_PASSWORD", "synthetic-test-password")
    monkeypatch.setenv("PRACE_DB_HOST", "127.0.0.1")
    monkeypatch.setenv("PRACE_DB_PORT", "5432")
    env = _postgres_env(base)
    assert env["PRACE_DB_PASSWORD"] == "synthetic-test-password"
    assert env["PRACE_DB_NAME"] == "prace_synthetic_test"


def test_postgres_env_forwards_migration_credential_pair(monkeypatch):
    monkeypatch.setenv("PRACE_WORKFLOW_PG", "1")
    for name in POSTGRES_TARGET_ENV:
        monkeypatch.setenv(name, {
            "PRACE_DB_NAME": "prace_synthetic_test",
            "PRACE_DB_USER": "prace_synth_app",
            "PRACE_DB_PASSWORD": "synthetic-test-password",
            "PRACE_DB_HOST": "127.0.0.1",
            "PRACE_DB_PORT": "5432",
        }[name])
    monkeypatch.setenv("PRACE_MIGRATION_DB_USER", "prace_migrator")
    monkeypatch.setenv("PRACE_MIGRATION_DB_PASSWORD", "migrator-password")
    env = _postgres_env({"PATH": "/usr/bin:/bin"})
    assert env["PRACE_MIGRATION_DB_USER"] == "prace_migrator"
    assert env["PRACE_MIGRATION_DB_PASSWORD"] == "migrator-password"


def test_postgres_env_omits_migration_credentials_when_unset(monkeypatch):
    monkeypatch.setenv("PRACE_WORKFLOW_PG", "1")
    for name in POSTGRES_TARGET_ENV:
        monkeypatch.setenv(name, {
            "PRACE_DB_NAME": "prace_synthetic_test",
            "PRACE_DB_USER": "prace_synth_app",
            "PRACE_DB_PASSWORD": "synthetic-test-password",
            "PRACE_DB_HOST": "127.0.0.1",
            "PRACE_DB_PORT": "5432",
        }[name])
    monkeypatch.delenv("PRACE_MIGRATION_DB_USER", raising=False)
    monkeypatch.delenv("PRACE_MIGRATION_DB_PASSWORD", raising=False)
    env = _postgres_env({"PATH": "/usr/bin:/bin"})
    assert "PRACE_MIGRATION_DB_USER" not in env
    assert "PRACE_MIGRATION_DB_PASSWORD" not in env


def _run_script(args, env, *, timeout=600):
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        cwd=str(REPO_ROOT), env=env,
        capture_output=True, text=True, timeout=timeout,
    )


def _pid_matches_launch_record(workflow_root: Path, pid: int) -> bool:
    """Re-run the canonical ownership checks before signaling a PID.

    Mirrors scripts/rehearse_synthetic_site.sh verify_pid_ownership:
    the launch record (.gunicorn.cmdline) must exist, the /proc start
    time must match .gunicorn.started_at, and the live cmdline must
    mention gunicorn and portal.wsgi:application. A reused pidfile can
    therefore never point the fallback signal at an unrelated process.
    """
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as fh:
            cmdline = fh.read().decode("utf-8", "replace")
    except OSError:
        return False
    if "gunicorn" not in cmdline or "portal.wsgi:application" not in cmdline:
        return False
    started_at_file = workflow_root / ".gunicorn.started_at"
    cmdline_file = workflow_root / ".gunicorn.cmdline"
    if not (started_at_file.is_file() and cmdline_file.is_file()):
        return False
    recorded = cmdline_file.read_text()
    if "runtime_root=" not in recorded:
        return False
    recorded_started = started_at_file.read_text().strip()
    if not recorded_started.isdigit():
        return False
    try:
        proc_started = os.stat(f"/proc/{pid}").st_mtime
    except OSError:
        return False
    return int(proc_started) == int(recorded_started)


def _stop_workflow_gunicorn(workflow_root: Path, env: dict) -> int:
    """Stop the test-owned gunicorn process; returns the exit code.

    The canonical ``stop`` command runs FIRST: it refuses to signal a
    pidfile whose pid does not match the recorded launch (bind,
    runtime root, start time, cmdline). Only when the canonical stop
    did not bring the process down does this helper fall back to a
    direct signal, and that fallback repeats the ownership checks
    itself before signaling.
    """
    r = _run_script(["stop"], env, timeout=90)
    pidfile = workflow_root / "gunicorn.pid"
    pid = None
    if pidfile.is_file():
        try:
            pid = int(pidfile.read_text().strip())
        except (ValueError, OSError):
            pid = None
    if pid is None:
        return r.returncode
    try:
        os.kill(pid, 0)
    except OSError:
        return r.returncode
    if not _pid_matches_launch_record(workflow_root, pid):
        return r.returncode
    import time as _time
    try:
        os.kill(pid, 15)  # SIGTERM
    except OSError:
        return r.returncode
    deadline = 30
    start = _time.monotonic()
    while _time.monotonic() - start < deadline:
        try:
            os.kill(pid, 0)
        except OSError:
            return r.returncode
        _time.sleep(0.5)
    else:
        try:
            os.kill(pid, 9)  # SIGKILL
        except OSError:
            pass
    return r.returncode


@pytest.fixture
def workflow_root():
    name = f"supervised-workflow-pytest-{uuid.uuid4().hex[:8]}"
    root = REPO_ROOT / "runtime" / "portal" / name
    root.mkdir(mode=0o700)
    yield root
    shutil.rmtree(str(root), ignore_errors=True)


POSTGRES_TARGET_ENV = (
    "PRACE_DB_NAME",
    "PRACE_DB_USER",
    "PRACE_DB_PASSWORD",
    "PRACE_DB_HOST",
    "PRACE_DB_PORT",
)

# Optional target attributes forwarded verbatim when present so the
# workflow run and settings module observe the same connection contract
# (TLS mode and CA root are silently dropped today, which makes an
# encrypted target look plaintext to the subprocess).
POSTGRES_OPTIONAL_ENV = (
    "PRACE_DB_SSLMODE",
    "PRACE_DB_SSLROOTCERT",
)

# Command-scoped migration credentials forwarded verbatim when present so
# the workflow's ``manage.py migrate`` session uses the schema-owner role
# the operator exported, exactly like the shell rehearsal path.
POSTGRES_MIGRATION_ENV = (
    "PRACE_MIGRATION_DB_USER",
    "PRACE_MIGRATION_DB_PASSWORD",
)


def _postgres_env(base: dict, runtime_root: Path | None = None) -> dict:
    """If PRACE_WORKFLOW_PG=1 is set, require an explicit PostgreSQL
    target from the caller's environment.

    Mirrors the settings-module all-or-none contract: a partial or
    defaulted target (including an invented password) is never used
    silently. This makes a wrong credential or host fail closed with an
    actionable message instead of a cryptic auth error from a guessed
    value.

    When a runtime root is supplied, the assembled environment also
    carries the disposable-target ownership record and marker that the
    cleanup guard requires: the record proves this test-owned run claims
    the target as disposable, so an arbitrary database can never be swept.
    """
    if os.environ.get("PRACE_WORKFLOW_PG", "").strip() != "1":
        return base
    missing = [name for name in POSTGRES_TARGET_ENV if not os.environ.get(name)]
    if missing:
        raise RuntimeError(
            "PRACE_WORKFLOW_PG=1 requires an explicit PostgreSQL target "
            f"(missing: {', '.join(missing)}). Export the full PRACE_DB_* set, "
            "including PRACE_DB_PASSWORD; no defaults are applied."
        )
    env = dict(base)
    for name in POSTGRES_TARGET_ENV:
        env[name] = os.environ[name]
    for name in POSTGRES_OPTIONAL_ENV:
        if os.environ.get(name):
            env[name] = os.environ[name]
    for name in POSTGRES_MIGRATION_ENV:
        if os.environ.get(name):
            env[name] = os.environ[name]
    if runtime_root is not None:
        _write_disposable_ownership(runtime_root, env)
        env["PRACE_DISPOSABLE_TARGET"] = "1"
    return env


def _write_disposable_ownership(runtime_root: Path, env: dict) -> None:
    """Record the ownership of the explicitly configured target as a
    disposable, test-owned database. The record is written as private
    project files (0600) next to the runtime root so the cleanup guard
    can prove the target was provisioned for this run and is not an
    arbitrary database."""
    import json as _json
    record = {
        "database": env["PRACE_DB_NAME"],
        "host": env.get("PRACE_DB_HOST", ""),
        "port": env.get("PRACE_DB_PORT", ""),
        "disposable": True,
    }
    record_path = runtime_root / "disposable-pg.ownership.json"
    record_path.write_text(_json.dumps(record))
    record_path.chmod(0o600)
    env["PRACE_DISPOSABLE_OWNERSHIP"] = str(record_path)


@pytest.fixture
def workflow_env(workflow_root):
    port = _free_port()
    base = {
        "PATH": os.environ["PATH"],
        "HOME": os.environ.get("HOME", "/tmp"),
        "PRACE_RUNTIME_ROOT": str(workflow_root),
        "PRACE_SECRET_KEY": "workflow-pytest-"
                            + secrets.token_urlsafe(32),
        "PRACE_ALLOWED_HOSTS": "localhost,127.0.0.1",
        "PRACE_BIND": f"127.0.0.1:{port}",
        "PRACE_WORKERS": "1",
        "PRACE_REHEARSE_TIMEOUT": "60",
        "PRACE_READINESS_BUDGET_MS": "10000",
    }
    return _postgres_env(base, runtime_root=workflow_root)


def test_workflow_prepare_provision_browser_workflow_restart_persistence(
        workflow_root, workflow_env):
    """prepare → provision → start → browser workflow → stop →
    restart → query-after-restart → stop. Always stops the
    test-owned gunicorn before the runtime directory is removed."""
    gunicorn_started = False
    try:
        # 1. prepare (full migrate + collectstatic). ~45 s.
        r = _run_script(["prepare"], workflow_env, timeout=180)
        assert r.returncode == 0, (
            f"prepare failed:\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}")
        # 2. provision (operator + organization + jan_planner + TOTP).
        r = _run_script(["provision"], workflow_env, timeout=60)
        assert r.returncode == 0, (
            f"provision failed:\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}")
        operator = json.loads(
            (workflow_root / "operator.json").read_text())
        assert operator["membership_role"] == "jan_planner"
        assert operator["password"]
        assert operator["mfa"]["secret"]

        # 3. start gunicorn.
        r = _run_script(["start"], workflow_env, timeout=60)
        assert r.returncode == 0, (
            f"start failed:\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}")
        gunicorn_started = True

        # 4. Invoke the canonical workflow subcommand so the CLI and
        # the pytest test share the same outcome contract. The script
        # sets PYTHONPATH/cwd before invoking the browser helper, so
        # the standalone and the pytest entrypoint are equivalent.
        r = _run_script(["workflow"], workflow_env, timeout=300)
        # Preserve bounded error categories even though fixture cleanup removes
        # private runtime logs. Never copy request bodies or credentials.
        log_path = workflow_root / "logs" / "gunicorn.log"
        log_text = log_path.read_text() if log_path.is_file() else ""
        error_categories = [name for name in (
            "OperationalError", "database is locked", "IntegrityError",
            "PermissionDenied", "WORKER TIMEOUT",
        ) if name in log_text]
        assert r.returncode == 0, (
            f"workflow command failed (rc={r.returncode}):\n"
            f"SERVER_ERROR_CATEGORIES: {error_categories}\n"
            f"STDOUT:\n{r.stdout[:4000]}\nSTDERR:\n{r.stderr[:2000]}")
        if not r.stdout.strip():
            raise AssertionError(
                f"workflow command produced empty stdout:\n"
                f"STDERR:\n{r.stderr[:1000]}")
        journey = json.loads(r.stdout)
        assert journey.get("ok") is True, (
            "workflow evidence.ok is False; required stages failed: "
            f"{journey.get('failed_stages', journey['stages'])}\n"
            f"{json.dumps(journey['stages'], indent=2)}")
        for stage in journey["required_stages"]:
            assert journey["stages"].get(stage, {}).get("ok") is True, (
                f"required stage {stage!r} did not pass:\n"
                f"{json.dumps(journey['stages'][stage], indent=2)}")
        worker_pk = journey["worker_pk"]
        document_pk = journey["document_pk"]
        assignment_pk = journey["assignment_pk"]
        # Protected source-document bytes must be verified, not just a hash.
        assert journey["stages"]["source_document_downloaded"]["ok"] is True
        assert journey["source_document_sha256"], (
            "journey evidence must carry the source-document SHA-256")
        if journey.get("profile") == "optional-a1":
            case_pk = journey["case_pk"]
            regenerated_case_pk = journey["regenerated_case_pk"]
            first_sha256 = journey["stages"]["a1_pdf_downloaded"]["sha256"]
            regen_sha256 = journey["stages"]["regeneration_differs"][
                "regenerated_sha256"]
            # Correction/regeneration evidence must be present and truthful.
            assert first_sha256 != regen_sha256, (
                "regeneration must produce different PDF bytes; observed "
                f"same sha256 {first_sha256}")
            assert regenerated_case_pk != case_pk, (
                "regeneration must create a new A1Case row")
        else:
            # Core profile: A1 stages are intentionally skipped.
            assert journey["case_pk"] is None
            assert journey["regenerated_case_pk"] is None
        # The TOTP code never appears in evidence.
        assert "totp_code_used" not in journey, (
            "TOTP code leaked into journey evidence")
        assert "password" not in journey, (
            "operator password leaked into journey evidence")

        # 5. stop gunicorn.
        r = _run_script(["stop"], workflow_env, timeout=60)
        assert r.returncode == 0, (
            f"stop failed:\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}")
        gunicorn_started = False

        # 5b. Sparse-input data path. A separate subprocess loads the
        # supervised-synthetic settings and exercises the canonical
        # services against the same SQLite the browser journey used.
        # This demonstrates that (a) the jan_planner membership (not
        # operator) survives provision, (b) an unknown-optional-facts
        # sparse worker still saves, (c) prepare_a1 returns a BLOCKED
        # case for it, and (d) reserve_application_draft raises the
        # canonical DraftInputBlocked naming the missing facts. The
        # rows live in the same DB that is restarted next, so nothing
        # here creates replacements or helper-side memberships.
        dp_env = dict(workflow_env)
        dp_env["PYTHONPATH"] = str(REPO_ROOT)
        dp = subprocess.run(
            [str(PYTHON_BIN),
             str(REPO_ROOT / "tests" / "_rehearse_workflow_data_path.py"),
             str(workflow_root)],
            env=dp_env, cwd=str(REPO_ROOT),
            capture_output=True, text=True, timeout=120,
        )
        assert dp.returncode == 0, (
            f"sparse data path failed (rc={dp.returncode}):\n"
            f"STDOUT:\n{dp.stdout}\nSTDERR:\n{dp.stderr}")
        dp_evidence = json.loads(dp.stdout.strip())
        assert dp_evidence.get("ok") is True, (
            f"sparse data path evidence not ok:\n"
            f"{json.dumps(dp_evidence['stages'], indent=2)}")
        sparse_reserve = dp_evidence["stages"]["sparse_reserve_blocked"]
        assert sparse_reserve.get("ok") is True, (
            f"sparse reserve must block:\n{json.dumps(sparse_reserve, indent=2)}")
        assert sparse_reserve.get("exception_class") == "DraftInputBlocked", (
            f"unexpected exception class {sparse_reserve.get('exception_class')}")
        assert sparse_reserve.get("message"), (
            "sparse reserve block must carry an actionable message")

        # 6. restart gunicorn.
        r = _run_script(["start"], workflow_env, timeout=60)
        assert r.returncode == 0, (
            f"start after stop failed:\nSTDOUT:\n{r.stdout}\n"
            f"STDERR:\n{r.stderr}")
        gunicorn_started = True

        # 7. query-after-restart. The subprocess reloads the
        # supervised-synthetic settings and queries the supervised
        # SQLite for the worker, document, assignment and both cases
        # captured during the browser journey, and verifies the
        # published artifact bytes on disk still match the PDF the
        # operator downloaded. Nothing may be replaced after restart:
        # the same row pks and the same bytes must come back.
        query_env = dict(workflow_env)
        query_env["PYTHONPATH"] = str(REPO_ROOT)
        query_env["DJANGO_SETTINGS_MODULE"] = (
            "portal.settings_supervised_synthetic")
        query_env["PRACE_RELEASE_MANIFEST"] = (
            str(workflow_root / "release_manifest.json"))
        query_env["PRACE_RELEASE_MANIFEST_SHA256"] = (
            (workflow_root / ".release_manifest.sha256").read_text().strip())
        query_env["WORKER_PK"] = str(worker_pk)
        query_env["DOCUMENT_PK"] = str(document_pk)
        query_env["ASSIGNMENT_PK"] = str(assignment_pk)
        query_env["ORG_PK"] = str(operator["organization_id"])
        query_env["DOCUMENT_SHA256"] = journey["source_document_sha256"]
        query_env["PROFILE"] = journey.get("profile", "core")
        if journey.get("profile") == "optional-a1":
            query_env["CASE_PK"] = str(case_pk)
            query_env["REGENERATED_CASE_PK"] = str(regenerated_case_pk)
            query_env["PDF_SHA256"] = first_sha256
            query_env["REGEN_SHA256"] = regen_sha256
        proc = subprocess.run(
            [str(PYTHON_BIN), "-c", """
import os, json, hashlib
from pathlib import Path
import django; django.setup()
from django.conf import settings
from portal.release1a.models import Worker, A1Case, Document, Assignment
from portal.release1a.document_storage import document_storage


def case_artifact(pk, expect_sha256, org_pk):
    case = A1Case.objects.filter(
        pk=int(pk), organization_id=int(org_pk)).first()
    if case is None:
        return {'found': False}
    ref = case.artifact_reference or {}
    key = ref.get('key')
    if not key:
        return {'found': True, 'key': None, 'file_exists': False}
    pdf = Path(settings.DOCUMENT_STORAGE_ROOT) / 'j4' / key / 'artifact.pdf'
    file_exists = pdf.is_file()
    sha256_matches = False
    if file_exists:
        sha256_matches = (
            hashlib.sha256(pdf.read_bytes()).hexdigest() == expect_sha256)
    return {'found': True, 'key': key, 'file_exists': file_exists,
            'sha256_matches': sha256_matches}


def stored_source_bytes(document_pk, org_pk, journey_sha):
    document = Document.objects.filter(
        pk=int(document_pk), organization_id=int(org_pk)).first()
    if document is None:
        return {'found': False}
    version = document.documentversion_set.order_by(
        '-version_number').first()
    if version is None:
        return {'found': True, 'version_found': False}
    with document_storage().open(version.opaque_key, 'rb') as stream:
        data = stream.read()
    stored_sha = hashlib.sha256(data).hexdigest()
    return {'found': True, 'version_found': True,
            'stored_matches_recorded': stored_sha == version.sha256,
            'stored_matches_journey': stored_sha == journey_sha,
            'size': len(data)}


profile = os.environ.get('PROFILE', 'core')
result = {
    'worker_found': Worker.objects.filter(
        pk=int(os.environ['WORKER_PK'])).exists(),
    'document_found': Document.objects.filter(
        pk=int(os.environ['DOCUMENT_PK'])).exists(),
    'assignment_found': Assignment.objects.filter(
        pk=int(os.environ['ASSIGNMENT_PK'])).exists(),
    'source_document': stored_source_bytes(
        os.environ['DOCUMENT_PK'], os.environ['ORG_PK'],
        os.environ['DOCUMENT_SHA256']),
}
if profile == 'optional-a1':
    result['case_found'] = A1Case.objects.filter(
        pk=int(os.environ['CASE_PK'])).exists()
    result['regenerated_case_found'] = A1Case.objects.filter(
        pk=int(os.environ['REGENERATED_CASE_PK'])).exists()
    result['original_artifact'] = case_artifact(
        os.environ['CASE_PK'], os.environ['PDF_SHA256'],
        os.environ['ORG_PK'])
    result['regenerated_artifact'] = case_artifact(
        os.environ['REGENERATED_CASE_PK'], os.environ['REGEN_SHA256'],
        os.environ['ORG_PK'])
print(json.dumps(result))
"""],
            env=query_env,
            cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=90,
        )
        assert proc.returncode == 0, (
            f"query-after-restart failed (rc={proc.returncode}):\n"
            f"STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
        query = json.loads(proc.stdout.strip().splitlines()[-1])
        assert query.get("worker_found") is True, (
            f"worker {worker_pk} not found after restart: {query}")
        assert query.get("document_found") is True, (
            f"document {document_pk} not found after restart: {query}")
        assert query.get("assignment_found") is True, (
            f"assignment {assignment_pk} not found after restart: {query}")
        source_document = query.get("source_document") or {}
        assert source_document.get("found") is True, (
            f"document {document_pk} missing after restart: {query}")
        assert source_document.get("stored_matches_recorded") is True, (
            f"stored source bytes no longer match the recorded version "
            f"hash after restart: {source_document}")
        assert source_document.get("stored_matches_journey") is True, (
            f"stored source bytes differ from the journey-downloaded "
            f"bytes after restart: {source_document}")
        if journey.get("profile") == "optional-a1":
            case_pk = journey["case_pk"]
            regenerated_case_pk = journey["regenerated_case_pk"]
            assert query.get("case_found") is True, (
                f"case {case_pk} not found after restart: {query}")
            assert query.get("regenerated_case_found") is True, (
                f"regenerated case {regenerated_case_pk} not found after "
                f"restart: {query}")
            original_artifact = query.get("original_artifact") or {}
            assert original_artifact.get("file_exists") is True, (
                f"original artifact file missing after restart: "
                f"{original_artifact}")
            assert original_artifact.get("sha256_matches") is True, (
                f"original artifact bytes changed after restart: "
                f"{original_artifact}")
            regenerated_artifact = query.get("regenerated_artifact") or {}
            assert regenerated_artifact.get("sha256_matches") is True, (
                f"regenerated artifact bytes missing or changed after "
                f"restart: {regenerated_artifact}")
    finally:
        # Always stop the test-owned gunicorn before the runtime
        # directory is removed by the workflow_root fixture.
        if gunicorn_started:
            rc = _stop_workflow_gunicorn(workflow_root, workflow_env)
            assert rc == 0, (
                f"final stop returned {rc}; runtime root may contain "
                f"a stale gunicorn process")
        # PostgreSQL-backed runs share the target database across
        # runtime roots. Remove the test operator so the next
        # invocation can provision a fresh one.
        if workflow_env.get("PRACE_DB_NAME"):
            _cleanup_pg_operator(workflow_env)


def _cleanup_pg_operator(env: dict) -> None:
    """Remove the workflow test operator from the configured test target.

    Uses the explicit PRACE_DB_* target tuple from the environment and
    runs scoped DELETEs as the configured test role. Never touches a
    hardcoded database name, never uses `sudo … TRUNCATE` as the
    cluster superuser, and never runs against the operator database.

    A table-wide DELETE is a destructive operation, so this never
    runs before the disposable-target guard has positively verified an
    exclusively-owned disposable target: the guard demands
    ``PRACE_DISPOSABLE_TARGET=1`` plus a provisioning ownership record
    naming this exact database, refuses an operator database by exact
    name, and blocks when the cluster is not reachable or the lock is
    already held. The advisory lock is then held by the SAME session that
    performs the DELETEs (``exclusive_cleanup_sql``), so a concurrent run
    cannot interleave between the verification and the teardown.
    """
    pg_env = psql_env(env)
    verdict = verify_target(pg_env)
    assert verdict.get("ok"), (
        f"refusing PostgreSQL cleanup: {verdict.get('reason')}")
    lock_key_value = verdict.get("lock_key")
    assert isinstance(lock_key_value, int), (
        f"refusing PostgreSQL cleanup: guard verdict missing 'lock_key' "
        f"(verdict={verdict})")
    delete_sql = (
        "DELETE FROM release1a_fielddecision;"
        " DELETE FROM release1a_reviewtask;"
        " DELETE FROM release1a_a1generationconfirmation;"
        " DELETE FROM release1a_a1case;"
        " DELETE FROM release1a_documentregionassociation;"
        " DELETE FROM release1a_workeridentityrevision;"
        " DELETE FROM release1a_release1aacceptance;"
        " DELETE FROM release1a_release1areviewsession;"
        " DELETE FROM release1a_membership;"
        " DELETE FROM release1a_organization;"
        " DELETE FROM account_emailaddress;"
        " DELETE FROM mfa_authenticator;"
        " DELETE FROM socialaccount_socialaccount;"
        " DELETE FROM auth_user_user_permissions;"
        " DELETE FROM auth_user_groups;"
        " DELETE FROM auth_user;"
    )
    sql = exclusive_cleanup_sql(delete_sql, lock_key_value=lock_key_value)
    subprocess.run(
        ["psql", "-h", env.get("PRACE_DB_HOST", "127.0.0.1"),
         "-p", env.get("PRACE_DB_PORT", "5432"),
         "-U", env["PRACE_DB_USER"], "-d", env["PRACE_DB_NAME"],
         "-v", "ON_ERROR_STOP=1", "-c", sql],
        env=pg_env, capture_output=True, timeout=30, check=True,
    )
