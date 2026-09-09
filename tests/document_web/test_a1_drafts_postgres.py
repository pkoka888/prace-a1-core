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


    def test_0017_preserves_legacy_packages_and_guards_revision_rollback(self):
        import uuid
        from src.document_core.serialization import result_hash

        before = [("release1a", "0016_a1_draft_reservation")]
        after = [("release1a", "0017_a1_draft_generation")]
        executor = MigrationExecutor(connection)
        leaves = executor.loader.graph.leaf_nodes()
        try:
            executor.migrate(before)
            old = executor.loader.project_state(before).apps
            org = old.get_model("release1a", "Organization").objects.create(
                key="synthetic-generation-migration", label="Synthetic Generation Migration")
            worker = old.get_model("release1a", "Worker").objects.create(
                organization_id=org.pk, given_name="Synthetic", family_name="Generation", birth_date="1991-03-02")
            originals = []
            for published in (False, True):
                package_key = uuid.uuid4()
                snapshot = {"row": {"document_id": "SYNTHETIC-" + str(published)}, "label": "Příprava"}
                dependencies = {"synthetic": "original"}
                reference = {"key": package_key.hex, "pdf_sha256": "c" * 64} if published else {}
                case = old.get_model("release1a", "A1Case").objects.create(
                    organization_id=org.pk, worker_id=worker.pk, source_hash=str(int(published)) * 64,
                    artifact_reference=reference, artifact_dependencies=dependencies if published else {},
                    prepared_artifact_hash="c" * 64 if published else "")
                reservation = old.get_model("release1a", "A1DraftReservation").objects.create(
                    organization_id=org.pk, case_id=case.pk, package_key=package_key,
                    document_id=snapshot["row"]["document_id"], reference_date="2026-09-09",
                    snapshot=snapshot, snapshot_sha256=result_hash(snapshot), dependencies=dependencies)
                originals.append((reservation.pk, old.get_model("release1a", "A1Case").objects.values().get(pk=case.pk)))
            executor = MigrationExecutor(connection)
            executor.migrate(after)
            current = executor.loader.project_state(after).apps
            Generation = current.get_model("release1a", "A1DraftGeneration")
            for reservation_id, original_case in originals:
                reservation = current.get_model("release1a", "A1DraftReservation").objects.get(pk=reservation_id)
                generation = Generation.objects.get(reservation_id=reservation_id)
                self.assertEqual(generation.revision, 1)
                for field in ("package_key", "snapshot", "snapshot_sha256", "dependencies"):
                    self.assertEqual(getattr(generation, field), getattr(reservation, field))
                self.assertEqual(generation.fingerprint, result_hash({"snapshot": reservation.snapshot, "dependencies": reservation.dependencies}))
                for field in ("artifact_reference", "artifact_dependencies", "prepared_artifact_hash"):
                    self.assertEqual(getattr(generation, field), original_case[field])
                self.assertEqual(current.get_model("release1a", "A1Case").objects.values().get(pk=original_case["id"]), original_case)
            extra = Generation.objects.create(organization_id=org.pk, reservation_id=originals[0][0],
                revision=2, fingerprint="d" * 64, snapshot={}, snapshot_sha256=result_hash({}), dependencies={})
            with self.assertRaisesMessage(ValueError, "A1_DRAFT_GENERATIONS_PREVENT_ROLLBACK"):
                MigrationExecutor(connection).migrate(before)
            Generation.objects.filter(pk=extra.pk).delete()
            first = Generation.objects.get(reservation_id=originals[0][0])
            Generation.objects.filter(pk=first.pk).update(artifact_reference={"key": first.package_key.hex})
            with self.assertRaisesMessage(ValueError, "A1_DRAFT_GENERATION_DATA_PREVENT_ROLLBACK"):
                MigrationExecutor(connection).migrate(before)
            Generation.objects.filter(pk=first.pk).update(artifact_reference={})
            MigrationExecutor(connection).migrate(before)
            restored = MigrationExecutor(connection).loader.project_state(before).apps
            self.assertEqual(restored.get_model("release1a", "A1DraftReservation").objects.count(), 2)
            for _, original_case in originals:
                self.assertEqual(restored.get_model("release1a", "A1Case").objects.values().get(pk=original_case["id"]), original_case)
        finally:
            MigrationExecutor(connection).migrate(leaves)


    def test_0017_rejects_inconsistent_legacy_package(self):
        from src.document_core.serialization import result_hash
        before = [("release1a", "0016_a1_draft_reservation")]
        after = [("release1a", "0017_a1_draft_generation")]
        executor = MigrationExecutor(connection)
        leaves = executor.loader.graph.leaf_nodes()
        case = None
        try:
            executor.migrate(before)
            old = executor.loader.project_state(before).apps
            org = old.get_model("release1a", "Organization").objects.create(
                key="synthetic-inconsistent-generation", label="Synthetic Inconsistent Generation")
            worker = old.get_model("release1a", "Worker").objects.create(
                organization_id=org.pk, given_name="Synthetic", family_name="Mismatch", birth_date="1991-03-02")
            Case = old.get_model("release1a", "A1Case")
            case = Case.objects.create(organization_id=org.pk, worker_id=worker.pk,
                artifact_reference={"key": "f" * 32})
            old.get_model("release1a", "A1DraftReservation").objects.create(
                organization_id=org.pk, case_id=case.pk, document_id="SYNTHETIC-MISMATCH",
                reference_date="2026-09-09", snapshot={"row": {"document_id": "SYNTHETIC-MISMATCH"}},
                snapshot_sha256=result_hash({"row": {"document_id": "SYNTHETIC-MISMATCH"}}), dependencies={})
            with self.assertRaisesMessage(ValueError, "A1_DRAFT_GENERATION_LEGACY_PACKAGE_MISMATCH"):
                MigrationExecutor(connection).migrate(after)
        finally:
            if case is not None:
                Case.objects.filter(pk=case.pk).update(artifact_reference={})
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


    def test_same_case_generation_reservation_is_idempotent(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.contrib.auth import get_user_model
        from django.db import close_old_connections
        from portal.release1a.a1_drafts import reserve_application_generation
        from portal.release1a.models import A1DraftGeneration, A1DraftReservation, Organization

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
                generation = reserve_application_generation(user, org, self.case.pk)
                return backend, generation.pk, generation.reservation_id, generation.package_key
            finally:
                connection.close()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = [future.result(timeout=30) for future in [executor.submit(reserve) for _ in range(2)]]
        self.assertNotEqual(results[0][0], results[1][0])
        self.assertEqual(results[0][1:], results[1][1:])
        self.assertEqual(A1DraftReservation.objects.filter(case=self.case).count(), 1)
        self.assertEqual(A1DraftGeneration.objects.filter(reservation__case=self.case).count(), 1)


    def test_generation_inputs_and_published_artifact_are_immutable(self):
        from portal.release1a.a1_drafts import reserve_application_generation
        from portal.release1a.models import Organization

        generation = reserve_application_generation(self.user, self.org, self.case.pk)
        generation.snapshot = {"changed": True}
        with self.assertRaisesMessage(ValueError, "A1_DRAFT_GENERATION_IMMUTABLE"):
            generation.save()
        generation.refresh_from_db()
        generation.artifact_reference = {"key": generation.package_key.hex}
        generation.artifact_dependencies = {"synthetic": True}
        generation.prepared_artifact_hash = "a" * 64
        generation.save(update_fields=["artifact_reference", "artifact_dependencies", "prepared_artifact_hash"])
        generation.prepared_artifact_hash = "b" * 64
        with self.assertRaisesMessage(ValueError, "A1_DRAFT_GENERATION_ARTIFACT_IMMUTABLE"):
            generation.save()
        generation.refresh_from_db()
        other = Organization.objects.create(key="synthetic-other-generation", label="Synthetic Other")
        generation.organization = other
        with self.assertRaisesMessage(ValueError, "A1_DRAFT_GENERATION_ORGANIZATION_MISMATCH"):
            generation.save()
