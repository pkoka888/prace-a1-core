"""Shared synthetic fixtures for the test suite.

These fixtures reduce duplication across 20+ test files that each
independently create Organization, Worker, Membership, and User objects.
"""
from __future__ import annotations

import uuid

import pytest

from portal.release1a.models import Organization, Worker, Membership


@pytest.fixture
def synthetic_org(db):
    """A minimal synthetic organization."""
    return Organization.objects.create(
        key=f"synthetic-{uuid.uuid4().hex[:8]}",
        label="Synthetic Organization",
    )


@pytest.fixture
def synthetic_user(db, synthetic_org):
    """A synthetic user with jan_planner membership in the synthetic org."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    username = f"synthetic-user-{uuid.uuid4().hex[:8]}"
    user = User.objects.create_user(username=username, email=f"{username}@test.local")
    Membership.objects.create(
        user=user,
        organization=synthetic_org,
        role="jan_planner",
    )
    return user


@pytest.fixture
def synthetic_worker(db, synthetic_org):
    """A synthetic worker in the synthetic org."""
    return Worker.objects.create(
        organization=synthetic_org,
        given_name="Synthetic",
        family_name="Worker",
        birth_date="1990-01-01",
        activity_profile="employee",
    )


@pytest.fixture
def synthetic_case(db, synthetic_org, synthetic_worker):
    """A minimal synthetic case with one worker."""
    from portal.release1a.models import Case
    return Case.objects.create(
        organization=synthetic_org,
        worker=synthetic_worker,
        status="active",
    )
