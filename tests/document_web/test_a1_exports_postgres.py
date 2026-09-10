"""Synthetic A1 input races and historical migration on disposable PostgreSQL."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless

from allauth.mfa.models import Authenticator
from django.contrib.auth import get_user_model
from django.db import close_old_connections, connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase, override_settings

from portal.release1a.a1_exports import prepare_input_case, update_assignment_facts
from portal.release1a.models import A1Case, Assignment, Membership, Organization, Worker
from portal.release1a.services import StaleWrite


@skipUnless(connection.vendor == "postgresql", "Disposable PostgreSQL required")
@override_settings(M2_SYNTHETIC_ONLY=True)
class PostgresA1InputConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            key="synthetic-a1-race", label="Synthetic A1 Race",
        )
        self.user = get_user_model().objects.create_user("synthetic-a1-operator")
        Membership.objects.create(
            user=self.user, organization=self.org, role="organization_admin",
        )
        Authenticator.objects.create(user=self.user, type=Authenticator.Type.TOTP, data={})
        self.worker = Worker.objects.create(
            organization=self.org, given_name="SYNTHETIC", family_name="A1 RACE",
            birth_date="1992-01-01", activity_profile="employee",
        )
        self.assignment = Assignment.objects.create(
            organization=self.org, worker=self.worker,
            workplace_label="Synthetic workplace", activity_label="Synthetic activity",
            start="2026-01-01", end="2026-12-31",
        )

    def simultaneous(self, operation, other_operation=None):
        barrier = Barrier(2, timeout=10)

        def invoke(call):
            close_old_connections()
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SET statement_timeout = '10s'")
                    cursor.execute("SET lock_timeout = '5s'")
                    cursor.execute("SELECT pg_backend_pid()")
                    backend = cursor.fetchone()[0]
                user = get_user_model().objects.get(pk=self.user.pk)
                organization = Organization.objects.get(pk=self.org.pk)
                barrier.wait()
                return backend, call(user, organization)
            finally:
                connection.close()

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(invoke, call)
                       for call in (operation, other_operation or operation)]
            results = [future.result(timeout=30) for future in futures]
        self.assertNotEqual(results[0][0], results[1][0])
        return [result for _, result in results]

    def test_simultaneous_same_worker_input_reuses_one_case(self):
        results = self.simultaneous(lambda user, org: prepare_input_case(
            user, org, self.worker.pk, assignment_id=self.assignment.pk,
        ).pk)
        self.assertEqual(results[0], results[1])
        case = A1Case.objects.get(organization=self.org, worker=self.worker)
        self.assertEqual(case.pk, results[0])
        self.assertEqual(case.source_snapshot_json["schema_version"], "a1-input-1")
        self.assertEqual(case.source_snapshot_json["dependencies"]["assignment"]["ref"],
                         self.assignment.pk)
        self.assertFalse(case.is_stale)

    def test_competing_assignment_updates_reject_stale_version(self):
        def update(name):
            def operation(user, org):
                facts = {"employment": {"employer_name": name}}
                try:
                    assignment = update_assignment_facts(
                        user, org, self.assignment.pk, facts, expected_version=1,
                    )
                    return "updated", assignment.version, facts
                except StaleWrite as error:
                    return "stale", str(error), facts
            return operation

        results = self.simultaneous(update("Synthetic First"), update("Synthetic Second"))
        self.assertCountEqual([result[0] for result in results], ["updated", "stale"])
        winner = next(result for result in results if result[0] == "updated")
        loser = next(result for result in results if result[0] == "stale")
        self.assertEqual(winner[1], 2)
        self.assertEqual(loser[1], "ASSIGNMENT_VERSION_STALE")
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.version, 2)
        self.assertEqual(self.assignment.a1_facts_json, winner[2])
        self.assertNotEqual(self.assignment.a1_facts_json, loser[2])


    def test_assignment_editor_and_fact_update_share_version_lock(self):
        from concurrent.futures import TimeoutError
        from threading import Event
        from unittest.mock import patch
        from django.test import Client
        from tests.test_j4_minimum import _mfa_login
        from portal.release1a.forms import AssignmentForm
        self.user.set_password('test-m2'); self.user.save()
        client=Client(); _mfa_login(client,self.user)
        ready, release, updating=Event(),Event(),Event()
        original=AssignmentForm.is_valid
        def pause(form):
            valid=original(form)
            ready.set()
            if not release.wait(10): raise RuntimeError('Synthetic timeout')
            return valid
        def details():
            close_old_connections()
            try:
                return client.post(f'/workers/{self.worker.pk}/assignments/{self.assignment.pk}/edit/',
                    {'version':1,'workplace_label':'Synthetic edited','activity_label':'Synthetic',
                     'start':'2026-01-01','end':'2026-12-31','state':'planned'}).status_code
            finally: connection.close()
        def facts():
            close_old_connections()
            try:
                updating.set()
                try:
                    update_assignment_facts(self.user,self.org,self.assignment.pk,
                        {'employment':{'employer_id':'SYNTHETIC-RACE'}},expected_version=1)
                    return 'updated'
                except StaleWrite: return 'stale'
            finally: connection.close()
        with patch.object(AssignmentForm,'is_valid',pause), ThreadPoolExecutor(max_workers=2) as pool:
            edit=pool.submit(details)
            try:
                self.assertTrue(ready.wait(10))
                update=pool.submit(facts)
                self.assertTrue(updating.wait(10))
                # A fact update cannot commit while the editor holds an older instance.
                with self.assertRaises(TimeoutError): update.result(timeout=0.5)
            finally: release.set()
            self.assertEqual(edit.result(timeout=15),302)
            self.assertEqual(update.result(timeout=15),'stale')
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.version,2)
        self.assertEqual(self.assignment.a1_facts_json,{})
        self.assertEqual(self.assignment.workplace_label,'Synthetic edited')


@skipUnless(connection.vendor == "postgresql", "Disposable PostgreSQL required")
class PostgresA1FactsMigrationTests(TransactionTestCase):
    def test_0015_preserves_records_defaults_facts_and_reverses(self):
        before = [("release1a", "0014_identity_evaluation_and_draft_claim")]
        after = [("release1a", "0015_assignment_a1_facts")]
        executor = MigrationExecutor(connection)
        leaves = executor.loader.graph.leaf_nodes()
        try:
            executor.migrate(before)
            old = executor.loader.project_state(before).apps
            org = old.get_model("release1a", "Organization").objects.create(
                key="synthetic-a1-migration", label="Synthetic A1 Migration",
            )
            worker = old.get_model("release1a", "Worker").objects.create(
                organization_id=org.pk, given_name="SYNTHETIC", family_name="MIGRATION",
                birth_date="1990-01-01", activity_profile="employee", version=7,
            )
            assignment = old.get_model("release1a", "Assignment").objects.create(
                organization_id=org.pk, worker_id=worker.pk,
                workplace_label="Synthetic retained workplace",
                activity_label="Synthetic retained activity", state="active", version=3,
                start="2026-01-01", end="2026-12-31",
            )
            original_worker = old.get_model("release1a", "Worker").objects.values().get(pk=worker.pk)
            original_assignment = old.get_model("release1a", "Assignment").objects.values().get(pk=assignment.pk)

            executor = MigrationExecutor(connection)
            executor.migrate(after)
            apps = executor.loader.project_state(after).apps
            self.assertEqual(apps.get_model("release1a", "Worker").objects.values().get(pk=worker.pk),
                             original_worker)
            migrated = apps.get_model("release1a", "Assignment").objects.values().get(pk=assignment.pk)
            self.assertEqual(migrated.pop("a1_facts_json"), {})
            self.assertEqual(migrated, original_assignment)
            apps.get_model("release1a", "Assignment").objects.filter(pk=assignment.pk).update(
                a1_facts_json={"employment": {"employer_name": "Synthetic migration facts"}},
            )

            executor = MigrationExecutor(connection)
            executor.migrate(before)
            restored = executor.loader.project_state(before).apps
            self.assertEqual(restored.get_model("release1a", "Worker").objects.values().get(pk=worker.pk),
                             original_worker)
            self.assertEqual(restored.get_model("release1a", "Assignment").objects.values().get(pk=assignment.pk),
                             original_assignment)
        finally:
            MigrationExecutor(connection).migrate(leaves)
