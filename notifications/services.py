"""Service functions for notifications app."""
from django.utils import timezone
from django.template import Template, Context
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from .models import Notification, NotificationRecipient, NotificationGroup
import json
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


def render_notification_message(message_template, context_dict):
    """
    Render a message template with context data.
    Supports Jinja2-like syntax: {{variable_name}}
    
    Args:
        message_template: Template string with {{placeholders}}
        context_dict: Dictionary of variables to inject
    
    Returns:
        Rendered message string
    """
    if not message_template:
        return ""
    
    try:
        template = Template(message_template)
        context = Context(context_dict)
        return template.render(context)
    except Exception as e:
        # If template rendering fails, return original message
        return message_template


def send_notification_to_users(
    notification,
    user_list,
    send_email=True,
    send_in_app=True,
    user_type='gamer'
):
    """
    Send a notification to a list of users.
    Creates NotificationRecipient records and optionally sends emails.
    
    Args:
        notification: Notification instance
        user_list: QuerySet or list of user instances (Gamer, ShopOwner, or Account)
        send_email: Whether to send email notifications
        send_in_app: Whether to create in-app notifications
        user_type: Type of users ('gamer', 'shop_owner', 'admin')
    
    Returns:
        Dict with statistics: {'created': int, 'updated': int, 'failed': int}
    """
    if not send_in_app:
        return {'created': 0, 'updated': 0, 'failed': 0}
    
    # Prepare NotificationRecipient records
    stats = {'created': 0, 'updated': 0, 'failed': 0}
    
    for user in user_list:
        # Create/get NotificationRecipient with appropriate user field
        recipient_data = {'notification': notification}
        
        if user_type == 'gamer':
            recipient_data['gamer'] = user
        elif user_type == 'shop_owner':
            recipient_data['shop_owner'] = user
        elif user_type == 'admin':
            recipient_data['admin_user'] = user
        
        recipient, created = NotificationRecipient.objects.get_or_create(
            **recipient_data,
            defaults={'delivery_status': 'pending'}
        )
        
        if created:
            stats['created'] += 1
        else:
            stats['updated'] += 1
        
        # Send email if requested
        if send_email and hasattr(user, 'email'):
            try:
                send_notification_email(notification, user)
                recipient.delivery_status = 'sent'
                recipient.sent_at = timezone.now()
                recipient.save(update_fields=['delivery_status', 'sent_at'])
            except Exception as e:
                recipient.delivery_status = 'failed'
                recipient.save(update_fields=['delivery_status'])
                stats['failed'] += 1
                logger.error(f"Failed to send email to {user.email}: {str(e)}")
    
    # Update denormalized count
    notification.total_recipients = NotificationRecipient.objects.filter(
        notification=notification
    ).exclude(gamer__isnull=True, shop_owner__isnull=True, admin_user__isnull=True).count()
    notification.save(update_fields=['total_recipients'])
    
    return stats


def get_group_users(notification_group):
    """
    Get all users matching a NotificationGroup's criteria.
    
    Args:
        notification_group: NotificationGroup instance
    
    Returns:
        QuerySet of Gamer instances
    """
    from accounts.models import Gamer
    from games.models import Game
    from competitions.models import Competition, CompetitionRegistration
    from payments.models import MpesaTransaction
    
    criteria_type = notification_group.criteria_type
    criteria_data = notification_group.criteria_data
    
    if criteria_type == 'all_users':
        return Gamer.objects.all()
    
    elif criteria_type == 'level':
        # Filter by level IDs
        level_ids = criteria_data.get('levels', [])
        return Gamer.objects.filter(current_level_id__in=level_ids).distinct()
    
    elif criteria_type == 'game':
        # Filter by game names
        game_names = criteria_data.get('games', [])
        games = Game.objects.filter(name__in=game_names)
        return Gamer.objects.filter(games__in=games).distinct()
    
    elif criteria_type == 'competition':
        # Filter by competition registration
        competition_id = criteria_data.get('competition_id')
        if competition_id:
            registrations = CompetitionRegistration.objects.filter(
                competition_id=competition_id
            )
            return Gamer.objects.filter(
                competitionregistration__in=registrations
            ).distinct()
        return Gamer.objects.none()
    
    elif criteria_type == 'custom':
        # Filter by explicit user IDs
        user_ids = criteria_data.get('user_ids', [])
        return Gamer.objects.filter(id__in=user_ids)
    
    elif criteria_type == 'payment_status':
        # Filter by payment status (last transaction)
        payment_status = criteria_data.get('payment_status')  # 'completed', 'pending', 'failed'
        transactions = MpesaTransaction.objects.filter(
            status=payment_status
        ).distinct('gamer_id')
        return Gamer.objects.filter(
            id__in=transactions.values_list('gamer_id', flat=True)
        ).distinct()
    
    return Gamer.objects.none()


def send_notification_email(notification, user):
    """
    Send a notification email to a user using HTML template.
    
    Args:
        notification: Notification instance
        user: Gamer instance with email field
    
    Raises:
        Exception: If email sending fails
    """
    try:
        site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000').rstrip('/')
        
        # Prepare context for email template
        context = {
            'user': user,
            'notification': notification,
            'title': notification.title,
            'message': notification.message,
            'category': notification.get_category_display(),
            'site_url': site_url,
            'project_name': getattr(settings, 'PROJECT_NAME', 'GamiKonnect'),
        }
        
        subject = f"[{notification.get_category_display()}] {notification.title}"
        
        # Render HTML template
        html_content = render_to_string(
            'notifications/email_templates/../accounts/templates/accounts/email_templates/notifications/notification.html', context)
        plain_message = strip_tags(html_content)
        
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html_content,
            fail_silently=False
        )
        logger.info(f"Notification email sent to {user.email}: {notification.title}")
    except Exception as e:
        logger.error(f"Failed to send notification email to {user.email}: {e}")
        raise


def cleanup_expired_notifications():
    """
    Delete expired notifications and their recipients.
    Called by management command.
    
    Returns:
        Dict with statistics: {'deleted_notifications': int, 'deleted_recipients': int}
    """
    now = timezone.now()
    
    # Find expired notifications
    expired = Notification.objects.filter(
        expires_at__lt=now
    )
    
    # Count recipients to delete
    deleted_recipients = NotificationRecipient.objects.filter(
        notification__in=expired
    ).delete()[0]
    
    # Delete notifications
    deleted_notifications = expired.delete()[0]
    
    return {
        'deleted_notifications': deleted_notifications,
        'deleted_recipients': deleted_recipients
    }


def update_group_member_count(notification_group):
    """
    Update the denormalized member_count on a NotificationGroup.
    
    Args:
        notification_group: NotificationGroup instance
    """
    users = get_group_users(notification_group)
    notification_group.member_count = users.count()
    notification_group.save(update_fields=['member_count'])
