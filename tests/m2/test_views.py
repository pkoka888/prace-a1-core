"""M2 Sprint tests — View-layer validation for J1–J4 journeys."""
import os
import time
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "portal.settings")
import django
django.setup()


from datetime import date
import pytest
from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
from django.test import Client, TransactionTestCase, override_settings
import tempfile
from tests.test_document_core.helpers import OP, card, png
from allauth.mfa.models import Authenticator
from portal.release1a.models import (
    AuditEvent, Membership, Organization, Worker,
    Document, Assignment, A1Case
)

def _mfa_login(client, user):
    """
    Perform a Django login and set allauth session state so that
    require_org_membership passes MFA check without a real TOTP code.
    Creates a TOTP Authenticator for the user if one does not exist.
    """
    client.login(username=user.username, password="test-m2")
    sk = client.session.session_key
    if not Authenticator.objects.filter(user=user, type=Authenticator.Type.TOTP).exists():
        Authenticator.objects.create(
            user=user,
            type=Authenticator.Type.TOTP,
            data={"secret": "JBSWY3DPEHPK3PXP"},
        )
    s = SessionStore(session_key=sk)
    s["account_authentication_methods"] = [
        {"method": "password", "at": int(time.time())},
        {"method": "mfa", "type": "totp", "at": int(time.time())},
    ]
    s.save()


class M2ViewTests(TransactionTestCase):
    """Test M2 J1–J4 view layer — redirects, CRUD, audit."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        config = override_settings(DOCUMENT_STORAGE_ROOT=temporary.name)
        config.enable(); self.addCleanup(config.disable)
        self.org_alpha = Organization.objects.create(key="alpha-m2", label="Alpha M2")
        self.org_beta = Organization.objects.create(key="beta-m2", label="Beta M2")
        self.user = get_user_model().objects.create_user("m2user", password="test-m2")
        self.membership = Membership.objects.create(
            user=self.user, organization=self.org_alpha,
            role="jan_planner"
        )
        self.client = Client()

    def test_j1_dashboard_requires_login(self):
        """J1: Dashboard requires authentication."""
        response = self.client.get("/")
        # Should show unauthenticated state (not redirect)
        self.assertIn(response.status_code, [200, 302])
        if response.status_code == 200:
            self.assertContains(response, "Nepřihlášen")

    def test_j1_worker_list_requires_login(self):
        """J1: Worker list requires login."""
        response = self.client.get("/workers/")
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_j1_worker_list_authenticated(self):
        """J1: Worker list shows correctly when authenticated."""
        _mfa_login(self.client, self.user)
        response = self.client.get("/workers/")
        self.assertEqual(response.status_code, 200)

    def test_j1_worker_create_form_get(self):
        """J1: Worker create form renders."""
        _mfa_login(self.client, self.user)
        response = self.client.get("/workers/new/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "form")

    def test_j1_worker_create_post_success(self):
        """J1: Worker create POST creates worker + audit event."""
        _mfa_login(self.client, self.user)
        data = {
            "family_name": "TestWorker",
            "given_name": "Jan",
            "birth_date": "1990-01-01",
            "activity_profile": "self_employed",
            "state": "draft",
        }
        response = self.client.post("/workers/new/", data, follow=False)
        # Should redirect on success
        self.assertEqual(response.status_code, 302)
        # Worker should exist
        self.assertTrue(Worker.objects.filter(family_name="TestWorker").exists())
        # Audit event should be created
        self.assertTrue(AuditEvent.objects.filter(event_type="worker.created").exists())

    def test_j1_worker_create_post_validation_error(self):
        """J1: Worker create POST with invalid data shows errors."""
        _mfa_login(self.client, self.user)
        data = {
            "family_name": "",  # Empty
            "given_name": "",
            "birth_date": "",
            "activity_profile": "",
            "state": "",
        }
        response = self.client.post("/workers/new/", data)
        # Should re-render form (not redirect)
        self.assertEqual(response.status_code, 200)
        # No worker created
        self.assertEqual(Worker.objects.count(), 0)

    def test_j2_document_upload_requires_login(self):
        """J2: Document upload requires login."""
        worker = Worker.objects.create(
            organization=self.org_alpha,
            given_name="Test", family_name="Worker",
            birth_date=date(1990, 1, 1),
            activity_profile="self_employed",
        )
        response = self.client.get(f"/workers/{worker.pk}/documents/upload/")
        self.assertEqual(response.status_code, 302)

    def test_j3_assignment_create_form_get(self):
        """J3: Assignment create form renders."""
        _mfa_login(self.client, self.user)
        worker = Worker.objects.create(
            organization=self.org_alpha,
            given_name="Test", family_name="Worker",
            birth_date=date(1990, 1, 1),
            activity_profile="self_employed",
        )
        response = self.client.get(f"/workers/{worker.pk}/assignments/new/")
        self.assertEqual(response.status_code, 200)

    def test_j4_a1_prepare_form_get(self):
        """J4: A1 prepare form renders."""
        _mfa_login(self.client, self.user)
        worker = Worker.objects.create(
            organization=self.org_alpha,
            given_name="Test", family_name="Worker",
            birth_date=date(1990, 1, 1),
            activity_profile="self_employed",
        )
        response = self.client.get(f"/workers/{worker.pk}/a1/prepare/")
        self.assertEqual(response.status_code, 200)

    def test_tenant_isolation_in_views(self):
        """Tenant isolation: cross-org access returns 404."""
        _mfa_login(self.client, self.user)
        worker_beta = Worker.objects.create(
            organization=self.org_beta,
            given_name="Beta", family_name="Worker",
            birth_date=date(1990, 1, 1),
            activity_profile="self_employed",
        )
        # Alpha user trying to access beta worker detail → 404
        response = self.client.get(f"/workers/{worker_beta.pk}/")
        self.assertEqual(response.status_code, 404)

    def test_audit_events_for_j1_j2_j3_j4(self):
        """AuditEvent records for all J1–J4 actions."""
        from portal.release1a.services import (
            create_worker, upload_document, create_assignment, prepare_a1
        )
        # Ensure user has a TOTP authenticator (service functions require MFA)
        if not Authenticator.objects.filter(user=self.user, type=Authenticator.Type.TOTP).exists():
            Authenticator.objects.create(
                user=self.user,
                type=Authenticator.Type.TOTP,
                data={"secret": "JBSWY3DPEHPK3PXP"},
            )

        worker = create_worker(
            self.user, self.org_alpha,
            given_name="Syntetický", family_name="Pracovník",
            birth_date=date(1990, 1, 1), activity_profile="self_employed",
        )
        document = upload_document(
            self.user, self.org_alpha, worker,
            "fixture.png", "image/png", png(card(OP)),
        )
        _, _ = create_assignment(
            self.user, self.org_alpha, worker,
            start=date(2026, 8, 1), end=date(2026, 8, 15),
            workplace_label="Test", activity_label="Test",
        )
        case = prepare_a1(self.user, self.org_alpha, worker)

        # All 4 audit events present
        event_types = list(AuditEvent.objects.values_list("event_type", flat=True))
        self.assertIn("worker.created", event_types)
        self.assertIn("document.uploaded", event_types)
        self.assertIn("assignment.created", event_types)
        self.assertIn("a1.prepared", event_types)

        # No sensitive data in audit payloads
        for event in AuditEvent.objects.all():
            self.assertNotIn("Syntetický", event.object_ref)


class M2NavigationRegressionTests(TransactionTestCase):
    """Regression tests for navigation links - proves routes resolve correctly."""

    def setUp(self):
        self.org = Organization.objects.create(key="nav-org", label="Navigation Org")
        self.user = get_user_model().objects.create_user("navuser", password="test-m2")
        self.membership = Membership.objects.create(
            user=self.user, organization=self.org, role="admin"
        )
        self.client = Client()
        _mfa_login(self.client, self.user)
        self.worker = Worker.objects.create(
            organization=self.org,
            given_name="Navigace", family_name="Test",
            birth_date=date(1990, 1, 1),
            activity_profile="employee",
        )

    def test_workers_list_navigates(self):
        """Pracovníci → Zobrazit všechny links to /workers/"""
        response = self.client.get("/workers/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Navigace")

    def test_worker_detail_navigates(self):
        """Worker detail page renders without HTMX modal issues."""
        response = self.client.get(f"/workers/{self.worker.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Navigace")
        self.assertContains(response, "Test")
        self.assertNotContains(response, "hx-get", status_code=200)

    def test_dashboard_documents_link_resolves(self):
        """Dashboard Dokumenty link goes to /documents/"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="/documents/"')

    def test_dashboard_assignments_link_resolves(self):
        """Dashboard Přiřazení link goes to /assignments/"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="/assignments/"')

    def test_dashboard_a1_link_resolves(self):
        """Dashboard A1 případy link goes to /a1/"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="/a1/"')

    def test_document_list_navigates(self):
        """Global document list renders at /documents/"""
        response = self.client.get("/documents/")
        self.assertEqual(response.status_code, 200)

    def test_assignment_list_navigates(self):
        """Global assignment list renders at /assignments/"""
        response = self.client.get("/assignments/")
        self.assertEqual(response.status_code, 200)

    def test_a1_list_navigates(self):
        """Global A1 list renders at /a1/"""
        response = self.client.get("/a1/")
        self.assertEqual(response.status_code, 200)

    def test_intake_wizard_navigates(self):
        """Intake wizard renders at /workers/new/intake/"""
        response = self.client.get("/workers/new/intake/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Přidat pracovníka")

    def test_planned_pages_render(self):
        """Planned module pages show inactive message."""
        planned_modules = [
            "/partners/", "/jobs/", "/candidates/", "/requests/",
            "/capacity/", "/attendance/", "/communications/", "/finance/",
            "/invoices/", "/payroll-cz/", "/payroll-de/", "/integrations/",
            "/privacy/", "/admin/"
        ]
        for url in planned_modules:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, f"Failed for {url}")
            self.assertContains(response, "Funkce zatím není aktivní")

    def test_ocr_review_queue_navigates(self):
        """OCR review queue renders at /ocr-review/"""
        response = self.client.get("/ocr-review/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Kontrola OCR")

    def test_assignment_conflicts_navigates(self):
        """Assignment conflicts renders at /assignments/conflicts/"""
        response = self.client.get("/assignments/conflicts/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Konflikty přiřazení")

    def test_worker_archive_page_loads(self):
        """Worker archive confirmation page renders."""
        response = self.client.get(f"/workers/{self.worker.pk}/archive/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Archivovat")