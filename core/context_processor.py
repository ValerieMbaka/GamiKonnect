import os
from django.conf import settings
from .models import SiteStyle, ProjectDetail


def site_style(request):
    style = SiteStyle.get_active()
    return {"site_style": style.as_dict() if style else {}}


def firebase_config(request):
    # Provide client-side Firebase config for templates if available in settings
    cfg = getattr(settings, "FIREBASE_CLIENT_CONFIG", None)
    return {"firebase_config": cfg or {}}


def global_site_context(request):
    # Automatically injects global site configuration across all pages
    project_detail = ProjectDetail.objects.filter(is_active=True).first()
    
    # Dynamically determine site_url from the current request
    site_url = request.build_absolute_uri('/').rstrip('/')
    
    return {
        'project_detail': project_detail,
        'site_url': site_url,
        'pusher_key': getattr(settings, 'PUSHER_KEY', '') or os.environ.get('PUSHER_KEY', ''),
        'pusher_cluster': getattr(settings, 'PUSHER_CLUSTER', '') or os.environ.get('PUSHER_CLUSTER', ''),
    }

def admin_competition_context(request):
    if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
        from competitions.models import Competition
        return {
            'pending_competitions_count': Competition.objects.filter(
                status='pending'
            ).count()
        }
    return {}


def admin_notification_context(request):
    if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
        from notifications.models import NotificationRecipient

        admin_email = getattr(request.user, 'email', '')
        return {
            'admin_unread_notifications_count': NotificationRecipient.objects.filter(
                admin_user__email=admin_email,
                is_read=False,
            ).count(),
            'admin_recent_notifications': NotificationRecipient.objects.filter(
                admin_user__email=admin_email,
            ).select_related('notification').order_by('-created_at')[:5],
        }
    return {}