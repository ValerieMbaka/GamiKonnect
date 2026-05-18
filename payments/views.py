import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db import transaction
from .models import MpesaTransaction
from .services import MpesaService, PaymentSimulationService
from competitions.models import CompetitionRegistration
from activities.models import ActivityLog
from core.email_service import EmailManager


def _complete_registration_after_payment(payment_transaction):
    """
    Internal helper to complete registration after successful payment.
    Called from both real and simulated payment callbacks.
    """
    if not payment_transaction.competition_registration:
        return None
    
    registration = payment_transaction.competition_registration
    
    # Update registration with payment details
    registration.payment_status = 'completed'
    registration.paid_at = timezone.now()
    registration.save()
    
    # Create activity log for successful registration
    ActivityLog.objects.create(
        gamer=registration.gamer,
        activity_type='registration',
        audit_label='competition_registration_completed',
        description=f"Completed registration for {registration.competition.name} competition"
    )
    
    # Send confirmation email to gamer
    try:
        EmailManager.send_competition_registration(
            registration.gamer,
            registration.competition,
            registration
        )
    except Exception as e:
        print(f"Failed to send confirmation email: {e}")
    
    return registration


@csrf_exempt
def mpesa_callback(request):
    """
    Safaricom strictly hits this URL with the transaction results.
    Processes payment callbacks and completes registration.
    """
    if request.method == 'POST':
        try:
            # Safaricom sends the data as a JSON string in the request body
            payload = json.loads(request.body)
            
            # Extract the core data from Safaricom's deeply nested JSON
            body = payload.get('Body', {}).get('stkCallback', {})
            result_code = body.get('ResultCode')
            checkout_request_id = body.get('CheckoutRequestID')
            
            # Find the pending transaction in our database
            payment_trans = MpesaTransaction.objects.filter(checkout_request_id=checkout_request_id).first()
            
            if payment_trans:
                if result_code == 0:
                    # ResultCode 0 means SUCCESS!
                    callback_metadata = body.get('CallbackMetadata', {}).get('Item', [])
                    for item in callback_metadata:
                        if item.get('Name') == 'MpesaReceiptNumber':
                            payment_trans.receipt_number = item.get('Value')
                    
                    payment_trans.status = 'SUCCESS'
                    payment_trans.save()
                    
                    # Complete the registration now that payment succeeded
                    _complete_registration_after_payment(payment_trans)
                else:
                    # Anything other than 0 means FAILED (cancelled by user, insufficient funds, timeout, etc.)
                    payment_trans.status = 'FAILED'
                    payment_trans.save()
                    
                    # Update registration to reflect payment failure
                    if payment_trans.competition_registration:
                        registration = payment_trans.competition_registration
                        registration.payment_status = 'failed'
                        registration.save()
            
            # We MUST return this specific response so Safaricom knows we received the message
            return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})
        
        except Exception as e:
            print(f"M-Pesa Callback Error: {e}")
            return JsonResponse({"ResultCode": 1, "ResultDesc": "Failed to process"}, status=400)
    
    return JsonResponse({"error": "Method not allowed"}, status=405)


@login_required
def initiate_payment(request):
    """
    Triggered when the gamer clicks 'Pay' on the frontend.
    Supports both real M-Pesa payments and simulated payments (for testing).
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            phone_number = data.get('phone_number')
            amount = data.get('amount')
            competition_id = data.get('competition_id')
            registration_id = data.get('registration_id')
            simulate = data.get('simulate', False)  # If True, simulate the payment
            
            # Validate required fields
            if not all([phone_number, amount, competition_id, registration_id]):
                return JsonResponse(
                    {"success": False, "error": "Missing required fields"},
                    status=400
                )
            
            # Get the registration (ensure it exists and belongs to this gamer)
            try:
                registration = CompetitionRegistration.objects.select_for_update().get(
                    id=registration_id,
                    gamer=request.user.gamer
                )
            except CompetitionRegistration.DoesNotExist:
                return JsonResponse(
                    {"success": False, "error": "Registration not found"},
                    status=404
                )
            
            # Ensure registration is in pending status
            if registration.payment_status != 'pending':
                return JsonResponse(
                    {"success": False, "error": f"Registration is already {registration.payment_status}"},
                    status=400
                )
            
            # Update registration to show payment is processing
            registration.payment_status = 'processing'
            registration.payment_phone_number = phone_number
            registration.save()
            
            with transaction.atomic():
                if simulate:
                    # SIMULATED PAYMENT MODE (for testing/development)
                    response = PaymentSimulationService.create_simulated_payment(
                        phone_number=phone_number,
                        amount=amount,
                        reference=f"Comp-{competition_id}",
                        description="Competition Registration Fee"
                    )
                    checkout_request_id = response.get("CheckoutRequestID")
                    
                    # Create the transaction record
                    payment_trans = MpesaTransaction.objects.create(
                        gamer=request.user.gamer,
                        phone_number=phone_number,
                        amount=amount,
                        checkout_request_id=checkout_request_id,
                        status='PENDING',
                        is_simulated=True,
                        competition_registration=registration
                    )
                    
                    return JsonResponse({
                        "success": True,
                        "message": "Payment initiated (simulated mode)",
                        "checkout_request_id": checkout_request_id,
                        "is_simulated": True
                    })
                else:
                    # REAL M-PESA PAYMENT MODE
                    mpesa = MpesaService()
                    response = mpesa.initiate_stk_push(
                        phone_number=phone_number,
                        amount=amount,
                        reference=f"Comp-{competition_id}",
                        description="Competition Registration Fee"
                    )
                    
                    # Check if the STK Push was successful
                    if "CheckoutRequestID" in response:
                        checkout_request_id = response["CheckoutRequestID"]
                        
                        # Log the pending transaction
                        payment_trans = MpesaTransaction.objects.create(
                            gamer=request.user.gamer,
                            phone_number=phone_number,
                            amount=amount,
                            checkout_request_id=checkout_request_id,
                            status='PENDING',
                            is_simulated=False,
                            competition_registration=registration
                        )
                        
                        return JsonResponse({
                            "success": True,
                            "message": "STK Push sent to your phone!",
                            "checkout_request_id": checkout_request_id
                        })
                    else:
                        # Payment initiation failed
                        registration.payment_status = 'pending'
                        registration.save()
                        
                        return JsonResponse({
                            "success": False,
                            "error": response.get("errorMessage", "Failed to initiate payment")
                        }, status=400)
        
        except Exception as e:
            print(f"Payment initiation error: {e}")
            return JsonResponse({
                "success": False,
                "error": str(e)
            }, status=500)
    
    return JsonResponse({"error": "Invalid request method"}, status=405)


@login_required
def confirm_simulated_payment(request, checkout_request_id):
    """
    Test endpoint to manually confirm a simulated payment.
    Used for testing purposes - simulates Safaricom's callback.
    """
    if request.method == 'POST':
        try:
            # Get the transaction
            payment_trans = MpesaTransaction.objects.get(
                checkout_request_id=checkout_request_id,
                is_simulated=True,
                gamer=request.user.gamer
            )
            
            # Simulate successful payment
            payment_trans.status = 'SUCCESS'
            payment_trans.receipt_number = f"SIM{checkout_request_id[-8:]}"
            payment_trans.save()
            
            # Complete registration
            _complete_registration_after_payment(payment_trans)
            
            return JsonResponse({
                "success": True,
                "message": "Simulated payment confirmed successfully!",
                "receipt_number": payment_trans.receipt_number
            })
        
        except MpesaTransaction.DoesNotExist:
            return JsonResponse({
                "success": False,
                "error": "Transaction not found or access denied"
            }, status=404)
        except Exception as e:
            print(f"Error confirming simulated payment: {e}")
            return JsonResponse({
                "success": False,
                "error": str(e)
            }, status=500)
    
    return JsonResponse({"error": "Invalid request method"}, status=405)