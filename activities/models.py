from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from accounts.models import Account


class ActivityLog(models.fields):
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
    target_object_id = models.PositiveIntegerField(null=True, blank=True)
    target = GenericForeignKey('target_content_type', 'target_object_id')
    
    # Details
    description = models.TextField(
        help_text="A summary of the event (e.g., 'Updated opening hours for GamiKonnect')."
    )
    meta_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Unstructured data about the event (e.g., old vs new values, IP address)."
    )
    
    # Timestamp
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Activity Log'
        verbose_name_plural = 'Activity Logs'
        
        # Indexes make querying massive logs fast
        indexes = [
            models.Index(fields=['target_content_type', 'target_object_id']),
            models.Index(fields=['actor', 'action_type']),
        ]
    
    def __str__(self):
        actor_name = self.actor.email if self.actor else "System"
        return f"[{self.action_type}] {actor_name} - {self.description[:50]}"