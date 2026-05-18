from django.apps import AppConfig


class ProgressionConfig(AppConfig):
    name = 'progression'
    verbose_name = 'Progression'

    def ready(self):
        """
        Connect signals when the app is ready.
        Import signals here to ensure they are registered.
        """
        import progression.signals  # noqa: F401