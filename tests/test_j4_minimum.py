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
    Document, DocumentVersion, WorkerIdentityRevision,
)
from portal.release1a.services import (
    create_assignment, create_worker, prepare_a1, StaleWrite, current_a1_source, current_identity_source,
)
from portal.release1a.a1_exports import export_input_case
from src.document_core.serialization import result_hash


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
        from src.document_core.serialization import result_hash

        org, user = _setup_org_user("synthetic-j4-h", "J4 hash")
        worker = _make_worker(user, org)
        _make_assignment(user, org, worker, date(2026, 9, 1), date(2026, 9, 30))

        case = prepare_a1(user, org, worker)

        # The stored J4 snapshot is schema-versioned; its digest is the
        # ``source_hash`` the read-time integrity checks compare against.
        self.assertEqual(case.source_snapshot_json["schema_version"], "a1-input-1")
        self.assertIn("profile", case.source_snapshot_json)
        self.assertIn("assignments", case.source_snapshot_json)
        self.assertEqual(case.source_hash, result_hash(case.source_snapshot_json))


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


class TestJ4LegacyExportSourceBinding(TransactionTestCase):
    """Out-of-band mutations that bypass the canonical services layer must
    not leak into the legacy export path under the original case hash.

    ``_current_input_snapshot`` now recomputes ``current_a1_source``
    (the canonical J4 live-hashing contract for profile + assignment
    facts/version/state/dates) before rebuilding the legacy row shape,
    so direct ``Assignment.a1_facts_json`` writes and
    ``Worker.family_name`` writes that never set ``is_stale`` are
    rejected as ``A1_INPUT_STALE``.
    """

    def test_legacy_export_binds_live_fact_drift_without_version_bump(self):
        """Directly overwriting a1_facts_json without using
        update_assignment_facts (which bumps version and sets is_stale)
        must still be caught by the live-hash comparison.
        """
        org, user = _setup_org_user("synthetic-j4-fact-drift", "J4 fact drift")
        worker = _make_worker(user, org)
        _make_assignment(user, org, worker, date(2026, 9, 1), date(2026, 9, 30))
        facts = {
            "status_profile": "employee_multi_state",
            "employment": {
                "employer_id": "12345678",
                "employer_name": "Original GmbH",
                "street": "Pracovní",
                "house_number": "1",
                "city": "Mnichov",
                "postal_code": "12345",
                "country_code": "DE",
            },
            "activity": {"name": "Test role", "address": "DE, CZ"},
            "institution": {"resolved_ossz": "OSSZ Děčín", "profile_key": "decin"},
        }
        assignment = Assignment.objects.get(organization=org, worker=worker)
        Assignment.objects.filter(pk=assignment.pk).update(
            a1_facts_json=facts, version=1
        )
        case = prepare_a1(user, org, worker)
        export_input_case(user, org, case.pk)
        # Direct DB mutation — no version bump, no is_stale set.
        Assignment.objects.filter(pk=assignment.pk).update(
            a1_facts_json={**facts, "employment": {**facts["employment"], "employer_name": "Drift GmbH"}}
        )
        with self.assertRaises(StaleWrite):
            export_input_case(user, org, case.pk)


class TestJ4IdentityBinding(TransactionTestCase):
    """J4 identity source binding: new-contract cases carry live identity
    content; legacy rows adopt once and then drift is blocked."""

    def test_prepare_binds_live_identity_and_blocks_confirmed_field_mutation(self):
        org, user = _setup_org_user("synthetic-j4-identity-bind", "J4 identity bind")
        worker = _make_worker(user, org, activity_profile="self_employed")
        assignment, _ = _make_assignment(user, org, worker, date(2026, 9, 1), date(2026, 9, 30))
        Assignment.objects.filter(pk=assignment.pk).update(
            a1_facts_json={
                "status_profile": "self_employed_multi_state",
                "employment": {"employer_name": "Bind GmbH"},
                "activity": {"name": "Test role", "address": "DE, CZ"},
                "institution": {"resolved_ossz": "OSSZ Děčín", "profile_key": "decin"},
            },
            version=1,
        )
        doc = Document.objects.create(
            organization=org, worker=worker, opaque_key="synthetic-identity-doc",
            sha256="f" * 64, content_type="image/png", purpose="worker_intake",
        )
        version = DocumentVersion.objects.create(
            organization=org, document=doc, version_number=1, opaque_key="v1",
            sha256="e" * 64, content_type="image/png", byte_size=1,
        )
        WorkerIdentityRevision.objects.create(
            organization=org, worker=worker, source_document=doc, source_version=version,
            revision_number=1, confirmed_fields={"birth_place": "Syntetický"},
            confirmed_by=user,
        )

        case = prepare_a1(user, org, worker)
        self.assertEqual(case.source_snapshot_json["source_contract"], "a1-j4-identity-v1")
        identity = case.source_snapshot_json["identity"]["identity_revision"]
        self.assertEqual(identity["fields_sha256"], result_hash({"birth_place": "Syntetický"}))
        export_input_case(user, org, case.pk)

        WorkerIdentityRevision.objects.filter(pk=identity["ref"]).update(confirmed_fields={"birth_place": "AFTER"})
        with self.assertRaises(StaleWrite):
            export_input_case(user, org, case.pk)

    def test_legacy_row_adopts_identity_binding_once_then_blocks_drift(self):
        org, user = _setup_org_user("synthetic-j4-legacy-bind", "J4 legacy bind")
        worker = _make_worker(user, org, activity_profile="self_employed")
        assignment, _ = _make_assignment(user, org, worker, date(2026, 9, 1), date(2026, 9, 30))
        Assignment.objects.filter(pk=assignment.pk).update(
            a1_facts_json={
                "status_profile": "self_employed_multi_state",
                "employment": {"employer_name": "Legacy GmbH"},
                "activity": {"name": "Test", "address": "DE, CZ"},
                "institution": {"resolved_ossz": "OSSZ Děčín", "profile_key": "decin"},
            },
            version=1,
        )
        doc = Document.objects.create(
            organization=org, worker=worker, opaque_key="synthetic-legacy-doc",
            sha256="d" * 64, content_type="image/png", purpose="worker_intake",
        )
        version = DocumentVersion.objects.create(
            organization=org, document=doc, version_number=1, opaque_key="v1",
            sha256="c" * 64, content_type="image/png", byte_size=1,
        )
        revision = WorkerIdentityRevision.objects.create(
            organization=org, worker=worker, source_document=doc, source_version=version,
            revision_number=1, confirmed_fields={"birth_place": "Legacy"},
            confirmed_by=user,
        )

        profile, normalized, _ = current_a1_source(worker, org)
        legacy_snapshot = {
            "schema_version": "a1-input-1",
            "profile": profile,
            "assignments": normalized,
        }
        legacy_hash = result_hash(legacy_snapshot)
        case = A1Case.objects.create(
            organization=org, worker=worker, source_hash=legacy_hash,
            source_snapshot_json=legacy_snapshot,
            readiness=A1Case.Readiness.READY,
            is_stale=False,
        )
        export_input_case(user, org, case.pk)
        case.refresh_from_db()
        self.assertEqual(case.bound_identity_sha256, result_hash(current_identity_source(worker, org)))
        self.assertTrue(
            AuditEvent.objects.filter(event_type="a1.identity_revision_bound_legacy", object_ref=f"a1:{case.pk}").exists()
        )
        WorkerIdentityRevision.objects.filter(pk=revision.pk).update(confirmed_fields={"birth_place": "DRIFT"})
        with self.assertRaises(StaleWrite):
            export_input_case(user, org, case.pk)

    def test_legacy_export_binds_worker_projection_drift(self):
        """Changing a worker projection field (family_name) via a direct
        DB write without is_stale must be caught.
        """
        org, user = _setup_org_user("synthetic-j4-proj-drift", "J4 proj drift")
        worker = _make_worker(user, org)
        _make_assignment(user, org, worker, date(2026, 9, 1), date(2026, 9, 30))
        Assignment.objects.filter(
            organization=org, worker=worker
        ).update(
            a1_facts_json={
                "status_profile": "employee_multi_state",
                "employment": {"employer_name": "Acme GmbH"},
                "activity": {"name": "Test", "address": "DE, CZ"},
                "institution": {"resolved_ossz": "OSSZ Děčín", "profile_key": "decin"},
            },
            version=1,
        )
        case = prepare_a1(user, org, worker)
        export_input_case(user, org, case.pk)
        # Direct worker-projection write — no is_stale set.
        Worker.objects.filter(pk=worker.pk).update(family_name="ProjDrift")
        with self.assertRaises(StaleWrite):
            export_input_case(user, org, case.pk)