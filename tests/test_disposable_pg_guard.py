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