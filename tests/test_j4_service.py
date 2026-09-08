"""Run using Django's isolated settings_document_tests database."""
import json
import tempfile
from datetime import date
from pathlib import Path

from allauth.mfa.models import Authenticator
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase, override_settings

from portal.release1a.models import Organization, Membership, Worker, A1Case
from portal.release1a.services import prepare_a1, attach_a1_artifact, Forbidden, StaleWrite
from portal.release1a.j4_artifacts import verify_artifact
from tests.test_finalize_a1 import employee, review_row


class J4ServiceTests(TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="j4-service-synthetic-", dir=settings.BASE_DIR / "runtime/portal")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        config = override_settings(DOCUMENT_STORAGE_ROOT=self.root)
        config.enable()
        self.addCleanup(config.disable)
        self.org = Organization.objects.create(key="j4-synthetic", label="Synthetic")
        self.user = get_user_model().objects.create_user("j4-synthetic")
        self.membership = Membership.objects.create(user=self.user, organization=self.org, role="organization_admin")
        Authenticator.objects.create(user=self.user, type=Authenticator.Type.TOTP, data={"secret": "JBSWY3DPEHPK3PXP"})
        self.worker = Worker.objects.create(organization=self.org, given_name="ANNA", family_name="TESTOVA", birth_date=date(1990, 2, 1), activity_profile="self_employed")
        self.case = prepare_a1(self.user, self.org, self.worker)
        source = employee("synthetic", "TESTOVA", "ANNA", "01.02.1990", "900201/1234")
        self.rows = [review_row(source, "SYNTHETIC-DOC")]
        self.employees = self.root / "employees.json"
        self.employees.write_text(json.dumps({"employees": [source]}))
        self.profiles = self.root / "profiles"
        self.profiles.mkdir()
        (self.profiles / "teplice-test.json").write_text(json.dumps({"version": "test", "review_status": "VERIFIED", "source_url": "https://example.invalid/official-institution-record", "verified_on": "01.01.2026", "expected_ossz": "OSSZ Teplice", "institution": {"name": "TEST OSSZ Teplice", "street": "Synthetic", "house_number": "1", "city": "Teplice", "postal_code": "415 02", "country_code": "CZ", "code": "TEST"}}))

    def attach(self):
        return attach_a1_artifact(self.user, self.org, self.case.pk, expected_source_hash=self.case.source_hash,
                                  employee_id="synthetic", rows=self.rows, employees_path=self.employees, profile_dir=self.profiles)

    def test_canonical_bundle_persisted_and_cannot_replace(self):
        self.assertEqual(self.case.prepared_artifact_hash, "")
        case = self.attach()
        case.refresh_from_db()
        self.assertEqual(case.prepared_artifact_hash, case.artifact_reference["pdf_sha256"])
        self.assertEqual(verify_artifact(self.root / "j4", case.artifact_reference, case.artifact_dependencies), {"integrity": "verified", "stale": False})
        with self.assertRaises(StaleWrite):
            self.attach()

    def test_snapshot_cannot_be_replaced(self):
        self.case.source_snapshot_json = {"replacement": True}
        with self.assertRaisesRegex(ValueError, "A1_SNAPSHOT_IMMUTABLE"):
            self.case.save()

    def test_changed_current_worker_is_rejected(self):
        Worker.objects.filter(pk=self.worker.pk).update(given_name="CHANGED SYNTHETIC")
        with self.assertRaises(StaleWrite):
            self.attach()
        self.assertFalse((self.root / "j4").exists())

    def test_planner_cannot_attach_authoritative_artifact(self):
        self.membership.role = "jan_planner"
        self.membership.save()
        with self.assertRaises(Forbidden):
            self.attach()

    def test_missing_authoritative_evidence_blocks_render(self):
        from scripts.finalize_a1 import FinalizationError
        self.rows[0]["validated_by_user"] = "0"
        with self.assertRaises(FinalizationError):
            self.attach()
        self.assertFalse((self.root / "j4").exists())


class J4MigrationTests(TransactionTestCase):
    def test_historical_0010_to_0011_preserves_snapshot(self):
        before = [("release1a", "0010_a1case_j4_minimum")]
        after = [("release1a", "0011_a1case_artifact_evidence")]
        executor = MigrationExecutor(connection)
        executor.migrate(before)
        try:
            apps = executor.loader.project_state(before).apps
            org = apps.get_model("release1a", "Organization").objects.create(key="historical-j4", label="Synthetic")
            worker = apps.get_model("release1a", "Worker").objects.create(organization_id=org.pk, given_name="Synthetic", family_name="Fixture", birth_date=date(1990, 1, 1), activity_profile="employee")
            case = apps.get_model("release1a", "A1Case").objects.create(organization_id=org.pk, worker_id=worker.pk, source_hash="a" * 64, source_snapshot_json={"synthetic": True}, readiness="blocked")
            executor = MigrationExecutor(connection)
            executor.migrate(after)
            migrated = executor.loader.project_state(after).apps.get_model("release1a", "A1Case").objects.get(pk=case.pk)
            self.assertEqual(migrated.source_snapshot_json, {"synthetic": True})
            self.assertEqual(migrated.artifact_reference, {})
            self.assertEqual(migrated.artifact_dependencies, {})
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())
