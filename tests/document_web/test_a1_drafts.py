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
from portal.release1a.a1_drafts import prepare_application_draft, reserve_application_draft, DraftInputBlocked
from portal.release1a.models import A1Case, A1DraftReservation, FieldProposal, WorkerIdentityRevision
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
        case = prepare_application_draft(self.user, self.org, self.case.pk)
        first = dict(case.artifact_reference)
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

    def test_missing_facts_stale_source_and_changed_profile_block(self):
        reservation = reserve_application_draft(self.user, self.org, self.case.pk)
        path = self.profiles / "synthetic.json"
        profile = synthetic_profile()
        profile["institution"]["house_number"] = "3"
        path.write_text(json.dumps(profile))
        with self.assertRaises(StaleWrite):
            prepare_application_draft(self.user, self.org, self.case.pk)
        self.assertFalse((self.storage / "j4").exists())
        path.write_text(json.dumps(synthetic_profile()))
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
