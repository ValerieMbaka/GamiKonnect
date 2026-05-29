from django.urls import path
from . import views

app_name = 'feeds'

urlpatterns = [
    # Main feed
    path('', views.feed_list, name='feed_list'),
    
    # Post management
    path('create/', views.create_post, name='create_post'),
    path('post/<uuid:post_id>/', views.post_detail, name='post_detail'),
    
    # Comments
    path('post/<uuid:post_id>/comment/', views.add_comment, name='add_comment'),
    path('comment/<uuid:comment_id>/delete/', views.delete_comment, name='delete_comment'),
    
    # Likes (AJAX)
    path('post/<uuid:post_id>/like/', views.toggle_like, name='toggle_like'),
    
    # Gamer profile feed
    path('gamer/<int:gamer_id>/', views.gamer_feed, name='gamer_feed'),
    
    # API Endpoints (AJAX for modals)
    path('api/create-post/', views.api_create_post, name='api_create_post'),
    path('api/post/<uuid:post_id>/comments/', views.api_get_post_comments, name='api_get_post_comments'),
    path('api/post/<uuid:post_id>/comment/', views.api_add_comment, name='api_add_comment'),
    
    # New API Endpoints for Unified Feeds Architecture
    path('api/posts/', views.api_posts_list, name='api_posts_list'),
    path('api/posts/<uuid:post_id>/comments/', views.api_post_comments_list, name='api_post_comments_list'),
    path('api/posts/<uuid:post_id>/comments/create/', views.api_create_comment, name='api_create_comment'),
    path('api/posts/<uuid:post_id>/like/', views.api_like_post, name='api_like_post'),
    path('api/posts/<uuid:post_id>/delete/', views.api_delete_post, name='api_delete_post'),
    path('api/members/', views.api_members_list, name='api_members_list'),
]