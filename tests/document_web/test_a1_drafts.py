"""Synthetic draft preparation, preserved machine status and package recovery."""
import json
import io
from django.core.management import call_command
from pathlib import Path
from unittest.mock import patch

from django.test import TransactionTestCase, override_settings
from scripts.finalize_a1 import CSV_FIELDS
from tests.test_a1_application_draft import pending_row, synthetic_profile
from . import test_a1_exports as a1_export_tests
from . import test_inbox as inbox_tests
from portal.release1a.a1_exports import IDENTITY, GROUPS, prepare_input_case, update_assignment_facts
from portal.release1a.a1_drafts import prepare_application_draft, reserve_application_draft, DraftInputBlocked, reserve_application_generation, _publish_reserved
from portal.release1a.models import A1Case, A1DraftReservation, A1DraftGeneration, FieldProposal, WorkerIdentityRevision
from portal.release1a.services import Forbidden, StaleWrite


def setup_draft(test):
    a1_export_tests.A1ExportTests.setUp(test)
    a1_export_tests.A1ExportTests.inputs(test)
    row = pending_row()
    FieldProposal.objects.filter(ocr_run=test.run).delete()
    for field in set(IDENTITY.values()):
        FieldProposal.objects.create(organization=test.org, document=test.run.document,
            version=test.run.version, ocr_run=test.run, document_region_id=test.region,
            field_name=field, proposed_value=row[field])
    facts = {group: {key: row[field] for key, field in fields.items() if row[field]}
             for group, fields in GROUPS.items()}
    facts["certificate"] = {}  # No issue, validity or identifier evidence supplied.
    facts["status_profile"] = row["status_profile"]
    update_assignment_facts(test.user, test.org, test.assignment.pk, facts, expected_version=1)
    test.profiles = test.storage / "profiles"
    test.profiles.mkdir(mode=0o700)
    (test.profiles / "synthetic.json").write_text(json.dumps(synthetic_profile()))
    setting = override_settings(A1_DRAFT_PROFILE_ROOT=test.profiles)
    setting.enable()
    test.addCleanup(setting.disable)
    test.case = prepare_input_case(test.user, test.org, test.worker_id)


class A1DraftTests(TransactionTestCase):
    evaluation = a1_export_tests.A1ExportTests.evaluation
    draft = a1_export_tests.A1ExportTests.draft
    setUp = setup_draft
    batch = inbox_tests.InboxTests.batch
    write = inbox_tests.InboxTests.write
    run_inbox = inbox_tests.InboxTests.run_inbox

    def test_three_pages_retry_and_pending_status(self):
        generation = prepare_application_draft(self.user, self.org, self.case.pk)
        self.case.refresh_from_db()
        case = self.case
        first = dict(generation.artifact_reference)
        again = prepare_application_draft(self.user, self.org, case.pk)
        self.assertEqual(first, again.artifact_reference)
        reservation = A1DraftReservation.objects.get(case=case)
        self.assertRegex(reservation.document_id, r"^N00999S\d{3}/\d{4}/DE$")
        self.assertEqual(A1DraftReservation.objects.count(), 1)
        package = self.storage / "j4" / first["key"]
        self.assertEqual(len(list(package.glob("page-*.png"))), 3)
        self.assertEqual(len([p for p in (self.storage / "j4").iterdir() if p.is_dir()]), 1)
        self.assertEqual(case.readiness, "blocked")
        self.assertEqual(case.external_status, "not_submitted")
        self.assertFalse(case.visual_confirmed)
        self.assertFalse(WorkerIdentityRevision.objects.exists())
        self.assertEqual(reservation.snapshot["row"]["issue_date"], "")
        self.assertEqual(reservation.snapshot["row"]["start_date"], "")
        self.assertEqual(reservation.snapshot["row"]["validated_by_user"], "0")
        self.assertTrue(all(p.stat().st_mode & 0o077 == 0 for p in package.iterdir()))

    def test_failed_db_attachment_recovers_same_number_and_package(self):
        from portal.release1a.a1_drafts import audit as real_audit
        def fail_publication(user, org, event, ref):
            if event == "a1.draft_published":
                raise RuntimeError("Synthetic audit failure")
            return real_audit(user, org, event, ref)
        with patch("portal.release1a.a1_drafts.audit", side_effect=fail_publication):
            with self.assertRaises(RuntimeError):
                prepare_application_draft(self.user, self.org, self.case.pk)
        reservation = A1DraftReservation.objects.get()
        self.case.refresh_from_db()
        self.assertFalse(self.case.artifact_reference)
        result = prepare_application_draft(self.user, self.org, self.case.pk)
        self.assertEqual(result.artifact_reference["key"], reservation.package_key.hex)
        self.assertEqual(A1DraftReservation.objects.count(), 1)
        self.assertEqual(len([p for p in (self.storage / "j4").iterdir() if p.is_dir()]), 1)

    def test_missing_facts_and_stale_source_block(self):
        reservation = reserve_application_draft(self.user, self.org, self.case.pk)
        update_assignment_facts(self.user, self.org, self.assignment.pk, {}, expected_version=2)
        with self.assertRaises(StaleWrite):
            prepare_application_draft(self.user, self.org, self.case.pk)
        missing = prepare_input_case(self.user, self.org, self.worker_id)
        with self.assertRaises(DraftInputBlocked):
            reserve_application_draft(self.user, self.org, missing.pk)
        self.assertEqual(A1DraftReservation.objects.count(), 1)

    def test_authorization_and_reservation_integrity(self):
        with self.assertRaises(Forbidden):
            prepare_application_draft(self.user, self.other, self.case.pk)
        with override_settings(M2_SYNTHETIC_ONLY=False):
            with self.assertRaises(Forbidden):
                prepare_application_draft(self.user, self.org, self.case.pk)
        reservation = reserve_application_draft(self.user, self.org, self.case.pk)
        changed = reservation.snapshot
        changed["row"]["surname"] = "OTHER SYNTHETIC"
        A1DraftReservation.objects.filter(pk=reservation.pk).update(snapshot=changed)
        with self.assertRaisesRegex(StaleWrite, "CORRUPT"):
            prepare_application_draft(self.user, self.org, self.case.pk)

    def test_inbox_generates_eligible_draft_and_command_returns_existing_package(self):
        path, items = self.batch()
        items[0]["activity_profile"] = "self_employed"
        self.write(path / "ready.json", json.dumps({"organization_id": self.org.pk, "files": items}).encode())
        result = self.run_inbox()[0]
        self.assertEqual(result["status"], "completed")
        draft = result["drafts"][0]["a1_draft"]
        self.assertEqual(draft["status"], "unverified_draft")
        output = io.StringIO()
        call_command("a1_prepare_draft", case_id=draft["case_ref"], organization_id=self.org.pk,
                     actor_id=self.user.pk, stdout=output)
        report = json.loads(output.getvalue())
        self.assertEqual(Path(report["pdf"]).parent.name, draft["package_key"])
        self.assertTrue(Path(report["pdf"]).is_file())
        self.assertEqual(A1DraftReservation.objects.count(), 1)

    def test_changed_profile_creates_revision_preserving_number_and_old_package(self):
        first = prepare_application_draft(self.user, self.org, self.case.pk)
        old_pdf = (self.storage / "j4" / first.package_key.hex / "artifact.pdf").read_bytes()
        path = self.profiles / "synthetic.json"
        profile = synthetic_profile()
        profile["institution"]["house_number"] = "3"
        path.write_text(json.dumps(profile))
        second = prepare_application_draft(self.user, self.org, self.case.pk)
        self.assertEqual((first.revision, second.revision), (1, 2))
        self.assertEqual(first.reservation_id, second.reservation_id)
        self.assertEqual(first.snapshot["row"], second.snapshot["row"])
        self.assertNotEqual(first.package_key, second.package_key)
        self.assertNotEqual(first.prepared_artifact_hash, second.prepared_artifact_hash)
        self.assertEqual(old_pdf, (self.storage / "j4" / first.package_key.hex / "artifact.pdf").read_bytes())
        self.case.refresh_from_db()
        self.assertEqual(self.case.artifact_reference, first.artifact_reference)
        self.assertFalse(self.case.visual_confirmed)
        self.assertEqual(second.snapshot["visual_review"], "pending")
        self.assertEqual(second.snapshot["identity_verification"], "pending")
        self.assertEqual(prepare_application_draft(self.user, self.org, self.case.pk).pk, second.pk)
        path.write_text(json.dumps(synthetic_profile()))
        self.assertEqual(prepare_application_draft(self.user, self.org, self.case.pk).pk, first.pk)
        self.assertEqual(A1DraftGeneration.objects.count(), 2)

    def test_dependency_change_before_publish_rejects_old_generation_and_retry_recovers_new(self):
        first = reserve_application_generation(self.user, self.org, self.case.pk)
        from portal.release1a.a1_drafts import _dependencies, audit as real_audit
        def changed(*args):
            return dict(_dependencies(*args), build={"app_build_id": "synthetic-new-build"})
        def fail_publication(user, org, event, ref):
            if event == "a1.draft_published":
                raise RuntimeError("Synthetic audit failure")
            return real_audit(user, org, event, ref)
        with patch("portal.release1a.a1_drafts._dependencies", side_effect=changed):
            with self.assertRaisesRegex(StaleWrite, "DEPENDENCIES_CHANGED"):
                _publish_reserved(self.user, self.org, first.pk)
            with patch("portal.release1a.a1_drafts.audit", side_effect=fail_publication):
                with self.assertRaises(RuntimeError):
                    prepare_application_draft(self.user, self.org, self.case.pk)
            second = A1DraftGeneration.objects.get(revision=2)
            self.assertFalse(second.artifact_reference)
            result = prepare_application_draft(self.user, self.org, self.case.pk)
            self.assertEqual(result.pk, second.pk)
            self.assertEqual(result.package_key, second.package_key)
        self.assertEqual(A1DraftReservation.objects.count(), 1)
        self.assertEqual(A1DraftGeneration.objects.count(), 2)
        self.assertEqual(len([p for p in (self.storage / "j4").iterdir() if p.is_dir()]), 1)

    def test_generation_tampering_and_mutation_are_rejected(self):
        generation = reserve_application_generation(self.user, self.org, self.case.pk)
        generation.revision = 99
        with self.assertRaises(ValueError):
            generation.save()
        A1DraftGeneration.objects.filter(pk=generation.pk).update(snapshot_sha256="0" * 64)
        with self.assertRaisesRegex(StaleWrite, "GENERATION_CORRUPT"):
            prepare_application_draft(self.user, self.org, self.case.pk)

    def test_complete_input_operator_journey_preserves_review_and_retry(self):
        """Complete synthetic fixture is a precondition, not proof of cold-start mapping."""
        from tests.test_j4_minimum import _mfa_login
        from portal.release1a.identity_review import association_review_context
        from portal.release1a.field_review import review_context
        from portal.release1a.models import Worker, OcrRun, FieldDecision, AuditEvent
        from zipfile import ZipFile
        self.user.set_password('test-m2'); self.user.save()
        _mfa_login(self.client, self.user)
        url = f'/documents/{self.run.document_id}/'
        options = association_review_context(self.user, self.org, [self.run.pk])[
            (self.run.pk, self.region)]['worker_options']
        token = next(o['token'] for o in options if o['worker'].pk == self.worker_id)
        self.assertEqual(self.client.post(url, {'action':'associate', 'worker_choice':token,
            'reason':'Synthetic source reviewed'}).status_code, 302)
        proposal = FieldProposal.objects.get(ocr_run=self.run, field_name='sex')
        token = review_context(self.user, self.org, [proposal.pk])[proposal.pk]['token']
        review = {'action':'confirm', f'confirm_{proposal.pk}':'on',
                  f'value_sex_{proposal.pk}':proposal.proposed_value, f'expected_{proposal.pk}':token}
        self.assertEqual(self.client.post(url, review).status_code, 302)
        self.assertEqual(self.client.post(url, review).status_code, 409)
        path, items = self.batch()
        items[0]['activity_profile'] = 'self_employed'
        self.write(path/'ready.json', json.dumps({'organization_id':self.org.pk, 'files':items}).encode())
        first = self.run_inbox()[0]
        draft = first['drafts'][0]['a1_draft']
        self.assertEqual(draft['status'], 'unverified_draft')
        case = A1Case.objects.get(pk=draft['case_ref'])
        generation = A1DraftGeneration.objects.get(reservation__case=case)
        base = f'/a1/{case.pk}/'
        self.assertEqual(self.client.get(base+f'artifact/?generation={generation.pk}').status_code, 200)
        for page in (1,2,3):
            self.assertEqual(self.client.get(base+f'preview/{page}/?generation={generation.pk}').status_code, 200)
        response = self.client.post('/a1/inputs/', {'selection':[f'{case.pk}:{case.source_hash}']})
        self.assertEqual(response.status_code, 200)
        digest = AuditEvent.objects.filter(event_type='a1.input_bundle_published').latest('pk').object_ref.split(':')[1]
        download = self.client.get(base+f'inputs/{digest}/download/')
        self.assertEqual(download.status_code, 200)
        with ZipFile(io.BytesIO(download.content)) as archive:
            snapshots = json.loads(archive.read('input_snapshots.json'))['snapshots']
            self.assertEqual(snapshots[0], case.source_snapshot_json)
            row = snapshots[0]['row']
            self.assertEqual((row['activity_name'], row['activity_address']), ('', 'DE, CZ'))
            self.assertEqual(row['validated_by_user'], '0')
            self.assertEqual(row['identity_reviewed'], 'NO')
        counts = (Worker.objects.count(), OcrRun.objects.count(), FieldDecision.objects.count(),
                  A1DraftGeneration.objects.count())
        again = self.run_inbox()[0]
        self.assertEqual(again['drafts'][0]['a1_draft']['package_key'], draft['package_key'])
        self.assertEqual(counts, (Worker.objects.count(), OcrRun.objects.count(),
            FieldDecision.objects.count(), A1DraftGeneration.objects.count()))
        self.assertEqual(WorkerIdentityRevision.objects.latest('pk').confirmed_fields['sex'], 'M')
        self.assertFalse(case.visual_confirmed)
        self.assertEqual(case.external_status, 'not_submitted')
