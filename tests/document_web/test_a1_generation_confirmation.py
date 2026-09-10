"""Synthetic, generation-bound human visual decisions; identity facts remain untouched."""
import json
from unittest import skipUnless
from unittest.mock import patch
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase, Client, override_settings
from tests.test_j4_minimum import _mfa_login
from . import test_a1_generation_access as access_tests
from . import test_a1_exports as export_tests
from portal.release1a.a1_drafts import prepare_application_draft
from portal.release1a.models import A1GenerationConfirmation, A1DraftGeneration, AuditEvent, Membership, WorkerIdentityRevision
from portal.release1a.a1_generation_confirmation import confirmation_context, confirm_generation
from portal.release1a.services import StaleWrite, Forbidden


class GenerationConfirmationTests(TransactionTestCase):
    setUp = access_tests.GenerationAccessTests.setUp
    evaluation = export_tests.A1ExportTests.evaluation
    draft = export_tests.A1ExportTests.draft
    prepare = access_tests.GenerationAccessTests.prepare
    change_profile = access_tests.GenerationAccessTests.change_profile

    def tokens(self, generation):
        return dict(generation_id=generation.pk, expected_source_hash=generation.reservation.case.source_hash,
            expected_fingerprint=generation.fingerprint,
            expected_receipt_sha256=generation.artifact_reference['receipt_sha256'],
            expected_pdf_sha256=generation.prepared_artifact_hash)

    def confirm(self, generation, **overrides):
        values = dict(self.tokens(generation), pages=[1, 2, 3])
        values.update(overrides)
        return confirm_generation(self.user, self.org, self.case.pk, **values)

    def test_atomic_idempotent_confirmation_does_not_verify_identity_or_issue(self):
        generation = self.prepare()
        first = self.confirm(generation)
        again = self.confirm(generation)
        self.assertEqual(first.pk, again.pk)
        self.assertEqual(first.confirmed_at, again.confirmed_at)
        self.assertEqual(first.actor_id, self.user.pk)
        self.assertEqual(first.fingerprint, generation.fingerprint)
        self.assertEqual(first.receipt_sha256, generation.artifact_reference['receipt_sha256'])
        self.assertEqual(A1GenerationConfirmation.objects.count(), 1)
        self.assertEqual(AuditEvent.objects.filter(event_type='a1.generation_visual_confirmed').count(), 1)
        self.case.refresh_from_db()
        self.assertFalse(self.case.visual_confirmed)
        self.assertEqual(self.case.external_status, 'not_submitted')
        self.assertEqual(self.case.readiness, 'blocked')
        self.assertFalse(WorkerIdentityRevision.objects.exists())
        first.source_hash = '0' * 64
        with self.assertRaises(ValueError):
            first.save()

    def test_changed_dependencies_reject_old_confirmation_and_do_not_inherit(self):
        first = self.prepare()
        self.confirm(first)
        self.change_profile()
        with self.assertRaises(StaleWrite):
            self.confirm(first)
        second = self.prepare()
        self.assertFalse(A1GenerationConfirmation.objects.filter(generation=second).exists())
        with self.assertRaises(StaleWrite):
            self.confirm(second, expected_fingerprint=first.fingerprint)
        self.assertEqual(A1GenerationConfirmation.objects.count(), 1)
        self.confirm(second)
        self.assertEqual(A1GenerationConfirmation.objects.count(), 2)

    def test_each_expected_token_and_page_review_is_required(self):
        generation = self.prepare()
        for field in ('expected_source_hash','expected_fingerprint','expected_receipt_sha256','expected_pdf_sha256'):
            with self.subTest(field=field), self.assertRaises(StaleWrite):
                self.confirm(generation, **{field:'0' * 64})
        for pages in ([], [1,2], [True,2,3], [1,2,3,3]):
            with self.subTest(pages=pages), self.assertRaises(ValueError):
                self.confirm(generation, pages=pages)
        self.assertFalse(A1GenerationConfirmation.objects.exists())

    def test_audit_failure_rolls_back_and_source_change_denies(self):
        generation = self.prepare()
        with patch('portal.release1a.a1_generation_confirmation.audit', side_effect=RuntimeError('Synthetic audit failure')):
            with self.assertRaises(RuntimeError):
                self.confirm(generation)
        self.assertFalse(A1GenerationConfirmation.objects.exists())
        from portal.release1a.a1_exports import update_assignment_facts
        update_assignment_facts(self.user, self.org, self.assignment.pk, {}, expected_version=2)
        with self.assertRaises(StaleWrite):
            self.confirm(generation)

    def test_bo_get_post_and_csrf(self):
        generation = self.prepare()
        url = self.url + f'confirm/?generation={generation.pk}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('no-store', response['Cache-Control'])
        for page in (1,2,3):
            self.assertContains(response, f'preview/{page}/?generation={generation.pk}')
        self.assertContains(response, 'expected_receipt_sha256')
        self.assertFalse(A1GenerationConfirmation.objects.exists())
        payload = dict(self.tokens(generation), check_1='on', check_2='on', check_3='on')
        guarded = Client(enforce_csrf_checks=True)
        _mfa_login(guarded, self.user)
        self.assertEqual(guarded.post(url, payload).status_code, 403)
        self.assertEqual(self.client.post(url, payload).status_code, 302)
        self.assertEqual(A1GenerationConfirmation.objects.count(), 1)
        self.assertEqual(self.client.post(url, payload).status_code, 302)
        self.assertContains(self.client.get(self.url), 'Vzhled verze')

    def test_authorization_and_tampered_package(self):
        generation = self.prepare()
        with self.assertRaises(Forbidden):
            confirm_generation(self.user, self.other, self.case.pk, **self.tokens(generation), pages=[1,2,3])
        with override_settings(M2_SYNTHETIC_ONLY=False), self.assertRaises(Forbidden):
            self.confirm(generation)
        Membership.objects.filter(user=self.user).update(role='privacy_admin')
        self.assertEqual(self.client.get(self.url+'confirm/').status_code, 403)
        Membership.objects.filter(user=self.user).update(role='organization_admin')
        (self.storage/'j4'/generation.package_key.hex/'artifact.pdf').write_bytes(b'%PDF-synthetic-corruption')
        self.assertEqual(self.client.post(self.url+'confirm/', dict(self.tokens(generation), check_1='on',check_2='on',check_3='on')).status_code, 409)
        self.assertFalse(A1GenerationConfirmation.objects.exists())


@skipUnless(connection.vendor == 'postgresql', 'Disposable PostgreSQL required')
class GenerationConfirmationPostgresTests(TransactionTestCase):
    setUp = access_tests.GenerationAccessTests.setUp
    evaluation = export_tests.A1ExportTests.evaluation
    draft = export_tests.A1ExportTests.draft
    prepare = access_tests.GenerationAccessTests.prepare
    tokens = GenerationConfirmationTests.tokens
    confirm = GenerationConfirmationTests.confirm
    # Races use independent connections; history uses actual migration states.
    def test_concurrent_confirmation_preserves_one_receipt(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.contrib.auth import get_user_model
        from django.db import close_old_connections
        from portal.release1a.models import Organization
        generation = self.prepare()
        tokens = self.tokens(generation)
        barrier = Barrier(2, timeout=10)
        def confirm():
            close_old_connections()
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SET statement_timeout = '15s'")
                    cursor.execute("SET lock_timeout = '10s'")
                    cursor.execute('SELECT pg_backend_pid()')
                    backend = cursor.fetchone()[0]
                user = get_user_model().objects.get(pk=self.user.pk)
                org = Organization.objects.get(pk=self.org.pk)
                barrier.wait()
                receipt = confirm_generation(user, org, self.case.pk, **tokens, pages=[1,2,3])
                return backend, receipt.pk, receipt.confirmed_at
            finally:
                connection.close()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(confirm) for _ in range(2)]
            results=[future.result(timeout=30) for future in futures]
        self.assertNotEqual(results[0][0], results[1][0])
        self.assertEqual(results[0][1:], results[1][1:])
        self.assertEqual(A1GenerationConfirmation.objects.count(), 1)

    def test_historical_migration_preserves_generation_and_does_not_confirm(self):
        generation = self.prepare()
        before = [('release1a','0017_a1_draft_generation')]
        after = [('release1a','0018_a1_generation_confirmation')]
        executor = MigrationExecutor(connection)
        leaves = executor.loader.graph.leaf_nodes()
        try:
            executor.migrate(before)
            old = executor.loader.project_state(before).apps
            original = old.get_model('release1a','A1DraftGeneration').objects.values().get(pk=generation.pk)
            executor = MigrationExecutor(connection)
            executor.migrate(after)
            current = executor.loader.project_state(after).apps
            self.assertEqual(current.get_model('release1a','A1DraftGeneration').objects.values().get(pk=generation.pk), original)
            self.assertFalse(current.get_model('release1a','A1GenerationConfirmation').objects.exists())
            MigrationExecutor(connection).migrate(before)
            MigrationExecutor(connection).migrate(after)
            MigrationExecutor(connection).migrate(leaves)  # Runtime services require the current Worker schema.
            receipt = self.confirm(generation)
            with self.assertRaises(ValueError):
                MigrationExecutor(connection).migrate(before)
            self.assertTrue(A1GenerationConfirmation.objects.filter(pk=receipt.pk).exists())
        finally:
            MigrationExecutor(connection).migrate(leaves)
