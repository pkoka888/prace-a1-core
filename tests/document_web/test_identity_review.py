"""Synthetic BO association choices bind the displayed source and worker revision."""
from unittest import skipUnless
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TransactionTestCase, override_settings
from tests.test_j4_minimum import _mfa_login
from . import test_intake as fixtures
from portal.release1a.identity_review import association_review_context, confirm_association
from portal.release1a.document_intake import read_result, supersede
from portal.release1a.models import (Worker, Organization, Membership, IdentityEvaluation,
    IdentityResolution, DocumentRegionAssociation, WorkerIdentityRevision, FieldDecision)
from portal.release1a.services import StaleWrite, Forbidden


class IdentityReviewTests(TransactionTestCase):
    ingest = fixtures.IntakeTests.ingest

    def setUp(self):
        fixtures.IntakeTests.setUp(self)
        self.doc, self.version, _, self.run = self.ingest()
        self.region = read_result(self.user, self.org, self.run.pk)['result']['documents'][0]['document_id']
        self.user.set_password('test-m2'); self.user.save()
        _mfa_login(self.client, self.user)
        self.url = f'/documents/{self.doc.pk}/'

    def token(self, worker=None):
        options = association_review_context(self.user, self.org, [self.run.pk])[(self.run.pk, self.region)]['worker_options']
        return next(item['token'] for item in options if item['worker'].pk == (worker or self.worker).pk)

    def confirm(self, token, **kwargs):
        return confirm_association(self.user, self.org, token=token,
            reason=kwargs.pop('reason', 'Synthetic original reviewed'),
            allowed_run_ids=kwargs.pop('allowed_run_ids', [self.run.pk]), **kwargs)

    def test_get_is_read_only_and_retry_preserves_exact_resolution(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'name="worker_choice"')
        self.assertIn('no-store', response['Cache-Control'])
        token = self.token()
        self.assertFalse(IdentityEvaluation.objects.exists())
        self.assertFalse(DocumentRegionAssociation.objects.exists())
        first = self.confirm(token)
        second = self.confirm(token)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(IdentityResolution.objects.count(), 1)
        self.assertEqual(DocumentRegionAssociation.objects.count(), 1)
        self.assertEqual(first.worker_version, self.worker.version)
        self.assertFalse(FieldDecision.objects.exists())
        self.assertFalse(WorkerIdentityRevision.objects.exists())

    def test_worker_edit_and_identity_revision_reject_old_choices(self):
        token = self.token()
        Worker.objects.filter(pk=self.worker.pk).update(version=2)
        with self.assertRaises(StaleWrite): self.confirm(token)
        token = self.token()
        WorkerIdentityRevision.objects.create(organization=self.org, worker=self.worker,
            revision_number=1, confirmed_fields={'given_name': 'ALFA'}, confirmed_by=self.user)
        with self.assertRaises(StaleWrite): self.confirm(token)
        self.assertFalse(IdentityResolution.objects.exists())
        self.assertFalse(IdentityEvaluation.objects.exists())

    def test_superseded_source_rejects_old_choice(self):
        token = self.token()
        supersede(self.user, self.org, self.doc.pk, 'synthetic.png', 'image/png',
            fixtures.png(fixtures.card(fixtures.ZP)), processor=fixtures.processor(fixtures.ZP))
        with self.assertRaises(StaleWrite): self.confirm(token)
        self.assertFalse(DocumentRegionAssociation.objects.exists())

    def test_tamper_actor_scope_and_disabled_operator_fail_closed(self):
        token = self.token()
        with self.assertRaises(StaleWrite): self.confirm(token + 'x')
        with self.assertRaises(StaleWrite): self.confirm(token, allowed_run_ids=[])
        other_actor = get_user_model().objects.create_user('synthetic-second-reviewer')
        Membership.objects.create(organization=self.org, user=other_actor, role='operator')
        fixtures.Authenticator.objects.create(user=other_actor, type=fixtures.Authenticator.Type.TOTP, data={})
        with self.assertRaises(StaleWrite):
            confirm_association(other_actor, self.org, token=token, allowed_run_ids=[self.run.pk])
        with self.assertRaises(Forbidden):
            confirm_association(self.user, self.other, token=token, allowed_run_ids=[self.run.pk])
        self.user.is_active = False
        with self.assertRaises(Forbidden): self.confirm(token)
        self.user.is_active = True
        with override_settings(M2_SYNTHETIC_ONLY=False), self.assertRaises(Forbidden): self.confirm(token)
        self.assertFalse(IdentityResolution.objects.exists())

    def test_operator_without_upload_permission_can_review(self):
        Membership.objects.filter(user=self.user, organization=self.org).update(role='operator')
        resolution = self.confirm(self.token())
        self.assertEqual(resolution.association.worker_id, self.worker.pk)

    def test_override_reason_required_and_failed_decision_rolls_back_evaluation(self):
        token = self.token()
        with self.assertRaises(ValueError): self.confirm(token, reason='')
        self.assertFalse(IdentityEvaluation.objects.exists())
        with patch('portal.release1a.identity.audit', side_effect=RuntimeError('synthetic failure')):
            with self.assertRaises(RuntimeError): self.confirm(token)
        self.assertFalse(IdentityEvaluation.objects.exists())
        self.assertFalse(DocumentRegionAssociation.objects.exists())
        self.assertFalse(IdentityResolution.objects.exists())

    def test_http_rejects_unsigned_duplicate_and_stale_choices(self):
        raw = {'action':'associate', 'worker_id':self.worker.pk,
               'run_id':self.run.pk, 'region_id':self.region}
        self.assertEqual(self.client.post(self.url, raw).status_code, 409)
        token = self.token()
        self.assertEqual(self.client.post(self.url, {'action':'associate',
            'worker_choice':[token,token]}).status_code, 409)
        Worker.objects.filter(pk=self.worker.pk).update(version=2)
        self.assertEqual(self.client.post(self.url, {'action':'associate',
            'worker_choice':token, 'reason':'Synthetic review'}).status_code, 409)
        self.assertEqual(self.client.post(self.url, {'action':'associate',
            'worker_choice':self.token(), 'reason':'Synthetic review'}).status_code, 302)

    def test_token_for_other_document_cannot_be_posted_here(self):
        _, _, _, other_run = fixtures.intake(self.user, self.org, None, 'synthetic-other.png',
            'image/png', fixtures.png(fixtures.card(fixtures.ZP)), processor=fixtures.processor(fixtures.ZP))
        contexts = association_review_context(self.user, self.org, [other_run.pk])
        token = next(iter(contexts.values()))['worker_options'][0]['token']
        response = self.client.post(self.url, {'action':'associate',
            'worker_choice':token, 'reason':'Synthetic review'})
        self.assertEqual(response.status_code, 409)
        self.assertFalse(DocumentRegionAssociation.objects.exists())

    def test_failed_batch_member_does_not_block_successful_region_review(self):
        session = fixtures.IntakeSession.objects.create(organization=self.org,
            purpose=fixtures.IntakeSession.Purpose.A1)
        session.ocr_runs.add(self.run)
        class Broken:
            def process(self, *args, **kwargs):
                raise RuntimeError('Synthetic OCR failure')
        _, _, _, failed_run = fixtures.intake(self.user, self.org, None,
            'synthetic-failed.png', 'image/png', fixtures.png(fixtures.card(fixtures.ZP)),
            session, processor=Broken())
        self.assertEqual(failed_run.state, 'failed')
        response = self.client.get(self.url)
        self.assertContains(response, 'name="worker_choice"')
        region = next(item for item in response.context['regions']
                      if item['ocr_run_id'] == self.run.pk and item['document_id'] == self.region)
        token = next(option['token'] for option in region['worker_options']
                     if option['worker'].pk == self.worker.pk)
        response = self.client.post(self.url, {'action':'associate',
            'worker_choice':token, 'reason':'Synthetic successful source reviewed'})
        self.assertEqual(response.status_code, 302)
        association = DocumentRegionAssociation.objects.get()
        self.assertEqual(association.ocr_run_id, self.run.pk)
        self.assertEqual(association.region_id, self.region)
        self.assertEqual(IdentityResolution.objects.count(), 1)
        self.assertFalse(FieldDecision.objects.exists())

    def test_derivative_source_hash_mismatch_rejected(self):
        token = self.token()
        payload = read_result(self.user, self.org, self.run.pk)
        payload['source_hash'] = '0' * 64
        with patch('portal.release1a.document_intake.read_result', return_value=payload):
            with self.assertRaises((StaleWrite, ValueError)): self.confirm(token)
        self.assertFalse(IdentityResolution.objects.exists())


@skipUnless(connection.vendor == 'postgresql', 'Disposable PostgreSQL required')
class IdentityReviewPostgresTests(TransactionTestCase):
    setUp = IdentityReviewTests.setUp
    ingest = fixtures.IntakeTests.ingest
    token = IdentityReviewTests.token

    def test_concurrent_different_worker_choices_cannot_both_associate(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.db import close_old_connections
        alternate = Worker.objects.create(organization=self.org, given_name='BETA',
            family_name='SYNTHETIC', birth_date='1988-01-02', activity_profile='employee')
        tokens = [self.token(), self.token(alternate)]
        barrier = Barrier(2, timeout=10)
        def submit(token):
            close_old_connections()
            try:
                user = get_user_model().objects.get(pk=self.user.pk)
                org = Organization.objects.get(pk=self.org.pk)
                with connection.cursor() as cursor:
                    cursor.execute("SET statement_timeout = '15s'")
                    cursor.execute("SET lock_timeout = '10s'")
                barrier.wait()
                try:
                    confirm_association(user, org, token=token, reason='Synthetic conflict review',
                                        allowed_run_ids=[self.run.pk])
                    return 'confirmed'
                except (ValueError, StaleWrite):
                    return 'rejected'
            finally:
                connection.close()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(submit, token) for token in tokens]
            results = [future.result(timeout=30) for future in futures]
        self.assertCountEqual(results, ['confirmed', 'rejected'])
        self.assertEqual(IdentityResolution.objects.count(), 1)
        self.assertEqual(DocumentRegionAssociation.objects.count(), 1)
        self.assertFalse(FieldDecision.objects.exists())
