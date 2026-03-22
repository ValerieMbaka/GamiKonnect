from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    # Authentication Routes
    path('login/', views.admin_login, name='login'),
    
    path('', views.admin_dashboard, name='dashboard'),
    
]