"""Small local filesystem contracts; no Django setup or engine imports."""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import uuid


def no_symlinks(path):
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts:
        raise ValueError('PATH_INVALID')
    for item in [*reversed(path.parents), path]:
        if item.is_symlink():
            raise ValueError('PATH_SYMLINK')
    return path


def confined_root(path):
    root = no_symlinks(path)
    parent = Path(__file__).resolve().parents[2] / 'runtime' / 'portal'
    if root.parent != parent or not root.name.startswith('supervised-'):
        raise ValueError('RUNTIME_ROOT_OUTSIDE_APPROVED_SUBTREE')
    try:
        runtime_directory(root, allow_static_group=True)
    except (OSError, ValueError):
        raise ValueError('RUNTIME_ROOT_PERMISSIONS') from None
    return root


def runtime_directory(path, *, allow_static_group=False):
    """Require owner-only access, or explicit root/static primary-group access.

    Preserve inherited setgid semantics: the access bits, not special bits,
    determine privacy. Infrastructure owns group membership; accepting 0750
    never authorizes sharing credentials or document directories with that group.
    """
    path = no_symlinks(path)
    info = path.stat()
    mode = stat.S_IMODE(info.st_mode) & 0o777
    allowed = mode == 0o700 or (
        allow_static_group and mode == 0o750 and info.st_gid == os.getegid()
    )
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or not allowed:
        raise ValueError('RUNTIME_DIRECTORY_PERMISSIONS')
    return path


def exclusive_probe(path):
    """Never truncate an existing file; unlink only our exclusive probe."""
    root = no_symlinks(path)
    directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    name = '.readiness-' + uuid.uuid4().hex
    created = False
    try:
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
        created = True
        try:
            if os.write(fd, b'ok') != 2:
                raise OSError('PROBE_SHORT_WRITE')
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        if created:
            os.unlink(name, dir_fd=directory)
        os.close(directory)


def read_manifest(path, expected):
    if not isinstance(expected, str) or not re.fullmatch('[0-9a-f]{64}', expected):
        raise ValueError('MANIFEST_EXPECTED_HASH_REQUIRED')
    path = no_symlinks(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) not in (0o400, 0o440) or info.st_size > 65536:
            raise ValueError('MANIFEST_PERMISSIONS_OR_SIZE')
        data = stream.read(65537)
    if len(data) > 65536 or hashlib.sha256(data).hexdigest() != expected:
        raise ValueError('MANIFEST_HASH_MISMATCH')
    payload = json.loads(data)
    if not isinstance(payload, dict):
        raise ValueError('MANIFEST_SCHEMA')
    if not re.fullmatch('[0-9a-f]{40}', str(payload.get('git_commit', ''))):
        raise ValueError('MANIFEST_SCHEMA')
    if not re.fullmatch('[A-Za-z0-9_-]{1,128}', str(payload.get('app_build_id', ''))):
        raise ValueError('MANIFEST_SCHEMA')
    from datetime import datetime
    if datetime.fromisoformat(payload.get('generated_at', '').replace('Z', '+00:00')).tzinfo is None:
        raise ValueError('MANIFEST_SCHEMA')
    return payload
