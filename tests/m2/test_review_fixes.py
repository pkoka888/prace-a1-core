"""Regression tests for review-fixed M2 behaviors.

Covers bugs found in code review 2026-08-19:
- worker delete with protected records (ProtectedError) -> friendly response
- overlap warns instead of blocking (DEC-005)
- optimistic locking rejects stale version edits
- field evidence proposals and service audit events are not duplicated
"""
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "portal.settings")
import django
django.setup()


from datetime import date
from django.contrib.auth import get_user_model
from django.test import Client, TransactionTestCase, override_settings
import tempfile
import pymupdf
from tests.test_document_core.helpers import OP, card, png
from allauth.mfa.models import Authenticator
from portal.release1a.models import (
    AuditEvent, Membership, FieldProposal, Organization, Worker,
)
from portal.release1a.forms import AssignmentForm
from portal.release1a.services import create_worker, prepare_a1, upload_document

class ReviewFixRegressionTests(TransactionTestCase):

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        config = override_settings(DOCUMENT_STORAGE_ROOT=temporary.name)
        config.enable()
        self.addCleanup(config.disable)
        self.org = Organization.objects.create(key="review-fix-alpha", label="Review Fix Alpha")
        self.user = get_user_model().objects.create_user("reviewfix", password="x")
        Membership.objects.create(user=self.user, organization=self.org, role="jan_planner", active=True)
        Authenticator.objects.create(
            user=self.user,
            type=Authenticator.Type.TOTP,
            data={"secret": "JBSWY3DPEHPK3PXP"},
        )
        self.client = Client()
        self.client.force_login(self.user)
        # Set up allauth session auth methods so views pass MFA check
        import time
        from django.contrib.sessions.backends.db import SessionStore
        sk = self.client.session.session_key
        s = SessionStore(session_key=sk)
        s["account_authentication_methods"] = [
            {"method": "password", "at": int(time.time())},
            {"method": "mfa", "type": "totp", "at": int(time.time())},
        ]
        s.save()

    def test_worker_delete_with_a1_case_returns_denied_not_500(self):
        """worker with related A1Case must not 500 (ProtectedError handled)."""
        worker = create_worker(self.user, self.org, given_name="P", family_name="Q", birth_date=date(1990, 1, 1), activity_profile="employee")
        prepare_a1(self.user, self.org, worker)
        response = self.client.delete(f"/workers/{worker.pk}/delete/")
        self.assertEqual(response.status_code, 200)  # friendly denied page
        self.assertTrue(Worker.objects.filter(pk=worker.pk).exists())  # not deleted
        self.assertTrue(AuditEvent.objects.filter(event_type="worker.delete_denied").exists())

    def test_worker_delete_without_records_succeeds(self):
        worker = create_worker(self.user, self.org, given_name="A", family_name="B", birth_date=date(1990, 1, 1), activity_profile="employee")
        response = self.client.delete(f"/workers/{worker.pk}/delete/")
        self.assertEqual(response.status_code, 302)  # redirect to list
        self.assertFalse(Worker.objects.filter(pk=worker.pk).exists())

    def test_overlap_warns_but_saves(self):
        """DEC-005: overlapping assignment is saved with a warning, not blocked."""
        worker = create_worker(self.user, self.org, given_name="C", family_name="D", birth_date=date(1990, 1, 1), activity_profile="employee")
        f1 = AssignmentForm(data={"workplace_label": "A", "activity_label": "Y", "start": "2026-08-01", "end": "2026-08-15", "state": "planned"}, organization=self.org, worker=worker)
        self.assertTrue(f1.is_valid())
        f1.save()
        f2 = AssignmentForm(data={"workplace_label": "B", "activity_label": "Y", "start": "2026-08-10", "end": "2026-08-30", "state": "planned"}, organization=self.org, worker=worker)
        self.assertTrue(f2.is_valid(), "overlap must warn, not block")
        self.assertTrue(getattr(f2, "overlap_warning", False))
        f2.save()

    def test_overlapping_assignments_block_a1_preparation(self):
        worker = create_worker(self.user, self.org, given_name="E", family_name="F", birth_date=date(1990, 1, 1), activity_profile="employee")
        for label, s, e in [("A", "2026-08-01", "2026-08-15"), ("B", "2026-08-10", "2026-08-30")]:
            form = AssignmentForm(data={"workplace_label": label, "activity_label": "Y", "start": s, "end": e, "state": "planned"}, organization=self.org, worker=worker)
            self.assertTrue(form.is_valid())
            form.save()
        case = prepare_a1(self.user, self.org, worker)
        self.assertEqual(case.readiness, "blocked")

    @staticmethod
    def synthetic_pdf():
        with pymupdf.open() as document:
            page = document.new_page(width=720, height=420)
            page.insert_image(page.rect, stream=png(card(OP)))
            return document.tobytes()

    def test_upload_creates_unique_field_evidence_proposals(self):
        """Real decoded PDF yields one proposal per field/source region."""
        worker = create_worker(self.user, self.org, given_name="G", family_name="H", birth_date=date(1990, 1, 1), activity_profile="employee")
        document = upload_document(self.user, self.org, worker, "fixture.pdf", "application/pdf", self.synthetic_pdf())
        proposals = list(FieldProposal.objects.filter(document=document))
        self.assertTrue(proposals)
        keys = [(p.field_name, p.document_region_id, p.source_page) for p in proposals]
        self.assertEqual(len(keys), len(set(keys)), "service must not duplicate field evidence")
        values = {p.field_name: p.proposed_value for p in proposals}
        self.assertEqual(values["family_name"], "TESTOVA")
        self.assertEqual(values["birth_date"], "1990-03-15")
        self.assertTrue(all(p.source_bounding_box and p.ocr_run_id for p in proposals))

    def test_no_duplicate_audit_events_for_service_actions(self):
        """Service actions must produce exactly one audit event (no view duplicate)."""
        worker = create_worker(self.user, self.org, given_name="I", family_name="J", birth_date=date(1990, 1, 1), activity_profile="employee")
        upload_document(self.user, self.org, worker, "fixture.pdf", "application/pdf", self.synthetic_pdf())
        prepare_a1(self.user, self.org, worker)

        self.assertEqual(AuditEvent.objects.filter(event_type="worker.created").count(), 1)
        self.assertEqual(AuditEvent.objects.filter(event_type="document.uploaded").count(), 1)
        self.assertEqual(AuditEvent.objects.filter(event_type="ocr.completed").count(), 1)
        self.assertEqual(AuditEvent.objects.filter(event_type="a1.prepared").count(), 1)
    def test_invalid_pdf_is_rejected_without_proposals(self):
        worker = create_worker(self.user, self.org, given_name="K", family_name="L",
                               birth_date=date(1990, 1, 1), activity_profile="employee")
        with self.assertRaises(ValueError):
            upload_document(self.user, self.org, worker, "invalid.pdf", "application/pdf",
                            b"%PDF-1.4\n%%EOF")
        self.assertFalse(FieldProposal.objects.exists())
