"""Synthetic process ownership and cleanup contracts, no database or secrets."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import uuid

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ocr_lifecycle', REPO_ROOT / 'scripts/run_ocr_worker_lifecycle.py')
lifecycle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lifecycle)


@pytest.fixture
def runtime(monkeypatch):
    root = REPO_ROOT / 'runtime/portal' / ('supervised-worker-unit-' + uuid.uuid4().hex)
    root.mkdir(mode=0o700)
    (root / 'logs').mkdir(mode=0o700)
    (root / 'operator.json').write_text(json.dumps({'id': 123, 'organization_id': 456}))
    (root / 'operator.json').chmod(0o600)
    (root / '.release_manifest.sha256').write_text('0' * 64)
    yield root
    try:
        lifecycle.stop(root, .2)
    except lifecycle.LifecycleError:
        pass
    shutil.rmtree(root)


def dummy(monkeypatch, root, *, ready=True, ignore_term=False, exit_early=False):
    script = root / 'worker-fixture.py'
    script.write_text(
        'import os, pathlib, signal, time\n'
        + ('raise SystemExit(3)\n' if exit_early else '')
        + ('signal.signal(signal.SIGTERM, signal.SIG_IGN)\n' if ignore_term else '')
        + ('os.umask(0o077)\np = pathlib.Path(__file__).parent / ".ocr-worker.ready"\n'
           'p.write_text("ready\\n")\n' if ready else '')
        + 'while True: time.sleep(.1)\n'
    )
    monkeypatch.setattr(lifecycle, '_worker_argv', lambda root, org, actor:
                        [str(REPO_ROOT / 'venv/bin/python'), str(script)])


def test_ready_owned_worker_start_is_idempotent_and_stop_reaps_identity(runtime, monkeypatch):
    dummy(monkeypatch, runtime)
    assert lifecycle.main(['start', '--runtime-root', str(runtime), '--timeout', '3']) == 0
    record = json.loads((runtime / '.ocr-worker.json').read_text())
    assert lifecycle._owned(record, runtime)
    assert lifecycle.start(runtime, 3) == 'already-running'
    assert json.loads((runtime / '.ocr-worker.json').read_text())['pid'] == record['pid']
    for name in ('.ocr-worker.json', '.ocr-worker.lock', '.ocr-worker.ready', 'logs/ocr-worker.log'):
        assert (runtime / name).stat().st_mode & 0o777 == 0o600
    assert lifecycle.stop(runtime, 1) == 'stopped'
    assert lifecycle._process(record['pid']) is None
    assert not (runtime / '.ocr-worker.json').exists()
    assert not (runtime / '.ocr-worker.ready').exists()


def test_start_failure_cleans_owned_record(runtime, monkeypatch):
    dummy(monkeypatch, runtime, exit_early=True)
    assert lifecycle.main(['start', '--runtime-root', str(runtime), '--timeout', '2']) == 1
    assert not (runtime / '.ocr-worker.json').exists()


def test_ready_deadline_cleans_worker(runtime, monkeypatch):
    dummy(monkeypatch, runtime, ready=False)
    with pytest.raises(lifecycle.LifecycleError, match='WORKER_START_DEADLINE'):
        lifecycle.start(runtime, .2)
    assert not (runtime / '.ocr-worker.json').exists()


def test_stop_escalates_only_owned_process(runtime, monkeypatch):
    dummy(monkeypatch, runtime, ignore_term=True)
    lifecycle.start(runtime, 3)
    record = json.loads((runtime / '.ocr-worker.json').read_text())
    assert lifecycle.stop(runtime, .2) == 'stopped'
    assert lifecycle._process(record['pid']) is None


def test_foreign_pid_never_signalled(runtime, monkeypatch):
    lifecycle._atomic_json(runtime / '.ocr-worker.json', {'pid': os.getpid(), 'runtime_root': str(runtime)})
    calls = []
    monkeypatch.setattr(lifecycle.signal, 'pidfd_send_signal', lambda *args: calls.append(args))
    with pytest.raises(lifecycle.LifecycleError, match='WORKER_FOREIGN_PID_REFUSED'):
        lifecycle.stop(runtime, .2)
    assert not calls
    (runtime / '.ocr-worker.json').unlink()


def test_pid_reuse_never_signalled(runtime, monkeypatch):
    dummy(monkeypatch, runtime)
    lifecycle.start(runtime, 3)
    original = json.loads((runtime / '.ocr-worker.json').read_text())
    forged = dict(original, start_ticks='different-launch')
    lifecycle._atomic_json(runtime / '.ocr-worker.json', forged)
    with pytest.raises(lifecycle.LifecycleError, match='WORKER_FOREIGN_PID_REFUSED'):
        lifecycle.stop(runtime, .1)
    assert lifecycle._process(original['pid']) is not None
    lifecycle._atomic_json(runtime / '.ocr-worker.json', original)


@pytest.mark.parametrize('name', ['.ocr-worker.lock', '.ocr-worker.json', '.ocr-worker.ready', 'operator.json', 'logs/ocr-worker.log'])
def test_sidecar_symlink_is_refused_before_mutation(runtime, name):
    target = runtime / 'untouched'
    target.write_text('untouched')
    path = runtime / name
    path.unlink(missing_ok=True)
    path.symlink_to(target)
    assert lifecycle.main(['start', '--runtime-root', str(runtime)]) == 1
    assert target.read_text() == 'untouched'
    path.unlink()


def test_existing_unsafe_log_mode_is_refused(runtime, monkeypatch):
    dummy(monkeypatch, runtime)
    log = runtime / 'logs/ocr-worker.log'
    log.write_text('existing')
    log.chmod(0o644)
    assert lifecycle.main(['start', '--runtime-root', str(runtime)]) == 1
    assert log.read_text() == 'existing'


def test_operator_change_requires_explicit_stop(runtime, monkeypatch):
    dummy(monkeypatch, runtime)
    lifecycle.start(runtime, 3)
    (runtime / 'operator.json').write_text(json.dumps({'id': 321, 'organization_id': 456}))
    with pytest.raises(lifecycle.LifecycleError, match='WORKER_OPERATOR_CHANGED_STOP_FIRST'):
        lifecycle.start(runtime, 3)
