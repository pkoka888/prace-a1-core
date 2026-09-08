"""Synthetic failure, concurrency and confinement proofs for A1 operations."""
import json
import multiprocessing
import os
from pathlib import Path
import uuid
from unittest.mock import patch

import pytest
from scripts import a1_audit as audit
from scripts import a1_paths as paths


@pytest.fixture
def private(tmp_path, monkeypatch):
    monkeypatch.setenv('A1_PRIVATE_DIR', str(tmp_path))
    (tmp_path/'a1').mkdir()
    (tmp_path/'a1/operator.json').write_text('{"organization_id":"synthetic-org"}')
    return tmp_path


def _append_worker():
    audit.append_event('review_validate', 'started', 'a1_validate', run_id=str(uuid.uuid4()))


def test_concurrent_audit_appends_preserve_every_event(private):
    audit.append_event('review_validate', 'started', 'a1_validate', run_id=str(uuid.uuid4()))
    processes = [multiprocessing.get_context('fork').Process(target=_append_worker) for _ in range(8)]
    for p in processes: p.start()
    for p in processes:
        p.join(10)
        assert p.exitcode == 0
    log = private/'a1/audit/events.jsonl'
    events = [json.loads(line) for line in log.read_text().splitlines()]
    assert len(events) == 9
    assert len({e['run_id'] for e in events}) == 9
    assert all(e['organization'] == 'synthetic-org' and e['actor'].startswith('uid:') for e in events)
    assert log.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize('metadata', [{'employee_name':'synthetic'}, {'employee_count':'secret'}, {'ready':1}])
def test_audit_metadata_is_typed_allowlist(private, metadata):
    with pytest.raises(audit.AuditWriteError):
        audit.append_event('review_validate','started','a1_validate',run_id=str(uuid.uuid4()),extra=metadata)
    assert not (private/'a1/audit/events.jsonl').exists()


@pytest.mark.parametrize('bad_context', [None, {}, [], {'organization_id':'UNKNOWN'}])
def test_missing_context_blocks_before_body_and_writes_receipt(private, bad_context):
    p=private/'a1/operator.json'
    if bad_context is None: p.unlink()
    else: p.write_text(json.dumps(bad_context))
    with pytest.raises(audit.AuditWriteError):
        with audit.audited_operation('review_validate','a1_validate'):
            pytest.fail('processing must not begin')
    receipt=list((private/'a1/receipts').glob('*.json'))
    assert len(receipt)==1
    assert json.loads(receipt[0].read_text())['status']=='failed'


def test_audit_unwritable_blocks_body_and_preserves_failure_receipt(private):
    real=os.open
    def deny(path,*args,**kwargs):
        if str(path).endswith('events.jsonl'):raise PermissionError('private path must not leak')
        return real(path,*args,**kwargs)
    with patch.object(audit.os,'open',side_effect=deny), pytest.raises(audit.AuditWriteError):
        with audit.audited_operation('review_validate','a1_validate'):
            pytest.fail('must block')
    receipt=list((private/'a1/receipts').glob('*.json'))
    assert len(receipt)==1
    assert json.loads(receipt[0].read_text())['status']=='failed'


@pytest.mark.parametrize('relative', ['../escape', 'public/result', 'a1/result', 'output/final/a', 'output/pdf/a'])
def test_destinations_outside_output_and_final_are_rejected(private, relative):
    with pytest.raises(paths.PathValidationError):paths.validate_output_path(private/relative)


def test_ancestor_symlinks_and_input_overlap_rejected(private):
    (private/'output').mkdir()
    (private/'alias').symlink_to(private/'output',target_is_directory=True)
    with pytest.raises(paths.PathValidationError):paths.validate_output_path(private/'alias/result')
    (private/'output/link').symlink_to(private/'a1',target_is_directory=True)
    with pytest.raises(paths.PathValidationError):paths.validate_output_path(private/'output/link/result')
    with pytest.raises(paths.PathValidationError):
        paths.validate_output_path(private/'output/package',private/'output/package/review.csv')
    with pytest.raises(paths.PathValidationError):
        paths.validate_output_path(private/'output/package',private/'output')


def test_cleanup_ignores_unowned_directories_and_staging_is_exclusive(private):
    parent=private/'output';parent.mkdir()
    unowned=parent/'unowned';unowned.mkdir();(unowned/'keep').write_text('synthetic')
    paths.cleanup_staging_only(unowned,os.getpid())
    assert (unowned/'keep').exists()
    a=paths.unique_staging_path(parent,'same');b=paths.unique_staging_path(parent,'same')
    assert a!=b
    for p in (a,b):
        assert p.stat().st_mode & 0o777==0o700
        paths.cleanup_staging_only(p)
        assert not p.exists()


def _publish(output, queue):
    try:
        with audit.audited_operation('candidate_generate','a1_candidate'):
            staging=paths.unique_staging_path(output.parent,'candidate')
            try:
                (staging/'artifact').write_text('synthetic')
                with paths.destination_lock(output):paths.publish_package(staging,output)
            finally:
                # A published stage is cleaned by the operation after receipt/audit completion.
                if staging.exists():paths.cleanup_staging_only(staging)
        queue.put('success')
    except paths.PathValidationError:
        queue.put('conflict')


def test_concurrent_publication_has_one_winner(private):
    ctx=multiprocessing.get_context('fork');queue=ctx.Queue()
    out=private/'output/package'
    procs=[ctx.Process(target=_publish,args=(out,queue)) for _ in range(2)]
    for p in procs:p.start()
    for p in procs:
        p.join(10);assert p.exitcode==0
    assert sorted(queue.get(timeout=2) for _ in procs)==['conflict','success']
    assert [p.name for p in out.iterdir()]==['artifact']
    assert not list(out.parent.glob('.staging-*'))


@pytest.mark.parametrize('failure', ['rename', 'completion_audit', 'completion_receipt'])
def test_failed_publication_or_completion_leaves_no_package(private,failure):
    out=private/'output/package'
    real_append=audit.append_event;real_write=audit.write_private_json;real_rename=os.rename
    def append(*args,**kw):
        if failure=='completion_audit' and args[1]=='completed':raise audit.AuditWriteError('test')
        return real_append(*args,**kw)
    def write(path,value):
        if failure=='completion_receipt' and value['status']=='completed':raise OSError('test')
        return real_write(path,value)
    def rename(src,dst):
        if failure=='rename' and Path(dst)==out:raise OSError('test')
        return real_rename(src,dst)
    with patch.object(audit,'append_event',side_effect=append), patch.object(audit,'write_private_json',side_effect=write), patch.object(paths.os,'rename',side_effect=rename):
        with pytest.raises((OSError,audit.AuditWriteError)):
            with audit.audited_operation('candidate_generate','a1_candidate') as run_id:
                staging=paths.unique_staging_path(out.parent,'candidate')
                try:
                    (staging/'artifact').write_text('synthetic')
                    with paths.destination_lock(out):paths.publish_package(staging,out)
                except BaseException:
                    paths.cleanup_staging_only(staging)
                    raise
    assert not out.exists()
    assert not list(out.parent.glob('.staging-*'))
    receipt=private/'a1/receipts'/f'{run_id}.json'
    assert json.loads(receipt.read_text())['status']=='failed'


def test_atomic_receipt_replace_failure_keeps_previous_receipt(private):
    p=private/'a1/receipt.json';p.write_text('{"status":"old"}')
    with patch.object(audit.os,'replace',side_effect=OSError('synthetic')):
        assert not audit.write_failure_receipt(p,'TEST_FAILURE')
    assert json.loads(p.read_text())['status']=='old'
    assert not list(p.parent.glob('.receipt-*'))


def test_partial_audit_append_is_rolled_back_under_lock(private):
    audit.append_event('review_validate','started','a1_validate',run_id=str(uuid.uuid4()))
    log=private/'a1/audit/events.jsonl';before=log.read_bytes()
    real=audit.os.fdopen
    class PartialWriter:
        def __init__(self,stream):self.stream=stream;self.calls=0
        def __enter__(self):return self
        def __exit__(self,*args):self.stream.close()
        def fileno(self):return self.stream.fileno()
        def write(self,data):
            self.calls+=1
            if self.calls==1:return self.stream.write(data[:8])
            raise OSError('synthetic partial write')
    with patch.object(audit.os,'fdopen',side_effect=lambda *a,**kw: PartialWriter(real(*a,**kw))):
        with pytest.raises(audit.AuditWriteError):
            audit.append_event('review_validate','started','a1_validate',run_id=str(uuid.uuid4()))
    assert log.read_bytes()==before
    audit.append_event('review_validate','started','a1_validate',run_id=str(uuid.uuid4()))
    assert len([json.loads(line) for line in log.read_text().splitlines()])==2


def test_interrupted_log_requires_recovery_without_appending(private):
    log=private/'a1/audit/events.jsonl';log.parent.mkdir();log.write_bytes(b'{"interrupted":')
    with pytest.raises(audit.AuditWriteError,match='AUDIT_RECOVERY_REQUIRED'):
        audit.append_event('review_validate','started','a1_validate',run_id=str(uuid.uuid4()))
    assert log.read_bytes()==b'{"interrupted":'


def test_rollback_failure_still_persists_failure_receipt(private,capsys):
    out=private/'output/package';real_append=audit.append_event;real_rename=os.rename
    def append(*a,**kw):
        if a[1]=='completed':raise audit.AuditWriteError('synthetic')
        return real_append(*a,**kw)
    def rename(src,dst):
        if Path(src)==out:raise OSError('synthetic rollback unavailable')
        return real_rename(src,dst)
    with patch.object(audit,'append_event',side_effect=append),patch.object(paths.os,'rename',side_effect=rename):
        with pytest.raises(audit.AuditWriteError):
            with audit.audited_operation('candidate_generate','a1_candidate') as run_id:
                stage=paths.unique_staging_path(out.parent,'candidate')
                (stage/'artifact').write_text('synthetic')
                with paths.destination_lock(out):paths.publish_package(stage,out)
    receipt=json.loads((private/'a1/receipts'/f'{run_id}.json').read_text())
    assert receipt['status']=='failed'
    assert receipt['error_tag']=='PUBLICATION_RECOVERY_REQUIRED'
    assert 'PUBLICATION_RECOVERY_REQUIRED' in capsys.readouterr().err


def test_publication_without_operation_does_not_publish(private):
    out=private/'output/package';stage=paths.unique_staging_path(out.parent,'candidate')
    try:
        with pytest.raises(audit.AuditWriteError):paths.publish_package(stage,out)
        assert not out.exists()
    finally:paths.cleanup_staging_only(stage)


def test_interruption_cleans_registered_staging_and_records_failure(private):
    with pytest.raises(KeyboardInterrupt):
        with audit.audited_operation('candidate_generate','a1_candidate') as run_id:
            stage=paths.unique_staging_path(private/'output/deep/nested','candidate')
            assert all((private/name).stat().st_mode & 0o777==0o700 for name in ['output','output/deep','output/deep/nested'])
            raise KeyboardInterrupt()
    assert not stage.exists()
    assert json.loads((private/'a1/receipts'/f'{run_id}.json').read_text())['status']=='failed'
