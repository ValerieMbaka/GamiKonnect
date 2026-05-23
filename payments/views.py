import json
import hmac
import hashlib
import uuid

from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from accounts.models import Gamer, ShopOwner
from activities.models import ActivityLog
from competitions.models import CompetitionRegistration
from core.email_service import EmailManager
from .models import MpesaTransaction
from .services import PaystackService


def _get_gamer_from_session(request):
    """Resolve gamer from the custom session-based auth model used by the project."""
    if request.session.get('role') not in ['gamer', 'shop_owner']:
        return None

    user_id = request.session.get('user_id')
    if not user_id:
        return None

    try:
        return Gamer.objects.get(id=user_id)
    except Gamer.DoesNotExist:
        try:
            shop_owner = ShopOwner.objects.get(id=user_id)
            return Gamer.objects.get(uid=shop_owner.uid)
        except (ShopOwner.DoesNotExist, Gamer.DoesNotExist):
            return None


def _complete_registration_after_payment(payment_transaction):
    """
    Internal helper to complete registration after successful payment.
    Called from both real and simulated payment callbacks.
    """
    if not payment_transaction.competition_registration:
        return None

    registration = payment_transaction.competition_registration

    # Idempotency: callbacks can be retried by gateway/network.
    if registration.payment_status == 'completed':
        return registration
    
    registration.payment_status = 'completed'
    registration.paid_at = timezone.now()
    registration.save(update_fields=['payment_status', 'paid_at'])

    ActivityLog.objects.create(
        actor=registration.gamer,
        gamer=registration.gamer,
        action_type=ActivityLog.ActionTypes.UPDATE,
        target=registration,
        description=f"Completed payment for competition registration: {registration.competition.name}",
        meta_data={
            'competition_slug': registration.competition.slug,
            'registration_id': str(registration.id),
            'payment_reference': payment_transaction.checkout_request_id,
        }
    )

    try:
        EmailManager.send_competition_registration(
            registration.gamer,
            registration.competition,
            registration
        )
    except Exception as e:
        print(f"Failed to send confirmation email: {e}")

    return registration


def _mark_payment_failed(payment_transaction):
    payment_transaction.status = 'FAILED'
    payment_transaction.save(update_fields=['status', 'updated_at'])

    registration = payment_transaction.competition_registration
    if registration and registration.payment_status != 'completed':
        registration.payment_status = 'failed'
        registration.save(update_fields=['payment_status'])


def _redirect_after_payment_result(request, registration, success, detail_message):
    if success:
        messages.success(request, detail_message)
    else:
        messages.error(request, detail_message)

    if registration and registration.competition:
        return redirect('competitions:detail', slug=registration.competition.slug)
    return redirect('competitions:list')


def _verify_and_finalize_paystack_reference(request, reference, detail_message_on_error):
    payment_trans = MpesaTransaction.objects.filter(checkout_request_id=reference).select_related(
        'competition_registration__competition'
    ).first()

    if not payment_trans:
        return _redirect_after_payment_result(
            request,
            registration=None,
            success=False,
            detail_message=detail_message_on_error,
        )

    verify_response = PaystackService().verify_transaction(reference)
    data = verify_response.get('data') or {}
    paystack_status = data.get('status')

    if verify_response.get('status') is True and paystack_status == 'success':
        if payment_trans.status != 'SUCCESS':
            payment_trans.status = 'SUCCESS'
            payment_trans.receipt_number = str(data.get('id') or reference)
            payment_trans.save(update_fields=['status', 'receipt_number', 'updated_at'])

        registration = _complete_registration_after_payment(payment_trans)
        return _redirect_after_payment_result(
            request,
            registration=registration,
            success=True,
            detail_message='Payment confirmed successfully. Your competition registration is now complete.',
        )

    _mark_payment_failed(payment_trans)
    return _redirect_after_payment_result(
        request,
        registration=payment_trans.competition_registration,
        success=False,
        detail_message='Payment could not be verified as successful. Please try again.',
    )


def paystack_callback(request):
    """
    Paystack redirect callback endpoint.
    Paystack redirects browser with ?reference=... after checkout.
    We verify server-to-server before granting access.
    """
    reference = request.GET.get('reference') or request.GET.get('trxref')
    if not reference:
        return _redirect_after_payment_result(
            request,
            registration=None,
            success=False,
            detail_message='Missing payment reference from Paystack callback.',
        )

    return _verify_and_finalize_paystack_reference(
        request,
        reference,
        'Payment transaction not found. Please contact support if you were charged.',
    )


@csrf_exempt
def paystack_webhook(request):
    """Handle Paystack webhook notifications with signature validation."""
    if request.method != 'POST':
        return JsonResponse({"error": "Invalid request method"}, status=405)

    raw_body = request.body or b''
    signature = request.headers.get('X-Paystack-Signature', '')
    secret_key = settings.PAYSTACK_SECRET_KEY or ''
    expected_signature = hmac.new(
        secret_key.encode('utf-8'),
        raw_body,
        hashlib.sha512,
    ).hexdigest()

    if not secret_key or not hmac.compare_digest(signature, expected_signature):
        return JsonResponse({"error": "Invalid signature"}, status=401)

    try:
        payload = json.loads(raw_body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid payload"}, status=400)

    event = payload.get('event')
    data = payload.get('data') or {}
    reference = data.get('reference')

    if event != 'charge.success' or not reference:
        return JsonResponse({"received": True})

    # The webhook itself is a browser-less confirmation path; it still verifies server-side.
    _verify_and_finalize_paystack_reference(
        request,
        reference,
        'Webhook payment transaction not found.',
    )
    return JsonResponse({"received": True})


def initiate_payment(request):
    """
    Triggered after creating/updating a pending competition registration.
    Initializes a Paystack transaction and returns authorization_url for redirect.
    """
    if request.method != 'POST':
        return JsonResponse({"error": "Invalid request method"}, status=405)

    gamer = _get_gamer_from_session(request)
    if not gamer:
        return JsonResponse({"success": False, "error": "You must be logged in as a gamer."}, status=403)

    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON payload."}, status=400)

    registration_id = data.get('registration_id')
    phone_number = data.get('phone_number') or gamer.phone

    if not registration_id:
        return JsonResponse({"success": False, "error": "registration_id is required."}, status=400)

    try:
        with transaction.atomic():
            registration = CompetitionRegistration.objects.select_for_update().select_related('competition').get(
                id=registration_id,
                gamer=gamer,
                is_cancelled=False,
            )

            if registration.payment_status == 'completed':
                return JsonResponse({"success": False, "error": "Registration is already paid."}, status=400)

            if registration.competition.entry_fee <= 0:
                return JsonResponse({"success": False, "error": "This competition does not require payment."}, status=400)

            registration.payment_status = 'processing'
            registration.payment_phone_number = phone_number
            registration.save(update_fields=['payment_status', 'payment_phone_number'])

            reference = f"GK-{uuid.uuid4().hex[:20].upper()}"
            callback_url = f"{request.scheme}://{request.get_host()}{reverse('payments:paystack_callback')}"

            paystack = PaystackService()
            initialize_response = paystack.initialize_transaction(
                email=gamer.email,
                amount=registration.competition.entry_fee,
                reference=reference,
                callback_url=callback_url,
                currency='KES',
                metadata={
                    'competition_slug': registration.competition.slug,
                    'registration_id': str(registration.id),
                    'gamer_id': str(gamer.id),
                },
            )

            if initialize_response.get('status') is not True:
                registration.payment_status = 'pending'
                registration.save(update_fields=['payment_status'])
                return JsonResponse({
                    "success": False,
                    "error": initialize_response.get('message', 'Failed to initialize Paystack transaction.'),
                }, status=400)

            payload_data = initialize_response.get('data') or {}
            authorization_url = payload_data.get('authorization_url')
            if not authorization_url:
                registration.payment_status = 'pending'
                registration.save(update_fields=['payment_status'])
                return JsonResponse({"success": False, "error": "Missing Paystack authorization URL."}, status=400)

            MpesaTransaction.objects.update_or_create(
                competition_registration=registration,
                defaults={
                    'gamer': gamer,
                    'phone_number': phone_number,
                    'amount': registration.competition.entry_fee,
                    'checkout_request_id': reference,
                    'status': 'PENDING',
                    'is_simulated': False,
                },
            )

            return JsonResponse({
                "success": True,
                "authorization_url": authorization_url,
                "reference": reference,
                "public_key": settings.PAYSTACK_PUBLIC_KEY,
            })
    except CompetitionRegistration.DoesNotExist:
        return JsonResponse({"success": False, "error": "Registration not found."}, status=404)
    except Exception as e:
        print(f"Payment initiation error: {e}")
        return JsonResponse({"success": False, "error": "Failed to initialize payment."}, status=500)


@csrf_exempt
def mpesa_callback(request):
    """Deprecated endpoint retained for backward compatibility."""
    return JsonResponse({"success": False, "message": "M-Pesa callback is no longer in use."}, status=410)


def confirm_simulated_payment(request, checkout_request_id):
    """Deprecated simulation endpoint retained to avoid URL breakage."""
    return JsonResponse({"success": False, "message": "Simulated payment endpoint has been retired."}, status=410)