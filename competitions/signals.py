"""Signal handlers for competition-related notifications."""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender='competitions.CompetitionRegistration')
def on_competition_registration(sender, instance, created, update_fields, **kwargs):
    """Send dashboard notification when a registration payment is completed."""
    if instance.payment_status != 'completed':
        return

    if not created and update_fields and 'payment_status' not in update_fields:
        return

    try:
        from notifications.models import Notification
        from notifications.services import send_notification_to_users

        competition = instance.competition
        gamer = instance.gamer

        notification_text = (
            f"You've successfully registered for {competition.name}! "
            f"Your access code is {instance.unique_code}. "
            f"Competition starts at {competition.scheduled_time.strftime('%I:%M %p')}."
        )

        notification, _ = Notification.objects.get_or_create(
            title=f"Registered: {competition.name}",
            category="competition",
            importance="high",
            is_system=True,
            defaults={
                'message': notification_text,
            }
        )

        notification.set_expiry()
        notification.save()
        send_notification_to_users(notification, [gamer], send_email=False)

        logger.info("%s registered for %s", gamer.custom_username, competition.name)
    except Exception as e:
        logger.error("Error sending competition registration notification: %s", e)


@receiver(post_save, sender='competitions.CompetitionResult')
def on_competition_result_published(sender, instance, created, update_fields, **kwargs):
    """Send notification when competition results are verified."""
    if update_fields and 'verified' not in update_fields:
        return

    if not instance.verified:
        return

    try:
        from notifications.models import Notification
        from notifications.services import send_notification_to_users

        gamer = instance.gamer
        competition = instance.competition

        if instance.is_no_show:
            notification_text = f"You were marked as no-show for {competition.name}."
            importance = "medium"
        elif instance.rank == 1:
            notification_text = f"Congratulations! You won {competition.name}!"
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
        send_notification_to_users(notification, [gamer], send_email=False)

        logger.info("Results notification sent to %s for %s", gamer.custom_username, competition.name)
    except Exception as e:
        logger.error("Error sending competition results notification: %s", e)


@receiver(post_save, sender='competitions.Competition')
def on_competition_deployed(sender, instance, created, update_fields, **kwargs):
    """Notify eligible gamers when a competition is deployed for registration."""
    if created:
        return

    if update_fields and 'status' not in update_fields:
        return

    if instance.status != 'registration':
        return

    try:
        from notifications.models import Notification
        from notifications.services import send_notification_to_users

        eligible_gamers = instance.get_eligible_gamers()
        if not eligible_gamers.exists():
            return

        closes_at = instance.registration_closes_at.strftime('%I:%M %p') if instance.registration_closes_at else 'the deadline'
        notification_text = (
            f"A new competition is available: {instance.name}! "
            f"Register before {closes_at} to participate."
        )

        notification, _ = Notification.objects.get_or_create(
            title=f"New Competition: {instance.name}",
            category="competition",
            importance="high",
            is_system=True,
            defaults={'message': notification_text},
        )

        notification.set_expiry()
        notification.save()
        send_notification_to_users(notification, eligible_gamers, send_email=False)

        logger.info("New competition notification sent for %s", instance.name)
    except Exception as e:
        logger.error("Error sending new competition notification: %s", e)
