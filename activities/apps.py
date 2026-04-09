from django.apps import AppConfig

class ActivitiesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'activities'

    def ready(self):
        # Imports the signals so they start listening as soon as Django boots up
        import activities.signals