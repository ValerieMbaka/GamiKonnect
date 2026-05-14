from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    # The URL your frontend calls to start the payment
    path('api/initiate/', views.initiate_payment, name='initiate_payment'),
    
    # The CRITICAL URL Safaricom calls in the background to confirm payment
    path('api/callback/', views.mpesa_callback, name='mpesa_callback'),
]