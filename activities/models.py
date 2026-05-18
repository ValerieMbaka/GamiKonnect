from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from accounts.models import Account


class Activity(models.Model):
    """
    Gamer-centric activity tracking for progression, achievements, and gaming milestones.
    """
    class ActivityTypes(models.TextChoices):
        # Progression
        LEVEL_UP = 'level_up', 'Level Up'
        ACHIEVEMENT_EARNED = 'achievement_earned', 'Achievement Earned'
        
        # Profile
        PROFILE_COMPLETED = 'profile_completed', 'Profile Completed'
        PROFILE_UPDATED = 'profile_updated', 'Profile Updated'
        GAME_ADDED = 'game_added', 'Game Added'
        GAME_REMOVED = 'game_removed', 'Game Removed'
        
        # Competitions
        COMPETITION_REGISTERED = 'competition_registered', 'Registered for Competition'
        COMPETITION_CHECKEDIN = 'competition_checkedin', 'Checked In to Competition'
        COMPETITION_COMPLETED = 'competition_completed', 'Competed in Tournament'
        COMPETITION_WON = 'competition_won', 'Won Competition'
        
        # Authentication
        LOGIN = 'login', 'Logged In'
        LOGOUT = 'logout', 'Logged Out'
        
        # System
        SYSTEM = 'system', 'System Event'
    
    gamer = models.ForeignKey(
        'accounts.Gamer',
        on_delete=models.CASCADE,
        related_name='activities'
    )
    activity_type = models.CharField(
        max_length=50,
        choices=ActivityTypes.choices,
        db_index=True
    )
    description = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Activity'
        verbose_name_plural = 'Activities'
        indexes = [
            models.Index(fields=['gamer', '-timestamp']),
            models.Index(fields=['activity_type', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.gamer.email} - {self.get_activity_type_display()}"


class ActivityLog(models.Model):
    """
    System-wide activity logging for audit trails and security events.
    """
    class ActionTypes(models.TextChoices):
        CREATE = 'CREATE', 'Created'
        UPDATE = 'UPDATE', 'Updated'
        DELETE = 'DELETE', 'Deleted'
        SECURITY = 'SECURITY', 'Security Event'
        SYSTEM = 'SYSTEM', 'System Event'
    
    actor = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activities_performed',
        help_text="The user who performed the action. Null if done by the system."
    )
    
    # Optional: Link to gamer for easier filtering
    gamer = models.ForeignKey(
        'accounts.Gamer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activity_logs',
        help_text="The gamer associated with this activity log (if applicable)."
    )
    
    action_type = models.CharField(
        max_length=20,
        choices=ActionTypes.choices,
        db_index=True
    )
    
    target_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    target_object_id = models.CharField(max_length=255, null=True, blank=True, help_text="Can store integer or UUID values")
    target = GenericForeignKey('target_content_type', 'target_object_id')
    
    description = models.TextField(
        help_text="A human-readable summary of the event."
    )
    meta_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Unstructured data about the event."
    )
    
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Activity Log'
        verbose_name_plural = 'Activity Logs'
        indexes = [
            models.Index(fields=['target_content_type', 'target_object_id']),
            models.Index(fields=['actor', 'action_type']),
            models.Index(fields=['gamer', '-timestamp']),
        ]
    
    def __str__(self):
        actor_name = self.actor.email if self.actor else "System"
        return f"[{self.action_type}] {actor_name} - {self.description[:50]}"


# --- PROGRESSION ENGINE MODELS ---

class Level(models.Model):
    name = models.CharField(max_length=50, unique=True, help_text="e.g., Amateur, Bronze, Gold")
    required_points = models.PositiveIntegerField(help_text="XP/Points required to reach this level")
    badge_image = models.ImageField(upload_to='badges/levels/', blank=True, null=True)
    order = models.PositiveIntegerField(
        unique=True,
        help_text="Numeric order of the level (e.g., 1 for Amateur, 2 for Beginner). Used for progression logic."
    )
    
    class Meta:
        verbose_name = 'Level'
        verbose_name_plural = 'Levels'
        ordering = ['order']
    
    def __str__(self):
        return f"{self.name} (Lvl {self.order})"


class Achievement(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    badge_image = models.ImageField(upload_to='badges/achievements/', blank=True, null=True)
    xp = models.PositiveIntegerField(default=0, help_text="XP awarded for unlocking this achievement")
    condition_key = models.CharField(
        max_length=50,
        unique=True,
        help_text="Internal key used by signals to trigger this (e.g., 'first_win', 'five_checkins')"
    )
    
    class Meta:
        verbose_name = 'Achievement'
        verbose_name_plural = 'Achievements'
    
    def __str__(self):
        return self.name


class GamerAchievement(models.Model):
    gamer = models.ForeignKey('accounts.Gamer', on_delete=models.CASCADE, related_name='unlocked_achievements')
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    unlocked_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Gamer Achievement'
        verbose_name_plural = 'Gamer Achievements'
        unique_together = ['gamer', 'achievement']
    
    def __str__(self):
        return f"{self.gamer} unlocked {self.achievement.name}"