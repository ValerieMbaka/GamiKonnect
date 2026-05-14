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
    
    # Game Management & API Routes
    path('games/', views.admin_game_list, name='games'),
    path('games/api/save/', views.admin_game_save, name='game_save'),
    path('games/api/<int:game_id>/', views.admin_game_detail, name='game_detail'),
    path('games/api/<int:game_id>/delete/', views.admin_game_delete, name='game_delete'),
    path('games/api/<int:game_id>/toggle/', views.admin_game_toggle_status, name='game_toggle_status'),
    
# Competition Management
path('competitions/create/', views.admin_competition_create, name='competition_create'),
path('competitions/', views.admin_competition_list, name='competition_list'),
path('competitions/<int:competition_id>/', views.admin_competition_detail, name='competition_detail'),
path('competitions/<int:competition_id>/approve/', views.admin_competition_approve, name='competition_approve'),
path('competitions/<int:competition_id>/reject/', views.admin_competition_reject, name='competition_reject'),
path('competitions/<int:competition_id>/confirm-checkins/', views.admin_confirm_checkins, name='competition_confirm_checkins'),
path('competitions/<int:competition_id>/verify-results/', views.admin_verify_results, name='competition_verify_results'),
]