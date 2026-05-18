from django.apps import AppConfig


class CompetitionsConfig(AppConfig):
    name = "competitions"

    def ready(self):
        """
        Called once when Django starts.
        Starts the background scheduler for automated competition transitions.

        Guard: only start in the main process — not in management commands,
        migrations, or Django's auto-reloader child process — to avoid
        duplicate scheduler instances.
        """
        import os
        import sys

        # Skip scheduler during migrations, shell, or test runs
        excluded_commands = {'migrate', 'makemigrations', 'shell', 'test', 'collectstatic'}
        if len(sys.argv) > 1 and sys.argv[1] in excluded_commands:
            return

        # In Django's dev server, ready() is called twice (reloader + main process).
        # RUN_MAIN is set only in the main process — skip the reloader.
        if os.environ.get('RUN_MAIN') == 'true' or not os.environ.get('RUN_MAIN'):
            try:
                from .scheduler import start_scheduler
                start_scheduler()
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(
                    f"Failed to start competition scheduler: {e}"
                )