"""Synthetic identity races and historical migration on disposable PostgreSQL."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
from threading import Barrier, Event
from unittest import skipUnless
from unittest.mock import patch

from allauth.mfa.models import Authenticator
from django.contrib.auth import get_user_model
from django.db import IntegrityError, close_old_connections, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase, override_settings

from portal.release1a import document_intake, identity
from portal.release1a.document_intake import execute_run, intake, read_result
from portal.release1a.identity import (
    persist_identity_evaluation, prepare_identity_draft, resolve_identity_evaluation,
)
from portal.release1a.models import (
    DocumentRegionAssociation, FieldDecision, IdentityEvaluation, IdentityResolution,
    Membership, Organization, Worker,
    WorkerIdentityClaim, WorkerIdentityRevision,
)
from src.document_core.pipeline import DocumentProcessor
from tests.test_document_core.helpers import OP, ScriptedEngine, card, png


@skipUnless(connection.vendor == "postgresql", "Disposable PostgreSQL required")
class PostgresIdentityConcurrencyTests(TransactionTestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="synthetic-identity-")
        self.addCleanup(temporary.cleanup)
        settings = override_settings(
            DOCUMENT_STORAGE_ROOT=Path(temporary.name), M2_SYNTHETIC_ONLY=True,
        )
        settings.enable()
        self.addCleanup(settings.disable)
        self.org = Organization.objects.create(
            key="synthetic-identity-race", label="Synthetic Identity Race",
        )
        self.user = get_user_model().objects.create_user("synthetic-identity-operator")
        Membership.objects.create(
            user=self.user, organization=self.org, role="organization_admin",
        )
        Authenticator.objects.create(user=self.user, type=Authenticator.Type.TOTP, data={})
        _, _, _, self.run = intake(
            self.user, self.org, None, "synthetic.png", "image/png", png(card(OP)),
            processor=DocumentProcessor(lambda: ScriptedEngine([OP, OP])),
        )
        self.region = read_result(self.user, self.org, self.run.pk)["result"]["documents"][0]["document_id"]

    def simultaneous(self, operation, other_operation=None):
        barrier = Barrier(2, timeout=10)

        def invoke(operation):
            close_old_connections()
            try:
                # Thread-local connections and bounded SQL waits keep failures finite.
                with connection.cursor() as cursor:
                    cursor.execute("SET statement_timeout = '10s'")
                    cursor.execute("SET lock_timeout = '5s'")
                    cursor.execute("SELECT pg_backend_pid()")
                    backend = cursor.fetchone()[0]
                user = get_user_model().objects.get(pk=self.user.pk)
                organization = Organization.objects.get(pk=self.org.pk)
                barrier.wait()
                return backend, operation(user, organization)
            finally:
                connection.close()

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(invoke, call)
                       for call in (operation, other_operation or operation)]
            results = [future.result(timeout=30) for future in futures]
        self.assertNotEqual(results[0][0], results[1][0])
        return [result for _, result in results]

    def test_simultaneous_evaluations_reuse_one_record(self):
        results = self.simultaneous(lambda user, org: persist_identity_evaluation(
            user, org, [self.run.pk],
        ).pk)
        self.assertEqual(results[0], results[1])
        self.assertEqual(IdentityEvaluation.objects.filter(organization=self.org).count(), 1)

    def test_ocr_completion_overlaps_evaluation_without_foreign_key_deadlock(self):
        class BrokenProcessor:
            def process(self, *args, **kwargs):
                raise RuntimeError("SYNTHETIC_OCR_FAILURE")

        _, _, _, run = intake(
            self.user, self.org, None, "synthetic-retry.png", "image/png",
            png(card(OP, border=True)), processor=BrokenProcessor(),
        )
        self.assertEqual(run.state, "failed")
        run_locked, org_locked = Event(), Event()
        real_persist = document_intake.persist_proposals
        real_lock = identity._lock_organization

        def persist_after_organization_lock(*args, **kwargs):
            run_locked.set()
            if not org_locked.wait(timeout=10):
                raise AssertionError("Evaluation did not acquire its organization lock")
            return real_persist(*args, **kwargs)

        def lock_and_signal(organization):
            real_lock(organization)
            org_locked.set()

        def invoke(operation):
            close_old_connections()
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SET statement_timeout = '10s'")
                    cursor.execute("SET lock_timeout = '5s'")
                    cursor.execute("SELECT pg_backend_pid()")
                    backend = cursor.fetchone()[0]
                user = get_user_model().objects.get(pk=self.user.pk)
                organization = Organization.objects.get(pk=self.org.pk)
                return backend, operation(user, organization)
            finally:
                connection.close()

        with patch.object(document_intake, "persist_proposals", side_effect=persist_after_organization_lock), \
                patch.object(identity, "_lock_organization", side_effect=lock_and_signal), \
                ThreadPoolExecutor(max_workers=2) as executor:
            ocr = executor.submit(invoke, lambda user, org: execute_run(
                user, org, run.pk,
                processor=DocumentProcessor(lambda: ScriptedEngine([OP, OP])),
            ).state)
            self.assertTrue(run_locked.wait(timeout=10), "OCR did not acquire its run lock")
            evaluation = executor.submit(invoke, lambda user, org: persist_identity_evaluation(
                user, org, [run.pk],
            ).pk)
            ocr_backend, state = ocr.result(timeout=30)
            evaluation_backend, evaluation_id = evaluation.result(timeout=30)
        self.assertNotEqual(ocr_backend, evaluation_backend)
        self.assertEqual(state, "completed")
        run.refresh_from_db()
        self.assertEqual(run.state, "completed")
        self.assertEqual(run.retry_count, 2)
        record = IdentityEvaluation.objects.get(organization=self.org)
        self.assertEqual(record.pk, evaluation_id)
        self.assertEqual(record.evidence["sources"][0]["run_ref"], run.pk)
        self.assertTrue(run.fieldproposal_set.exists())

    def test_simultaneous_drafts_reuse_one_worker_and_claim(self):
        evaluation = persist_identity_evaluation(self.user, self.org, [self.run.pk])
        results = self.simultaneous(lambda user, org: prepare_identity_draft(
            user, org, evaluation.pk, self.run.pk, self.region, activity_profile="employee",
        ))
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[0]["status"], "draft")
        self.assertFalse(results[0]["accepted"])
        worker = Worker.objects.get(organization=self.org)
        claim = WorkerIdentityClaim.objects.get(organization=self.org)
        self.assertEqual(results[0]["worker_ref"], worker.pk)
        self.assertEqual(results[0]["claim_ref"], claim.pk)
        self.assertEqual(claim.worker_id, worker.pk)
        self.assertEqual(claim.evaluation_id, evaluation.pk)
        self.assertEqual(claim.ocr_run_id, self.run.pk)
        self.assertEqual(claim.region_id, self.region)
        self.assertEqual(worker.state, Worker.State.DRAFT)
        self.assertEqual(worker.activity_profile, "employee")
        self.assertFalse(FieldDecision.objects.exists())
        self.assertFalse(WorkerIdentityRevision.objects.exists())

    def test_simultaneous_same_worker_resolutions_reuse_one_decision(self):
        worker = Worker.objects.create(
            organization=self.org, given_name="SYNTHETIC", family_name="RESOLUTION",
            birth_date="1992-01-01", activity_profile="employee", version=1,
        )
        evaluation = persist_identity_evaluation(self.user, self.org, [self.run.pk])
        results = self.simultaneous(lambda user, org: resolve_identity_evaluation(
            user, org, evaluation.pk, self.run.pk, self.region, worker.pk,
            expected_worker_version=1, expected_revision_id=None,
            reason="Synthetic operator association",
        ).pk)
        self.assertEqual(results[0], results[1])
        resolution = IdentityResolution.objects.get(organization=self.org)
        association = DocumentRegionAssociation.objects.get(organization=self.org)
        self.assertEqual(results[0], resolution.pk)
        self.assertEqual(resolution.association_id, association.pk)
        self.assertEqual(resolution.evaluation_id, evaluation.pk)
        self.assertEqual(association.worker_id, worker.pk)
        self.assertEqual(association.ocr_run_id, self.run.pk)
        self.assertEqual(association.region_id, self.region)
        self.assertFalse(FieldDecision.objects.exists())
        self.assertFalse(WorkerIdentityRevision.objects.exists())

    def test_simultaneous_different_worker_resolutions_reject_losing_decision(self):
        workers = [Worker.objects.create(
            organization=self.org, given_name="SYNTHETIC", family_name=family,
            birth_date="1992-01-01", activity_profile="employee", version=1,
        ) for family in ("FIRST", "SECOND")]
        evaluation = persist_identity_evaluation(self.user, self.org, [self.run.pk])

        def resolve(worker):
            def operation(user, org):
                try:
                    resolution = resolve_identity_evaluation(
                        user, org, evaluation.pk, self.run.pk, self.region, worker.pk,
                        expected_worker_version=1, expected_revision_id=None,
                        reason="Synthetic operator association",
                    )
                    return ("resolved", worker.pk, resolution.pk)
                except ValueError as error:
                    return ("rejected", worker.pk, str(error))
            return operation

        results = self.simultaneous(resolve(workers[0]), resolve(workers[1]))
        self.assertCountEqual([result[0] for result in results], ["resolved", "rejected"])
        winner = next(result for result in results if result[0] == "resolved")
        loser = next(result for result in results if result[0] == "rejected")
        self.assertEqual(loser[2], "ASSOCIATION_ALREADY_DECIDED")
        self.assertNotEqual(winner[1], loser[1])
        resolution = IdentityResolution.objects.get(organization=self.org)
        association = DocumentRegionAssociation.objects.get(organization=self.org)
        self.assertEqual(resolution.pk, winner[2])
        self.assertEqual(resolution.association_id, association.pk)
        self.assertEqual(association.worker_id, winner[1])
        self.assertEqual(association.ocr_run_id, self.run.pk)
        self.assertEqual(association.region_id, self.region)
        self.assertFalse(FieldDecision.objects.exists())
        self.assertFalse(WorkerIdentityRevision.objects.exists())


@skipUnless(connection.vendor == "postgresql", "Disposable PostgreSQL required")
class PostgresIdentityMigrationTests(TransactionTestCase):
    def test_0014_preserves_workers_and_enforces_tenant_unique_keys(self):
        before = [("release1a", "0013_alter_a1case_visual_confirmed_by")]
        after = [("release1a", "0014_identity_evaluation_and_draft_claim")]
        executor = MigrationExecutor(connection)
        leaves = executor.loader.graph.leaf_nodes()
        try:
            executor.migrate(before)
            old = executor.loader.project_state(before).apps
            org = old.get_model("release1a", "Organization").objects.create(
                key="synthetic-migration", label="Synthetic Migration",
            )
            worker = old.get_model("release1a", "Worker").objects.create(
                organization_id=org.pk, given_name="SYNTHETIC", family_name="MIGRATION",
                birth_date="1990-01-01", activity_profile="employee", state="active", version=7,
            )
            original = old.get_model("release1a", "Worker").objects.values().get(pk=worker.pk)
            executor = MigrationExecutor(connection)
            executor.migrate(after)
            apps = executor.loader.project_state(after).apps
            self.assertEqual(apps.get_model("release1a", "Worker").objects.values().get(pk=worker.pk), original)
            Evaluation = apps.get_model("release1a", "IdentityEvaluation")
            Claim = apps.get_model("release1a", "WorkerIdentityClaim")
            other = apps.get_model("release1a", "Organization").objects.create(
                key="synthetic-migration-other", label="Synthetic Other",
            )
            for organization in (org, other):
                evaluation = Evaluation.objects.create(
                    organization_id=organization.pk, evaluation_sha256="a" * 64,
                )
                with self.assertRaises(IntegrityError), transaction.atomic():
                    Evaluation.objects.create(
                        organization_id=organization.pk, evaluation_sha256="a" * 64,
                    )
                document = apps.get_model("release1a", "Document").objects.create(
                    organization_id=organization.pk, opaque_key=f"synthetic-{organization.pk}",
                    sha256="b" * 64, content_type="image/png",
                )
                version = apps.get_model("release1a", "DocumentVersion").objects.create(
                    organization_id=organization.pk, document=document, version_number=1,
                    opaque_key=document.opaque_key, sha256=document.sha256,
                    content_type="image/png", byte_size=1,
                )
                run = apps.get_model("release1a", "OcrRun").objects.create(
                    organization_id=organization.pk, document=document, version=version,
                )
                tenant_worker = apps.get_model("release1a", "Worker").objects.create(
                    organization_id=organization.pk, given_name="SYNTHETIC", family_name="CLAIM",
                    birth_date="1991-01-01", activity_profile="employee",
                )
                values = dict(organization_id=organization.pk, identifier_sha256="c" * 64,
                              worker_id=tenant_worker.pk, evaluation=evaluation, ocr_run=run,
                              region_id="00000000-0000-4000-8000-000000000001")
                Claim.objects.create(**values)
                with self.assertRaises(IntegrityError), transaction.atomic():
                    Claim.objects.create(**values)
            self.assertEqual(Evaluation.objects.filter(evaluation_sha256="a" * 64).count(), 2)
            self.assertEqual(Claim.objects.filter(identifier_sha256="c" * 64).count(), 2)
        finally:
            MigrationExecutor(connection).migrate(leaves)
