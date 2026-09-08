"""Actual cancellation and filesystem-negative proofs; generated fixtures only."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from unittest.mock import patch

import pytest
from django.test import override_settings
from portal.release1a.runtime_safety import exclusive_probe, read_manifest, confined_root
from portal.release1a.readiness_runner import run_process
from portal.release1a.readiness_checks import check_release_manifest_live, check_model_assets


def test_deadline_interrupts_a_blocked_child():
    start = time.monotonic()
    result = run_process([sys.executable, '-c', 'import time; time.sleep(30)'], 100)
    assert result == {'status':'not_ready','reason':'deadline_exceeded'}
    assert time.monotonic()-start < .8


def test_successful_process_and_failure_sanitization():
    assert run_process([sys.executable,'-c','print(\'{"status":"ready"}\')'],1000)['status']=='ready'
    assert run_process([sys.executable,'-c','raise Exception("private-token-path")'],1000)=={'status':'not_ready','reason':'probe_failed'}


def test_probe_preserves_collisions_and_rejects_child_symlink(tmp_path):
    victim=tmp_path/'.readiness-fixed';victim.write_bytes(b'original')
    class Fixed:hex='fixed'
    with patch('portal.release1a.runtime_safety.uuid.uuid4',return_value=Fixed()):
        with pytest.raises(FileExistsError):exclusive_probe(tmp_path)
    assert victim.read_bytes()==b'original'
    linked=tmp_path/'linked';linked.symlink_to(tmp_path,target_is_directory=True)
    with pytest.raises(ValueError):exclusive_probe(linked)
    exclusive_probe(tmp_path)
    assert sorted(p.name for p in tmp_path.iterdir())==['.readiness-fixed','linked']


def test_unapproved_runtime_root_rejected(tmp_path):
    with pytest.raises(ValueError,match='OUTSIDE_APPROVED'):confined_root(tmp_path)


def manifest(tmp_path):
    p=tmp_path/'manifest.json';p.write_text(json.dumps({'git_commit':'0'*40,'app_build_id':'synthetic','generated_at':'2026-09-07T00:00:00Z'}));p.chmod(0o440)
    return p,hashlib.sha256(p.read_bytes()).hexdigest()


def test_manifest_rejects_missing_hash_writes_symlinks_and_tampering(tmp_path):
    p,h=manifest(tmp_path);assert read_manifest(p,h)['app_build_id']=='synthetic'
    with pytest.raises(ValueError):read_manifest(p,None)
    linked=tmp_path/'alias';linked.symlink_to(p)
    with pytest.raises(ValueError):read_manifest(linked,h)
    p.chmod(0o640)
    with pytest.raises(ValueError):read_manifest(p,h)
    p.write_text('{}');p.chmod(0o440)
    with pytest.raises(ValueError):read_manifest(p,h)
    with pytest.raises(ValueError):read_manifest(p,hashlib.sha256(p.read_bytes()).hexdigest())


def test_supervised_manifest_cannot_fail_open(tmp_path):
    p,h=manifest(tmp_path)
    with override_settings(PRACE_SUPERVISED=True,PRACE_RELEASE_MANIFEST_PATH=p,PRACE_RELEASE_MANIFEST_SHA256=None):
        assert check_release_manifest_live()[0]=='fail'
    with override_settings(PRACE_SUPERVISED=True,PRACE_RELEASE_MANIFEST_PATH=p,PRACE_RELEASE_MANIFEST_SHA256=h,PRACE_RELEASE_MANIFEST={}):
        assert check_release_manifest_live()==('fail','manifest_identity_changed')


def test_local_model_hashes_without_engine_import():
    before=set(sys.modules)
    assert check_model_assets()==('ok','')
    assert 'rapidocr' not in set(sys.modules)-before
    assert 'onnxruntime' not in set(sys.modules)-before


def test_missing_models_fail_closed():
    with patch('importlib.metadata.distribution',side_effect=OSError('private-path')):
        assert check_model_assets()==('fail','model_assets_unavailable')


def test_actual_supervised_worker_missing_db_does_not_create_it():
    import tempfile
    from tests.test_settings_supervised_synthetic import _valid_env
    root_parent=Path(__file__).resolve().parents[1]/'runtime/portal'
    with tempfile.TemporaryDirectory(prefix='supervised-probe-',dir=root_parent) as temporary:
        root=Path(temporary)
        p,h=manifest(root)
        env={**os.environ,'PRACE_RUNTIME_ROOT':str(root),'PRACE_SECRET_KEY':'synthetic-test-only',
             'PRACE_RELEASE_MANIFEST':str(p),'PRACE_RELEASE_MANIFEST_SHA256':h,
             'PRACE_ALLOWED_HOSTS':'localhost','DJANGO_SETTINGS_MODULE':'portal.settings_supervised_synthetic'}
        for key in list(env):
            if key.startswith('PRACE_DB_'):env.pop(key)
        # This checks the missing-database side effect, not cold-start latency.
        # The separate blocked-child test enforces actual deadline cancellation.
        result=run_process([str(root_parent.parents[1]/'venv/bin/python'),'-m','portal.release1a.readiness_worker'],10000,env=env)
        assert result['status']=='not_ready'
        assert any(c.get('detail')=='database_missing' for c in result.get('checks', [])), result
        assert not (root/'db.sqlite3').exists()


def test_probe_concurrency_slot_defers_without_spawning():
    from portal.release1a import readiness_runner as runner
    with runner._PROBE_SLOT:
        with patch.object(runner,'run_process') as execute:
            assert runner.supervised_probe(2000)['reason']=='probe_busy'
            execute.assert_not_called()
