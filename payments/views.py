import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import MpesaTransaction
from django.contrib.auth.decorators import login_required
from .services import MpesaService


@csrf_exempt
def mpesa_callback(request):
    """Safaricom strictly hits this URL with the transaction results."""
    if request.method == 'POST':
        try:
            # Safaricom sends the data as a JSON string in the request body
            payload = json.loads(request.body)
            
            # Extract the core data from Safaricom's deeply nested JSON
            body = payload.get('Body', {}).get('stkCallback', {})
            result_code = body.get('ResultCode')
            checkout_request_id = body.get('CheckoutRequestID')
            
            # Find the pending transaction in our database
            transaction = MpesaTransaction.objects.filter(checkout_request_id=checkout_request_id).first()
            
            if transaction:
                if result_code == 0:
                    # ResultCode 0 means SUCCESS!
                    callback_metadata = body.get('CallbackMetadata', {}).get('Item', [])
                    for item in callback_metadata:
                        if item.get('Name') == 'MpesaReceiptNumber':
                            transaction.receipt_number = item.get('Value')
                    
                    transaction.status = 'SUCCESS'
                    # TODO: Trigger logic to officially register the gamer for the competition here
                else:
                    # Anything other than 0 means FAILED (cancelled by user, insufficient funds, timeout, etc.)
                    transaction.status = 'FAILED'
                
                transaction.save()
            
            # We MUST return this specific response so Safaricom knows we received the message
            return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})
        
        except Exception as e:
            print(f"M-Pesa Callback Error: {e}")
            return JsonResponse({"ResultCode": 1, "ResultDesc": "Failed to process"}, status=400)
    
    return JsonResponse({"error": "Method not allowed"}, status=405)


@login_required
def initiate_payment(request):
    """Triggered when the gamer clicks 'Pay' on the frontend."""
    if request.method == 'POST':
        try:
            # In a real scenario, you'd get these from the frontend form/request
            data = json.loads(request.body)
            phone_number = data.get('phone_number')
            amount = data.get('amount')
            competition_id = data.get('competition_id')
            
            mpesa = MpesaService()
            # Firing the STK Push
            response = mpesa.initiate_stk_push(
                phone_number=phone_number,
                amount=amount,
                reference=f"Comp-{competition_id}",
                description="Competition Registration Fee"
            )
            
            # If Safaricom accepts the request, they return a CheckoutRequestID
            if "CheckoutRequestID" in response:
                # Log the pending transaction in our new database table!
                MpesaTransaction.objects.create(
                    gamer=request.user.gamer,  # Assuming your user profile setup
                    phone_number=phone_number,
                    amount=amount,
                    checkout_request_id=response["CheckoutRequestID"],
                    status='PENDING'
                )
                return JsonResponse({"success": True, "message": "STK Push sent to your phone!"})
            
            return JsonResponse({"success": False, "error": response.get("errorMessage", "Failed to initiate")},
                                status=400)
        
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)
    
    return JsonResponse({"error": "Invalid request method"}, status=405)