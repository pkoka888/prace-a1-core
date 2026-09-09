#!/usr/bin/env python3
"""Run synthetic Django tests in an ephemeral in-project PostgreSQL cluster.

No host services, system databases, credentials or network listeners are used.
Invoke with venv/bin/python scripts/test_document_intake.py.
"""
import os
from pathlib import Path
import pwd
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BIN = Path("/usr/lib/postgresql/18/bin")


def main():
    runtime = ROOT / "runtime"
    runtime.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="doc-pg-", dir=runtime) as temporary:
        root = Path(temporary)
        data = root / "db"
        env = {**os.environ, "DJANGO_SETTINGS_MODULE": "portal.settings_document_tests",
               "DOCUMENT_TEST_PG_SOCKET": str(root), "DOCUMENT_TEST_PG_USER": pwd.getpwuid(os.getuid()).pw_name}
        subprocess.run([str(BIN/"initdb"), "-D", str(data), "--auth=trust", "--no-locale", "--encoding=UTF8"],
                       check=True, stdout=subprocess.DEVNULL, cwd=ROOT)
        started = False
        try:
            subprocess.run([str(BIN/"pg_ctl"), "-D", str(data), "-l", str(root/"server.log"),
                            "-o", f"-k {root} -p 55439 -c listen_addresses=''", "-w", "start"], check=True, stdout=subprocess.DEVNULL)
            started = True
            return subprocess.run([sys.executable, "manage.py", "test", "tests.document_web.test_intake", "tests.document_web.test_inbox", "tests.document_web.test_identity", "tests.document_web.test_identity_postgres", "tests.document_web.test_readiness_postgres", "tests.test_j4_service", "--noinput", "-v", "1"],
                                  cwd=ROOT, env=env).returncode
        finally:
            if started:
                subprocess.run([str(BIN/"pg_ctl"), "-D", str(data), "-m", "immediate", "-w", "stop"], check=True, stdout=subprocess.DEVNULL)


if __name__ == "__main__":
    raise SystemExit(main())
