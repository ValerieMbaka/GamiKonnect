"""Management command to clean up expired notifications."""
from django.core.management.base import BaseCommand
from django.utils import timezone
from notifications.models import Notification, NotificationRecipient
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Delete expired notifications based on their importance level'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )
    
    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        now = timezone.now()
        
        # Find expired notifications
        expired_notifications = Notification.objects.filter(
            expires_at__lt=now
        )
        
        notification_count = expired_notifications.count()
        
        if notification_count == 0:
            self.stdout.write(
                self.style.SUCCESS('✓ No expired notifications to clean up')
            )
            return
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'[DRY RUN] Would delete {notification_count} notifications')
            )
            
            # Show breakdown by importance
            breakdown = expired_notifications.values('importance').annotate(
                Count('id')
            )
            for item in breakdown:
                self.stdout.write(
                    f"  - {item['importance']}: {item['id__count']} notifications"
                )
        else:
            # Delete recipients first
            recipient_count, _ = NotificationRecipient.objects.filter(
                notification__in=expired_notifications
            ).delete()
            
            # Delete notifications
            notification_delete_count, _ = expired_notifications.delete()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ Deleted {notification_delete_count} notifications '
                    f'and {recipient_count} recipient records'
                )
            )
            logger.info(
                f'Notification cleanup: deleted {notification_delete_count} notifications '
                f'and {recipient_count} recipient records'
            )
