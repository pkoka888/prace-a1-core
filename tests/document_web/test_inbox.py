"""Behavioral synthetic inbox tests; isolated Django database and private temp files."""
from datetime import timedelta
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
from unittest.mock import patch
from uuid import uuid4

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "portal.settings_document_tests")
import django
django.setup()
from allauth.mfa.models import Authenticator
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TransactionTestCase, override_settings
from django.utils import timezone
from portal.release1a.inbox import process_inbox
from portal.release1a.document_intake import (intake, read_result, associate_region,
    evaluate_identity_proposals, supersede)
from portal.release1a.models import (Organization, Membership, Document, OcrRun, Worker,
    FieldProposal, FieldDecision, WorkerIdentityRevision, AuditEvent)
from portal.release1a.services import Forbidden, confirm_field_proposal
from src.document_core.pipeline import DocumentProcessor
from tests.test_document_core.helpers import OP, card, png, ScriptedEngine


def processor():
    return DocumentProcessor(lambda: ScriptedEngine([OP, OP]))


class InboxTests(TransactionTestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.storage = Path(temporary.name)
        self.root = self.storage / "inbox"
        self.root.mkdir(mode=0o700)
        self.org = Organization.objects.create(key="inbox-synthetic", label="Synthetic Inbox")
        self.other = Organization.objects.create(key="inbox-other", label="Synthetic Other")
        self.user = get_user_model().objects.create_user("inbox-operator")
        Membership.objects.create(user=self.user, organization=self.org, role="organization_admin")
        Authenticator.objects.create(user=self.user, type=Authenticator.Type.TOTP, data={})
        self.override = override_settings(DOCUMENT_STORAGE_ROOT=self.storage,
            DOCUMENT_INBOX_ROOTS={self.org.pk: self.root}, M2_SYNTHETIC_ONLY=True)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.content = png(card(OP))

    def write(self, path, content):
        path.write_bytes(content)
        path.chmod(0o600)

    def batch(self, contents=None, ready=True, org=None):
        path = self.root / uuid4().hex
        path.mkdir(mode=0o700)
        items = []
        for content in contents if contents is not None else [self.content]:
            name = uuid4().hex + ".png"
            self.write(path / name, content)
            items.append({"name": name, "sha256": hashlib.sha256(content).hexdigest()})
        if ready:
            self.write(path / "ready.json", json.dumps({"organization_id": (org or self.org).pk,
                "files": items}).encode())
        return path, items

    def run_inbox(self, proc=None):
        return process_inbox(self.user, self.org, processor=proc or processor())

    def test_retry_reuses_completed_proposals_and_never_confirms(self):
        self.batch()
        first = self.run_inbox()[0]
        count = FieldProposal.objects.count()
        second = self.run_inbox()[0]
        self.assertEqual(first["items"], second["items"])
        self.assertEqual(first["status"], "completed")
        self.assertEqual(first["identity_resolution"], "requires_review")
        self.assertEqual(Document.objects.count(), 1)
        self.assertEqual(OcrRun.objects.get().retry_count, 1)
        self.assertEqual(FieldProposal.objects.count(), count)
        self.assertGreater(count, 0)
        self.assertFalse(FieldDecision.objects.exists())
        self.assertFalse(WorkerIdentityRevision.objects.exists())
        self.assertIsNone(Document.objects.get().worker_id)
        receipt = self.storage / first["receipt_key"]
        self.assertEqual(receipt.stat().st_mode & 0o777, 0o600)
        self.assertEqual(json.loads(receipt.read_text())["items"], first["items"])

    def test_failed_ocr_resumes_existing_run(self):
        class Broken:
            def process(self, *args, **kwargs):
                raise RuntimeError("SENSITIVE_SYNTHETIC_FAILURE")
        self.batch()
        first = self.run_inbox(Broken())[0]
        self.assertEqual(first["items"][0]["status"], "failed")
        second = self.run_inbox()[0]
        self.assertEqual(second["items"][0]["status"], "completed")
        self.assertEqual(first["items"][0]["run_ref"], second["items"][0]["run_ref"])
        self.assertEqual(OcrRun.objects.get().retry_count, 2)
        self.assertNotIn("SENSITIVE", json.dumps(first))

    def test_incomplete_ignored_bad_file_does_not_stop_good(self):
        self.batch(ready=False)
        self.batch([b"SENSITIVE_INVALID_FILE", self.content])
        results = self.run_inbox()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], "partial")
        self.assertEqual([r["status"] for r in results[0]["items"]], ["rejected", "completed"])
        self.assertEqual(Document.objects.count(), 1)
        self.assertNotIn("SENSITIVE", json.dumps(results))
        self.assertNotIn("SENSITIVE", str(list(AuditEvent.objects.values())))

    def test_authorization_and_activation_precede_filesystem(self):
        with patch("portal.release1a.inbox._private_fd") as access:
            with self.assertRaises(Forbidden):
                process_inbox(self.user, self.other)
            with override_settings(M2_SYNTHETIC_ONLY=False):
                with self.assertRaises(Forbidden):
                    self.run_inbox()
            access.assert_not_called()

    def test_manifest_scope_and_shared_root_are_rejected(self):
        self.batch(org=self.other)
        self.assertEqual(self.run_inbox()[0]["status"], "rejected")
        with override_settings(DOCUMENT_INBOX_ROOTS={self.org.pk: self.root, self.other.pk: self.root}):
            with self.assertRaisesRegex(ValueError, "DISJOINT"):
                self.run_inbox()
        self.assertFalse(Document.objects.exists())

    def test_symlink_source_and_modified_hash_rejected(self):
        path, items = self.batch([self.content, self.content])
        source = path / items[0]["name"]
        source.unlink()
        source.symlink_to(path / items[1]["name"])
        self.write(path / items[1]["name"], b"modified")
        results = self.run_inbox()[0]
        self.assertEqual([r["status"] for r in results["items"]], ["rejected", "rejected"])
        self.assertFalse(Document.objects.exists())

    def test_traversal_manifest_and_root_escape_fail_closed(self):
        path, items = self.batch()
        items[0]["name"] = "../private.png"
        self.write(path / "ready.json", json.dumps({"organization_id": self.org.pk, "files": items}).encode())
        self.assertEqual(self.run_inbox()[0]["status"], "rejected")
        with override_settings(DOCUMENT_INBOX_ROOTS={self.org.pk: self.storage.parent}):
            with self.assertRaisesRegex(ValueError, "OUTSIDE_PRIVATE"):
                self.run_inbox()
        self.assertFalse(Document.objects.exists())

    def test_command_reports_partial_as_failure_without_source_details(self):
        self.batch([b"SENSITIVE_INVALID_FILE"])
        output = io.StringIO()
        with self.assertRaisesRegex(CommandError, "UNRESOLVED"):
            call_command("a1_process_inbox", organization_id=self.org.pk, actor_id=self.user.pk, stdout=output)
        self.assertEqual(json.loads(output.getvalue())[0]["status"], "partial")
        self.assertNotIn("SENSITIVE", output.getvalue())

    def test_same_root_concurrent_invocation_is_not_claimed_twice(self):
        self.batch()
        lock = os.open(self.root / ".process.lock", os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(ValueError, "INBOX_BUSY"):
                self.run_inbox()
        finally:
            os.close(lock)
        self.assertFalse(Document.objects.exists())
        self.assertEqual(self.run_inbox()[0]["status"], "completed")

    def test_expired_ocr_lease_is_reclaimed_without_new_document(self):
        self.batch()
        self.run_inbox()
        run = OcrRun.objects.get()
        # Simulate an interrupted attempt before persistence, using the existing lease contract.
        FieldProposal.objects.all().delete()
        run.document.documentclassification_set.all().delete()
        OcrRun.objects.filter(pk=run.pk).update(state="running", retry_count=1,
            lease_expires_at=timezone.now() - timedelta(seconds=1), output_key="", output_sha256="")
        self.assertEqual(self.run_inbox()[0]["status"], "completed")
        self.assertEqual(Document.objects.count(), 1)
        self.assertEqual(OcrRun.objects.get().retry_count, 2)

    def test_duplicate_with_worker_context_is_not_silently_reassociated(self):
        worker = Worker.objects.create(organization=self.org, given_name="SYNTHETIC",
            family_name="EXAMPLE", birth_date="1990-01-01", activity_profile="employee")
        document, _, _, _ = intake(self.user, self.org, worker, "synthetic.png", "image/png",
            self.content, processor=processor())
        self.batch()
        self.assertEqual(self.run_inbox()[0]["items"][0]["status"], "rejected")
        document.refresh_from_db()
        self.assertEqual(document.worker_id, worker.pk)
        self.assertEqual(Document.objects.count(), 1)
        self.assertFalse(FieldDecision.objects.exists())

    def test_private_modes_and_byte_limit_are_enforced(self):
        path, items = self.batch()
        (path / items[0]["name"]).chmod(0o644)
        self.assertEqual(self.run_inbox()[0]["items"][0]["status"], "rejected")
        (path / items[0]["name"]).chmod(0o600)
        with patch("portal.release1a.inbox.MAX_BYTES", 10):
            self.assertEqual(self.run_inbox()[0]["items"][0]["status"], "rejected")
        self.assertFalse(Document.objects.exists())

    def test_command_uses_explicitly_configured_operator_and_org(self):
        self.batch([b"SYNTHETIC_INVALID"])
        output = io.StringIO()
        with override_settings(DOCUMENT_INBOX_ORGANIZATION_ID=self.org.pk, DOCUMENT_INBOX_ACTOR_ID=self.user.pk):
            with self.assertRaisesRegex(CommandError, "UNRESOLVED"):
                call_command("a1_process_inbox", stdout=output)
        result = json.loads(output.getvalue())[0]
        self.assertEqual(result["organization_id"], self.org.pk)
        self.assertEqual(result["actor_ref"], f"user:{self.user.pk}")
        with override_settings(DOCUMENT_INBOX_ORGANIZATION_ID=self.org.pk, DOCUMENT_INBOX_ACTOR_ID=self.user.pk):
            with self.assertRaisesRegex(CommandError, "DENIED_OR_UNAVAILABLE"):
                call_command("a1_process_inbox", organization_id=self.other.pk, stdout=io.StringIO())

    def test_command_never_invents_operator_configuration(self):
        with override_settings(DOCUMENT_INBOX_ORGANIZATION_ID=None, DOCUMENT_INBOX_ACTOR_ID=None):
            with self.assertRaisesRegex(CommandError, "DENIED_OR_UNAVAILABLE"):
                call_command("a1_process_inbox", stdout=io.StringIO())
        with override_settings(DOCUMENT_INBOX_ORGANIZATION_ID=self.org.pk, DOCUMENT_INBOX_ACTOR_ID=True):
            with self.assertRaisesRegex(CommandError, "DENIED_OR_UNAVAILABLE"):
                call_command("a1_process_inbox", stdout=io.StringIO())


    def confirmed_identifier(self):
        worker = Worker.objects.create(organization=self.org, given_name="ALFA",
            family_name="TESTOVA", birth_date="1990-03-15", activity_profile="employee")
        _, _, _, run = intake(self.user, self.org, None, "synthetic.png", "image/png",
            self.content, processor=processor())
        region = read_result(self.user, self.org, run.pk)["result"]["documents"][0]
        associate_region(self.user, self.org, run.pk, region["document_id"], worker)
        confirm_field_proposal(self.user, self.org,
            FieldProposal.objects.get(ocr_run=run, field_name="document_number"))
        return worker, run

    def test_receipt_recomputes_matching_after_confirmation_without_mutating_facts(self):
        self.batch()
        first = self.run_inbox()[0]["identity_evaluation"]
        self.assertEqual(first["regions"][0]["status"], "unassigned")
        worker, run = self.confirmed_identifier()
        counts = (FieldDecision.objects.count(), WorkerIdentityRevision.objects.count())
        second = self.run_inbox()[0]["identity_evaluation"]
        self.assertEqual(second["regions"][0]["worker_id"], str(worker.pk))
        self.assertEqual(second["regions"][0]["status"], "proposed")
        self.assertNotEqual(first["evaluation_sha256"], second["evaluation_sha256"])
        self.assertEqual(second, self.run_inbox()[0]["identity_evaluation"])
        self.assertEqual(second["sources"][0]["output_sha256"], run.output_sha256)
        self.assertFalse(second["accepted"])
        self.assertEqual(counts, (FieldDecision.objects.count(), WorkerIdentityRevision.objects.count()))
        self.assertIsNone(Document.objects.get().worker_id)
        self.assertNotIn("TST000001", json.dumps(second))
        self.assertNotIn("TESTOVA", json.dumps(second))

    def test_revision_conflict_changes_evaluation_and_leaves_confirmed_value_intact(self):
        worker, run = self.confirmed_identifier()
        before = evaluate_identity_proposals(self.user, self.org, [run.pk])
        proposal = FieldProposal.objects.get(ocr_run=run, field_name="birth_date")
        confirm_field_proposal(self.user, self.org, proposal, corrected_value="1991-03-15")
        after = evaluate_identity_proposals(self.user, self.org, [run.pk])
        self.assertNotEqual(before["worker_snapshot_sha256"], after["worker_snapshot_sha256"])
        self.assertEqual(after["regions"][0]["status"], "ambiguous")
        self.assertIsNone(after["regions"][0]["worker_id"])
        self.assertEqual(after["regions"][0]["findings"], ["worker_identity_conflict"])
        self.assertEqual(WorkerIdentityRevision.objects.filter(worker=worker).latest("revision_number").confirmed_fields["birth_date"], "1991-03-15")

    def test_evaluation_rejects_foreign_stale_and_tampered_sources(self):
        _, run = self.confirmed_identifier()
        with self.assertRaises(Forbidden):
            evaluate_identity_proposals(self.user, self.other, [run.pk])
        Membership.objects.create(user=self.user, organization=self.other, role="organization_admin")
        with self.assertRaises(OcrRun.DoesNotExist):
            evaluate_identity_proposals(self.user, self.other, [run.pk])
        path = self.storage / run.output_key
        content = path.read_bytes()
        path.write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "HASH_MISMATCH"):
            evaluate_identity_proposals(self.user, self.org, [run.pk])
        path.write_bytes(content)
        supersede(self.user, self.org, run.document_id, "replacement.png", "image/png",
            png(card(OP + ["SYNTHETIC REPLACEMENT"])), processor=processor())
        with self.assertRaisesRegex(ValueError, "NOT_CURRENT"):
            evaluate_identity_proposals(self.user, self.org, [run.pk])

    def test_other_organization_confirmations_do_not_supply_candidates(self):
        self.confirmed_identifier()
        Membership.objects.create(user=self.user, organization=self.other, role="organization_admin")
        _, _, _, run = intake(self.user, self.other, None, "synthetic.png", "image/png",
            self.content, processor=processor())
        evaluation = evaluate_identity_proposals(self.user, self.other, [run.pk])
        self.assertEqual(evaluation["regions"][0]["candidates"], [])
        self.assertEqual(evaluation["worker_evidence"], [])


    def test_matching_failure_is_partial_and_retry_preserves_completed_ocr(self):
        self.batch()
        with patch("portal.release1a.inbox.persist_identity_evaluation", side_effect=ValueError("SENSITIVE")):
            result = self.run_inbox()[0]
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["items"][0]["status"], "completed")
        self.assertEqual(result["identity_evaluation"]["status"], "unavailable")
        self.assertNotIn("SENSITIVE", json.dumps(result))
        self.assertEqual(self.run_inbox()[0]["status"], "completed")
        self.assertEqual(OcrRun.objects.get().retry_count, 1)

    def test_cold_start_address_stays_pending_until_structured_review(self):
        """Recognizing a free-form address is not structured A1 address acceptance."""
        from portal.release1a.models import A1Case, A1DraftGeneration
        lines = OP + ['TRVALY POBYT: Testovaci 12, 12345 Testov']
        self.content = png(card(lines))
        path, items = self.batch()
        items[0]['activity_profile'] = 'self_employed'
        self.write(path/'ready.json', json.dumps({'organization_id':self.org.pk, 'files':items}).encode())
        result = self.run_inbox(DocumentProcessor(lambda: ScriptedEngine([lines, lines])))[0]
        self.assertEqual(result['status'], 'completed')
        self.assertTrue(FieldProposal.objects.filter(field_name='residence_address').exists())
        case = A1Case.objects.get(pk=result['drafts'][0]['a1_input']['case_ref'])
        for field in ('street', 'house_number', 'city', 'postal_code', 'country_code'):
            self.assertEqual(case.source_snapshot_json['row'][field], '')
        self.assertEqual(result['drafts'][0]['a1_draft']['status'], 'blocked')
        self.assertFalse(A1DraftGeneration.objects.exists())
        self.assertFalse(FieldDecision.objects.exists())
        self.assertFalse(WorkerIdentityRevision.objects.exists())

        from tests.test_j4_minimum import _mfa_login
        from portal.release1a.identity_review import association_review_context
        from portal.release1a.field_review import address_review_context
        from portal.release1a.a1_exports import prepare_input_case
        self.user.set_password('test-m2'); self.user.save(); _mfa_login(self.client,self.user)
        proposal = FieldProposal.objects.get(field_name='residence_address')
        url = f'/documents/{proposal.document_id}/'
        options = association_review_context(self.user,self.org,[proposal.ocr_run_id])[
            (proposal.ocr_run_id,proposal.document_region_id)]['worker_options']
        choice = next(o['token'] for o in options if o['worker'].pk == case.worker_id)
        self.assertEqual(self.client.post(url,{'action':'associate','worker_choice':choice,
            'reason':'Synthetic source checked'}).status_code,302)
        values = dict(street='Testovaci',house_number='12',city='Testov',postal_code='12345',country_code='CZ')
        token = address_review_context(self.user,self.org,proposal.pk)['token']
        self.assertEqual(self.client.post(url,{'action':'confirm_address','address_source':proposal.pk,
            'address_token':token,**{'address_'+k:v for k,v in values.items()}}).status_code,302)
        fresh = prepare_input_case(self.user,self.org,case.worker_id)
        for field,value in values.items(): self.assertEqual(fresh.source_snapshot_json['row'][field],value)
        case.refresh_from_db(); self.assertTrue(case.is_stale)
        self.assertFalse(A1DraftGeneration.objects.exists())

        # Continue through the actual BO forms, without seeding missing identity facts.
        from portal.release1a.models import Assignment
        from portal.release1a.assignment_facts import FIELDS
        from scripts.finalize_a1 import validate_application_draft_row, FinalizationError
        from tests.test_a1_application_draft import synthetic_profile
        self.assertEqual(self.client.post(f'/workers/{case.worker_id}/assignments/new/', {
            'workplace_label':'Synthetic workplace', 'activity_label':'Synthetic role',
            'start':'2026-09-01', 'end':'2026-12-31', 'state':'planned',
        }).status_code, 302)
        assignment = Assignment.objects.get(worker_id=case.worker_id)
        profile_root = self.storage/'profiles'; profile_root.mkdir(mode=0o700)
        self.write(profile_root/'synthetic.json', json.dumps(synthetic_profile()).encode())
        facts = {'version':assignment.version, 'status_profile':'self_employed_multi_state',
                 **{f'{group}__{field}':'' for group,fields in FIELDS.items() for field in fields}}
        facts.update({'employment__employer_id':'SYNTHETIC-123',
            'employment__employer_name':'Synthetic activity', 'employment__street':'Testovaci',
            'employment__house_number':'12', 'employment__city':'Testov',
            'employment__postal_code':'12345', 'employment__country_code':'CZ',
            'institution__resolved_ossz':'OSSZ Testov', 'institution__profile_key':'synthetic'})
        with override_settings(A1_DRAFT_PROFILE_ROOT=profile_root):
            self.assertEqual(self.client.post(
                f'/workers/{case.worker_id}/assignments/{assignment.pk}/a1-inputs/', facts).status_code,302)
        current = prepare_input_case(self.user,self.org,case.worker_id)
        row = current.source_snapshot_json['row']
        self.assertNotIn('assignment_missing',current.source_snapshot_json['blockers'])
        self.assertEqual((row['activity_name'],row['activity_address']),('','DE, CZ'))
        # This temporary candidate mirrors the canonical pre-allocation validation only.
        # No number, certificate evidence or PDF is persisted by this readiness check.
        with self.assertRaises(FinalizationError) as blocked:
            validate_application_draft_row(dict(row,document_id='N00000S001/2000/DE'),synthetic_profile())
        self.assertEqual(str(blocked.exception),
            'APPLICATION_DRAFT_MISSING: birth_place, nationality, sex, insurance_number')
        self.assertEqual(row['document_id'],'')
        self.assertEqual(row['identity_reviewed'],'NO')
        self.assertEqual(row['validated_by_user'],'0')
        self.assertFalse(A1DraftGeneration.objects.exists())
        counts = (Worker.objects.count(), OcrRun.objects.count(), FieldDecision.objects.count())
        again = self.run_inbox(DocumentProcessor(lambda: ScriptedEngine([])))[0]
        self.assertEqual(again['drafts'][0]['a1_draft']['status'],'blocked')
        self.assertEqual(counts,(Worker.objects.count(), OcrRun.objects.count(), FieldDecision.objects.count()))
        from portal.release1a.field_review import missing_identity_context
        context = missing_identity_context(self.user,self.org,proposal.pk)
        self.assertEqual(self.client.post(url,{
            'action':'confirm_missing_identity','identity_source':proposal.pk,
            'identity_token':context['token'],'identity_birth_place':'Synthetic town',
            'identity_nationality':'CZE','identity_sex':'F','identity_insurance_number':'INS000001',
        }).status_code,302)
        ready = prepare_input_case(self.user,self.org,case.worker_id)
        validate_application_draft_row(dict(ready.source_snapshot_json['row'],
            document_id='N00000S001/2000/DE'),synthetic_profile())
        self.assertEqual(ready.source_snapshot_json['row']['validated_by_user'],'0')
        self.assertEqual(ready.source_snapshot_json['row']['identity_reviewed'],'NO')
        self.assertFalse(A1DraftGeneration.objects.exists())
