"""Signal handlers for account-related notifications."""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.apps import apps

logger = logging.getLogger(__name__)


@receiver(post_save, sender='accounts.Gamer')
def on_user_profile_completed(sender, instance, created, update_fields, **kwargs):
    """
    Send notification when a gamer completes their profile.
    Profile is considered complete when all required fields are filled.
    """
    # Only process if profile_completed changed to True
    if update_fields and 'profile_completed' not in update_fields:
        return
    
    if not instance.profile_completed:
        return
    
    try:
        from notifications.models import Notification, NotificationRecipient
        from notifications.services import send_notification_to_users
        
        # Create notification for profile completion
        notification, created = Notification.objects.get_or_create(
            title="Profile Complete!",
            category="account",
            importance="medium",
            is_system=True,
            defaults={
                'message': f"Great job, {instance.custom_username}! Your profile is now complete. "
                          "You can now participate in competitions and earn points.",
                'message_template': "Great job, {{username}}! Your profile is now complete. "
                                  "You can now participate in competitions and earn points."
            }
        )
        
        if created:
            notification.set_expiry()
            notification.save()
        
        # Create recipient for this user
        if not NotificationRecipient.objects.filter(
            notification=notification,
            user=instance
        ).exists():
            send_notification_to_users(notification, [instance], send_email=True)
        
        logger.info(f"Profile completion notification sent to {instance.custom_username}")
    except Exception as e:
        logger.error(f"Error sending profile completion notification: {e}")


@receiver(post_save, sender='accounts.Gamer')
def on_gamer_registered(sender, instance, created, **kwargs):
    """
    Send welcome notification when a new gamer registers.
    """
    if not created:
        return
    
    try:
        from notifications.models import Notification, NotificationRecipient
        from notifications.services import send_notification_to_users
        
        # Create welcome notification
        notification, _ = Notification.objects.get_or_create(
            title="Welcome to GamiKonnect!",
            category="account",
            importance="high",
            is_system=True,
            defaults={
                'message': f"Welcome to GamiKonnect, {instance.custom_username}! "
                          "Start by completing your profile, then join competitions to earn points and unlock achievements.",
                'message_template': "Welcome to GamiKonnect, {{username}}! "
                                  "Start by completing your profile, then join competitions to earn points and unlock achievements."
            }
        )
        
        notification.set_expiry()
        notification.save()
        
        # Create recipient for this user
        send_notification_to_users(notification, [instance], send_email=True)
        
        logger.info(f"Welcome notification sent to new gamer {instance.custom_username}")
    except Exception as e:
        logger.error(f"Error sending welcome notification: {e}")


@receiver(post_save, sender='accounts.Account')
def on_account_creation(sender, instance, created, **kwargs):
    """
    Track account creation (parent class signal for both Gamer and ShopOwner).
    """
    if not created:
        return
    
    try:
        from activities.signals import security_event_triggered
        
        # Log security event
        security_event_triggered.send(
            sender=sender,
            actor=instance,
            action='account_created',
            metadata={'role': instance.__class__.__name__}
        )
    except Exception as e:
        logger.error(f"Error in account creation signal: {e}")
