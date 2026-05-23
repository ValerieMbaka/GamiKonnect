from django.urls import path
from . import views

app_name = 'activities'

urlpatterns = [
    path('all/', views.all_activity, name='all_activity'),
    path('gamer/<int:gamer_id>/', views.gamer_activity_list, name='gamer_activity_list'),
    path('actor/<int:actor_id>/', views.actor_activity_logs, name='actor_activity_logs'),
]
