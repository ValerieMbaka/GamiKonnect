import uuid
from decimal import Decimal, InvalidOperation

import requests
from django.conf import settings


class PaystackService:
    """Server-side helpers for Paystack transaction initialization and verification."""

    BASE_URL = "https://api.paystack.co"

    def __init__(self):
        self.secret_key = settings.PAYSTACK_SECRET_KEY

    @staticmethod
    def _amount_to_subunits(amount):
        """Convert amount in major currency units to Paystack subunits (x100)."""
        try:
            decimal_amount = Decimal(str(amount))
        except (InvalidOperation, TypeError, ValueError):
            return None
        return int(decimal_amount * 100)

    def _headers(self):
        if not self.secret_key:
            raise ValueError("PAYSTACK_SECRET_KEY is not configured.")
        return {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }

    def initialize_transaction(
        self,
        email,
        amount,
        reference,
        callback_url,
        currency="KES",
        metadata=None,
    ):
        subunit_amount = self._amount_to_subunits(amount)
        if subunit_amount is None or subunit_amount <= 0:
            return {"status": False, "message": "Invalid payment amount."}

        payload = {
            "email": email,
            "amount": subunit_amount,
            "reference": reference,
            "callback_url": callback_url,
            "currency": currency,
            "metadata": metadata or {},
            "channels": ["mobile_money", "card", "bank_transfer", "ussd"],
        }

        try:
            response = requests.post(
                f"{self.BASE_URL}/transaction/initialize",
                json=payload,
                headers=self._headers(),
                timeout=20,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as exc:
            return {"status": False, "message": str(exc)}

    def verify_transaction(self, reference):
        try:
            response = requests.get(
                f"{self.BASE_URL}/transaction/verify/{reference}",
                headers=self._headers(),
                timeout=20,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as exc:
            return {"status": False, "message": str(exc)}


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