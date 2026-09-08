"""Protected A1 paths and serialized, whole-package publication."""
from __future__ import annotations

from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]
_OWNED: dict[Path, tuple[int, int, int]] = {}

class PathValidationError(ValueError):
    """A sanitized path policy failure."""


def _resolve_strict(path: Path) -> Path:
    path = path.expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    for component in (*reversed(path.parents), path):
        if component.is_symlink():
            raise PathValidationError('SYMLINK_REJECTED')
    return path.resolve()


def protected_root() -> Path:
    value = os.environ.get('A1_PRIVATE_DIR', '').strip()
    if not value:
        raise PathValidationError('A1_PRIVATE_DIR_REQUIRED')
    root = _resolve_strict(Path(value))
    if not root.is_dir():
        raise PathValidationError('A1_PRIVATE_DIR_INVALID')
    return root


def protected_path(path: Path, subdirs=('a1', 'evidence', 'output')) -> Path:
    resolved = _resolve_strict(path)
    root = protected_root()
    if not any(resolved.is_relative_to(root / name) for name in subdirs):
        raise PathValidationError('PROTECTED_DESTINATION_REQUIRED')
    return resolved


def ensure_private_directory(path: Path) -> Path:
    path = protected_path(path)
    current = protected_root()
    for part in path.relative_to(current).parts:
        current = current / part
        _resolve_strict(current)
        current.mkdir(mode=0o700, exist_ok=True)
        current.chmod(0o700)
    return path


def validate_output_path(output: Path, source_review=None, source_employees=None,
                         source_config=None, source_cohort=None, allow_existing=False) -> None:
    resolved = _resolve_strict(output)
    # Reserve repository destinations even when configuration is absent or points elsewhere.
    roots = [ROOT]
    value = os.environ.get('A1_PRIVATE_DIR', '').strip()
    if value:
        roots.append(_resolve_strict(Path(value)))
    for root in roots:
        if any(resolved.is_relative_to(root / 'output' / name) for name in ('final', 'pdf')):
            raise PathValidationError('FINAL_PROMOTION_REQUIRED: final promotion is separately gated')
    protected_path(resolved, ('output',))
    if resolved == protected_root() / 'output':
        raise PathValidationError('PACKAGE_DESTINATION_REQUIRED')
    for source in (source_review, source_employees, source_config, source_cohort):
        if source is not None:
            source = _resolve_strict(source)
            if source.is_relative_to(resolved) or resolved.is_relative_to(source):
                raise PathValidationError('INPUT_OUTPUT_OVERLAP')
    if resolved.exists() and (not allow_existing or not resolved.is_dir()):
        raise PathValidationError('OUTPUT_EXISTS')


def unique_staging_path(parent: Path, purpose: str) -> Path:
    parent = protected_path(parent, ('output',))
    ensure_private_directory(parent)
    staging = Path(tempfile.mkdtemp(prefix='.staging-', dir=parent))
    stat = staging.stat()
    _OWNED[staging] = (os.getpid(), stat.st_dev, stat.st_ino)
    try:
        from .a1_audit import register_staging
    except ImportError:
        from a1_audit import register_staging
    register_staging(staging)
    return staging


def cleanup_staging_only(staging: Path, owned_by_pid=None) -> None:
    token = _OWNED.get(staging)
    if token is None or token[0] != os.getpid() or owned_by_pid not in (None, os.getpid()):
        return
    if staging.exists() and not staging.is_symlink():
        stat = staging.stat()
        if (stat.st_dev, stat.st_ino) == token[1:]:
            shutil.rmtree(staging)
    _OWNED.pop(staging, None)


@contextmanager
def destination_lock(output: Path):
    validate_output_path(output)
    root = protected_path(protected_root() / 'a1/locks')
    ensure_private_directory(root)
    key = hashlib.sha256(str(_resolve_strict(output)).encode()).hexdigest()
    path = protected_path(root / (key + '.lock'))
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        os.fchmod(fd, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX)
        validate_output_path(output)
        yield
    finally:
        os.close(fd)


def publish_package(staging: Path, output: Path) -> None:
    validate_output_path(output)
    for artifact in staging.rglob('*'):
        if artifact.is_symlink():
            raise PathValidationError('SYMLINK_REJECTED')
        artifact.chmod(0o700 if artifact.is_dir() else 0o600)
        if artifact.is_file():
            with artifact.open('rb') as stream:
                os.fsync(stream.fileno())
    try:
        from .a1_audit import register_publication, current_run_id
    except ImportError:
        from a1_audit import register_publication, current_run_id
    current_run_id()  # Refuse unaudited publication before the filesystem mutation.
    os.rename(staging, output)
    register_publication(staging, output)
    fd = os.open(output.parent, os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def run_state_from_receipt(receipt_path: Path) -> str:
    try:
        status = json.loads(protected_path(receipt_path).read_text())['status']
        return status if status in ('completed', 'failed', 'running') else 'unknown'
    except (OSError, ValueError, KeyError):
        return 'unknown'

ensure_candidate_destination = validate_output_path
