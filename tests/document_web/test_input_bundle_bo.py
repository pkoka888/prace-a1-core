"""Synthetic BO publication and downloads pinned to exact compatibility inputs."""
import io
import json
import zipfile
from unittest.mock import patch
from django.test import Client, TransactionTestCase, override_settings
from tests.test_j4_minimum import _mfa_login
from . import test_a1_drafts as fixtures
from portal.release1a.a1_exports import publish_input_cohort
from portal.release1a.models import AuditEvent, Membership, Worker


class InputBundleBOTests(TransactionTestCase):
    evaluation = fixtures.A1DraftTests.evaluation
    draft = fixtures.A1DraftTests.draft

    def setUp(self):
        fixtures.setup_draft(self)
        self.user.set_password('test-m2')
        self.user.save()
        _mfa_login(self.client, self.user)
        self.url = f'/a1/{self.case.pk}/inputs/'

    def publish(self):
        return publish_input_cohort(self.user, self.org,
            [{'case_id': self.case.pk, 'expected_source_hash': self.case.source_hash}])

    def download_url(self, bundle):
        return self.url + bundle['manifest_sha256'] + '/download/'

    def test_page_is_read_only_publication_retry_and_exact_zip(self):
        self.assertContains(self.client.get(self.url), self.case.source_hash)
        self.assertFalse((self.storage/'a1-input').exists())
        self.assertFalse(AuditEvent.objects.filter(event_type='a1.input_exported').exists())
        response = self.client.post(self.url, {'expected_source_hash': self.case.source_hash})
        self.assertEqual(response.status_code, 200)
        bundle = self.publish()
        self.assertContains(response, self.download_url(bundle))
        before = AuditEvent.objects.filter(event_type='a1.input_exported').count()
        response = self.client.get(self.download_url(bundle))
        self.assertEqual(response.status_code, 200)
        self.assertIn('no-store', response['Cache-Control'])
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(response['Content-Type'], 'application/zip')
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            for name in archive.namelist():
                self.assertEqual(archive.read(name), (self.storage/bundle['relative_path']/name).read_bytes())
                self.assertEqual(archive.getinfo(name).external_attr >> 16, 0o100600)
        self.assertEqual(self.client.get(self.download_url(bundle)).content, response.content)
        self.assertEqual(AuditEvent.objects.filter(event_type='a1.input_exported').count(), before)
        self.case.refresh_from_db()
        self.assertFalse(self.case.visual_confirmed)
        self.assertEqual(self.case.external_status, 'not_submitted')
        self.assertFalse((self.storage/'j4').exists())

    def test_missing_pin_csrf_get_and_unknown_bundle_never_publish(self):
        self.assertEqual(self.client.post(self.url, {}).status_code, 400)
        self.assertEqual(self.client.post(self.url, {'expected_source_hash': ['a'*64, 'b'*64]}).status_code, 400)
        csrf = Client(enforce_csrf_checks=True)
        _mfa_login(csrf, self.user)
        self.assertEqual(csrf.post(self.url, {'expected_source_hash': self.case.source_hash}).status_code, 403)
        self.assertEqual(self.client.get(self.url + 'a'*64 + '/download/').status_code, 404)
        self.assertEqual(self.client.get(self.url + 'bad/download/').status_code, 409)
        self.assertFalse((self.storage/'a1-input').exists())

    def test_source_and_profile_changes_reject_pinned_download(self):
        first = self.publish()
        profile = self.profiles/'synthetic.json'
        original = profile.read_bytes()
        data = json.loads(original); data['version'] = 'new-synthetic'
        profile.write_text(json.dumps(data))
        self.assertEqual(self.client.get(self.download_url(first)).status_code, 409)
        second = self.publish()
        self.assertNotEqual(first, second)
        self.assertEqual(self.client.get(self.download_url(second)).status_code, 200)
        profile.write_bytes(original)
        self.assertEqual(self.client.get(self.download_url(first)).status_code, 200)
        Worker.objects.filter(pk=self.case.worker_id).update(version=99)
        self.assertEqual(self.client.get(self.download_url(first)).status_code, 409)
        self.assertEqual(self.client.post(self.url, {'expected_source_hash': self.case.source_hash}).status_code, 409)

    def test_denials_tamper_and_uncommitted_publication(self):
        bundle = self.publish()
        with override_settings(M2_SYNTHETIC_ONLY=False):
            self.assertEqual(self.client.get(self.url).status_code, 403)
            self.assertEqual(self.client.get(self.download_url(bundle)).status_code, 403)
        Membership.objects.filter(user=self.user).update(role='privacy_admin')
        for method, url in ((self.client.get, self.url), (self.client.post, self.url),
                            (self.client.get, self.download_url(bundle))):
            self.assertEqual(method(url).status_code, 403)
        Membership.objects.filter(user=self.user).update(role='organization_admin', organization=self.other)
        self.assertEqual(self.client.get(self.download_url(bundle)).status_code, 404)
        Membership.objects.filter(user=self.user).update(organization=self.org)
        (self.storage/bundle['relative_path']/'review.csv').write_bytes(b'tampered')
        self.assertEqual(self.client.get(self.download_url(bundle)).status_code, 409)
        AuditEvent.objects.filter(event_type='a1.input_bundle_published').delete()
        with patch('portal.release1a.input_bundle_access.read_input_artifact') as reader:
            self.assertEqual(self.client.get(self.download_url(bundle)).status_code, 404)
            reader.assert_not_called()
        self.assertTrue(AuditEvent.objects.filter(event_type='a1.input_bundle_read', outcome='denied').exists())

    def test_cohort_download_checks_other_sources_and_case_scope(self):
        from portal.release1a.a1_exports import prepare_input_case
        from portal.release1a.models import Assignment
        second_worker = Worker.objects.create(organization=self.org, given_name='BETA',
            family_name='SYNTHETIC', birth_date='1980-01-01', activity_profile='self_employed')
        Assignment.objects.create(organization=self.org, worker=second_worker,
            start='2026-01-01', end='2026-12-31', workplace_label='Synthetic',
            a1_facts_json={'institution': {'profile_key': 'synthetic'}})
        second = prepare_input_case(self.user, self.org, second_worker.pk)
        single = self.publish()
        self.assertEqual(self.client.get(f'/a1/{second.pk}/inputs/' +
            single['manifest_sha256'] + '/download/').status_code, 409)
        bundle = publish_input_cohort(self.user, self.org, [
            {'case_id': c.pk, 'expected_source_hash': c.source_hash} for c in (self.case, second)])
        self.assertEqual(self.client.get(self.download_url(bundle)).status_code, 200)
        Worker.objects.filter(pk=second_worker.pk).update(version=99)
        self.assertEqual(self.client.get(self.download_url(bundle)).status_code, 409)
        self.assertEqual(self.client.get(self.download_url(single)).status_code, 200)
