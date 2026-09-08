"""Runtime contract helpers: synthetic-only posture surfaced to infra probes.

These helpers read from `django.conf.settings` and return a sanitized,
public-facing dict that can be exposed via JSON endpoints. They must NOT
leak secrets, internal paths, identifiers, or PII.

Public surface (sanitized):
    mode            settings.SETTINGS_MODULE basename (e.g., settings_supervised_synthetic)
    real_data       always False for synthetic postures
    supervised      settings.PRACE_SUPERVISED is True
    build_id        from PRACE_RELEASE_MANIFEST.app_build_id when present
    git_commit      from PRACE_RELEASE_MANIFEST.git_commit when present
    db_engine       DATABASES.default.ENGINE basename (no host/credentials)
    storage_root    DOCUMENT_STORAGE_ROOT basename only (no full path)
    mfa_required    True when MFA_SUPPORTED_TYPES is non-empty

The contract is consumed by:
    /health/        liveness marker
    /readiness/     readiness body
    /synthetic/     full synthetic-only contract for infra edge probes
"""
from __future__ import annotations

from pathlib import Path

from django.conf import settings


def _safe_basename(value):
    """Return the rightmost dotted component of value (e.g., 'a.b.c' → 'c').

    For filesystem paths with no '/', falls back to Path(value).name.
    Returns "" for None/empty/invalid input.
    """
    if not value:
        return ""
    s = str(value)
    if "/" in s:
        try:
            return Path(s).name
        except (TypeError, ValueError):
            return ""
    if "." in s:
        return s.rsplit(".", 1)[-1]
    return s


def _manifest_pair():
    """Return (build_id, git_commit) from settings.PRACE_RELEASE_MANIFEST or ("", "")."""
    manifest = getattr(settings, "PRACE_RELEASE_MANIFEST", None)
    if not isinstance(manifest, dict):
        return "", ""
    build_id = str(manifest.get("app_build_id") or "")
    git_commit = str(manifest.get("git_commit") or "")
    return build_id, git_commit


def verify_manifest_hash():
    """Compatibility entrypoint; one fail-closed manifest implementation."""
    from .readiness_checks import check_release_manifest_live
    return check_release_manifest_live()


def runtime_mode():
    """Settings module identifier (e.g., 'settings_supervised_synthetic').

    Strips the conventional 'portal.' package prefix so the contract is
    short and stable for edge-probe correlation.
    """
    module = str(getattr(settings, "SETTINGS_MODULE", "") or "")
    if not module:
        return str(getattr(settings, "PRACE_RUNTIME_MODE", "unknown"))
    if module.startswith("portal."):
        module = module[len("portal."):]
    return module or "unknown"


def is_supervised():
    """True when settings.PRACE_SUPERVISED is True."""
    return bool(getattr(settings, "PRACE_SUPERVISED", False))


def synthetic_only():
    """True for any M2 posture; the runtime never processes real data."""
    return bool(getattr(settings, "M2_SYNTHETIC_ONLY", False))


def build_identity():
    """(build_id, git_commit) tuple; empty strings when manifest is unconfigured."""
    return _manifest_pair()


def db_engine():
    """Database engine basename from DATABASES.default.ENGINE (e.g., 'sqlite3')."""
    engine = ""
    try:
        engine = settings.DATABASES["default"]["ENGINE"]
    except (KeyError, TypeError):
        engine = ""
    return _safe_basename(engine)


def storage_root_basename():
    """DOCUMENT_STORAGE_ROOT basename only — never the full path."""
    return _safe_basename(getattr(settings, "DOCUMENT_STORAGE_ROOT", None))


def mfa_required():
    """True when MFA_SUPPORTED_TYPES is non-empty."""
    types = getattr(settings, "MFA_SUPPORTED_TYPES", []) or []
    return bool(types)


def health_payload():
    """Liveness marker payload — synthetic posture + build identity."""
    build_id, git_commit = _manifest_pair()
    return {
        "status": "synthetic-m2",
        "real_data": False,
        "mode": runtime_mode(),
        "supervised": is_supervised(),
        "build_id": build_id,
        "git_commit": git_commit,
    }


def synthetic_contract_payload():
    """Full synthetic-only contract for infra edge probes."""
    build_id, git_commit = _manifest_pair()
    return {
        "contract": "prace-synthetic-m2",
        "real_data": False,
        "mode": runtime_mode(),
        "supervised": is_supervised(),
        "synthetic_only": synthetic_only(),
        "build_id": build_id,
        "git_commit": git_commit,
        "db_engine": db_engine(),
        "storage_root": storage_root_basename(),
        "mfa_required": mfa_required(),
        "endpoints": {
            "live": "/health/",
            "ready": "/readiness/",
            "contract": "/synthetic/",
        },
    }