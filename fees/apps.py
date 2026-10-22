from django.apps import AppConfig


class FeesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "fees"

    def ready(self):
        from . import signals  # noqa: F401  (connects the signal handlers)
