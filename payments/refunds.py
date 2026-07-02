import logging
from django.utils import timezone
from django.db import transaction

from payments.models import MpesaTransaction
from payments.services import PaystackService

logger = logging.getLogger(__name__)


class RefundService:
    @staticmethod
    @transaction.atomic
    def refund_registration(registration, reason='Competition suspended'):
        """
        Refund a paid competition registration via Paystack.
        Returns (success: bool, message: str).
        """
        if registration.payment_status != 'completed':
            return False, 'Registration has no completed payment to refund.'

        payment = getattr(registration, 'payment', None)
        if not payment:
            return False, 'No payment record found for this registration.'

        if payment.status == 'REFUNDED':
            return True, 'Payment already refunded.'

        if payment.is_simulated:
            payment.status = 'REFUNDED'
            payment.refunded_at = timezone.now()
            payment.refund_note = reason
            payment.save(update_fields=['status', 'refunded_at', 'refund_note', 'updated_at'])
            registration.is_cancelled = True
            registration.save(update_fields=['is_cancelled'])
            return True, 'Simulated payment refunded.'

        payment.status = 'REFUND_PENDING'
        payment.save(update_fields=['status', 'updated_at'])

        paystack = PaystackService()
        response = paystack.refund_transaction(
            transaction_reference=payment.checkout_request_id,
            amount=payment.amount,
            customer_note=f"Refund: {registration.competition.name}",
            merchant_note=reason,
        )

        if response.get('status') is True:
            data = response.get('data') or {}
            payment.status = 'REFUNDED'
            payment.refund_reference = str(data.get('id') or data.get('transaction', {}).get('reference', ''))
            payment.refunded_at = timezone.now()
            payment.refund_note = reason
            payment.save(update_fields=[
                'status', 'refund_reference', 'refunded_at', 'refund_note', 'updated_at'
            ])
            registration.is_cancelled = True
            registration.save(update_fields=['is_cancelled'])
            return True, 'Refund processed successfully.'

        payment.status = 'REFUND_FAILED'
        payment.refund_note = response.get('message', 'Refund failed.')
        payment.save(update_fields=['status', 'refund_note', 'updated_at'])
        logger.error('Paystack refund failed for %s: %s', payment.checkout_request_id, response)
        return False, payment.refund_note

    @staticmethod
    def refund_competition_registrations(competition, reason='Competition suspended'):
        """Refund all paid registrations for a competition."""
        from competitions.models import CompetitionRegistration

        registrations = competition.registrations.filter(
            is_cancelled=False,
        ).select_related('payment')

        results = {'refunded': 0, 'failed': 0, 'skipped': 0, 'errors': []}

        for registration in registrations:
            entry_fee = registration.competition.entry_fee or 0
            if entry_fee <= 0 or registration.payment_status != 'completed':
                registration.is_cancelled = True
                registration.save(update_fields=['is_cancelled'])
                results['skipped'] += 1
                continue

            success, message = RefundService.refund_registration(registration, reason=reason)
            if success:
                results['refunded'] += 1
            else:
                results['failed'] += 1
                results['errors'].append(message)

        return results
