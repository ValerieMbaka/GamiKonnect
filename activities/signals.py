from django.dispatch import Signal, receiver
from django.contrib.contenttypes.models import ContentType
from .models import ActivityLog

# Broadcasters
security_event_triggered = Signal()
system_event_triggered = Signal()


# Receivers
@receiver(security_event_triggered)
def log_security_event(sender, actor, description, meta_data=None, **kwargs):
    # Listens for security events (e.g., password changes, logins)
    meta_data = meta_data or {}
    
    ActivityLog.objects.create(
        actor=actor,
        action_type=ActivityLog.ActionTypes.SECURITY,
        description=description,
        meta_data=meta_data
    )


@receiver(system_event_triggered)
def log_system_event(sender, actor, target, description, meta_data=None, **kwargs):
    # Listens for admin approvals, rejections, etc.
    meta_data = meta_data or {}
    
    ActivityLog.objects.create(
        actor=actor,
        action_type=ActivityLog.ActionTypes.SYSTEM,
        target=target,
        description=description,
        meta_data=meta_data
    )
