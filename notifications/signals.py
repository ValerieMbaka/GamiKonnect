"""Signal handlers for notifications app."""
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.conf import settings
from .models import Notification, NotificationRecipient
from .pusher_client import broadcast_notification
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Notification)
def broadcast_notification_created(sender, instance, created, **kwargs):
    """
    Broadcast newly created notifications via Pusher.
    
    When an admin creates a system notification, broadcast it to all clients
    so they receive real-time updates without page refresh.
    
    System notifications (is_system=True) are broadcast globally.
    Regular notifications with recipients are sent to their private channels.
    """
    if not created:
        return
    
    notification_data = {
        'title': instance.title,
        'message': instance.message,
        'category': instance.get_category_display(),
        'importance': instance.get_importance_display(),
        'timestamp': instance.created_at.isoformat(),
    }
    
    try:
        if instance.is_system:
            # System notifications broadcast to everyone
            broadcast_notification('gamikonnect-global', 'new-system-notification', notification_data)
            logger.info(f"System notification broadcast: {instance.title}")
        else:
            # Regular notifications: we'll handle them via NotificationRecipient handler
            # to target specific users
            pass
    except Exception as e:
        logger.error(f"Failed to broadcast notification {instance.id}: {str(e)}")


@receiver(post_save, sender=NotificationRecipient)
def broadcast_to_recipient(sender, instance, created, **kwargs):
    """
    Broadcast notification to a specific recipient when NotificationRecipient is created.
    
    This ensures each user gets their targeted notifications in real-time.
    Targets private user channels so notifications are not seen by others.
    """
    if not created:
        return
    
    notification = instance.notification
    
    notification_data = {
        'title': notification.title,
        'message': notification.message,
        'category': notification.get_category_display(),
        'is_read': instance.is_read,
        'timestamp': notification.created_at.isoformat(),
    }
    
    try:
        # Determine which user and channel to target
        if instance.gamer:
            from .pusher_client import broadcast_user_notification
            broadcast_user_notification(instance.gamer.id, 'gamer', notification_data)
            logger.debug(f"Notification {notification.id} broadcast to gamer {instance.gamer.id}")
            
        elif instance.shop_owner:
            from .pusher_client import broadcast_user_notification
            broadcast_user_notification(instance.shop_owner.id, 'shop_owner', notification_data)
            logger.debug(f"Notification {notification.id} broadcast to shop_owner {instance.shop_owner.id}")
            
        elif instance.admin_user:
            from .pusher_client import broadcast_user_notification
            broadcast_user_notification(instance.admin_user.id, 'admin', notification_data)
            logger.debug(f"Notification {notification.id} broadcast to admin {instance.admin_user.id}")
            
    except Exception as e:
        logger.error(f"Failed to broadcast to recipient {instance.id}: {str(e)}")
