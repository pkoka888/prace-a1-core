"""Synthetic review environment settings.

Inherits from portal.settings. Overrides:
- SECRET_KEY: loaded from secrets/synthetic_review.key (never committed, generated once)
- DATABASES: runtime/portal/synthetic-review/db.sqlite3 (never committed)
- M2_SYNTHETIC_ONLY: True (hard gate)
- ALLOWED_HOSTS: includes loopback and a placeholder for the future Tailscale review hostname

To start the review server:
    export SYNTHETIC_REVIEW_SECRET=$(cat secrets/synthetic_review.key)
    export DJANGO_SETTINGS_MODULE=portal.settings_synthetic_review
    python manage.py runserver 127.0.0.1:8000 --noreload
"""
from portal.settings import *

SECRET_KEY = __import__("os").environ.get(
    "SYNTHETIC_REVIEW_SECRET",
    "",
)
if not SECRET_KEY:
    raise ValueError(
        "SYNTHETIC_REVIEW_SECRET environment variable is not set. "
        "Run scripts/generate_synthetic_review_secret.sh first, then "
        "export SYNTHETIC_REVIEW_SECRET=$(cat secrets/synthetic_review.key)"
    )

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "runtime/portal/synthetic-review/db.sqlite3",
    }
}

ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "testserver",
    "prace-v-nemecku-internal.tvoje.info",
]
