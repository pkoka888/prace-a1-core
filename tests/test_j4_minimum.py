"""J4 minimum tests: source snapshot, staleness, receipt binding, notes.

Covers the four minimum improvements:
    1. source_snapshot_json persisted on every prepare_a1
    2. is_stale transitions tracked (latent bug fix)
    3. prepared_artifact_hash bound to PRACE_RELEASE_MANIFEST when present
    4. notes persisted on a1_case_detail approval

Plus regenerate semantics:
    5. regenerate with unchanged source clears is_stale, no new case
    6. regenerate with changed source creates a new case

Synthetic only; no real private data, scans, or PII.
"""
import json
import os
import tempfile
import time
from datetime import date
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
from django.test import Client, TransactionTestCase, override_settings
from allauth.mfa.models import Authenticator

from portal.release1a.models import (
    A1Case, AuditEvent, Assignment, Membership, Organization, Worker,
)
from portal.release1a.services import (
    create_assignment, create_worker, prepare_a1,
)


def _mfa_login(client, user, *, password="test-m2"):
    """Authenticate and set allauth session state so require_org_membership
    passes MFA without a real TOTP code. Mirrors tests/m2/test_views.py."""
    client.login(username=user.username, password=password)
    sk = client.session.session_key
    if not Authenticator.objects.filter(user=user, type=Authenticator.Type.TOTP).exists():
        Authenticator.objects.create(
            user=user, type=Authenticator.Type.TOTP,
            data={"secret": "JBSWY3DPEHPK3PXP"},
        )
    s = SessionStore(session_key=sk)
    s["account_authentication_methods"] = [
        {"method": "password", "at": int(time.time())},
        {"method": "mfa", "type": "totp", "at": int(time.time())},
    ]
    s.save()


@pytest.fixture(autouse=True)
def _patch_storage(tmp_path):
    config = override_settings(
        DOCUMENT_STORAGE_ROOT=str(tmp_path / "storage"),
        MEDIA_ROOT=str(tmp_path / "media"),
        STATIC_ROOT=str(tmp_path / "static"),
    )
    config.enable()
    yield
    config.disable()


def _make_worker(user, org, **overrides):
    defaults = dict(
        given_name="Syntet", family_name="Pracovník",
        birth_date=date(1990, 1, 1), activity_profile="employee",
    )
    defaults.update(overrides)
    return create_worker(user, org, **defaults)


def _make_assignment(user, org, worker, start, end):
    return create_assignment(
        user, org, worker, start=start, end=end,
        workplace_label="Syntetické", activity_label="Test",
    )


def _setup_org_user(key, label):
    org = Organization.objects.create(key=key, label=label)
    user = get_user_model().objects.create_user(key + "-user", password="test-m2")
    Membership.objects.create(user=user, organization=org, role="jan_planner")
    Authenticator.objects.create(user=user, type=Authenticator.Type.TOTP, data={})
    return org, user


class TestJ4SnapshotPersisted(TransactionTestCase):
    def test_source_snapshot_persisted_with_profile_and_assignments(self):
        from django.conf import settings
        if hasattr(settings, "PRACE_RELEASE_MANIFEST"):
            del settings.PRACE_RELEASE_MANIFEST
        org, user = _setup_org_user("synthetic-j4-snap", "J4 snap")
        worker = _make_worker(user, org)
        _make_assignment(user, org, worker, date(2026, 8, 1), date(2026, 8, 15))

        case = prepare_a1(user, org, worker)

        self.assertEqual(case.readiness, "ready")
        self.assertIn("profile", case.source_snapshot_json)
        self.assertIn("assignments", case.source_snapshot_json)
        self.assertEqual(
            case.source_snapshot_json["profile"]["given_name"], "Syntet",
        )
        self.assertEqual(len(case.source_snapshot_json["assignments"]), 1)
        self.assertEqual(
            case.source_snapshot_json["assignments"][0]["start"],
            "2026-08-01",
        )

    def test_source_hash_matches_proof_contract(self):
        from prototypes.architecture.adr001.proof_contract import stable_hash
        org, user = _setup_org_user("synthetic-j4-h", "J4 hash")
        worker = _make_worker(user, org)
        assignment, _ = _make_assignment(user, org, worker, date(2026, 9, 1), date(2026, 9, 30))

        case = prepare_a1(user, org, worker)

        expected = stable_hash({
            "profile": {
                "given_name": worker.given_name,
                "family_name": worker.family_name,
                "birth_date": str(worker.birth_date),
                "activity_profile": worker.activity_profile,
            },
            "assignments": [{"id": assignment.pk, "start": "2026-09-01", "end": "2026-09-30",
                             "workplace_label": "Syntetické", "activity_label": "Test",
                             "state": assignment.state, "version": assignment.version}],
        })
        self.assertEqual(case.source_hash, expected)


class TestJ4StalenessTransitions(TransactionTestCase):
    def test_first_prepare_marks_is_stale_false(self):
        org, user = _setup_org_user("synthetic-j4-fresh", "J4 fresh")
        worker = _make_worker(user, org)
        _make_assignment(user, org, worker, date(2026, 8, 1), date(2026, 8, 15))

        case = prepare_a1(user, org, worker)
        self.assertFalse(case.is_stale)

    def test_re_prepare_with_no_change_keeps_is_stale_false(self):
        org, user = _setup_org_user("synthetic-j4-unchanged", "unchanged")
        worker = _make_worker(user, org)
        _make_assignment(user, org, worker, date(2026, 8, 1), date(2026, 8, 15))

        case1 = prepare_a1(user, org, worker)
        case2 = prepare_a1(user, org, worker)
        self.assertFalse(case1.is_stale)
        self.assertFalse(case2.is_stale)
        self.assertEqual(case1.source_hash, case2.source_hash)

    def test_assignment_change_marks_previous_stale(self):
        org, user = _setup_org_user("synthetic-j4-stale", "stale")
        worker = _make_worker(user, org)
        _make_assignment(user, org, worker, date(2026, 8, 1), date(2026, 8, 15))
        case1 = prepare_a1(user, org, worker)

        _make_assignment(user, org, worker, date(2026, 9, 1), date(2026, 9, 30))
        prepare_a1(user, org, worker)

        case1.refresh_from_db()
        self.assertTrue(case1.is_stale)


class TestJ4ReceiptBinding(TransactionTestCase):
    def test_receipt_bound_when_manifest_configured(self):
        org, user = _setup_org_user("synthetic-j4-receipt", "receipt")
        worker = _make_worker(user, org)
        _make_assignment(user, org, worker, date(2026, 8, 1), date(2026, 8, 15))

        manifest = {
            "git_commit": "0" * 40,
            "app_build_id": "testbuild00000001",
            "generated_at": "2026-09-07T00:00:00+00:00",
        }
        with override_settings(PRACE_RELEASE_MANIFEST=manifest):
            case = prepare_a1(user, org, worker)

        self.assertEqual(case.receipt_build_id, "testbuild00000001")
        self.assertEqual(case.receipt_git_commit, "0" * 40)
        self.assertEqual(case.prepared_artifact_hash, "")
        self.assertFalse(case.artifact_reference)

    def test_receipt_falls_back_when_manifest_unset(self):
        from django.conf import settings
        org, user = _setup_org_user("synthetic-j4-fallback", "fallback")
        worker = _make_worker(user, org)
        _make_assignment(user, org, worker, date(2026, 8, 1), date(2026, 8, 15))

        with override_settings(PRACE_RELEASE_MANIFEST=None):
            case = prepare_a1(user, org, worker)

        self.assertEqual(case.receipt_build_id, "")
        self.assertEqual(case.receipt_git_commit, "")
        self.assertEqual(case.prepared_artifact_hash, "")


class TestJ4NotesPersistence(TransactionTestCase):
    def test_notes_persisted_on_approval(self):
        org, user = _setup_org_user("synthetic-j4-notes", "notes")
        worker = _make_worker(user, org)
        _make_assignment(user, org, worker, date(2026, 8, 1), date(2026, 8, 15))
        case = prepare_a1(user, org, worker)

        client = Client()
        _mfa_login(client, user)
        response = client.post(
            f"/a1/{case.pk}/",
            data={"decision": "approve", "external_status": "submitted",
                  "notes": "Syntetická poznámka k rozhodnutí"},
        )
        self.assertEqual(response.status_code, 302)
        case.refresh_from_db()
        self.assertEqual(case.external_status, "submitted")
        self.assertEqual(case.notes, "Syntetická poznámka k rozhodnutí")

    def test_notes_persisted_on_denial(self):
        org, user = _setup_org_user("synthetic-j4-deny", "deny")
        worker = _make_worker(user, org)
        _make_assignment(user, org, worker, date(2026, 8, 1), date(2026, 8, 15))
        case = prepare_a1(user, org, worker)

        client = Client()
        _mfa_login(client, user)
        response = client.post(
            f"/a1/{case.pk}/",
            data={"decision": "deny", "notes": "Zamítnuto — chybí údaj"},
        )
        self.assertEqual(response.status_code, 302)
        case.refresh_from_db()
        self.assertEqual(case.external_status, "denied")
        self.assertEqual(case.notes, "Zamítnuto — chybí údaj")

    def test_notes_empty_when_not_provided(self):
        org, user = _setup_org_user("synthetic-j4-empty-notes", "empty")
        worker = _make_worker(user, org)
        _make_assignment(user, org, worker, date(2026, 8, 1), date(2026, 8, 15))
        case = prepare_a1(user, org, worker)

        client = Client()
        _mfa_login(client, user)
        response = client.post(
            f"/a1/{case.pk}/",
            data={"decision": "approve", "external_status": "submitted"},
        )
        self.assertEqual(response.status_code, 302)
        case.refresh_from_db()
        self.assertEqual(case.external_status, "submitted")
        self.assertEqual(case.notes, "")


class TestJ4RegenerateSemantics(TransactionTestCase):
    def test_regenerate_with_unchanged_source_clears_stale(self):
        org, user = _setup_org_user("synthetic-j4-reg-clear", "reg clear")
        worker = _make_worker(user, org)
        _make_assignment(user, org, worker, date(2026, 8, 1), date(2026, 8, 15))
        case = prepare_a1(user, org, worker)
        case.is_stale = True
        case.save(update_fields=["is_stale"])

        client = Client()
        _mfa_login(client, user)
        response = client.post(f"/a1/{case.pk}/regenerate/")
        self.assertEqual(response.status_code, 302)

        case.refresh_from_db()
        self.assertFalse(case.is_stale)
        self.assertEqual(
            A1Case.objects.filter(organization=org, worker=worker).count(),
            1,
        )
        self.assertTrue(
            AuditEvent.objects.filter(
                event_type="a1.regenerated_no_change",
                object_ref=f"a1:{case.pk}",
            ).exists()
        )

    def test_regenerate_with_changed_source_creates_new_case(self):
        org, user = _setup_org_user("synthetic-j4-reg-new", "reg new")
        worker = _make_worker(user, org)
        _make_assignment(user, org, worker, date(2026, 8, 1), date(2026, 8, 15))
        case1 = prepare_a1(user, org, worker)

        _make_assignment(user, org, worker, date(2026, 9, 1), date(2026, 9, 30))

        client = Client()
        _mfa_login(client, user)
        response = client.post(f"/a1/{case1.pk}/regenerate/")
        self.assertEqual(response.status_code, 302)

        self.assertEqual(
            A1Case.objects.filter(organization=org, worker=worker).count(),
            2,
        )
        case2 = (
            A1Case.objects
            .filter(organization=org, worker=worker)
            .order_by("-id")
            .first()
        )
        self.assertNotEqual(case1.source_hash, case2.source_hash)

    def test_regenerate_blocked_for_issued_status(self):
        org, user = _setup_org_user("synthetic-j4-reg-block", "reg block")
        worker = _make_worker(user, org)
        _make_assignment(user, org, worker, date(2026, 8, 1), date(2026, 8, 15))
        case = prepare_a1(user, org, worker)
        case.external_status = "issued"
        case.save(update_fields=["external_status"])

        client = Client()
        _mfa_login(client, user)
        response = client.post(f"/a1/{case.pk}/regenerate/")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            A1Case.objects.filter(organization=org, worker=worker).count(),
            1,
        )