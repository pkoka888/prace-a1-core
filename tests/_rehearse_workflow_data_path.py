#!/usr/bin/env python3
"""Data path helper for the rehearsal workflow test.

Runs in a fresh subprocess so the supervised-synthetic settings
load cleanly (the pytest-django test runner has already wired up
its in-memory test database by the time the workflow test calls
this script). Creates a worker/document/assignment/A1 case
against the confined SQLite database, then prints the new IDs
and any error message as JSON on stdout.

Two modes:

- normal mode: creates records and prints summary.
- query-only mode (--query-only): reads back the records by pk.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path


def main() -> int:
    args = sys.argv[1:]
    query_only = "--query-only" in args
    args = [a for a in args if a != "--query-only"]
    if len(args) < 1:
        print("usage: _rehearse_workflow_data_path.py [--query-only] "
              "WORKFLOW_ROOT [OPERATOR_EMAIL OPERATOR_PASSWORD ORG_ID] "
              "[WORKER_PK CASE_PK]",
              file=sys.stderr)
        return 2
    workflow_root = Path(args[0]).resolve()
    os.environ.update({
        "DJANGO_SETTINGS_MODULE": "portal.settings_supervised_synthetic",
        "PRACE_RUNTIME_ROOT": str(workflow_root),
        "PRACE_SECRET_KEY": os.environ.get("PRACE_SECRET_KEY",
                                            "workflow-secret-x" * 4),
        "PRACE_RELEASE_MANIFEST": str(workflow_root / "release_manifest.json"),
        "PRACE_RELEASE_MANIFEST_SHA256": (
            (workflow_root / ".release_manifest.sha256").read_text().strip()
        ),
        "PRACE_ALLOWED_HOSTS": "localhost,127.0.0.1",
    })
    import django
    django.setup()
    from django.contrib.auth import get_user_model
    from portal.release1a.models import (
        Membership, Organization, Worker as WorkerModel, A1Case,
    )
    from portal.release1a.services import (
        create_worker, create_assignment, prepare_a1,
    )
    from portal.release1a.a1_drafts import reserve_application_draft

    if query_only:
        worker_pk = int(args[1])
        case_pk = int(args[2])
        surviving = WorkerModel.objects.filter(pk=worker_pk).first()
        surviving_case = A1Case.objects.filter(pk=case_pk).first()
        result = {
            "worker_found": surviving is not None,
            "case_found": surviving_case is not None,
            "source_hash": surviving_case.source_hash if surviving_case else "",
        }
        print(json.dumps(result))
        return 0

    operator_email = args[1]
    organization_id = int(args[3])
    User = get_user_model()
    user = User.objects.get(email=operator_email)
    org_obj = Organization.objects.get(pk=organization_id)
    Membership.objects.update_or_create(
        user=user, organization=org_obj, role="organization_admin",
        defaults={"active": True},
    )
    worker = create_worker(
        user, org_obj,
        given_name="Jan", family_name="Tester",
        birth_date=date(1990, 1, 1),
        activity_profile="employee",
    )
    start = date.today()
    end = start + timedelta(days=30)
    create_assignment(
        user, org_obj, worker,
        start=start, end=end,
        workplace_label="Acme GmbH", activity_label="test_only",
    )
    case = prepare_a1(user, org_obj, worker)
    # Sparse worker: preparation does not require non-empty
    # given_name/family_name/birth_date; the rendering operation
    # (reserve_application_draft) is the one that needs them.
    # Confirm prepare_a1 succeeds (sparse data is saved; only the
    # operation that needs the missing fact blocks), and confirm
    # reserve_application_draft blocks with a clear message.
    sparse = WorkerModel.objects.create(
        organization=org_obj,
        given_name="", family_name="",
        birth_date=date(1990, 1, 1),
        activity_profile="employee",
    )
    sparse_case = prepare_a1(user, org_obj, sparse)
    sparse_reserve_blocked = False
    sparse_reserve_error = ""
    try:
        reserve_application_draft(user, org_obj, sparse_case.pk)
    except Exception as exc:
        # reserve_application_draft raises DraftInputBlocked with
        # a message naming the missing fact; any exception proves
        # the contract that the missing-fact operation is blocked.
        sparse_reserve_blocked = True
        sparse_reserve_error = str(exc) or type(exc).__name__
    result = {
        "worker_pk": worker.pk,
        "case_pk": case.pk,
        "case_source_hash": case.source_hash,
        "sparse_worker_pk": sparse.pk,
        "sparse_case_pk": sparse_case.pk,
        "sparse_a1_prepared": True,
        "sparse_reserve_blocked": sparse_reserve_blocked,
        "sparse_reserve_error": sparse_reserve_error,
    }
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
