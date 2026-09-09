"""Synthetic BO access to exact draft generations, with no implicit generation or approval."""
import json
from unittest.mock import patch
from django.test import TransactionTestCase, override_settings
from tests.test_j4_minimum import _mfa_login
from tests.test_a1_application_draft import synthetic_profile
from . import test_a1_drafts as fixtures
from . import test_a1_exports as exports
from portal.release1a.a1_drafts import prepare_application_draft, reserve_application_generation
from portal.release1a.a1_generation_access import read_generation
from portal.release1a.models import A1DraftGeneration, A1DraftReservation, AuditEvent, Membership
from portal.release1a.j4_artifacts import ArtifactError


class GenerationAccessTests(TransactionTestCase):
    evaluation = exports.A1ExportTests.evaluation
    draft = exports.A1ExportTests.draft

    def setUp(self):
        fixtures.setup_draft(self)
        self.user.set_password('test-m2')
        self.user.save()
        _mfa_login(self.client, self.user)
        self.url = f'/a1/{self.case.pk}/'

    def prepare(self):
        return prepare_application_draft(self.user, self.org, self.case.pk)

    def change_profile(self):
        profile = synthetic_profile()
        profile['institution']['house_number'] = '3'
        (self.profiles / 'synthetic.json').write_text(json.dumps(profile))

    def test_bo_pdf_and_all_previews_pin_generation_and_do_not_confirm(self):
        generation = self.prepare()
        detail = self.client.get(self.url)
        self.assertContains(detail, f'artifact/?generation={generation.pk}')
        self.assertNotContains(detail, 'id="a1-approval-form"')
        response = self.client.get(self.url + f'artifact/?generation={generation.pk}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, (self.storage/'j4'/generation.package_key.hex/'artifact.pdf').read_bytes())
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('no-store', response['Cache-Control'])
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
        for page in (1, 2, 3):
            response = self.client.get(self.url + f'preview/{page}/?generation={generation.pk}')
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.content.startswith(b'\x89PNG'))
        self.case.refresh_from_db()
        self.assertFalse(self.case.visual_confirmed)
        self.assertEqual(self.case.external_status, 'not_submitted')
        self.assertTrue(AuditEvent.objects.filter(event_type='a1.artifact_read', outcome='success').exists())

    def test_old_link_rejected_and_unpinned_access_selects_current_generation(self):
        first = self.prepare()
        self.change_profile()
        self.assertEqual(self.client.get(self.url + f'artifact/?generation={first.pk}').status_code, 409)
        self.assertEqual(A1DraftGeneration.objects.count(), 1)
        self.assertNotContains(self.client.get(self.url), 'Stáhnout PDF')
        second = self.prepare()
        response = self.client.get(self.url + 'artifact/')
        self.assertEqual(response.content, (self.storage/'j4'/second.package_key.hex/'artifact.pdf').read_bytes())
        self.assertContains(self.client.get(self.url), f'artifact/?generation={second.pk}')
        (self.profiles/'synthetic.json').write_text(json.dumps(synthetic_profile()))
        self.assertContains(self.client.get(self.url), f'artifact/?generation={first.pk}')
        self.assertEqual(A1DraftGeneration.objects.count(), 2)

    def test_unpublished_generation_get_never_renders_and_legacy_posts_block(self):
        reserve_application_generation(self.user, self.org, self.case.pk)
        self.assertNotContains(self.client.get(self.url), 'Stáhnout PDF')
        self.assertEqual(self.client.get(self.url + 'artifact/').status_code, 409)
        for suffix, payload in (('', {'decision':'approve','external_status':'issued'}),
                                ('regenerate/', {}), ('confirm/', {'action':'confirm','check_1':'on','check_2':'on','check_3':'on'})):
            self.assertEqual(self.client.post(self.url + suffix, payload).status_code, 409)
        self.assertEqual(A1DraftGeneration.objects.count(), 1)
        self.assertEqual(A1DraftReservation.objects.count(), 1)
        self.assertFalse((self.storage/'j4').exists())
        self.case.refresh_from_db()
        self.assertFalse(self.case.visual_confirmed)
        self.assertEqual(self.case.external_status, 'not_submitted')

    def test_tenant_role_activation_and_invalid_reference_denials(self):
        generation = self.prepare()
        self.assertEqual(self.client.get(self.url + 'artifact/?generation=bad').status_code, 400)
        self.assertEqual(self.client.get(self.url + 'artifact/?generation=0').status_code, 400)
        for query in ('generation=1&generation=2', 'generation=999999999999999999999999', 'generation=١'):
            self.assertEqual(self.client.get(self.url + 'artifact/?' + query).status_code, 400)
        self.assertEqual(self.client.get(self.url + 'artifact/?generation=99999999').status_code, 404)
        self.assertEqual(self.client.get(self.url + 'preview/4/').status_code, 404)
        with override_settings(M2_SYNTHETIC_ONLY=False):
            self.assertEqual(self.client.get(self.url + 'artifact/').status_code, 403)
        Membership.objects.filter(user=self.user).update(role='privacy_admin')
        self.assertEqual(self.client.get(self.url + 'artifact/').status_code, 403)
        Membership.objects.filter(user=self.user).update(role='organization_admin', organization=self.other)
        self.assertEqual(self.client.get(self.url + f'artifact/?generation={generation.pk}').status_code, 404)
        self.assertTrue(AuditEvent.objects.filter(event_type='a1.artifact_read', outcome='denied').exists())

    def test_source_changes_and_tampered_package_fail_closed(self):
        generation = self.prepare()
        package = self.storage/'j4'/generation.package_key.hex
        original = (package/'artifact.pdf').read_bytes()
        (package/'artifact.pdf').write_bytes(b'%PDF-tampered-synthetic')
        self.assertEqual(self.client.get(self.url + 'artifact/').status_code, 409)
        (package/'artifact.pdf').write_bytes(original)
        from portal.release1a.a1_exports import update_assignment_facts
        update_assignment_facts(self.user, self.org, self.assignment.pk, {}, expected_version=2)
        self.assertEqual(self.client.get(self.url + 'artifact/').status_code, 409)

    def test_exact_returned_bytes_checked_after_package_verification(self):
        generation = self.prepare()
        from portal.release1a import a1_generation_access as access
        original_verify = access.verify_artifact
        def changed(*args):
            result = original_verify(*args)
            (self.storage/'j4'/generation.package_key.hex/'artifact.pdf').write_bytes(b'%PDF-changed-after-check')
            return result
        with patch.object(access, 'verify_artifact', side_effect=changed):
            with self.assertRaises(ArtifactError):
                read_generation(self.user, self.org, self.case.pk, generation.pk)

    def test_returned_preview_geometry_is_bound_to_receipt(self):
        import pymupdf
        generation = self.prepare()
        from portal.release1a import a1_generation_access as access
        original_verify = access.verify_artifact
        def changed(*args):
            result = original_verify(*args)
            path = self.storage/'j4'/generation.package_key.hex/'page-1.png'
            pixels = pymupdf.Pixmap(str(path))
            swapped = pymupdf.Pixmap(pymupdf.csRGB, pixels.height, pixels.width, pixels.samples, False)
            path.write_bytes(swapped.tobytes('png'))
            return result
        with patch.object(access, 'verify_artifact', side_effect=changed):
            with self.assertRaises(ArtifactError):
                read_generation(self.user, self.org, self.case.pk, generation.pk, page=1)
