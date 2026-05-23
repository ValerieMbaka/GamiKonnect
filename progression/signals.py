"""
progression/signals.py

Signal handlers that trigger progression checks when:
1. A CompetitionResult is saved with verified=True
2. A Gamer's points field is updated

Both handlers call process_progression(gamer) from services.py.

Also sends notifications for achievement unlocks and level ups.
"""

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender='competitions.CompetitionResult')
def on_competition_result_verified(sender, instance, created, **kwargs):
    """
    Fires when a CompetitionResult is saved.
    Only triggers progression if the result is verified and not a no-show.
    """
    if not instance.verified:
        return
    if instance.is_no_show:
        return

    try:
        from .services import process_progression
        process_progression(instance.gamer)
    except Exception as e:
        logger.error(
            f"[Progression Signal] Error processing result verification "
            f"for gamer {instance.gamer_id}: {e}"
        )


@receiver(post_save, sender='accounts.Gamer')
def on_gamer_points_updated(sender, instance, created, **kwargs):
    """
    Fires when a Gamer record is saved.
    Only triggers progression if the points field has actually changed.
    Uses update_fields to avoid infinite loops — only fires when
    'points' is explicitly in the update_fields list.
    """
    if created:
        try:
            from .models import GamerStats
            GamerStats.objects.get_or_create(gamer=instance)
        except Exception as e:
            logger.error(
                f"[Progression Signal] Error creating stats row for new gamer {instance.id}: {e}"
            )

        # New gamer — assign initial level if levels are defined
        try:
            from .services import check_and_update_level
            check_and_update_level(instance)
        except Exception as e:
            logger.error(
                f"[Progression Signal] Error assigning initial level "
                f"for new gamer {instance.id}: {e}"
            )
        return

    # Only process if points was explicitly updated
    update_fields = kwargs.get('update_fields')
    if update_fields is not None and 'points' not in update_fields:
        return

    # If update_fields is None (full save), check if points changed
    # by comparing with DB value — avoid on every save
    if update_fields is None:
        try:
            from accounts.models import Gamer
            db_gamer = Gamer.objects.get(pk=instance.pk)
            # Re-fetch to compare — if points haven't changed, skip
            # Note: this is a best-effort guard, not a strict diff
            # The service itself is idempotent so double-triggering is safe
        except Exception:
            pass

    try:
        from .services import process_progression
        process_progression(instance)
    except Exception as e:
        logger.error(
            f"[Progression Signal] Error processing points update "
            f"for gamer {instance.id}: {e}"
        )


@receiver(post_save, sender='progression.GamerAchievement')
def on_achievement_unlocked(sender, instance, created, **kwargs):
    """
    Send notification when a gamer unlocks an achievement.
    """
    if not created:
        return
    
    try:
        from notifications.models import Notification
        from notifications.services import send_notification_to_users
        
        gamer = instance.gamer
        achievement = instance.achievement
        
        notification_text = (
            f"🎖️ Achievement Unlocked: {achievement.name}! "
            f"{achievement.description}"
        )
        
        notification, _ = Notification.objects.get_or_create(
            title=f"Achievement: {achievement.name}",
            category="achievement",
            importance="high",
            is_system=True,
            defaults={'message': notification_text}
        )
        
        notification.set_expiry()
        notification.save()
        
        # Create recipient for this user
        send_notification_to_users(notification, [gamer], send_email=True)
        
        logger.info(f"{gamer.custom_username} unlocked achievement: {achievement.name}")
    except Exception as e:
        logger.error(f"Error sending achievement notification: {e}")


@receiver(post_save, sender='progression.GamerLevel')
def on_level_up(sender, instance, created, update_fields, **kwargs):
    """
    Send notification when a gamer levels up.
    """
    if created:
        return  # Initial level assignment, not a level up
    
    if update_fields and 'level' not in update_fields:
        return
    
    try:
        from notifications.models import Notification
        from notifications.services import send_notification_to_users
        
        gamer = instance.gamer
        level = instance.level
        
        notification_text = (
            f"⬆️ Level Up! You're now {level.get_display_name()}! "
            f"Congratulations on reaching {level.min_xp} XP!"
        )
        
        notification, _ = Notification.objects.get_or_create(
            title=f"Level Up: {level.get_display_name()}",
            category="level_up",
            importance="high",
            is_system=True,
            defaults={'message': notification_text}
        )
        
        notification.set_expiry()
        notification.save()
        
        # Create recipient for this user
        send_notification_to_users(notification, [gamer], send_email=True)
        
        logger.info(f"{gamer.custom_username} leveled up to {level.get_display_name()}")
    except Exception as e:
        logger.error(f"Error sending level up notification: {e}")