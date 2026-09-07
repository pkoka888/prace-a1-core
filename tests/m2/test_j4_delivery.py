"""Synthetic protected artifact journey; no final promotion."""
from django.test import TestCase

from portal.release1a.models import AuditEvent, Organization, Worker
from tests.test_j4_minimum import _mfa_login
from tests.test_j4_service import J4ServiceTests


class J4DeliveryTests(TestCase):
    def setUp(self):
        J4ServiceTests.setUp(self)
        self.user.set_password('test-m2');self.user.save()
        _mfa_login(self.client,self.user)

    def test_pdf_preview_staleness_and_tenant_denial(self):
        case=J4ServiceTests.attach(self)
        detail=self.client.get(f'/a1/{case.pk}/')
        self.assertContains(detail, f'/a1/{case.pk}/artifact/')
        response=self.client.get(f'/a1/{case.pk}/artifact/')
        self.assertEqual(response.status_code,200)
        self.assertTrue(response.content.startswith(b'%PDF'))
        self.assertIn('no-store',response['Cache-Control'])
        for page in (1,2,3):
            response=self.client.get(f'/a1/{case.pk}/preview/{page}/')
            self.assertEqual(response.status_code,200)
            self.assertTrue(response.content.startswith(b'\x89PNG'))
        self.assertEqual(self.client.get(f'/a1/{case.pk}/preview/4/').status_code,404)
        Worker.objects.filter(pk=self.worker.pk).update(family_name='CHANGED_SYNTHETIC')
        self.assertEqual(self.client.get(f'/a1/{case.pk}/artifact/').status_code,409)
        self.assertTrue(AuditEvent.objects.filter(event_type='a1.artifact_read',outcome='denied').exists())
        other=Organization.objects.create(key='foreign-j4',label='Foreign synthetic')
        self.membership.organization=other;self.membership.save()
        self.assertEqual(self.client.get(f'/a1/{case.pk}/artifact/').status_code,404)
        self.client.logout()
        self.assertEqual(self.client.get(f'/a1/{case.pk}/artifact/').status_code,302)

    def test_absent_artifact_does_not_get_generated_on_get(self):
        self.assertEqual(self.client.get(f'/a1/{self.case.pk}/artifact/').status_code,404)
        self.case.refresh_from_db()
        self.assertFalse(self.case.artifact_reference)

    def test_changed_build_requires_new_case_and_preserves_old_bytes(self):
        from django.test import override_settings

        from portal.release1a.models import A1Case
        case=J4ServiceTests.attach(self)
        original=case.prepared_artifact_hash
        with override_settings(PRACE_RELEASE_MANIFEST={'app_build_id':'new-synthetic-build'}):
            self.assertEqual(self.client.get(f'/a1/{case.pk}/artifact/').status_code,409)
            response=self.client.post(f'/a1/{case.pk}/regenerate/')
            self.assertEqual(response.status_code,302)
        case.refresh_from_db()
        self.assertTrue(case.is_stale)
        self.assertEqual(case.prepared_artifact_hash,original)
        newest=A1Case.objects.filter(worker=self.worker).latest('pk')
        self.assertNotEqual(newest.pk,case.pk)
        self.assertFalse(newest.artifact_reference)
        self.assertFalse(newest.is_stale)


class J4ConfirmationEvidenceTests(TestCase):
    """Tests for J4 visual confirmation and evidence intake views."""

    def setUp(self):
        J4ServiceTests.setUp(self)
        self.user.set_password('test-m2')
        self.user.save()
        _mfa_login(self.client, self.user)

    def test_confirm_get_renders_form_with_case(self):
        """Confirmation GET returns 200 and includes case in context."""
        case = J4ServiceTests.attach(self)
        response = self.client.get(f'/a1/{case.pk}/confirm/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('case', response.context)
        self.assertEqual(response.context['case'].pk, case.pk)

    def test_confirm_post_with_checkboxes_succeeds(self):
        """Confirmation POST with all three checkboxes ticks the visual_confirmed field."""
        case = J4ServiceTests.attach(self)
        response = self.client.post(f'/a1/{case.pk}/confirm/', {
            'action': 'confirm',
            'check_1': 'on',
            'check_2': 'on',
            'check_3': 'on',
            'notes': 'Synthetic visual confirmation',
        })
        self.assertEqual(response.status_code, 302)
        case.refresh_from_db()
        self.assertTrue(case.visual_confirmed)
        self.assertIsNotNone(case.visual_confirmed_at)
        self.assertEqual(case.visual_confirmed_by, self.user)
        self.assertEqual(case.visual_confirmation_notes, 'Synthetic visual confirmation')
        self.assertTrue(
            AuditEvent.objects.filter(
                event_type='a1.visual_confirmed', outcome='success'
            ).exists()
        )

    def test_confirm_post_without_checkboxes_rejected(self):
        """Confirmation POST without all checkboxes returns 400."""
        case = J4ServiceTests.attach(self)
        response = self.client.post(f'/a1/{case.pk}/confirm/', {
            'action': 'confirm',
            'check_1': 'on',
            'check_2': 'on',
            # check_3 missing
        })
        self.assertEqual(response.status_code, 400)
        case.refresh_from_db()
        self.assertFalse(case.visual_confirmed)

    def test_reject_post_clears_confirmation(self):
        """Reject POST clears visual_confirmed and records rejection."""
        case = J4ServiceTests.attach(self)
        # First confirm
        self.client.post(f'/a1/{case.pk}/confirm/', {
            'action': 'confirm',
            'check_1': 'on',
            'check_2': 'on',
            'check_3': 'on',
        })
        case.refresh_from_db()
        self.assertTrue(case.visual_confirmed)
        # Then reject
        response = self.client.post(f'/a1/{case.pk}/confirm/', {
            'action': 'reject',
            'notes': 'Synthetic rejection',
        })
        self.assertEqual(response.status_code, 302)
        case.refresh_from_db()
        self.assertFalse(case.visual_confirmed)
        self.assertIn('REJECTED', case.visual_confirmation_notes)
        self.assertTrue(
            AuditEvent.objects.filter(
                event_type='a1.visual_rejected', outcome='rejected'
            ).exists()
        )

    def test_evidence_get_renders_form(self):
        """Evidence GET returns 200 and includes a form in context."""
        response = self.client.get(f'/a1/{self.case.pk}/evidence/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)
        self.assertIn('case', response.context)

    def test_evidence_post_note_only_succeeds(self):
        """Evidence POST with note only (no document) succeeds without upload capability."""
        response = self.client.post(f'/a1/{self.case.pk}/evidence/', {
            'evidence_type': 'supporting',
            'note': 'Synthetic evidence note',
        })
        self.assertEqual(response.status_code, 302)
        self.case.refresh_from_db()
        self.assertEqual(len(self.case.evidence_notes), 1)
        self.assertEqual(self.case.evidence_notes[0]['note'], 'Synthetic evidence note')
        self.assertTrue(
            AuditEvent.objects.filter(
                event_type='a1.evidence_added', outcome='success'
            ).exists()
        )

    def test_confirm_requires_document_confirm_capability(self):
        """User without active membership is denied confirmation access."""
        case = J4ServiceTests.attach(self)
        # Deactivate membership to remove all capabilities
        self.membership.active = False
        self.membership.save()
        response = self.client.get(f'/a1/{case.pk}/confirm/')
        self.assertIn(response.status_code, (403, 302))

    def test_tenant_isolation_confirm(self):
        """User cannot confirm a case in a different organization."""
        case = J4ServiceTests.attach(self)
        other_org = Organization.objects.create(key='other-j4', label='Other synthetic')
        self.membership.organization = other_org
        self.membership.save()
        response = self.client.get(f'/a1/{case.pk}/confirm/')
        self.assertEqual(response.status_code, 404)

    def test_tenant_isolation_evidence(self):
        """User cannot add evidence to a case in a different organization."""
        other_org = Organization.objects.create(key='other-j4-ev', label='Other synthetic ev')
        self.membership.organization = other_org
        self.membership.save()
        response = self.client.get(f'/a1/{self.case.pk}/evidence/')
        self.assertEqual(response.status_code, 404)
