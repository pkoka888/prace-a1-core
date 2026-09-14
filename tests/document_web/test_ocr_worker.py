"""Durable synthetic OCR execution through the isolated Django test runner."""
from datetime import timedelta
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import threading
from unittest.mock import Mock, patch
from uuid import uuid4

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "portal.settings_document_tests")
import django
django.setup()

from allauth.mfa.models import Authenticator
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import DatabaseError, connections, transaction
from django.db.models.query import QuerySet
from django.test import TransactionTestCase, override_settings
from django.utils import timezone

from portal.release1a import document_intake
from portal.release1a.models import (
    AuditEvent, Document, FieldDecision, FieldProposal, Membership, OcrRun,
    Organization,
)
from src.document_core.pipeline import DocumentProcessor
from tests.test_document_core.helpers import OP, ScriptedEngine, card, png


def synthetic_processor():
    return DocumentProcessor(lambda: ScriptedEngine([OP, OP]))


class OcrWorkerTests(TransactionTestCase):
    def setUp(self):
        temporary_root = Path(__file__).resolve().parents[2] / "runtime/portal/temporary"
        temporary_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        temporary = tempfile.TemporaryDirectory(prefix="ocr-worker-test-", dir=temporary_root)
        self.addCleanup(temporary.cleanup)
        self.storage = Path(temporary.name)
        self.inbox = self.storage / "inbox"
        self.inbox.mkdir(mode=0o700)
        self.org = Organization.objects.create(key="ocr-worker-synthetic", label="Synthetic OCR")
        self.other = Organization.objects.create(key="ocr-worker-other", label="Synthetic Other")
        self.user = get_user_model().objects.create_user("ocr-worker-operator")
        Membership.objects.create(user=self.user, organization=self.org, role="organization_admin")
        Authenticator.objects.create(user=self.user, type=Authenticator.Type.TOTP, data={})
        override = override_settings(
            DOCUMENT_STORAGE_ROOT=self.storage,
            DOCUMENT_INBOX_ROOTS={self.org.pk: self.inbox},
            M2_SYNTHETIC_ONLY=True,
        )
        override.enable()
        self.addCleanup(override.disable)
        self.content = png(card(OP))

    def enqueue(self, *, content=None, processor=None):
        return document_intake.intake(
            self.user, self.org, None, "synthetic.png", "image/png",
            self.content if content is None else content, processor=processor, _sync=False,
        )[3]

    def process(self, **kwargs):
        return document_intake.process_pending(self.user, self.org, **kwargs)

    def inbox_batch(self):
        batch = self.inbox / uuid4().hex
        batch.mkdir(mode=0o700)
        name = uuid4().hex + ".png"
        for path, content in (
            (batch / name, self.content),
            (batch / "ready.json", json.dumps({"organization_id": self.org.pk, "files": [
                {"name": name, "sha256": hashlib.sha256(self.content).hexdigest()},
            ]}).encode()),
        ):
            path.write_bytes(content)
            path.chmod(0o600)

    def test_deferred_intake_persists_pending_without_processor_or_thread(self):
        processor = Mock()
        with patch("threading.Thread") as thread:
            run = self.enqueue(processor=processor)
        processor.process.assert_not_called()
        thread.assert_not_called()
        run.refresh_from_db()
        self.assertEqual(run.state, OcrRun.State.PENDING)
        self.assertEqual(run.retry_count, 0)
        self.assertEqual(run.attempt_token, "")
        self.assertIsNone(run.lease_expires_at)
        self.assertFalse(FieldProposal.objects.exists())

    def test_outer_rollback_leaves_no_job_for_worker(self):
        with self.assertRaisesRegex(RuntimeError, "synthetic rollback"):
            with transaction.atomic():
                self.enqueue()
                raise RuntimeError("synthetic rollback")
        processor = Mock()
        self.assertEqual(self.process(processor=processor), [])
        processor.process.assert_not_called()
        self.assertFalse(Document.objects.exists())
        self.assertFalse(OcrRun.objects.exists())

    def test_committed_job_is_processed_once_with_proposals_unconfirmed(self):
        with transaction.atomic():
            run = self.enqueue()
        results = self.process(processor=synthetic_processor())
        self.assertEqual(len(results), 1)
        self.assertIn("run_ref", results[0])
        self.assertEqual(results[0]["state"], OcrRun.State.COMPLETED)
        run.refresh_from_db()
        self.assertEqual(run.retry_count, 1)
        self.assertTrue(run.output_sha256)
        self.assertTrue(FieldProposal.objects.filter(ocr_run=run).exists())
        self.assertFalse(FieldDecision.objects.exists())
        processor = Mock()
        self.assertEqual(self.process(processor=processor), [])
        processor.process.assert_not_called()

    def test_http_upload_returns_pending_without_executing_ocr(self):
        self.client.force_login(self.user)
        session = self.client.session
        session["account_authentication_methods"] = [{"method": "mfa", "type": "totp"}]
        session.save()
        with patch("portal.release1a.document_intake.DocumentProcessor") as factory, \
                patch("threading.Thread") as thread:
            response = self.client.post("/documents/intake/", {
                "file1": SimpleUploadedFile("synthetic.png", self.content, "image/png"),
            })
        self.assertEqual(response.status_code, 302)
        factory.assert_not_called()
        thread.assert_not_called()
        self.assertEqual(OcrRun.objects.get().state, OcrRun.State.PENDING)

    def test_live_claim_is_not_reset_by_requeue_or_worker_scan(self):
        run = self.enqueue()
        token = uuid4().hex
        expiry = timezone.now() + timedelta(minutes=5)
        OcrRun.objects.filter(pk=run.pk).update(
            state=OcrRun.State.RUNNING, attempt_token=token,
            lease_expires_at=expiry, retry_count=1,
        )
        document_intake.queue_run(self.user, self.org, run.pk)
        processor = Mock()
        self.assertEqual(self.process(processor=processor), [])
        processor.process.assert_not_called()
        run.refresh_from_db()
        self.assertEqual(run.state, OcrRun.State.RUNNING)
        self.assertEqual(run.attempt_token, token)
        self.assertEqual(run.lease_expires_at, expiry)
        self.assertEqual(run.retry_count, 1)

    def test_expired_claim_is_recovered_with_new_attempt_token(self):
        run = self.enqueue()
        token = uuid4().hex
        OcrRun.objects.filter(pk=run.pk).update(
            state=OcrRun.State.RUNNING, attempt_token=token, retry_count=1,
            lease_expires_at=timezone.now() - timedelta(seconds=1),
        )
        processor = synthetic_processor()
        original_process = processor.process

        def observe_claim(*args, **kwargs):
            claimed = OcrRun.objects.get(pk=run.pk)
            self.assertNotEqual(claimed.attempt_token, token)
            self.assertEqual(claimed.retry_count, 2)
            self.assertGreater(claimed.lease_expires_at, timezone.now())
            return original_process(*args, **kwargs)

        with patch.object(processor, "process", side_effect=observe_claim):
            self.process(processor=processor)
        run.refresh_from_db()
        self.assertEqual(run.state, OcrRun.State.COMPLETED)
        self.assertEqual(run.retry_count, 2)
        self.assertEqual(Document.objects.count(), 1)

    def test_failed_job_is_sanitized_and_requires_explicit_retry(self):
        run = self.enqueue()
        processor = Mock()
        processor.process.side_effect = RuntimeError("SYNTHETIC_PRIVATE_ERROR_VALUE")
        results = self.process(processor=processor)
        run.refresh_from_db()
        self.assertEqual(run.state, OcrRun.State.FAILED)
        self.assertNotIn("SYNTHETIC_PRIVATE_ERROR_VALUE", json.dumps(results))
        self.assertNotIn("SYNTHETIC_PRIVATE_ERROR_VALUE", run.failure_reason)
        self.assertNotIn("SYNTHETIC_PRIVATE_ERROR_VALUE", str(list(AuditEvent.objects.values())))
        processor.reset_mock()
        self.assertEqual(self.process(processor=processor), [])
        processor.process.assert_not_called()
        document_intake.queue_run(self.user, self.org, run.pk)
        self.assertEqual(self.process(processor=synthetic_processor())[0]["state"], "completed")
        run.refresh_from_db()
        self.assertEqual(run.retry_count, 2)

    def test_expired_job_at_retry_limit_does_not_execute_again(self):
        run = self.enqueue()
        OcrRun.objects.filter(pk=run.pk).update(
            state=OcrRun.State.RUNNING, retry_count=3,
            lease_expires_at=timezone.now() - timedelta(seconds=1),
        )
        processor = Mock()
        self.process(processor=processor)
        processor.process.assert_not_called()
        run.refresh_from_db()
        self.assertEqual(run.retry_count, 3)

    def test_publication_failure_is_sanitized_and_records_failed_attempt(self):
        run = self.enqueue()
        with patch("portal.release1a.document_intake.persist_proposals",
                   side_effect=RuntimeError("SYNTHETIC_PRIVATE_PUBLICATION_VALUE")), \
                self.assertLogs("portal.release1a.document_intake", level="ERROR") as logs:
            with self.assertRaisesRegex(RuntimeError, "^OCR_PUBLICATION_FAILED$"):
                self.process(processor=synthetic_processor())
        self.assertNotIn("SYNTHETIC_PRIVATE_PUBLICATION_VALUE", " ".join(logs.output))
        self.assertTrue(all(record.exc_info is None for record in logs.records))
        run.refresh_from_db()
        self.assertEqual(run.state, OcrRun.State.FAILED)
        self.assertEqual(run.failure_reason, "OCR_PUBLICATION_FAILED")
        self.assertIsNone(run.lease_expires_at)
        self.assertFalse(FieldProposal.objects.exists())

    def test_old_attempt_failure_cannot_overwrite_replacement_claim(self):
        run = self.enqueue()
        replacement_token = uuid4().hex

        def replace_then_fail(*args):
            OcrRun.objects.filter(pk=run.pk).update(attempt_token=replacement_token)
            raise RuntimeError("SYNTHETIC_PRIVATE_OLD_ATTEMPT")

        with patch("portal.release1a.document_intake._run_ocr_sync", side_effect=replace_then_fail), \
                self.assertLogs("portal.release1a.document_intake", level="ERROR") as logs:
            with self.assertRaisesRegex(RuntimeError, "^OCR_PUBLICATION_FAILED$"):
                self.process(processor=synthetic_processor())
        run.refresh_from_db()
        self.assertEqual(run.state, OcrRun.State.RUNNING)
        self.assertEqual(run.attempt_token, replacement_token)
        self.assertEqual(run.failure_reason, "")
        self.assertFalse(AuditEvent.objects.filter(event_type="ocr.failed").exists())
        self.assertNotIn("SYNTHETIC_PRIVATE_OLD_ATTEMPT", " ".join(logs.output))

    def test_database_failure_during_publication_retains_recoverable_lease(self):
        run = self.enqueue()
        update = QuerySet.update

        def unavailable_failure_update(queryset, **kwargs):
            if queryset.model is OcrRun and kwargs.get("state") == OcrRun.State.FAILED:
                raise DatabaseError("SYNTHETIC_PRIVATE_FAILURE_WRITE_DSN")
            return update(queryset, **kwargs)

        with patch("portal.release1a.document_intake.persist_proposals",
                   side_effect=DatabaseError("SYNTHETIC_PRIVATE_PUBLICATION_DSN")), \
                patch.object(QuerySet, "update", unavailable_failure_update), \
                self.assertLogs("portal.release1a.document_intake", level="ERROR") as logs:
            with self.assertRaisesRegex(RuntimeError, "^OCR_STORAGE_OR_DATABASE_UNAVAILABLE$"):
                self.process(processor=synthetic_processor())
        run.refresh_from_db()
        self.assertEqual(run.state, OcrRun.State.RUNNING)
        self.assertEqual(run.retry_count, 1)
        self.assertGreater(run.lease_expires_at, timezone.now())
        previous_token = run.attempt_token
        self.assertTrue(previous_token)
        self.assertEqual(run.output_key, "")
        self.assertFalse(FieldProposal.objects.exists())
        self.assertNotIn("SYNTHETIC_PRIVATE", " ".join(logs.output))
        self.assertTrue(all(record.exc_info is None for record in logs.records))
        OcrRun.objects.filter(pk=run.pk).update(lease_expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.process(processor=synthetic_processor())[0]["state"], "completed")
        run.refresh_from_db()
        self.assertEqual(run.retry_count, 2)
        self.assertNotEqual(run.attempt_token, previous_token)

    def test_http_read_and_upload_complete_while_worker_processor_is_blocked(self):
        first = self.enqueue()
        self.client.force_login(self.user)
        session = self.client.session
        session["account_authentication_methods"] = [{"method": "mfa", "type": "totp"}]
        session.save()
        entered, release = threading.Event(), threading.Event()
        outcomes = []
        processor = synthetic_processor()
        original_process = processor.process

        def blocked_process(*args, **kwargs):
            entered.set()
            if not release.wait(timeout=10):
                raise RuntimeError("SYNTHETIC_TEST_WORKER_DEADLINE")
            return original_process(*args, **kwargs)

        def consume():
            try:
                actor = get_user_model().objects.get(pk=self.user.pk)
                organization = Organization.objects.get(pk=self.org.pk)
                outcomes.extend(document_intake.process_pending(actor, organization, processor=processor))
            except Exception as exc:
                outcomes.append({"exception_type": type(exc).__name__})
            finally:
                connections.close_all()

        with patch.object(processor, "process", side_effect=blocked_process):
            thread = threading.Thread(target=consume)
            thread.start()
            try:
                self.assertTrue(entered.wait(timeout=5), outcomes)
                response = self.client.get("/documents/")
                self.assertEqual(response.status_code, 200)
                with patch("portal.release1a.document_intake.DocumentProcessor") as factory:
                    response = self.client.post("/documents/intake/", {
                        "file1": SimpleUploadedFile(
                            "synthetic-second.png", png(card(OP + ["SYNTHETIC SECOND UPLOAD"])), "image/png",
                        ),
                    })
                self.assertEqual(response.status_code, 302)
                factory.assert_not_called()
                second = OcrRun.objects.exclude(pk=first.pk).get()
                self.assertEqual(second.state, OcrRun.State.PENDING)
                self.assertEqual(second.retry_count, 0)
                self.assertEqual(second.attempt_token, "")
                self.assertFalse(FieldProposal.objects.filter(ocr_run=second).exists())
                self.assertFalse(release.is_set())
                self.assertTrue(thread.is_alive())
            finally:
                release.set()
                thread.join(timeout=10)
            self.assertFalse(thread.is_alive())
        self.assertEqual([result.get("state") for result in outcomes], [OcrRun.State.COMPLETED])
        second.refresh_from_db()
        self.assertEqual(second.state, OcrRun.State.PENDING)

    def test_command_defaults_to_one_job_and_emits_safe_result(self):
        self.enqueue()
        self.enqueue(content=png(card(OP + ["SYNTHETIC SECOND UPLOAD"])))
        output = io.StringIO()
        with patch("portal.release1a.document_intake.DocumentProcessor", return_value=synthetic_processor()):
            call_command("process_ocr", organization_id=self.org.pk, actor_id=self.user.pk, stdout=output)
        self.assertEqual(OcrRun.objects.filter(state=OcrRun.State.COMPLETED).count(), 1)
        self.assertEqual(OcrRun.objects.filter(state=OcrRun.State.PENDING).count(), 1)
        self.assertNotIn("TESTOVA", output.getvalue())

    def test_command_requires_actor_and_organization(self):
        for options in ({}, {"organization_id": self.org.pk}, {"actor_id": self.user.pk}):
            with self.subTest(options=options), self.assertRaises(CommandError):
                call_command("process_ocr", stdout=io.StringIO(), **options)

    def test_command_startup_database_error_is_sanitized(self):
        from portal.release1a.management.commands.process_ocr import Command

        output = io.StringIO()
        with patch.object(Command, "_scope", side_effect=DatabaseError("SYNTHETIC_PRIVATE_DATABASE_DSN")):
            with self.assertRaisesRegex(CommandError, "^OCR_WORKER_STARTUP_FAILED$"):
                call_command("process_ocr", organization_id=self.org.pk,
                             actor_id=self.user.pk, stdout=output)
        self.assertNotIn("SYNTHETIC_PRIVATE_DATABASE_DSN", output.getvalue())

    def test_command_denies_foreign_scope_and_real_data_before_processing(self):
        self.enqueue()
        with patch("portal.release1a.document_intake.DocumentProcessor") as processor:
            with self.assertRaises(CommandError):
                call_command("process_ocr", organization_id=self.other.pk,
                             actor_id=self.user.pk, stdout=io.StringIO())
            with override_settings(M2_SYNTHETIC_ONLY=False), self.assertRaises(CommandError):
                call_command("process_ocr", organization_id=self.org.pk,
                             actor_id=self.user.pk, stdout=io.StringIO())
        processor.assert_not_called()
        self.assertEqual(OcrRun.objects.get().state, OcrRun.State.PENDING)

    def test_default_inbox_command_finishes_ocr_without_background_thread(self):
        self.inbox_batch()
        output = io.StringIO()
        with patch("portal.release1a.document_intake.DocumentProcessor", return_value=synthetic_processor()), \
                patch("threading.Thread") as thread:
            call_command("a1_process_inbox", organization_id=self.org.pk,
                         actor_id=self.user.pk, stdout=output)
        thread.assert_not_called()
        self.assertEqual(json.loads(output.getvalue())[0]["status"], "completed")
        self.assertEqual(OcrRun.objects.get().state, OcrRun.State.COMPLETED)
        self.assertFalse(FieldDecision.objects.exists())

    def test_default_inbox_command_reports_failed_receipt_and_nonzero_exit(self):
        self.inbox_batch()
        processor = Mock()
        processor.process.side_effect = RuntimeError("SYNTHETIC_PRIVATE_INBOX_FAILURE")
        output = io.StringIO()
        with patch("portal.release1a.document_intake.DocumentProcessor", return_value=processor):
            with self.assertRaisesRegex(CommandError, "^INBOX_HAS_UNRESOLVED_ITEMS$") as failure:
                call_command("a1_process_inbox", organization_id=self.org.pk,
                             actor_id=self.user.pk, stdout=output)
        self.assertEqual(failure.exception.returncode, 1)
        result = json.loads(output.getvalue())[0]
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["items"][0]["status"], "failed")
        self.assertNotIn("SYNTHETIC_PRIVATE_INBOX_FAILURE", output.getvalue())
        receipt = json.loads((self.storage / result["receipt_key"]).read_text())
        self.assertEqual(receipt["items"], result["items"])
        self.assertNotIn("SYNTHETIC_PRIVATE_INBOX_FAILURE", json.dumps(receipt))
        self.assertEqual(OcrRun.objects.get().state, OcrRun.State.FAILED)
