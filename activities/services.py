import logging
from django.db import transaction
from .models import Achievement, GamerAchievement, Activity, ActivityLog
from competitions.models import CompetitionResult, CompetitionAuditLog
from django.utils import timezone


def _display_name(account):
    if not account:
        return 'System'
    custom_username = getattr(account, 'custom_username', None)
    if custom_username:
        return custom_username
    first_name = getattr(account, 'first_name', '') or ''
    last_name = getattr(account, 'last_name', '') or ''
    full_name = f"{first_name} {last_name}".strip()
    return full_name or getattr(account, 'email', None) or getattr(account, 'username', 'User')


class ActivityFeedService:
    """Builds normalized dashboard activity feeds for each role."""

    GAMER_ACTIVITY_TYPES = {
        Activity.ActivityTypes.PROFILE_COMPLETED,
        Activity.ActivityTypes.PROFILE_UPDATED,
        Activity.ActivityTypes.GAME_ADDED,
        Activity.ActivityTypes.GAME_REMOVED,
        Activity.ActivityTypes.COMPETITION_REGISTERED,
        Activity.ActivityTypes.COMPETITION_CHECKEDIN,
        Activity.ActivityTypes.COMPETITION_COMPLETED,
        Activity.ActivityTypes.COMPETITION_WON,
        Activity.ActivityTypes.LEVEL_UP,
        Activity.ActivityTypes.ACHIEVEMENT_EARNED,
    }

    @staticmethod
    def get_gamer_feed(gamer, limit=5):
        activities = Activity.objects.filter(
            gamer=gamer,
            activity_type__in=ActivityFeedService.GAMER_ACTIVITY_TYPES,
        ).select_related('gamer').order_by('-timestamp')[:limit]
        return [ActivityFeedService._format_gamer_activity(item, gamer) for item in activities]

    @staticmethod
    def get_shop_owner_feed(shop_owner, limit=5):
        logs = ActivityLog.objects.filter(
            actor__uid=shop_owner.uid,
        ).select_related('actor', 'gamer').order_by('-timestamp')[:limit]
        return [ActivityFeedService._format_log_activity(item, shop_owner) for item in logs]

    @staticmethod
    def get_admin_feed(limit=5):
        logs = list(ActivityLog.objects.select_related('actor', 'gamer').order_by('-timestamp')[: limit * 2])
        audits = list(CompetitionAuditLog.objects.select_related('competition').order_by('-performed_at')[: limit * 2])

        feed = []
        for log in logs:
            feed.append(ActivityFeedService._format_log_activity(log, None, admin_view=True))
        for audit in audits:
            feed.append(ActivityFeedService._format_competition_audit(audit))

        feed.sort(key=lambda item: item['timestamp'], reverse=True)
        return feed[:limit]

    @staticmethod
    def _format_gamer_activity(activity, viewer):
        title_map = {
            Activity.ActivityTypes.PROFILE_COMPLETED: 'Profile Completed',
            Activity.ActivityTypes.PROFILE_UPDATED: 'Profile Updated',
            Activity.ActivityTypes.GAME_ADDED: 'Game Added',
            Activity.ActivityTypes.GAME_REMOVED: 'Game Removed',
            Activity.ActivityTypes.COMPETITION_REGISTERED: 'Competition Registered',
            Activity.ActivityTypes.COMPETITION_CHECKEDIN: 'Checked In',
            Activity.ActivityTypes.COMPETITION_COMPLETED: 'Competition Completed',
            Activity.ActivityTypes.COMPETITION_WON: 'Competition Won',
            Activity.ActivityTypes.LEVEL_UP: 'Level Up',
            Activity.ActivityTypes.ACHIEVEMENT_EARNED: 'Achievement Earned',
        }

        description = activity.description
        meta = activity.metadata or {}

        if activity.activity_type == Activity.ActivityTypes.PROFILE_COMPLETED:
            description = 'You completed your profile.'
        elif activity.activity_type == Activity.ActivityTypes.PROFILE_UPDATED:
            description = 'You updated your profile.'
        elif activity.activity_type == Activity.ActivityTypes.GAME_ADDED:
            description = f"You added {meta.get('game_name', 'a game')} to your profile."
        elif activity.activity_type == Activity.ActivityTypes.GAME_REMOVED:
            description = f"You removed {meta.get('game_name', 'a game')} from your profile."
        elif activity.activity_type == Activity.ActivityTypes.COMPETITION_REGISTERED:
            description = f"You registered for {meta.get('competition_name', description.replace('Registered for: ', ''))}."
        elif activity.activity_type == Activity.ActivityTypes.COMPETITION_CHECKEDIN:
            description = f"You checked in for {meta.get('competition_name', description.replace('Checked in for ', ''))}."
        elif activity.activity_type == Activity.ActivityTypes.COMPETITION_COMPLETED:
            rank = meta.get('rank')
            competition_name = meta.get('competition_name', description.replace('Completed ', '').split(':')[0])
            description = f"You completed {competition_name}"
            if rank:
                description += f" in rank #{rank}"
            description += '.'
        elif activity.activity_type == Activity.ActivityTypes.COMPETITION_WON:
            rank = meta.get('rank')
            competition_name = meta.get('competition_name', description.replace('Won ', '').split(':')[0])
            description = f"You won {competition_name}"
            if rank:
                description += f" with rank #{rank}"
            description += '!'
        elif activity.activity_type == Activity.ActivityTypes.LEVEL_UP:
            description = f"You leveled up to {meta.get('level_name', 'a new level')}!"
        elif activity.activity_type == Activity.ActivityTypes.ACHIEVEMENT_EARNED:
            description = f"You unlocked {meta.get('achievement_name', 'an achievement')}!"

        return {
            'title': title_map.get(activity.activity_type, activity.get_activity_type_display()),
            'description': description,
            'meta': ActivityFeedService._format_meta(meta),
            'timestamp': activity.timestamp,
            'icon': ActivityFeedService._icon_for_gamer_activity(activity.activity_type),
            'is_self': True,
            'source': 'gamer',
        }

    @staticmethod
    def _format_log_activity(log, viewer, admin_view=False):
        actor = log.actor
        actor_name = _display_name(actor)
        is_self = viewer is not None and actor is not None and getattr(viewer, 'uid', None) == getattr(actor, 'uid', None)

        description = log.description
        if is_self:
            description = ActivityFeedService._make_self_description(log)
        elif admin_view:
            description = ActivityFeedService._make_admin_description(log)

        return {
            'title': ActivityFeedService._log_title(log, is_self=is_self),
            'description': description,
            'meta': ActivityFeedService._format_meta(log.meta_data),
            'timestamp': log.timestamp,
            'icon': ActivityFeedService._icon_for_log(log),
            'is_self': is_self,
            'actor_name': 'You' if is_self else actor_name,
            'source': 'admin',
        }

    @staticmethod
    def _format_competition_audit(audit):
        details = audit.details or ''
        if audit.performed_by_label:
            actor_name = audit.performed_by_label
            is_self = False
        else:
            actor_name = 'System'
            is_self = False

        return {
            'title': audit.get_action_display(),
            'description': details or audit.get_action_display(),
            'meta': audit.competition.name,
            'timestamp': audit.performed_at,
            'icon': ActivityFeedService._icon_for_audit(audit.action),
            'is_self': is_self,
            'actor_name': actor_name,
            'source': 'audit',
        }

    @staticmethod
    def _log_title(log, is_self=False):
        if log.action_type == ActivityLog.ActionTypes.CREATE:
            return 'Created'
        if log.action_type == ActivityLog.ActionTypes.UPDATE:
            return 'Updated'
        if log.action_type == ActivityLog.ActionTypes.DELETE:
            return 'Deleted'
        if log.action_type == ActivityLog.ActionTypes.SECURITY:
            return 'Security Event'
        if log.action_type == ActivityLog.ActionTypes.SYSTEM:
            return 'System Event'
        return log.get_action_type_display()

    @staticmethod
    def _make_self_description(log):
        if log.action_type == ActivityLog.ActionTypes.CREATE:
            return f"You created {ActivityFeedService._target_label(log)}."
        if log.action_type == ActivityLog.ActionTypes.UPDATE:
            return f"You updated {ActivityFeedService._target_label(log)}."
        if log.action_type == ActivityLog.ActionTypes.DELETE:
            return f"You deleted {ActivityFeedService._target_label(log)}."
        if log.action_type == ActivityLog.ActionTypes.SECURITY:
            return f"You triggered a security event: {log.description}."
        if log.action_type == ActivityLog.ActionTypes.SYSTEM:
            return f"You performed: {log.description}."
        return f"You {log.description[:1].lower()}{log.description[1:]}"

    @staticmethod
    def _make_admin_description(log):
        target_label = ActivityFeedService._target_label(log)
        actor_name = _display_name(log.actor)
        if log.action_type == ActivityLog.ActionTypes.CREATE and 'registration' in log.description.lower():
            return f"New registration: {log.description}"
        if log.action_type == ActivityLog.ActionTypes.DELETE and 'account' in log.description.lower():
            return f"Account deleted: {target_label or log.description}"
        if log.action_type == ActivityLog.ActionTypes.CREATE:
            return f"{actor_name} created {target_label}."
        if log.action_type == ActivityLog.ActionTypes.UPDATE:
            return f"{actor_name} updated {target_label}."
        if log.action_type == ActivityLog.ActionTypes.DELETE:
            return f"{actor_name} deleted {target_label}."
        return log.description

    @staticmethod
    def _target_label(log):
        target = getattr(log, 'target', None)
        if not target:
            return ''
        if hasattr(target, 'name'):
            return target.name
        if hasattr(target, 'title'):
            return target.title
        if hasattr(target, 'email'):
            return target.email
        return str(target)

    @staticmethod
    def _format_meta(meta):
        if not meta:
            return ''
        if isinstance(meta, dict):
            parts = []
            for key, value in meta.items():
                if value in (None, '', [], {}):
                    continue
                parts.append(f"{key.replace('_', ' ').title()}: {value}")
            return ' · '.join(parts)
        return str(meta)

    @staticmethod
    def _icon_for_gamer_activity(activity_type):
        return {
            Activity.ActivityTypes.PROFILE_COMPLETED: 'fas fa-user-check',
            Activity.ActivityTypes.PROFILE_UPDATED: 'fas fa-user-edit',
            Activity.ActivityTypes.GAME_ADDED: 'fas fa-gamepad',
            Activity.ActivityTypes.GAME_REMOVED: 'fas fa-gamepad',
            Activity.ActivityTypes.COMPETITION_REGISTERED: 'fas fa-ticket-alt',
            Activity.ActivityTypes.COMPETITION_CHECKEDIN: 'fas fa-check-circle',
            Activity.ActivityTypes.COMPETITION_COMPLETED: 'fas fa-flag-checkered',
            Activity.ActivityTypes.COMPETITION_WON: 'fas fa-trophy',
            Activity.ActivityTypes.LEVEL_UP: 'fas fa-level-up-alt',
            Activity.ActivityTypes.ACHIEVEMENT_EARNED: 'fas fa-medal',
        }.get(activity_type, 'fas fa-bolt')

    @staticmethod
    def _icon_for_log(log):
        return {
            ActivityLog.ActionTypes.CREATE: 'fas fa-plus-circle',
            ActivityLog.ActionTypes.UPDATE: 'fas fa-pen',
            ActivityLog.ActionTypes.DELETE: 'fas fa-trash',
            ActivityLog.ActionTypes.SECURITY: 'fas fa-shield-alt',
            ActivityLog.ActionTypes.SYSTEM: 'fas fa-cogs',
        }.get(log.action_type, 'fas fa-circle')

    @staticmethod
    def _icon_for_audit(action):
        return {
            'approve': 'fas fa-check-circle',
            'reject': 'fas fa-times-circle',
            'open_registration': 'fas fa-door-open',
            'close_registration': 'fas fa-door-closed',
            'start': 'fas fa-play-circle',
            'end': 'fas fa-flag-checkered',
            'confirm_checkins': 'fas fa-user-check',
            'verify_results': 'fas fa-award',
            'submit_results': 'fas fa-upload',
            'submit_checkins': 'fas fa-clipboard-check',
        }.get(action, 'fas fa-bell')

logger = logging.getLogger(__name__)


class AchievementService:
    
    @staticmethod
    def check_post_competition_unlocks(gamer):
        """
        Scans a gamer's history to see if they qualify for any new achievements.
        """
        unlocked_new = False
        
        earned_ids = GamerAchievement.objects.filter(gamer=gamer).values_list('achievement_id', flat=True)
        available_achievements = Achievement.objects.exclude(id__in=earned_ids)
        
        for achievement in available_achievements:
            if AchievementService._evaluate_condition(gamer, achievement.condition_key):
                AchievementService._unlock_achievement(gamer, achievement)
                unlocked_new = True
        
        return unlocked_new
    
    @staticmethod
    def _evaluate_condition(gamer, condition_key):
        """
        The Master Rulebook. Matches the string 'condition_key' from the database
        to the actual Django QuerySet logic.
        """
        if condition_key == 'first_win':
            return CompetitionResult.objects.filter(gamer=gamer, rank__lte=3).exists()
        
        elif condition_key == 'five_wins':
            return CompetitionResult.objects.filter(gamer=gamer, rank__lte=3).count() >= 5
        
        elif condition_key == 'first_tournament':
            return CompetitionResult.objects.filter(gamer=gamer, is_no_show=False).exists()
        
        elif condition_key == 'five_tournaments':
            return CompetitionResult.objects.filter(gamer=gamer, is_no_show=False).count() >= 5
        
        return False
    
    @staticmethod
    @transaction.atomic
    def _unlock_achievement(gamer, achievement):
        """
        Securely grants the achievement and logs the Activity.
        """
        GamerAchievement.objects.create(gamer=gamer, achievement=achievement)
        
        Activity.objects.create(
            gamer=gamer,
            activity_type=Activity.ActivityTypes.ACHIEVEMENT_EARNED,
            description=f"Unlocked Achievement: {achievement.name}!",
            metadata={
                'achievement_name': achievement.name,
                'badge_url': achievement.badge_image.url if achievement.badge_image else None
            }
        )
        
        logger.info(f"ACHIEVEMENT UNLOCKED: {gamer.custom_username} earned '{achievement.name}'!")