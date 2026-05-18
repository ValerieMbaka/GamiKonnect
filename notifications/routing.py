"""WebSocket URL routing for notifications app."""
from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/notifications/', consumers.NotificationConsumer.as_asgi(), name='notifications_ws'),
]
