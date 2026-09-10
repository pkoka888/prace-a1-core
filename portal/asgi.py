"""ASGI entrypoint for the portal Django application.

The application object is the uvicorn/daphne/asgi import target. By default
it uses ``portal.settings`` (synthetic M2 with DEBUG=True for local dev).
Production deployment overrides via the standard environment contract:

    DJANGO_SETTINGS_MODULE=portal.settings_supervised_synthetic uvicorn portal.asgi:application

The supervised synthetic settings module is synthetic-only; production-real
deployment remains gated by real-data rules §14 and REV-003. No real-data
activation is performed by importing this module.

The portal application does not define asynchronous views; the ASGI entry is
provided for deployments that require an ASGI server (uvicorn/daphne) for
HTTP/2 or websockets. Channels is not installed; this module is HTTP-only.
"""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "portal.settings")

application = get_asgi_application()
