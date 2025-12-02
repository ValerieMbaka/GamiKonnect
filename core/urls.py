from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.index, name='home'),
    path('cookie-policy/', views.cookie_policy, name='cookie_policy'),
    path('terms-conditions/', views.terms_conditions, name='terms_conditions'),
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('faqs/', views.faqs, name='faqs'),
    path('contact-us/', views.contact_us, name='contact_us'),
    path('help-center/', views.help_center, name='help_center'),
    
    # Help Center detailed guides
    path('help/creating-account/', views.help_creating_account, name='help_creating_account'),
    path('help/platform-navigation/', views.help_platform_navigation, name='help_platform_navigation'),
    path('help/first-tournament/', views.help_first_tournament, name='help_first_tournament'),
    path('contact-submit/', views.contact_submit, name='contact_submit'),
]