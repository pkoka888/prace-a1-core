"""Synthetic A1 input snapshots; no PDF rendering or private operational inputs."""
import csv
import io
import json
from unittest.mock import patch
from django.test import TransactionTestCase, override_settings
from scripts.finalize_a1 import CSV_FIELDS
from portal.release1a.a1_exports import prepare_input_case, export_input_case, update_assignment_facts
from portal.release1a.document_intake import associate_region, supersede
from portal.release1a.models import A1Case, Assignment, WorkerIdentityRevision, FieldProposal
from portal.release1a.services import Forbidden, StaleWrite, confirm_field_proposal, current_a1_source
from . import test_identity as identity_tests
from . import test_inbox as inbox_tests
from tests.test_document_core.helpers import OP, card, png


class A1ExportTests(TransactionTestCase):
    setUp = inbox_tests.InboxTests.setUp
    evaluation = identity_tests.IdentityTests.evaluation
    draft = identity_tests.IdentityTests.draft

    def inputs(self, profile="self_employed"):
        evaluation, run, region = self.evaluation()
        result = self.draft(evaluation, run, region, profile)
        self.worker_id, self.claim_id, self.run, self.region = result["worker_ref"], result["claim_ref"], run, region
        self.assignment = Assignment.objects.create(organization=self.org, worker_id=self.worker_id,
            start="2026-09-01", end="2026-12-31", workplace_label="Synthetic workplace", activity_label="Synthetic role")
        return self.assignment

    def prepare(self):
        return prepare_input_case(self.user, self.org, self.worker_id)

    def test_snapshot_exports_all_columns_pending_flags_and_stable_case(self):
        self.inputs()
        case = self.prepare()
        self.assertEqual(case.pk, self.prepare().pk)
        exported = export_input_case(self.user, self.org, case.pk)
        rows = list(csv.DictReader(io.StringIO(exported["csv"].decode())))
        self.assertEqual(tuple(rows[0]), CSV_FIELDS)
        self.assertEqual(rows[0]["surname"], "TESTOVA")
        self.assertEqual(rows[0]["dob"], "15.03.1990")
        self.assertEqual(rows[0]["validated_by_user"], "0")
        self.assertEqual(rows[0]["identity_reviewed"], "NO")
        self.assertEqual(rows[0]["document_id"], "")
        self.assertEqual(rows[0]["start_date"], "")  # Assignment dates are not certificate dates.
        self.assertEqual(rows[0]["issue_date"], "")
        self.assertEqual(rows[0]["employment_name"], "")
        snapshot = json.loads(exported["json"])
        self.assertEqual(set(snapshot["provenance"]), set(CSV_FIELDS))
        self.assertEqual(snapshot["provenance"]["surname"]["kind"], "ocr_proposal")
        self.assertEqual(case.readiness, "blocked")
        self.assertEqual(case.external_status, "not_submitted")
        self.assertFalse(case.artifact_reference)
        self.assertFalse(case.visual_confirmed)
        self.assertFalse(WorkerIdentityRevision.objects.exists())

    def test_explicit_facts_section5_defaults_and_override_without_approval(self):
        assignment = self.inputs()
        assignment = update_assignment_facts(self.user, self.org, assignment.pk,
            {"status_profile": "self_employed_multi_state", "certificate": {"start_date": "2026-09-08"}}, expected_version=1)
        case = self.prepare()
        row = case.source_snapshot_json["row"]
        self.assertEqual((row["activity_name"], row["activity_address"]), ("", "DE, CZ"))
        self.assertEqual(row["start_date"], "08.09.2026")
        self.assertEqual(row["certificate_source_status"], "UNVERIFIED")
        update_assignment_facts(self.user, self.org, assignment.pk,
            {"status_profile": "self_employed_multi_state", "activity": {"address": "DE, CZ, AT"}}, expected_version=2)
        with self.assertRaises(StaleWrite):
            export_input_case(self.user, self.org, case.pk)
        new = self.prepare()
        self.assertNotEqual(case.pk, new.pk)
        self.assertEqual(new.source_snapshot_json["row"]["activity_address"], "DE, CZ, AT")
        case.refresh_from_db()
        self.assertEqual(case.source_snapshot_json["row"]["activity_address"], "DE, CZ")

    def test_confirmed_revision_wins_without_whole_identity_acceptance(self):
        self.inputs()
        before = self.prepare()
        associate_region(self.user, self.org, self.run.pk, self.region, self.assignment.worker)
        confirm_field_proposal(self.user, self.org, FieldProposal.objects.get(ocr_run=self.run, field_name="given_name"),
                               corrected_value="BETA")
        with self.assertRaises(StaleWrite):
            export_input_case(self.user, self.org, before.pk)
        current = self.prepare().source_snapshot_json
        self.assertEqual(current["row"]["given_name"], "BETA")
        self.assertEqual(current["row"]["identity_reviewed"], "NO")
        self.assertEqual(current["provenance"]["given_name"]["kind"], "confirmed_revision")
        self.assertEqual(current["provenance"]["given_name"]["actor_ref"], self.user.pk)

    def test_selection_scope_and_corruption_fail_closed(self):
        self.inputs()
        case = self.prepare()
        Assignment.objects.create(organization=self.org, worker_id=self.worker_id, start="2027-01-01", end="2027-02-01",
                                  workplace_label="Synthetic second", activity_label="Synthetic")
        with self.assertRaisesRegex(ValueError, "SELECTION_REQUIRED"):
            self.prepare()
        self.assertEqual(prepare_input_case(self.user, self.org, self.worker_id, assignment_id=self.assignment.pk).pk, case.pk)
        with self.assertRaises(Forbidden):
            export_input_case(self.user, self.other, case.pk)
        with override_settings(M2_SYNTHETIC_ONLY=False):
            with self.assertRaises(Forbidden):
                self.prepare()
        A1Case.objects.filter(pk=case.pk).update(source_snapshot_json={})
        with self.assertRaisesRegex(ValueError, "CORRUPT"):
            export_input_case(self.user, self.org, case.pk)

    def test_facts_cannot_supply_flags_and_stale_updates_and_audit_rollback(self):
        assignment = self.inputs()
        with self.assertRaisesRegex(ValueError, "FIELDS_INVALID"):
            update_assignment_facts(self.user, self.org, assignment.pk, {"validated_by_user": "1"}, expected_version=1)
        with patch("portal.release1a.a1_exports.audit", side_effect=RuntimeError("Synthetic failure")):
            with self.assertRaises(RuntimeError):
                update_assignment_facts(self.user, self.org, assignment.pk, {"status_profile": "self_employed_multi_state"}, expected_version=1)
        assignment.refresh_from_db()
        self.assertEqual(assignment.version, 1)
        self.assertEqual(assignment.a1_facts_json, {})
        with self.assertRaises(StaleWrite):
            update_assignment_facts(self.user, self.org, assignment.pk, {}, expected_version=0)

    def test_changed_facts_without_version_bump_and_replaced_source_are_detected(self):
        self.inputs()
        case = self.prepare()
        previous = current_a1_source(self.assignment.worker, self.org)[2]
        Assignment.objects.filter(pk=self.assignment.pk).update(a1_facts_json={"status_profile": "self_employed_multi_state"})
        self.assertNotEqual(current_a1_source(self.assignment.worker, self.org)[2], previous)
        with self.assertRaises(StaleWrite):
            export_input_case(self.user, self.org, case.pk)
        case = self.prepare()
        supersede(self.user, self.org, self.run.document_id, "replacement.png", "image/png",
                  png(card(OP + ["SYNTHETIC REPLACEMENT"])), processor=inbox_tests.processor())
        with self.assertRaisesRegex(ValueError, "SOURCE_STALE"):
            export_input_case(self.user, self.org, case.pk)

    def test_unchanged_selected_input_can_be_revalidated_after_conservative_invalidation(self):
        self.inputs()
        case = self.prepare()
        A1Case.objects.filter(pk=case.pk).update(is_stale=True)
        with self.assertRaises(StaleWrite):
            export_input_case(self.user, self.org, case.pk)
        refreshed = self.prepare()
        self.assertEqual(refreshed.pk, case.pk)
        self.assertFalse(refreshed.is_stale)
        self.assertTrue(export_input_case(self.user, self.org, case.pk)["csv"])

    def test_assignment_period_change_invalidates_without_becoming_certificate_dates(self):
        self.inputs()
        case = self.prepare()
        Assignment.objects.filter(pk=self.assignment.pk).update(end="2027-01-01")
        with self.assertRaises(StaleWrite):
            export_input_case(self.user, self.org, case.pk)
        self.assertEqual(self.prepare().source_snapshot_json["row"]["end_date"], "")

    def test_invalid_pending_date_is_a_blocker_and_confirmed_revision_wins(self):
        self.inputs()
        proposal = FieldProposal.objects.get(ocr_run=self.run, field_name="birth_date")
        FieldProposal.objects.filter(pk=proposal.pk).update(proposed_value="not-a-date")
        self.assertIn("conflict:dob", self.prepare().source_snapshot_json["blockers"])
        proposal.refresh_from_db()
        associate_region(self.user, self.org, self.run.pk, self.region, self.assignment.worker)
        confirm_field_proposal(self.user, self.org, proposal, corrected_value="1990-03-15")
        current = self.prepare().source_snapshot_json
        self.assertNotIn("conflict:dob", current["blockers"])
        self.assertEqual(current["row"]["dob"], "15.03.1990")
        self.assertEqual(current["provenance"]["dob"]["kind"], "confirmed_revision")

    def facts_bo(self):
        from tests.test_j4_minimum import _mfa_login
        self.inputs()
        self.user.set_password('test-m2'); self.user.save(); _mfa_login(self.client,self.user)
        return f'/workers/{self.worker_id}/assignments/{self.assignment.pk}/a1-inputs/'

    def facts_post(self):
        from portal.release1a.assignment_facts import FIELDS
        return {'version':self.assignment.version,'status_profile':'self_employed_multi_state',
            **{f'{group}__{field}':'' for group,fields in FIELDS.items() for field in fields}}

    def test_bo_assignment_facts_preserve_evidence_and_canonical_defaults(self):
        from portal.release1a.models import AuditEvent
        url=self.facts_bo()
        self.assignment.a1_facts_json={'certificate':{'document_id':'SYNTHETIC-REF'},
            'institution':{'signed_by':'Synthetic evidence','issue_date':'2026-09-01'}}
        self.assignment.save()
        before=self.prepare()
        self.assertContains(self.client.get(url),'name="employment__employer_id"')
        self.assertFalse(AuditEvent.objects.filter(event_type='a1.assignment_facts_updated').exists())
        post=self.facts_post(); post['employment__employer_id']='SYNTHETIC-123'
        post['certificate__document_id']='INJECTED'
        self.assertEqual(self.client.post(url,post).status_code,302)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.a1_facts_json['certificate']['document_id'],'SYNTHETIC-REF')
        self.assertEqual(self.assignment.a1_facts_json['institution']['signed_by'],'Synthetic evidence')
        self.assertEqual(self.assignment.version,2)
        before.refresh_from_db(); self.assertTrue(before.is_stale)
        row=self.prepare().source_snapshot_json['row']
        self.assertEqual((row['activity_name'],row['activity_address']),('','DE, CZ'))
        self.assertEqual(row['employment_id'],'SYNTHETIC-123')
        self.assertEqual(row['validated_by_user'],'0')
        self.assertEqual(self.client.post(url,post).status_code,409)
        post['version']=2; post['activity__address']='DE, CZ, AT'
        self.assertEqual(self.client.post(url,post).status_code,302)
        self.assertEqual(self.prepare().source_snapshot_json['row']['activity_address'],'DE, CZ, AT')

    def test_bo_assignment_facts_scope_csrf_invalid_and_missing_fields(self):
        from django.test import Client
        from tests.test_j4_minimum import _mfa_login
        from portal.release1a.models import Membership
        url=self.facts_bo(); post=self.facts_post()
        self.assertEqual(self.client.post(url,{'version':1}).status_code,400)
        self.assertEqual(self.client.post(url,dict(post,version=[1,1])).status_code,400)
        csrf=Client(enforce_csrf_checks=True); _mfa_login(csrf,self.user)
        self.assertEqual(csrf.post(url,post).status_code,403)
        bad=dict(post,status_profile='unsupported')
        self.assertEqual(self.client.post(url,bad).status_code,200)
        self.assignment.refresh_from_db(); self.assertEqual(self.assignment.version,1)
        Membership.objects.filter(user=self.user).update(role='privacy_admin')
        self.assertEqual(self.client.get(url).status_code,403)
        self.assertEqual(self.client.post(url,post).status_code,403)
        Membership.objects.filter(user=self.user).update(role='organization_admin',organization=self.other)
        self.assertEqual(self.client.get(url).status_code,404)
        Membership.objects.filter(user=self.user).update(organization=self.org)
        with override_settings(M2_SYNTHETIC_ONLY=False): self.assertEqual(self.client.get(url).status_code,403)

    def test_assignment_editor_rejects_old_version_without_overwriting_facts(self):
        self.facts_bo()
        update_assignment_facts(self.user,self.org,self.assignment.pk,
            {'employment':{'employer_id':'SYNTHETIC-NEW'}},expected_version=1)
        url=f'/workers/{self.worker_id}/assignments/{self.assignment.pk}/edit/'
        post={'version':1,'workplace_label':'Synthetic edit','activity_label':'Synthetic',
              'start':'2026-09-01','end':'2026-12-31','state':'planned'}
        self.assertEqual(self.client.post(url,post).status_code,200)
        self.assignment.refresh_from_db(); self.assertEqual(self.assignment.version,2)
        post['version']=2
        self.assertEqual(self.client.post(url,post).status_code,302)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.a1_facts_json['employment']['employer_id'],'SYNTHETIC-NEW')
        self.assertEqual(self.assignment.version,3)

    def test_assignment_editor_audit_failure_rolls_back_update(self):
        self.facts_bo()
        url=f'/workers/{self.worker_id}/assignments/{self.assignment.pk}/edit/'
        post={'version':1,'workplace_label':'Synthetic edit','activity_label':'Synthetic',
              'start':'2026-09-01','end':'2026-12-31','state':'planned'}
        with patch('portal.release1a.views.AuditEvent.objects.create',side_effect=RuntimeError('Synthetic audit failure')):
            self.assertEqual(self.client.post(url,post).status_code,200)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.version,1)
        self.assertEqual(self.assignment.workplace_label,'Synthetic workplace')

    def test_profile_choices_exclude_unverified_files_but_preserve_existing_selection(self):
        from portal.release1a.assignment_facts import profile_choices
        from tests.test_a1_application_draft import synthetic_profile
        directory=self.storage/'profiles'; directory.mkdir(mode=0o700)
        (directory/'synthetic.json').write_text(json.dumps(synthetic_profile()))
        (directory/'pending.json').write_text(json.dumps(dict(synthetic_profile(),review_status='PROVISIONAL')))
        (directory/'alias.json').symlink_to(directory/'synthetic.json')
        (directory/'invalid.json').write_text('[]')
        (directory/'null.json').write_text('null')
        (directory/'bad-date.json').write_text(json.dumps(dict(synthetic_profile(),verified_on=7)))
        (directory/'bad-institution.json').write_text(json.dumps(dict(synthetic_profile(),institution=[])))
        with override_settings(A1_DRAFT_PROFILE_ROOT=directory):
            choices=dict(profile_choices('unavailable'))
        self.assertIn('synthetic',choices)
        self.assertIn('unavailable',choices)
        self.assertNotIn('pending',choices)
        self.assertNotIn('alias',choices)
        for key in ('invalid','null','bad-institution','bad-date'): self.assertNotIn(key,choices)
