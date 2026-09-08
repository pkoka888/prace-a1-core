import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "portal.settings")
import django
django.setup()


from datetime import date
import pytest
from django.contrib.auth import get_user_model
from django.test import TransactionTestCase, override_settings
import tempfile
from tests.test_document_core.helpers import OP, card, png
from allauth.mfa.models import Authenticator
from portal.release1a.models import AuditEvent, Membership, Organization, FieldProposal
from portal.release1a.services import Forbidden, create_assignment, create_worker, prepare_a1, upload_document

class Release1AVerticalTests(TransactionTestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        config = override_settings(DOCUMENT_STORAGE_ROOT=temporary.name)
        config.enable(); self.addCleanup(config.disable)
        self.alpha = Organization.objects.create(key="synthetic-alpha", label="Synthetic Alpha")
        self.beta = Organization.objects.create(key="synthetic-beta", label="Synthetic Beta")
        self.user = get_user_model().objects.create_user("synthetic-admin", password="synthetic-only")
        self.membership = Membership.objects.create(user=self.user, organization=self.alpha, role="jan_planner")
        Authenticator.objects.create(user=self.user, type=Authenticator.Type.TOTP, data={})

    def test_j1_to_j4_coherent_path_and_non_content_audit(self):
        worker = create_worker(self.user, self.alpha, given_name="Syntetický", family_name="Pracovník", birth_date=date(1990, 1, 1), activity_profile="employee")
        document = upload_document(self.user, self.alpha, worker, "fixture.png", "image/png", png(card(OP)))
        assert FieldProposal.objects.get(document=document, field_name="birth_date").proposed_value == "1990-03-15"
        _, overlap = create_assignment(self.user, self.alpha, worker, start=date(2026, 8, 1), end=date(2026, 8, 15), workplace_label="Syntetické pracoviště", activity_label="Test")
        assert not overlap
        case = prepare_a1(self.user, self.alpha, worker)
        assert case.readiness == "ready" and not case.prepared_artifact_hash and case.external_status == "not_submitted"
        assert list(AuditEvent.objects.values_list("event_type", flat=True)) == ["worker.created", "document.uploaded", "ocr.completed", "assignment.created", "a1.prepared"]
        assert all("Syntetický" not in event.object_ref for event in AuditEvent.objects.all())

    def test_mandatory_mfa_tenant_denial_overlap_and_a1_ambiguity(self):
        Authenticator.objects.filter(user=self.user).delete()
        with pytest.raises(Forbidden): create_worker(self.user, self.alpha, given_name="A", family_name="B", birth_date=date(1990,1,1), activity_profile="employee")
        Authenticator.objects.create(user=self.user, type=Authenticator.Type.TOTP, data={})
        worker = create_worker(self.user, self.alpha, given_name="A", family_name="B", birth_date=date(1990,1,1), activity_profile="employee")
        with pytest.raises(Forbidden): upload_document(self.user, self.beta, worker, "x.pdf", "application/pdf", b"%PDF-1.4")
        create_assignment(self.user, self.alpha, worker, start=date(2026,8,1), end=date(2026,8,20), workplace_label="A", activity_label="A")
        _, overlap = create_assignment(self.user, self.alpha, worker, start=date(2026,8,10), end=date(2026,8,30), workplace_label="B", activity_label="B")
        assert overlap and prepare_a1(self.user, self.alpha, worker).readiness == "blocked"
