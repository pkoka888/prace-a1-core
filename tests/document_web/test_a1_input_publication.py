"""Synthetic profile-bound input publication through canonical services and CLI."""
import hashlib
import io
import json
from unittest.mock import patch
from django.core.management import call_command, CommandError
from django.test import TransactionTestCase
from . import test_a1_drafts as draft_fixtures
from portal.release1a.a1_exports import publish_input_cohort
from portal.release1a.models import AuditEvent, Worker
from portal.release1a.services import Forbidden, StaleWrite


class InputPublicationTests(TransactionTestCase):
    setUp=draft_fixtures.setup_draft
    evaluation=draft_fixtures.A1DraftTests.evaluation
    draft=draft_fixtures.A1DraftTests.draft

    def publish(self):
        return publish_input_cohort(self.user,self.org,[{'case_id':self.case.pk,'expected_source_hash':self.case.source_hash}])

    def test_profile_bytes_hashes_and_retry_through_cli(self):
        first=self.publish()
        self.assertEqual(first,self.publish())
        directory=self.storage/first['relative_path']
        raw=(directory/'manifest.json').read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),first['manifest_sha256'])
        manifest=json.loads(raw)
        self.assertEqual((directory/'profiles/synthetic.json').read_bytes(),(self.profiles/'synthetic.json').read_bytes())
        for name,digest in manifest['payload_sha256'].items():
            self.assertEqual(hashlib.sha256((directory/name).read_bytes()).hexdigest(),digest)
        out=io.StringIO()
        call_command('a1_export_inputs',case=[f'{self.case.pk}:{self.case.source_hash}'],organization_id=self.org.pk,actor_id=self.user.pk,stdout=out)
        self.assertEqual(json.loads(out.getvalue())['relative_path'],first['relative_path'])
        self.assertEqual(json.loads((directory/'cohort.json').read_text())['document_ids'][self.case.source_snapshot_json['employee_id']],'')

    def test_profile_changes_create_new_package_and_tampering_is_rejected(self):
        first=self.publish()
        profile=self.profiles/'synthetic.json'
        data=json.loads(profile.read_text());data['version']='synthetic-next';profile.write_text(json.dumps(data))
        second=self.publish()
        self.assertNotEqual(first['relative_path'],second['relative_path'])
        self.assertTrue((self.storage/first['relative_path']/'manifest.json').exists())
        target=self.storage/second['relative_path']/'review.csv'
        target.write_bytes(b'corrupt')
        with self.assertRaises(ValueError): self.publish()
        self.assertEqual(target.read_bytes(),b'corrupt')

    def test_stale_or_unauthorized_and_invalid_profile_do_not_publish(self):
        with self.assertRaises(Forbidden):
            publish_input_cohort(self.user,self.other,[{'case_id':self.case.pk,'expected_source_hash':self.case.source_hash}])
        profile=self.profiles/'synthetic.json';data=json.loads(profile.read_text())
        profile.write_text(json.dumps({**data,'review_status':'PROVISIONAL'}))
        with self.assertRaises(ValueError): self.publish()
        self.assertFalse((self.storage/'a1-input').exists())
        profile.write_text(json.dumps(data))
        Worker.objects.filter(pk=self.case.worker_id).update(version=99)
        with self.assertRaises(StaleWrite): self.publish()
        with self.assertRaises(CommandError):
            call_command('a1_export_inputs',case=[f'{self.case.pk}:{self.case.source_hash}'],organization_id=self.org.pk,actor_id=self.user.pk,stdout=io.StringIO())
        self.assertFalse((self.storage/'a1-input').exists())

    def test_late_audit_failure_recovers_existing_package_on_retry(self):
        from portal.release1a import a1_exports
        original=a1_exports.audit
        def fail(user,org,event,reference):
            if event=='a1.input_bundle_published': raise RuntimeError('Synthetic audit failure')
            return original(user,org,event,reference)
        with patch.object(a1_exports,'audit',side_effect=fail),self.assertRaises(RuntimeError): self.publish()
        self.assertFalse(AuditEvent.objects.filter(event_type='a1.input_bundle_published').exists())
        folders=list((self.storage/'a1-input').glob('[0-9a-f]'*64))
        self.assertEqual(len(folders),1)
        result=self.publish()
        self.assertEqual(self.storage/result['relative_path'],folders[0])

    def test_profile_edit_during_publication_rejects_stale_result(self):
        from portal.release1a import input_artifacts
        original=input_artifacts.publish_input_artifact
        def changed(root,payloads):
            result=original(root,payloads)
            path=self.profiles/'synthetic.json'
            profile=json.loads(path.read_text());profile['version']='changed-mid-publication'
            path.write_text(json.dumps(profile))
            return result
        with patch.object(input_artifacts,'publish_input_artifact',side_effect=changed),self.assertRaises(StaleWrite):
            self.publish()
        self.assertFalse(AuditEvent.objects.filter(event_type='a1.input_bundle_published').exists())
        self.publish()
        self.assertEqual(len(list((self.storage/'a1-input').glob('[0-9a-f]'*64))),2)

    def test_missing_or_symlinked_profile_keeps_unbound_export_available(self):
        from portal.release1a.a1_exports import export_input_cohort
        profile=self.profiles/'synthetic.json'
        data=profile.read_bytes();profile.unlink()
        with self.assertRaises(OSError): self.publish()
        self.assertIn('review.csv',export_input_cohort(self.user,self.org,[{
            'case_id':self.case.pk,'expected_source_hash':self.case.source_hash}]))
        other=self.profiles/'other.json';other.write_bytes(data);profile.symlink_to(other)
        with self.assertRaises(OSError): self.publish()
        self.assertFalse((self.storage/'a1-input').exists())
