from django.apps import AppConfig
import logging
import os
import sys


logger = logging.getLogger(__name__)


class CompetitionsConfig(AppConfig):
    name = "competitions"
    _scheduler_started = False

    @classmethod
    def _start_scheduler_once(cls):
        """Start scheduler only once per process."""
        if cls._scheduler_started:
            return

        try:
            from .scheduler import start_scheduler
            start_scheduler()
            cls._scheduler_started = True
        except Exception as e:
            logger.error(f"Failed to start competition scheduler: {e}")

    def ready(self):
        """
        Called once when Django starts.
        Starts the background scheduler for automated competition transitions.

        Guard: only start in the main process — not in management commands,
        migrations, or Django's auto-reloader child process — to avoid
        duplicate scheduler instances.
        """
        # Import signals first
        import competitions.signals  # noqa

        # Skip scheduler for manage.py commands that should not run background jobs.
        # Keep it only for runserver in development.
        if (
            len(sys.argv) > 1
            and sys.argv[0].endswith('manage.py')
            and sys.argv[1] != 'runserver'
        ):
            return

        # In Django's dev server, ready() is called twice (reloader + worker process).
        # Only continue in the worker process.
        is_runserver = len(sys.argv) > 1 and sys.argv[1] == 'runserver'
        if is_runserver:
            if os.environ.get('RUN_MAIN') != 'true':
                return

        # Defer scheduler startup to first HTTP request to avoid DB access in ready().
        from django.core.signals import request_started

        request_started.connect(
            lambda **kwargs: self._start_scheduler_once(),
            dispatch_uid='competitions.start_scheduler_on_first_request',
        )