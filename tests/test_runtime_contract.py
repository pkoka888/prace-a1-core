"""Tests for the synthetic-only runtime contract helpers and endpoints.

The contract is what infra edge probes consume; it must be:
-  sanitized: no secrets, no full paths, no identifiers
-  stable: same shape regardless of synthetic vs real posture
-  explicit: real_data is always False for M2

Synthetic only; no real private data.
"""
import os
from pathlib import Path

import pytest
from django.test import SimpleTestCase, Client, override_settings

from portal.release1a import runtime_contract


def _ensure_django_setup():
    import os
    import django
    from django.apps import apps as django_apps
    if django_apps.ready:
        return
    if not os.environ.get("DJANGO_SETTINGS_MODULE"):
        os.environ["DJANGO_SETTINGS_MODULE"] = "portal.settings_document_tests"
    django.setup()


class TestRuntimeContractHelpers:
    def setup_method(self, method):
        _ensure_django_setup()

    def test_runtime_mode_uses_settings_module_basename(self):
        with override_settings(SETTINGS_MODULE="portal.settings_supervised_synthetic"):
            assert runtime_contract.runtime_mode() == "settings_supervised_synthetic"

    def test_runtime_mode_handles_dotted_path(self):
        # Non-portal package paths return the full dotted name unchanged
        with override_settings(SETTINGS_MODULE="some.deep.module"):
            assert runtime_contract.runtime_mode() == "some.deep.module"

    def test_runtime_mode_handles_empty(self):
        with override_settings(SETTINGS_MODULE=""):
            assert runtime_contract.runtime_mode() == "unknown"

    def test_is_supervised_true_when_set(self):
        with override_settings(PRACE_SUPERVISED=True):
            assert runtime_contract.is_supervised() is True

    def test_is_supervised_false_when_unset(self):
        with override_settings(PRACE_SUPERVISED=False):
            assert runtime_contract.is_supervised() is False

    def test_synthetic_only_true_for_m2(self):
        assert runtime_contract.synthetic_only() is True

    def test_build_identity_from_manifest(self):
        with override_settings(PRACE_RELEASE_MANIFEST={
            "git_commit": "0" * 40,
            "app_build_id": "build-001",
            "generated_at": "2026-09-07T00:00:00+00:00",
        }):
            build_id, git_commit = runtime_contract.build_identity()
        assert build_id == "build-001"
        assert git_commit == "0" * 40

    def test_build_identity_empty_when_manifest_unset(self):
        with override_settings(PRACE_RELEASE_MANIFEST=None):
            build_id, git_commit = runtime_contract.build_identity()
        assert build_id == ""
        assert git_commit == ""

    def test_build_identity_handles_non_dict_manifest(self):
        with override_settings(PRACE_RELEASE_MANIFEST="not-a-dict"):
            build_id, git_commit = runtime_contract.build_identity()
        assert build_id == ""
        assert git_commit == ""

    def test_db_engine_returns_basename(self):
        with override_settings(DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3"}}):
            assert runtime_contract.db_engine() == "sqlite3"

    def test_db_engine_handles_missing_key(self):
        with override_settings(DATABASES={}):
            assert runtime_contract.db_engine() == ""

    def test_storage_root_basename_strips_full_path(self):
        with override_settings(DOCUMENT_STORAGE_ROOT="/var/www/example/runtime/portal/storage"):
            assert runtime_contract.storage_root_basename() == "storage"

    def test_storage_root_basename_handles_pathlib(self):
        with override_settings(DOCUMENT_STORAGE_ROOT=Path("/var/www/example/runtime/portal/storage")):
            assert runtime_contract.storage_root_basename() == "storage"

    def test_storage_root_basename_handles_none(self):
        with override_settings(DOCUMENT_STORAGE_ROOT=None):
            assert runtime_contract.storage_root_basename() == ""

    def test_mfa_required_true_when_totp_configured(self):
        with override_settings(MFA_SUPPORTED_TYPES=["totp"]):
            assert runtime_contract.mfa_required() is True

    def test_mfa_required_false_when_empty(self):
        with override_settings(MFA_SUPPORTED_TYPES=[]):
            assert runtime_contract.mfa_required() is False


class TestHealthPayload:
    def setup_method(self, method):
        _ensure_django_setup()

    def test_health_payload_shape(self):
        with override_settings(
            SETTINGS_MODULE="portal.settings_supervised_synthetic",
            PRACE_SUPERVISED=True,
            PRACE_RELEASE_MANIFEST={
                "git_commit": "a" * 40,
                "app_build_id": "build-x",
                "generated_at": "2026-09-07T00:00:00+00:00",
            },
        ):
            payload = runtime_contract.health_payload()
        assert payload["status"] == "synthetic-m2"
        assert payload["real_data"] is False
        assert payload["mode"] == "settings_supervised_synthetic"
        assert payload["supervised"] is True
        assert payload["build_id"] == "build-x"
        assert payload["git_commit"] == "a" * 40

    def test_health_payload_real_data_always_false(self):
        with override_settings(M2_SYNTHETIC_ONLY=True):
            assert runtime_contract.health_payload()["real_data"] is False


class TestSyntheticContractPayload:
    def setup_method(self, method):
        _ensure_django_setup()

    def test_payload_shape_is_complete(self):
        with override_settings(
            SETTINGS_MODULE="portal.settings_supervised_synthetic",
            PRACE_SUPERVISED=True,
            M2_SYNTHETIC_ONLY=True,
            MFA_SUPPORTED_TYPES=["totp"],
            PRACE_RELEASE_MANIFEST={
                "git_commit": "b" * 40,
                "app_build_id": "build-y",
                "generated_at": "2026-09-07T00:00:00+00:00",
            },
            DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3"}},
            DOCUMENT_STORAGE_ROOT="/srv/runtime/storage",
        ):
            payload = runtime_contract.synthetic_contract_payload()
        expected_keys = {
            "contract", "real_data", "mode", "supervised", "synthetic_only",
            "build_id", "git_commit", "db_engine", "storage_root",
            "mfa_required", "endpoints",
        }
        assert set(payload.keys()) == expected_keys
        assert payload["contract"] == "prace-synthetic-m2"
        assert payload["real_data"] is False
        assert payload["supervised"] is True
        assert payload["synthetic_only"] is True
        assert payload["db_engine"] == "sqlite3"
        assert payload["storage_root"] == "storage"
        assert payload["mfa_required"] is True
        assert payload["endpoints"]["live"] == "/health/"
        assert payload["endpoints"]["ready"] == "/readiness/"
        assert payload["endpoints"]["contract"] == "/synthetic/"

    def test_payload_does_not_leak_full_storage_path(self):
        secret_path = "/var/www/some/private/runtime/portal/storage"
        with override_settings(DOCUMENT_STORAGE_ROOT=secret_path):
            payload = runtime_contract.synthetic_contract_payload()
        assert secret_path not in str(payload)
        assert payload["storage_root"] == "storage"

    def test_payload_does_not_leak_secret_key(self):
        payload = runtime_contract.synthetic_contract_payload()
        # SECRET_KEY is intentionally never referenced by helpers
        assert "SECRET_KEY" not in payload
        assert "secret" not in {k.lower() for k in payload.keys()}

    def test_payload_endpoints_are_canonical(self):
        payload = runtime_contract.synthetic_contract_payload()
        assert payload["endpoints"]["live"] == "/health/"
        assert payload["endpoints"]["ready"] == "/readiness/"
        assert payload["endpoints"]["contract"] == "/synthetic/"


class TestProbeEndpoints:
    """HTTP-level tests for /health/, /readiness/, /synthetic/."""

    def setup_method(self, method):
        _ensure_django_setup()

    def test_health_returns_200_with_synthetic_payload(self):
        client = Client()
        r = client.get("/health/")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "synthetic-m2"
        assert body["real_data"] is False
        assert body["supervised"] is False  # default in document_tests
        assert "mode" in body
        assert "build_id" in body
        assert "git_commit" in body

    def test_health_does_not_query_db(self):
        client = Client()
        with override_settings(DATABASES={"default": {"ENGINE": "should.not.be.touched"}}):
            r = client.get("/health/")
        assert r.status_code == 200

    def test_synthetic_endpoint_returns_200_with_contract(self):
        client = Client()
        r = client.get("/synthetic/")
        assert r.status_code == 200
        body = r.json()
        assert body["contract"] == "prace-synthetic-m2"
        assert body["real_data"] is False
        assert "mode" in body
        assert "db_engine" in body
        assert "storage_root" in body
        assert "endpoints" in body

    def test_synthetic_endpoint_no_store_header(self):
        client = Client()
        r = client.get("/synthetic/")
        assert "no-store" in r["Cache-Control"]

    def test_health_endpoint_no_store_header(self):
        client = Client()
        r = client.get("/health/")
        assert "no-store" in r["Cache-Control"]

    def test_synthetic_endpoint_does_not_query_db(self):
        client = Client()
        with override_settings(DATABASES={"default": {"ENGINE": "should.not.be.touched"}}):
            r = client.get("/synthetic/")
        assert r.status_code == 200

    def test_synthetic_endpoint_unsafe_method_rejected(self):
        client = Client()
        r = client.post("/synthetic/")
        assert r.status_code == 405

    def test_health_endpoint_unsafe_method_rejected(self):
        client = Client()
        r = client.post("/health/")
        assert r.status_code == 405

    def test_synthetic_endpoint_payload_is_json(self):
        client = Client()
        r = client.get("/synthetic/")
        assert "application/json" in r["Content-Type"]

    def test_health_endpoint_payload_is_json(self):
        client = Client()
        r = client.get("/health/")
        assert "application/json" in r["Content-Type"]


class TestReadinessCarriesSyntheticFlags:
    """The readiness body must carry mode + supervised for edge correlation."""

    def setup_method(self, method):
        _ensure_django_setup()

    def test_readiness_body_contains_mode_and_supervised(self):
        client = Client()
        r = client.get("/readiness/")
        # 503 is acceptable when migrations not run; the body still carries the flags
        assert r.status_code in (200, 503)
        body = r.json()
        assert "mode" in body
        assert "supervised" in body
        assert "build_id" in body
        assert "git_commit" in body