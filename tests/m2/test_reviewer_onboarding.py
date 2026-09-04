"""
test_reviewer_onboarding.py

Full reviewer onboarding integration test using real HTTP posts:
1. Inactive reviewer (invitation simulation via token file)
2. Password selection via one-time invitation URL
3. Real allauth password login
4. TOTP enrollment via real allauth activation form
5. Normal logout
6. Real password + TOTP login (via allauth challenge)
7. Access to /review/
8. Auth audit event recorded for the successful login

Uses real HTTP posts to allauth endpoints. No force_login() or direct
session mutation for authentication state.
"""
import json
import os
import tempfile
import time

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "portal.settings")
os.environ.setdefault("REVIEW_BUILD_MANIFEST_PATH", tempfile.mktemp(suffix=".json"))
os.environ.setdefault("REVIEW_INVITATIONS_DIR", tempfile.mkdtemp())

import django
django.setup()


import pyotp
from django.test import Client, TransactionTestCase
from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
from django.conf import settings
from allauth.mfa.models import Authenticator
from allauth.account.models import EmailAddress
from portal.release1a.models import AuthAuditEvent, Organization, Membership


with open(os.environ["REVIEW_BUILD_MANIFEST_PATH"], "w") as f:
    json.dump({"app_build_id": "testbuild123", "git_commit": "a" * 40, "git_clean": True}, f)


def _totp_code(secret):
    return pyotp.TOTP(secret).now()


def _session_key(client) -> str | None:
    """Return the current session key from the client's cookie."""
    morsel = client.cookies.get(settings.SESSION_COOKIE_NAME)
    return morsel.value if morsel else None


class ReviewerOnboardingTests(TransactionTestCase):

    def setUp(self):
        self.client = Client()
        self.org = Organization.objects.create(key="reviewtest-org", label="Review Test Org")
        self.user = get_user_model().objects.create_user(
            username="reviewer", email="reviewer@example.invalid",
            password="!notused123", is_active=False,
        )
        EmailAddress.objects.create(
            user=self.user, email="reviewer@example.invalid",
            verified=True, primary=True,
        )
        Membership.objects.create(
            user=self.user, organization=self.org,
            role="admin", active=True,
        )
        self.invitations_dir = os.environ["REVIEW_INVITATIONS_DIR"]
        os.makedirs(self.invitations_dir, exist_ok=True)
        self.token = "test-invite-token-12345"
        self.token_file = os.path.join(self.invitations_dir, f"{self.token}.json")
        payload = {
            "email": "reviewer@example.invalid",
            "user_pk": self.user.pk,
            "created_at": int(time.time()),
            "expires_at": int(time.time()) + 86400,
            "used": False,
        }
        with open(self.token_file, "w") as f:
            json.dump(payload, f)

    def test_full_onboarding_flow(self):
        """Full journey: invitation → password → real login → TOTP enrollment → logout → real login+MFA → /review/ access."""
        # Step 1: Activation URL loads
        r = self.client.get(f"/accounts/activate/{self.token}/")
        self.assertEqual(r.status_code, 200)

        # Step 2: Submit password (activates user, then logs out, redirects to TOTP activate)
        r = self.client.post(
            f"/accounts/activate/{self.token}/",
            {"password1": "SuperSecretPass123!", "password2": "SuperSecretPass123!"},
        )
        self.assertEqual(r.status_code, 302)
        self.assertIn("2fa", r.url)

        # Step 3: Real allauth password login
        # (activation logged the user out)
        r = self.client.post(
            "/accounts/login/",
            {"login": "reviewer@example.invalid", "password": "SuperSecretPass123!"},
        )
        self.assertEqual(r.status_code, 302)
        # Synthetic-review users land directly in their review workspace.
        self.assertEqual(r.url, "/review/")
        sk = _session_key(self.client)
        self.assertIsNotNone(sk)

        # Step 4: GET TOTP activation page — stores secret in session
        r = self.client.get("/accounts/2fa/totp/activate/")
        self.assertEqual(r.status_code, 200)
        enroll_secret = SessionStore(session_key=sk).get("mfa.totp.secret")
        self.assertIsNotNone(enroll_secret)

        # Step 5: POST TOTP code to enroll
        r = self.client.post(
            "/accounts/2fa/totp/activate/",
            {"code": _totp_code(enroll_secret)},
        )
        self.assertIn(r.status_code, (302, 303))
        self.assertTrue(
            Authenticator.objects.filter(
                user=self.user, type=Authenticator.Type.TOTP
            ).exists()
        )

        # Step 6: Normal logout (POST to ensure session is flushed)
        r = self.client.post("/accounts/logout/", HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertIn(r.status_code, (200, 302))

        # Step 7: Real login — triggers allauth MFA challenge redirect
        r = self.client.post(
            "/accounts/login/",
            {"login": "reviewer@example.invalid", "password": "SuperSecretPass123!"},
        )
        self.assertEqual(r.status_code, 302)
        self.assertIn("authenticate", r.url)
        mfa_challenge_url = r.url

        # Step 8: Submit TOTP code to the allauth MFA challenge
        r = self.client.post(
            mfa_challenge_url,
            {"code": _totp_code(enroll_secret)},
        )
        self.assertEqual(r.status_code, 302)

        # Step 9: /review/ accessible after MFA
        r = self.client.get("/review/")
        self.assertEqual(r.status_code, 200)

        # Step 10: Auth audit event was recorded for the successful login
        # (fires via authenticator_used signal after TOTP challenge completes)
        login_events = AuthAuditEvent.objects.filter(
            event_type="authentication.login_succeeded",
            actor_ref=f"actor:user:{self.user.pk}",
        )
        self.assertGreaterEqual(login_events.count(), 1)

    def test_invitation_invalid_token(self):
        """Invalid invitation token shows error."""
        r = self.client.get("/accounts/activate/invalid-token/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("neplatný", r.content.decode())

    def test_invitation_expired(self):
        """Expired invitation token shows error."""
        with open(self.token_file, "w") as f:
            json.dump({
                "email": "reviewer@example.invalid",
                "user_pk": self.user.pk,
                "created_at": int(time.time()) - 86400 * 2,
                "expires_at": int(time.time()) - 3600,
                "used": False,
            }, f)
        r = self.client.get(f"/accounts/activate/{self.token}/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("vypršel", r.content.decode())

    def test_mfa_required_for_review_access(self):
        """Unauthenticated / MFA-missing requests to /review/ redirect to login/MFA."""
        anon = Client()
        r = anon.get("/review/")
        self.assertIn(r.status_code, (302, 301))
