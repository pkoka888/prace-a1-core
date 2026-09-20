#!/usr/bin/env python3
"""Run the committed-source owned core journey acceptance.

Owns a disposable PostgreSQL cluster and a supervised runtime root inside the
exported source work tree, drives the canonical rehearsal lifecycle
(prepare → provision → start → smoke → workflow → stop → start → smoke → stop),
saves the journey evidence, and runs the strict persistence verifier
(``--profile core --require-identity``) against the restarted service. A1
stages stay optional (``--profile optional-a1``).

The owning environment is built from scratch: caller evidence overrides
(``JOURNEY_EVIDENCE_PATH``, ``ORG_PK``, ``WORKER_PK``, ``PRACE_DB_*``, ``PG*``
and friends) are never inherited into the run. This is the "clear inherited
evidence overrides" contract of the release reproducer.

It is also the seam the reproducer needs: the exported work tree is a
blob-only copy with no ``venv/`` and no ``.git``, so the rehearsal shell and
the OCR worker receive the host interpreter/gunicorn and the manifest commit
through the ``PRACE_REHEARSE_*`` / ``PRACE_RELEASE_MANIFEST_COMMIT``
environment seams added to ``rehearse_synthetic_site.sh``.

Exit codes:
  0 — journey + restart + strict verification all passed
  2 — configuration/evidence refusal: missing tool, invalid commit, missing
      mandatory evidence key, insecure/partial target or symlinked parent
  3 — a lifecycle phase (shell or owned PostgreSQL) failed
  4 — persistence verification failed (or its evidence was unusable)
  5 — the owned PostgreSQL cluster could not be stopped cleanly

Runtime directories are retained (owned and stopped for review) and a 0600
receipt records every phase's native exit code and log locations.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import secrets
import signal
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone

PG_BIN_DEFAULT = Path("/usr/lib/postgresql/18/bin")
EXIT_OK = 0
EXIT_CONFIG = 2
EXIT_PHASE = 3
EXIT_VERIFIER = 4
EXIT_POSTGRES_STOP = 5

PHASE_TERMINATION_BUDGET = 5.0

_SECRET_MARKERS = ("PASSWORD", "SECRET", "TOKEN", "APIKEY", "PRIVATE_KEY")

PHASE_SEQUENCE = (
    ("prepare", ("prepare",)),
    ("provision", ("provision",)),
    ("start", ("start",)),
    ("smoke", ("smoke",)),
    ("workflow", ("workflow",)),
    ("stop", ("stop",)),
    ("restart", ("start",)),
    ("smoke-after-restart", ("smoke",)),
    ("final-stop", ("stop",)),
)

BASE_MANDATORY_EVIDENCE_KEYS = frozenset({
    "ok", "profile", "organization_id", "worker_pk", "document_pk",
    "assignment_pk", "source_document_sha256", "required_stages", "stages",
})
CORE_STAGES_REQUIRED = frozenset({
    "login_redirect", "login_authenticated", "totp_completed",
    "worker_created", "document_uploaded", "document_associated",
    "ocr_proposals_confirmed", "missing_identity_confirmed",
    "address_confirmed", "identity_confirmed", "assignment_created",
    "assignment_corrected", "source_document_downloaded",
})
A1_EXTRA_STAGES = frozenset({
    "a1_prepared", "a1_draft_generated", "a1_pdf_downloaded",
    "a1_corrected_facts", "a1_regenerated", "regeneration_differs",
})
A1_EXTRA_EVIDENCE_KEYS = frozenset({
    "case_pk", "regenerated_case_pk", "pdf_sha256", "regen_sha256",
})

# Caller evidence / database identifiers the owned run must never inherit.
# build_env reads os.environ never: it composes the run environment from the
# named whitelist below, so forwarding collisions are structurally impossible.
_EVIDENCE_OVERRIDE_NAMES = frozenset({
    "JOURNEY_EVIDENCE_PATH", "ORG_PK", "WORKER_PK", "DOCUMENT_PK",
    "ASSIGNMENT_PK", "DOCUMENT_SHA256", "CONFIRMED_IDENTITY_FIELDS",
    "CORRECTED_ACTIVITY_LABEL", "CASE_PK", "REGENERATED_CASE_PK",
    "PDF_SHA256", "REGEN_SHA256", "PRACE_MIGRATION_DB_USER",
    "PRACE_MIGRATION_DB_PASSWORD",
})


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _die(rc: int, *lines: str) -> None:
    marker = {
        EXIT_CONFIG: "CORE_JOURNEY_BLOCKED",
        EXIT_PHASE: "CORE_JOURNEY_PHASE_FAILED",
        EXIT_VERIFIER: "CORE_JOURNEY_VERIFIER_FAILED",
        EXIT_POSTGRES_STOP: "CORE_JOURNEY_POSTGRES_STOP_UNCERTAIN",
    }.get(rc, "CORE_JOURNEY_FAILED")
    for line in lines:
        print(f"{marker}: {line}", file=sys.stderr)
    raise SystemExit(rc)


def reject_symlink_components(path: Path) -> None:
    """Refuse any symlink component from repo/runtime/portal/ down to `path`."""
    if path.is_symlink():
        _die(EXIT_CONFIG, f"refusing symlinked runtime path: {path}")
    for parent in (path, path.parent, path.parent.parent):
        if parent.is_symlink():
            _die(EXIT_CONFIG, f"refusing symlinked runtime path component: {parent}")


def private_dir(path: Path) -> None:
    if path.is_symlink():
        _die(EXIT_CONFIG, f"refusing symlinked private path: {path}")
    if not path.exists():
        path.mkdir(mode=0o700, parents=True)
        path.chmod(0o700)  # Clear any inherited setgid from a parent.
    if not path.is_dir():
        _die(EXIT_CONFIG, f"private path is not a directory: {path}")


def sanitize_environment(env):
    """Receipt-safe view: secret names reduce to set/unset presence markers.

    Execution variables keep their real values only in the subprocess env,
    never in the receipt. Mirrors the reproducer contract.
    """
    out = {}
    for name, value in env.items():
        upper = name.upper()
        if any(marker in upper for marker in _SECRET_MARKERS):
            out[name] = "set" if value else "unset"
        else:
            out[name] = value
    return out


def check_socket_path(root: Path, port: int) -> None:
    if len(os.fsencode(root / f".s.PGSQL.{port}")) >= 108:
        _die(EXIT_CONFIG,
             "PostgreSQL socket path is too long; keep the owned cluster "
             "under the real repo runtime/portal/, not inside the export")


def find_free_port(host: str = "127.0.0.1") -> int:
    """Pick an ephemeral free loopback port for the session."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return sock.getsockname()[1]


def real_home_dir() -> str:
    try:
        home = pwd.getpwuid(os.getuid()).pw_dir
    except KeyError:
        _die(EXIT_CONFIG, "cannot resolve the invoking user's home directory")
    return home


def build_env(*, work: Path, pg_root: Path, db_name: str, db_user: str,
              db_port: int, bind: str, commit: str, state: Path,
              python_bin: str, gunicorn: str, supervised: Path) -> dict:
    """Compose the run environment from scratch (target-isolation contract).

    Only the named keys are present; caller evidence/database variables are
    neither read nor forwarded. A missing interpreter or gunicorn raises.
    """
    if not python_bin or not (Path(python_bin).is_file()
                              and os.access(python_bin, os.X_OK)):
        _die(EXIT_CONFIG, f"interpreter unavailable for the run: {python_bin}")
    if not gunicorn or not (Path(gunicorn).is_file()
                            and os.access(gunicorn, os.X_OK)):
        _die(EXIT_CONFIG, f"gunicorn executable unavailable for the run: {gunicorn}")
    password_file = pg_root / "pgpass"
    if not password_file.is_file():
        fd = os.open(password_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.close(fd)
    binaries_path = Path(python_bin).parent
    # A real browser seed is a missing-check: without it the journey cannot
    # start. `state/home` is isolated, so the browsers path points at the
    # invoking user's cache outside that isolation.
    browsers = Path(real_home_dir()) / ".cache" / "ms-playwright"
    if not browsers.is_dir():
        _die(EXIT_CONFIG,
             f"Playwright browser cache not found: {browsers} (missing-check refusal)")
    secret_key = secrets.token_hex(32)
    env = {
        "PATH": f"{binaries_path}:/usr/bin:/bin",
        "HOME": str(state / "home"),
        "TMPDIR": str(state / "tmp"),
        "LC_ALL": "C.UTF-8",
        "PYTHONPATH": str(work),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PGPASSFILE": str(password_file),
        "PLAYWRIGHT_BROWSERS_PATH": str(browsers),
        "PRACE_DB_NAME": db_name,
        "PRACE_DB_USER": db_user,
        "PRACE_DB_HOST": str(pg_root),
        "PRACE_DB_PORT": str(db_port),
        "PRACE_DB_SSLMODE": "disable",
        "PRACE_SECRET_KEY": secret_key,
        "PRACE_RUNTIME_ROOT": str(supervised),
        "PRACE_RELEASE_MANIFEST": str(supervised / "release_manifest.json"),
        "PRACE_RELEASE_MANIFEST_SHA256": "",  # Refreshed after prepare.
        "PRACE_RELEASE_MANIFEST_COMMIT": commit,
        "PRACE_APP_BUILD_ID": f"g{commit[:12]}",
        "PRACE_ALLOWED_HOSTS": "localhost,127.0.0.1",
        "PRACE_BIND": bind,
        "PRACE_WORKERS": "1",
        "PRACE_COOKIE_SECURE": "false",
        "PRACE_READINESS_BUDGET_MS": "10000",
        "PRACE_REHEARSE_PYTHON_BIN": python_bin,
        "PRACE_REHEARSE_GUNICORN": gunicorn,
    }
    # The whitelist can never shadow an override name; build_env derives
    # everything from its parameters and reads no caller environment at all.
    for name in _EVIDENCE_OVERRIDE_NAMES:
        if name in env:
            _die(EXIT_CONFIG, f"build_env whitelist shadowed override name: {name}")
    return env


DEFAULT_OUTER_TIMEOUT = 3600.0
OUTER_TIMEOUT_LEAD = 1.0
CLEANUP_TIMEOUT = 4.0
CLEANUP_TERMINATION_BUDGET = 1.0


class JourneyInterrupted(Exception):
    """Internal cancellation raised by a signal or outer deadline."""

    def __init__(self, signum: int, reason: str, record: dict | None = None):
        super().__init__(reason)
        self.signum = signum
        self.reason = reason
        self.record = record


class Cancellation:
    def __init__(self):
        self.requested = False
        self.signum = None
        self.reason = None
        self.raise_on_signal = True

    def request(self, signum: int, reason: str) -> None:
        if not self.requested:
            self.signum = signum
            self.reason = reason
            self.requested = True

    def raise_if_requested(self) -> None:
        if self.requested:
            raise JourneyInterrupted(self.signum, self.reason)


def _signal_name(signum: int | None) -> str | None:
    if signum is None:
        return None
    try:
        return signal.Signals(signum).name
    except ValueError:
        return str(signum)


def _exception_payload(exc: BaseException) -> dict:
    message = str(exc)
    for marker in _SECRET_MARKERS:
        message = re.sub(
            rf"(?i)({re.escape(marker)}\s*[:=]\s*)(\S+)",
            rf"\1<redacted>",
            message,
        )
    return {"type": type(exc).__name__, "message": message[:500]}


def _exception_phase_record(name: str, argv: list, exc: BaseException) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "name": name,
        "argv": argv,
        "exit_code": 127,
        "started_at": now,
        "finished_at": now,
        "exception": _exception_payload(exc),
        "timed_out": False,
        "interrupted": False,
    }


def _terminate_process_group(proc: subprocess.Popen, grace: float) -> dict:
    """Terminate an owned process group, escalating only after a bounded wait."""
    try:
        if proc.poll() is not None:
            return {"outcome": "already_exited", "exit_code": proc.returncode}
    except Exception:
        return {"outcome": "uncertain", "exit_code": None}
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return {"outcome": "already_exited", "exit_code": proc.returncode}
    except OSError as exc:
        return {"outcome": "uncertain", "error": _exception_payload(exc)["message"]}
    try:
        code = proc.wait(timeout=max(0.0, grace))
        return {"outcome": "terminated", "exit_code": code}
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except OSError as exc:
            return {"outcome": "uncertain", "error": _exception_payload(exc)["message"]}
        try:
            code = proc.wait(timeout=max(0.0, grace))
            return {"outcome": "killed", "exit_code": code}
        except subprocess.TimeoutExpired:
            return {"outcome": "uncertain", "exit_code": None}


def run_phase(state: Path, steps_dir: Path, name: str, argv: list,
              cwd: Path, env: dict, timeout: float = 900,
              cancellation: Cancellation | None = None,
              allow_during_cancellation: bool = False,
              termination_budget: float = PHASE_TERMINATION_BUDGET):
    """Run one lifecycle phase, retaining native exit code and logs."""
    started_at = datetime.now(timezone.utc).isoformat()
    stdout_path = steps_dir / f"{name}.stdout"
    stderr_path = steps_dir / f"{name}.stderr"
    proc = None
    code = None
    timed_out = False
    interrupted = None
    termination = None
    with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
        try:
            if cancellation is not None and not allow_during_cancellation:
                cancellation.raise_if_requested()
            proc = subprocess.Popen(
                argv, cwd=cwd, env=env, stdout=stdout, stderr=stderr,
                start_new_session=True)
            deadline = time.monotonic() + max(0.0, timeout)
            while True:
                if cancellation is not None and not allow_during_cancellation:
                    cancellation.raise_if_requested()
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    timed_out = True
                    stderr.write(
                        f"run_core_journey: phase {name} exceeded {timeout:.0f}s\n".encode())
                    termination = _terminate_process_group(
                        proc, min(termination_budget, max(timeout, 0.0)))
                    code = 124
                    break
                try:
                    code = proc.wait(timeout=min(0.25, remaining))
                    break
                except subprocess.TimeoutExpired:
                    continue
        except JourneyInterrupted as exc:
            interrupted = exc
            code = 128 + exc.signum
            stderr.write(f"run_core_journey: phase {name} interrupted: {exc.reason}\n".encode())
            if proc is not None:
                termination = _terminate_process_group(proc, termination_budget)
        except KeyboardInterrupt:
            interrupted = JourneyInterrupted(signal.SIGINT, "keyboard interrupt")
            code = 130
            stderr.write(b"run_core_journey: phase interrupted by keyboard\n")
            if proc is not None:
                termination = _terminate_process_group(proc, termination_budget)
        except OSError as exc:
            stderr.write(f"{type(exc).__name__}: {exc}\n".encode())
            code = 127
        except BaseException:
            if proc is not None and proc.poll() is None:
                termination = _terminate_process_group(proc, termination_budget)
            raise
    stdout_path.chmod(0o600)
    stderr_path.chmod(0o600)
    finished_at = datetime.now(timezone.utc).isoformat()
    record = {
        "name": name, "argv": argv, "exit_code": code,
        "started_at": started_at, "finished_at": finished_at,
        "stdout_log": str(stdout_path), "stderr_log": str(stderr_path),
        "stdout_sha256": digest(stdout_path.read_bytes()),
        "stderr_sha256": digest(stderr_path.read_bytes()),
        "timed_out": timed_out,
        "interrupted": interrupted is not None,
    }
    if termination is not None:
        record["termination"] = termination
    if interrupted is not None:
        record["interruption"] = {
            "signal": interrupted.signum,
            "signal_name": _signal_name(interrupted.signum),
            "reason": interrupted.reason,
        }
    print(f"run_core_journey: {name}: exit {code}", flush=True)
    if interrupted is not None:
        interrupted.record = record
        raise interrupted
    return code, record


def parse_journey_evidence(stdout: bytes, profile: str):
    """Parse workflow phase stdout into a validated evidence dict.

    Returns ``(evidence, errors)``; errors is a non-empty list when the
    evidence is missing mandatory result keys (missing-check refusal)."""
    start = stdout.find(b"{")
    end = stdout.rfind(b"}")
    if start == -1 or end == -1:
        return None, ["workflow phase stdout carried no JSON evidence"]
    try:
        evidence = json.loads(stdout[start:end + 1].decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return None, [f"workflow phase stdout was not valid JSON: {exc}"]
    if not isinstance(evidence, dict):
        return None, ["workflow evidence is not a JSON object"]
    errors = []
    if evidence.get("ok") is not True:
        errors.append("evidence.ok is not true")
    if evidence.get("profile") != profile:
        errors.append(f"evidence.profile {evidence.get('profile')!r} != {profile!r}")
    for key in BASE_MANDATORY_EVIDENCE_KEYS:
        if key not in evidence:
            errors.append(f"missing mandatory evidence key: {key}")
    for key in ("organization_id", "worker_pk", "document_pk", "assignment_pk"):
        if evidence.get(key) is None or evidence.get(key) == "":
            errors.append(f"mandatory evidence value is empty: {key}")
    source_sha256 = evidence.get("source_document_sha256")
    if not isinstance(source_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", source_sha256):
        errors.append("source_document_sha256 is not a lowercase SHA-256")
    stages = evidence.get("stages")
    if not isinstance(stages, dict):
        errors.append("evidence.stages is not a JSON object")
    else:
        expected_stages = set(CORE_STAGES_REQUIRED)
        if profile == "optional-a1":
            expected_stages.update(A1_EXTRA_STAGES)
        required_stages = evidence.get("required_stages")
        if not isinstance(required_stages, list):
            errors.append("evidence.required_stages is not a JSON array")
        elif not all(isinstance(stage, str) for stage in required_stages):
            errors.append("evidence.required_stages contains a non-string entry")
        else:
            if len(set(required_stages)) != len(required_stages):
                errors.append("evidence.required_stages contains duplicates")
            missing_stages = expected_stages - set(required_stages)
            extra_stages = set(required_stages) - expected_stages
            if missing_stages:
                errors.append("required_stages omits: " + ", ".join(sorted(missing_stages)))
            if extra_stages:
                errors.append("required_stages contains unexpected: " + ", ".join(sorted(extra_stages)))
        for stage_name in sorted(expected_stages):
            stage = stages.get(stage_name)
            if not isinstance(stage, dict):
                errors.append(f"missing required stage: {stage_name}")
                continue
            if stage.get("stage") != stage_name:
                errors.append(f"required stage {stage_name} has a mismatched stage name")
            if stage.get("ok") is not True:
                errors.append(f"required stage {stage_name} did not pass")
        if profile == "core":
            skipped = stages.get("a1_skipped")
            if not isinstance(skipped, dict):
                errors.append("core evidence is missing stages.a1_skipped")
            elif skipped.get("stage") != "a1_skipped" or skipped.get("ok") is not True:
                errors.append("core evidence stages.a1_skipped did not pass")
        downloaded = stages.get("source_document_downloaded")
        if isinstance(downloaded, dict) and downloaded.get("ok") is True:
            if downloaded.get("document_pk") != evidence.get("document_pk"):
                errors.append("source_document_downloaded.document_pk does not match evidence.document_pk")
            if downloaded.get("sha256") != source_sha256:
                errors.append("source_document_downloaded.sha256 does not match evidence source_document_sha256")
        identity = stages.get("identity_confirmed")
        if isinstance(identity, dict):
            if identity.get("ok") is not True:
                errors.append("identity_confirmed.ok is not true")
            fields = identity.get("confirmed_fields")
            if not isinstance(fields, dict) or not fields:
                errors.append("identity_confirmed.confirmed_fields is empty")
            if str(identity.get("worker_pk")) != str(evidence.get("worker_pk")):
                errors.append("identity_confirmed.worker_pk does not match evidence.worker_pk")
        else:
            errors.append("stages.identity_confirmed is missing")
        corrected = stages.get("assignment_corrected")
        if isinstance(corrected, dict):
            if corrected.get("ok") is not True:
                errors.append("assignment_corrected.ok is not true")
            label = corrected.get("corrected_activity")
            if not isinstance(label, str) or not label.strip():
                errors.append("assignment_corrected.corrected_activity is empty")
            if str(corrected.get("assignment_pk")) != str(evidence.get("assignment_pk")):
                errors.append("assignment_corrected.assignment_pk does not match")
        else:
            errors.append("stages.assignment_corrected is missing")
    if profile == "optional-a1":
        for key in A1_EXTRA_EVIDENCE_KEYS:
            value = evidence.get(key)
            if not isinstance(value, (str, int)) or (isinstance(value, str) and not value.strip()) or (isinstance(value, int) and value <= 0):
                errors.append(f"missing mandatory A1 evidence key: {key}")
    return evidence, errors


def retain_evidence(state: Path, evidence: dict) -> Path:
    evidence_path = state / "journey-evidence.json"
    evidence_path.write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n")
    os.chmod(evidence_path, 0o600)
    return evidence_path


VERIFIER_CORE_CHECKS = frozenset({
    "worker_found", "document_found", "assignment_found",
    "worker_document_relationship", "worker_assignment_relationship",
    "document_sha256", "assignment_corrected_value", "identity_confirmed",
})
VERIFIER_OPTIONAL_A1_CHECKS = frozenset({
    "case_found", "regenerated_case_found", "original_artifact",
    "regenerated_artifact",
})


def _check_passed(value) -> bool:
    if value is True:
        return True
    if not isinstance(value, dict):
        return False
    if "ok" in value:
        return value.get("ok") is True
    if "matches" in value:
        return value.get("matches") is True
    if "found" in value:
        return (value.get("found") is True
                and value.get("file_exists") is True
                and value.get("sha256_matches") is True)
    return False


def parse_verifier_result(stdout: bytes, profile: str):
    """Parse and validate the post-restart verifier's machine-readable result."""
    start = stdout.find(b"{")
    end = stdout.rfind(b"}")
    if start == -1 or end == -1:
        return None, ["verifier stdout carried no JSON result"]
    try:
        result = json.loads(stdout[start:end + 1].decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return None, [f"verifier stdout was not valid JSON: {exc}"]
    if not isinstance(result, dict):
        return None, ["verifier result is not a JSON object"]
    errors = []
    if result.get("ok") is not True:
        errors.append("verifier.ok is not true")
    if result.get("profile") != profile:
        errors.append(f"verifier.profile {result.get('profile')!r} != {profile!r}")
    checks = result.get("checks")
    if not isinstance(checks, dict):
        return None, errors + ["verifier.checks is not a JSON object"]
    expected = set(VERIFIER_CORE_CHECKS)
    if profile == "optional-a1":
        expected.update(VERIFIER_OPTIONAL_A1_CHECKS)
    for name in sorted(expected):
        if name not in checks:
            errors.append(f"missing mandatory verifier check: {name}")
        elif not _check_passed(checks[name]):
            errors.append(f"verifier check did not pass: {name}")
    return result, errors


def run_core_journey(*, work: Path, repo_root: Path, state: Path, commit: str,
                     profile: str, pg_bin: Path, pg_port: int | None,
                     http_port: int | None, timeout: float = 900.0,
                     outer_timeout: float | None = DEFAULT_OUTER_TIMEOUT) -> int:
    """Owned core journey acceptance; returns the process exit code.

    The returned receipt is failure-first: success is assigned only after the
    journey, strict verifier result, application shutdown and PostgreSQL
    shutdown are all known. SIGTERM, SIGINT and the optional outer deadline
    request cooperative cancellation; owned phase process groups are drained
    with a bounded graceful termination before escalation.
    """
    if timeout <= 0:
        _die(EXIT_CONFIG, f"phase timeout must be positive, got {timeout!r}")
    if outer_timeout is not None and outer_timeout <= 0:
        _die(EXIT_CONFIG,
             f"outer timeout must be positive or null, got {outer_timeout!r}")

    started_at = datetime.now(timezone.utc).isoformat()
    user = pwd.getpwuid(os.getuid()).pw_name
    pgid = f"pg-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{secrets.token_hex(8)}"
    db_name = f"prace_core_journey_{secrets.token_hex(6)}"
    runid = secrets.token_hex(8)
    env = None
    compiled_env = None
    exit_code = EXIT_PHASE
    primary_success = False
    start_phase_attempted = False
    postgres_start_attempted = False
    phases = []
    supervised = None
    data = None
    shell = None
    steps_dir = None
    pg_root = None
    pg_http_port = None
    bind = None
    cancellation = Cancellation()
    interruption = None
    unexpected_exception = None
    failure = None
    verifier_summary = None
    app_shutdown = {
        "attempted": False, "outcome": "not_attempted", "exit_code": None,
        "phase": None, "record": None,
    }
    postgres_shutdown = {
        "attempted": False, "outcome": "not_attempted", "exit_code": None,
        "phase": None, "record": None,
    }
    cleanup_exceptions = []

    def record_phase(code, record, exc=None):
        if record is None:
            record = _exception_phase_record(
                "unknown", [], exc or RuntimeError("phase failed without a record"))
        phases.append(record)
        if exc is not None:
            raise exc
        return code, record

    def run_tracked(name, argv, *, allow_during_cancellation=False,
                    phase_timeout=None, termination_budget=PHASE_TERMINATION_BUDGET):
        record = None
        try:
            code, record = run_phase(
                state, steps_dir, name, argv, cwd=work, env=compiled_env,
                timeout=timeout if phase_timeout is None else phase_timeout,
                cancellation=cancellation,
                allow_during_cancellation=allow_during_cancellation,
                termination_budget=termination_budget)
        except JourneyInterrupted as exc:
            record = exc.record or _exception_phase_record(name, argv, exc)
            phases.append(record)
            raise
        except BaseException as exc:
            record = _exception_phase_record(name, argv, exc)
            phases.append(record)
            raise
        phases.append(record)
        return code, record

    def run_postgres(name, argv, *, allow_during_cancellation=False,
                     phase_timeout=None):
        code, record = run_tracked(
            name, argv, allow_during_cancellation=allow_during_cancellation,
            phase_timeout=phase_timeout)
        return code, record

    def shutdown_outcome(record, phase_name):
        if record is None:
            return "uncertain"
        if record.get("exit_code") == 0:
            return "stopped"
        termination = record.get("termination") or {}
        if record.get("timed_out") or termination.get("outcome") == "uncertain":
            return "uncertain"
        return "failed"

    def install_signal_handlers():
        previous = {}
        def handle(signum, frame):
            if signum == signal.SIGALRM:
                reason = "outer timeout exceeded"
            elif signum == signal.SIGINT:
                reason = "interrupt signal received"
            else:
                reason = "termination signal received"
            cancellation.request(signum, reason)
            if cancellation.raise_on_signal:
                raise JourneyInterrupted(signum, reason)
        for signum in (signal.SIGTERM, signal.SIGINT, signal.SIGALRM):
            try:
                previous[signum] = signal.getsignal(signum)
                signal.signal(signum, handle)
            except (ValueError, OSError):
                continue
        return previous

    def restore_signal_handlers(previous):
        for signum, handler in previous.items():
            try:
                signal.signal(signum, handler)
            except (ValueError, OSError):
                pass

    previous_handlers = {}
    timer_installed = False
    try:
        previous_handlers = install_signal_handlers()
        if outer_timeout is not None:
            signal.setitimer(signal.ITIMER_REAL, outer_timeout)
            timer_installed = True

        # Required exported-source shape and tool availability: refuse before
        # any mkdir, initdb or run (missing-check contract).
        for tool in ("initdb", "pg_ctl", "createdb", "psql"):
            if not ((pg_bin / tool).is_file() and os.access(pg_bin / tool, os.X_OK)):
                _die(EXIT_CONFIG, f"required PostgreSQL binary unavailable in {pg_bin}: {tool}")
        shell = work / "scripts" / "rehearse_synthetic_site.sh"
        verifier_script = work / "scripts" / "rehearse_verify_persistence.py"
        for required, label in ((shell, "rehearse_synthetic_site.sh"),
                                (verifier_script, "rehearse_verify_persistence.py"),
                                (work / "scripts/build_release_manifest.py",
                                 "build_release_manifest.py"),
                                (work / "manage.py", "manage.py")):
            if not required.is_file():
                _die(EXIT_CONFIG, f"required exported source file missing: {required}")
        if not re.fullmatch(r"[0-9a-f]{40}", commit):
            _die(EXIT_CONFIG, f"commit {commit!r} is not a 40-hex SHA")
        if Path.cwd().resolve() != work:
            _die(EXIT_CONFIG, f"cwd {Path.cwd()} is not the exported source tree {work}")

        # Owned PostgreSQL placement stays short (Unix socket < 108 bytes); the
        # export work tree is far longer, so the cluster lives under the real repo
        # runtime/portal/ mirroring scripts/test_document_intake.py.
        pg_parent = repo_root / "runtime" / "portal"
        reject_symlink_components(pg_parent)
        pg_root = pg_parent / pgid
        pg_http_port = pg_port if pg_port is not None else find_free_port()
        check_socket_path(pg_root, pg_http_port)
        http_port = http_port if http_port is not None else find_free_port()
        bind = f"127.0.0.1:{http_port}"

        private_dir(state)
        for child in ("home", "tmp"):
            private_dir(state / child)
        steps_dir = state / "journey"
        private_dir(steps_dir)
        private_dir(pg_parent)
        private_dir(pg_root)
        data = pg_root / "db"
        supervised = work / "runtime" / "portal" / f"supervised-journey-{runid}"

        code, _ = run_postgres("initdb", [str(pg_bin / "initdb"), "-D", str(data),
                                         "--auth=trust", "--no-locale",
                                         "--encoding=UTF8"])
        if code != 0:
            _die(EXIT_PHASE, "owned PostgreSQL initdb failed")
        postgres_start_attempted = True
        code, _ = run_postgres("pg-start", [str(pg_bin / "pg_ctl"), "-D", str(data),
                                           "-l", str(pg_root / "server.log"), "-o",
                                           f"-k {pg_root} -p {pg_http_port} -c listen_addresses=''",
                                           "-t", "60", "-w", "start"])
        if code != 0:
            _die(EXIT_PHASE, f"owned PostgreSQL start failed on port {pg_http_port}")
        code, _ = run_postgres("createdb", [str(pg_bin / "createdb"), "-h", str(pg_root),
                                           "-p", str(pg_http_port), db_name])
        if code != 0:
            _die(EXIT_PHASE, f"createdb failed for {db_name}")

        python_bin = sys.executable
        gunicorn = str(Path(python_bin).parent / "gunicorn")
        env = build_env(work=work, pg_root=pg_root, db_name=db_name,
                        db_user=user, db_port=pg_http_port, bind=bind,
                        commit=commit, state=state, python_bin=python_bin,
                        gunicorn=gunicorn, supervised=supervised)
        compiled_env = dict(env)

        for name, args in PHASE_SEQUENCE:
            if name in ("start", "restart"):
                start_phase_attempted = True
            argv = ["bash", str(shell), *args]
            if name == "workflow":
                argv += ["--profile", profile]
            code, _ = run_tracked(name, argv)
            if code != 0:
                _die(EXIT_PHASE, f"lifecycle phase {name} failed with exit {code}")
            if name == "prepare":
                sha_file = supervised / ".release_manifest.sha256"
                try:
                    sha = sha_file.read_text().strip()
                except OSError as exc:
                    _die(EXIT_CONFIG, f"release manifest SHA sidecar unreadable: {exc}")
                if not re.fullmatch(r"[0-9a-f]{64}", sha):
                    _die(EXIT_CONFIG,
                         f"release manifest SHA invalid after prepare: {sha!r}")
                compiled_env["PRACE_RELEASE_MANIFEST_SHA256"] = sha

        evidence, errors = parse_journey_evidence(
            (steps_dir / "workflow.stdout").read_bytes(), profile)
        if errors:
            refute = "\n".join(f"- {error}" for error in errors)
            _die(EXIT_CONFIG,
                 f"journey evidence failed mandatory-key checks ({profile} profile):\n{refute}")
        evidence_path = retain_evidence(state, evidence)

        verifier_env = dict(compiled_env)
        verifier_env.update({
            "DJANGO_SETTINGS_MODULE": "portal.settings_supervised_synthetic",
            "JOURNEY_EVIDENCE_PATH": str(evidence_path),
            "PRACE_RELEASE_MANIFEST_SHA256": compiled_env["PRACE_RELEASE_MANIFEST_SHA256"],
        })
        verifier_argv = [python_bin, str(verifier_script), "--profile", profile,
                         "--require-identity"]
        code, verifier_record = run_tracked("verifier", verifier_argv)
        if code != 0:
            _die(EXIT_VERIFIER, f"persistence verifier failed with exit {code}")
        verifier_result, verifier_errors = parse_verifier_result(
            (steps_dir / "verifier.stdout").read_bytes(), profile)
        if verifier_errors:
            refute = "\n".join(f"- {error}" for error in verifier_errors)
            _die(EXIT_VERIFIER,
                 f"persistence verifier result failed mandatory checks ({profile} profile):\n{refute}")
        verifier_summary = {
            "ok": True,
            "profile": profile,
            "checks": {
                name: _check_passed(verifier_result["checks"].get(name))
                for name in sorted(set(VERIFIER_CORE_CHECKS) | (
                    VERIFIER_OPTIONAL_A1_CHECKS if profile == "optional-a1" else set()))
            },
        }
        primary_success = True
    except JourneyInterrupted as exc:
        interruption = {
            "signal": exc.signum,
            "signal_name": _signal_name(exc.signum),
            "reason": exc.reason,
        }
        exit_code = 128 + exc.signum
        failure = {"type": "JourneyInterrupted", **interruption}
    except KeyboardInterrupt:
        interruption = {
            "signal": signal.SIGINT,
            "signal_name": _signal_name(signal.SIGINT),
            "reason": "keyboard interrupt",
        }
        exit_code = 130
        failure = {"type": "KeyboardInterrupt", **interruption}
    except SystemExit:
        raise
    except BaseException as exc:
        unexpected_exception = _exception_payload(exc)
        exit_code = EXIT_PHASE
        failure = {"type": "Exception", **unexpected_exception}
    finally:
        # Do not let a second signal turn cleanup into another primary failure.
        cancellation.raise_on_signal = False
        if timer_installed:
            try:
                signal.setitimer(signal.ITIMER_REAL, 0)
            except (ValueError, OSError):
                pass

        if compiled_env is not None and start_phase_attempted \
                and app_shutdown["outcome"] == "not_attempted":
            argv = ["bash", str(shell), "stop"]
            try:
                code, record = run_tracked(
                    "cleanup-stop", argv, allow_during_cancellation=True,
                    phase_timeout=CLEANUP_TIMEOUT,
                    termination_budget=CLEANUP_TERMINATION_BUDGET)
                app_shutdown.update({
                    "attempted": True, "exit_code": code,
                    "phase": "cleanup-stop", "record": record,
                    "outcome": shutdown_outcome(record, "cleanup-stop"),
                })
            except BaseException as exc:
                record = _exception_phase_record("cleanup-stop", argv, exc)
                phases.append(record)
                app_shutdown.update({
                    "attempted": True, "exit_code": 127,
                    "phase": "cleanup-stop", "record": record,
                    "outcome": "uncertain",
                })
                cleanup_exceptions.append(_exception_payload(exc))

        if postgres_start_attempted and data is not None:
            argv = [str(pg_bin / "pg_ctl"), "-D", str(data),
                    "-m", "fast", "-t", "60", "-w", "stop"]
            try:
                code, record = run_postgres(
                    "pg-stop", argv, allow_during_cancellation=True,
                    phase_timeout=CLEANUP_TIMEOUT)
                postgres_shutdown.update({
                    "attempted": True, "exit_code": code,
                    "phase": "pg-stop", "record": record,
                    "outcome": shutdown_outcome(record, "pg-stop"),
                })
            except BaseException as exc:
                record = _exception_phase_record("pg-stop", argv, exc)
                phases.append(record)
                postgres_shutdown.update({
                    "attempted": True, "exit_code": 127,
                    "phase": "pg-stop", "record": record,
                    "outcome": "uncertain",
                })
                cleanup_exceptions.append(_exception_payload(exc))

        # The final-stop phase is the normal application shutdown. A failed or
        # interrupted final-stop is followed by the idempotent cleanup-stop above.
        if app_shutdown["outcome"] == "not_attempted" and start_phase_attempted:
            app_shutdown["outcome"] = "uncertain"
        if postgres_shutdown["outcome"] == "not_attempted" and postgres_start_attempted:
            postgres_shutdown["outcome"] = "uncertain"

        if primary_success:
            if app_shutdown["outcome"] != "stopped":
                exit_code = EXIT_PHASE
            elif postgres_shutdown["outcome"] != "stopped":
                exit_code = EXIT_POSTGRES_STOP
            else:
                exit_code = EXIT_OK
        elif interruption is None and exit_code == EXIT_OK:
            exit_code = EXIT_PHASE

        app_stopped = app_shutdown["outcome"] == "stopped"
        postgres_stopped = postgres_shutdown["outcome"] == "stopped"
        uncertain = []
        failures = []
        if app_shutdown["outcome"] == "uncertain":
            uncertain.append({"component": "app", **app_shutdown})
        elif app_shutdown["outcome"] == "failed":
            failures.append({"component": "app", **app_shutdown})
        if postgres_shutdown["outcome"] == "uncertain":
            uncertain.append({"component": "postgres", **postgres_shutdown})
        elif postgres_shutdown["outcome"] == "failed":
            failures.append({"component": "postgres", **postgres_shutdown})
        shutdown_certain = not uncertain
        shutdown_successful = app_stopped and postgres_stopped
        status = "success" if exit_code == EXIT_OK else (
            "interrupted" if interruption is not None else "failed")

        receipt = {
            "schema_version": "1.0",
            "ok": exit_code == EXIT_OK,
            "status": status,
            "profile": profile,
            "commit_sha": commit,
            "repo_root": str(repo_root),
            "export_cwd": str(work),
            "pg_root": str(pg_root) if pg_root is not None else None,
            "db_name": db_name,
            "db_user": user,
            "db_host": str(pg_root) if pg_root is not None else None,
            "db_port": pg_http_port,
            "http_bind": bind,
            "runtime_root": str(supervised) if supervised is not None else None,
            "environment": sanitize_environment(compiled_env or {}),
            "phases": phases,
            "started_at": started_at,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "exit_code": exit_code,
            "outer_timeout": outer_timeout,
            "interruption": interruption,
            "exception": unexpected_exception,
            "failure": failure,
            "verifier": verifier_summary,
            "app_shutdown": app_shutdown,
            "postgres_shutdown": postgres_shutdown,
            "app_stopped": app_stopped,
            "postgres_stopped": postgres_stopped,
            "shutdown_successful": shutdown_successful,
            "shutdown_certain": shutdown_certain,
            "shutdown_outcomes_known": not uncertain,
            "shutdown_failures": failures,
            "uncertain_shutdown": uncertain,
            "cleanup_exceptions": cleanup_exceptions,
        }
        if compiled_env is not None and compiled_env.get("PRACE_RELEASE_MANIFEST_SHA256"):
            receipt["manifest_sha256"] = compiled_env["PRACE_RELEASE_MANIFEST_SHA256"]
        if state.exists():
            receipt_path = state / "core-journey.json"
            try:
                receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
                os.chmod(receipt_path, 0o600)
                print(f"run_core_journey: receipt {receipt_path}", flush=True)
            except BaseException as exc:
                print(f"run_core_journey: could not write receipt: {exc}",
                      file=sys.stderr, flush=True)
        restore_signal_handlers(previous_handlers)
    return exit_code


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", required=True,
                        help="40-hex SHA of the exported source (manifest git_commit)")
    parser.add_argument("--repo-root", required=True, type=Path,
                        help="Real repository root (owned PostgreSQL lives under "
                             "its runtime/portal/ to keep the Unix socket path short)")
    parser.add_argument("--state", required=True, type=Path,
                        help="Private state directory for receipts, logs and the retained supervisor")
    parser.add_argument("--profile", choices=("core", "optional-a1"), default="core",
                        help="Journey profile (default: core; A1 stays optional)")
    parser.add_argument("--pg-bin", type=Path, default=PG_BIN_DEFAULT,
                        help="PostgreSQL utility directory (default: %(default)s)")
    parser.add_argument("--pg-port", type=int, default=None,
                        help="Owned PostgreSQL port (default: a free loopback port)")
    parser.add_argument("--http-port", type=int, default=None,
                        help="Owned gunicorn bind port (default: a free loopback port)")
    parser.add_argument("--timeout", type=float, default=900.0,
                        help="Per-phase timeout in seconds (default: %(default)s)")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if not re.fullmatch(r"[0-9a-f]{40}", args.commit):
        _die(EXIT_CONFIG, f"commit {args.commit!r} is not a 40-hex SHA")
    old_umask = os.umask(0o077)
    try:
        work = Path.cwd().resolve()
        if not (work / "scripts").is_dir():
            _die(EXIT_CONFIG,
                 f"current working directory is not an exported source tree: {work}")
        return run_core_journey(
            work=work, repo_root=args.repo_root.resolve(), state=args.state.resolve(),
            commit=args.commit, profile=args.profile, pg_bin=args.pg_bin.resolve(),
            pg_port=args.pg_port, http_port=args.http_port, timeout=args.timeout)
    finally:
        os.umask(old_umask)


if __name__ == "__main__":
    raise SystemExit(main())