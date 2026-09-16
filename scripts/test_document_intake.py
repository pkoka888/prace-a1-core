#!/usr/bin/env python3
"""Run synthetic Django tests in an ephemeral in-project PostgreSQL cluster.

No host services, operator databases or credentials are used. PostgreSQL has
no TCP listener; browser labels launch their own loopback HTTP test server.
Invoke with venv/bin/python scripts/test_document_intake.py.
"""
import argparse
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
BIN = Path("/usr/lib/postgresql/18/bin")
SETTINGS = ("portal.settings_document_tests", "portal.settings_browser_tests")
DEFAULT_LABELS = (
    "tests.document_web.test_intake", "tests.document_web.test_inbox",
    "tests.document_web.test_field_review", "tests.document_web.test_identity_review",
    "tests.document_web.test_legacy_reconciliation", "tests.document_web.test_identity",
    "tests.document_web.test_a1_exports", "tests.document_web.test_a1_cohort_exports",
    "tests.document_web.test_a1_input_publication", "tests.document_web.test_input_bundle_bo",
    "tests.document_web.test_a1_drafts", "tests.document_web.test_a1_generation_access",
    "tests.document_web.test_a1_generation_confirmation", "tests.document_web.test_a1_drafts_postgres",
    "tests.document_web.test_a1_exports_postgres", "tests.document_web.test_identity_postgres",
    "tests.document_web.test_readiness_postgres", "tests.test_j4_service",
)


def django_label(value):
    if not re.fullmatch(r"tests(?:\.[A-Za-z_]\w*)+", value):
        raise argparse.ArgumentTypeError("use an explicit dotted label under tests")
    return value


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--settings", choices=SETTINGS, default=SETTINGS[0])
    parser.add_argument("labels", nargs="*", type=django_label,
                        help="Django test labels; omission retains the document suite")
    return parser.parse_args(argv)


def check_socket_path(root):
    if len(os.fsencode(root / ".s.PGSQL.55439")) >= 108:
        raise ValueError("Unix socket path is too long; use a shorter in-project source checkout")


def run_owned_cluster(args):
    for binary in (BIN / "initdb", BIN / "pg_ctl"):
        if not binary.is_file() or not os.access(binary, os.X_OK):
            raise ValueError(f"Required local PostgreSQL executable unavailable: {binary}")
    runtime = ROOT
    for component in ("runtime", "portal"):
        runtime = runtime / component
        if runtime.is_symlink():
            raise ValueError("Refusing symlinked runtime directory")
        runtime.mkdir(mode=0o700, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="pg-", dir=runtime))
    root.chmod(0o700)
    # libpq requires a regular password file. A private empty file avoids both
    # device-file warnings and fallback to the operator's ~/.pgpass.
    password_file = root / "pgpass"
    password_fd = os.open(password_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(password_fd)
    data = root / "db"
    labels = args.labels or list(DEFAULT_LABELS)
    # Caller target variables never authorize or select a database for this run.
    env = {name: value for name, value in os.environ.items()
           if not name.startswith(("PRACE_", "DOCUMENT_TEST_PG_", "PG"))}
    env.update(DJANGO_SETTINGS_MODULE=args.settings, PYTHONPATH=str(ROOT),
               PGPASSFILE=str(password_file),
               DOCUMENT_TEST_PG_SOCKET=str(root),
               DOCUMENT_TEST_PG_USER=pwd.getpwuid(os.getuid()).pw_name,
               DOCUMENT_TEST_PG_NAME="prace_document_tests", DOCUMENT_TEST_PG_PORT="55439")
    receipt = {"settings": args.settings, "labels": labels, "phases": [],
               "started_at": datetime.now(timezone.utc).isoformat()}
    print(f"Owned PostgreSQL run: {root}", flush=True)

    def run_phase(name, argv):
        started_at = datetime.now(timezone.utc).isoformat()
        print(f"Running {name}; logs: {root / (name + '.stdout.log')}", flush=True)
        with (root / f"{name}.stdout.log").open("wb") as stdout, \
                (root / f"{name}.stderr.log").open("wb") as stderr:
            try:
                code = subprocess.run(argv, cwd=ROOT, env=env, stdout=stdout,
                                      stderr=stderr, check=False).returncode
            except OSError as exc:
                stderr.write(f"{type(exc).__name__}: {exc}\n".encode())
                code = 127
        receipt["phases"].append({"name": name, "command": argv, "exit_code": code,
                                  "started_at": started_at,
                                  "finished_at": datetime.now(timezone.utc).isoformat()})
        return code

    code = 2
    start_attempted = False
    stopped = False
    try:
        check_socket_path(root)
        code = run_phase("initdb", [str(BIN / "initdb"), "-D", str(data),
                                   "--auth=trust", "--no-locale", "--encoding=UTF8"])
        if code == 0:
            start_attempted = True
            # The socket belongs to this newly created cluster; TCP is disabled.
            code = run_phase("start", [str(BIN / "pg_ctl"), "-D", str(data),
                                      "-l", str(root / "server.log"), "-o",
                                      f"-k {root} -p 55439 -c listen_addresses=''",
                                      "-t", "60", "-w", "start"])
        if code == 0:
            code = run_phase("django", [sys.executable, "manage.py", "test", *labels,
                                       "--noinput", "-v", "1"])
    except KeyboardInterrupt:
        code = 130
    finally:
        # A failed pg_ctl start can still leave a server running. Always attempt
        # shutdown of this exact newly initialized data directory after start.
        if start_attempted:
            stop_code = run_phase("stop", [str(BIN / "pg_ctl"), "-D", str(data),
                                          "-m", "fast", "-t", "60", "-w", "stop"])
            stopped = stop_code == 0
            if code == 0:
                code = stop_code
        # Keep failure evidence (including the data directory). A successful run
        # retains its logs/receipt and removes only its stopped disposable DB.
        if code == 0 and stopped:
            try:
                shutil.rmtree(data)
            except OSError as exc:
                code = 2
                receipt["cleanup_error"] = type(exc).__name__
        receipt.update(exit_code=code, stopped=stopped,
                       finished_at=datetime.now(timezone.utc).isoformat())
        (root / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        print(f"Receipt: {root / 'receipt.json'}", flush=True)
    return code if code >= 0 else 128 - code


def main(argv=None):
    args = parse_args(argv)
    old_umask = os.umask(0o077)
    try:
        return run_owned_cluster(args)
    except (ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    finally:
        os.umask(old_umask)


if __name__ == "__main__":
    raise SystemExit(main())
