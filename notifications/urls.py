"""URL configuration for notifications app."""
from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    # Notification center (paginated list)
    path('center/', views.notification_center, name='center'),
    
    # AJAX endpoints for dashboard
    path('api/unread-count/', views.get_unread_count, name='api_unread_count'),
    path('api/recent/', views.get_recent_notifications, name='api_recent'),
    path('api/mark-read/<int:notification_id>/', views.mark_notification_as_read, name='api_mark_read'),
    path('api/mark-all-read/', views.mark_all_as_read, name='api_mark_all_read'),
    path('auth/', views.pusher_auth, name='pusher_auth'),
]
