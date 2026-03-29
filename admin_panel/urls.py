from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    # Authentication Routes
    path('login/', views.admin_login, name='login'),
    path('logout/', views.admin_logout, name='logout'),
    
    # Admin Profile Routes
    path('profile/', views.admin_profile, name='profile'),
    path('change-password/', views.admin_change_password, name='change_password'),
    
    # Admin Dashboard
    path('', views.admin_dashboard, name='dashboard'),
    path('settings/', views.admin_site_settings, name='site_settings'),

]