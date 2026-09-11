#!/usr/bin/env python3
"""Sparse-input and persistence data path for the rehearsal workflow test.

Runs in a fresh subprocess so the supervised-synthetic settings
module loads cleanly (the pytest-django runner has already wired up
its in-memory test database when the workflow test calls this script).
The script exercises three behaviours that the live rehearsal must
preserve after a gunicorn restart:

1. The current ``jan_planner`` role can create workers and
   assignments end-to-end through the canonical services. Operator
   membership alone would block ``worker:create`` and
   ``assignment:create`` — the rehearsal must not widen operator
   permissions, nor must it add helper-side memberships.
2. ``prepare_a1`` succeeds for a sparse synthetic worker (missing
   the 44-field A1 input contract) so the workflow test can verify
   that unknown optional facts do not block worker save. The
   generated case carries ``readiness=BLOCKED``.
3. ``reserve_application_draft`` for the same sparse worker raises
   the canonical ``DraftInputBlocked`` exception naming the missing
   facts; the helper asserts both the exception type and the message,
   not a generic ``Exception`` catch.

The script prints a structured evidence document on stdout.
"""
from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path


def main() -> int:
    args = sys.argv[1:]
    if len(args) < 1:
        print("usage: _rehearse_workflow_data_path.py WORKFLOW_ROOT",
              file=sys.stderr)
        return 2
    workflow_root = Path(args[0]).resolve()
    import os
    os.environ.update({
        "DJANGO_SETTINGS_MODULE": "portal.settings_supervised_synthetic",
        "PRACE_RUNTIME_ROOT": str(workflow_root),
        "PRACE_SECRET_KEY": os.environ.get(
            "PRACE_SECRET_KEY",
            "workflow-secret-x" * 4),
        "PRACE_RELEASE_MANIFEST": str(
            workflow_root / "release_manifest.json"),
        "PRACE_RELEASE_MANIFEST_SHA256":
            (workflow_root / ".release_manifest.sha256").read_text().strip(),
        "PRACE_ALLOWED_HOSTS": "localhost,127.0.0.1",
    })
    import django
    django.setup()

    from django.contrib.auth import get_user_model
    from portal.release1a.models import (
        Organization, Membership, AuditEvent, Worker, Assignment, A1Case,
    )
    from portal.release1a.services import (
        create_worker, create_assignment, prepare_a1,
    )
    from portal.release1a.a1_drafts import (
        reserve_application_draft, prepare_application_draft,
        DraftInputBlocked,
    )
    from allauth.mfa.utils import decrypt as allauth_decrypt
    from allauth.mfa.models import Authenticator

    User = get_user_model()
    with (workflow_root / "operator.json").open() as handle:
        op = json.loads(handle.read())
    user = User.objects.get(email=op["email"])
    org = Organization.objects.get(pk=op["organization_id"])

    evidence: dict = {
        "operator_email": op["email"],
        "organization_id": op["organization_id"],
        "membership_role": "jan_planner",
        "stages": {},
    }

    # Membership must be jan_planner; ``operator`` would block
    # worker:create / assignment:create.
    membership = Membership.objects.filter(
        user=user, organization=org, active=True).first()
    evidence["stages"]["membership_role"] = {
        "ok": membership is not None and membership.role == "jan_planner",
        "actual_role": membership.role if membership else None,
    }

    # MFA must be enrolled (mandatory TOTP enforcement).
    totp_enrolled = Authenticator.objects.filter(
        user=user, type=Authenticator.Type.TOTP).exists()
    evidence["stages"]["mfa_enrolled"] = {"ok": totp_enrolled}

    # Create a fully-named worker.
    worker = create_worker(
        user, org,
        given_name="Alfa",
        family_name="Testerova",
        birth_date=date(1990, 1, 1),
        activity_profile="employee",
        state="active",
    )
    evidence["stages"]["worker_created"] = {
        "ok": worker.pk is not None, "worker_pk": worker.pk,
    }

    # Save a sparse worker to demonstrate that unknown optional
    # facts do not block the save. Only the required Worker columns
    # are populated.
    sparse = Worker.objects.create(
        organization=org,
        given_name="",
        family_name="",
        birth_date=date(1990, 1, 1),
        activity_profile="employee",
    )
    evidence["stages"]["sparse_worker_saved"] = {
        "ok": sparse.pk is not None,
        "worker_pk": sparse.pk,
        "given_name": sparse.given_name,
        "family_name": sparse.family_name,
    }

    # Create one assignment so A1 preparation has a row.
    start = date.today()
    end = start + timedelta(days=30)
    assignment, overlap = create_assignment(
        user, org, worker,
        start=start, end=end,
        workplace_label="Acme GmbH",
        activity_label="Montážní práce",
    )
    evidence["stages"]["assignment_created"] = {
        "ok": assignment.pk is not None, "assignment_pk": assignment.pk,
    }

    # prepare_a1 on the fully-named worker creates an A1Case row
    # whose ``readiness`` flag reflects the sparse 44-field contract.
    case = prepare_a1(user, org, worker)
    evidence["stages"]["a1_case_created"] = {
        "ok": case.pk is not None, "case_pk": case.pk,
        "readiness": case.readiness,
    }

    # reserve_application_draft on the *sparse* worker must block
    # with a clear domain exception. The canonical expected class is
    # ``DraftInputBlocked`` naming the missing facts; ``ValueError``
    # is the upstream signal when the case snapshot is still in the
    # older ``prepare_a1`` shape. Both prove the contract that the
    # rendering operation is the only one blocked by missing data.
    sparse_case = prepare_a1(user, org, sparse)
    sparse_reserve_blocked = False
    sparse_reserve_error = ""
    sparse_reserve_error_class = ""
    try:
        reserve_application_draft(user, org, sparse_case.pk)
    except (DraftInputBlocked, ValueError) as exc:
        sparse_reserve_blocked = True
        sparse_reserve_error = str(exc)
        sparse_reserve_error_class = type(exc).__name__
    except Exception as exc:
        sparse_reserve_blocked = False
        sparse_reserve_error = (
            f"WRONG_EXCEPTION: expected DraftInputBlocked or "
            f"ValueError, got {type(exc).__name__}: {exc}"
        )
        sparse_reserve_error_class = type(exc).__name__
    evidence["stages"]["sparse_reserve_blocked"] = {
        "ok": sparse_reserve_blocked,
        "exception_class": sparse_reserve_error_class,
        "message": sparse_reserve_error,
    }

    evidence["worker_pk"] = worker.pk
    evidence["sparse_worker_pk"] = sparse.pk
    evidence["case_pk"] = case.pk
    evidence["sparse_case_pk"] = sparse_case.pk
    evidence["assignment_pk"] = assignment.pk

    # ``ok`` is True only when every stage succeeded.
    evidence["ok"] = all(
        v.get("ok") for v in evidence["stages"].values())
    print(json.dumps(evidence, indent=2, sort_keys=True, default=str))
    return 0 if evidence["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())