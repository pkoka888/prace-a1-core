"""Real PostgreSQL cancellation, on the disposable harness only."""
import time
from unittest import skipUnless
from unittest.mock import patch
from django.db import connection
from django.test import TransactionTestCase
from portal.release1a.readiness_runner import collect_checks


@skipUnless(connection.vendor == 'postgresql', 'Disposable PostgreSQL required')
class PostgresReadinessDeadlineTests(TransactionTestCase):
    def test_slow_statement_is_cancelled_and_connection_recovers(self):
        def slow(conn):
            with conn.cursor() as cursor:
                cursor.execute('SELECT pg_sleep(3)')
            return ('ok','')
        started=time.monotonic()
        with patch('portal.release1a.readiness_checks.check_db_reachable',side_effect=slow):
            result=collect_checks()
        self.assertEqual(result['status'],'not_ready')
        self.assertLess(time.monotonic()-started,2)
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            self.assertEqual(cursor.fetchone(),(1,))
            cursor.execute('SHOW statement_timeout')
            self.assertEqual(cursor.fetchone(),('0',))
