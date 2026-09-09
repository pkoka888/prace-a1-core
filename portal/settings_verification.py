"""Synthetic verification settings with an explicitly confined optional test root.

PRACE_VERIFICATION_ROOT selects a private child of runtime/portal/verification/.
The default retains the existing verification harness location. No wrapper
settings modules or arbitrary database paths are needed for isolated tests.
"""
import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured
from portal.settings import *

_verification_base = BASE_DIR / "runtime/portal/verification"
_verification_root = Path(os.environ.get("PRACE_VERIFICATION_ROOT", str(_verification_base)))
if not _verification_root.is_absolute() or ".." in _verification_root.parts:
    raise ImproperlyConfigured("Verification root must be an absolute confined path")
try:
    _verification_root.relative_to(_verification_base)
except ValueError:
    raise ImproperlyConfigured("Verification root must remain under runtime/portal/verification") from None
for _path in (_verification_root, *_verification_root.parents):
    if _path.is_symlink():
        raise ImproperlyConfigured("Verification root must not traverse symlinks")
# Private umask also applies to SQLite journals and new database files.
os.umask(0o077)
_verification_base.mkdir(mode=0o700, parents=True, exist_ok=True)
_verification_root.mkdir(mode=0o700, parents=True, exist_ok=True)
for _path in (_verification_root,):
    if _path.stat().st_mode & 0o077 or _path.stat().st_uid != os.getuid():
        raise ImproperlyConfigured("Verification directories must be private and owned by the operator")
_verification_db = _verification_root / "verification.sqlite3"
if _verification_db.is_symlink():
    raise ImproperlyConfigured("Verification database must not be a symlink")
if _verification_db.exists() and (_verification_db.stat().st_mode & 0o077):
    raise ImproperlyConfigured("Verification database must be private")
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": _verification_db}}
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]
DEBUG = True
M2_SYNTHETIC_ONLY = True

# Reuse the base synthetic settings key policy; this module never provisions credentials.
