"""Supervised probes run in a fresh process; no fork of web/ONNX threads."""
import json
import os
from pathlib import Path
import signal
import subprocess
import time
import threading

_PROBE_SLOT = threading.BoundedSemaphore(1)


def run_process(command, budget_ms, *, env=None):
    started = time.monotonic()
    process = None
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                   env=env, start_new_session=True)
        remaining = budget_ms / 1000 - (time.monotonic() - started)
        output, _ = process.communicate(timeout=max(0, remaining))
        if time.monotonic() - started > budget_ms / 1000:
            return {'status': 'not_ready', 'reason': 'deadline_exceeded'}
        if process.returncode or len(output) > 16384:
            return {'status': 'not_ready', 'reason': 'probe_failed'}
        result = json.loads(output)
        if not isinstance(result, dict) or result.get('status') not in ('ready', 'not_ready'):
            raise ValueError()
        return result
    except subprocess.TimeoutExpired:
        return {'status': 'not_ready', 'reason': 'deadline_exceeded'}
    except (OSError, ValueError):
        return {'status': 'not_ready', 'reason': 'probe_failed'}
    finally:
        if process is not None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            try:
                process.communicate(timeout=.2)
            except subprocess.TimeoutExpired:
                # A kernel-level uninterruptible I/O stall cannot be solved in Python.
                # Do not turn cleanup into an unbounded HTTP wait.
                pass


def supervised_probe(budget_ms):
    root = Path(__file__).resolve().parents[2]
    env = dict(os.environ)
    env['DJANGO_SETTINGS_MODULE'] = 'portal.settings_supervised_synthetic'
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    if not _PROBE_SLOT.acquire(blocking=False):
        return {'status': 'not_ready', 'reason': 'probe_busy'}
    try:
        return run_process([str(root/'venv/bin/python'), '-m', 'portal.release1a.readiness_worker'],
                           budget_ms, env=env)
    finally:
        _PROBE_SLOT.release()


def collect_checks():
    from django.conf import settings
    from django.db import connection, transaction
    from . import readiness_checks as rc
    started = time.monotonic()
    checks = []
    def check(name, fn):
        tick = time.monotonic()
        try:
            status, detail = fn()
        except Exception:
            status, detail = 'fail', 'check_failed'
        checks.append(dict(name=name, status=status, detail=rc.sanitize_detail(detail),
                           elapsed_ms=round((time.monotonic()-tick)*1000)))
        return status == 'ok'
    check('apps_loaded', rc.check_app_loaded)
    check('csrf_confined', lambda: rc.check_csrf_confined(getattr(settings,'CSRF_TRUSTED_ORIGINS',[])))
    paths = {name.lower(): getattr(settings, name, None) for name in
             ('DOCUMENT_STORAGE_ROOT','MEDIA_ROOT','STATIC_ROOT')}
    paths.update({name.lower(): getattr(settings, name) for name in
                  ('CACHE_DIR','TMP_DIR','LOG_DIR') if hasattr(settings, name)})
    check('runtime_paths', lambda: rc.check_runtime_paths(paths))
    check('storage_writable', lambda: rc.check_storage_writable(getattr(settings,'DOCUMENT_STORAGE_ROOT',None)))
    check('release_manifest', rc.check_release_manifest_live)
    if getattr(settings, 'PRACE_SUPERVISED', False):
        if connection.vendor == 'sqlite' and not Path(connection.settings_dict['NAME']).is_file():
            checks.append(dict(name='db_reachable',status='fail',detail='database_missing',elapsed_ms=0))
            return dict(status='not_ready',reason='check_failed',checks=checks)
        check('model_assets', rc.check_model_assets)
    try:
        # SET LOCAL needs an actual transaction. Startup connection options also
        # bound the BEGIN/connect preceding set_config on supervised PostgreSQL.
        if connection.vendor == 'postgresql':
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute("SELECT set_config('statement_timeout', %s, true)", ['500ms'])
                if check('db_reachable', lambda: rc.check_db_reachable(connection)):
                    check('migrations_current', lambda: rc.check_migrations_current(connection))
        elif check('db_reachable', lambda: rc.check_db_reachable(connection)):
            check('migrations_current', lambda: rc.check_migrations_current(connection))
    except Exception:
        checks.append(dict(name='db_reachable',status='fail',detail='database_unavailable',elapsed_ms=0))
    if not any(c['name']=='migrations_current' for c in checks):
        checks.append(dict(name='migrations_current',status='fail',detail='skipped_db_unavailable',elapsed_ms=0))
    ready = all(c['status']=='ok' for c in checks)
    body = dict(status='ready' if ready else 'not_ready', checks=checks,
                elapsed_ms=round((time.monotonic()-started)*1000))
    body.update({'migrations':'current'} if ready else {'reason':'check_failed'})
    return body
