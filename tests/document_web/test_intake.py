"""Isolated synthetic Django integration; run with Django's test runner."""
import json
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "portal.settings_document_tests")
import django
django.setup()
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from datetime import timedelta
from django.test import TransactionTestCase, override_settings, RequestFactory
from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone
from allauth.mfa.models import Authenticator
from portal.release1a.models import (Organization, Worker, Membership, Document, OcrRun, IntakeSession,
                                    FieldProposal, FieldDecision, WorkerIdentityRevision, AuditEvent)
from portal.release1a.services import Forbidden, confirm_field_proposal
from portal.release1a.document_intake import supersede, intake, execute_run, read_result, associate_region, download_original, read_session
from portal.release1a.document_storage import document_storage
from portal.release1a.intake_views import detail, original
from src.document_core.pipeline import DocumentProcessor
from src.document_core.cli import process_files
from tests.test_document_core.helpers import OP, ZP, card, png, ScriptedEngine, td1


def processor(lines=OP):
    return DocumentProcessor(lambda: ScriptedEngine([lines, lines]))


def semantic(result):
    return [{"classification": {k: d["classification"][k] for k in ("type", "country", "side", "version")},
             "fields": [(f["field"], f["value"], f["findings"]) for f in d["fields"]],
             "completeness": d["completeness"]} for d in result["documents"]]


class IntakeTests(TransactionTestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.settings_override = override_settings(DOCUMENT_STORAGE_ROOT=Path(self.temporary.name), M2_SYNTHETIC_ONLY=True)
        self.settings_override.enable(); self.addCleanup(self.settings_override.disable)
        self.org = Organization.objects.create(key="synthetic-one", label="Synthetic One")
        self.other = Organization.objects.create(key="synthetic-two", label="Synthetic Two")
        self.user = get_user_model().objects.create_user("synthetic-reviewer")
        Membership.objects.create(user=self.user, organization=self.org, role="organization_admin")
        Authenticator.objects.create(user=self.user, type=Authenticator.Type.TOTP, data={})
        self.worker = Worker.objects.create(organization=self.org, given_name="ALFA", family_name="TESTOVA",
                                            birth_date="1990-03-15", activity_profile="employee")
        self.content = png(card(OP))

    def ingest(self, proc=None):
        return intake(self.user, self.org, None, "misleading-passport.png", "image/png", self.content,
                      processor=proc or processor(), _sync=True)

    def test_preserved_source_separate_derivative_and_cli_parity(self):
        document, version, classifications, run = self.ingest()
        self.assertEqual(run.state, "completed")
        self.assertIsNone(document.worker_id)
        self.assertNotEqual(version.opaque_key, run.output_key)
        self.assertEqual(download_original(self.user,self.org,document)[0],self.content)
        payload=read_result(self.user,self.org,run.pk)
        self.assertTrue(FieldProposal.objects.filter(ocr_run=run, field_name="birth_date", proposed_value="1990-03-15").exists())
        path=Path(self.temporary.name)/"synthetic.png";path.write_bytes(self.content)
        out=Path(self.temporary.name)/"cli"
        self.assertEqual(process_files([path],out,processor=processor()),0)
        cli=json.loads(next(out.glob('*/result.json')).read_text())
        self.assertEqual(semantic(payload["result"]),semantic(cli))
        self.assertEqual(FieldDecision.objects.count(),0)
        self.assertEqual(WorkerIdentityRevision.objects.count(),0)
        self.assertFalse(payload["result"]["workflow_ready"])

    def test_duplicate_keeps_run_region_ids_and_receipt(self):
        doc,version,_,run=self.ingest()
        first=read_result(self.user,self.org,run.pk)
        duplicate=self.ingest()
        self.assertEqual(duplicate[0].pk,doc.pk)
        self.assertEqual(duplicate[3].pk,run.pk)
        self.assertEqual(read_result(self.user,self.org,run.pk),first)
        self.assertEqual(execute_run(self.user,self.org,run.pk,_sync=True).output_key,run.output_key)

    def test_failure_retry_and_completed_idempotency(self):
        class Broken:
            def process(self,*args,**kwargs): raise RuntimeError("synthetic sensitive exception")
        doc,version,_,run=self.ingest(Broken())
        self.assertEqual(run.state,"failed")
        self.assertIsNotNone(run.completed_at)
        failed=read_result(self.user,self.org,run.pk)
        self.assertEqual(failed["status"],"failed")
        self.assertNotIn("sensitive",json.dumps(failed))
        self.assertFalse(FieldProposal.objects.exists())
        run=execute_run(self.user,self.org,run.pk,processor=processor(),_sync=True)
        self.assertEqual(run.state,"completed")
        self.assertEqual(run.retry_count,2)
        count=FieldProposal.objects.count()
        execute_run(self.user,self.org,run.pk,processor=Broken())
        self.assertEqual(FieldProposal.objects.count(),count)
        self.assertEqual(download_original(self.user,self.org,doc)[0],self.content)

    def test_tenant_and_capability_checks_before_storage(self):
        doc,_,_,run=self.ingest()
        other_worker=Worker.objects.create(organization=self.other,given_name="B",family_name="TEST",birth_date="1990-01-01")
        with patch("portal.release1a.document_intake.document_storage") as storage:
            with self.assertRaises(Forbidden):
                intake(self.user,self.org,other_worker,"a.png","image/png",self.content)
            with self.assertRaises(Forbidden): read_result(self.user,self.other,run.pk)
            storage.assert_not_called()
        Membership.objects.filter(user=self.user).update(role="system_worker")
        request=RequestFactory().get("/");request.user=self.user;request.organization=self.org
        response=original(request,doc.pk)
        self.assertEqual(response.status_code,403);self.assertEqual(response.content,b"")

    def test_hash_corruption_blocks_read(self):
        _,_,_,run=self.ingest()
        Path(document_storage().path(run.output_key)).write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError,"DERIVATIVE_HASH_MISMATCH"):
            read_result(self.user,self.org,run.pk)

    def test_scanner_failure_and_real_activation_block(self):
        with override_settings(DOCUMENT_SCANNER=lambda _: False):
            with self.assertRaisesRegex(ValueError,"SCANNER_REJECTED"): self.ingest()
        with override_settings(M2_SYNTHETIC_ONLY=False):
            with self.assertRaises(Forbidden): self.ingest()
        self.assertFalse(Document.objects.exists())

    def test_human_association_then_acceptance_creates_revision(self):
        doc,_,_,run=self.ingest()
        proposal=FieldProposal.objects.get(ocr_run=run,field_name="birth_date")
        with self.assertRaisesRegex(ValueError,"REGION_ASSOCIATION_REQUIRED"):
            confirm_field_proposal(self.user,self.org,proposal)
        region=read_result(self.user,self.org,run.pk)["result"]["documents"][0]
        first = associate_region(self.user,self.org,run.pk,region["document_id"],self.worker)
        repeated = associate_region(self.user,self.org,run.pk,region["document_id"],self.worker)
        self.assertEqual(first.pk, repeated.pk)
        confirm_field_proposal(self.user,self.org,proposal)
        self.assertEqual(WorkerIdentityRevision.objects.get().confirmed_fields["birth_date"],"1990-03-15")
        self.assertEqual(FieldDecision.objects.count(),1)
        with self.assertRaises(ValueError): confirm_field_proposal(self.user,self.org,proposal)
        self.worker.refresh_from_db()
        self.assertEqual(self.worker.family_name,"TESTOVA")
        request=RequestFactory().get("/");request.user=self.user;request.organization=self.org
        self.assertEqual(detail(request,doc.pk).status_code,200)

    def test_live_lease_not_reclaimed_expired_lease_recovered(self):
        _,_,_,run=self.ingest()
        OcrRun.objects.filter(pk=run.pk).update(state="running",lease_expires_at=timezone.now()+timedelta(minutes=5))
        class Never:
            def process(self,*args,**kwargs): raise AssertionError("must not call")
        self.assertEqual(execute_run(self.user,self.org,run.pk,processor=Never()).state,"running")
        # Simulate crash before a first publication, not editing an existing accepted result.
        OcrRun.objects.filter(pk=run.pk).update(lease_expires_at=timezone.now()-timedelta(seconds=1), retry_count=0)
        FieldProposal.objects.filter(ocr_run=run).delete()
        self.assertEqual(execute_run(self.user,self.org,run.pk,processor=processor(),_sync=True).state,"completed")

    def test_result_storage_failure_records_retryable_failed_run(self):
        from portal.release1a.document_storage import ProtectedDocumentStorage
        original_save = ProtectedDocumentStorage.save
        def save(storage, name, *args, **kwargs):
            if name.endswith(".json"):
                raise OSError("synthetic result write failure")
            return original_save(storage, name, *args, **kwargs)
        with patch.object(ProtectedDocumentStorage, "save", save):
            _, _, _, run = self.ingest()
        self.assertEqual(run.state, "failed")
        self.assertEqual(run.failure_reason, "OUTPUT_STORAGE_FAILED")
        self.assertEqual(run.output_key, "")
        self.assertEqual(execute_run(self.user, self.org, run.pk, processor=processor(),_sync=True).state, "completed")

    def test_storage_has_no_public_url_and_requires_opaque_key(self):
        with self.assertRaises(ValueError): document_storage().url("anything")
        with self.assertRaises(ValueError): document_storage().path("../outside")

    def test_audit_does_not_contain_extracted_values(self):
        self.ingest()
        for event in AuditEvent.objects.all():
            self.assertNotIn("TESTOVA",str(event.__dict__))
            self.assertNotIn("TST000001",str(event.__dict__))

    def test_cross_file_side_matching_and_reused_duplicate_in_session(self):
        first = IntakeSession.objects.create(organization=self.org, purpose="a1")
        doc, _, _, run = intake(self.user,self.org,None,"front.png","image/png",self.content,first,processor=processor(),_sync=True)
        second = IntakeSession.objects.create(organization=self.org,purpose="a1")
        intake(self.user,self.org,None,"same-front.png","image/png",self.content,second,processor=processor(),_sync=True)
        back = png(card(td1()))
        intake(self.user,self.org,None,"unrelated-name.png","image/png",back,second,processor=processor(td1()),_sync=True)
        result = read_session(self.user,self.org,second)
        self.assertEqual(len(result["documents"]),2)
        self.assertTrue(all(d["paired_with"] for d in result["documents"]))
        request=RequestFactory().get("/");request.user=self.user;request.organization=self.org
        self.assertEqual(detail(request,doc.pk).status_code,200)

    def test_existing_accepted_identifier_proposes_worker_without_accepting(self):
        _,_,_,run=self.ingest()
        region=read_result(self.user,self.org,run.pk)["result"]["documents"][0]
        associate_region(self.user,self.org,run.pk,region["document_id"],self.worker)
        proposal=FieldProposal.objects.get(ocr_run=run,field_name="document_number")
        confirm_field_proposal(self.user,self.org,proposal)
        content=png(card(OP+["SYNTHETIC COPY"]))
        _,_,_,new_run=intake(self.user,self.org,None,"copy.png","image/png",content,processor=processor(),_sync=True)
        association=read_result(self.user,self.org,new_run.pk)["result"]["documents"][0]["association"]
        self.assertEqual(association["status"],"proposed")
        self.assertEqual(association["worker_id"],str(self.worker.pk))
        self.assertFalse(association["accepted"])
        self.assertEqual(FieldDecision.objects.count(),1)

    def test_http_unassigned_upload_review_crops_and_worker_card(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.client.force_login(self.user)
        session=self.client.session
        session["account_authentication_methods"]=[{"method":"mfa","type":"totp"}]
        session.save()
        with patch("portal.release1a.document_intake.DocumentProcessor", return_value=processor()):
            response=self.client.post("/documents/intake/", {"file1":SimpleUploadedFile("synthetic.png",self.content,"image/png")})
        self.assertEqual(response.status_code,302)
        document=Document.objects.get()
        run=OcrRun.objects.get()
        self.assertEqual(run.state, OcrRun.State.PENDING)
        from portal.release1a.document_intake import process_pending
        process_pending(self.user, self.org, run_id=run.pk, processor=processor())
        self.assertContains(self.client.get(response.url),"Občanský průkaz")
        self.assertContains(self.client.get("/documents/"),"Nepřiřazeno")
        region=read_result(self.user,self.org,run.pk)["result"]["documents"][0]
        image=self.client.get(f"/documents/ocr/{run.pk}/{region['document_id']}/original/")
        self.assertEqual(image.status_code,200)
        self.assertTrue(image.content.startswith(b"\x89PNG"))
        review=self.client.get(f"/documents/{document.pk}/")
        options=review.context["regions"][0]["worker_options"]
        token=next(option["token"] for option in options if option["worker"].pk == self.worker.pk)
        response=self.client.post(f"/documents/{document.pk}/",{"action":"associate","worker_choice":token,
                                   "reason":"Synthetic source checked"})
        self.assertEqual(response.status_code,302)
        # Empty confirmation is never an implicit document acceptance.
        self.assertEqual(self.client.post(f"/documents/{document.pk}/",{"action":"confirm"}).status_code,200)
        self.assertEqual(FieldDecision.objects.count(),0)
        proposal=FieldProposal.objects.get(ocr_run=run,field_name="birth_date")
        from portal.release1a.field_review import review_context
        token = review_context(self.user, self.org, [proposal.pk])[proposal.pk]["token"]
        response=self.client.post(f"/documents/{document.pk}/",{"action":"confirm",f"confirm_{proposal.pk}":"on", f"expected_{proposal.pk}":token, f"value_{proposal.field_name}_{proposal.pk}":proposal.proposed_value})
        self.assertEqual(response.status_code,302)
        self.assertEqual(FieldDecision.objects.count(),1)
        self.assertContains(self.client.get(f"/workers/{self.worker.pk}/"),"Potvrzené údaje z dokladů")
        self.assertContains(self.client.get(f"/workers/{self.worker.pk}/"),"1990-03-15")

    def test_supersede_preserves_bytes_receipts_and_is_idempotent(self):
        doc, old_version, _, old_run = self.ingest()
        receipt = read_result(self.user, self.org, old_run.pk)
        replacement = png(card(ZP))
        version, run = supersede(self.user, self.org, doc.pk, "replacement.png", "image/png", replacement, processor=processor(ZP),_sync=True)
        self.assertEqual(version.version_number, 2)
        self.assertEqual(run.state, "completed")
        self.assertEqual(download_original(self.user, self.org, doc)[0], replacement)
        with document_storage().open(old_version.opaque_key, "rb") as stream:
            self.assertEqual(stream.read(), self.content)
        self.assertEqual(read_result(self.user, self.org, old_run.pk), receipt)
        duplicate, repeated = supersede(self.user, self.org, doc.pk, "retry.png", "image/png", replacement, processor=processor(ZP),_sync=True)
        self.assertEqual((duplicate.pk, repeated.pk), (version.pk, run.pk))
        self.assertEqual(doc.documentversion_set.count(), 2)
        self.assertEqual(AuditEvent.objects.filter(event_type="document.superseded").count(), 1)
        self.assertEqual(FieldDecision.objects.count(), 0)
        self.assertEqual(WorkerIdentityRevision.objects.count(), 0)

    def test_supersede_denies_role_tenant_and_real_data_before_storage(self):
        doc, _, _, _ = self.ingest()
        replacement = png(card(ZP))
        files = sorted(Path(self.temporary.name).rglob("*.source"))
        Membership.objects.filter(user=self.user).update(role="jan_planner")
        with self.assertRaises(Forbidden):
            supersede(self.user, self.org, doc.pk, "next.png", "image/png", replacement)
        Membership.objects.filter(user=self.user).update(role="organization_admin")
        foreign = Document.objects.create(organization=self.other, worker=None, opaque_key="synthetic-foreign", sha256="a"*64, content_type="image/png")
        with self.assertRaises(Document.DoesNotExist):
            supersede(self.user, self.org, foreign.pk, "next.png", "image/png", replacement)
        with override_settings(M2_SYNTHETIC_ONLY=False, DOCUMENT_SCANNER=lambda _: True):
            with self.assertRaises(Forbidden):
                supersede(self.user, self.org, doc.pk, "next.png", "image/png", replacement)
        self.assertEqual(sorted(Path(self.temporary.name).rglob("*.source")), files)
        self.assertEqual(doc.documentversion_set.count(), 1)

    def test_supersede_rejects_invalid_content_and_cleans_failed_database_write(self):
        doc, _, _, _ = self.ingest()
        before = sorted(Path(self.temporary.name).rglob("*.source"))
        with self.assertRaises(ValueError):
            supersede(self.user, self.org, doc.pk, "bad.png", "image/png", b"invalid")
        with patch("portal.release1a.document_intake.audit", side_effect=RuntimeError("synthetic write failure")):
            with self.assertRaises(RuntimeError):
                supersede(self.user, self.org, doc.pk, "next.png", "image/png", png(card(ZP)))
        self.assertEqual(sorted(Path(self.temporary.name).rglob("*.source")), before)
        self.assertEqual(doc.documentversion_set.count(), 1)
        self.assertEqual(download_original(self.user, self.org, doc)[0], self.content)

    def test_superseded_proposals_cannot_be_accepted_and_failed_ocr_is_retryable(self):
        doc, _, _, old_run = self.ingest()
        region = read_result(self.user, self.org, old_run.pk)["result"]["documents"][0]
        associate_region(self.user, self.org, old_run.pk, region["document_id"], self.worker)
        proposal = FieldProposal.objects.get(ocr_run=old_run, field_name="birth_date")
        class Broken:
            def process(self, *args, **kwargs):
                raise RuntimeError("synthetic OCR failure")
        version, run = supersede(self.user, self.org, doc.pk, "next.png", "image/png", png(card(ZP)), processor=Broken(),_sync=True)
        self.assertEqual(run.state, "failed")
        with self.assertRaisesRegex(ValueError, "DOCUMENT_VERSION_SUPERSEDED"):
            confirm_field_proposal(self.user, self.org, proposal)
        with self.assertRaisesRegex(ValueError, "DOCUMENT_VERSION_SUPERSEDED"):
            associate_region(self.user, self.org, old_run.pk, region["document_id"], self.worker)
        self.assertEqual(execute_run(self.user, self.org, run.pk, processor=processor(ZP),_sync=True).state, "completed")
        self.assertEqual(doc.documentversion_set.count(), 2)

    def test_http_supersede_uses_protected_pipeline(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        doc, _, _, _ = self.ingest()
        self.client.force_login(self.user)
        session = self.client.session
        session["account_authentication_methods"] = [{"method":"mfa", "type":"totp"}]
        session.save()
        with patch("portal.release1a.document_intake.DocumentProcessor", return_value=processor(ZP)):
            response = self.client.post(f"/documents/{doc.pk}/supersede/", {
                "new_file": SimpleUploadedFile("replacement.png", png(card(ZP)), "image/png")})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(doc.documentversion_set.count(), 2)
        new_run = OcrRun.objects.filter(document=doc).order_by("-pk").first()
        self.assertEqual(new_run.state, OcrRun.State.PENDING)
        from portal.release1a.document_intake import process_pending
        process_pending(self.user, self.org, run_id=new_run.pk, processor=processor(ZP))
        self.assertEqual(self.client.get(f"/documents/{doc.pk}/download/").content, png(card(ZP)))
        self.assertContains(self.client.get(response.url), "Průkaz pojištěnce")
        Membership.objects.filter(user=self.user).update(role="operator")
        self.assertEqual(self.client.get(f"/documents/{doc.pk}/supersede/").status_code, 403)

    def test_old_ocr_completion_cannot_change_replacement_state(self):
        if connection.vendor != "postgresql":
            self.skipTest("PostgreSQL concurrency evidence required")
        from concurrent.futures import ThreadPoolExecutor
        from threading import Event
        from django.db import close_old_connections
        class Broken:
            def process(self, *args, **kwargs):
                raise RuntimeError("synthetic failure")
        doc, _, _, old_run = self.ingest(Broken())
        started, release = Event(), Event()
        class Slow:
            def process(self, *args, **kwargs):
                started.set()
                if not release.wait(15):
                    raise RuntimeError("synthetic timeout")
                return processor().process(*args, **kwargs)
        def finish_old():
            close_old_connections()
            try:
                return execute_run(self.user, self.org, old_run.pk, processor=Slow(),_sync=True).state
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(finish_old)
            try:
                self.assertTrue(started.wait(10))
                supersede(self.user, self.org, doc.pk, "next.png", "image/png", png(card(ZP)), processor=processor(ZP),_sync=True)
                Document.objects.filter(pk=doc.pk).update(state="confirmed")
            finally:
                release.set()
            self.assertEqual(pending.result(timeout=20), "completed")
        doc.refresh_from_db()
        self.assertEqual(doc.state, "confirmed")

    def test_concurrent_duplicate_supersede_creates_one_version(self):
        if connection.vendor != "postgresql":
            self.skipTest("PostgreSQL row locks required")
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.db import close_old_connections
        doc, _, _, _ = self.ingest()
        replacement = png(card(ZP))
        barrier = Barrier(2)
        def replace():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                version, run = supersede(self.user, self.org, doc.pk, "next.png", "image/png", replacement, processor=processor(ZP),_sync=True)
                return version.pk, run.pk
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: replace(), range(2)))
        self.assertEqual(results[0], results[1])
        self.assertEqual(doc.documentversion_set.count(), 2)
        self.assertEqual(OcrRun.objects.get(pk=results[0][1]).state, "completed")

    def test_concurrent_claim_and_expired_attempt_fencing(self):
        if connection.vendor != "postgresql":
            self.skipTest("PostgreSQL concurrency evidence requires the ephemeral PG harness")
        from concurrent.futures import ThreadPoolExecutor
        from threading import Event
        from django.db import close_old_connections
        class Broken:
            def process(self,*args,**kwargs): raise ValueError("synthetic failure")
        _,_,_,run=self.ingest(Broken())
        started, release=Event(),Event()
        class Slow:
            def process(inner,*args,**kwargs):
                started.set()
                if not release.wait(20): raise RuntimeError("test timeout")
                return processor().process(*args,**kwargs)
        def work():
            close_old_connections()
            try: return execute_run(self.user,self.org,run.pk,processor=Slow(),_sync=True).state
            finally: close_old_connections()
        with ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(work)
            try:
                self.assertTrue(started.wait(10))
                # A live lease prevents another attempt from reaching OCR.
                self.assertEqual(execute_run(self.user,self.org,run.pk,processor=Broken()).state,"running")
                OcrRun.objects.filter(pk=run.pk).update(lease_expires_at=timezone.now()-timedelta(seconds=1))
                winner=execute_run(self.user,self.org,run.pk,processor=processor(),_sync=True)
                self.assertEqual(winner.state,"completed")
                saved=read_result(self.user,self.org,run.pk)
            finally:
                release.set()
            self.assertEqual(future.result(timeout=20),"completed")
        self.assertEqual(read_result(self.user,self.org,run.pk),saved)
        self.assertEqual(FieldProposal.objects.filter(ocr_run=run).count(),5)



class MigrationTests(TransactionTestCase):
    def test_forward_transition_from_historical_states(self):
        target=[("release1a","0009_document_region_association")]
        previous=[("release1a","0007_add_state_textchoices")]
        executor=MigrationExecutor(connection)
        executor.migrate(previous)
        try:
            apps=executor.loader.project_state(previous).apps
            Organization=apps.get_model("release1a","Organization")
            org=Organization.objects.create(key="historical-synthetic",label="Historical Synthetic")
            Worker=apps.get_model("release1a","Worker")
            worker=Worker.objects.create(organization=org,given_name="OLD",family_name="TEST",birth_date="1990-01-01")
            Document=apps.get_model("release1a","Document")
            original=Document.objects.create(organization=org,worker=worker,opaque_key="historical-key",sha256="a"*64,content_type="image/png")
            MigrationExecutor(connection).migrate(target)
            apps=MigrationExecutor(connection).loader.project_state(target).apps
            migrated=apps.get_model("release1a","Document").objects.get(pk=original.pk)
            self.assertEqual(migrated.opaque_key,"historical-key")
            self.assertEqual(migrated.worker_id,worker.pk)
            self.assertEqual(migrated.purpose,"worker_intake")
            doc=apps.get_model("release1a","Document").objects.create(organization_id=org.pk,worker=None,opaque_key="new-key",sha256="b"*64,content_type="image/png")
            self.assertIsNone(doc.worker_id)
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())
