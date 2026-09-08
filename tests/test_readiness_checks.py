"""Unit tests for portal.release1a.readiness_checks.

Each check function is exercised in isolation. No HTTP layer; no DB migrations.
"""
import hashlib
import json
import os
import stat
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from django.db import OperationalError

from portal.release1a import readiness_checks as rc


class TestSanitizeDetail:
    def test_none_becomes_empty(self):
        assert rc.sanitize_detail(None) == ""
        assert rc.sanitize_detail("") == ""

    def test_collapses_whitespace(self):
        assert rc.sanitize_detail("a\n\tb   d") == "a b d"

    def test_truncates(self):
        long = "x" * 200
        out = rc.sanitize_detail(long)
        assert len(out) == rc._DETAIL_MAX_LEN
        assert out.endswith("...")

    def test_non_string_coerced(self):
        assert rc.sanitize_detail(42) == "42"


class TestDbReachable:
    def test_returns_ok_on_select_one(self):
        cursor = MagicMock()
        cursor.__enter__.return_value.fetchone.return_value = (1,)
        connection = MagicMock()
        connection.cursor.return_value = cursor
        status, detail = rc.check_db_reachable(connection)
        assert status == "ok"
        assert detail == ""

    def test_returns_fail_on_unexpected_response(self):
        cursor = MagicMock()
        cursor.__enter__.return_value.fetchone.return_value = None
        connection = MagicMock()
        connection.cursor.return_value = cursor
        status, _ = rc.check_db_reachable(connection)
        assert status == "fail"

    def test_returns_fail_on_exception(self):
        connection = MagicMock()
        connection.cursor.return_value.__enter__.side_effect = OperationalError("x")
        status, detail = rc.check_db_reachable(connection)
        assert status == "fail"
        assert detail == "database_unavailable"


class TestStorageWritable:
    def test_returns_ok_on_writable_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            status, detail = rc.check_storage_writable(tmp)
        assert status == "ok"
        assert detail == ""

    def test_returns_fail_when_missing(self):
        status, detail = rc.check_storage_writable("/tmp/does-not-exist-readiness-xyz")
        assert status == "fail"
        assert detail == "storage_missing"

    def test_returns_fail_when_not_dir(self):
        with tempfile.NamedTemporaryFile() as f:
            status, detail = rc.check_storage_writable(f.name)
        assert status == "fail"
        assert detail == "storage_not_dir"

    def test_returns_fail_when_unwritable(self):
        if os.geteuid() == 0:
            pytest.skip("cannot enforce unwritable dir as root")
        with tempfile.TemporaryDirectory() as tmp:
            os.chmod(tmp, 0o500)
            try:
                status, detail = rc.check_storage_writable(tmp)
            finally:
                os.chmod(tmp, 0o700)
        assert status == "fail"
        assert detail == "storage_unwritable"

    def test_returns_fail_when_none(self):
        status, detail = rc.check_storage_writable(None)
        assert status == "fail"
        assert detail == "storage_unconfigured"


class TestRuntimePaths:
    def test_all_writable(self):
        with tempfile.TemporaryDirectory() as root:
            paths = {
                "a": root,
                "b": root,
            }
            status, detail = rc.check_runtime_paths(paths)
        assert status == "ok"
        assert detail == ""

    def test_missing_path_reported(self):
        with tempfile.TemporaryDirectory() as root:
            paths = {"a": root, "b": "/tmp/does-not-exist-readiness-xyz"}
            status, detail = rc.check_runtime_paths(paths)
        assert status == "fail"
        assert "missing:b" in detail

    def test_none_path_reported(self):
        with tempfile.TemporaryDirectory() as root:
            paths = {"a": root, "b": None}
            status, detail = rc.check_runtime_paths(paths)
        assert status == "fail"
        assert "missing:b" in detail

    def test_unwritable_reported(self):
        if os.geteuid() == 0:
            pytest.skip("cannot enforce unwritable dir as root")
        with tempfile.TemporaryDirectory() as root:
            os.chmod(root, 0o500)
            try:
                paths = {"a": root}
                status, detail = rc.check_runtime_paths(paths)
            finally:
                os.chmod(root, 0o700)
        assert status == "fail"
        assert "unwritable:a" in detail

    def test_empty_mapping_ok(self):
        assert rc.check_runtime_paths({}) == ("ok", "")


class TestReleaseManifest:
    def _make_manifest(self, tmp, **overrides):
        payload = {
            "git_commit": "0" * 40,
            "app_build_id": "0" * 16,
            "generated_at": "2026-09-07T00:00:00+00:00",
        }
        payload.update(overrides)
        path = Path(tmp) / "build_manifest.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path, payload

    def test_absent_path_ok(self):
        assert rc.check_release_manifest(None, None) == ("ok", "absent")

    def test_valid_manifest_with_matching_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, payload = self._make_manifest(tmp)
            expected = hashlib.sha256(path.read_bytes()).hexdigest()
            status, detail = rc.check_release_manifest(path, payload, expected)
        assert status == "ok"
        assert detail == ""

    def test_hash_mismatch_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, payload = self._make_manifest(tmp)
            status, detail = rc.check_release_manifest(path, payload, "0" * 64)
        assert status == "fail"
        assert detail == "manifest_hash_mismatch"

    def test_missing_required_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "build_manifest.json"
            path.write_text(json.dumps({"git_commit": "x"}), encoding="utf-8")
            status, detail = rc.check_release_manifest(
                path,
                {"git_commit": "x"},
                hashlib.sha256(path.read_bytes()).hexdigest(),
            )
        assert status == "fail"
        assert detail == "manifest_missing_key"

    def test_missing_file(self):
        status, detail = rc.check_release_manifest(
            "/tmp/does-not-exist-readiness-manifest.json",
            None,
        )
        assert status == "fail"
        assert detail == "manifest_missing"

    def test_unparsed_payload_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "build_manifest.json"
            path.write_text(json.dumps({"git_commit": "x"}), encoding="utf-8")
            status, detail = rc.check_release_manifest(path, None)
        assert status == "fail"
        assert detail == "manifest_unparsed"


class TestCsrfConfined:
    def test_empty_ok(self):
        assert rc.check_csrf_confined([]) == ("ok", "")
        assert rc.check_csrf_confined(None) == ("ok", "")

    def test_https_ok(self):
        assert rc.check_csrf_confined(["https://a.example"]) == ("ok", "")

    def test_http_rejected(self):
        status, detail = rc.check_csrf_confined(["http://insecure.example"])
        assert status == "fail"
        assert detail == "insecure_origin"

    def test_mixed_rejected(self):
        status, _ = rc.check_csrf_confined(
            ["https://ok.example", "http://bad.example"]
        )
        assert status == "fail"

    def test_non_string_rejected(self):
        status, _ = rc.check_csrf_confined(["https://ok.example", 42])
        assert status == "fail"


class TestAppLoaded:
    def test_returns_count(self):
        if not os.environ.get("DJANGO_SETTINGS_MODULE"):
            pytest.skip("requires DJANGO_SETTINGS_MODULE")
        import django
        from django.apps import apps as django_apps
        if not django_apps.ready:
            django.setup()
        status, detail = rc.check_app_loaded()
        assert status == "ok"
        assert "_apps" in detail