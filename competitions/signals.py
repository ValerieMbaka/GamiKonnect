"""Signal handlers for competition-related notifications."""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender='competitions.CompetitionRegistration')
def on_competition_registration(sender, instance, created, **kwargs):
    """
    Send notification when user registers for a competition.
    """
    if not created:
        return
    
    try:
        from notifications.models import Notification, NotificationRecipient
        from notifications.services import send_notification_to_users
        
        competition = instance.competition
        gamer = instance.gamer
        
        # Create notification for registration
        notification_text = (
            f"You've successfully registered for {competition.name}! "
            f"Competition starts at {competition.scheduled_time.strftime('%I:%M %p')}. Good luck!"
        )
        
        notification, _ = Notification.objects.get_or_create(
            title=f"Registered: {competition.name}",
            category="competition",
            importance="high",
            is_system=True,
            defaults={
                'message': notification_text,
                'message_template': (
                    f"You've successfully registered for {{competition_name}}! "
                    f"Competition starts at {competition.scheduled_time.strftime('%I:%M %p')}. Good luck!"
                )
            }
        )
        
        notification.set_expiry()
        notification.save()
        
        # Create recipient for this user
        send_notification_to_users(notification, [gamer], send_email=True)
        
        logger.info(f"{gamer.custom_username} registered for {competition.name}")
    except Exception as e:
        logger.error(f"Error sending competition registration notification: {e}")


@receiver(post_save, sender='competitions.CompetitionResult')
def on_competition_result_published(sender, instance, created, update_fields, **kwargs):
    """
    Send notification when competition results are published (verified).
    """
    # Only process if verified changed to True
    if update_fields and 'verified' not in update_fields:
        return
    
    if not instance.verified:
        return
    
    try:
        from notifications.models import Notification, NotificationRecipient
        from notifications.services import send_notification_to_users
        
        gamer = instance.gamer
        competition = instance.competition_registration.competition
        
        # Different message based on result
        if instance.is_no_show:
            notification_text = f"You were marked as no-show for {competition.name}."
            importance = "medium"
        elif instance.rank == 1:
            notification_text = f"🏆 Congratulations! You won {competition.name}!"
            importance = "critical"
        else:
            notification_text = (
                f"Results for {competition.name} are now available. "
                f"You placed #{instance.rank}!"
            )
            importance = "high"
        
        notification, _ = Notification.objects.get_or_create(
            title=f"Results: {competition.name}",
            category="competition",
            importance=importance,
            is_system=True,
            defaults={'message': notification_text}
        )
        
        notification.set_expiry()
        notification.save()
        
        # Create recipient for this user
        send_notification_to_users(notification, [gamer], send_email=True)
        
        logger.info(f"Results notification sent to {gamer.custom_username} for {competition.name}")
    except Exception as e:
        logger.error(f"Error sending competition results notification: {e}")


@receiver(post_save, sender='competitions.Competition')
def on_competition_registration_opened(sender, instance, created, update_fields, **kwargs):
    """
    Send notification when competition registration opens.
    Targeted to eligible gamers (not created, only when status changes).
    """
    if created:
        return
    
    if update_fields and 'status' not in update_fields:
        return
    
    # Only notify when status changes to 'registration_open'
    if instance.status != 'registration_open':
        return
    
    try:
        from notifications.models import Notification, NotificationGroup
        from notifications.services import get_group_users, send_notification_to_users
        
        # Determine eligibility based on competition criteria
        eligible_gamers = instance.get_eligible_gamers()
        
        if not eligible_gamers.exists():
            return
        
        notification_text = (
            f"Registration is now open for {instance.name}! "
            f"Register before {instance.registration_closes_at.strftime('%I:%M %p')} to participate."
        )
        
        notification, _ = Notification.objects.get_or_create(
            title=f"Registration Open: {instance.name}",
            category="competition",
            importance="high",
            is_system=True,
            defaults={'message': notification_text}
        )
        
        notification.set_expiry()
        notification.save()
        
        # Send to eligible gamers
        send_notification_to_users(
            notification,
            eligible_gamers,
            send_email=True
        )
        
        logger.info(f"Registration open notification sent for {instance.name}")
    except Exception as e:
        logger.error(f"Error sending competition registration notification: {e}")
