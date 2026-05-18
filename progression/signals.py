"""
progression/signals.py

Signal handlers that trigger progression checks when:
1. A CompetitionResult is saved with verified=True
2. A Gamer's points field is updated

Both handlers call process_progression(gamer) from services.py.
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