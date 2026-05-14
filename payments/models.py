from django.db import models
from accounts.models import Gamer  # Ensure this matches your actual Gamer model import


class MpesaTransaction(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
    )
    
    gamer = models.ForeignKey(Gamer, on_delete=models.SET_NULL, null=True, related_name='transactions')
    phone_number = models.CharField(max_length=15)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Safaricom's unique tracker for the prompt session
    checkout_request_id = models.CharField(max_length=100, unique=True)
    
    # The actual M-Pesa code (e.g., QWE123RTY) generated upon success
    receipt_number = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.receipt_number or 'Pending'} - {self.phone_number} - {self.amount}"