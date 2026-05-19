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
]