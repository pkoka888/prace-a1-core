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


    def address_source(self):
        return FieldProposal.objects.create(organization=self.org, document=self.doc,
            version=self.version, ocr_run=self.run, document_region_id=self.birth.document_region_id,
            field_name='residence_address', proposed_value='Testovaci 12, 12345 Testov')

    def address_values(self):
        return dict(street='Testovaci', house_number='12', city='Testov',
                    postal_code='12345', country_code='CZ')

    def test_address_http_confirmation_maps_to_a1_without_fabricated_ocr(self):
        from portal.release1a.field_review import address_review_context
        from portal.release1a.a1_exports import prepare_input_case
        from portal.release1a.models import A1Case
        source = self.address_source()
        before = prepare_input_case(self.user, self.org, self.worker.pk)
        count = FieldProposal.objects.count()
        page = self.client.get(self.url)
        self.assertContains(page, 'name="address_street"')
        self.assertEqual(FieldProposal.objects.count(), count)
        token = address_review_context(self.user,self.org,source.pk)['token']
        post = {'action':'confirm_address', 'address_source':source.pk, 'address_token':token,
                **{'address_'+f:v for f,v in self.address_values().items()}}
        self.assertEqual(self.client.post(self.url,post).status_code,302)
        self.assertEqual(self.client.post(self.url,post).status_code,409)
        self.assertEqual(FieldDecision.objects.count(),5)
        self.assertFalse(FieldDecision.objects.filter(field_proposal=source).exists())
        entered = FieldProposal.objects.filter(ocr_engine='operator')
        self.assertEqual(entered.count(),5)
        for proposal in entered:
            self.assertEqual(proposal.version_id,self.version.pk)
            self.assertEqual(proposal.document_region_id,source.document_region_id)
            self.assertEqual(proposal.raw_ocr_text,'')
            self.assertIsNone(proposal.confidence)
        before.refresh_from_db(); self.assertTrue(before.is_stale)
        fresh = prepare_input_case(self.user,self.org,self.worker.pk)
        for field,value in self.address_values().items():
            self.assertEqual(fresh.source_snapshot_json['row'][field],value)
            self.assertEqual(fresh.source_snapshot_json['provenance'][field]['kind'],'confirmed_revision')
        self.assertEqual(fresh.source_snapshot_json['row']['identity_reviewed'],'NO')
        self.assertFalse(fresh.visual_confirmed)

    def test_address_validation_replacement_and_noop(self):
        from portal.release1a.field_review import address_review_context, confirm_address_review
        source = self.address_source()
        def save(values, reason=''):
            return confirm_address_review(self.user,self.org,source.pk,
                address_review_context(self.user,self.org,source.pk)['token'],values,reason=reason)
        for values in ({}, dict(self.address_values(), country_code='CZE'),
                       dict(self.address_values(), street='bad\nvalue'),
                       dict(self.address_values(), house_number='')):
            with self.assertRaises(ValueError): save(values)
        self.assertFalse(FieldDecision.objects.exists())
        save(self.address_values())
        count = WorkerIdentityRevision.objects.count()
        self.assertEqual(save(self.address_values()),[])
        self.assertEqual(WorkerIdentityRevision.objects.count(),count)
        changed = dict(self.address_values(), house_number='13')
        with self.assertRaises(ValueError): save(changed)
        save(changed,'Synthetic changed source reviewed')
        self.assertEqual(WorkerIdentityRevision.objects.latest('pk').confirmed_fields['house_number'],'13')

    def test_address_source_revision_auth_and_confirmed_raw_source(self):
        from portal.release1a.field_review import address_review_context, confirm_address_review
        from portal.release1a.document_intake import supersede
        from django.test import override_settings, Client
        source = self.address_source()
        token = address_review_context(self.user,self.org,source.pk)['token']
        confirm_field_proposal(self.user,self.org,source)
        with self.assertRaises(StaleWrite):
            confirm_address_review(self.user,self.org,source.pk,token,self.address_values())
        # Raw OCR text can already be confirmed; structured entry still remains available.
        token = address_review_context(self.user,self.org,source.pk)['token']
        self.assertContains(self.client.get(self.url),'name="address_street"')
        with self.assertRaises(Forbidden): address_review_context(self.user,self.other,source.pk)
        with override_settings(M2_SYNTHETIC_ONLY=False), self.assertRaises(Forbidden):
            address_review_context(self.user,self.org,source.pk)
        csrf = Client(enforce_csrf_checks=True); _mfa_login(csrf,self.user)
        self.assertEqual(csrf.post(self.url,{'action':'confirm_address'}).status_code,403)
        supersede(self.user,self.org,self.doc.pk,'synthetic.png','image/png',
            fixtures.png(fixtures.card(fixtures.ZP)),processor=fixtures.processor(fixtures.ZP))
        with self.assertRaises(StaleWrite):
            confirm_address_review(self.user,self.org,source.pk,token,self.address_values())
        self.assertEqual(FieldDecision.objects.count(),1)

    def test_address_late_failure_rolls_back_all_entered_fields(self):
        from portal.release1a.field_review import address_review_context, confirm_address_review
        source = self.address_source()
        token = address_review_context(self.user,self.org,source.pk)['token']
        from portal.release1a.document_intake import audit as original_audit
        def fail(user, org, event, ref, **kwargs):
            if event == 'identity.address_confirmed': raise RuntimeError('Synthetic failure')
            return original_audit(user, org, event, ref, **kwargs)
        with patch('portal.release1a.document_intake.audit',side_effect=fail):
            with self.assertRaises(RuntimeError):
                confirm_address_review(self.user,self.org,source.pk,token,self.address_values())
        self.assertFalse(FieldProposal.objects.filter(ocr_engine='operator').exists())
        self.assertFalse(FieldDecision.objects.exists())
        self.assertFalse(WorkerIdentityRevision.objects.exists())



    def test_missing_identity_bo_entry_is_explicit_source_bound_and_stale(self):
        from portal.release1a.field_review import missing_identity_context
        context = missing_identity_context(self.user,self.org,self.name.pk)
        self.assertIn('sex',context['fields'])
        self.assertContains(self.client.get(self.url),'identity_sex')
        post = {'action':'confirm_missing_identity','identity_source':self.name.pk,
            'identity_token':context['token'],'identity_sex':'M', 'identity_birth_place':'Synthetic town'}
        self.assertEqual(self.client.post(self.url,post).status_code,302)
        entered = FieldProposal.objects.get(ocr_engine='operator',field_name='sex')
        self.assertEqual(entered.version_id,self.name.version_id)
        self.assertEqual(entered.document_region_id,self.name.document_region_id)
        latest = WorkerIdentityRevision.objects.order_by('-revision_number').first()
        self.assertEqual(latest.confirmed_fields['sex'],'M')
        self.assertEqual(self.client.post(self.url,post).status_code,409)
        self.assertEqual(FieldDecision.objects.count(),2)
        current = missing_identity_context(self.user,self.org,self.name.pk)
        self.assertNotIn('sex',current['fields'])
        self.assertIn('insurance_number',current['fields'])

    def test_missing_identity_rejects_invalid_batch_and_existing_proposals(self):
        from portal.release1a.field_review import missing_identity_context, confirm_missing_identity
        context = missing_identity_context(self.user,self.org,self.name.pk)
        with self.assertRaises(ValueError):
            confirm_missing_identity(self.user,self.org,self.name.pk,context['token'],
                {'birth_place':'Synthetic town','sex':'invalid'})
        self.assertFalse(FieldProposal.objects.filter(ocr_engine='operator').exists())
        with self.assertRaises(ValueError):
            confirm_missing_identity(self.user,self.org,self.name.pk,context['token'],{'given_name':'OTHER'})
        with patch('portal.release1a.field_review.confirm_field_proposal',side_effect=RuntimeError('synthetic')):
            with self.assertRaises(RuntimeError):
                confirm_missing_identity(self.user,self.org,self.name.pk,context['token'],{'sex':'M'})
        self.assertFalse(FieldProposal.objects.filter(ocr_engine='operator').exists())
        with self.assertRaises(Forbidden):
            confirm_missing_identity(self.user,self.other,self.name.pk,context['token'],{'sex':'M'})

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


    def test_concurrent_addresses_cannot_both_confirm(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.db import close_old_connections
        from portal.release1a.field_review import address_review_context, confirm_address_review
        from portal.release1a.models import Organization
        from django.contrib.auth import get_user_model
        source = FieldReviewTests.address_source(self)
        token = address_review_context(self.user,self.org,source.pk)['token']
        barrier = Barrier(2,timeout=10)
        def save(number):
            close_old_connections()
            try:
                user=get_user_model().objects.get(pk=self.user.pk)
                org=Organization.objects.get(pk=self.org.pk)
                with connection.cursor() as cursor:
                    cursor.execute("SET statement_timeout = '15s'")
                    cursor.execute("SET lock_timeout = '10s'")
                barrier.wait()
                try:
                    confirm_address_review(user,org,source.pk,token,
                        dict(FieldReviewTests.address_values(self),house_number=number))
                    return 'confirmed'
                except StaleWrite: return 'stale'
            finally: connection.close()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(save,n) for n in ('12','13')]
            self.assertCountEqual([f.result(timeout=30) for f in futures],['confirmed','stale'])
        self.assertEqual(FieldDecision.objects.count(),5)
        self.assertEqual(WorkerIdentityRevision.objects.count(),5)

    def test_concurrent_missing_identity_entry_has_one_winner(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.contrib.auth import get_user_model
        from django.db import close_old_connections
        from portal.release1a.models import Organization
        from portal.release1a.field_review import missing_identity_context, confirm_missing_identity
        token = missing_identity_context(self.user,self.org,self.name.pk)['token']
        barrier = Barrier(2,timeout=10)
        def confirm(value):
            close_old_connections()
            try:
                user = get_user_model().objects.get(pk=self.user.pk)
                org = Organization.objects.get(pk=self.org.pk)
                with connection.cursor() as cursor:
                    cursor.execute("SET statement_timeout = '15s'")
                    cursor.execute("SET lock_timeout = '10s'")
                barrier.wait()
                try:
                    confirm_missing_identity(user,org,self.name.pk,token,{'sex':value})
                    return 'confirmed'
                except StaleWrite:
                    return 'stale'
            finally:
                connection.close()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(confirm,value) for value in ('M','F')]
            self.assertCountEqual([f.result(timeout=30) for f in futures],['confirmed','stale'])
        self.assertEqual(FieldDecision.objects.count(),1)
        self.assertEqual(FieldProposal.objects.filter(ocr_engine='operator').count(),1)
