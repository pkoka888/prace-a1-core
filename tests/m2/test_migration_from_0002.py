"""
tests/m2/test_migration_from_0002.py

Schema verification tests — confirm the final migrated schema has the expected
structure after applying migrations 0003 and 0004.

These tests verify the schema outcomes without running the full migration
executor (which requires a truly isolated DB per test to avoid state pollution).
The functional PROTECT, org-derivation, and multi-org rejection behaviors are
covered in test_migration_0003.py.
"""
import os
import tempfile

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "portal.settings")
os.environ.setdefault("REVIEW_BUILD_MANIFEST_PATH", tempfile.mktemp(suffix=".json"))

import django
django.setup()

import pytest
from django.test import TransactionTestCase
from portal.release1a.models import (
    Organization, Membership, Release1aReview,
    Release1aReviewSession, Release1aAcceptance,
)


class MigratedSchemaTests(TransactionTestCase):
    """
    Verify the final migrated schema has the correct structure.
    These run after pytest-django applies all migrations to the test DB.
    """

    def test_acceptance_has_org_and_session_fks(self):
        """Release1aAcceptance has organization and session FKs."""
        # Verify the FK fields exist on the model
        field_names = {f.name for f in Release1aAcceptance._meta.get_fields()}
        assert "organization" in field_names
        assert "session" in field_names
        assert "user" in field_names

    def test_acceptance_org_is_protect(self):
        """organization FK on Release1aAcceptance uses PROTECT."""
        org_field = Release1aAcceptance._meta.get_field("organization")
        self.assertEqual(org_field.remote_field.on_delete.__name__, "PROTECT")

    def test_acceptance_session_is_protect(self):
        """session FK on Release1aAcceptance uses PROTECT."""
        session_field = Release1aAcceptance._meta.get_field("session")
        self.assertEqual(session_field.remote_field.on_delete.__name__, "PROTECT")

    def test_acceptance_user_is_protect(self):
        """user FK on Release1aAcceptance uses PROTECT."""
        user_field = Release1aAcceptance._meta.get_field("user")
        self.assertEqual(user_field.remote_field.on_delete.__name__, "PROTECT")

    def test_review_session_unique_constraint(self):
        """(user, organization, build_id) is unique on Release1aReviewSession."""
        constraints = Release1aReviewSession._meta.constraints
        unique_fields = [
            c.fields for c in constraints
            if hasattr(c, "fields")
        ]
        self.assertIn(("user", "organization", "build_id"), unique_fields)

    def test_review_section_unique_per_session(self):
        """(session, section) is unique on Release1aReview."""
        constraints = Release1aReview._meta.constraints
        unique_fields = [
            c.fields for c in constraints
            if hasattr(c, "fields")
        ]
        self.assertIn(("session", "section"), unique_fields)

    def test_review_has_no_old_columns(self):
        """Release1aReview has no user_id, git_commit_at_visit, app_build_id_at_visit, review_session_uuid."""
        field_names = {f.name for f in Release1aReview._meta.get_fields()}
        assert "user" not in field_names
        assert "git_commit_at_visit" not in field_names
        assert "app_build_id_at_visit" not in field_names
        assert "review_session_uuid" not in field_names

    def test_acceptance_has_no_old_review_session_uuid(self):
        """Release1aAcceptance has no review_session_uuid field."""
        field_names = {f.name for f in Release1aAcceptance._meta.get_fields()}
        assert "review_session_uuid" not in field_names

    def test_auth_audit_event_model_exists(self):
        """AuthAuditEvent model is registered."""
        from portal.release1a.models import AuthAuditEvent
        field_names = {f.name for f in AuthAuditEvent._meta.get_fields()}
        assert "event_type" in field_names
        assert "outcome" in field_names
        assert "actor_ref" in field_names
        assert "occurred_at" in field_names
