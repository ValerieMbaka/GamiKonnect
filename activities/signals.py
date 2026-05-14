import logging
from django.dispatch import Signal, receiver
from django.db.models.signals import post_save
from django.contrib.contenttypes.models import ContentType
from .models import ActivityLog, Level, Activity
from accounts.models import Gamer
from competitions.models import CompetitionRegistration, CompetitionResult
from .models import GamerAchievement

logger = logging.getLogger(__name__)

# --- CUSTOM BROADCASTERS ---
security_event_triggered = Signal()
system_event_triggered = Signal()


# --- RECEIVERS ---
@receiver(security_event_triggered)
def log_security_event(sender, actor, description, meta_data=None, **kwargs):
    meta_data = meta_data or {}
    ActivityLog.objects.create(
        actor=actor,
        action_type=ActivityLog.ActionTypes.SECURITY,
        description=description,
        meta_data=meta_data
    )


@receiver(system_event_triggered)
def log_system_event(sender, actor, target, description, meta_data=None, **kwargs):
    meta_data = meta_data or {}
    ActivityLog.objects.create(
        actor=actor,
        action_type=ActivityLog.ActionTypes.SYSTEM,
        target=target,
        description=description,
        meta_data=meta_data
    )


# --- PROGRESSION ENGINE SIGNAL ---
@receiver(post_save, sender=Gamer)
def auto_level_up_gamer(sender, instance, created, update_fields, **kwargs):
    """
    Listens for updates to a Gamer's points. Automatically upgrades their level
    if they cross a new XP threshold, and logs the Activity.
    """
    if not created and (update_fields is None or 'points' not in update_fields):
        return
    
    qualifying_level = Level.objects.filter(
        required_points__lte=instance.points
    ).order_by('-order').first()
    
    if qualifying_level and instance.current_level != qualifying_level:
        if not instance.current_level or qualifying_level.order > instance.current_level.order:
            # Safely update the DB without triggering another save signal
            Gamer.objects.filter(pk=instance.pk).update(current_level=qualifying_level)
            
            # Log the activity
            Activity.objects.create(
                gamer=instance,
                activity_type=Activity.ActivityTypes.LEVEL_UP,
                description=f"Leveled up to {qualifying_level.name}!",
                metadata={'level_name': qualifying_level.name, 'level_order': qualifying_level.order}
            )
            
            logger.info(f"PROGRESSION: {instance.custom_username} leveled up to {qualifying_level.name}!")


# --- COMPETITION & ACHIEVEMENT ACTIVITY LOGGING ---
@receiver(post_save, sender=CompetitionRegistration)
def log_competition_registration(sender, instance, created, **kwargs):
    if not created:
        return
    Activity.objects.create(
        gamer=instance.gamer,
        activity_type=Activity.ActivityTypes.COMPETITION_REGISTERED,
        description=f"Registered for: {instance.competition.name}",
        metadata={'competition_id': str(instance.competition.id), 'registration_id': str(instance.id)}
    )


@receiver(post_save, sender=CompetitionResult)
def log_competition_result(sender, instance, created, **kwargs):
    # Log when a result is created or when points are awarded/verified
    if created:
        activity_type = Activity.ActivityTypes.COMPETITION_COMPLETED
        desc = f"Completed {instance.competition.name}: rank #{instance.rank}"
        
        # If they won (top 3), log it as a win
        if instance.rank and instance.rank <= 3:
            activity_type = Activity.ActivityTypes.COMPETITION_WON
            desc = f"Won {instance.competition.name}: rank #{instance.rank}!"
    else:
        activity_type = Activity.ActivityTypes.COMPETITION_COMPLETED
        desc = f"Result updated for {instance.competition.name}: rank #{instance.rank}"

    Activity.objects.create(
        gamer=instance.gamer,
        activity_type=activity_type,
        description=desc,
        metadata={
            'competition_id': str(instance.competition.id),
            'result_id': str(instance.id),
            'rank': instance.rank,
            'points_awarded': instance.points_awarded,
            'verified': instance.verified,
        }
    )


@receiver(post_save, sender=GamerAchievement)
def log_achievement_unlocked(sender, instance, created, **kwargs):
    if not created:
        return
    Activity.objects.create(
        gamer=instance.gamer,
        activity_type=Activity.ActivityTypes.ACHIEVEMENT_EARNED,
        description=f"Unlocked: {instance.achievement.name}",
        metadata={
            'achievement_id': instance.achievement.id,
            'achievement_key': instance.achievement.condition_key,
            'achievement_xp': instance.achievement.xp
        }
    )