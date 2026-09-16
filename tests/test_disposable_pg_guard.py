"""Deterministic tests for :mod:`scripts.disposable_pg_guard`.

The guard is deliberately connection-free at import time; these tests
exercise the refusal logic deterministically and stub the exclusive-use
lock so the success path is verified without a live cluster.
"""
from __future__ import annotations

import json

import pytest

from scripts import disposable_pg_guard as guard


FULL_TARGET = {
    "PRACE_DB_NAME": "prace_synthetic_test",
    "PRACE_DB_USER": "prace_synth_app",
    "PRACE_DB_PASSWORD": "synthetic-test-password",
    "PRACE_DB_HOST": "127.0.0.1",
    "PRACE_DB_PORT": "5432",
}


def _ownership(monkeypatch, tmp_path, *, name="prace_synthetic_test", host="127.0.0.1",
               port="5432", disposable=True):
    record = {"database": name, "host": host, "port": port, "disposable": disposable}
    path = tmp_path / "disposable-pg.ownership.json"
    path.write_text(json.dumps(record))
    monkeypatch.setenv("PRACE_DISPOSABLE_OWNERSHIP", str(path))
    return path


def _disposable_env(monkeypatch, tmp_path):
    env = dict(FULL_TARGET)
    env["PRACE_DISPOSABLE_TARGET"] = "1"
    path = _ownership(monkeypatch, tmp_path)
    env["PRACE_DISPOSABLE_OWNERSHIP"] = str(path)
    return env


def test_no_target_is_local_default():
    verdict = guard.verify_target({})
    assert verdict["ok"] is True
    assert verdict["blocked"] is False
    assert verdict["target"] is None


def test_partial_target_is_refused():
    env = dict(FULL_TARGET)
    del env["PRACE_DB_PASSWORD"]
    verdict = guard.verify_target(env)
    assert verdict["ok"] is False
    assert verdict["blocked"] is False
    assert "partial PostgreSQL target" in verdict["reason"]


def test_operator_database_name_is_refused(monkeypatch, tmp_path):
    env = _disposable_env(monkeypatch, tmp_path)
    env["PRACE_DB_NAME"] = "prace_synthetic"
    verdict = guard.verify_target(env)
    assert verdict["ok"] is False
    assert verdict["blocked"] is False
    assert "operator database name" in verdict["reason"]


def test_marker_alone_is_not_enough_without_ownership(monkeypatch):
    env = dict(FULL_TARGET, PRACE_DISPOSABLE_TARGET="1")
    verdict = guard.verify_target(env)
    assert verdict["ok"] is False
    assert verdict["blocked"] is False
    assert "PRACE_DISPOSABLE_OWNERSHIP is required" in verdict["reason"]


def test_missing_marker_is_refused(monkeypatch, tmp_path):
    env = dict(FULL_TARGET)
    env["PRACE_DISPOSABLE_OWNERSHIP"] = str(_ownership(monkeypatch, tmp_path))
    verdict = guard.verify_target(env)
    assert verdict["ok"] is False
    assert verdict["blocked"] is False
    assert "PRACE_DISPOSABLE_TARGET=1" in verdict["reason"]


def test_ownership_record_must_flag_disposable(monkeypatch, tmp_path):
    env = dict(FULL_TARGET, PRACE_DISPOSABLE_TARGET="1")
    env["PRACE_DISPOSABLE_OWNERSHIP"] = str(
        _ownership(monkeypatch, tmp_path, disposable=False))
    verdict = guard.verify_target(env)
    assert verdict["ok"] is False
    assert verdict["blocked"] is False
    assert "disposable: true" in verdict["reason"]


def test_ownership_record_must_name_the_target(monkeypatch, tmp_path):
    env = dict(FULL_TARGET, PRACE_DISPOSABLE_TARGET="1")
    env["PRACE_DISPOSABLE_OWNERSHIP"] = str(
        _ownership(monkeypatch, tmp_path, name="some_other_db"))
    verdict = guard.verify_target(env)
    assert verdict["ok"] is False
    assert "ownership record names" in verdict["reason"]


def test_marker_lock_and_ownership_accept_disposable_target(monkeypatch, tmp_path):
    monkeypatch.setattr(guard, "_try_exclusive_lock",
                        lambda values, key: {"acquired": True})
    env = _disposable_env(monkeypatch, tmp_path)
    verdict = guard.verify_target(env)
    assert verdict["ok"] is True
    assert verdict["target"] == "prace_synthetic_test"
    assert verdict["lock"]["acquired"] is True
    assert verdict["lock_key"] == guard.DEFAULT_LOCK_KEY


def test_unreachable_cluster_blocks_with_valid_disposable(monkeypatch, tmp_path):
    monkeypatch.setattr(guard, "_try_exclusive_lock",
                        lambda values, key: {"acquired": False, "reason": "n/a"})
    env = _disposable_env(monkeypatch, tmp_path)
    verdict = guard.verify_target(env)
    assert verdict["ok"] is False
    assert verdict["blocked"] is True


def test_lock_key_validation():
    with pytest.raises(ValueError):
        guard.lock_key({"PRACE_DISPOSABLE_LOCK_KEY": "not-a-number"})
    with pytest.raises(ValueError):
        guard.lock_key({"PRACE_DISPOSABLE_LOCK_KEY": "0"})
    assert guard.lock_key({}) == guard.DEFAULT_LOCK_KEY
    assert guard.lock_key({"PRACE_DISPOSABLE_LOCK_KEY": "77"}) == 77


def test_exclusive_cleanup_sql_holds_lock_across_operation():
    sql = guard.exclusive_cleanup_sql("DELETE FROM release1a_membership;", lock_key_value=77)
    assert "SELECT pg_advisory_lock(77);" in sql
    assert "DELETE FROM release1a_membership;" in sql
    assert "SELECT pg_advisory_unlock(77);" in sql
    assert sql.index("advisory_lock(77)") < sql.index("DELETE FROM") < sql.index("advisory_unlock(77)")


def test_cleanup_env_carries_password_but_guard_sees_no_raw_secret(monkeypatch, tmp_path):
    env = _disposable_env(monkeypatch, tmp_path)
    verdict = guard.verify_target(env)
    assert "synthetic-test-password" not in str(verdict)


def test_psql_probe_command_is_pure_sql_with_tls_env():
    values = dict(FULL_TARGET, PRACE_DB_SSLMODE="verify-full",
                  PRACE_DB_SSLROOTCERT="/etc/ssl/root.crt")
    argv, env = guard.psql_probe_command(values, key=77)
    assert argv[0] == guard.PSQL
    idx = argv.index("-Atc")
    sql = argv[idx + 1]
    assert "\\set" not in sql
    assert "\\" not in sql
    assert "SELECT pg_try_advisory_lock(77);" in sql
    assert "SELECT pg_advisory_unlock(77);" in sql
    assert "-v" in argv and argv[argv.index("-v") + 1] == "ON_ERROR_STOP=1"
    assert argv[argv.index("-d") + 1] == FULL_TARGET["PRACE_DB_NAME"]
    assert env["PGPASSWORD"] == FULL_TARGET["PRACE_DB_PASSWORD"]
    assert env["PGSSLMODE"] == "verify-full"
    assert env["PGSSLROOTCERT"] == "/etc/ssl/root.crt"


def test_psql_env_omits_tls_vars_when_not_configured():
    argv, env = guard.psql_probe_command(dict(FULL_TARGET), key=7)
    assert "PGSSLMODE" not in env
    assert "PGSSLROOTCERT" not in env
    assert env["PGPASSWORD"] == FULL_TARGET["PRACE_DB_PASSWORD"]


def test_psql_env_preserves_caller_target_and_ownership_keys():
    """Regression: ``psql_env`` is called by cleanup with the caller-supplied
    worker env that carries PRACE_DB_* and the disposable marker / ownership
    record path. ``verify_target`` then resolves the same target — a mislayered
    helper that rebuilt from ``os.environ`` caused a silent ``no PostgreSQL
    target`` verdict and a follow-on ``KeyError('lock_key')`` in the cleanup
    caller. The helper now preserves every caller-supplied key.
    """
    values = dict(FULL_TARGET,
                  PRACE_DISPOSABLE_TARGET="1",
                  PRACE_DISPOSABLE_OWNERSHIP="/tmp/ownership.json")
    env = guard.psql_env(values)
    for key in ("PRACE_DB_NAME", "PRACE_DB_USER", "PRACE_DB_PASSWORD",
                "PRACE_DB_HOST", "PRACE_DB_PORT", "PRACE_DISPOSABLE_TARGET",
                "PRACE_DISPOSABLE_OWNERSHIP"):
        assert env[key] == values[key], key
    assert env["PGPASSWORD"] == values["PRACE_DB_PASSWORD"]


def test_collect_target_carries_optional_tls_values():
    env = dict(FULL_TARGET, PRACE_DB_SSLMODE="  verify-full  ",
               PRACE_DB_SSLROOTCERT=" /etc/ssl/root.crt ")
    target = guard._collect_target(env)
    assert target["values"]["PRACE_DB_SSLMODE"] == "verify-full"
    assert target["values"]["PRACE_DB_SSLROOTCERT"] == "/etc/ssl/root.crt"