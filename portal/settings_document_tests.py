"""Isolated synthetic integration tests; never production settings."""
from .settings import *  # noqa: F403

# Test isolation: the operator database must never be used for test
# database creation or teardown. Require explicit test-target
# configuration; never point Django database-creation or teardown tests
# at the operator database.
#
# Shared fail-closed contract: ANY DOCUMENT_TEST_PG_* variable presence
# requires a complete, consistent PostgreSQL test target. A lone variable
# (for example only DOCUMENT_TEST_PG_HOST) raises instead of silently
# falling back to SQLite.
from .test_pg_contract import resolve_test_postgres_target  # noqa: E402

_test_db_config = resolve_test_postgres_target(os.environ, runtime_base=str(BASE_DIR))  # noqa: F405
if _test_db_config:
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
