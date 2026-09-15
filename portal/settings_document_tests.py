"""Isolated synthetic integration tests; never production settings."""
from .settings import *  # noqa: F403

# Test isolation: the operator database must never be used for test
# database creation or teardown. Require explicit test-target
# configuration; never point Django database-creation or teardown tests
# at the operator database.
_test_socket = os.environ.get("DOCUMENT_TEST_PG_SOCKET")  # noqa: F405
_test_name = os.environ.get("DOCUMENT_TEST_PG_NAME")  # noqa: F405
_test_user = os.environ.get("DOCUMENT_TEST_PG_USER")  # noqa: F405
_test_host = os.environ.get("DOCUMENT_TEST_PG_HOST")  # noqa: F405
_test_port = os.environ.get("DOCUMENT_TEST_PG_PORT")  # noqa: F405

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
        _test_db_config["PORT"] = _test_port or "5432"
    DATABASES = {"default": _test_db_config}
else:
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}

# All fallback storage and cache state belongs to this synthetic test process.
# Individual cases may override storage with their own disposable fixtures.
import tempfile
import uuid

_synthetic_storage = tempfile.TemporaryDirectory(prefix="document-tests-")
DOCUMENT_STORAGE_ROOT = Path(_synthetic_storage.name)  # noqa: F405
MEDIA_ROOT = DOCUMENT_STORAGE_ROOT / "media"
STATIC_ROOT = DOCUMENT_STORAGE_ROOT / "static"
CACHE_DIR = DOCUMENT_STORAGE_ROOT / "cache"
TMP_DIR = DOCUMENT_STORAGE_ROOT / "tmp"
LOG_DIR = DOCUMENT_STORAGE_ROOT / "logs"
for _child in (MEDIA_ROOT, STATIC_ROOT, CACHE_DIR, TMP_DIR, LOG_DIR):
    _child.mkdir(mode=0o700, parents=True, exist_ok=True)
M2_SYNTHETIC_ONLY = True
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
CACHES = {"default": {
    "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    "LOCATION": "document-tests-" + uuid.uuid4().hex,
}}
