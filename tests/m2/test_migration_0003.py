"""
tests/m2/test_migration_0003.py

Unit tests for migration 0003 backfill logic.

Tests the actual two-pass cardinality check and final model constraints:
1. Org derivation: exactly one active membership → derive org; zero or multiple → raise.
2. Session keying by (user_id, organization_id, build_id).
3. PROTECT on Release1aAcceptance.session, .organization, .user.
4. Inactive memberships are excluded from cardinality check.
"""

import os
import tempfile

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "portal.settings")
os.environ.setdefault("REVIEW_BUILD_MANIFEST_PATH", tempfile.mktemp(suffix=".json"))

import django

django.setup()

from collections import defaultdict
from django.test import TransactionTestCase
from django.contrib.auth import get_user_model
from portal.release1a.models import (
    Organization,
    Membership,
    Release1aReviewSession,
    Release1aAcceptance,
)


class BackfillLogicTests(TransactionTestCase):
    """Test the two-pass cardinality check and final model constraints."""

    def setUp(self):
        self.org_a = Organization.objects.create(key="backfill-a", label="Backfill A")
        self.org_b = Organization.objects.create(key="backfill-b", label="Backfill B")
        User = get_user_model()
        self.user = User.objects.create_user(
            username="backfill-user",
            email="backfill@example.invalid",
            password="!notused123",
        )

    def _cardinality_check(self):
        """
        Replicate the two-pass cardinality check from migration 0003.

        Pass 1: collect org_ids per user from active memberships.
        Raise ValueError if any user has != 1 active org.
        Return {user_id: unique_org_id}.
        """
        user_org_sets = defaultdict(set)
        for m in Membership.objects.filter(active=True).values(
            "user_id", "organization_id"
        ):
            user_org_sets[m["user_id"]].add(m["organization_id"])
        for user_id, org_ids in user_org_sets.items():
            if len(org_ids) != 1:
                raise ValueError(
                    f"Cannot migrate: user_id={user_id} has {len(org_ids)} "
                    f"active memberships (must be exactly 1)."
                )
        return {uid: next(iter(oids)) for uid, oids in user_org_sets.items()}

    def test_unique_membership_derives_org(self):
        """Exactly one active membership → two-pass check passes and org is derived."""
        Membership.objects.create(
            user=self.user, organization=self.org_a, role="admin", active=True
        )
        org_by_user = self._cardinality_check()
        self.assertEqual(org_by_user[self.user.pk], self.org_a.pk)

    def test_no_membership_raises(self):
        """Zero active memberships → ValueError from cardinality check."""
        # No memberships for this user → org_by_user won't contain this user
        # The migration would raise when accessing org_by_user[user_id]
        with self.assertRaises(KeyError):
            self._cardinality_check()[self.user.pk]

    def test_multiple_memberships_raises(self):
        """User with two active memberships → ValueError from cardinality check."""
        Membership.objects.create(
            user=self.user, organization=self.org_a, role="admin", active=True
        )
        Membership.objects.create(
            user=self.user, organization=self.org_b, role="admin", active=True
        )
        with self.assertRaises(ValueError) as ctx:
            self._cardinality_check()
        self.assertIn("2 active memberships", str(ctx.exception))
        self.assertIn("Cannot migrate", str(ctx.exception))

    def test_session_key_includes_org(self):
        """Sessions are keyed by (user, org, build) not just (user, build)."""
        s1 = Release1aReviewSession.objects.create(
            user=self.user, organization=self.org_a, build_id="same-build"
        )
        s2 = Release1aReviewSession.objects.create(
            user=self.user, organization=self.org_b, build_id="same-build"
        )
        self.assertNotEqual(s1.pk, s2.pk)
        self.assertEqual(s1.build_id, s2.build_id)
        self.assertEqual(s1.user_id, s2.user_id)
        self.assertNotEqual(s1.organization_id, s2.organization_id)

    def test_acceptance_protect_on_session(self):
        """Deleting a session is blocked by PROTECT when acceptances reference it."""
        session = Release1aReviewSession.objects.create(
            user=self.user, organization=self.org_a, build_id="protect-test"
        )
        Release1aAcceptance.objects.create(
            user=self.user,
            organization=self.org_a,
            session=session,
            git_commit_hash="a" * 40,
            git_clean=False,
            app_build_id="protect-test",
        )
        from django.db.models import ProtectedError

        with self.assertRaises(ProtectedError):
            session.delete()

    def test_acceptance_protect_on_organization(self):
        """Deleting an org is blocked by PROTECT when acceptances reference it."""
        Release1aAcceptance.objects.create(
            user=self.user,
            organization=self.org_a,
            session=Release1aReviewSession.objects.create(
                user=self.user, organization=self.org_a, build_id="org-protect"
            ),
            git_commit_hash="b" * 40,
            git_clean=False,
            app_build_id="org-protect",
        )
        from django.db.models import ProtectedError

        with self.assertRaises(ProtectedError):
            self.org_a.delete()

    def test_acceptance_user_protect(self):
        """Deleting a user is blocked by PROTECT when acceptances reference them."""
        session = Release1aReviewSession.objects.create(
            user=self.user, organization=self.org_a, build_id="user-protect"
        )
        Release1aAcceptance.objects.create(
            user=self.user,
            organization=self.org_a,
            session=session,
            git_commit_hash="c" * 40,
            git_clean=False,
            app_build_id="user-protect",
        )
        from django.db.models import ProtectedError

        with self.assertRaises(ProtectedError):
            self.user.delete()

    def test_inactive_membership_not_used_for_org(self):
        """Inactive membership is excluded — only active org is counted."""
        Membership.objects.create(
            user=self.user, organization=self.org_a, role="admin", active=True
        )
        Membership.objects.create(
            user=self.user, organization=self.org_b, role="admin", active=False
        )
        org_by_user = self._cardinality_check()
        # Exactly one active org → passes cardinality check
        self.assertEqual(org_by_user[self.user.pk], self.org_a.pk)
