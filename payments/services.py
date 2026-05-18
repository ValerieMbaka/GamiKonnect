import requests
import base64
from datetime import datetime
from django.conf import settings
from requests.auth import HTTPBasicAuth
import uuid


class MpesaService:
    def __init__(self):
        self.env = settings.MPESA_ENVIRONMENT
        self.base_url = "https://sandbox.safaricom.co.ke" if self.env == "sandbox" else "https://api.safaricom.co.ke"

    def get_access_token(self):
        """Requests the temporary OAuth access token from Safaricom."""
        api_url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
        try:
            response = requests.get(
                api_url,
                auth=HTTPBasicAuth(settings.MPESA_CONSUMER_KEY, settings.MPESA_CONSUMER_SECRET)
            )
            response.raise_for_status()
            return response.json()['access_token']
        except requests.exceptions.RequestException as e:
            print(f"Failed to get M-Pesa Access Token: {e}")
            return None

    def initiate_stk_push(self, phone_number, amount, reference, description):
        """Fires the STK Push request to Safaricom."""
        access_token = self.get_access_token()
        if not access_token:
            return {"error": "Failed to authenticate with M-Pesa"}

        api_url = f"{self.base_url}/mpesa/stkpush/v1/processrequest"
        headers = {"Authorization": f"Bearer {access_token}"}

        # Generate the timestamp and encrypted password Safaricom requires
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password_str = f"{settings.MPESA_SHORTCODE}{settings.MPESA_PASSKEY}{timestamp}"
        password = base64.b64encode(password_str.encode('utf-8')).decode('utf-8')

        # Ensure phone number is formatted correctly (e.g., 2547XXXXXXXX)
        formatted_phone = str(phone_number).replace('+', '')
        if formatted_phone.startswith('0'):
            formatted_phone = '254' + formatted_phone[1:]

        payload = {
            "BusinessShortCode": settings.MPESA_SHORTCODE,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": int(amount),
            "PartyA": formatted_phone,
            "PartyB": settings.MPESA_SHORTCODE,
            "PhoneNumber": formatted_phone,
            # THIS CALLBACK URL IS CRITICAL. It must be your live Render URL.
            "CallBackURL": "https://gamikonnect.onrender.com/api/payments/callback/",
            "AccountReference": reference,
            "TransactionDesc": description
        }

        try:
            response = requests.post(api_url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json() # Returns the CheckoutRequestID
        except requests.exceptions.RequestException as e:
            print(f"STK Push Failed: {e}")
            return {"error": str(e)}


class PaymentSimulationService:
    """
    Service for simulating M-Pesa payments in development/testing.
    Allows testing the full registration flow without a real Paybill/Till.
    """
    
    @staticmethod
    def create_simulated_payment(phone_number, amount, reference, description):
        """
        Creates a simulated M-Pesa transaction that can be confirmed via API.
        Returns a mock checkout request ID that can be used for testing.
        """
        # Generate a realistic-looking checkout request ID
        checkout_request_id = f"sim_{uuid.uuid4().hex[:20].upper()}"
        
        return {
            "CheckoutRequestID": checkout_request_id,
            "ResponseCode": "0",
            "ResponseDescription": "Success. Request accepted for processing.",
            "MerchantRequestID": f"merge_{uuid.uuid4().hex[:15].upper()}",
            "is_simulated": True
        }
    
    @staticmethod
    def confirm_simulated_payment(checkout_request_id):
        """
        Confirms a simulated payment by simulating the M-Pesa callback response.
        Used for testing - simulates what Safaricom would send back.
        """
        return {
            "Body": {
                "stkCallback": {
                    "MerchantRequestID": f"merge_{uuid.uuid4().hex[:15].upper()}",
                    "CheckoutRequestID": checkout_request_id,
                    "ResultCode": 0,  # 0 = success
                    "ResultDesc": "The service request has been processed successfully.",
                    "CallbackMetadata": {
                        "Item": [
                            {"Name": "Amount", "Value": 100},
                            {"Name": "MpesaReceiptNumber", "Value": f"SIM{uuid.uuid4().hex[:8].upper()}"},
                            {"Name": "TransactionDate", "Value": int(datetime.now().strftime('%Y%m%d%H%M%S'))},
                            {"Name": "PhoneNumber", "Value": "2547XXXXXXXX"},
                        ]
                    }
                }
            }
        }