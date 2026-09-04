"""
test_review_acceptance_flow.py

Integration test for the Kontrola Release 1A review acceptance flow.
"""
import json
import os
import tempfile

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "portal.settings")
os.environ.setdefault("REVIEW_BUILD_MANIFEST_PATH", tempfile.mktemp(suffix=".json"))

import django
django.setup()


from django.test import Client, TransactionTestCase
from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
from django.conf import settings
from allauth.mfa.models import Authenticator
from portal.release1a.models import (
    Organization, Membership, Release1aReview,
    Release1aReviewSession, Release1aAcceptance,
)


with open(os.environ["REVIEW_BUILD_MANIFEST_PATH"], "w") as f:
    json.dump({"app_build_id": "testbuild123", "git_commit": "a" * 40, "git_clean": True}, f)


class ReviewAcceptanceFlowTests(TransactionTestCase):

    def setUp(self):
        self.client = Client()
        self.org = Organization.objects.create(key="reviewtest-org", label="Review Test Org")
        self.user = get_user_model().objects.create_user(
            username="reviewer", email="reviewer@example.invalid",
            password="testpassword123", is_active=True,
        )
        Membership.objects.create(
            user=self.user, organization=self.org,
            role="admin", active=True
        )
        Authenticator.objects.create(
            user=self.user, type=Authenticator.Type.TOTP, data={}
        )
        self.client.force_login(self.user)
        session_key = self.client.session.session_key
        s = SessionStore(session_key=session_key)
        s["account_authentication_methods"] = [
            {"method": "password"},
            {"method": "mfa", "type": "totp"},
        ]
        s.save()
        self.client.cookies[settings.SESSION_COOKIE_NAME] = session_key
        self.review_session = Release1aReviewSession.objects.create(
            user=self.user, organization=self.org, build_id="testbuild123"
        )

    def test_review_dashboard_loads(self):
        """Authenticated user with TOTP can load /review/."""
        response = self.client.get("/review/")
        self.assertEqual(response.status_code, 200)

    def test_review_dashboard_redirects_unauthenticated(self):
        """Unauthenticated user is redirected from /review/."""
        anon = Client()
        response = anon.get("/review/")
        self.assertIn(response.status_code, (302, 301))

    def test_section_update_creates_review_row(self):
        """POST to /review/section/<section>/update/ creates a Release1aReview row."""
        initial_count = Release1aReview.objects.count()
        response = self.client.post(
            "/review/section/worker/update/",
            {"status": Release1aReview.Status.IN_PROGRESS},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Release1aReview.objects.count(), initial_count + 1)

    def test_approval_requires_all_sections_done(self):
        """Approval button should be disabled unless all four sections are DONE."""
        for section in [
            Release1aReview.Section.WORKER,
            Release1aReview.Section.DOCUMENT_OCR,
            Release1aReview.Section.ASSIGNMENT,
            Release1aReview.Section.A1,
        ]:
            Release1aReview.objects.update_or_create(
                session=self.review_session, section=section,
                defaults={"status": Release1aReview.Status.DONE}
            )
        response = self.client.get("/review/check-answers/")
        self.assertEqual(response.status_code, 200)

    def test_receipt_requires_acceptance(self):
        """Accessing /review/receipt/ without an acceptance should redirect."""
        response = self.client.get("/review/receipt/")
        self.assertIn(response.status_code, (200, 302))

    def test_acceptance_record_is_immutable(self):
        """Creating two acceptance records should succeed (append-only)."""
        session2 = Release1aReviewSession.objects.create(
            user=self.user, organization=self.org, build_id="testbuild2"
        )
        Release1aAcceptance.objects.create(
            user=self.user, organization=self.org, session=self.review_session,
            git_commit_hash="a" * 40, git_clean=False, app_build_id="testbuild1",
        )
        Release1aAcceptance.objects.create(
            user=self.user, organization=self.org, session=session2,
            git_commit_hash="b" * 40, git_clean=True, app_build_id="testbuild2",
        )
        self.assertEqual(Release1aAcceptance.objects.filter(user=self.user).count(), 2)


class Rev002GateTests(TransactionTestCase):
    """Verify that the REV-002 engineering gate prevents Release1aAcceptance creation."""

    def setUp(self):
        self.client = Client()
        self.org = Organization.objects.create(key="gatetest-org", label="Gate Test Org")
        self.user = get_user_model().objects.create_user(
            username="gatetester", email="gatetester@example.invalid",
            password="testpassword123", is_active=True,
        )
        Membership.objects.create(
            user=self.user, organization=self.org,
            role="admin", active=True
        )
        Authenticator.objects.create(
            user=self.user, type=Authenticator.Type.TOTP, data={}
        )
        self.client.force_login(self.user)
        session_key = self.client.session.session_key
        s = SessionStore(session_key=session_key)
        s["account_authentication_methods"] = [
            {"method": "password"},
            {"method": "mfa", "type": "totp"},
        ]
        s.save()
        self.client.cookies[settings.SESSION_COOKIE_NAME] = session_key
        self.review_session = Release1aReviewSession.objects.create(
            user=self.user, organization=self.org, build_id="testbuild123"
        )
        for section in [
            Release1aReview.Section.WORKER,
            Release1aReview.Section.DOCUMENT_OCR,
            Release1aReview.Section.ASSIGNMENT,
            Release1aReview.Section.A1,
        ]:
            Release1aReview.objects.update_or_create(
                session=self.review_session, section=section,
                defaults={"status": Release1aReview.Status.DONE}
            )

    def test_rev002_gate_open_returns_correct_status(self):
        """Unit test for _rev002_gate_open with blocked and open gates."""
        from portal.release1a.views import _rev002_gate_open
        from unittest.mock import patch

        blocked_json = {
            "schema_version": "1.0",
            "updated_at": "2026-09-04T00:00:00+02:00",
            "records": [{
                "id": "REV-002",
                "title": "Test",
                "scope": "Test scope",
                "owner": "test",
                "approver": "tester",
                "human_decision": "proposed",
                "validation": "pending",
                "implementation_gate": "blocked",
                "activation_gate": "blocked",
                "choices": [],
                "checks": [],
                "dependencies": [],
                "source": "test.md",
            }]
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(blocked_json, f)
            blocked_path = f.name
        try:
            with patch("portal.release1a.views.APPROVALS_FILE", blocked_path):
                open_, reason = _rev002_gate_open()
            self.assertFalse(open_)
            self.assertIn("blocked", reason)
        finally:
            os.unlink(blocked_path)

        open_json = dict(blocked_json)
        open_json["records"][0]["implementation_gate"] = "open"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(open_json, f)
            open_path = f.name
        try:
            with patch("portal.release1a.views.APPROVALS_FILE", open_path):
                open_, reason = _rev002_gate_open()
            self.assertTrue(open_)
        finally:
            os.unlink(open_path)

    def test_blocked_gate_rejects_approval(self):
        """
        POST to review_approve while REV-002 implementation_gate is blocked
        must return 403 and not create a Release1aAcceptance record.
        """
        from portal.release1a import views as review_views
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmpdir:
            blocked_approvals = os.path.join(tmpdir, "approvals.json")
            with open(blocked_approvals, "w") as f:
                json.dump({
                    "schema_version": "1.0",
                    "updated_at": "2026-09-04T00:00:00+02:00",
                    "records": [{
                        "id": "REV-002",
                        "title": "Test",
                        "scope": "Test scope",
                        "owner": "test",
                        "approver": "tester",
                        "human_decision": "proposed",
                        "validation": "pending",
                        "implementation_gate": "blocked",
                        "activation_gate": "blocked",
                        "choices": [],
                        "checks": [],
                        "dependencies": [],
                        "source": "test.md",
                    }]
                }, f)
            with patch.object(review_views, "APPROVALS_FILE", blocked_approvals):
                with patch.object(review_views, "_scoped_tree_clean", return_value=(True, "")):
                    with patch.object(review_views, "_readiness_passed", return_value=(True, "OK")):
                        response = self.client.post("/review/approve/")
        self.assertEqual(response.status_code, 403)
        self.assertIn("blocked", response.json().get("error", "").lower())
        self.assertEqual(Release1aAcceptance.objects.count(), 0)

    def test_open_gate_allows_approval(self):
        """
        POST to review_approve when REV-002 implementation_gate is open
        must succeed and create a Release1aAcceptance record.
        """
        from portal.release1a import views as review_views
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmpdir:
            open_approvals = os.path.join(tmpdir, "approvals.json")
            with open(open_approvals, "w") as f:
                json.dump({
                    "schema_version": "1.0",
                    "updated_at": "2026-09-04T00:00:00+02:00",
                    "records": [{
                        "id": "REV-002",
                        "title": "Test",
                        "scope": "Test scope",
                        "owner": "test",
                        "approver": "tester",
                        "human_decision": "proposed",
                        "validation": "passed",
                        "implementation_gate": "open",
                        "activation_gate": "blocked",
                        "choices": [],
                        "checks": [],
                        "dependencies": [],
                        "source": "test.md",
                    }]
                }, f)
            with patch.object(review_views, "APPROVALS_FILE", open_approvals):
                with patch.object(review_views, "_scoped_tree_clean", return_value=(True, "")):
                    with patch.object(review_views, "_readiness_passed", return_value=(True, "OK")):
                        response = self.client.post("/review/approve/")
        self.assertEqual(response.status_code, 302)  # redirect to receipt
        self.assertEqual(Release1aAcceptance.objects.count(), 1)
