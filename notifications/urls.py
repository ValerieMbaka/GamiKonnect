"""URL configuration for notifications app."""
from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    # Notification center (paginated list) for gamers
    path('center/', views.notification_center, name='center'),
    
    # AJAX endpoints for gamer dashboard
    path('api/unread-count/', views.get_unread_count, name='api_unread_count'),
    path('api/recent/', views.get_recent_notifications, name='api_recent'),
    path('api/mark-read/<int:notification_id>/', views.mark_notification_as_read, name='api_mark_read'),
    path('api/mark-all-read/', views.mark_all_as_read, name='api_mark_all_read'),
    
    # Notification center for shop owners
    path('shop-owner/', views.shop_owner_notification_center, name='shop_owner_center'),
    
    # AJAX endpoints for shop owner dashboard
    path('api/shop-owner/unread-count/', views.shop_owner_get_unread_count, name='api_shop_owner_unread_count'),
    path('api/shop-owner/mark-read/<int:notification_id>/', views.shop_owner_mark_notification_as_read, name='api_shop_owner_mark_read'),
    path('api/shop-owner/mark-all-read/', views.shop_owner_mark_all_as_read, name='api_shop_owner_mark_all_read'),
    
    # Pusher auth
    path('auth/', views.pusher_auth, name='pusher_auth'),
]
