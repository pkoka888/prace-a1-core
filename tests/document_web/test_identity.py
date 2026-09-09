"""Synthetic durable identity workflow; real records and persistent databases excluded."""
import json
from unittest.mock import patch
from django.test import TransactionTestCase, override_settings
from portal.release1a import identity
from portal.release1a.document_intake import intake, read_result, associate_region, supersede
from portal.release1a.models import (Worker, FieldProposal, FieldDecision, WorkerIdentityRevision,
    IdentityEvaluation, WorkerIdentityClaim, IdentityResolution, DocumentRegionAssociation, AuditEvent)
from portal.release1a.services import Forbidden, StaleWrite, confirm_field_proposal
from tests.test_document_core.helpers import OP, card, png, ScriptedEngine
from src.document_core.pipeline import DocumentProcessor
from . import test_inbox as inbox_tests


class IdentityTests(TransactionTestCase):
    setUp = inbox_tests.InboxTests.setUp
    write = inbox_tests.InboxTests.write
    batch = inbox_tests.InboxTests.batch
    run_inbox = inbox_tests.InboxTests.run_inbox
    confirmed_identifier = inbox_tests.InboxTests.confirmed_identifier

    def evaluation(self, content=None, lines=OP):
        _, _, _, run = intake(self.user, self.org, None, "synthetic.png", "image/png",
            content or self.content, processor=DocumentProcessor(lambda: ScriptedEngine([lines, lines])))
        evaluation = identity.persist_identity_evaluation(self.user, self.org, [run.pk])
        return evaluation, run, evaluation.evidence["regions"][0]["region_ref"]

    def draft(self, evaluation, run, region, profile="employee"):
        return identity.prepare_identity_draft(self.user, self.org, evaluation.pk, run.pk, region,
                                               activity_profile=profile)

    def worker(self):
        return Worker.objects.create(organization=self.org, given_name="ALFA", family_name="TESTOVA",
                                     birth_date="1990-03-15", activity_profile="employee")

    def test_durable_evaluation_and_draft_retry_create_one_effect_without_confirmation(self):
        evaluation, run, region = self.evaluation()
        self.assertEqual(evaluation.pk, identity.persist_identity_evaluation(self.user, self.org, [run.pk]).pk)
        first = self.draft(evaluation, run, region)
        self.assertEqual(first, self.draft(evaluation, run, region))
        self.assertEqual(first["status"], "draft")
        worker = Worker.objects.get()
        self.assertEqual((worker.given_name, worker.family_name, str(worker.birth_date)), ("ALFA", "TESTOVA", "1990-03-15"))
        self.assertEqual(worker.state, "draft")
        self.assertEqual(WorkerIdentityClaim.objects.count(), 1)
        self.assertEqual(IdentityEvaluation.objects.count(), 1)
        self.assertFalse(FieldDecision.objects.exists())
        self.assertFalse(WorkerIdentityRevision.objects.exists())
        self.assertFalse(DocumentRegionAssociation.objects.exists())
        self.assertNotIn("TST000001", json.dumps(evaluation.evidence))
        self.assertNotIn("TESTOVA", str(list(AuditEvent.objects.values())))
        copy, new_run, new_region = self.evaluation(png(card(OP + ["SYNTHETIC COPY"])))
        self.assertEqual(self.draft(copy, new_run, new_region)["worker_ref"], worker.pk)
        self.assertEqual(Worker.objects.count(), 1)

    def test_missing_profile_homonym_and_missing_identity_do_not_create_worker(self):
        evaluation, run, region = self.evaluation()
        with self.assertRaisesRegex(ValueError, "PROFILE_REQUIRED"):
            self.draft(evaluation, run, region, None)
        self.worker()
        self.assertEqual(self.draft(evaluation, run, region)["reason"], "POSSIBLE_EXISTING_WORKER")
        lines = [line for line in OP if not line.startswith("DATUM NAROZENI")]
        evaluation, run, region = self.evaluation(png(card(lines)), lines)
        self.assertEqual(self.draft(evaluation, run, region)["reason"], "IDENTITY_INCOMPLETE")
        self.assertEqual(Worker.objects.count(), 1)
        self.assertFalse(WorkerIdentityClaim.objects.exists())

    def test_same_identifier_conflicting_batch_creates_neither_worker(self):
        evaluation, run, region = self.evaluation()
        lines = [line.replace("ALFA", "BETA") for line in OP]
        _, second, other_region = self.evaluation(png(card(lines)), lines)
        together = identity.persist_identity_evaluation(self.user, self.org, [run.pk, second.pk])
        self.assertEqual(self.draft(together, run, region)["reason"], "IDENTITY_CONFLICT")
        self.assertEqual(self.draft(together, second, other_region)["reason"], "IDENTITY_CONFLICT")
        self.assertFalse(Worker.objects.exists())

    def test_failed_audit_rolls_back_draft_and_claim(self):
        evaluation, run, region = self.evaluation()
        with patch("portal.release1a.identity.audit", side_effect=RuntimeError("synthetic failure")):
            with self.assertRaises(RuntimeError):
                self.draft(evaluation, run, region)
        self.assertFalse(Worker.objects.exists())
        self.assertFalse(WorkerIdentityClaim.objects.exists())
        self.assertFalse(AuditEvent.objects.filter(event_type="worker.created").exists())

    def test_explicit_resolution_is_idempotent_and_retains_source_actor_revision(self):
        evaluation, run, region = self.evaluation()
        worker = self.worker()
        with self.assertRaisesRegex(ValueError, "REASON_REQUIRED"):
            identity.resolve_identity_evaluation(self.user, self.org, evaluation.pk, run.pk, region, worker.pk,
                expected_worker_version=1, expected_revision_id=None)
        resolution = identity.resolve_identity_evaluation(self.user, self.org, evaluation.pk, run.pk, region, worker.pk,
            expected_worker_version=1, expected_revision_id=None, reason="Reviewed synthetic source")
        repeated = identity.resolve_identity_evaluation(self.user, self.org, evaluation.pk, run.pk, region, worker.pk,
            expected_worker_version=1, expected_revision_id=None, reason="Reviewed synthetic source")
        self.assertEqual(resolution.pk, repeated.pk)
        self.assertEqual(resolution.association.decided_by_id, self.user.pk)
        self.assertEqual(resolution.association.ocr_run_id, run.pk)
        self.assertEqual(resolution.evaluation_id, evaluation.pk)
        self.assertFalse(FieldDecision.objects.exists())
        self.assertFalse(WorkerIdentityRevision.objects.exists())

    def test_worker_version_and_confirmation_revision_change_reject_decision(self):
        evaluation, run, region = self.evaluation()
        worker = self.worker()
        Worker.objects.filter(pk=worker.pk).update(version=2)
        with self.assertRaises(StaleWrite):
            identity.resolve_identity_evaluation(self.user, self.org, evaluation.pk, run.pk, region, worker.pk,
                expected_worker_version=1, expected_revision_id=None, reason="Synthetic review")
        _, other_run, other_region = self.evaluation(png(card(OP + ["SYNTHETIC COPY"])))
        associate_region(self.user, self.org, other_run.pk, other_region, worker)
        confirm_field_proposal(self.user, self.org, FieldProposal.objects.get(ocr_run=other_run, field_name="birth_date"))
        with self.assertRaises(StaleWrite):
            identity.resolve_identity_evaluation(self.user, self.org, evaluation.pk, run.pk, region, worker.pk,
                expected_worker_version=2, expected_revision_id=None, reason="Synthetic review")
        self.assertFalse(IdentityResolution.objects.exists())

    def test_new_confirmed_identifier_and_superseded_source_invalidate_evaluation(self):
        evaluation, run, region = self.evaluation()
        self.confirmed_identifier()
        with self.assertRaises(StaleWrite):
            self.draft(evaluation, run, region)
        current = identity.persist_identity_evaluation(self.user, self.org, [run.pk])
        self.assertNotEqual(current.pk, evaluation.pk)
        supersede(self.user, self.org, run.document_id, "replacement.png", "image/png",
                  png(card(OP + ["REPLACEMENT"])), processor=inbox_tests.processor())
        with self.assertRaisesRegex(ValueError, "NOT_CURRENT"):
            self.draft(current, run, region)

    def test_authorization_precedes_database_and_cross_org_ids_are_unavailable(self):
        evaluation, run, region = self.evaluation()
        with override_settings(M2_SYNTHETIC_ONLY=False), patch("portal.release1a.identity._lock_organization") as lock:
            with self.assertRaises(Forbidden):
                self.draft(evaluation, run, region)
            lock.assert_not_called()
        with self.assertRaises(Forbidden):
            identity.prepare_identity_draft(self.user, self.other, evaluation.pk, run.pk, region, activity_profile="employee")
        self.user.is_active = False
        with self.assertRaises(Forbidden):
            self.draft(evaluation, run, region)
        self.assertFalse(Worker.objects.exists())

    def test_inbox_persists_evaluation_and_uses_explicit_profile(self):
        path, items = self.batch()
        without_profile = self.run_inbox()[0]
        self.assertEqual(without_profile["drafts"][0]["reason"], "ACTIVITY_PROFILE_REQUIRED")
        items[0]["activity_profile"] = "self_employed"
        self.write(path / "ready.json", json.dumps({"organization_id": self.org.pk, "files": items}).encode())
        result = self.run_inbox()[0]
        self.assertEqual(result["drafts"][0]["status"], "draft")
        self.assertEqual(Worker.objects.get().activity_profile, "self_employed")
        self.assertEqual(result["identity_evaluation"]["evaluation_ref"], IdentityEvaluation.objects.get().pk)
        self.assertEqual(result["drafts"], self.run_inbox()[0]["drafts"])
        self.assertEqual(Worker.objects.count(), 1)
        self.assertFalse(WorkerIdentityRevision.objects.exists())


    def test_conflicting_profiles_block_all_identifier_peers_in_batch(self):
        path, items = self.batch([self.content, self.content, png(card(OP + ["SYNTHETIC COPY"]))])
        for item, profile in zip(items, ("employee", "self_employed", "self_employed")):
            item["activity_profile"] = profile
        self.write(path / "ready.json", json.dumps({"organization_id": self.org.pk, "files": items}).encode())
        # The first two files reuse one run; the third has a separate run with the same identifier.
        proc = DocumentProcessor(lambda: ScriptedEngine([OP, OP, OP, OP]))
        result = self.run_inbox(proc)[0]
        self.assertEqual(len(result["drafts"]), 2)
        self.assertTrue(all(d["reason"] == "ACTIVITY_PROFILE_CONFLICT" for d in result["drafts"]))
        self.assertFalse(Worker.objects.exists())
        self.assertFalse(WorkerIdentityClaim.objects.exists())

    def test_claim_reuse_preserves_confirmed_correction(self):
        evaluation, run, region = self.evaluation()
        draft = self.draft(evaluation, run, region)
        worker = Worker.objects.get(pk=draft["worker_ref"])
        associate_region(self.user, self.org, run.pk, region, worker)
        confirm_field_proposal(self.user, self.org, FieldProposal.objects.get(ocr_run=run, field_name="birth_date"),
                               corrected_value="1991-03-15")
        # No confirmed document identifier yet: the draft claim must still respect confirmed DOB.
        current = identity.persist_identity_evaluation(self.user, self.org, [run.pk])
        self.assertEqual(self.draft(current, run, region)["reason"], "CONFIRMED_IDENTITY_CONFLICT")
        self.assertEqual(Worker.objects.count(), 1)
        self.assertEqual(WorkerIdentityRevision.objects.get().confirmed_fields["birth_date"], "1991-03-15")

    def test_authorized_other_tenant_cannot_resolve_foreign_evaluation(self):
        from portal.release1a.models import Membership
        evaluation, run, region = self.evaluation()
        Membership.objects.create(user=self.user, organization=self.other, role="organization_admin")
        with self.assertRaises(IdentityEvaluation.DoesNotExist):
            identity.prepare_identity_draft(self.user, self.other, evaluation.pk, run.pk, region, activity_profile="employee")
        self.assertFalse(Worker.objects.exists())

    def test_corrupted_evaluation_and_failed_resolution_audit_make_no_decision(self):
        evaluation, run, region = self.evaluation()
        worker = self.worker()
        with patch("portal.release1a.identity.audit", side_effect=RuntimeError("synthetic failure")):
            with self.assertRaises(RuntimeError):
                identity.resolve_identity_evaluation(self.user, self.org, evaluation.pk, run.pk, region, worker.pk,
                    expected_worker_version=1, expected_revision_id=None, reason="Synthetic review")
        self.assertFalse(DocumentRegionAssociation.objects.exists())
        self.assertFalse(IdentityResolution.objects.exists())
        IdentityEvaluation.objects.filter(pk=evaluation.pk).update(evidence={})
        with self.assertRaisesRegex(ValueError, "CORRUPT"):
            self.draft(evaluation, run, region)
        with self.assertRaisesRegex(ValueError, "CORRUPT"):
            identity.persist_identity_evaluation(self.user, self.org, [run.pk])
