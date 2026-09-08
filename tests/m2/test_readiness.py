"""Dependency probe contracts using isolated fixtures; never a service database."""
from unittest.mock import MagicMock, patch
from django.db import OperationalError, connections
from django.test import SimpleTestCase, TransactionTestCase, override_settings
from django.db.migrations.exceptions import InconsistentMigrationHistory


def _check(response, name):
    """Return the per-check dict with the matching name from /readiness/."""
    body = response.json()
    for entry in body.get("checks", []):
        if entry["name"] == name:
            return entry
    raise AssertionError(
        f"check {name!r} missing in response: {body!r}"
    )


class ReadinessContracts(SimpleTestCase):
    def setUp(self):
        self.cursor_patch = patch.object(connections['default'], 'cursor')
        self.cursor = self.cursor_patch.start()
        self.addCleanup(self.cursor_patch.stop)
        self.cursor.return_value.__enter__.return_value.fetchone.return_value = (1,)
        self.executor_patch = patch('django.db.migrations.executor.MigrationExecutor')
        self.executor_factory = self.executor_patch.start()
        self.addCleanup(self.executor_patch.stop)
        self.executor = self.executor_factory.return_value
        self.targets = [('release1a', '0009_document_region_association'), ('sessions', '0001_initial')]
        self.executor.loader.graph.leaf_nodes.return_value = self.targets
        self.executor.loader.detect_conflicts.return_value = {}
        self.executor.migration_plan.return_value = []

    def test_liveness_does_not_query_dependencies(self):
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['status'], 'synthetic-m2')
        self.assertEqual(body['real_data'], False)
        # Synthetic posture always surfaced
        self.assertIn('mode', body)
        self.assertIn('supervised', body)
        self.assertIn('build_id', body)
        self.assertIn('git_commit', body)
        self.cursor.assert_not_called()
        self.executor_factory.assert_not_called()

    def test_current_history_checks_all_apps_without_writing(self):
        response = self.client.get('/readiness/')
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['status'], 'ready')
        self.assertEqual(body['migrations'], 'current')
        self.assertEqual(body['budget_ms'], 2000)
        self.assertGreaterEqual(body['elapsed_ms'], 0)
        # All named checks present and ok
        for name in (
            'apps_loaded', 'csrf_confined', 'runtime_paths',
            'storage_writable', 'release_manifest',
            'db_reachable', 'migrations_current',
        ):
            entry = _check(response, name)
            self.assertEqual(entry['status'], 'ok', f"{name}={entry}")
        self.executor.migration_plan.assert_called_once_with(self.targets)
        self.executor.loader.check_consistent_history.assert_called_once()
        self.executor.migrate.assert_not_called()
        self.assertIn('no-store', response.headers['Cache-Control'])

    def test_pending_non_release_app_is_not_ready(self):
        self.executor.migration_plan.return_value = [(MagicMock(app_label='sessions'), False)]
        response = self.client.get('/readiness/')
        self.assertEqual(response.status_code, 503)
        body = response.json()
        self.assertEqual(body['status'], 'not_ready')
        self.assertEqual(body['reason'], 'check_failed')
        self.assertEqual(_check(response, 'migrations_current')['status'], 'fail')
        self.assertEqual(_check(response, 'migrations_current')['detail'], 'pending_migrations')
        self.executor.migrate.assert_not_called()

    def test_database_failure_is_sanitized(self):
        self.cursor.side_effect = OperationalError('synthetic secret/path/identifier')
        response = self.client.get('/readiness/')
        self.assertEqual(response.status_code, 503)
        body = response.json()
        self.assertEqual(body['status'], 'not_ready')
        self.assertEqual(body['reason'], 'check_failed')
        # db_reachable fails first; no exception detail leaks
        entry = _check(response, 'db_reachable')
        self.assertEqual(entry['status'], 'fail')
        self.assertEqual(entry['detail'], 'database_unavailable')
        self.assertNotIn('synthetic secret', body['reason'])
        self.assertNotIn('secret/path', str(body))
        self.executor_factory.assert_not_called()
        self.assertIn('no-store', response.headers['Cache-Control'])

    def test_invalid_database_response_is_not_ready(self):
        self.cursor.return_value.__enter__.return_value.fetchone.return_value = None
        response = self.client.get('/readiness/')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['status'], 'not_ready')

    def test_inconsistent_history_is_sanitized(self):
        self.executor.loader.check_consistent_history.side_effect = InconsistentMigrationHistory('synthetic details')
        response = self.client.get('/readiness/')
        self.assertEqual(response.status_code, 503)
        body = response.json()
        self.assertEqual(body['reason'], 'check_failed')
        self.assertEqual(_check(response, 'migrations_current')['status'], 'fail')
        self.assertEqual(_check(response, 'migrations_current')['detail'], 'migration_check_failed')
        self.assertNotIn('synthetic details', str(body))

    def test_conflicting_migrations_are_not_ready(self):
        self.executor.loader.detect_conflicts.return_value = {'sessions':['one','two']}
        response = self.client.get('/readiness/')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(_check(response, 'migrations_current')['detail'], 'migration_check_failed')

    def test_plan_loading_error_is_sanitized(self):
        self.executor_factory.side_effect = RuntimeError('synthetic internal path')
        response = self.client.get('/readiness/')
        self.assertEqual(response.status_code, 503)
        body = response.json()
        self.assertEqual(body['reason'], 'check_failed')
        self.assertNotIn('synthetic internal', str(body))

    def test_unsafe_method_does_not_query_database(self):
        self.assertEqual(self.client.post('/readiness/').status_code, 405)
        self.cursor.assert_not_called()
        self.executor_factory.assert_not_called()

    def test_response_includes_per_check_elapsed(self):
        response = self.client.get('/readiness/')
        for entry in response.json()['checks']:
            self.assertIsInstance(entry['elapsed_ms'], int)
            self.assertGreaterEqual(entry['elapsed_ms'], 0)
            self.assertIn('name', entry)
            self.assertIn('status', entry)
            self.assertIn('detail', entry)


class ReadinessBoundedBudget(SimpleTestCase):
    """Budget enforcement: per-check + total budget."""

    def setUp(self):
        self.cursor_patch = patch.object(connections['default'], 'cursor')
        self.cursor = self.cursor_patch.start()
        self.addCleanup(self.cursor_patch.stop)
        self.cursor.return_value.__enter__.return_value.fetchone.return_value = (1,)
        self.executor_patch = patch('django.db.migrations.executor.MigrationExecutor')
        self.executor_factory = self.executor_patch.start()
        self.addCleanup(self.executor_patch.stop)
        self.executor = self.executor_factory.return_value
        self.executor.loader.graph.leaf_nodes.return_value = []
        self.executor.loader.detect_conflicts.return_value = {}
        self.executor.migration_plan.return_value = []

    def test_late_legacy_test_results_are_not_ready(self):
        import time
        with override_settings(PRACE_READINESS_BUDGET_MS=1), patch(
            'portal.release1a.readiness_checks.check_app_loaded',
            side_effect=lambda: (time.sleep(.01) or ('ok', '')),
        ):
            response = self.client.get('/readiness/')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['reason'], 'deadline_exceeded')

    def test_custom_budget_propagates(self):
        with override_settings(PRACE_READINESS_BUDGET_MS=750):
            response = self.client.get('/readiness/')
        self.assertEqual(response.json()['budget_ms'], 750)


class ReadinessStorageAndManifest(SimpleTestCase):
    """Storage and manifest checks: independent of database."""

    def setUp(self):
        self.cursor_patch = patch.object(connections['default'], 'cursor')
        self.cursor = self.cursor_patch.start()
        self.addCleanup(self.cursor_patch.stop)
        self.cursor.return_value.__enter__.return_value.fetchone.return_value = (1,)
        self.executor_patch = patch('django.db.migrations.executor.MigrationExecutor')
        self.executor_factory = self.executor_patch.start()
        self.addCleanup(self.executor_patch.stop)
        self.executor = self.executor_factory.return_value
        self.executor.loader.graph.leaf_nodes.return_value = []
        self.executor.loader.detect_conflicts.return_value = {}
        self.executor.migration_plan.return_value = []

    def test_storage_unwritable_reports_failure(self):
        import os
        import stat
        import tempfile
        from pathlib import Path

        if os.geteuid() == 0:
            self.skipTest("cannot enforce unwritable dir as root")
        unwritable = tempfile.mkdtemp(prefix="readiness-unwritable-")
        try:
            (Path(unwritable) / "media").mkdir(mode=0o500)
            (Path(unwritable) / "static").mkdir(mode=0o500)
            os.chmod(unwritable, 0o500)
            with override_settings(
                DOCUMENT_STORAGE_ROOT=unwritable,
                MEDIA_ROOT=Path(unwritable) / "media",
                STATIC_ROOT=Path(unwritable) / "static",
            ):
                response = self.client.get('/readiness/')
            self.assertEqual(response.status_code, 503)
            entry = _check(response, 'runtime_paths')
            self.assertEqual(entry['status'], 'fail')
            self.assertIn('unwritable', entry['detail'])
        finally:
            os.chmod(unwritable, 0o700)

    def test_storage_missing_path_reports_failure(self):
        with override_settings(DOCUMENT_STORAGE_ROOT="/tmp/no-such-readiness-root"):
            response = self.client.get('/readiness/')
        self.assertEqual(response.status_code, 503)
        entry = _check(response, 'storage_writable')
        self.assertEqual(entry['status'], 'fail')
        self.assertEqual(entry['detail'], 'storage_missing')


class ReadinessDatabaseIntegration(TransactionTestCase):
    def test_real_isolated_database_with_current_migrations(self):
        from django.db import connection
        from django.db.migrations.recorder import MigrationRecorder
        before = MigrationRecorder(connection).applied_migrations()
        response = self.client.get('/readiness/')
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['status'], 'ready')
        self.assertEqual(body['migrations'], 'current')
        self.assertEqual(_check(response, 'db_reachable')['status'], 'ok')
        self.assertEqual(_check(response, 'migrations_current')['status'], 'ok')
        self.assertEqual(MigrationRecorder(connection).applied_migrations(), before)