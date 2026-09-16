"""Deterministic unit tests for the shared DOCUMENT_TEST_PG_* contract."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from portal.test_pg_contract import resolve_test_postgres_target

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME = str(REPO_ROOT / "runtime")


def _env(**overrides):
    env = {
        "DOCUMENT_TEST_PG_SOCKET": str(REPO_ROOT / "runtime" / "pg-socket"),
        "DOCUMENT_TEST_PG_NAME": "prace_doc_tests",
        "DOCUMENT_TEST_PG_USER": "doc_tester",
        "DOCUMENT_TEST_PG_PORT": "55439",
    }
    env.update(overrides)
    return env


def test_no_vars_selects_sqlite_default():
    assert resolve_test_postgres_target({}, runtime_base=RUNTIME) is None


def test_host_alone_is_partial_and_refused():
    with pytest.raises(RuntimeError, match="partial test PostgreSQL target"):
        resolve_test_postgres_target({"DOCUMENT_TEST_PG_HOST": "127.0.0.1"},
                                     runtime_base=RUNTIME)


def test_socket_requires_name_and_user():
    with pytest.raises(RuntimeError, match="DOCUMENT_TEST_PG_NAME"):
        resolve_test_postgres_target({"DOCUMENT_TEST_PG_SOCKET": "/tmp/pg"},
                                     runtime_base=RUNTIME)
    with pytest.raises(RuntimeError, match="DOCUMENT_TEST_PG_USER"):
        resolve_test_postgres_target(
            {"DOCUMENT_TEST_PG_SOCKET": "/tmp/pg",
             "DOCUMENT_TEST_PG_NAME": "prace_doc_tests"},
            runtime_base=RUNTIME)


def test_last_var_alone_also_fails_closed():
    with pytest.raises(RuntimeError, match="partial test PostgreSQL target"):
        resolve_test_postgres_target({"DOCUMENT_TEST_PG_USER": "stray"},
                                     runtime_base=RUNTIME)


def test_socket_path_must_be_inside_runtime():
    outside = "/tmp/not-the-project-runtime"
    with pytest.raises(RuntimeError, match="inside project runtime"):
        resolve_test_postgres_target(
            dict(_env(), DOCUMENT_TEST_PG_SOCKET=outside),
            runtime_base=RUNTIME)


def test_tcp_target_requires_password():
    with pytest.raises(RuntimeError, match="DOCUMENT_TEST_PG_PASSWORD is required"):
        resolve_test_postgres_target(
            {k: v for k, v in _env().items() if k != "DOCUMENT_TEST_PG_SOCKET"}
            | {"DOCUMENT_TEST_PG_HOST": "127.0.0.1"},
            runtime_base=RUNTIME)


def test_tcp_target_carries_password():
    config = resolve_test_postgres_target(
        {k: v for k, v in _env().items() if k != "DOCUMENT_TEST_PG_SOCKET"}
        | {"DOCUMENT_TEST_PG_HOST": "127.0.0.1",
           "DOCUMENT_TEST_PG_PASSWORD": "secret"},
        runtime_base=RUNTIME)
    assert config["HOST"] == "127.0.0.1"
    assert config["PASSWORD"] == "secret"


def test_socket_and_host_together_refused():
    with pytest.raises(RuntimeError, match="not both"):
        resolve_test_postgres_target(
            _env(DOCUMENT_TEST_PG_HOST="127.0.0.1"),
            runtime_base=RUNTIME)


def test_operator_database_name_refused():
    with pytest.raises(RuntimeError, match="operator database name"):
        resolve_test_postgres_target(
            dict(_env(), DOCUMENT_TEST_PG_NAME="prace_synthetic"),
            runtime_base=RUNTIME)


def test_disposable_test_database_name_allowed():
    config = resolve_test_postgres_target(_env(), runtime_base=RUNTIME)
    assert config["NAME"] == "prace_doc_tests"
    assert "PASSWORD" not in config


def test_document_test_settings_host_only_fails_closed():
    """settings_document_tests must not silently fall back to SQLite when
    only DOCUMENT_TEST_PG_HOST is exported."""
    code = (
        "import os, sys\n"
        "sys.path.insert(0, " + repr(str(REPO_ROOT)) + ")\n"
        "os.environ['DJANGO_SETTINGS_MODULE'] = 'portal.settings_document_tests'\n"
        "from portal import settings_document_tests\n"
        "print(settings_document_tests.DATABASES['default']['ENGINE'])\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=str(REPO_ROOT),
        env={**os.environ, "DOCUMENT_TEST_PG_HOST": "127.0.0.1"},
        capture_output=True, text=True, timeout=60)
    assert result.returncode != 0, (
        "host-only target silently selected SQLite; must fail closed")
    assert "partial test PostgreSQL target" in result.stderr