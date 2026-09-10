"""Selected compatibility inputs preserve canonical rows and source revisions."""
import csv
import hashlib
import io
import json
from unittest.mock import patch
from django.test import TransactionTestCase
from . import test_intake as fixtures
from portal.release1a.models import Worker, A1Case, AuditEvent
from portal.release1a.a1_exports import prepare_input_case, export_input_case, export_input_cohort
from portal.release1a.legacy_reconciliation import reconcile_legacy_keys
from portal.release1a.services import Forbidden, StaleWrite


class CohortExportTests(TransactionTestCase):
    def setUp(self):
        fixtures.IntakeTests.setUp(self)
        second=Worker.objects.create(organization=self.org,given_name='BETA',family_name='SYNTHETIC',birth_date='1980-01-01',activity_profile='self_employed')
        reconcile_legacy_keys(self.user,self.org,[{'worker_id':self.worker.pk,'expected_version':1,'legacy_employee_id':'synthetic-alfa'}],source_sha256='a'*64)
        self.cases=[prepare_input_case(self.user,self.org,w.pk) for w in (self.worker,second)]
        self.selections=[{'case_id':c.pk,'expected_source_hash':c.source_hash} for c in self.cases]

    def export(self, selections=None):
        return export_input_cohort(self.user,self.org,self.selections if selections is None else selections)

    def test_deterministic_round_trip_and_hash_manifest(self):
        package=self.export()
        self.assertEqual(package,self.export(list(reversed(self.selections))))
        rows=list(csv.DictReader(io.StringIO(package['review.csv'].decode())))
        employees=json.loads(package['employees_normalized.json'])['employees']
        cohort=json.loads(package['cohort.json'])
        manifest=json.loads(package['manifest.json'])
        snapshots=json.loads(package['input_snapshots.json'])['snapshots']
        self.assertEqual({r['employee_id'] for r in rows},{e['id'] for e in employees})
        self.assertEqual(set(cohort['document_ids']),{r['employee_id'] for r in rows})
        for name,digest in manifest['payload_sha256'].items():
            self.assertEqual(hashlib.sha256(package[name]).hexdigest(),digest)
        for row,employee,snapshot in zip(rows,employees,snapshots):
            self.assertEqual(row,snapshot['row'])
            self.assertEqual(row['employee_id'],employee['id'])
            for group in ('person','residence'):
                for field,value in employee[group].items(): self.assertEqual(row[field],value)
            self.assertEqual(cohort['issue_dates'][employee['id']],row['issue_date'])
            self.assertEqual(row['identity_reviewed'],'NO')
            self.assertEqual(row['validated_by_user'],'0')
        for case in self.cases:
            single=json.loads(export_input_case(self.user,self.org,case.pk)['json'])
            self.assertIn(single,snapshots)

    def test_selection_errors_tenant_checks_and_no_partial_export_audit(self):
        for selections in ([],self.selections+[self.selections[0]],
                           [{'case_id':True,'expected_source_hash':'a'*64}],
                           [{'case_id':self.cases[0].pk,'expected_source_hash':'0'*64}]):
            with self.assertRaises((ValueError,StaleWrite)): self.export(selections)
        with self.assertRaises(Forbidden): export_input_cohort(self.user,self.other,self.selections)
        foreign_worker=Worker.objects.create(organization=self.other,given_name='GAMMA',family_name='SYNTHETIC',birth_date='1980-01-01',activity_profile='employee')
        foreign_case=A1Case.objects.create(organization=self.other,worker=foreign_worker,source_hash='f'*64)
        with self.assertRaises(A1Case.DoesNotExist):
            self.export(self.selections+[{'case_id':foreign_case.pk,'expected_source_hash':foreign_case.source_hash}])
        Worker.objects.filter(pk=self.cases[-1].worker_id).update(version=2)
        before=AuditEvent.objects.filter(event_type='a1.input_exported').count()
        with self.assertRaises(StaleWrite): self.export()
        self.assertEqual(AuditEvent.objects.filter(event_type='a1.input_exported').count(),before)
        self.assertFalse(AuditEvent.objects.filter(event_type='a1.cohort_exported').exists())

    def test_native_key_collision_and_duplicate_certificate_ids_rejected(self):
        from portal.release1a.models import Assignment
        first,second=self.cases
        Worker.objects.filter(pk=first.worker_id).update(legacy_employee_id=f'worker-{second.worker_id}')
        fresh=prepare_input_case(self.user,self.org,first.worker_id)
        with self.assertRaises(ValueError):
            self.export([{'case_id':fresh.pk,'expected_source_hash':fresh.source_hash},self.selections[1]])
        Worker.objects.filter(pk=first.worker_id).update(legacy_employee_id='synthetic-alfa')
        choices=[]
        for case in self.cases:
            Assignment.objects.create(organization=self.org,worker_id=case.worker_id,
                start='2026-01-01',end='2026-12-31',workplace_label='Synthetic',activity_label='Synthetic',
                a1_facts_json={'certificate':{'document_id':'SYNTHETIC-DUPLICATE'}})
            current=prepare_input_case(self.user,self.org,case.worker_id)
            choices.append({'case_id':current.pk,'expected_source_hash':current.source_hash})
        with self.assertRaises(ValueError): self.export(choices)
        self.assertFalse(AuditEvent.objects.filter(event_type='a1.cohort_exported').exists())

    def test_final_audit_failure_rolls_back_per_case_audits(self):
        from portal.release1a import a1_exports
        original=a1_exports.audit
        def fail(user,org,event,reference):
            if event=='a1.cohort_exported': raise RuntimeError('Synthetic failure')
            return original(user,org,event,reference)
        with patch.object(a1_exports,'audit',side_effect=fail),self.assertRaises(RuntimeError): self.export()
        self.assertFalse(AuditEvent.objects.filter(event_type='a1.input_exported').exists())
