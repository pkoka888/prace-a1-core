from django.apps import AppConfig


class Release1AConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "portal.release1a"

    def ready(self):
        from . import signals  # noqa: F401

