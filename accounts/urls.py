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
    
    # Gamer URLs
    path('gamer-profile-completion/', views.gamer_profile_completion, name='gamer_profile_completion'),
    path('check-username/', views.check_username, name='check_username'),
    path('gamer-dashboard/', views.gamer_dashboard, name='gamer_dashboard'),
    path('gamer-games/', views.gamer_games, name='gamer_games'),
    path('gamer-profile-edit/', views.gamer_profile_edit, name='gamer_profile_edit'),
    path('gamer-settings/', views.gamer_settings, name='gamer_settings'),
    path('gamer-public-profile/', views.gamer_public_profile, name='gamer_public_profile'),
    path('gamer-public-profile/<str:username>/', views.gamer_public_profile, name='gamer_public_profile_username'),
    
    # Shop Owner URLs
    path('shop-owner-dashboard/', views.shop_owner_dashboard, name='shop_owner_dashboard'),
    path('shop-owner-profile/', views.shop_owner_profile, name='shop_owner_profile'),
    path('shop-owner-profile-edit/', views.shop_owner_profile_edit, name='shop_owner_profile_edit'),
    path('shop-owner-venues/', views.shop_owner_venues, name='shop_owner_venues'),
    path('shop-owner-venues/<int:pk>/', views.shop_owner_shop_detail, name='shop_owner_shop_detail'),
    path('edit-shop/<int:pk>/', views.edit_shop, name='edit_shop'),
    path('create-shop/', views.create_shop, name='create_shop'),
    
    # Toggle between gamer and shop owner dashboard roles
    path('toggle-gamer-mode/', views.toggle_gamer_mode, name='toggle_gamer_mode'),
    
    # Admin Quick Actions
    path('quick-approve-shop/<str:token>/', views.quick_approve_shop, name='quick_approve_shop'),
    path('quick-reject-shop/<str:token>/', views.quick_reject_shop, name='quick_reject_shop'),
]