#!/usr/bin/env python3
"""
Create and seed an isolated verification database.

Recreates the database at runtime/portal/verification/verification.sqlite3,
applies all migrations through 0007, and seeds synthetic organizations,
users, workers, documents, and assignments.

Safe to re-run: always recreates from scratch.
"""
from __future__ import annotations

import os
import sys
import uuid
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "runtime" / "portal" / "verification" / "verification.sqlite3"


def header():
    print("=" * 60)
    print(" Release 1A Verification DB Seeder")
    print("=" * 60)


def destroy_db():
    if DB_PATH.exists():
        DB_PATH.unlink()
        print(f"  Removed existing database: {DB_PATH}")


def migrate():
    print("  Applying migrations...")
    from django.core.management import call_command
    call_command("migrate", verbosity=1, interactive=False)
    print("  Migrations applied.")


def seed():
    print("  Seeding synthetic data...")
    import django
    django.setup()

    from django.contrib.auth import get_user_model
    from django.db import transaction
    from django.utils import timezone
    from portal.release1a import models as r1a

    User = get_user_model()

    SLUG_A = "syn-acme-" + uuid.uuid4().hex[:6]
    SLUG_B = "syn-beta-" + uuid.uuid4().hex[:6]

    with transaction.atomic():
        org_a = r1a.Organization.objects.create(key=SLUG_A, label="Acme Workers s.r.o.")
        org_b = r1a.Organization.objects.create(key=SLUG_B, label="Beta Personal GmbH")
        print(f"    Created orgs: {org_a.label}, {org_b.label}")

        user_a = User.objects.create_user(
            username=f"vrfyr_{SLUG_A}",
            password="synthetick+pass.1",
            email=f"vrfyr_{SLUG_A}@example.example",
            is_staff=True,
            is_superuser=False,
        )
        user_b = User.objects.create_user(
            username=f"vrfyr_{SLUG_B}",
            password="synthetick+pass.1",
            email=f"vrfyr_{SLUG_B}@example.example",
            is_staff=True,
            is_superuser=False,
        )
        r1a.Membership.objects.create(user=user_a, organization=org_a, role="reviewer")
        r1a.Membership.objects.create(user=user_b, organization=org_b, role="reviewer")
        print(f"    Created users: {user_a.username}, {user_b.username}")

        workers = []
        for i, (org, user) in enumerate([(org_a, user_a), (org_b, user_b)]):
            for j in range(3):
                w = r1a.Worker.objects.create(
                    organization=org,
                    given_name=f"TestFirst{j+1}",
                    family_name=f"TestLast{j+1}",
                    birth_date=date(1990, 1, 1) + timedelta(days=j * 100),
                    activity_profile="employee",
                    state=r1a.Worker.State.ACTIVE if j < 2 else r1a.Worker.State.ARCHIVED,
                )
                workers.append(w)
        print(f"    Created {len(workers)} workers")

        docs = []
        for i, (org, user) in enumerate([(org_a, user_a), (org_b, user_b)]):
            for j in range(2):
                opaque_key = uuid.uuid4().hex
                sha = uuid.uuid4().hex + uuid.uuid4().hex[:32]
                d = r1a.Document.objects.create(
                    organization=org,
                    worker=workers[i * 3],
                    opaque_key=opaque_key,
                    sha256=sha,
                    content_type="application/pdf",
                    state=r1a.Document.State.QUARANTINED,
                )
                dv = r1a.DocumentVersion.objects.create(
                    document=d,
                    organization=org,
                    version_number=1,
                    opaque_key=uuid.uuid4().hex,
                    sha256=sha,
                    content_type="application/pdf",
                    byte_size=2048 * (j + 1),
                    quarantine_result="clean",
                    malware_result="clean",
                    mime_result="clean",
                )
                docs.append((d, dv, user))
        print(f"    Created {len(docs)} documents + versions")

        assignments = []
        for i, (org, worker) in enumerate([(org_a, workers[0]), (org_a, workers[1]),
                                            (org_b, workers[3]), (org_b, workers[4])]):
            a = r1a.Assignment.objects.create(
                organization=org,
                worker=worker,
                workplace_label=f"Workplace {i+1}",
                activity_label=f"Activity {i+1}",
                start=date(2026, 1, 1) + timedelta(days=i * 30),
                end=date(2026, 12, 31) + timedelta(days=i * 30),
                state=r1a.Assignment.State.PLANNED if i % 2 == 0 else r1a.Assignment.State.ACTIVE,
            )
            assignments.append(a)
        print(f"    Created {len(assignments)} assignments")

        d, dv, u = docs[0]
        ocr = r1a.OcrRun.objects.create(
            document=d,
            version=dv,
            organization=org_a,
            engine=r1a.OcrRun.Engine.RAPIDOCR,
            state=r1a.OcrRun.State.COMPLETED,
            retry_count=0,
            completed_at=timezone.now(),
        )
        fp = r1a.FieldProposal.objects.create(
            document=d,
            version=dv,
            organization=org_a,
            ocr_run=ocr,
            field_name="given_name",
            proposed_value="Synthetic",
            confidence=0.95,
            ocr_engine="RapidOCR",
            state=r1a.FieldProposal.State.PROPOSED,
        )
        fd = r1a.FieldDecision.objects.create(
            field_proposal=fp,
            organization=org_a,
            decision="confirmed",
            corrected_value="Synthetic",
            decided_by=u,
        )
        rev = r1a.WorkerIdentityRevision.objects.create(
            worker=workers[0],
            organization=org_a,
            source_document=d,
            source_version=dv,
            revision_number=1,
            confirmed_fields={"given_name": "Synthetic"},
            confirmed_by=u,
        )
        print("    Created OCR run, field proposal/decision, identity revision")

        r1a.ReviewTask.objects.create(
            organization=org_a,
            worker=workers[0],
            document=d,
            task_type=r1a.ReviewTask.TaskType.FIELD_REVIEW,
            state=r1a.ReviewTask.State.PENDING,
            priority=r1a.ReviewTask.Priority.MEDIUM,
        )
        r1a.IntakeSession.objects.create(
            organization=org_a,
            worker=workers[0],
            purpose=r1a.IntakeSession.Purpose.A1,
            state=r1a.IntakeSession.State.DRAFT,
        )
        print("    Created review tasks")

        r1a.AuditEvent.objects.create(
            organization=org_a,
            actor_ref=f"user:{user_a.pk}",
            event_type="worker.created",
            object_ref=f"worker:{workers[0].pk}",
            outcome="success",
        )
        print("    Created audit events")

        r1a.A1Case.objects.create(
            organization=org_a,
            worker=workers[0],
            source_hash=uuid.uuid4().hex,
            readiness=r1a.A1Case.Readiness.BLOCKED,
        )
        print("    Created intake session and A1 case")

    print("  Seeding complete.")


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "portal.settings_verification")
    sys.path.insert(0, str(ROOT))

    import django
    django.setup()

    header()
    print(f"\nDatabase: {DB_PATH}")
    destroy_db()
    migrate()
    seed()
    print(f"\nVerification DB ready: {DB_PATH}")
    print(f"  Run with: DJANGO_SETTINGS_MODULE=portal.settings_verification")


if __name__ == "__main__":
    main()
