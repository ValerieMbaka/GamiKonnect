"""Notification models for GamiKonnect."""
from django.db import models
from django.utils import timezone
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator, MaxValueValidator
import json
from datetime import timedelta


class NotificationCategory(models.TextChoices):
    """Categories for notifications."""
    GENERAL = "general", "General"
    SYSTEM = "system", "System"
    COMPETITION = "competition", "Competition"
    PAYMENT = "payment", "Payment"
    ACHIEVEMENT = "achievement", "Achievement"
    LEVEL_UP = "level_up", "Level Up"
    ACCOUNT = "account", "Account"


class NotificationImportance(models.TextChoices):
    """Importance levels for notifications (drives retention)."""
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    CRITICAL = "critical", "Critical"


class NotificationGroupCriteria(models.TextChoices):
    """Criteria types for predefined notification groups."""
    LEVEL = "level", "By Level"
    GAME = "game", "By Game"
    COMPETITION = "competition", "By Competition"
    CUSTOM = "custom", "Custom User List"
    PAYMENT_STATUS = "payment_status", "By Payment Status"
    ALL_USERS = "all_users", "All Users"


class DeliveryStatus(models.TextChoices):
    """Status of notification delivery to a user."""
    PENDING = "pending", "Pending"
    SENT = "sent", "Sent"
    FAILED = "failed", "Failed"


class Notification(models.Model):
    """
    Core notification template. A single notification can have multiple recipients
    tracked in NotificationRecipient.
    """
    id = models.BigAutoField(primary_key=True)
    
    # Categorization
    category = models.CharField(
        max_length=20,
        choices=NotificationCategory.choices,
        default=NotificationCategory.GENERAL,
        db_index=True
    )
    importance = models.CharField(
        max_length=10,
        choices=NotificationImportance.choices,
        default=NotificationImportance.MEDIUM,
        db_index=True
    )
    
    # Content
    title = models.CharField(max_length=255)
    message = models.TextField()
    message_template = models.TextField(
        blank=True,
        help_text="Template with merge fields like {{username}}, {{level}}, {{game}}"
    )
    
    # Metadata
    is_system = models.BooleanField(
        default=False,
        help_text="System notifications are created programmatically"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="When this notification expires and can be auto-deleted"
    )
    
    # Tracking
    total_recipients = models.IntegerField(
        default=0,
        help_text="Denormalized count of NotificationRecipient records"
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['category', '-created_at']),
            models.Index(fields=['importance', 'expires_at']),
        ]
    
    def __str__(self):
        return f"{self.get_category_display()}: {self.title}"
    
    def set_expiry(self):
        """Set expiry_at based on importance level."""
        now = timezone.now()
        if self.importance == NotificationImportance.CRITICAL:
            self.expires_at = now + timedelta(days=90)
        elif self.importance == NotificationImportance.HIGH:
            self.expires_at = now + timedelta(days=30)
        elif self.importance == NotificationImportance.MEDIUM:
            self.expires_at = now + timedelta(days=14)
        else:  # LOW
            self.expires_at = now + timedelta(days=7)


class NotificationRecipient(models.Model):
    """
    Tracks delivery and read status for each user receiving a notification.
    One Notification can have many NotificationRecipient records.
    Supports Gamer, ShopOwner, and Admin users.
    """
    id = models.BigAutoField(primary_key=True)
    
    # Foreign keys - support multiple user types
    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name='recipients'
    )
    gamer = models.ForeignKey(
        'accounts.Gamer',
        on_delete=models.CASCADE,
        related_name='notifications',
        null=True,
        blank=True
    )
    shop_owner = models.ForeignKey(
        'accounts.ShopOwner',
        on_delete=models.CASCADE,
        related_name='notifications',
        null=True,
        blank=True
    )
    admin_user = models.ForeignKey(
        'accounts.Account',
        on_delete=models.CASCADE,
        related_name='admin_notifications',
        null=True,
        blank=True,
        limit_choices_to={'is_staff': True}
    )
    
    # Read status
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Delivery tracking
    delivery_status = models.CharField(
        max_length=20,
        choices=DeliveryStatus.choices,
        default=DeliveryStatus.PENDING,
        db_index=True
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['gamer', 'is_read']),
            models.Index(fields=['gamer', '-created_at']),
            models.Index(fields=['gamer', 'delivery_status']),
            models.Index(fields=['shop_owner', 'is_read']),
            models.Index(fields=['shop_owner', '-created_at']),
            models.Index(fields=['admin_user', 'is_read']),
            models.Index(fields=['admin_user', '-created_at']),
        ]
    
    def __str__(self):
        user_display = self.gamer.custom_username if self.gamer else (self.shop_owner.first_name if self.shop_owner else self.admin_user.username)
        return f"{self.notification.title} → {user_display}"
    
    def mark_as_read(self):
        """Mark notification as read."""
        self.is_read = True
        self.read_at = timezone.now()
        self.save(update_fields=['is_read', 'read_at'])


class NotificationGroup(models.Model):
    """
    Predefined groups of users for targeting notifications.
    Supports different criteria types (level, game, competition, etc.).
    """
    id = models.BigAutoField(primary_key=True)
    
    # Metadata
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    
    # Criteria
    criteria_type = models.CharField(
        max_length=20,
        choices=NotificationGroupCriteria.choices,
        default=NotificationGroupCriteria.CUSTOM,
        db_index=True
    )
    criteria_data = models.JSONField(
        default=dict,
        help_text="JSON data defining the group. Format depends on criteria_type. "
                  "Examples: {'levels': [1,2,3]}, {'games': ['chess', 'scrabble']}, "
                  "{'user_ids': [1,2,3]}, {'competition_id': 5}, {'payment_status': 'completed'}"
    )
    
    # Metadata
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Denormalized count
    member_count = models.IntegerField(
        default=0,
        help_text="Cached count of users matching this group"
    )
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.get_criteria_type_display()})"


class NotificationSchedule(models.Model):
    """
    Schedule a notification for future delivery.
    Allows admins to create notifications that will be sent at a specified time.
    """
    id = models.BigAutoField(primary_key=True)
    
    # Foreign keys
    notification = models.OneToOneField(
        Notification,
        on_delete=models.CASCADE,
        related_name='schedule'
    )
    
    # Scheduling
    scheduled_at = models.DateTimeField(
        db_index=True,
        help_text="When this notification should be sent"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('scheduled', 'Scheduled'),
            ('sent', 'Sent'),
            ('cancelled', 'Cancelled'),
        ],
        default='scheduled',
        db_index=True
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['scheduled_at']
        indexes = [
            models.Index(fields=['status', 'scheduled_at']),
        ]
    
    def __str__(self):
        return f"{self.notification.title} @ {self.scheduled_at}"
