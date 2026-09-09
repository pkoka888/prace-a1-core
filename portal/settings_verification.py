"""Isolated verification Django settings.

Database path resolves under runtime/portal/verification/ — never shared
with the review DB or any committed database.

To use for isolated verification:
    export DJANGO_SETTINGS_MODULE=portal.settings_verification
    python manage.py migrate --settings=portal.settings_verification
"""
from portal.settings import *

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "runtime/portal/verification/verification.sqlite3",
    }
}

ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "testserver",
]

DEBUG = True

M2_SYNTHETIC_ONLY = True

_sk = "synthetic-verification-key-not-for-production"
SECRET_KEY = _sk
