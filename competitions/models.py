import uuid
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from accounts.models import Gamer, ShopOwner, Account
from games.models import Game, Platform
from shops.models import Shop


class Competition(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('rejected', 'Rejected'),
        ('live', 'Live'),
        ('registration_open', 'Registration Open'),
        ('registration_closed', 'Registration Closed'),
        ('ongoing', 'Ongoing'),
        ('checkin_submitted', 'Check-in Submitted'),
        ('results_pending', 'Results Pending'),
        ('results_submitted', 'Results Submitted'),
        ('pending_prize_verification', 'Pending Prize Verification'),
        ('completed', 'Completed'),
    ]
    
    # Gamer-facing status display labels
    GAMER_STATUS_DISPLAY = {
        'draft': None,
        'pending': None,
        'rejected': None,
        'live': 'Coming Soon',
        'registration_open': 'Open',
        'registration_closed': 'Closed',
        'ongoing': 'Live',
        'checkin_submitted': 'Live',
        'results_pending': 'Completed',
        'results_submitted': 'Completed',
        'pending_prize_verification': 'Completed',
        'completed': 'Completed',
    }

    PRIZE_TYPE_CHOICES = [
        ('points', 'Points'),
        ('money', 'Money'),
        ('gift', 'Gift'),
    ]

    GENDER_RULE_CHOICES = [
        ('all', 'All (All Genders)'),
        ('male', 'Male (Male Gamers Only)'),
        ('female', 'Female (Female Gamers Only)'),
    ]

    # Identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    integer_id = models.PositiveIntegerField(unique=True, editable=False, db_index=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)

    # Core Details (set by shop owner or admin at creation)
    name = models.CharField(max_length=255)
    description = models.TextField()
    game = models.ForeignKey(Game, on_delete=models.PROTECT, related_name='competitions')
    platform = models.ForeignKey(Platform, on_delete=models.PROTECT, related_name='competitions')
    shop = models.ForeignKey(Shop, on_delete=models.PROTECT, related_name='competitions')
    scheduled_time = models.DateTimeField(
        help_text="The date and time the competition starts."
    )
    competition_end_time = models.DateTimeField(
        null=True, blank=True,
        help_text="The date and time the competition ends. Used to compute participation hours."
    )
    max_participants = models.PositiveIntegerField(
        help_text="Maximum number of participants allowed to register."
    )
    team_size = models.PositiveIntegerField(
        default=1,
        help_text="Number of players per team (currently default is 1 for individual)."
    )
    gender_rules = models.CharField(
        max_length=10,
        choices=GENDER_RULE_CHOICES,
        default='all',
        help_text="Gender restriction for the competition."
    )
    is_pwa_only = models.BooleanField(
        default=False,
        verbose_name="PWA Only",
        help_text="If True, the competition is only for PWA."
    )
    rules = models.TextField(
        blank=True,
        help_text="Competition rules. Age restriction and ID requirement will be appended automatically."
    )
    timeline = models.TextField(blank=True)

    # Entry Fee (set by shop owner; admin can edit during review)
    entry_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00,
        help_text="Entry fee for the competition. Admin can adjust during review."
    )

    # Age Restriction
    age_restricted = models.BooleanField(
        default=True,
        help_text="If True, only gamers aged 18 and above may register. ID verification required on competition day."
    )

    # Prize (set by admin on approval)
    prize_type = models.CharField(
        max_length=10, choices=PRIZE_TYPE_CHOICES,
        null=True, blank=True,
        help_text="Type of prize for this competition. Set by admin during approval."
    )

    # Points prize fields (used when prize_type = 'points')
    points_1st = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="XP/points awarded to 1st place."
    )
    points_2nd = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="XP/points awarded to 2nd place."
    )
    points_3rd = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="XP/points awarded to 3rd place."
    )
    points_4_to_10 = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="XP/points awarded to positions 4 through 10."
    )
    points_beyond_10 = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="XP/points awarded to positions 11 and beyond. Defaults to 0 if not set."
    )

    # Money prize fields (used when prize_type = 'money')
    # Only top 3 positions receive money prizes.
    prize_money_total = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        help_text="Total money prize pool for this competition."
    )
    prize_money_1st_pct = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Percentage of total prize money awarded to 1st place (e.g. 50 for 50%)."
    )
    prize_money_2nd_pct = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Percentage of total prize money awarded to 2nd place."
    )
    prize_money_3rd_pct = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Percentage of total prize money awarded to 3rd place."
    )

    # Gift prize fields (used when prize_type = 'gift')
    # Only top 3 positions receive gift prizes.
    prize_gift_description = models.TextField(
        null=True, blank=True,
        help_text="Description of the gift prize and how it is distributed across the top 3."
    )

    # Registration Window (set by admin on approval)
    registration_opens_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Date and time registration opens. Set by admin during approval."
    )
    registration_closes_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Date and time registration closes. Set by admin during approval."
    )

    # Ownership & Status
    created_by = models.ForeignKey(
        Account, on_delete=models.PROTECT,
        related_name='created_competitions',
        help_text="The admin or shop owner who created this competition."
    )
    status = models.CharField(
        max_length=30, choices=STATUS_CHOICES, default='draft', db_index=True
    )
    rejection_reason = models.TextField(
        blank=True,
        help_text="Reason provided by admin when rejecting a competition submission."
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Competition'
        verbose_name_plural = 'Competitions'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        from games.models import Counter
        from django.utils.text import slugify

        if not self.integer_id:
            self.integer_id = Counter.get_next_id('Competition')
        if not self.slug:
            self.slug = slugify(f"{self.name}-{self.shop.name}")
            # Ensure uniqueness
            original_slug = self.slug
            counter = 1
            while Competition.objects.filter(slug=self.slug).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
                    
        super().save(*args, **kwargs)

    def clean(self):
        # Platform must be supported by the selected game
        if self.platform and self.game:
            if not self.game.supported_platforms.filter(pk=self.platform.pk).exists():
                raise ValidationError(
                    "The selected platform is not supported by this game."
                )
        # Platform must be physically available at the shop (via consoles)
        if self.platform and self.shop:
            if not self.shop.consoles.filter(console_type=self.platform).exists():
                raise ValidationError(
                    "The selected platform is not available at this shop."
                )
        # Game must be in the shop's available games list
        if self.game and self.shop:
            if not self.shop.games_available.filter(pk=self.game.pk).exists():
                raise ValidationError(
                    "The selected game is not available at this shop."
                )
        # Registration window must be before the competition starts
        if self.registration_opens_at and self.registration_closes_at:
            if self.registration_opens_at >= self.registration_closes_at:
                raise ValidationError(
                    "Registration open time must be before registration close time."
                )
        if self.registration_closes_at and self.scheduled_time:
            if self.registration_closes_at >= self.scheduled_time:
                raise ValidationError(
                    "Registration must close before the competition starts."
                )
        # Competition end time must be after start time
        if self.competition_end_time and self.scheduled_time:
            if self.competition_end_time <= self.scheduled_time:
                raise ValidationError(
                    "Competition end time must be after the scheduled start time."
                )
        # Money prize percentages must not exceed 100%
        if self.prize_type == 'money':
            total_pct = (
                (self.prize_money_1st_pct or 0) +
                (self.prize_money_2nd_pct or 0) +
                (self.prize_money_3rd_pct or 0)
            )
            if total_pct > 100:
                raise ValidationError(
                    "Total prize money percentages for positions 1, 2, and 3 cannot exceed 100%."
                )

    # Helper Methods
    def is_registration_full(self):
        # Returns True if the maximum number of participants has been reached
        return self.registrations.filter(
            is_cancelled=False
        ).count() >= self.max_participants

    def registered_count(self):
        # Returns the current number of active registrations
        return self.registrations.filter(is_cancelled=False).count()

    def get_points_for_rank(self, rank):
        # Returns the points to be awarded for a given rank. Only applicable when prize_type is 'points'.
        if self.prize_type != 'points':
            return 0
        if rank == 1:
            return self.points_1st or 0
        elif rank == 2:
            return self.points_2nd or 0
        elif rank == 3:
            return self.points_3rd or 0
        elif 4 <= rank <= 10:
            return self.points_4_to_10 or 0
        else:
            return self.points_beyond_10 or 0

    def get_full_rules(self):
        """
        Returns the competition rules with default age/ID verification notices included.
        This is used for gamer display (read-only).
        """
        base_rules = self.rules.strip()
        
        # Check if the specific text is already in the rules to avoid duplication
        age_notice = "This competition is open to participants aged 18 and above only."
        id_notice = "A valid government-issued ID is required on the day of the competition for age verification, in addition to your unique registration code."
        
        # If rules already contain these notices, don't add them again
        if age_notice in base_rules and id_notice in base_rules:
            return base_rules
        
        # Build the combined rules
        rules_parts = [base_rules] if base_rules else []
        
        if self.age_restricted:
            if age_notice not in base_rules:
                rules_parts.append(age_notice)
            if id_notice not in base_rules:
                rules_parts.append(id_notice)
        
        if rules_parts:
            # If we have additional notices to add, format them
            if len(rules_parts) > 1:
                return rules_parts[0] + "\n\n--- IMPORTANT REQUIREMENTS ---\n" + "\n".join(rules_parts[1:])
            return rules_parts[0]
        
        return base_rules
    
    def get_rules_for_admin_editing(self):
        """
        Returns all rules (user-provided + default notices) for admin editing.
        The admin can modify the combined rules and save them as one final rules text.
        """
        base_rules = self.rules.strip()
        
        # Default notices that should always be included for age-restricted competitions
        age_notice = "This competition is open to participants aged 18 and above only."
        id_notice = "A valid government-issued ID is required on the day of the competition for age verification, in addition to your unique registration code."
        
        # Build combined rules for editing
        if self.age_restricted:
            default_notices = [age_notice, id_notice]
            # Check which notices are already in the rules
            notices_to_add = [n for n in default_notices if n not in base_rules]
            
            if notices_to_add:
                notice_section = "\n\n--- IMPORTANT REQUIREMENTS (Default) ---\n" + "\n".join(notices_to_add)
                if base_rules:
                    return base_rules + notice_section
                else:
                    return "--- IMPORTANT REQUIREMENTS (Default) ---\n" + "\n".join(notices_to_add)
        
        return base_rules
    
    def get_gamer_facing_status(self):
        """
        Returns the user-friendly status label for gamers.
        Maps internal status to gamer-visible status.
        Returns None if the status shouldn't be displayed to gamers.
        """
        return self.GAMER_STATUS_DISPLAY.get(self.status, self.status)

    def __str__(self):
        return self.name

    @property
    def generated_timeline(self):
        """
        Automatically generates a competition timeline based on the scheduled start time.
        Timeline events:
        - Check-in begins: 30 minutes before competition starts
        - Competition starts: At scheduled_time
        - Competition ends: At competition_end_time (or 2 hours after start if not set)
        - Results submission: 10 to 45 minutes after competition ends
        - Prize allocation: 1 to 48 hours after competition ends
        """
        start = self.scheduled_time
        end = self.competition_end_time or (start + timezone.timedelta(hours=2))
        
        check_in_start = start - timezone.timedelta(minutes=30)
        results_submit_min = end + timezone.timedelta(minutes=10)
        results_submit_max = end + timezone.timedelta(minutes=45)
        prize_allocation_min = end + timezone.timedelta(hours=1)
        prize_allocation_max = end + timezone.timedelta(hours=48)
        
        return {
            'check_in_start': check_in_start,
            'competition_start': start,
            'competition_end': end,
            'results_submit_min': results_submit_min,
            'results_submit_max': results_submit_max,
            'prize_allocation_min': prize_allocation_min,
            'prize_allocation_max': prize_allocation_max,
        }


class CompetitionRegistration(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    competition = models.ForeignKey(
        Competition, on_delete=models.CASCADE,
        related_name='registrations'
    )
    gamer = models.ForeignKey(
        Gamer, on_delete=models.PROTECT,
        related_name='competition_registrations'
    )
    unique_code = models.CharField(
        max_length=6, unique=True, editable=False,
        help_text="Unique 6-character code generated at registration."
    )
    registered_at = models.DateTimeField(auto_now_add=True)
    
    # Payment Tracking
    payment_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ],
        default='pending',
        help_text="Payment status for this registration."
    )
    payment_phone_number = models.CharField(
        max_length=15,
        blank=True, null=True,
        help_text="Phone number used to pay for this registration."
    )
    paid_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Timestamp when payment was completed."
    )

    # Check-in Tracking
    checked_in = models.BooleanField(default=False)
    checked_in_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Timestamp when the shop owner verified this gamer's code. Used for participation hours calculation."
    )
    code_expired = models.BooleanField(
        default=False,
        help_text="Set to True once the gamer has been verified and the code is no longer valid."
    )

    # No-show / Cancellation
    is_cancelled = models.BooleanField(
        default=False,
        help_text="Marks a registration as cancelled. Slot remains occupied."
    )

    class Meta:
        verbose_name = 'Competition Registration'
        verbose_name_plural = 'Competition Registrations'
        unique_together = ['competition', 'gamer']

    def save(self, *args, **kwargs):
        import string
        import random
        if not self.unique_code:
            # Generate a unique 6-character alphanumeric code
            chars = string.ascii_uppercase + string.digits
            while True:
                code = ''.join(random.choice(chars) for _ in range(6))
                if not CompetitionRegistration.objects.filter(unique_code=code).exists():
                    self.unique_code = code
                    break
        super().save(*args, **kwargs)

    def clean(self):
        # Only Gamer accounts may register
        # Shop owners can register only if the competition is NOT held at one of their shops
        # Only run validations if both gamer and competition are set
        if not self.gamer or not self.competition:
            return
        
        if self.gamer and self.competition:
            try:
                shop_owner = ShopOwner.objects.get(uid=self.gamer.uid)
                if shop_owner.shops.filter(pk=self.competition.shop.pk).exists():
                    raise ValidationError(
                        "Shop owners cannot register for competitions held at their own shop."
                    )
            except ShopOwner.DoesNotExist:
                pass  # Pure gamer — no restriction

            # Age restriction check
            if self.competition.age_restricted and self.gamer.date_of_birth:
                today = timezone.now().date()
                dob = self.gamer.date_of_birth
                age = today.year - dob.year - (
                    (today.month, today.day) < (dob.month, dob.day)
                )
                if age < 18:
                    raise ValidationError(
                        "You must be 18 years or older to register for this competition."
                    )
            
            # Gender restriction check
            if self.competition.gender_rules != 'all':
                if self.gamer.gender and self.gamer.gender != self.competition.gender_rules:
                    raise ValidationError(
                        f"This competition is only for {self.competition.get_gender_rules_display()} gamers."
                    )

    def participation_hours(self):
        """
        Computes the gamer's participation duration in hours.
        Calculated from check-in time to the competition's end time.
        Returns None if either timestamp is missing.
        """
        if self.checked_in_at and self.competition.competition_end_time:
            delta = self.competition.competition_end_time - self.checked_in_at
            return round(delta.total_seconds() / 3600, 2)
        return None

    def __str__(self):
        return f"{self.gamer} — {self.competition.name}"


class CompetitionResult(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    competition = models.ForeignKey(
        Competition, on_delete=models.CASCADE,
        related_name='results'
    )
    gamer = models.ForeignKey(
        Gamer, on_delete=models.PROTECT,
        related_name='competition_results'
    )

    # Result Details
    rank = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Final rank of the gamer. Null if the gamer was a no-show."
    )
    points_awarded = models.PositiveIntegerField(
        default=0,
        help_text="XP/points awarded to the gamer based on their rank and the competition's prize structure."
    )
    is_no_show = models.BooleanField(
        default=False,
        help_text="True if the gamer registered but did not show up. No points are awarded."
    )

    # Verification
    verified = models.BooleanField(
        default=False,
        help_text="True once the admin has verified the results."
    )
    verified_at = models.DateTimeField(null=True, blank=True)

    # Auto-allocation tracking
    auto_allocated = models.BooleanField(
        default=False,
        help_text="True if points were automatically allocated upon results submission (points prize type only)."
    )

    class Meta:
        verbose_name = 'Competition Result'
        verbose_name_plural = 'Competition Results'
        unique_together = ['competition', 'gamer']
        ordering = ['rank']

    def is_win(self):
        """
        A result is considered a win if the gamer finished in the top 3.
        Used for win rate calculations.
        """
        return self.rank is not None and self.rank <= 3

    def __str__(self):
        return f"{self.gamer} — Rank {self.rank} in {self.competition.name}"


class CompetitionAuditLog(models.Model):
    """Records admin and automated actions taken against a Competition."""
    ACTION_CHOICES = [
        ('approve', 'Approved'),
        ('reject', 'Rejected'),
        ('open_registration', 'Open Registration'),
        ('close_registration', 'Close Registration'),
        ('start', 'Competition Started'),
        ('end', 'Competition Ended'),
        ('confirm_checkins', 'Checkins Confirmed'),
        ('verify_results', 'Results Verified'),
        ('submit_results', 'Results Submitted'),
        ('submit_checkins', 'Checkins Submitted'),
        ('auto_transition', 'Automated Transition'),
        ('other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    competition = models.ForeignKey(Competition, on_delete=models.CASCADE, related_name='audit_logs')
    action = models.CharField(max_length=40, choices=ACTION_CHOICES)
    performed_by = models.ForeignKey(Account, null=True, blank=True, on_delete=models.SET_NULL)
    performed_by_label = models.CharField(max_length=255, blank=True, default='')
    performed_at = models.DateTimeField(auto_now_add=True)
    details = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Competition Audit Log'
        verbose_name_plural = 'Competition Audit Logs'
        ordering = ['-performed_at']

    def __str__(self):
        actor = self.performed_by_label or (self.performed_by.email if self.performed_by else 'system')
        return f"[{self.performed_at}] {self.competition} - {self.get_action_display()} by {actor}"