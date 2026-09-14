#!/usr/bin/env python3
"""Owned synthetic OCR worker lifecycle; durable work remains in OcrRun.

No Django imports/settings initialization here. The management command validates
its actor and organization before writing its private readiness handshake.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import tempfile
import time

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
from portal.release1a.runtime_safety import confined_root, no_symlinks


class LifecycleError(Exception):
    """An opaque operator-actionable error; no source values or environment."""


def _private_file(path: Path, flags: int):
    no_symlinks(path)
    fd = os.open(path, flags | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    info = os.fstat(fd)
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o600):
        os.close(fd)
        raise LifecycleError("WORKER_PRIVATE_FILE_REQUIRED")
    return fd


def _read_json(path: Path):
    with os.fdopen(_private_file(path, os.O_RDONLY)) as stream:
        return json.load(stream)


def _atomic_json(path: Path, payload):
    no_symlinks(path)
    fd, tmp = tempfile.mkstemp(prefix='.ocr-record-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(payload, stream, sort_keys=True)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _process(pid: int):
    """Return PID-reuse-resistant start ticks; zombies are already stopped."""
    try:
        proc = Path('/proc') / str(pid)
        fields = (proc / 'stat').read_text().rsplit(')', 1)[1].split()
        if fields[0] == 'Z':
            return None
        return {
            'start_ticks': fields[19],
            'argv': (proc / 'cmdline').read_bytes().rstrip(b'\0').decode().split('\0'),
            'runtime_root': next((item.split(b'=', 1)[1].decode()
                for item in (proc / 'environ').read_bytes().split(b'\0')
                if item.startswith(b'PRACE_RUNTIME_ROOT=')), None),
            'cwd': str((proc / 'cwd').resolve(strict=True)),
        }
    except FileNotFoundError:
        return None
    except PermissionError:
        # A process can become a zombie between reading stat and environ.
        # Live-process permission failures still fail closed.
        for _ in range(10):
            try:
                if (proc / 'stat').read_text().rsplit(')', 1)[1].split()[0] in ('Z', 'X'):
                    return None
            except FileNotFoundError:
                return None
            time.sleep(0.01)
        raise


def _owned(record, root):
    pid = record.get('pid')
    if type(pid) is not int or pid <= 1:
        raise LifecycleError('WORKER_RECORD_INVALID')
    current = _process(pid)
    if current is None:
        return False
    if (record.get('runtime_root') != str(root)
            or current['runtime_root'] != str(root)
            or current['cwd'] != str(REPO_ROOT)
            or current['start_ticks'] != record.get('start_ticks')
            or current['argv'] != record.get('argv')
            or record.get('argv') != _worker_argv(root, record['organization_id'], record['actor_id'])):
        raise LifecycleError('WORKER_FOREIGN_PID_REFUSED')
    return True


def _worker_argv(root, organization_id, actor_id):
    return [str(REPO_ROOT / 'venv/bin/python'), str(REPO_ROOT / 'manage.py'),
            'process_ocr', '--organization-id', str(organization_id),
            '--actor-id', str(actor_id), '--loop', '--poll-interval', '1',
            '--ready-file', str(root / '.ocr-worker.ready')]


def _clear(root):
    for name in ('.ocr-worker.json', '.ocr-worker.ready'):
        path = no_symlinks(root / name)
        path.unlink(missing_ok=True)


def _same_launch_alive(record):
    """Wait after a verified signal without reading disappearing environ data."""
    try:
        fields = (Path('/proc') / str(record['pid']) / 'stat').read_text().rsplit(')', 1)[1].split()
    except FileNotFoundError:
        return False
    if fields[0] in ('Z', 'X'):
        return False
    if fields[19] != record['start_ticks']:
        raise LifecycleError('WORKER_FOREIGN_PID_REFUSED')
    return True


def _signal_owned(record, root, signum):
    # Hold the kernel process reference across the ownership check so PID reuse
    # between checking /proc and signalling cannot target another process.
    try:
        fd = os.pidfd_open(record['pid'])
    except ProcessLookupError:
        return
    try:
        if _owned(record, root):
            try:
                signal.pidfd_send_signal(fd, signum)
            except ProcessLookupError:
                pass
    finally:
        os.close(fd)


def stop(root: Path, timeout: float):
    record_path = root / '.ocr-worker.json'
    if not record_path.exists():
        return 'not-running'
    record = _read_json(record_path)
    if not _owned(record, root):
        _clear(root)
        return 'stale-cleared'
    _signal_owned(record, root, signal.SIGTERM)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _same_launch_alive(record):
            _clear(root)
            return 'stopped'
        time.sleep(0.1)
    # A reused PID must never receive the escalation signal.
    if _owned(record, root):
        _signal_owned(record, root, signal.SIGKILL)
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        if not _same_launch_alive(record):
            _clear(root)
            return 'stopped'
        time.sleep(0.1)
    raise LifecycleError('WORKER_STOP_DEADLINE')


def start(root: Path, timeout: float):
    payload = _read_json(root / 'operator.json')
    actor_id, organization_id = payload.get('id'), payload.get('organization_id')
    if any(type(value) is not int or value <= 0 for value in (actor_id, organization_id)):
        raise LifecycleError('WORKER_OPERATOR_IDENTIFIERS_REQUIRED')
    record_path = root / '.ocr-worker.json'
    if record_path.exists():
        record = _read_json(record_path)
        if _owned(record, root):
            if (record.get('actor_id'), record.get('organization_id')) != (actor_id, organization_id):
                raise LifecycleError('WORKER_OPERATOR_CHANGED_STOP_FIRST')
            return 'already-running'
        _clear(root)
    no_symlinks(root / '.ocr-worker.ready').unlink(missing_ok=True)
    log_dir = no_symlinks(root / 'logs')
    if not log_dir.is_dir() or log_dir.stat().st_uid != os.getuid() or stat.S_IMODE(log_dir.stat().st_mode) != 0o700:
        raise LifecycleError('WORKER_PRIVATE_LOG_DIRECTORY_REQUIRED')
    env = dict(os.environ)
    env.update(PRACE_RUNTIME_ROOT=str(root), DJANGO_SETTINGS_MODULE='portal.settings_supervised_synthetic',
               PRACE_RELEASE_MANIFEST=str(root / 'release_manifest.json'))
    env['PRACE_RELEASE_MANIFEST_SHA256'] = no_symlinks(root / '.release_manifest.sha256').read_text().strip()
    argv = _worker_argv(root, organization_id, actor_id)
    with os.fdopen(_private_file(log_dir / 'ocr-worker.log', os.O_WRONLY | os.O_APPEND | os.O_CREAT), 'a') as log:
        proc = subprocess.Popen(argv, cwd=REPO_ROOT, env=env, stdin=subprocess.DEVNULL,
                                stdout=log, stderr=log, start_new_session=True)
    recorded = False
    try:
        current = _process(proc.pid)
        if current is None:
            raise LifecycleError('WORKER_EXITED_DURING_START')
        record = dict(pid=proc.pid, start_ticks=current['start_ticks'], argv=argv,
                      runtime_root=str(root), organization_id=organization_id, actor_id=actor_id)
        _atomic_json(record_path, record)
        recorded = True
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                raise LifecycleError('WORKER_START_FAILED_SEE_PRIVATE_LOG')
            ready = no_symlinks(root / '.ocr-worker.ready')
            if ready.exists():
                with os.fdopen(_private_file(ready, os.O_RDONLY)) as stream:
                    if stream.read(32) == 'ready\n' and _owned(record, root):
                        return 'started'
                raise LifecycleError('WORKER_READINESS_INVALID')
            time.sleep(0.1)
        raise LifecycleError('WORKER_START_DEADLINE_SEE_PRIVATE_LOG')
    except BaseException:
        if recorded:
            stop(root, min(timeout, 3))
        elif proc.poll() is None:
            # Direct child still owned by Popen, before a durable record exists.
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=3)
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('start', 'stop', 'status'))
    parser.add_argument('--runtime-root', required=True, type=Path)
    parser.add_argument('--timeout', type=float, default=30)
    args = parser.parse_args(argv)
    try:
        if not 0 < args.timeout <= 300:
            raise LifecycleError('WORKER_TIMEOUT_INVALID')
        root = confined_root(args.runtime_root)
        # Validate sidecars before locks or writes. Never silently adopt symlinks.
        for name in ('.ocr-worker.lock', '.ocr-worker.json', '.ocr-worker.ready', 'operator.json', 'logs/ocr-worker.log'):
            no_symlinks(root / name)
        with os.fdopen(_private_file(root / '.ocr-worker.lock', os.O_RDWR | os.O_CREAT), 'r+') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if args.action == 'start':
                outcome = start(root, args.timeout)
            elif args.action == 'stop':
                outcome = stop(root, args.timeout)
            else:
                path = root / '.ocr-worker.json'
                outcome = 'running' if path.exists() and _owned(_read_json(path), root) else 'not-running'
        print('OCR worker: ' + outcome)
        return 0
    except (OSError, ValueError, KeyError, TypeError, LifecycleError) as exc:
        # Exception strings from JSON/filesystem may contain private source values.
        code = str(exc) if isinstance(exc, LifecycleError) else type(exc).__name__
        print('FAIL: OCR worker ' + code, file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
