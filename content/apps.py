from django.apps import AppConfig


class ContentConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "content"
    verbose_name = "Content & Videos"

    def ready(self):
        """
        Wird beim Start von Django ausgeführt.
        Hier registrieren wir die Signals, indem wir das Modul importieren.
        """
        from . import signals  # noqa: F401  -> nur importieren, damit die Receiver registriert werden
