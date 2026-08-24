"""Disposable ADR-001 settings. Never import these into the M2 application."""
SECRET_KEY = "synthetic-proof-only-not-for-production"
DEBUG = False
ALLOWED_HOSTS = ["testserver"]
ROOT_URLCONF = "prototypes.architecture.adr001.project.urls"
INSTALLED_APPS = ["django.contrib.auth", "django.contrib.contenttypes", "django.contrib.sessions"]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
MIDDLEWARE = ["django.contrib.sessions.middleware.SessionMiddleware", "django.contrib.auth.middleware.AuthenticationMiddleware"]
USE_TZ = True

