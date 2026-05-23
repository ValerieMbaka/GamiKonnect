import uuid
from django.db import models
from django.utils import timezone
from accounts.models import Gamer


class Level(models.Model):
    """
    Defines the XP-based progression tiers.
    A gamer's current level is always derived from their total XP —
    it is never stored directly on the Gamer model.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True, help_text="e.g. Amateur, Bronze, Champion")
    min_xp = models.PositiveIntegerField(
        unique=True,
        help_text="Minimum cumulative XP required to reach this level."
    )
    badge_image = models.ImageField(
        upload_to='progression/level_badges/',
        blank=True, null=True,
        help_text="Badge image displayed on the gamer's profile and dashboard."
    )
    color_hex = models.CharField(
        max_length=7,
        default='#35A8F0',
        help_text="Hex colour used to style this level's badge in the UI (e.g. #FFD700)."
    )
    order = models.PositiveIntegerField(
        unique=True,
        help_text="Sort order — lower number = lower level. Used to determine rank progression."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Level'
        verbose_name_plural = 'Levels'
        ordering = ['order']

    def __str__(self):
        return f"{self.name} (≥ {self.min_xp} XP)"

    @classmethod
    def get_level_for_xp(cls, xp):
        """
        Returns the highest Level whose min_xp is <= the given XP value.
        Returns None if no level has been defined yet.
        """
        return cls.objects.filter(min_xp__lte=xp).order_by('-min_xp').first()

    @classmethod
    def get_next_level(cls, current_level):
        """
        Returns the next Level above the current one, or None if at max.
        """
        if current_level is None:
            return cls.objects.order_by('order').first()
        return cls.objects.filter(order__gt=current_level.order).order_by('order').first()


class GamerStats(models.Model):
    """
    Hyper-optimized tracker for player progression.
    These counters let the progression engine evaluate unlock rules
    without running expensive aggregate queries on every profile load.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gamer = models.OneToOneField(Gamer, on_delete=models.CASCADE, related_name='progression_stats')

    # Community & Social
    communities_joined = models.PositiveIntegerField(default=0)
    gamers_invited = models.PositiveIntegerField(default=0)
    comments_made = models.PositiveIntegerField(default=0)

    # Content Quality (Anti-Spam Metrics)
    posts_made = models.PositiveIntegerField(default=0)
    posts_with_10_likes = models.PositiveIntegerField(default=0)
    posts_with_25_likes = models.PositiveIntegerField(default=0)
    posts_with_75_likes = models.PositiveIntegerField(default=0)

    # Competitions (Single-Day)
    competitions_joined = models.PositiveIntegerField(default=0)
    competitions_won = models.PositiveIntegerField(default=0)

    # Leagues (Community Tournaments)
    leagues_joined = models.PositiveIntegerField(default=0)
    leagues_won = models.PositiveIntegerField(default=0)

    # Loyalty
    login_streak_days = models.PositiveIntegerField(default=0)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Gamer Stat'
        verbose_name_plural = 'Gamer Stats'

    def __str__(self):
        display_name = self.gamer.custom_username or self.gamer.get_full_name() or self.gamer.email
        return f"Stats for {display_name}"


class Achievement(models.Model):
    """
    Catalogue of all possible achievements on GamiKonnect.
    Achievements are auto-awarded by the progression service when
    a gamer meets the defined condition.
    """

    CATEGORY_CHOICES = [
        ('ONBOARDING', 'Onboarding & Setup'),
        ('COMMUNITY', 'Community & Networking'),
        ('CONTENT', 'Content Creation'),
        ('SOCIAL', 'Social Interaction'),
        ('COMPETITION', 'Competitions'),
        ('LEAGUE', 'Community Leagues'),
        ('PROGRESSION', 'Level & XP Progression'),
        ('LOYALTY', 'Loyalty & Streaks'),
        ('HIDDEN', 'Hidden / Secret'),
        ('SEASONAL', 'Seasonal Events'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(help_text="Shown to the gamer when they earn this achievement.")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='ONBOARDING')
    metric_key = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="The exact field name in GamerStats (e.g. 'competitions_won')",
    )
    target_value = models.PositiveIntegerField(
        default=1,
        help_text="The number required to unlock this achievement",
    )
    xp_reward = models.PositiveIntegerField(
        default=50,
        help_text="XP awarded to the gamer when unlocked",
    )
    badge_image = models.ImageField(
        upload_to='progression/achievement_badges/',
        blank=True, null=True
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Inactive achievements will not be awarded to gamers."
    )
    is_hidden = models.BooleanField(
        default=False,
        help_text="Hide from users until unlocked?",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    achievement_type = models.CharField(
        max_length=30,
        choices=[
            ('first_registration', 'First Competition Registered'),
            ('first_completion', 'First Competition Completed'),
            ('first_win', 'First Win (Top 3 Finish)'),
            ('competition_count', 'Compete N Times'),
            ('xp_milestone', 'Reach XP Milestone'),
            ('level_reached', 'Reach a Level'),
            ('participation_hours', 'Participate for N Hours'),
        ],
        db_index=True,
        blank=True,
        null=True,
    )
    threshold = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = 'Achievement'
        verbose_name_plural = 'Achievements'
        ordering = ['category', 'target_value']

    def __str__(self):
        return f"[{self.get_category_display()}] {self.name}"

    @property
    def xp(self):
        return self.xp_reward

    @property
    def condition_key(self):
        return self.metric_key or self.achievement_type


class GamerAchievement(models.Model):
    """
    Records an achievement earned by a specific gamer.
    Each gamer can earn each achievement only once.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gamer = models.ForeignKey(
        Gamer,
        on_delete=models.CASCADE,
        related_name='achievements'
    )
    achievement = models.ForeignKey(
        Achievement,
        on_delete=models.CASCADE,
        related_name='earned_by'
    )
    earned_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = 'Gamer Achievement'
        verbose_name_plural = 'Gamer Achievements'
        unique_together = ['gamer', 'achievement']
        ordering = ['-earned_at']

    def __str__(self):
        return f"{self.gamer} — {self.achievement.name}"


class GamerLevel(models.Model):
    """
    Tracks the current level of a gamer.
    Updated whenever the gamer earns XP and crosses a level threshold.
    One record per gamer — created on first level assignment.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gamer = models.OneToOneField(
        Gamer,
        on_delete=models.CASCADE,
        related_name='gamer_level'
    )
    level = models.ForeignKey(
        Level,
        on_delete=models.PROTECT,
        related_name='gamers_at_level'
    )
    reached_at = models.DateTimeField(
        default=timezone.now,
        help_text="When the gamer reached this level."
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Gamer Level'
        verbose_name_plural = 'Gamer Levels'

    def __str__(self):
        return f"{self.gamer} — {self.level.name}"