"""Locked non-content audit events and mandatory operation receipts."""
from __future__ import annotations
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from functools import wraps
import fcntl
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import uuid
try:
    from .a1_paths import protected_path, protected_root, cleanup_staging_only, ensure_private_directory
except ImportError:
    from a1_paths import protected_path, protected_root, cleanup_staging_only, ensure_private_directory

class AuditWriteError(RuntimeError):
    pass

_CURRENT = ContextVar('a1_operation', default=None)
_OPERATIONS = {'provisional_generate', 'candidate_generate', 'readiness_check',
               'review_prepare', 'review_validate', 'qa_render', 'qa_validate', 'qa_review'}
_PURPOSES = {'a1_provisional', 'a1_candidate', 'a1_readiness', 'a1_prepare', 'a1_validate', 'a1_qa'}


def _metadata(value):
    value = {} if value is None else value
    if not isinstance(value, dict):
        raise AuditWriteError("AUDIT_METADATA_INVALID")
    for key, item in value.items():
        if key in {'employee_count', 'blocked', 'page_count'}:
            valid = type(item) is int and item >= 0
        elif key == 'ready':
            valid = type(item) is bool
        else:
            valid = False
        if not valid:
            raise AuditWriteError('AUDIT_METADATA_INVALID')
    return dict(value)


def _operator_org():
    try:
        data = json.loads(protected_path(protected_root() / 'a1/operator.json').read_text())
        if not isinstance(data, dict):
            raise ValueError()
        org = data.get('organization_id', '')
        if not isinstance(org, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', org) or org == 'UNKNOWN':
            raise ValueError()
        return org
    except (OSError, ValueError, KeyError) as exc:
        raise AuditWriteError('AUDIT_CONTEXT_REQUIRED') from exc


def append_event(operation, outcome, purpose='a1_provisional', error=None, run_id=None, extra=None):
    if operation not in _OPERATIONS or purpose not in _PURPOSES or outcome not in {'started','completed','failed','blocked'}:
        raise AuditWriteError('AUDIT_EVENT_INVALID')
    try:
        if str(uuid.UUID(run_id)) != run_id:
            raise ValueError()
    except (ValueError, TypeError, AttributeError) as exc:
        raise AuditWriteError('AUDIT_RUN_ID_INVALID') from exc
    event = dict(timestamp=datetime.now(timezone.utc).isoformat(), actor=f'uid:{os.geteuid()}',
                 organization=_operator_org(), purpose=purpose, run_id=run_id,
                 operation=operation, outcome=outcome, extra=_metadata(extra))
    if error is not None:
        event['error_tag'] = 'OPERATION_FAILED'
    path = protected_path(protected_root() / 'a1/audit/events.jsonl')
    try:
        ensure_private_directory(path.parent)
        fd = os.open(path, os.O_CREAT | os.O_APPEND | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'ab', buffering=0) as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            os.fchmod(stream.fileno(), 0o600)
            data = (json.dumps(event, ensure_ascii=True) + '\n').encode()
            initial_size = os.fstat(stream.fileno()).st_size
            if initial_size and os.pread(stream.fileno(), 1, initial_size - 1) != b"\n":
                raise AuditWriteError("AUDIT_RECOVERY_REQUIRED")
            try:
                view = memoryview(data)
                while view:
                    written = stream.write(view)
                    if not written:
                        raise OSError('AUDIT_WRITE_FAILED')
                    view = view[written:]
                os.fsync(stream.fileno())
            except OSError:
                # Remove only this interrupted append, while holding the same lock.
                os.ftruncate(stream.fileno(), initial_size)
                os.fsync(stream.fileno())
                raise
    except OSError as exc:
        raise AuditWriteError('AUDIT_WRITE_FAILED') from exc
    return True


def write_private_json(path: Path, value: dict):
    path = protected_path(path)
    ensure_private_directory(path.parent)
    fd, name = tempfile.mkstemp(prefix='.receipt-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
        directory = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        Path(name).unlink(missing_ok=True)


def write_failure_receipt(receipt_path, error_tag, context=None, run_id=None):
    try:
        if not re.fullmatch('[A-Z_]+', error_tag):
            raise AuditWriteError('RECEIPT_TAG_INVALID')
        value = dict(status='failed', error_tag=error_tag,
                     timestamp=datetime.now(timezone.utc).isoformat(), context=_metadata(context))
        if run_id:
            value['run_id'] = str(uuid.UUID(run_id))
        write_private_json(receipt_path, value)
        return True
    except (OSError, ValueError, AuditWriteError):
        print('FAILURE_RECEIPT_UNAVAILABLE', file=sys.stderr)
        return False


def current_run_id():
    state = _CURRENT.get()
    if state is None:
        raise AuditWriteError('AUDIT_OPERATION_REQUIRED')
    return state['run_id']


def register_staging(staging):
    state = _CURRENT.get()
    if state is not None:
        state['staging'].append(staging)


def register_publication(staging, output):
    state = _CURRENT.get()
    if state is None:
        raise AuditWriteError('AUDIT_OPERATION_REQUIRED')
    state['publications'].append((staging, output))


@contextmanager
def audited_operation(operation, purpose, run_id=None):
    run_id = run_id or str(uuid.uuid4())
    state = dict(run_id=run_id, publications=[], staging=[])
    token = _CURRENT.set(state)
    receipt = None
    started = False
    try:
        receipt = protected_path(protected_root() / 'a1/receipts' / f'{run_id}.json')
        append_event(operation, 'started', purpose, run_id=run_id)
        started = True
        write_private_json(receipt, dict(status='running', run_id=run_id))
        yield run_id
        write_private_json(receipt, dict(status='completed', run_id=run_id))
        append_event(operation, 'completed', purpose, run_id=run_id)
    except BaseException as exc:
        # Only this run's new package can be withdrawn; old destinations are never replaced.
        rollback_failed = False
        for staging, output in reversed(state['publications']):
            try:
                if output.exists() and not staging.exists():
                    os.rename(output, staging)
                    cleanup_staging_only(staging)
            except OSError:
                rollback_failed = True
                print('PUBLICATION_RECOVERY_REQUIRED', file=sys.stderr)
        if started:
            try:
                append_event(operation, 'failed', purpose, error=exc, run_id=run_id)
            except (AuditWriteError, OSError, ValueError):
                print('AUDIT_WRITE_FAILED', file=sys.stderr)
        if receipt is not None:
            write_failure_receipt(receipt, 'PUBLICATION_RECOVERY_REQUIRED' if rollback_failed else 'OPERATION_FAILED', run_id=run_id)
        else:
            print('FAILURE_RECEIPT_UNAVAILABLE', file=sys.stderr)
        raise
    finally:
        try:
            for staging in state["staging"]:
                try:
                    cleanup_staging_only(staging)
                except OSError:
                    print("STAGING_CLEANUP_REQUIRED", file=sys.stderr)
        finally:
            _CURRENT.reset(token)


def audited(operation, purpose):
    def decorate(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            with audited_operation(operation, purpose):
                return fn(*args, **kwargs)
        return wrapped
    return decorate


def completed_operation_evidence(run_id: str, operations) -> str:
    """Require both durable completion records; return the stable terminal-event hash.

    The append-only log itself changes as later operations run and is not a dependency hash.
    """
    import hashlib
    try:
        if str(uuid.UUID(run_id)) != run_id:
            raise ValueError()
        receipt = json.loads(protected_path(protected_root() / 'a1/receipts' / f'{run_id}.json').read_text())
        if receipt.get('run_id') != run_id or receipt.get('status') != 'completed':
            raise ValueError()
        path = protected_path(protected_root() / 'a1/audit/events.jsonl')
        last = None
        with path.open('r', encoding='utf-8') as stream:
            fcntl.flock(stream, fcntl.LOCK_SH)
            for line in stream:
                event = json.loads(line)
                if event.get('run_id') == run_id:
                    last = event
        if (last is None or last.get('operation') not in operations
                or last.get('outcome') != 'completed' or last.get('organization') != _operator_org()):
            raise ValueError()
        return hashlib.sha256(json.dumps(last, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        raise AuditWriteError('GENERATION_COMPLETION_REQUIRED') from exc
