"""Confined supervised synthetic settings — dummy-value contract tests.

Each case runs in a fresh subprocess so Django's settings caching does not
mask a contract violation. All values are dummy synthetic test material; no
real private data, secrets, DB credentials or file paths are used.

Parent: docs/operations/infra-return-work-order-2026-09-07.md (Priority 2).
"""
import json
import hashlib
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SETTINGS_MODULE = "portal.settings_supervised_synthetic"
# Public invalid value used only to verify the base default is rejected.
BAD_DEFAULT = "synthetic-m2-local-only-insecure-default"
IMPORT_CODE = (
    "import os, sys\n"
    "os.environ.pop('DJANGO_SETTINGS_MODULE', None)\n"
    "os.environ['DJANGO_SETTINGS_MODULE'] = '{module}'\n"
    "try:\n"
    "    import {module}\n"
    "except Exception as exc:\n"
    "    sys.stderr.write('IMPORT_ERROR: ' + repr(exc) + '\\n')\n"
    "    sys.exit(2)\n"
    "from django.conf import settings\n"
    "sys.stdout.write('OK:')\n"
    "sys.stdout.write('DEBUG=' + str(settings.DEBUG) + ';')\n"
    "sys.stdout.write('SUPERVISED=' + str(getattr(settings, 'PRACE_SUPERVISED', False)) + ';')\n"
    "sys.stdout.write('SYNTHETIC=' + str(getattr(settings, 'M2_SYNTHETIC_ONLY', False)) + ';')\n"
    "sys.stdout.write('RUNTIME_ROOT=' + str(getattr(settings, 'PRACE_RUNTIME_ROOT', None)) + ';')\n"
    "sys.stdout.write('ALLOWED=' + ','.join(getattr(settings, 'ALLOWED_HOSTS', [])) + ';')\n"
    "sys.stdout.write('COOKIES=' + str(settings.SESSION_COOKIE_SECURE) + ',' + str(settings.CSRF_COOKIE_SECURE) + ';')\n"
    "sys.stdout.write('EMAIL=' + settings.EMAIL_BACKEND + ';')\n"
    "sys.stdout.write('ENGINE=' + settings.DATABASES['default']['ENGINE'] + '\\n')\n"
).format(module=SETTINGS_MODULE)


def _runtime_tmp():
    return tempfile.mkdtemp(
        prefix="supervised-runtime-",
        dir=str(REPO_ROOT / "runtime" / "portal"),
    )


def _make_manifest(tmpdir, **overrides):
    payload = {
        "git_commit": "0" * 40,
        "app_build_id": "0" * 16,
        "generated_at": "2026-09-07T00:00:00+00:00",
    }
    payload.update(overrides)
    path = Path(tmpdir) / "build_manifest.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    os.chmod(path, stat.S_IRUSR | stat.S_IRGRP)
    return str(path)


def _valid_env(**overrides):
    tmpdir = _runtime_tmp()
    env = {
        "PRACE_RUNTIME_ROOT": tmpdir,
        "PRACE_SECRET_KEY": "dummy-test-secret-not-a-real-key",
        "PRACE_RELEASE_MANIFEST": _make_manifest(tmpdir),
        "PRACE_ALLOWED_HOSTS": "localhost,127.0.0.1",
    }
    env.update(overrides)
    path = Path(env["PRACE_RELEASE_MANIFEST"])
    env["PRACE_RELEASE_MANIFEST_SHA256"] = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "0" * 64
    return env


def _import_with(env):
    proc = subprocess.run(
        [sys.executable, "-c", IMPORT_CODE],
        env={**os.environ, **env},
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    return proc


def _stderr_text(proc):
    return proc.stderr or ""


def _assert_failure(proc, *markers):
    assert proc.returncode != 0, (
        f"expected failure but import succeeded\nstdout={proc.stdout!r}\nstderr={proc.stderr!r}"
    )
    body = _stderr_text(proc)
    for marker in markers:
        assert marker in body, (
            f"expected {marker!r} in stderr; got:\n{body}\nstdout={proc.stdout!r}"
        )


class TestValidBaseline:
    def test_minimal_env_loads(self):
        proc = _import_with(_valid_env())
        assert proc.returncode == 0, _stderr_text(proc)
        assert "OK:DEBUG=False" in proc.stdout
        assert "SUPERVISED=True" in proc.stdout
        assert "SYNTHETIC=True" in proc.stdout
        assert "ENGINE=django.db.backends.sqlite3" in proc.stdout

    def test_runtime_root_captured(self):
        tmpdir = _runtime_tmp()
        proc = _import_with(_valid_env(PRACE_RUNTIME_ROOT=tmpdir))
        assert proc.returncode == 0
        assert tmpdir in proc.stdout
        assert (Path(tmpdir) / "storage").is_dir()
        assert (Path(tmpdir) / "cache").is_dir()
        assert (Path(tmpdir) / "tmp").is_dir()
        assert (Path(tmpdir) / "logs").is_dir()
        assert (Path(tmpdir) / "static").is_dir()


class TestRuntimeRoot:
    def test_missing(self):
        env = _valid_env()
        env.pop("PRACE_RUNTIME_ROOT")
        _assert_failure(_import_with(env), "PRACE_RUNTIME_ROOT")

    def test_empty(self):
        _assert_failure(_import_with(_valid_env(PRACE_RUNTIME_ROOT="")), "PRACE_RUNTIME_ROOT")

    def test_whitespace_only(self):
        _assert_failure(_import_with(_valid_env(PRACE_RUNTIME_ROOT="   ")), "PRACE_RUNTIME_ROOT")

    def test_relative(self):
        _assert_failure(_import_with(_valid_env(PRACE_RUNTIME_ROOT="relative/path")), "PRACE_RUNTIME_ROOT")

    def test_missing_directory(self):
        _assert_failure(
            _import_with(_valid_env(PRACE_RUNTIME_ROOT="/tmp/does-not-exist-supervised-xyz")),
            "PRACE_RUNTIME_ROOT",
        )

    def test_file_not_dir(self):
        tmpdir = _runtime_tmp()
        not_dir = Path(tmpdir) / "not-a-dir"
        not_dir.write_text("x", encoding="utf-8")
        _assert_failure(
            _import_with(_valid_env(PRACE_RUNTIME_ROOT=str(not_dir))),
            "PRACE_RUNTIME_ROOT",
        )

    def test_unwritable_rejected(self, tmp_path):
        if os.geteuid() == 0:
            pytest.skip("cannot enforce unwritable directory as root")
        tmp_path.chmod(0o500)
        try:
            _assert_failure(
                _import_with(_valid_env(PRACE_RUNTIME_ROOT=str(tmp_path))),
                "PRACE_RUNTIME_ROOT",
            )
        finally:
            tmp_path.chmod(0o700)


class TestSecretKey:
    def test_missing(self):
        env = _valid_env()
        env.pop("PRACE_SECRET_KEY")
        _assert_failure(_import_with(env), "PRACE_SECRET_KEY")

    def test_empty(self):
        _assert_failure(_import_with(_valid_env(PRACE_SECRET_KEY="")), "PRACE_SECRET_KEY")

    def test_insecure_default_rejected(self):
        _assert_failure(
            _import_with(_valid_env(PRACE_SECRET_KEY=BAD_DEFAULT)),
            "insecure default",
        )


class TestReleaseManifest:
    def test_missing(self):
        env = _valid_env()
        env.pop("PRACE_RELEASE_MANIFEST")
        _assert_failure(_import_with(env), "PRACE_RELEASE_MANIFEST")

    def test_relative(self):
        _assert_failure(
            _import_with(_valid_env(PRACE_RELEASE_MANIFEST="manifest.json")),
            "absolute",
        )

    def test_missing_file(self):
        _assert_failure(
            _import_with(_valid_env(PRACE_RELEASE_MANIFEST="/tmp/no-such-manifest-xyz.json")),
            "PRACE_RELEASE_MANIFEST",
        )

    def test_not_json(self):
        tmpdir = _runtime_tmp()
        path = Path(tmpdir) / "build_manifest.json"
        path.write_text("not json at all", encoding="utf-8")
        os.chmod(path, stat.S_IRUSR | stat.S_IRGRP)
        _assert_failure(
            _import_with(_valid_env(PRACE_RELEASE_MANIFEST=str(path))),
            "PRACE_RELEASE_MANIFEST",
        )

    def test_writable_rejected(self):
        tmpdir = _runtime_tmp()
        path = Path(tmpdir) / "build_manifest.json"
        path.write_text(json.dumps({
            "git_commit": "0" * 40,
            "app_build_id": "0" * 16,
            "generated_at": "2026-09-07T00:00:00+00:00",
        }), encoding="utf-8")
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP)
        _assert_failure(
            _import_with(_valid_env(PRACE_RELEASE_MANIFEST=str(path))),
            "read-only",
        )

    def test_missing_required_key(self):
        tmpdir = _runtime_tmp()
        path = Path(tmpdir) / "build_manifest.json"
        path.write_text(json.dumps({"git_commit": "x", "generated_at": "y"}), encoding="utf-8")
        os.chmod(path, stat.S_IRUSR | stat.S_IRGRP)
        _assert_failure(
            _import_with(_valid_env(PRACE_RELEASE_MANIFEST=str(path))),
            "PRACE_RELEASE_MANIFEST",
        )


class TestAllowedHosts:
    def test_missing(self):
        env = _valid_env()
        env.pop("PRACE_ALLOWED_HOSTS")
        _assert_failure(_import_with(env), "PRACE_ALLOWED_HOSTS")

    def test_empty(self):
        _assert_failure(_import_with(_valid_env(PRACE_ALLOWED_HOSTS="")), "PRACE_ALLOWED_HOSTS")

    def test_only_whitespace(self):
        _assert_failure(
            _import_with(_valid_env(PRACE_ALLOWED_HOSTS=" , , ")),
            "at least one host",
        )

    def test_invalid_chars(self):
        _assert_failure(
            _import_with(_valid_env(PRACE_ALLOWED_HOSTS="host;injection")),
            "invalid entry",
        )

    def test_valid_loads(self):
        proc = _import_with(_valid_env(PRACE_ALLOWED_HOSTS="a.test,b.test,127.0.0.1"))
        assert proc.returncode == 0
        assert "ALLOWED=a.test,b.test,127.0.0.1" in proc.stdout


class TestTrustedOrigins:
    def test_unset_ok(self):
        env = _valid_env()
        env.pop("PRACE_TRUSTED_ORIGINS", None)
        proc = _import_with(env)
        assert proc.returncode == 0

    def test_http_rejected(self):
        _assert_failure(
            _import_with(_valid_env(PRACE_TRUSTED_ORIGINS="http://insecure.example")),
            "https://",
        )

    def test_multiple_https_ok(self):
        proc = _import_with(
            _valid_env(PRACE_TRUSTED_ORIGINS="https://a.example,https://b.example")
        )
        assert proc.returncode == 0


class TestDatabaseTargets:
    def test_no_db_defaults_sqlite(self):
        env = _valid_env()
        for k in ("PRACE_DB_NAME", "PRACE_DB_USER", "PRACE_DB_HOST", "PRACE_DB_PORT"):
            env.pop(k, None)
        proc = _import_with(env)
        assert proc.returncode == 0
        assert "ENGINE=django.db.backends.sqlite3" in proc.stdout

    def test_partial_rejected(self):
        _assert_failure(
            _import_with(_valid_env(PRACE_DB_HOST="/tmp")),
            "PRACE_DB_*",
        )

    def test_partial_three_of_four_rejected(self):
        env = _valid_env()
        env["PRACE_DB_NAME"] = "x"
        env["PRACE_DB_USER"] = "y"
        env["PRACE_DB_HOST"] = "/tmp"
        _assert_failure(_import_with(env), "PRACE_DB_*")

    def test_port_not_integer(self):
        env = _valid_env()
        env["PRACE_DB_NAME"] = "x"
        env["PRACE_DB_USER"] = "y"
        env["PRACE_DB_HOST"] = "/tmp"
        env["PRACE_DB_PORT"] = "abc"
        _assert_failure(_import_with(env), "integer")

    def test_port_too_high(self):
        env = _valid_env()
        env["PRACE_DB_NAME"] = "x"
        env["PRACE_DB_USER"] = "y"
        env["PRACE_DB_HOST"] = "/tmp"
        env["PRACE_DB_PORT"] = "70000"
        _assert_failure(_import_with(env), "1-65535")

    def test_port_zero(self):
        env = _valid_env()
        env["PRACE_DB_NAME"] = "x"
        env["PRACE_DB_USER"] = "y"
        env["PRACE_DB_HOST"] = "/tmp"
        env["PRACE_DB_PORT"] = "0"
        _assert_failure(_import_with(env), "1-65535")

    def test_sslmode_invalid(self):
        env = _valid_env()
        env["PRACE_DB_NAME"] = "x"
        env["PRACE_DB_USER"] = "y"
        env["PRACE_DB_HOST"] = "/tmp"
        env["PRACE_DB_PORT"] = "5432"
        env["PRACE_DB_SSLMODE"] = "maybenot"
        _assert_failure(_import_with(env), "PRACE_DB_SSLMODE")

    def test_verify_full_requires_rootcert(self):
        env = _valid_env()
        env["PRACE_DB_NAME"] = "x"
        env["PRACE_DB_USER"] = "y"
        env["PRACE_DB_HOST"] = "/tmp"
        env["PRACE_DB_PORT"] = "5432"
        env["PRACE_DB_SSLMODE"] = "verify-full"
        _assert_failure(_import_with(env), "PRACE_DB_SSLROOTCERT")

    def test_verify_ca_requires_rootcert(self):
        env = _valid_env()
        env["PRACE_DB_NAME"] = "x"
        env["PRACE_DB_USER"] = "y"
        env["PRACE_DB_HOST"] = "/tmp"
        env["PRACE_DB_PORT"] = "5432"
        env["PRACE_DB_SSLMODE"] = "verify-ca"
        _assert_failure(_import_with(env), "PRACE_DB_SSLROOTCERT")

    def test_full_postgres_target_loads(self):
        tmpdir = _runtime_tmp()
        sslrootcert = Path(tmpdir) / "ca.pem"
        sslrootcert.write_text("dummy ca", encoding="utf-8")
        env = _valid_env(
            PRACE_DB_NAME="synthetic",
            PRACE_DB_USER="synthetic",
            PRACE_DB_HOST="/tmp",
            PRACE_DB_PORT="5432",
            PRACE_DB_SSLMODE="verify-full",
            PRACE_DB_SSLROOTCERT=str(sslrootcert),
        )
        proc = _import_with(env)
        assert proc.returncode == 0, _stderr_text(proc)
        assert "ENGINE=django.db.backends.postgresql" in proc.stdout


class TestPostgreSQLRootcert:
    def test_rootcert_relative_rejected(self):
        env = _valid_env()
        env["PRACE_DB_NAME"] = "x"
        env["PRACE_DB_USER"] = "y"
        env["PRACE_DB_HOST"] = "/tmp"
        env["PRACE_DB_PORT"] = "5432"
        env["PRACE_DB_SSLMODE"] = "verify-full"
        env["PRACE_DB_SSLROOTCERT"] = "relative-ca.pem"
        _assert_failure(_import_with(env), "absolute")

    def test_rootcert_missing_rejected(self):
        env = _valid_env()
        env["PRACE_DB_NAME"] = "x"
        env["PRACE_DB_USER"] = "y"
        env["PRACE_DB_HOST"] = "/tmp"
        env["PRACE_DB_PORT"] = "5432"
        env["PRACE_DB_SSLMODE"] = "verify-full"
        env["PRACE_DB_SSLROOTCERT"] = "/tmp/does-not-exist-supervised-ca.pem"
        _assert_failure(_import_with(env), "not found")


class TestReadinessBudget:
    def test_unset_uses_default(self):
        env = _valid_env()
        env.pop("PRACE_READINESS_BUDGET_MS", None)
        proc = _import_with(env)
        assert proc.returncode == 0

    def test_valid_override_loads(self):
        env = _valid_env(PRACE_READINESS_BUDGET_MS="750")
        proc = _import_with(env)
        assert proc.returncode == 0

    def test_non_integer_rejected(self):
        _assert_failure(
            _import_with(_valid_env(PRACE_READINESS_BUDGET_MS="abc")),
            "PRACE_READINESS_BUDGET_MS",
        )

    def test_below_minimum_rejected(self):
        _assert_failure(
            _import_with(_valid_env(PRACE_READINESS_BUDGET_MS="50")),
            "PRACE_READINESS_BUDGET_MS",
        )

    def test_above_maximum_rejected(self):
        _assert_failure(
            _import_with(_valid_env(PRACE_READINESS_BUDGET_MS="120000")),
            "PRACE_READINESS_BUDGET_MS",
        )


def test_optional_inbox_defaults_use_existing_ids_and_private_root():
    env = _valid_env(PRACE_INBOX_ORGANIZATION_ID="12", PRACE_INBOX_ACTOR_ID="34")
    code = (
        "from portal import settings_supervised_synthetic as s; "
        "import stat; "
        "assert s.DOCUMENT_INBOX_ORGANIZATION_ID == 12; "
        "assert s.DOCUMENT_INBOX_ACTOR_ID == 34; "
        "root=s.DOCUMENT_INBOX_ROOTS[12]; "
        "assert root == s.DOCUMENT_STORAGE_ROOT / 'inbox' / 'org-12'; "
        "assert stat.S_IMODE(root.stat().st_mode) == 0o700"
    )
    result = subprocess.run([sys.executable, "-c", code], cwd=REPO_ROOT,
                            env={**os.environ, **env}, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("org,actor", [("12", ""), ("", "34"), ("0", "34"), ("12", "../34")])
def test_inbox_configuration_requires_positive_id_pair(org, actor):
    result = _import_with(_valid_env(PRACE_INBOX_ORGANIZATION_ID=org, PRACE_INBOX_ACTOR_ID=actor))
    _assert_failure(result, "Inbox organization and actor IDs")


@pytest.mark.parametrize("override, expected", [(None, "True,True"), ("false", "False,False"), ("unexpected", "True,True")])
def test_synthetic_cookie_override_is_explicit_and_email_stays_local(monkeypatch, override, expected):
    monkeypatch.delenv("PRACE_COOKIE_SECURE", raising=False)
    env = _valid_env()
    if override is not None:
        env["PRACE_COOKIE_SECURE"] = override
    proc = _import_with(env)
    assert proc.returncode == 0, proc.stderr
    assert "COOKIES=" + expected in proc.stdout
    assert "EMAIL=django.core.mail.backends.locmem.EmailBackend" in proc.stdout
