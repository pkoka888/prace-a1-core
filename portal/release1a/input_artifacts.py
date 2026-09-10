"""Atomic private input bundles; callers own authorization and input semantics."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import tempfile

from .j4_artifacts import ArtifactError, _root, _write

_REQUIRED = {'review.csv', 'cohort.json', 'employees_normalized.json',
             'input_snapshots.json', 'manifest.json'}
_PROFILE = re.compile(r'profiles/[a-z0-9-]+\.json\Z')


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _validate(payloads):
    if not isinstance(payloads, dict) or not _REQUIRED <= payloads.keys():
        raise ArtifactError('INPUT_PAYLOAD_SET_INVALID')
    if any(not isinstance(name, str) or (name not in _REQUIRED and not _PROFILE.fullmatch(name))
           or not isinstance(data, bytes) for name, data in payloads.items()):
        raise ArtifactError('INPUT_PAYLOAD_INVALID')
    try:
        manifest = json.loads(payloads['manifest.json'])
    except (ValueError, UnicodeError):
        raise ArtifactError('INPUT_MANIFEST_INVALID') from None
    expected = {name: _digest(data) for name, data in payloads.items() if name != 'manifest.json'}
    if not isinstance(manifest, dict) or manifest.get('payload_sha256') != expected:
        raise ArtifactError('INPUT_MANIFEST_HASH_MISMATCH')
    return _digest(payloads['manifest.json'])


def _mode(path, expected):
    mode = path.lstat().st_mode
    if stat.S_ISLNK(mode):
        raise ArtifactError('INPUT_SYMLINK')
    kind = stat.S_ISDIR if expected == 0o700 else stat.S_ISREG
    if not kind(mode) or stat.S_IMODE(mode) != expected:
        raise ArtifactError('INPUT_PERMISSIONS_OR_TYPE_INVALID')


def _sync(directory):
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _verify(directory, payloads):
    _mode(directory, 0o700)
    expected_dirs = {'profiles'} if any(name.startswith('profiles/') for name in payloads) else set()
    found_files, found_dirs = set(), set()
    for parent, dirs, files in os.walk(directory, followlinks=False):
        for name in dirs:
            path = Path(parent) / name
            _mode(path, 0o700)
            found_dirs.add(path.relative_to(directory).as_posix())
        for name in files:
            path = Path(parent) / name
            _mode(path, 0o600)
            relative = path.relative_to(directory).as_posix()
            found_files.add(relative)
            descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            with os.fdopen(descriptor, 'rb') as stream:
                mode = os.fstat(stream.fileno()).st_mode
                if not stat.S_ISREG(mode) or stat.S_IMODE(mode) != 0o600:
                    raise ArtifactError('INPUT_PERMISSIONS_OR_TYPE_INVALID')
                if relative not in payloads or stream.read() != payloads[relative]:
                    raise ArtifactError('INPUT_ARTIFACT_TAMPERED')
    if found_files != set(payloads) or found_dirs != expected_dirs:
        raise ArtifactError('INPUT_ARTIFACT_FILE_SET_INVALID')


def publish_input_artifact(root, payloads):
    """Verify before writing; retry only an exact, protected existing bundle."""
    if not isinstance(payloads, dict):
        raise ArtifactError('INPUT_PAYLOAD_SET_INVALID')
    payloads = dict(payloads)
    digest = _validate(payloads)
    root = _root(root)
    _mode(root, 0o700)
    parent = root / 'a1-input'
    if parent.is_symlink():
        raise ArtifactError('INPUT_SYMLINK')
    parent.mkdir(mode=0o700, exist_ok=True)
    _mode(parent, 0o700)
    lock = os.open(parent / '.publication.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    stage = None
    try:
        if not stat.S_ISREG(os.fstat(lock).st_mode) or stat.S_IMODE(os.fstat(lock).st_mode) != 0o600:
            raise ArtifactError('INPUT_LOCK_INVALID')
        fcntl.flock(lock, fcntl.LOCK_EX)
        target = parent / digest
        if target.exists() or target.is_symlink():
            _verify(target, payloads)
        else:
            stage = Path(tempfile.mkdtemp(prefix='.stage-', dir=parent))
            for name, data in sorted(payloads.items()):
                destination = stage / name
                if destination.parent != stage:
                    destination.parent.mkdir(mode=0o700, exist_ok=True)
                _write(destination, data)
            _verify(stage, payloads)
            if (stage / 'profiles').exists():
                _sync(stage / 'profiles')
            _sync(stage)
            os.rename(stage, target)
            _sync(parent)
            _sync(root)
        return {'relative_path': f'a1-input/{digest}', 'manifest_sha256': digest}
    finally:
        if stage is not None and stage.exists():
            shutil.rmtree(stage)
        os.close(lock)
