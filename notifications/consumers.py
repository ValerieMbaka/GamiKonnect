"""WebSocket consumers for real-time notifications."""
from channels.generic.websocket import AsyncWebsocketConsumer
import json
import logging

logger = logging.getLogger(__name__)


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time notification updates.
    
    Each authenticated user gets their own connection to receive notifications in real-time.
    Falls back to polling if WebSocket drops (handled client-side).
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize consumer with default user_group_name."""
        super().__init__(*args, **kwargs)
        self.user_group_name = None
    
    async def connect(self):
        """Handle WebSocket connection."""
        # Get user from scope
        self.user = self.scope['user']
        
        if not self.user.is_authenticated:
            await self.close()
            return
        
        # Create a channel group name per user
        self.user_group_name = f'notifications_user_{self.user.id}'
        
        # Join the user's group
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )
        
        await self.accept()
        logger.info(f"WebSocket connected for user {self.user.id}")
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        # Only discard from group if we successfully joined
        if self.user_group_name:
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )
        
        user_id = getattr(self, 'user', None)
        user_id = user_id.id if user_id else 'unknown'
        logger.info(f"WebSocket disconnected for user {user_id}")
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages (heartbeat, etc)."""
        try:
            data = json.loads(text_data)
            
            # Handle ping/pong for connection monitoring
            if data.get('type') == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong'
                }))
        except json.JSONDecodeError:
            user_id = getattr(self, 'user', None)
            user_id = user_id.id if user_id else 'unknown'
            logger.warning(f"Invalid JSON from user {user_id}")
    
    async def notification_message(self, event):
        """
        Receive notification message from group layer.
        Called when a notification is broadcast to this user's group.
        """
        # Extract message data
        notification_data = event['notification_data']
        
        # Send notification to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification': notification_data
        }))
    
    async def unread_count_update(self, event):
        """
        Receive unread count update.
        Allows frontend to update badge without full page refresh.
        """
        unread_count = event['unread_count']
        
        await self.send(text_data=json.dumps({
            'type': 'unread_count_update',
            'unread_count': unread_count
        }))
