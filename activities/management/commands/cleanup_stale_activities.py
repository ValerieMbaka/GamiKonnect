"""
Management command to clean up stale activities and activity logs.

Cleanup rules:
- Login/Logout activities: Deleted 3 days after creation
- Competition registration activities: Deleted 1 week after creation
- Competition creation ActivityLogs: Deleted 1 week after creation
- All other activities: Deleted 1 week after creation

Usage:
    python manage.py cleanup_stale_activities
    python manage.py cleanup_stale_activities --dry-run
    python manage.py cleanup_stale_activities --days 14
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from activities.services import ActivityCleanupService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Delete stale activities and activity logs based on their type and age'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        now = timezone.now()

        if dry_run:
            self.stdout.write(
                self.style.WARNING('[DRY RUN] No data will be deleted')
            )
            self.stdout.write('')

        # Run the full cleanup
        stats = ActivityCleanupService.run_full_cleanup(dry_run=dry_run)

        # Display results
        self.stdout.write(self.style.MIGRATE_HEADING('Activity Cleanup Summary'))
        self.stdout.write('-' * 50)
        
        if dry_run:
            self.stdout.write(f"Login/Logout activities to delete:    {stats['login_logout_deleted']:>6}")
            self.stdout.write(f"Competition registrations to delete:  {stats['competition_registration_deleted']:>6}")
            self.stdout.write(f"Other activities to delete:           {stats['other_activities_deleted']:>6}")
            self.stdout.write(f"Competition creation logs to delete:  {stats['competition_creation_logs_deleted']:>6}")
            self.stdout.write(f"Other activity logs to delete:        {stats['other_logs_deleted']:>6}")
            self.stdout.write('-' * 50)
            self.stdout.write(f"Total items to delete:                {stats['total_activities_deleted'] + stats['total_logs_deleted']:>6}")
        else:
            self.stdout.write(self.style.SUCCESS(f"Deleted {stats['login_logout_deleted']} login/logout activities (older than 3 days)"))
            self.stdout.write(self.style.SUCCESS(f"Deleted {stats['competition_registration_deleted']} competition registration activities (older than 7 days)"))
            self.stdout.write(self.style.SUCCESS(f"Deleted {stats['other_activities_deleted']} other activities (older than 7 days)"))
            self.stdout.write(self.style.SUCCESS(f"Deleted {stats['competition_creation_logs_deleted']} competition creation logs (older than 7 days)"))
            self.stdout.write(self.style.SUCCESS(f"Deleted {stats['other_logs_deleted']} other activity logs (older than 7 days)"))
            self.stdout.write('-' * 50)
            self.stdout.write(
                self.style.SUCCESS(
                    f'Total: {stats["total_activities_deleted"]} activities '
                    f'and {stats["total_logs_deleted"]} activity logs cleaned up'
                )
            )

        # Log the results
        logger.info(
            f'Activity cleanup completed (dry_run={dry_run}): '
            f'{stats["login_logout_deleted"]} login/logout, '
            f'{stats["competition_registration_deleted"]} competition registrations, '
            f'{stats["other_activities_deleted"]} other activities, '
            f'{stats["competition_creation_logs_deleted"]} competition creation logs, '
            f'{stats["other_logs_deleted"]} other logs'
        )