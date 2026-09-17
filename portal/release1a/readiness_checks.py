"""Small readiness operations returning sanitized status codes.

Filesystem probes write only exclusive temporary files. Supervised execution is
bounded by the disposable readiness worker; these functions do not claim to
interrupt blocking calls themselves.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import re
from pathlib import Path
from typing import Callable, Iterable


_DETAIL_MAX_LEN = 80
_DETAIL_RE = re.compile(r"\s+")


def sanitize_detail(value) -> str:
    """Reduce arbitrary detail to a short, single-line, safe string."""
    if value is None or value == "":
        return ""
    s = _DETAIL_RE.sub(" ", str(value)).strip()
    if len(s) > _DETAIL_MAX_LEN:
        s = s[: _DETAIL_MAX_LEN - 3] + "..."
    return s


def _probe_writable(path: Path) -> bool:
    from .runtime_safety import exclusive_probe
    try:
        exclusive_probe(path)
        return True
    except (OSError, ValueError):
        return False


def check_db_reachable(connection) -> tuple[str, str]:
    """SELECT 1 round-trip. Sanitized: never raises to caller."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            row = cursor.fetchone()
        if row != (1,):
            return ("fail", "unexpected_response")
        return ("ok", "")
    except Exception:
        return ("fail", "database_unavailable")


def check_migrations_current(connection) -> tuple[str, str]:
    """Migration graph consistency + no pending leaves."""
    from django.db.migrations.executor import MigrationExecutor

    try:
        executor = MigrationExecutor(connection)
        executor.loader.check_consistent_history(connection)
        if executor.loader.detect_conflicts():
            return ("fail", "migration_check_failed")
        if executor.migration_plan(executor.loader.graph.leaf_nodes()):
            return ("fail", "pending_migrations")
        return ("ok", "")
    except Exception:
        return ("fail", "migration_check_failed")


def check_storage_writable(document_storage_root) -> tuple[str, str]:
    """DOCUMENT_STORAGE_ROOT exists, is a directory, is writable."""
    if document_storage_root is None:
        return ("fail", "storage_unconfigured")
    try:
        root = Path(document_storage_root)
    except (TypeError, ValueError):
        return ("fail", "storage_path_invalid")
    if not root.exists():
        return ("fail", "storage_missing")
    if not root.is_dir():
        return ("fail", "storage_not_dir")
    if not _probe_writable(root):
        return ("fail", "storage_unwritable")
    return ("ok", "")


def check_runtime_paths(paths: dict) -> tuple[str, str]:
    """Each required path exists and is writable. Bounded.

    `paths` is a mapping of short name (used in the failure detail) to
    filesystem path. Names are not user-controlled; they only appear in
    structured detail output.
    """
    missing: list[str] = []
    unwritable: list[str] = []
    candidates = []
    for name, raw in paths.items():
        if raw is None:
            missing.append(name)
            continue
        try:
            p = Path(raw)
        except (TypeError, ValueError):
            missing.append(name)
            continue
        if not p.exists():
            missing.append(name)
            continue
        candidates.append((name, p))
    # These exclusive probes are independent. Concurrent fsyncs can share one
    # journal commit instead of serially consuming the readiness deadline.
    # The disposable worker still bounds the entire operation, including threads.
    if candidates:
        with ThreadPoolExecutor(max_workers=min(6, len(candidates))) as pool:
            results = pool.map(_probe_writable, (path for _, path in candidates))
            unwritable.extend(name for (name, _), ok in zip(candidates, results) if not ok)
    if missing:
        return ("fail", "missing:" + ",".join(sorted(missing)))
    if unwritable:
        return ("fail", "unwritable:" + ",".join(sorted(unwritable)))
    return ("ok", "")


def check_release_manifest(
    manifest_path,
    manifest_payload,
    expected_sha256=None,
) -> tuple[str, str]:
    """Read-only verification of the release manifest file.

    Required keys (when present): git_commit, app_build_id, generated_at.
    If expected_sha256 is provided, the file's actual hash is compared.
    Returns ("ok", "absent") when manifest_path is None (legacy / not
    configured); the view decides whether "absent" is acceptable.
    """
    if manifest_path is None:
        return ("ok", "absent")
    try:
        p = Path(manifest_path)
    except (TypeError, ValueError):
        return ("fail", "manifest_path_invalid")
    if not p.is_file():
        return ("fail", "manifest_missing")
    try:
        data = p.read_bytes()
    except OSError:
        return ("fail", "manifest_unreadable")
    actual = hashlib.sha256(data).hexdigest()
    if expected_sha256 is not None and actual != expected_sha256:
        return ("fail", "manifest_hash_mismatch")
    if manifest_payload is None:
        return ("fail", "manifest_unparsed")
    for key in ("git_commit", "app_build_id", "generated_at"):
        if key not in manifest_payload:
            return ("fail", "manifest_missing_key")
    return ("ok", "")


def check_release_manifest_live():
    from django.conf import settings
    from .runtime_safety import read_manifest
    path = getattr(settings, 'PRACE_RELEASE_MANIFEST_PATH', None)
    if path is None and not getattr(settings, 'PRACE_SUPERVISED', False):
        return ('ok', 'legacy_test_mode')
    try:
        payload = read_manifest(path, getattr(settings, 'PRACE_RELEASE_MANIFEST_SHA256', None))
        if payload != getattr(settings, 'PRACE_RELEASE_MANIFEST', None):
            return ('fail', 'manifest_identity_changed')
        return ('ok', '')
    except (OSError, ValueError, TypeError):
        return ('fail', 'manifest_invalid')


def check_model_assets():
    # Package metadata locates assets without importing RapidOCR/ONNX.
    from importlib.metadata import distribution
    models = {
        'PP-OCRv6_det_small.onnx': '090f04abcd9d9a7498bc4ebf677e4cb9bdce1fe4197ddb7e529f1ef44e1ff94f',
        'PP-OCRv6_rec_small.onnx': '6f327246b50388f3c176ae304bd95767ea6dc0c9ae92153ef8cbe210b3c14884',
        'ch_ppocr_mobile_v2.0_cls_mobile.onnx': 'e47acedf663230f8863ff1ab0e64dd2d82b838fceb5957146dab185a89d6215c',
    }
    try:
        base = Path(distribution('rapidocr').locate_file('rapidocr/models'))
        for name, expected in models.items():
            digest = hashlib.sha256()
            with (base/name).open('rb') as stream:
                for chunk in iter(lambda: stream.read(1024*1024), b''):
                    digest.update(chunk)
            if digest.hexdigest() != expected:
                return ('fail', 'model_hash_mismatch')
        return ('ok', '')
    except Exception:
        return ('fail', 'model_assets_unavailable')


def check_csrf_confined(csrf_trusted_origins: Iterable[str]) -> tuple[str, str]:
    """Synthetic-only CSRF origin discipline.

    Empty list is acceptable (loopback-only). Each present origin must
    start with https://. The synthetic M2 posture is fixed; an http://
    origin is a misconfiguration that must block readiness.
    """
    for origin in csrf_trusted_origins or []:
        if not isinstance(origin, str) or not origin.startswith("https://"):
            return ("fail", "insecure_origin")
    return ("ok", "")


def check_app_loaded() -> tuple[str, str]:
    """Django app registry populated. Bounded: only enumerates configs."""
    from django.apps import apps

    try:
        configs = list(apps.get_app_configs())
    except Exception:
        return ("fail", "apps_unavailable")
    if not configs:
        return ("fail", "no_apps")
    return ("ok", f"{len(configs)}_apps")


# Registry: ordered list of (name, callable) for the view to dispatch.
# Cheap checks first; DB last.
CHECK_REGISTRY: list[tuple[str, Callable[[], tuple[str, str]]]] = [
    ("apps_loaded", check_app_loaded),
]