"""
test_totp_real_enforcement.py

Confirms MFA enforcement uses allauth TOTP, not Membership.mfa_verified.
"""
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "portal.settings")
import django
django.setup()


from django.test import TransactionTestCase
from django.contrib.auth import get_user_model
from allauth.mfa.models import Authenticator
from portal.release1a.models import Organization, Membership
from portal.release1a.services import require_membership, require_mfa_enrolled, Forbidden


class TOTPRealEnforcementTests(TransactionTestCase):

    def setUp(self):
        self.org = Organization.objects.create(key="totptest-org", label="TOTP Test Org")
        self.user_without_totp = get_user_model().objects.create_user(
            username="totp-no", email="totp-no@example.invalid",
            password="testpassword123", is_active=True,
        )
        Membership.objects.create(
            user=self.user_without_totp, organization=self.org,
            role="admin", active=True
        )
        self.user_with_totp = get_user_model().objects.create_user(
            username="totp-yes", email="totp-yes@example.invalid",
            password="testpassword123", is_active=True,
        )
        Membership.objects.create(
            user=self.user_with_totp, organization=self.org,
            role="admin", active=True
        )
        Authenticator.objects.create(
            user=self.user_with_totp, type=Authenticator.Type.TOTP, data={}
        )

    def test_mfa_verified_flag_does_not_grant_access(self):
        """A user with mfa_verified=True but no allauth TOTP should be denied."""
        membership = Membership.objects.get(user=self.user_without_totp, organization=self.org)
        membership.mfa_verified = True
        membership.save(update_fields=["mfa_verified"])
        self.assertFalse(require_mfa_enrolled(self.user_without_totp))

    def test_user_with_allauth_totp_passes_mfa_check(self):
        """A user with an allauth TOTP Authenticator should pass the MFA check."""
        self.assertTrue(require_mfa_enrolled(self.user_with_totp))

    def test_require_membership_blocks_without_totp(self):
        """require_membership should raise Forbidden when user has no allauth TOTP."""
        with self.assertRaises(Forbidden):
            require_membership(self.user_without_totp, self.org)

    def test_require_membership_passes_with_totp(self):
        """require_membership should pass when user has allauth TOTP enrolled."""
        require_membership(self.user_with_totp, self.org)
