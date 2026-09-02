"""
test_csrf_enforcement.py

Confirms CSRF middleware is present and enforced.
POST without a valid CSRF token to a protected view returns 403.
"""
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "portal.settings")
import django
django.setup()

from django.test import Client, TransactionTestCase
from django.contrib.auth import get_user_model


class CSRFEnforcementTests(TransactionTestCase):

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.user = get_user_model().objects.create_user(
            username="csrf-test", email="csrf-test@example.invalid",
            password="testpassword123", is_active=True,
        )
        from portal.release1a.models import Organization, Membership
        org = Organization.objects.create(key="csrftest-org", label="CSRF Test Org")
        Membership.objects.create(user=self.user, organization=org, role="admin", active=True)

    def test_post_without_csrf_token_returns_403(self):
        """POST without CSRF token to login should return 403, not 200 or 302."""
        response = self.client.post("/login/", {})
        self.assertEqual(response.status_code, 403)
