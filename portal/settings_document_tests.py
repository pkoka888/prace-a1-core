"""Isolated synthetic integration tests; never production settings."""
from .settings import *  # noqa: F403

# The test harness owns this ephemeral cluster under the project runtime directory.
_socket = os.environ.get("DOCUMENT_TEST_PG_SOCKET")  # noqa: F405
if _socket:
    _path = Path(_socket).resolve()  # noqa: F405
    if not _path.is_relative_to(BASE_DIR / "runtime"):  # noqa: F405
        raise RuntimeError("test PostgreSQL socket must be inside project runtime")
    DATABASES = {"default": {"ENGINE": "django.db.backends.postgresql", "NAME": "postgres",
                             "USER": os.environ["DOCUMENT_TEST_PG_USER"], "HOST": str(_path), "PORT": "55439"}}
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
