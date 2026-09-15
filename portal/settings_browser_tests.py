"""Disposable synthetic browser tests, never a runtime service configuration."""
from .settings import *  # noqa: F403
import secrets
import tempfile

_runtime = BASE_DIR / "runtime" / "portal"  # noqa: F405
_runtime.mkdir(parents=True, exist_ok=True)
_browser_root = tempfile.TemporaryDirectory(prefix="infra-browser-", dir=_runtime)
# The parent runtime directory may carry a different setgid group. Newly
# owned disposable storage uses this process's mapped group, including userns.
os.chown(_browser_root.name, -1, os.getgid())
os.chmod(_browser_root.name, 0o700)
DEBUG = False
ALLOWED_HOSTS = ["127.0.0.1", "localhost", "testserver"]
DOCUMENT_STORAGE_ROOT = Path(_browser_root.name) / "storage"  # noqa: F405
MEDIA_ROOT = Path(_browser_root.name) / "media"  # noqa: F405

# Test isolation: optional explicit PostgreSQL test target. When set, the
# browser test settings use the isolated PostgreSQL target instead of
# SQLite. This prevents browser test runs from accidentally using the
# operator database.
_test_socket = os.environ.get("DOCUMENT_TEST_PG_SOCKET")  # noqa: F405
_test_name = os.environ.get("DOCUMENT_TEST_PG_NAME")  # noqa: F405
_test_user = os.environ.get("DOCUMENT_TEST_PG_USER")  # noqa: F405
_test_host = os.environ.get("DOCUMENT_TEST_PG_HOST")  # noqa: F405
_test_port = os.environ.get("DOCUMENT_TEST_PG_PORT", "5432")  # noqa: F405

if _test_socket or _test_name:
    if not _test_name:
        raise RuntimeError(
            "DOCUMENT_TEST_PG_NAME is required when DOCUMENT_TEST_PG_SOCKET is set"
        )
    if not _test_user:
        raise RuntimeError(
            "DOCUMENT_TEST_PG_USER is required for test PostgreSQL target"
        )
    _test_db_config = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": _test_name,
        "USER": _test_user,
    }
    if _test_socket:
        _path = Path(_test_socket).resolve()  # noqa: F405
        if not _path.is_relative_to(BASE_DIR / "runtime"):  # noqa: F405
            raise RuntimeError("test PostgreSQL socket must be inside project runtime")
        _test_db_config["HOST"] = str(_path)
        _test_db_config["PORT"] = os.environ.get("DOCUMENT_TEST_PG_PORT", "55439")  # noqa: F405
    elif _test_host:
        _test_db_config["HOST"] = _test_host
        _test_db_config["PORT"] = _test_port
    DATABASES = {"default": _test_db_config}
else:
    # Separate per-thread connections prevent concurrent crop/audit requests from
    # sharing the same in-memory SQLite connection during real browser tests.
    DATABASES = {"default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(Path(_browser_root.name) / "fixture.sqlite3"),
        "TEST": {"NAME": str(Path(_browser_root.name) / "browser-test.sqlite3")},
        "OPTIONS": {"timeout": 5},
    }}

_SK = secrets.token_urlsafe(48)
SECRET_KEY = _SK
M2_SYNTHETIC_ONLY = True
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Disposable readiness paths; never shared runtime defaults.
STATIC_ROOT = Path(_browser_root.name) / "static"
for _directory in (DOCUMENT_STORAGE_ROOT, MEDIA_ROOT, STATIC_ROOT):
    _directory.mkdir(mode=0o700, exist_ok=True)

PRACE_RUNTIME_MODE = "settings_browser_tests"
