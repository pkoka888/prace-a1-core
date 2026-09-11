"""Confined supervised synthetic settings, never an activation authorization.

Required: PRACE_RUNTIME_ROOT (private project runtime/portal/supervised-* child),
PRACE_SECRET_KEY, PRACE_RELEASE_MANIFEST, PRACE_RELEASE_MANIFEST_SHA256,
PRACE_ALLOWED_HOSTS. Optional HTTPS PRACE_TRUSTED_ORIGINS and a complete
PRACE_DB_NAME/USER/HOST/PORT target; remote TCP requires verify-full plus trust
file. Password bytes are preserved. SQLite defaults to the confined root.

Read-only manifest bytes/schema/hash and existing child paths are checked before
service startup. DEBUG=False and synthetic-only behavior are fixed. Operational
identity, secret delivery, deployment and database migrations remain separately
owned by infrastructure. The readiness subprocess bounds blocking I/O; settings
alone do not establish host isolation or a supervised service.
"""
import json
import os
import stat
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured


_HOST_RE = __import__("re").compile(r"^[A-Za-z0-9.\-_\[\]:]+$")
_ORIGIN_RE = __import__("re").compile(r"^https://[A-Za-z0-9.\-_\[\]:]+$")
_SSLMODES = {"disable", "allow", "prefer", "require", "verify-ca", "verify-full"}
_REQUIRE_SSLROOTCERT = {"verify-ca", "verify-full"}
_BASE_SECRET_DEFAULT = "synthetic-m2-local-only-insecure-default"


def _require_env(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise ImproperlyConfigured(
            f"{name} is required for portal.settings_supervised_synthetic. "
            "See docs/operations/infra-return-work-order-2026-09-07.md."
        )
    return value


def _abs_path(name, raw):
    path = Path(raw)
    if not path.is_absolute():
        raise ImproperlyConfigured(
            f"{name} must be an absolute path"
        )
    return path


def _csv(value):
    return [item.strip() for item in value.split(",") if item.strip()]


# Resolve the approved synthetic root before any writes.
from portal.release1a.runtime_safety import confined_root, no_symlinks, read_manifest
_runtime_root_raw = _require_env("PRACE_RUNTIME_ROOT")
try:
    _runtime_root = confined_root(_runtime_root_raw)
except (OSError, ValueError):
    raise ImproperlyConfigured("PRACE_RUNTIME_ROOT confinement or permissions invalid") from None

# --- Secret: required, nonempty, not the insecure base default ---
_secret = _require_env("PRACE_SECRET_KEY")
if _secret == _BASE_SECRET_DEFAULT:
    raise ImproperlyConfigured(
        "PRACE_SECRET_KEY must not equal the base settings insecure default"
    )

# Validate the same bounded bytes against an independently supplied release hash.
_manifest_path = _abs_path("PRACE_RELEASE_MANIFEST", _require_env("PRACE_RELEASE_MANIFEST"))
_manifest_sha256_raw = _require_env("PRACE_RELEASE_MANIFEST_SHA256")
try:
    _manifest = read_manifest(_manifest_path, _manifest_sha256_raw)
except (OSError, ValueError, TypeError):
    raise ImproperlyConfigured("PRACE_RELEASE_MANIFEST invalid hash, JSON or read-only mode") from None

# --- Allowed hosts: required, comma-separated, validated ---
_allowed_raw = _require_env("PRACE_ALLOWED_HOSTS")
_allowed_hosts = _csv(_allowed_raw)
if not _allowed_hosts:
    raise ImproperlyConfigured(
        "PRACE_ALLOWED_HOSTS must list at least one host"
    )
for _host in _allowed_hosts:
    if not _HOST_RE.match(_host):
        raise ImproperlyConfigured(
            f"PRACE_ALLOWED_HOSTS contains invalid entry {_host!r}"
        )

# --- Trusted origins: optional; HTTPS only ---
_trusted_raw = os.environ.get("PRACE_TRUSTED_ORIGINS", "")
_trusted_origins = _csv(_trusted_raw)
for _origin in _trusted_origins:
    if not _ORIGIN_RE.match(_origin):
        raise ImproperlyConfigured(
            f"PRACE_TRUSTED_ORIGINS entry {_origin!r} must be https://..."
        )

# --- Database target: all-or-none PostgreSQL; otherwise confined SQLite ---
_db_name = os.environ.get("PRACE_DB_NAME", "").strip()
_db_user = os.environ.get("PRACE_DB_USER", "").strip()
_db_host = os.environ.get("PRACE_DB_HOST", "").strip()
_db_port_raw = os.environ.get("PRACE_DB_PORT", "").strip()
_db_password = os.environ.get("PRACE_DB_PASSWORD", "")
_db_sslmode = os.environ.get("PRACE_DB_SSLMODE", "").strip()
_db_sslrootcert = os.environ.get("PRACE_DB_SSLROOTCERT", "").strip()
_db_present = [
    _n for _n, _v in (
        ("PRACE_DB_NAME", _db_name),
        ("PRACE_DB_USER", _db_user),
        ("PRACE_DB_HOST", _db_host),
        ("PRACE_DB_PORT", _db_port_raw),
    ) if _v
]
if _db_present and len(_db_present) != 4:
    _missing = {"PRACE_DB_NAME", "PRACE_DB_USER", "PRACE_DB_HOST", "PRACE_DB_PORT"} - set(_db_present)
    raise ImproperlyConfigured(
        f"PRACE_DB_* partial: missing {_missing}. Set all four or none."
    )
if _db_present:
    try:
        _db_port = int(_db_port_raw)
    except ValueError as exc:
        raise ImproperlyConfigured(
            f"PRACE_DB_PORT={_db_port_raw!r} must be an integer"
        ) from exc
    if not 1 <= _db_port <= 65535:
        raise ImproperlyConfigured(
            f"PRACE_DB_PORT={_db_port} outside 1-65535"
        )
    if _db_sslmode and _db_sslmode not in _SSLMODES:
        raise ImproperlyConfigured(
            f"PRACE_DB_SSLMODE={_db_sslmode!r} not in {sorted(_SSLMODES)}"
        )
    # Unix socket paths (starting with /) are local; others are remote
    _is_unix_socket = _db_host.startswith("/")
    _is_remote = not _is_unix_socket and _db_host not in ("", "localhost", "127.0.0.1", "::1")
    if _is_remote:
        if _db_sslmode != "verify-full":
            raise ImproperlyConfigured(
                f"PRACE_DB_SSLMODE must be 'verify-full' for remote target {_db_host}"
            )
        if not _db_sslrootcert:
            raise ImproperlyConfigured(
                f"PRACE_DB_SSLROOTCERT required for remote target {_db_host}"
            )
    if _db_sslmode in _REQUIRE_SSLROOTCERT and not _db_sslrootcert:
        raise ImproperlyConfigured(
            f"PRACE_DB_SSLMODE={_db_sslmode} requires PRACE_DB_SSLROOTCERT"
        )
    if _db_sslrootcert:
        _sslrootcert_path = _abs_path("PRACE_DB_SSLROOTCERT", _db_sslrootcert)
        if not _sslrootcert_path.is_file():
            raise ImproperlyConfigured(
                f"PRACE_DB_SSLROOTCERT={_db_sslrootcert} not found"
            )

# --- Now bring in base settings; everything below overrides ---
from portal.settings import *  # noqa: E402, F403

DEBUG = False
SECRET_KEY = _secret
ALLOWED_HOSTS = _allowed_hosts
CSRF_TRUSTED_ORIGINS = _trusted_origins

# WhiteNoise serves static assets for gunicorn + DEBUG=False. The
# synthetic M2 base uses DEBUG=True with runserver's auto-serve, so
# the base MIDDLEWARE does not include WhiteNoise. Here we replace
# the base MIDDLEWARE with one that includes WhiteNoise right after
# SecurityMiddleware so the login form's CSS/JS render in the
# rehearsal without requiring a reverse proxy.
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
# WhiteNoise uses the default staticfiles storage; no need to switch to
# the compressed manifest backend in the supervised deployment.

PRACE_RUNTIME_ROOT = _runtime_root
PRACE_RELEASE_MANIFEST = _manifest
PRACE_RELEASE_MANIFEST_PATH = _manifest_path
PRACE_RUNTIME_MODE = "settings_supervised_synthetic"
PRACE_SUPERVISED = True
PRACE_SUPERVISED_SYNTHETIC = True

# Confined layout under PRACE_RUNTIME_ROOT
DOCUMENT_STORAGE_ROOT = _runtime_root / "storage"
MEDIA_ROOT = _runtime_root / "media"
STATIC_ROOT = _runtime_root / "static"
CACHE_DIR = _runtime_root / "cache"
TMP_DIR = _runtime_root / "tmp"
LOG_DIR = _runtime_root / "logs"
for _child in (DOCUMENT_STORAGE_ROOT, MEDIA_ROOT, STATIC_ROOT, CACHE_DIR, TMP_DIR, LOG_DIR):
    try:
        no_symlinks(_child)
        _child.mkdir(mode=0o700, exist_ok=True)
        if _child.stat().st_uid != os.getuid() or _child.stat().st_mode & 0o077:
            raise ValueError("CHILD_PERMISSIONS")
    except (OSError, ValueError):
        raise ImproperlyConfigured("RUNTIME_CHILD_CONFINEMENT_INVALID") from None
try:
    no_symlinks(_runtime_root / "db.sqlite3")
except ValueError:
    raise ImproperlyConfigured("DATABASE_PATH_SYMLINK") from None
MEDIA_URL = "/__confined_media__/"
# Direct Python temporary files to the private runtime, including library callers.
os.environ["TMPDIR"] = str(TMP_DIR)
import tempfile
tempfile.tempdir = str(TMP_DIR)

# Optional readiness tuning; defaults applied in views.readiness()
_budget_raw = os.environ.get("PRACE_READINESS_BUDGET_MS", "").strip()
if _budget_raw:
    try:
        PRACE_READINESS_BUDGET_MS = int(_budget_raw)
    except ValueError as exc:
        raise ImproperlyConfigured(
            f"PRACE_READINESS_BUDGET_MS={_budget_raw!r} must be an integer (ms)"
        ) from exc
    if not 100 <= PRACE_READINESS_BUDGET_MS <= 60000:
        raise ImproperlyConfigured(
            f"PRACE_READINESS_BUDGET_MS={PRACE_READINESS_BUDGET_MS} outside 100-60000"
        )

PRACE_RELEASE_MANIFEST_SHA256 = _manifest_sha256_raw

# Security posture
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "same-origin"

# Synthetic-only posture is fixed
M2_SYNTHETIC_ONLY = True

# Optional one-time synthetic inbox configuration. Both IDs refer to existing
# records; importing settings never creates an operator, membership or MFA proof.
_inbox_org = os.environ.get("PRACE_INBOX_ORGANIZATION_ID", "").strip()
_inbox_actor = os.environ.get("PRACE_INBOX_ACTOR_ID", "").strip()
DOCUMENT_INBOX_ROOTS = {}
if _inbox_org or _inbox_actor:
    if not all(__import__("re").fullmatch(r"[1-9][0-9]*", value)
               for value in (_inbox_org, _inbox_actor)):
        raise ImproperlyConfigured("Inbox organization and actor IDs must both be positive integers")
    DOCUMENT_INBOX_ORGANIZATION_ID = int(_inbox_org)
    DOCUMENT_INBOX_ACTOR_ID = int(_inbox_actor)
    _inbox_parent = DOCUMENT_STORAGE_ROOT / "inbox"
    _inbox_root = _inbox_parent / ("org-" + _inbox_org)
    for _child in (_inbox_parent, _inbox_root):
        no_symlinks(_child)
        try:
            _child.mkdir(mode=0o700)
        except FileExistsError:
            pass
        else:
            _child.chmod(0o700)  # Clear an inherited setgid bit on our new directory.
        if (not _child.is_dir() or _child.stat().st_uid != os.getuid()
                or _child.stat().st_mode & 0o077):
            raise ImproperlyConfigured("Inbox directories must be private and operator-owned")
    DOCUMENT_INBOX_ROOTS[DOCUMENT_INBOX_ORGANIZATION_ID] = _inbox_root

# Database: confined SQLite by default; PostgreSQL when all four DB_* are set
if _db_present:
    _db_conf = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": _db_name,
        "USER": _db_user,
        "PASSWORD": _db_password,
        "HOST": _db_host,
        "PORT": str(_db_port),
        "CONN_MAX_AGE": 60,
    }
    _db_opts = {"connect_timeout": 1, "options": "-c statement_timeout=500"}
    if _db_sslmode:
        _db_opts["sslmode"] = _db_sslmode
    if _db_sslrootcert:
        _db_opts["sslrootcert"] = _db_sslrootcert
    if _db_opts:
        _db_conf["OPTIONS"] = _db_opts
    DATABASES = {"default": _db_conf}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": str(_runtime_root / "db.sqlite3"),
            "OPTIONS": {"timeout": 0.5},
        }
    }

# Cache: in-memory only (no shared backend in supervised synthetic)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "supervised-synthetic",
    }
}

# Logging: confined log file only
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        },
    },
    "handlers": {
        "file": {
            "class": "logging.FileHandler",
            "filename": str(LOG_DIR / "supervised.log"),
            "formatter": "standard",
        },
    },
    "root": {"handlers": ["file"], "level": "INFO"},
    "loggers": {
        "django.db.backends": {"level": "WARNING", "handlers": ["file"], "propagate": False},
    },
}

# Login routing remains allauth
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/review/"
