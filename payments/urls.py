from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    # Frontend initialization endpoint (returns Paystack authorization URL)
    path('api/initiate/', views.initiate_payment, name='initiate_payment'),

    # Paystack redirects the gamer here after checkout; backend verifies transaction.
    path('api/paystack/callback/', views.paystack_callback, name='paystack_callback'),

    # Paystack webhook endpoint for browser-free confirmation.
    path('api/paystack/webhook/', views.paystack_webhook, name='paystack_webhook'),

    # Legacy endpoints retained for backward compatibility.
    path('api/callback/', views.mpesa_callback, name='mpesa_callback'),
    path('api/confirm-simulated/<str:checkout_request_id>/', views.confirm_simulated_payment, name='confirm_simulated_payment'),
]