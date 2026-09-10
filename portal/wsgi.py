"""WSGI entrypoint for the portal Django application.

The application object is the gunicorn/uWSGI import target. By default it
uses ``portal.settings`` (synthetic M2 with DEBUG=True for local dev) so a
developer can run the application without further configuration. Production
deployment overrides the settings module via the standard Django environment
contract:

    DJANGO_SETTINGS_MODULE=portal.settings_supervised_synthetic gunicorn portal.wsgi:application

The supervised synthetic settings module is synthetic-only; production-real
deployment remains gated by real-data rules §14 and REV-003. No real-data
activation is performed by importing this module.
"""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "portal.settings")

application = get_wsgi_application()
