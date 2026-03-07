from django.urls import path
from . import views

app_name = 'games'

urlpatterns = [
    path('get-profile-form-data/', views.get_profile_form_data, name='get_profile_form_data'),
]