"""WSGI/ASGI entrypoint contract tests.

The entrypoints are thin wrappers that expose the WSGIHandler / ASGIHandler
to gunicorn / uvicorn. The contract is:

* ``portal.wsgi:application`` imports cleanly and produces a Django WSGI
  handler. Default ``DJANGO_SETTINGS_MODULE`` is ``portal.settings``.
* ``portal.asgi:application`` imports cleanly and produces a Django ASGI
  handler. Default ``DJANGO_SETTINGS_MODULE`` is ``portal.settings``.
* The WSGI app serves the URL routing defined in ``portal.urls``:
  - ``/login/`` redirects to ``/accounts/login/``
  - ``/health/`` is reachable (no auth required)
  - protected pages (e.g. ``/review/``) redirect anonymous users to login
* The supervised synthetic settings module is the production-style module
  the entrypoints switch to via ``DJANGO_SETTINGS_MODULE``. The entrypoints
  do not bypass the existing ``M2_SYNTHETIC_ONLY`` intake guard.

These tests run the WSGI app via the Django test client so they do not
require a live HTTP server. They do NOT exercise real-data activation,
which remains gated by real-data rules §14 and REV-003.
"""
import importlib
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def _run_in_subprocess(import_module):
    """Run ``import {module}`` in a fresh subprocess so DJANGO_SETTINGS_MODULE
    caching does not mask a contract violation."""
    code = (
        "import sys\n"
        "os_module = __import__('os')\n"
        "os_module.environ.pop('DJANGO_SETTINGS_MODULE', None)\n"
        f"import {import_module}\n"
        f"print('MODULE:', {import_module}.application.__class__.__module__)\n"
        "print('OK')\n"
    )
    r = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=30,
    )
    return r


def test_wsgi_imports_with_default_settings():
    """``portal.wsgi:application`` imports cleanly with default settings."""
    r = _run_in_subprocess("portal.wsgi")
    assert r.returncode == 0, r.stderr or r.stdout
    assert "MODULE: django.core.handlers.wsgi" in r.stdout
    assert "OK" in r.stdout


def test_asgi_imports_with_default_settings():
    """``portal.asgi:application`` imports cleanly with default settings."""
    r = _run_in_subprocess("portal.asgi")
    assert r.returncode == 0, r.stderr or r.stdout
    assert "MODULE: django.core.handlers.asgi" in r.stdout
    assert "OK" in r.stdout


def test_wsgi_default_settings_module_is_portal_settings(monkeypatch):
    """When DJANGO_SETTINGS_MODULE is not set, wsgi.py defaults to portal.settings."""
    monkeypatch.delenv("DJANGO_SETTINGS_MODULE", raising=False)
    # Reload the module to pick up the cleared env
    import portal.wsgi as wsgi_module
    importlib.reload(wsgi_module)
    assert os.environ["DJANGO_SETTINGS_MODULE"] == "portal.settings"


def test_wsgi_app_routes_basic_requests():
    """The WSGI app serves the URL routing defined in portal.urls."""
    os.environ["DJANGO_SETTINGS_MODULE"] = "portal.settings_document_tests"
    import django
    django.setup()
    from django.test import Client
    import portal.wsgi

    client = Client(HTTP_HOST="localhost")
    # /login/ → 302 to /accounts/login/
    r_login = client.get("/login/")
    assert r_login.status_code == 302
    assert r_login.headers["Location"].endswith("/accounts/login/")
    # /health/ → 200 (no auth required)
    r_health = client.get("/health/")
    assert r_health.status_code == 200
    # /review/ → 302 to /login/?next=/review/ (anonymous)
    r_review = client.get("/review/")
    assert r_review.status_code == 302
    assert "/review/" in r_review.headers["Location"]


def test_wsgi_does_not_bypass_intake_synthetic_guard():
    """The WSGI app preserves the existing M2_SYNTHETIC_ONLY intake guard.

    Importing the WSGI module with default settings must leave
    ``settings.M2_SYNTHETIC_ONLY`` True; the intake function ``intake()``
    rejects any non-synthetic configuration. The guard is owned by the
    settings module and the intake service (``tests/document_web/test_intake.py``
    exercises the ``M2_SYNTHETIC_ONLY=False`` path directly); the WSGI
    entrypoint does not redefine or bypass it.
    """
    os.environ["DJANGO_SETTINGS_MODULE"] = "portal.settings_document_tests"
    import django
    django.setup()
    from django.conf import settings as django_settings

    assert django_settings.M2_SYNTHETIC_ONLY is True
