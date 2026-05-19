"""
Pusher client utilities for broadcasting real-time notifications.

This module provides helper functions to broadcast notifications to users
via Pusher Channels without cluttering business logic.
"""
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def broadcast_notification(channel_name, event_name, data):
    """
    Broadcast a notification event to a specific Pusher channel.
    
    Args:
        channel_name: Pusher channel to broadcast to (e.g., 'gamikonnect-global')
        event_name: Event name to trigger (e.g., 'new-notification')
        data: Dictionary of data to send (must be JSON-serializable)
    
    Returns:
        bool: True if broadcast succeeded, False otherwise
    
    Example:
        broadcast_notification(
            'gamikonnect-global',
            'new-notification',
            {'title': 'Test', 'message': 'Hello World'}
        )
    """
    try:
        settings.PUSHER_CLIENT.trigger(channel_name, event_name, data)
        logger.debug(f"Pusher broadcast: {event_name} to {channel_name}")
        return True
    except Exception as e:
        logger.error(f"Pusher broadcast failed ({channel_name}/{event_name}): {str(e)}")
        return False


def broadcast_user_notification(user_id, user_type, notification_data):
    """
    Broadcast a notification to a specific user's private channel.
    
    Args:
        user_id: ID of the user receiving the notification
        user_type: Type of user ('gamer', 'shop_owner', 'admin')
        notification_data: Dict with 'title' and 'message' keys
    
    Returns:
        bool: True if broadcast succeeded, False otherwise
    
    Example:
        broadcast_user_notification(
            123,
            'gamer',
            {'title': 'New Achievement!', 'message': 'You unlocked the speedrunner badge'}
        )
    """
    # User-specific channel: private-gamer-123 for Gamer ID 123
    channel_name = f'private-{user_type}-{user_id}'
    
    try:
        settings.PUSHER_CLIENT.trigger(
            channel_name,
            'new-notification',
            notification_data
        )
        logger.debug(f"Pusher user notification: {user_type} {user_id}")
        return True
    except Exception as e:
        logger.error(f"Pusher user notification failed ({channel_name}): {str(e)}")
        return False


def broadcast_activity_feed(activity_data):
    """
    Broadcast an activity to the global activity feed channel.
    
    Used for system-wide updates like new competitions, shops being verified, etc.
    
    Args:
        activity_data: Dict with activity information
    
    Returns:
        bool: True if broadcast succeeded, False otherwise
    
    Example:
        broadcast_activity_feed({
            'title': 'New Shop Verified',
            'message': 'RetroMania Arcade has been verified',
            'type': 'shop',
            'timestamp': '2025-05-19T10:30:00Z'
        })
    """
    return broadcast_notification('gamikonnect-global', 'activity-feed', activity_data)


def broadcast_competition_update(competition_data):
    """
    Broadcast competition updates to subscribers.
    
    Args:
        competition_data: Dict with competition details
    
    Returns:
        bool: True if broadcast succeeded, False otherwise
    
    Example:
        broadcast_competition_update({
            'id': 5,
            'title': 'Street Fighter VI Tournament',
            'status': 'started',
            'timestamp': '2025-05-19T10:30:00Z'
        })
    """
    return broadcast_notification('competitions', 'competition-update', competition_data)
