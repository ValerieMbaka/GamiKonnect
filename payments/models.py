from django.db import models
from accounts.models import Gamer  # Ensure this matches your actual Gamer model import


class MpesaTransaction(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
        ('REFUND_PENDING', 'Refund Pending'),
        ('REFUND_FAILED', 'Refund Failed'),
    )
    
    gamer = models.ForeignKey(Gamer, on_delete=models.SET_NULL, null=True, related_name='transactions')
    phone_number = models.CharField(max_length=15)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Safaricom's unique tracker for the prompt session
    checkout_request_id = models.CharField(max_length=100, unique=True)
    
    # The actual M-Pesa code (e.g., QWE123RTY) generated upon success
    receipt_number = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    # Link to competition registration (for tracking which registration this payment is for)
    competition_registration = models.OneToOneField(
        'competitions.CompetitionRegistration',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='payment',
        help_text="The competition registration this payment is for."
    )
    
    # Payment simulation flag (for testing without real M-Pesa)
    is_simulated = models.BooleanField(
        default=False,
        help_text="If True, this is a simulated payment for testing purposes."
    )
    refund_reference = models.CharField(max_length=100, blank=True, null=True)
    refunded_at = models.DateTimeField(null=True, blank=True)
    refund_note = models.TextField(blank=True, default='')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'M-Pesa Transaction'
        verbose_name_plural = 'M-Pesa Transactions'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.receipt_number or 'Pending'} - {self.phone_number} - {self.amount}"