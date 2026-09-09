"""Synthetic optimistic field review through the existing confirmation service."""
from unittest import skipUnless
from unittest.mock import patch
from django.test import TransactionTestCase
from django.db import connection
from tests.test_j4_minimum import _mfa_login
from . import test_intake as fixtures
from portal.release1a.document_intake import associate_region
from portal.release1a.field_review import review_context, confirm_review_batch
from portal.release1a.models import FieldProposal, FieldDecision, WorkerIdentityRevision, Membership
from portal.release1a.services import confirm_field_proposal, StaleWrite, Forbidden


class FieldReviewTests(TransactionTestCase):
    ingest = fixtures.IntakeTests.ingest

    def setUp(self):
        fixtures.IntakeTests.setUp(self)
        self.doc, self.version, _, self.run = self.ingest()
        self.birth = FieldProposal.objects.get(ocr_run=self.run, field_name='birth_date')
        self.name = FieldProposal.objects.get(ocr_run=self.run, field_name='given_name')
        associate_region(self.user, self.org, self.run.pk, self.birth.document_region_id, self.worker)
        self.user.set_password('test-m2'); self.user.save()
        _mfa_login(self.client, self.user)
        self.url=f'/documents/{self.doc.pk}/'

    def selections(self, *proposals):
        contexts=review_context(self.user,self.org,[p.pk for p in proposals])
        return [{'proposal_id':p.pk,'expected_token':contexts[p.pk]['token'],'value':p.proposed_value} for p in proposals]

    def test_multi_field_batch_preserves_one_review_snapshot(self):
        decisions=confirm_review_batch(self.user,self.org,self.selections(self.birth,self.name))
        self.assertEqual(len(decisions),2)
        latest=WorkerIdentityRevision.objects.order_by('-revision_number').first()
        self.assertEqual(latest.confirmed_fields['birth_date'],self.birth.proposed_value)
        self.assertEqual(latest.confirmed_fields['given_name'],self.name.proposed_value)
        self.worker.refresh_from_db()
        self.assertEqual(self.worker.given_name,'ALFA')

    def test_stale_other_field_revision_rolls_back_entire_batch(self):
        selections=self.selections(self.birth,self.name)
        confirm_field_proposal(self.user,self.org,self.birth)
        with self.assertRaises(StaleWrite):
            confirm_review_batch(self.user,self.org,[selections[1]])
        self.assertEqual(FieldDecision.objects.count(),1)
        self.assertNotIn('given_name',WorkerIdentityRevision.objects.latest('revision_number').confirmed_fields)

    def test_existing_value_shown_and_replacement_needs_reason(self):
        confirm_field_proposal(self.user,self.org,self.name,corrected_value='OMEGA')
        proposal=FieldProposal.objects.create(organization=self.org,document=self.doc,version=self.version,
            ocr_run=self.run,document_region_id=self.name.document_region_id,
            field_name='given_name',proposed_value='BETA')
        context=review_context(self.user,self.org,[proposal.pk])[proposal.pk]
        self.assertEqual(context['confirmed_value'],'OMEGA')
        selections=[{'proposal_id':proposal.pk,'expected_token':context['token'],'value':'BETA'}]
        with self.assertRaises(ValueError):
            confirm_review_batch(self.user,self.org,selections)
        self.assertEqual(WorkerIdentityRevision.objects.latest('revision_number').confirmed_fields['given_name'],'OMEGA')
        confirm_review_batch(self.user,self.org,selections,reason='Synthetic source reviewed')
        self.assertEqual(WorkerIdentityRevision.objects.latest('revision_number').confirmed_fields['given_name'],'BETA')

    def test_late_failure_rolls_back_all_decisions(self):
        from portal.release1a import field_review
        original=field_review.confirm_field_proposal
        calls=[]
        def fail(*args,**kwargs):
            calls.append(True)
            if len(calls)==2: raise RuntimeError('Synthetic failure')
            return original(*args,**kwargs)
        with patch.object(field_review,'confirm_field_proposal',side_effect=fail), self.assertRaises(RuntimeError):
            confirm_review_batch(self.user,self.org,self.selections(self.birth,self.name))
        self.assertFalse(FieldDecision.objects.exists())
        self.assertFalse(WorkerIdentityRevision.objects.exists())

    def test_http_requires_token_and_rejects_stale_form(self):
        response=self.client.get(self.url)
        self.assertContains(response,f'name="expected_{self.birth.pk}"')
        self.assertIn('no-store',response['Cache-Control'])
        selected=self.selections(self.birth)[0]
        payload={'action':'confirm',f'confirm_{self.birth.pk}':'on', f'value_birth_date_{self.birth.pk}':self.birth.proposed_value}
        self.assertEqual(self.client.post(self.url,payload).status_code,409)
        payload[f'expected_{self.birth.pk}']=selected['expected_token']
        confirm_field_proposal(self.user,self.org,self.name)
        self.assertEqual(self.client.post(self.url,payload).status_code,409)
        payload[f'expected_{self.birth.pk}']=self.selections(self.birth)[0]['expected_token']
        self.assertEqual(self.client.post(self.url,payload).status_code,302)

    def test_cross_org_tampered_tokens_and_association_changes(self):
        selected=self.selections(self.birth)
        with self.assertRaises(Forbidden): review_context(self.user,self.other,[self.birth.pk])
        self.user.is_active=False
        with self.assertRaises(Forbidden): review_context(self.user,self.org,[self.birth.pk])
        self.user.is_active=True
        selected[0]['expected_token']='0'*64
        with self.assertRaises(StaleWrite): confirm_review_batch(self.user,self.org,selected)
        selected=self.selections(self.birth)
        from portal.release1a.models import DocumentRegionAssociation
        DocumentRegionAssociation.objects.filter(ocr_run=self.run).delete()
        with self.assertRaises((StaleWrite,ValueError)):
            confirm_review_batch(self.user,self.org,selected)
        self.assertFalse(FieldDecision.objects.exists())


    def test_disappeared_selection_and_missing_value_cannot_partially_confirm(self):
        selections=self.selections(self.birth,self.name)
        payload={'action':'confirm'}
        for item in selections:
            proposal=FieldProposal.objects.get(pk=item['proposal_id'])
            payload[f'confirm_{proposal.pk}']='on'
            payload[f'expected_{proposal.pk}']=item['expected_token']
            payload[f'value_{proposal.field_name}_{proposal.pk}']=item['value']
        self.birth.delete()
        self.assertEqual(self.client.post(self.url,payload).status_code,409)
        self.assertFalse(FieldDecision.objects.exists())
        selected=self.selections(self.name)[0]
        self.assertEqual(self.client.post(self.url,{'action':'confirm',f'confirm_{self.name.pk}':'on',
            f'expected_{self.name.pk}':selected['expected_token']}).status_code,409)
        self.assertFalse(FieldDecision.objects.exists())

    def test_derivative_must_belong_to_selected_source_version(self):
        from portal.release1a import field_review
        payload=field_review.read_result(self.user,self.org,self.run.pk)
        payload['source_hash']='0'*64
        with patch.object(field_review,'read_result',return_value=payload), self.assertRaises(StaleWrite):
            review_context(self.user,self.org,[self.birth.pk])


@skipUnless(connection.vendor=='postgresql','Disposable PostgreSQL required')
class FieldReviewPostgresTests(TransactionTestCase):
    setUp=FieldReviewTests.setUp
    ingest=fixtures.IntakeTests.ingest
    selections=FieldReviewTests.selections

    def test_concurrent_stale_forms_cannot_both_overwrite_revision(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.contrib.auth import get_user_model
        from django.db import close_old_connections
        from portal.release1a.models import Organization
        selections=[self.selections(self.birth),self.selections(self.name)]
        barrier=Barrier(2,timeout=10)
        def confirm(selected):
            close_old_connections()
            try:
                user=get_user_model().objects.get(pk=self.user.pk)
                org=Organization.objects.get(pk=self.org.pk)
                with connection.cursor() as cursor:
                    cursor.execute("SET statement_timeout = '15s'")
                    cursor.execute("SET lock_timeout = '10s'")
                barrier.wait()
                try:
                    confirm_review_batch(user,org,selected)
                    return 'confirmed'
                except StaleWrite:
                    return 'stale'
            finally:
                connection.close()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(confirm,s) for s in selections]
            results=[f.result(timeout=30) for f in futures]
        self.assertCountEqual(results,['confirmed','stale'])
        self.assertEqual(FieldDecision.objects.count(),1)
        self.assertEqual(WorkerIdentityRevision.objects.count(),1)
