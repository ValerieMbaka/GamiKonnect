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
]