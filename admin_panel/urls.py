from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'admin_panel'

urlpatterns = [
    # Authentication Routes
    path('login/', views.admin_login, name='login'),
    
]