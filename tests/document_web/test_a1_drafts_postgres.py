"""Independent-connection reservation races and historical schema acceptance."""
from unittest import skipUnless

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from . import test_a1_drafts as draft_tests
from . import test_a1_exports as export_tests


@skipUnless(connection.vendor == "postgresql", "Disposable PostgreSQL required")
class PostgresA1DraftMigrationTests(TransactionTestCase):
    def test_0016_preserves_case_and_worker_and_reverses(self):
        before = [("release1a", "0015_assignment_a1_facts")]
        after = [("release1a", "0016_a1_draft_reservation")]
        executor = MigrationExecutor(connection)
        leaves = executor.loader.graph.leaf_nodes()
        try:
            executor.migrate(before)
            old = executor.loader.project_state(before).apps
            org = old.get_model("release1a", "Organization").objects.create(
                key="synthetic-draft-migration", label="Synthetic Draft Migration")
            worker = old.get_model("release1a", "Worker").objects.create(
                organization_id=org.pk, given_name="Synthetic", family_name="Migration",
                birth_date="1991-03-02", activity_profile="self_employed", version=4)
            case = old.get_model("release1a", "A1Case").objects.create(
                organization_id=org.pk, worker_id=worker.pk, readiness="blocked",
                source_hash="a" * 64, source_snapshot_json={"synthetic": "retained"})
            original_worker = old.get_model("release1a", "Worker").objects.values().get(pk=worker.pk)
            original_case = old.get_model("release1a", "A1Case").objects.values().get(pk=case.pk)
            executor = MigrationExecutor(connection)
            executor.migrate(after)
            current = executor.loader.project_state(after).apps
            self.assertEqual(current.get_model("release1a", "Worker").objects.values().get(pk=worker.pk), original_worker)
            self.assertEqual(current.get_model("release1a", "A1Case").objects.values().get(pk=case.pk), original_case)
            reservations = current.get_model("release1a", "A1DraftReservation")
            self.assertEqual(reservations.objects.count(), 0)
            reservations.objects.create(organization_id=org.pk, case_id=case.pk,
                document_id="SYNTHETIC-MIGRATION-001", reference_date="2026-09-09",
                snapshot={"synthetic": "reservation"}, snapshot_sha256="b" * 64,
                dependencies={"synthetic": "dependency"})
            executor = MigrationExecutor(connection)
            executor.migrate(before)
            restored = executor.loader.project_state(before).apps
            self.assertEqual(restored.get_model("release1a", "Worker").objects.values().get(pk=worker.pk), original_worker)
            self.assertEqual(restored.get_model("release1a", "A1Case").objects.values().get(pk=case.pk), original_case)
        finally:
            MigrationExecutor(connection).migrate(leaves)


@skipUnless(connection.vendor == "postgresql", "Disposable PostgreSQL required")
class PostgresA1DraftConcurrencyTests(TransactionTestCase):
    setUp = draft_tests.setup_draft
    evaluation = export_tests.A1ExportTests.evaluation
    draft = export_tests.A1ExportTests.draft

    def test_same_case_reservation_reuses_number_and_package_key(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.contrib.auth import get_user_model
        from django.db import close_old_connections
        from portal.release1a.a1_drafts import reserve_application_draft
        from portal.release1a.models import A1DraftReservation, Organization

        barrier = Barrier(2, timeout=10)

        def reserve():
            close_old_connections()
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SET statement_timeout = '10s'")
                    cursor.execute("SET lock_timeout = '5s'")
                    cursor.execute("SELECT pg_backend_pid()")
                    backend = cursor.fetchone()[0]
                user = get_user_model().objects.get(pk=self.user.pk)
                org = Organization.objects.get(pk=self.org.pk)
                barrier.wait()
                result = reserve_application_draft(user, org, self.case.pk)
                return backend, result.pk, result.document_id, result.package_key
            finally:
                connection.close()

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(reserve) for _ in range(2)]
            results = [future.result(timeout=30) for future in futures]
        self.assertNotEqual(results[0][0], results[1][0])
        self.assertEqual(results[0][1:], results[1][1:])
        self.assertEqual(A1DraftReservation.objects.filter(case=self.case).count(), 1)
        self.case.refresh_from_db()
        self.assertFalse(self.case.artifact_reference)
        self.assertFalse(self.case.visual_confirmed)
        self.assertEqual(self.case.external_status, "not_submitted")
