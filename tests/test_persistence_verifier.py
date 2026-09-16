"""Regression tests for rehearse_verify_persistence.py.

Tests the actual execution paths, not just settings existence:
- F2: core profile runs without A1/PDF env vars
- F3: document hash is compared against the expected value
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "rehearse_verify_persistence.py"


def _run(args, env):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        env={**os.environ, **env},
        capture_output=True,
        text=True,
        timeout=30,
    )


def _base_env(tmp_root, with_pdf=True):
    env = {
        "DJANGO_SETTINGS_MODULE": "portal.settings_supervised_synthetic",
        "PRACE_RUNTIME_ROOT": str(tmp_root),
        "PRACE_SECRET_KEY": "test-secret-not-a-real-key",
        "PRACE_ALLOWED_HOSTS": "localhost,127.0.0.1",
        "PYTHONPATH": str(REPO_ROOT),
    }
    manifest = tmp_root / "build_manifest.json"
    manifest.write_text(
        json.dumps({"git_commit": "0" * 40, "app_build_id": "0" * 16, "generated_at": "2026-01-01T00:00:00Z"})
    )
    manifest.chmod(0o400)
    import hashlib
    sha = hashlib.sha256(manifest.read_bytes()).hexdigest()
    env["PRACE_RELEASE_MANIFEST"] = str(manifest)
    env["PRACE_RELEASE_MANIFEST_SHA256"] = sha
    if with_pdf:
        env.update({
            "PDF_SHA256": "0" * 64,
            "REGEN_SHA256": "1" * 64,
        })
    return env


def _migrated_runtime_env(tmp_root):
    """Build the supervised-synthetic env and run a real migrate once, so
    the verification queries run against a real schema (rows missing) and
    not against an empty database (which now correctly exits BLOCKED)."""
    env = _base_env(tmp_root, with_pdf=False)
    r = subprocess.run(
        [sys.executable, "manage.py", "migrate", "--noinput"],
        cwd=str(REPO_ROOT), env={**os.environ, **env},
        capture_output=True, text=True, timeout=180)
    assert r.returncode == 0, f"migrate failed:\n{r.stdout}\n{r.stderr}"
    return env


class TestCoreProfileNoPdfVars:
    """F2: core profile must run without A1/PDF env vars."""

    def test_core_profile_succeeds_without_pdf_vars(self):
        with tempfile.TemporaryDirectory(prefix="supervised-persistence-test-", dir=str(REPO_ROOT / "runtime" / "portal")) as tmp:
            tmp_root = Path(tmp)
            os.chmod(str(tmp_root), 0o700)
            env = _migrated_runtime_env(tmp_root)
            env.update({
                "ORG_PK": "1",
                "WORKER_PK": "99999",
                "DOCUMENT_PK": "99999",
                "ASSIGNMENT_PK": "99999",
                "DOCUMENT_SHA256": "0" * 64,
            })
            r = _run(["--profile", "core"], env)
            # Exit 1 is expected because rows don't exist; exit 2 would
            # mean the script blocked on missing env (the bug).
            assert r.returncode != 2, (
                f"core profile blocked on missing env (F2 not fixed):\n"
                f"stderr: {r.stderr}"
            )

    def test_optional_a1_profile_blocks_without_pdf_vars(self):
        with tempfile.TemporaryDirectory(prefix="supervised-persistence-test-", dir=str(REPO_ROOT / "runtime" / "portal")) as tmp:
            tmp_root = Path(tmp)
            os.chmod(str(tmp_root), 0o700)
            env = _base_env(tmp_root, with_pdf=False)
            env.update({
                "ORG_PK": "1",
                "WORKER_PK": "99999",
                "DOCUMENT_PK": "99999",
                "ASSIGNMENT_PK": "99999",
                "DOCUMENT_SHA256": "0" * 64,
            })
            r = _run(["--profile", "optional-a1"], env)
            # Exit 2 = PERSISTENCE_ACCEPTANCE_BLOCKED is expected for optional-a1 without PDF vars
            assert r.returncode == 2, (
                f"optional-a1 profile should block without PDF vars:\n"
                f"rc={r.returncode}\nstderr: {r.stderr}"
            )
            assert "PERSISTENCE_ACCEPTANCE_BLOCKED" in r.stderr


class TestDocumentHashVerification:
    """F3: document hash must be compared, not just retrieved."""

    def test_hash_mismatch_reported(self):
        """When the stated identifier rows do not exist, the core check
        reports a row/check failure (exit 1) — not a blocked exit 2."""
        with tempfile.TemporaryDirectory(prefix="supervised-persistence-test-", dir=str(REPO_ROOT / "runtime" / "portal")) as tmp:
            tmp_root = Path(tmp)
            os.chmod(str(tmp_root), 0o700)
            env = _migrated_runtime_env(tmp_root)
            env.update({
                "ORG_PK": "1",
                "WORKER_PK": "99999",
                "DOCUMENT_PK": "99999",
                "ASSIGNMENT_PK": "99999",
                "DOCUMENT_SHA256": "abcd" * 16,
            })
            r = _run(["--profile", "core"], env)
            assert r.returncode == 1, f"unexpected rc={r.returncode}: {r.stderr}"
            assert "PERSISTENCE_ACCEPTANCE_BLOCKED" not in r.stderr

    def test_hash_function_accepts_expected_value(self):
        """The _document_worker_sha256 function must accept expected_sha256."""
        code = (
            "import sys\n"
            "sys.path.insert(0, " + repr(str(REPO_ROOT)) + ")\n"
            "from scripts.rehearse_verify_persistence import _document_worker_sha256\n"
            "import inspect\n"
            "sig = inspect.signature(_document_worker_sha256)\n"
            "params = list(sig.parameters.keys())\n"
            "print('params=' + ','.join(params))\n"
            "assert 'expected_sha256' in params, '_document_worker_sha256 must accept expected_sha256'\n"
        )
        r = subprocess.run(
            [sys.executable, "-c", code],
            env={**os.environ, "PYTHONPATH": str(REPO_ROOT)},
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert r.returncode == 0, f"F3 not fixed: {r.stderr}"


class TestSourceBytesVerification:
    """F3 refinement: the verifier must prove source-file bytes, not only
    the stored hash column. A correct sha256 column with corrupted source
    bytes must FAIL, and a corrupted column with correct bytes must FAIL
    with a distinct message."""

    SEED_CODE = (
        "import hashlib, datetime\n"
        "from django.core.files.storage import default_storage\n"
        "from portal.release1a.models import Organization, Worker, Document, Assignment\n"
        "org, _ = Organization.objects.get_or_create(\n"
        "    key='persist-source-test-org', defaults={'label': 'Persistence source test'})\n"
        "worker = Worker.objects.create(organization=org, given_name='Jan', family_name='Vyzkus',\n"
        "    birth_date=datetime.date(1990, 1, 1), activity_profile='employee', state='active')\n"
        "content = b'SOURCE-DOCUMENT-BYTES-2026 42\\n'\n"
        "key = 'doc-source-42.txt'\n"
        "sha = hashlib.sha256(content).hexdigest()\n"
        "with default_storage.open(key, 'wb') as stream:\n"
        "    stream.write(content)\n"
        "document = Document.objects.create(organization=org, worker=worker,\n"
        "    purpose='worker_intake', opaque_key=key, sha256=sha,\n"
        "    content_type='text/plain', state='confirmed')\n"
        "assignment = Assignment.objects.create(organization=org, worker=worker,\n"
        "    workplace_label='Hamburg', activity_label='montáž',\n"
        "    start=datetime.date(2026, 9, 1), end=datetime.date(2027, 8, 31),\n"
        "    state='active')\n"
        "print('ORG=%d WORKER=%d DOC=%d ASSIGN=%d SHA=%s KEY=%s' % (\n"
        "    org.pk, worker.pk, document.pk, assignment.pk, sha, key))\n"
    )

    def _provision(self, tmp_root):
        env = _base_env(tmp_root, with_pdf=False)
        base = {
            "PATH": os.environ["PATH"],
            "HOME": os.environ.get("HOME", "/tmp"),
            "PYTHONPATH": str(REPO_ROOT),
            "DJANGO_SETTINGS_MODULE": "portal.settings_supervised_synthetic",
            "PRACE_RUNTIME_ROOT": str(tmp_root),
            "PRACE_SECRET_KEY": "test-secret-not-a-real-key",
            "PRACE_ALLOWED_HOSTS": "localhost,127.0.0.1",
        }
        base["PRACE_RELEASE_MANIFEST"] = env["PRACE_RELEASE_MANIFEST"]
        base["PRACE_RELEASE_MANIFEST_SHA256"] = env["PRACE_RELEASE_MANIFEST_SHA256"]
        r = subprocess.run(
            [sys.executable, "manage.py", "migrate", "--noinput"],
            cwd=str(REPO_ROOT), env={**os.environ, **base},
            capture_output=True, text=True, timeout=180)
        assert r.returncode == 0, f"migrate failed:\n{r.stdout}\n{r.stderr}"
        seed = subprocess.run(
            [sys.executable, "manage.py", "shell", "-c", self.SEED_CODE],
            cwd=str(REPO_ROOT), env={**os.environ, **base},
            capture_output=True, text=True, timeout=60)
        assert seed.returncode == 0, f"seed failed:\n{seed.stdout}\n{seed.stderr}"
        values = {}
        for token in seed.stdout.strip().split():
            key, _, value = token.partition("=")
            values[key] = value
        values["env"] = base
        return values

    def _verify(self, values, doc_sha):
        env = dict(values["env"])
        env.update({
            "ORG_PK": values["ORG"],
            "WORKER_PK": values["WORKER"],
            "DOCUMENT_PK": values["DOC"],
            "ASSIGNMENT_PK": values["ASSIGN"],
            "DOCUMENT_SHA256": doc_sha,
        })
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--profile", "core"],
            env={**os.environ, **env}, capture_output=True, text=True, timeout=60)

    def test_source_bytes_and_stored_hash_both_proven(self):
        """One provisioned journey proves all three acceptance paths:
        matching source bytes pass, corrupted source bytes fail despite a
        correct stored hash, and a wrong expected DB hash fails with the
        distinct db-mismatch message."""
        with tempfile.TemporaryDirectory(
                prefix="supervised-persistence-source-test-",
                dir=str(REPO_ROOT / "runtime" / "portal")) as tmp:
            tmp_root = Path(tmp)
            os.chmod(str(tmp_root), 0o700)
            values = self._provision(tmp_root)
            content = b"SOURCE-DOCUMENT-BYTES-2026 42\n"

            good = self._verify(values, values["SHA"])
            assert good.returncode == 0, (
                f"matching source bytes must pass:\n{good.stderr}")
            assert "db+source matched" in good.stdout

            corrupt = (tmp_root / "media" / values["KEY"])
            corrupt.write_bytes(b"CORRUPTED-DIFFERENT-BYTES\n")
            bad_source = self._verify(values, values["SHA"])
            assert bad_source.returncode == 1
            assert "source bytes" in bad_source.stderr

            bugfix = (tmp_root / "media" / values["KEY"])
            bugfix.write_bytes(content)
            wrong_hash = self._verify(values, "f" * 64)
            assert wrong_hash.returncode == 1
            assert "db hash mismatch" in wrong_hash.stderr


class TestBrowserProfileWiring:
    """F5: playwright_smoke must not strip PostgreSQL env vars."""

    def test_playwright_smoke_preserves_pg_env(self):
        source = (REPO_ROOT / "scripts/playwright_smoke.py").read_text()
        assert "DOCUMENT_TEST_PG_SOCKET" not in source, (
            "F5 not fixed: playwright_smoke.py still pops DOCUMENT_TEST_PG_SOCKET"
        )
        assert "DOCUMENT_TEST_PG_USER" not in source, (
            "F5 not fixed: playwright_smoke.py still pops DOCUMENT_TEST_PG_USER"
        )


class TestOperatorUrlWiring:
    """F6: PRACE_OPERATOR_URL must be consumed by the workflow caller."""

    def test_rehearse_script_uses_operator_url(self):
        source = (REPO_ROOT / "scripts/rehearse_synthetic_site.sh").read_text()
        assert "PRACE_OPERATOR_URL" in source, (
            "F6 not fixed: rehearse_synthetic_site.sh does not reference PRACE_OPERATOR_URL"
        )
        assert "base_url" in source, (
            "F6 not fixed: base_url variable not set from PRACE_OPERATOR_URL"
        )


class TestIsolatedPgWiring:
    """F7: browser test settings must accept complete PostgreSQL targets,
    must require PASSWORD on TCP, and must fail closed on a lone variable
    instead of silently selecting SQLite."""

    IMPORT = (
        "import os, sys\n"
        "os.environ['DJANGO_SETTINGS_MODULE'] = 'portal.settings_browser_tests'\n"
        "sys.path.insert(0, " + repr(str(REPO_ROOT)) + ")\n"
        "try:\n"
        "    from portal import settings_browser_tests as s\n"
        "except Exception as exc:\n"
        "    sys.stderr.write('IMPORT_ERROR: ' + repr(exc) + '\\n')\n"
        "    sys.exit(2)\n"
        "db = s.DATABASES['default']\n"
        "print('ENGINE=' + db['ENGINE'])\n"
        "print('NAME=' + db['NAME'])\n"
        "print('USER=' + str(db.get('USER', '')))\n"
        "print('PASSWORD=' + str('PASSWORD' in db))\n"
    )

    def _run(self, extra_env):
        runtime = REPO_ROOT / "runtime" / "portal"
        runtime.mkdir(parents=True, exist_ok=True)
        socket_dir = tempfile.mkdtemp(prefix="browser-pg-", dir=runtime)
        env = {
            **os.environ,
            "DOCUMENT_TEST_PG_SOCKET": socket_dir,
            "DOCUMENT_TEST_PG_NAME": "prace_browser_tests",
            "DOCUMENT_TEST_PG_USER": "browser_tester",
            "DOCUMENT_TEST_PG_PORT": "55439",
        }
        if "DOCUMENT_TEST_PG_HOST" in extra_env:
            env.pop("DOCUMENT_TEST_PG_SOCKET")
        env.update(extra_env)
        return subprocess.run([sys.executable, "-c", self.IMPORT],
                              cwd=str(REPO_ROOT), env=env,
                              capture_output=True, text=True, timeout=60)

    def test_browser_settings_accepts_socket_target_without_password(self):
        result = self._run({})
        assert result.returncode == 0, result.stderr
        assert "ENGINE=django.db.backends.postgresql" in result.stdout
        assert "NAME=prace_browser_tests" in result.stdout
        assert "USER=browser_tester" in result.stdout
        assert "PASSWORD=False" in result.stdout

    def test_browser_settings_requires_password_for_tcp_target(self):
        result = self._run({
            "DOCUMENT_TEST_PG_HOST": "127.0.0.1",
            "DOCUMENT_TEST_PG_PORT": "5432",
        })
        assert result.returncode != 0
        assert "DOCUMENT_TEST_PG_PASSWORD is required" in result.stderr

    def test_browser_settings_host_only_fails_closed(self):
        result = subprocess.run(
            [sys.executable, "-c", self.IMPORT], cwd=str(REPO_ROOT),
            env={
                **os.environ,
                "DOCUMENT_TEST_PG_HOST": "127.0.0.1",
                "DOCUMENT_TEST_PG_PORT": "5432",
            },
            capture_output=True, text=True, timeout=60)
        assert result.returncode != 0, (
            "host-only target must fail closed, not silently select SQLite")
        assert "partial test PostgreSQL target" in result.stderr
