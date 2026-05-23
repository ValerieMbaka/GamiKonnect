from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    # Authentication & Profile Routes
    path('login/', views.admin_login, name='login'),
    path('logout/', views.admin_logout, name='logout'),
    path('profile/', views.admin_profile, name='profile'),
    path('change-password/', views.admin_change_password, name='change_password'),
    
    # Dashboard & Settings
    path('', views.admin_dashboard, name='dashboard'),
    path('settings/', views.admin_site_settings, name='site_settings'),
    path('content/', views.admin_content_library, name='content_library'),
    path('notifications/', views.admin_notification_hub, name='notification_hub'),
    path('notifications/send/', views.admin_send_notification, name='notification_send'),
    
    # Game Management & API Routes
    path('games/', views.admin_game_list, name='games'),
    path('games/api/save/', views.admin_game_save, name='game_save'),
    path('games/api/<int:game_id>/', views.admin_game_detail, name='game_detail'),
    path('games/api/<int:game_id>/delete/', views.admin_game_delete, name='game_delete'),
    path('games/api/<int:game_id>/toggle/', views.admin_game_toggle_status, name='game_toggle_status'),
    
    # Competition Management
    path('competitions/create/', views.admin_competition_create, name='competition_create'),
    path('competitions/', views.admin_competition_list, name='competition_list'),
    path('competitions/<slug:slug>/', views.admin_competition_detail, name='competition_detail'),
    path('competitions/<slug:slug>/approve/', views.admin_competition_approve, name='competition_approve'),
    path('competitions/<slug:slug>/reject/', views.admin_competition_reject, name='competition_reject'),
    path('competitions/<slug:slug>/confirm-checkins/', views.admin_confirm_checkins, name='competition_confirm_checkins'),
    path('competitions/<slug:slug>/verify-results/', views.admin_verify_results, name='competition_verify_results'),

    # User Management
    path('users/', views.admin_user_list, name='user_list'),
    path('users/<int:user_id>/', views.admin_user_detail, name='user_detail'),
    path('users/<int:user_id>/toggle-status/', views.admin_user_toggle_status, name='user_toggle_status'),

    # Shop Management
    path('shops/', views.admin_shop_list, name='shop_list'),
    path('shops/<int:shop_id>/', views.admin_shop_detail, name='shop_detail'),
    path('shops/<int:shop_id>/approve/', views.admin_shop_approve, name='shop_approve'),
    path('shops/<int:shop_id>/reject/', views.admin_shop_reject, name='shop_reject'),

    # Payments
    path('payments/', views.admin_payment_list, name='payment_list'),
    path('payments/<int:transaction_id>/', views.admin_payment_detail, name='payment_detail'),

    # Progression
    path('progression/levels/', views.admin_level_list, name='level_list'),
    path('progression/levels/save/', views.admin_level_save, name='level_save'),
    path('progression/achievements/', views.admin_achievement_list, name='achievement_list'),
    path('progression/achievements/save/', views.admin_achievement_save, name='achievement_save'),

    # Activities
    path('activities/', views.admin_activity_logs, name='activity_logs'),
    path('activities/gamer/', views.admin_gamer_activities, name='gamer_activities'),
]