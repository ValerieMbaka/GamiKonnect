"""Signal handlers for payment-related notifications."""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender='payments.MpesaTransaction')
def on_payment_completed(sender, instance, created, update_fields, **kwargs):
    """
    Send notification when a payment is completed or fails.
    """
    if not created and update_fields and 'status' not in update_fields:
        return
    
    if instance.status not in ['SUCCESS', 'FAILED']:
        return
    
    try:
        from notifications.models import Notification
        from notifications.services import send_notification_to_users
        
        gamer = instance.gamer
        
        if instance.status == 'SUCCESS':
            notification_text = (
                f"Payment of Ksh {instance.amount} received successfully! "
                f"Your competition registration is confirmed."
            )
            title = "Payment Successful"
            importance = "high"
        else:  # failed
            notification_text = (
                f"Payment of Ksh {instance.amount} failed. "
                f"Please try again or contact support."
            )
            title = "Payment Failed"
            importance = "high"
        
        notification, _ = Notification.objects.get_or_create(
            title=title,
            category="payment",
            importance=importance,
            is_system=True,
            defaults={'message': notification_text}
        )
        
        notification.set_expiry()
        notification.save()
        
        # Create recipient for this user
        send_notification_to_users(notification, [gamer], send_email=True)
        
        logger.info(f"Payment notification sent to {gamer.custom_username}: {instance.status}")
    except Exception as e:
        logger.error(f"Error sending payment notification: {e}")
