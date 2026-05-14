import requests
import base64
from datetime import datetime
from django.conf import settings
from requests.auth import HTTPBasicAuth

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