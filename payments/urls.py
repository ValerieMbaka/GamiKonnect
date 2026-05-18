from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    # The URL your frontend calls to start the payment
    path('api/initiate/', views.initiate_payment, name='initiate_payment'),
    
    # The CRITICAL URL Safaricom calls in the background to confirm payment
    path('api/callback/', views.mpesa_callback, name='mpesa_callback'),
    
    # Test endpoint to manually confirm simulated payments (development only)
    path('api/confirm-simulated/<str:checkout_request_id>/', views.confirm_simulated_payment, name='confirm_simulated_payment'),
]