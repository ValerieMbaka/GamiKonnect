from django.apps import AppConfig


class FeedsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = "feeds"
    
    def ready(self):
        """Import signals when app is ready."""
        import feeds.signals
