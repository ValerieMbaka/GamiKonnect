from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentication URLs
    path('register/', views.register_view, name='register'),
    path('register/submit/', views.register_submit, name='register_submit'),
    path('login/', views.login_view, name='login'),
    path('session-login/', views.session_login, name='session_login'),
    path('logout/', views.logout_view, name='logout'),
    path('verify-email/<str:uid>/', views.verify_email, name='verify_email'),
    path('resend-verification/', views.resend_verification, name='resend_verification'),
    
    # Password & Account Management
    path('change-password/', views.change_password, name='change_password'),
    path('delete-account/', views.delete_account, name='delete_account'),
    
    
    # Test URL
    path('test-firebase/', views.test_firebase, name='test_firebase'),
]