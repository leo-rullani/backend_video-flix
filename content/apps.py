from django.apps import AppConfig


class ContentConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "content"
    verbose_name = "Content & Videos"

    def ready(self):
        """
        Called when Django starts.
        We import signals so the receivers are registered.
        """
        from . import signals  # noqa: F401