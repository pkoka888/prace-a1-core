"""Synthetic legacy mapping, historical migration and export continuity."""
import csv
import io
import json
from unittest import skipUnless
from unittest.mock import patch
from django.db import connection, IntegrityError, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from . import test_intake as fixtures
from portal.release1a.models import Worker, A1Case, AuditEvent, WorkerIdentityRevision
from portal.release1a.legacy_reconciliation import reconcile_legacy_keys
from portal.release1a.a1_exports import prepare_input_case, export_input_case
from portal.release1a.services import Forbidden, StaleWrite


class LegacyReconciliationTests(TransactionTestCase):
    setUp = fixtures.IntakeTests.setUp

    def mapping(self, worker=None, key='synthetic-alfa', version=1):
        return {'worker_id': (worker or self.worker).pk, 'expected_version': version, 'legacy_employee_id': key}

    def apply(self, mappings=None):
        return reconcile_legacy_keys(self.user, self.org, mappings or [self.mapping()], source_sha256='a'*64)

    def test_mapping_invalidates_old_input_and_freezes_key_with_provenance(self):
        old = prepare_input_case(self.user, self.org, self.worker.pk)
        self.assertEqual(json.loads(export_input_case(self.user,self.org,old.pk)['json'])['employee_id'], f'worker-{self.worker.pk}')
        first = self.apply()[0]
        again = self.apply()[0]
        self.assertEqual(first.legacy_key_provenance, again.legacy_key_provenance)
        self.assertEqual(again.version, 2)
        self.assertEqual(AuditEvent.objects.filter(event_type='worker.legacy_key_reconciled').count(), 1)
        with self.assertRaises(StaleWrite): export_input_case(self.user,self.org,old.pk)
        case = prepare_input_case(self.user, self.org, self.worker.pk)
        package = export_input_case(self.user,self.org,case.pk)
        snapshot = json.loads(package['json'])
        row = next(csv.DictReader(io.StringIO(package['csv'].decode())))
        self.assertEqual(row['employee_id'], 'synthetic-alfa')
        self.assertEqual(snapshot['employee_id'], row['employee_id'])
        self.assertEqual(snapshot['provenance']['employee_id']['source_sha256'], 'a'*64)
        self.assertEqual(row['identity_reviewed'], 'NO')
        self.assertFalse(WorkerIdentityRevision.objects.exists())

    def test_duplicate_collision_stale_batch_and_reserved_namespace(self):
        other = Worker.objects.create(organization=self.org,given_name='BETA',family_name='SYNTHETIC',birth_date='1980-01-01',activity_profile='employee')
        for mappings in ([self.mapping(),self.mapping()], [self.mapping(),self.mapping(other)],
                         [self.mapping(),self.mapping(other,'synthetic-beta',2)],
                         [self.mapping(key=f'worker-{other.pk}')]):
            with self.assertRaises((ValueError,StaleWrite)): self.apply(mappings)
            self.assertFalse(Worker.objects.exclude(legacy_employee_id=None).exists())
        self.apply()
        with self.assertRaises(ValueError): self.apply([self.mapping(other)])
        with self.assertRaises(ValueError): self.apply([self.mapping(key='synthetic-new',version=2)])
        Worker.objects.filter(pk=self.worker.pk).update(version=3)
        with self.assertRaises(StaleWrite): self.apply()

    def test_atomic_audit_failure_and_tenant_authorization(self):
        with patch('portal.release1a.legacy_reconciliation.audit',side_effect=RuntimeError('synthetic failure')):
            with self.assertRaises(RuntimeError): self.apply()
        self.worker.refresh_from_db()
        self.assertIsNone(self.worker.legacy_employee_id)
        self.assertEqual(self.worker.version,1)
        with self.assertRaises(Forbidden):
            reconcile_legacy_keys(self.user,self.other,[self.mapping()],source_sha256='a'*64)
        foreign = Worker.objects.create(organization=self.other,given_name='BETA',family_name='SYNTHETIC',birth_date='1980-01-01',activity_profile='employee')
        with self.assertRaises(ValueError): self.apply([self.mapping(),self.mapping(foreign,'synthetic-beta')])
        self.assertFalse(Worker.objects.exclude(legacy_employee_id=None).exists())

    def test_constraints_allow_unmapped_workers_and_same_key_across_tenants(self):
        self.apply()
        values=dict(given_name='BETA',family_name='SYNTHETIC',birth_date='1980-01-01',activity_profile='employee')
        Worker.objects.create(organization=self.org,**values)
        Worker.objects.create(organization=self.other,legacy_employee_id='synthetic-alfa',**values)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Worker.objects.create(organization=self.org,legacy_employee_id='synthetic-alfa',**values)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Worker.objects.create(organization=self.org,legacy_employee_id='',**values)


@skipUnless(connection.vendor == 'postgresql','Disposable PostgreSQL required')
class LegacyReconciliationPostgresTests(TransactionTestCase):
    setUp = fixtures.IntakeTests.setUp
    mapping = LegacyReconciliationTests.mapping
    apply = LegacyReconciliationTests.apply

    def test_historical_workers_preserved_and_mapped_keys_block_rollback(self):
        before=[('release1a','0018_a1_generation_confirmation')]
        after=[('release1a','0019_worker_legacy_key')]
        executor=MigrationExecutor(connection)
        leaves=executor.loader.graph.leaf_nodes()
        try:
            executor.migrate(before)
            old=executor.loader.project_state(before).apps
            original=old.get_model('release1a','Worker').objects.values().get(pk=self.worker.pk)
            executor=MigrationExecutor(connection); executor.migrate(after)
            apps=executor.loader.project_state(after).apps
            current=apps.get_model('release1a','Worker').objects.values().get(pk=self.worker.pk)
            self.assertIsNone(current.pop('legacy_employee_id'))
            self.assertEqual(current.pop('legacy_key_provenance'),{})
            self.assertEqual(current,original)
            self.apply()
            with self.assertRaises(ValueError): MigrationExecutor(connection).migrate(before)
            self.worker.refresh_from_db()
            self.assertEqual(self.worker.legacy_employee_id,'synthetic-alfa')
        finally:
            MigrationExecutor(connection).migrate(leaves)

    def test_concurrent_key_claims_have_one_winner(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.db import close_old_connections
        other=Worker.objects.create(organization=self.org,given_name='BETA',family_name='SYNTHETIC',birth_date='1980-01-01',activity_profile='employee')
        barrier=Barrier(2,timeout=10)
        def submit(worker):
            close_old_connections()
            try:
                with connection.cursor() as cursor: cursor.execute("SET statement_timeout = '15s'")
                barrier.wait()
                try: self.apply([self.mapping(worker)]); return 'mapped'
                except ValueError: return 'collision'
            finally: connection.close()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(submit,[self.worker,other]))
        self.assertCountEqual(results,['mapped','collision'])
        self.assertEqual(Worker.objects.filter(legacy_employee_id='synthetic-alfa').count(),1)
