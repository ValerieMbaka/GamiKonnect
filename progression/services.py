"""
progression/services.py

Core progression logic for GamiKonnect.
All level-up and achievement checks run through this module.

Entry points:
    process_progression(gamer)  — called from signals after XP changes
                                  or competition results are verified.
"""

import logging
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------

def process_progression(gamer):
    """
    Main entry point called from signals.
    Runs level check first, then achievement checks.
    Both run inside a single atomic transaction.
    """
    try:
        with transaction.atomic():
            check_and_update_level(gamer)
            check_and_award_achievements(gamer)
    except Exception as e:
        logger.error(f"Progression processing error for gamer {gamer.id}: {e}")


# ---------------------------------------------------------------------------
# Level Check
# ---------------------------------------------------------------------------

def check_and_update_level(gamer):
    """
    Finds the highest Level the gamer qualifies for based on their XP.
    If it differs from their current level, updates GamerLevel and
    creates a dashboard notification.
    """
    from .models import Level, GamerLevel

    new_level = Level.get_level_for_xp(gamer.points)
    if new_level is None:
        return  # No levels defined yet

    try:
        gamer_level = GamerLevel.objects.get(gamer=gamer)
        if gamer_level.level.order < new_level.order:
            # Level up!
            old_level_name = gamer_level.level.name
            gamer_level.level = new_level
            gamer_level.reached_at = timezone.now()
            gamer_level.save()
            _notify_level_up(gamer, new_level, old_level_name)
            logger.info(f"[Progression] {gamer} levelled up to {new_level.name}.")
    except GamerLevel.DoesNotExist:
        # First level assignment
        GamerLevel.objects.create(gamer=gamer, level=new_level)
        _notify_level_up(gamer, new_level, previous_level_name=None)
        logger.info(f"[Progression] {gamer} assigned initial level: {new_level.name}.")


# ---------------------------------------------------------------------------
# Achievement Checks
# ---------------------------------------------------------------------------

def check_and_award_achievements(gamer):
    """
    Iterates through all active achievements and awards any the gamer
    qualifies for but hasn't earned yet.
    """
    from .models import Achievement, GamerAchievement

    active_achievements = Achievement.objects.filter(is_active=True)

    # Get IDs of achievements the gamer already has
    already_earned = set(
        GamerAchievement.objects.filter(gamer=gamer).values_list('achievement_id', flat=True)
    )

    for achievement in active_achievements:
        if achievement.id in already_earned:
            continue

        if _qualifies_for_achievement(gamer, achievement):
            award_achievement(gamer, achievement)


def _qualifies_for_achievement(gamer, achievement):
    """
    Returns True if the gamer meets the condition for the given achievement.
    """
    from competitions.models import CompetitionRegistration, CompetitionResult

    try:
        metric_key = getattr(achievement, 'metric_key', None)
        target_value = getattr(achievement, 'target_value', None)

        if metric_key:
            stats = _get_gamer_stats(gamer)
            stat_value = getattr(stats, metric_key, None)
            if stat_value is not None:
                return stat_value >= (target_value or 0)

        atype = achievement.achievement_type
        threshold = achievement.threshold

        if atype == 'first_registration':
            return CompetitionRegistration.objects.filter(
                gamer=gamer, is_cancelled=False
            ).exists()

        elif atype == 'first_completion':
            return CompetitionResult.objects.filter(
                gamer=gamer, verified=True, is_no_show=False
            ).exists()

        elif atype == 'first_win':
            return CompetitionResult.objects.filter(
                gamer=gamer, verified=True, rank__lte=3
            ).exists()

        elif atype == 'competition_count':
            count = CompetitionResult.objects.filter(
                gamer=gamer, verified=True, is_no_show=False
            ).count()
            return count >= threshold

        elif atype == 'xp_milestone':
            return gamer.points >= threshold

        elif atype == 'level_reached':
            try:
                from .models import GamerLevel
                gamer_level = GamerLevel.objects.get(gamer=gamer)
                return gamer_level.level.order >= threshold
            except Exception:
                return False

        elif atype == 'participation_hours':
            total_hours = _get_total_participation_hours(gamer)
            return total_hours >= threshold

    except Exception as e:
        logger.error(f"[Progression] Error checking achievement '{achievement.name}' for {gamer}: {e}")
        return False

    return False


def _get_gamer_stats(gamer):
    """
    Returns the gamer's progression stats row, creating it on demand.
    """
    from .models import GamerStats

    stats, _ = GamerStats.objects.get_or_create(gamer=gamer)
    return stats


def _get_total_participation_hours(gamer):
    """
    Computes total participation hours across all checked-in competitions.
    Sums (competition_end_time - checked_in_at) for each valid registration.
    """
    from competitions.models import CompetitionRegistration

    registrations = CompetitionRegistration.objects.filter(
        gamer=gamer,
        checked_in=True,
        checked_in_at__isnull=False,
        competition__competition_end_time__isnull=False
    ).select_related('competition')

    total_seconds = 0
    for reg in registrations:
        delta = reg.competition.competition_end_time - reg.checked_in_at
        if delta.total_seconds() > 0:
            total_seconds += delta.total_seconds()

    return total_seconds / 3600  # Convert to hours


# ---------------------------------------------------------------------------
# Award Achievement
# ---------------------------------------------------------------------------

def award_achievement(gamer, achievement):
    """
    Creates a GamerAchievement record and triggers a dashboard notification.
    Safe to call multiple times — will not duplicate due to unique_together.
    """
    from .models import GamerAchievement

    _, created = GamerAchievement.objects.get_or_create(
        gamer=gamer,
        achievement=achievement,
        defaults={'earned_at': timezone.now()}
    )

    if created:
        _notify_achievement(gamer, achievement)
        logger.info(f"[Progression] Achievement '{achievement.name}' awarded to {gamer}.")


# ---------------------------------------------------------------------------
# Dashboard Notifications
# ---------------------------------------------------------------------------

def _notify_level_up(gamer, new_level, previous_level_name=None):
    """
    Creates a dashboard activity notification for a level-up event.
    Uses the existing activities app.
    """
    try:
        from activities.models import Activity
        if previous_level_name:
            description = (
                f"You levelled up from {previous_level_name} to {new_level.name}! "
                f"Keep competing to reach the next tier."
            )
        else:
            description = f"Welcome to GamiKonnect! You've been assigned the {new_level.name} level."

        Activity.objects.create(
            gamer=gamer,
            activity_type='level_up',
            description=description,
            metadata={
                'level_name': new_level.name,
                'level_order': new_level.order,
                'min_xp': new_level.min_xp,
                'color_hex': new_level.color_hex,
                'badge_image': new_level.badge_image.url if new_level.badge_image else None,
            }
        )
    except Exception as e:
        logger.error(f"[Progression] Failed to create level-up notification for {gamer}: {e}")


def _notify_achievement(gamer, achievement):
    """
    Creates a dashboard activity notification for an achievement award.
    Uses the existing activities app.
    """
    try:
        from activities.models import Activity
        Activity.objects.create(
            gamer=gamer,
            activity_type='achievement_earned',
            description=f"You earned the '{achievement.name}' achievement! {achievement.description}",
            metadata={
                'achievement_name': achievement.name,
                'achievement_category': getattr(achievement, 'category', None),
                'metric_key': getattr(achievement, 'metric_key', None),
                'target_value': getattr(achievement, 'target_value', None),
                'xp_reward': getattr(achievement, 'xp_reward', None),
                'achievement_type': getattr(achievement, 'achievement_type', None),
                'badge_image': achievement.badge_image.url if achievement.badge_image else None,
            }
        )
    except Exception as e:
        logger.error(f"[Progression] Failed to create achievement notification for {gamer}: {e}")


# ---------------------------------------------------------------------------
# Leaderboard Queries
# ---------------------------------------------------------------------------

def get_global_leaderboard(limit=None):
    """
    Returns all gamers ordered by total XP descending.
    Annotates each gamer with their current level.
    """
    from accounts.models import Gamer
    from django.db.models import Prefetch
    from .models import GamerLevel

    gamers = Gamer.objects.filter(
        profile_completed=True
    ).select_related(
        'gamer_level__level'
    ).order_by('-points')

    if limit:
        gamers = gamers[:limit]

    return gamers


def get_game_leaderboard(game, limit=None):
    """
    Returns gamers ranked by total XP earned specifically from competitions
    of the given game.
    """
    from django.db.models import Sum
    from competitions.models import CompetitionResult

    qs = CompetitionResult.objects.filter(
        competition__game=game,
        verified=True,
        is_no_show=False
    ).values(
        'gamer'
    ).annotate(
        game_xp=Sum('points_awarded')
    ).order_by('-game_xp')

    if limit:
        qs = qs[:limit]

    # Resolve gamer objects with level data
    from accounts.models import Gamer
    gamer_ids = [item['gamer'] for item in qs]
    gamer_map = {
        g.id: g for g in Gamer.objects.filter(
            id__in=gamer_ids
        ).select_related('gamer_level__level')
    }

    results = []
    for item in qs:
        gamer = gamer_map.get(item['gamer'])
        if gamer:
            results.append({
                'gamer': gamer,
                'game_xp': item['game_xp'],
            })

    return results


def get_gamer_global_rank(gamer):
    """
    Returns the gamer's position in the global leaderboard (1-indexed).
    """
    from accounts.models import Gamer
    rank = Gamer.objects.filter(
        profile_completed=True,
        points__gt=gamer.points
    ).count() + 1
    return rank


def get_gamer_game_rank(gamer, game):
    """
    Returns the gamer's position in the per-game leaderboard (1-indexed).
    """
    from django.db.models import Sum
    from competitions.models import CompetitionResult

    gamer_xp = CompetitionResult.objects.filter(
        gamer=gamer, competition__game=game, verified=True, is_no_show=False
    ).aggregate(total=Sum('points_awarded'))['total'] or 0

    higher_count = CompetitionResult.objects.filter(
        competition__game=game, verified=True, is_no_show=False
    ).values('gamer').annotate(
        total=Sum('points_awarded')
    ).filter(total__gt=gamer_xp).count()

    return higher_count + 1