# Competition Payment API Documentation

## Overview
This document describes the complete payment flow for competition registration with M-Pesa integration.

## Payment Flow

```
1. Gamer clicks "Register" on competition
   ↓
2. Frontend shows registration modal with phone field
   ↓
3. Gamer submits registration form
   ↓
4. POST /competitions/{competition_id}/register/ 
   → Creates CompetitionRegistration with payment_status='pending'
   → Returns: registration_id, unique_code, entry_fee
   ↓
5. Frontend shows payment confirmation
   ↓
6. Gamer clicks "Pay Now"
   ↓
7. POST /payments/api/initiate/
   → Creates MpesaTransaction (links to registration)
   → Initiates M-Pesa STK Push OR simulated payment
   → Returns: checkout_request_id
   ↓
8. Gamer completes M-Pesa payment on phone
   ↓
9. M-Pesa callback to POST /payments/api/callback/
   → Updates MpesaTransaction with receipt_number and status
   → Updates CompetitionRegistration with payment_status='completed' and paid_at
   → Sends confirmation email to gamer
   → Creates ActivityLog entry
   ↓
10. Frontend can poll or listen for completion
    → Gamer officially registered for competition
```

## API Endpoints

### 1. Create Registration (Step 1)

**Endpoint:** `POST /competitions/{competition_id}/register/`

**Authentication:** Required (Session-based)

**Request Body:**
```json
{}  // Currently empty, form handles validation
```

**Success Response (200):**
```json
{
  "success": true,
  "message": "Registration created! Please proceed to payment.",
  "registration": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "unique_code": "comp-abc123def456"
  },
  "payment": {
    "amount": 500,
    "currency": "KES",
    "description": "Entry fee for Championship Tournament"
  }
}
```

**Error Response (400/403/404):**
```json
{
  "success": false,
  "message": "Registration already exists for this competition",
  "errors": {}
}
```

### 2. Initiate Payment (Step 2)

**Endpoint:** `POST /payments/api/initiate/`

**Authentication:** Required (Session-based)

**Request Body:**
```json
{
  "phone_number": "0712345678",           // Must be valid Kenyan format
  "amount": 500,                          // From competition.entry_fee
  "competition_id": 1,                    // From URL
  "registration_id": "550e8400-...",     // From Step 1 response
  "simulate": false                       // Optional: true for testing without real M-Pesa
}
```

**Success Response (200) - Real Payment:**
```json
{
  "success": true,
  "message": "STK Push sent to your phone!",
  "checkout_request_id": "ws_CO_0623202350123001"
}
```

**Success Response (200) - Simulated Payment:**
```json
{
  "success": true,
  "message": "Payment initiated (simulated mode)",
  "checkout_request_id": "sim_A1B2C3D4E5F6G7H8",
  "is_simulated": true
}
```

**Error Response (400/500):**
```json
{
  "success": false,
  "error": "Missing required fields"
}
```

### 3. Confirm Simulated Payment (Testing Only)

**Endpoint:** `POST /payments/api/confirm-simulated/{checkout_request_id}/`

**Authentication:** Required

**Request Body:** `{}` (empty)

**Response (200):**
```json
{
  "success": true,
  "message": "Simulated payment confirmed successfully!",
  "receipt_number": "SIMD4E5F6G7"
}
```

**Note:** This endpoint is for development/testing only. It simulates Safaricom's callback response.

### 4. M-Pesa Callback (Automatic - Backend Only)

**Endpoint:** `POST /payments/api/callback/` (This is called by Safaricom automatically)

**Authentication:** None (CSRF exempt, Safaricom server)

**Payload from Safaricom:**
```json
{
  "Body": {
    "stkCallback": {
      "MerchantRequestID": "16813-1590768991-...",
      "CheckoutRequestID": "ws_CO_0623202350123001",
      "ResultCode": 0,  // 0 = Success, non-zero = Failed
      "ResultDesc": "The service request has been processed successfully.",
      "CallbackMetadata": {
        "Item": [
          {"Name": "Amount", "Value": 500},
          {"Name": "MpesaReceiptNumber", "Value": "O7I6WB2N6B"},
          {"Name": "TransactionDate", "Value": 20230623203850},
          {"Name": "PhoneNumber", "Value": "254712345678"}
        ]
      }
    }
  }
}
```

**Response (200):**
```json
{
  "ResultCode": 0,
  "ResultDesc": "Accepted"
}
```

## Database Models

### MpesaTransaction
```python
{
  "id": UUID,
  "gamer": ForeignKey(Gamer),
  "phone_number": "0712345678",
  "amount": 500,
  "checkout_request_id": "ws_CO_...",
  "receipt_number": "O7I6WB2N6B",  // Only after success
  "status": "PENDING|SUCCESS|FAILED",
  "is_simulated": False,
  "competition_registration": OneToOneField(CompetitionRegistration),  // Links to registration
  "created_at": DateTime,
  "updated_at": DateTime
}
```

### CompetitionRegistration (Updated)
```python
{
  "id": UUID,
  "competition": ForeignKey(Competition),
  "gamer": ForeignKey(Gamer),
  "unique_code": UUID,
  "registered_at": DateTime,
  "payment_status": "pending|processing|completed|failed",
  "payment_phone_number": "0712345678",  // Phone used to pay
  "paid_at": DateTime,  // Set when payment succeeds
  "checked_in": Boolean,
  "is_cancelled": Boolean,
  // ... other fields
}
```

## Frontend Implementation Guide

### Step 1: Registration Modal
```javascript
// Show modal when user clicks "Register"
function showRegistrationModal(competitionId) {
  // Get competition details
  // Pre-fill phone from user profile
  // Show modal with form
}

// When user submits registration form
async function submitRegistration(competitionId) {
  const response = await fetch(`/competitions/${competitionId}/register/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({})
  });
  
  const data = await response.json();
  
  if (data.success) {
    // Store registration details
    localStorage.registration = JSON.stringify({
      id: data.registration.id,
      unique_code: data.registration.unique_code
    });
    // Show payment confirmation
    showPaymentScreen(data);
  }
}
```

### Step 2: Payment Initiation
```javascript
// When user clicks "Pay Now"
async function initiatePayment(phoneNumber, simulate = false) {
  const registration = JSON.parse(localStorage.registration);
  
  const response = await fetch('/payments/api/initiate/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      phone_number: phoneNumber,
      amount: 500,  // From competition
      competition_id: competitionId,
      registration_id: registration.id,
      simulate: simulate
    })
  });
  
  const data = await response.json();
  
  if (data.success) {
    if (simulate) {
      // For testing: show button to manually confirm
      showConfirmSimulatedPaymentButton(data.checkout_request_id);
    } else {
      // For real payments: Wait for M-Pesa callback (usually <2 minutes)
      startPaymentPolling(data.checkout_request_id);
    }
  }
}
```

### Step 3: Test Simulated Payment
```javascript
// For development/testing - manual confirmation
async function confirmSimulatedPayment(checkoutRequestId) {
  const response = await fetch(`/payments/api/confirm-simulated/${checkoutRequestId}/`, {
    method: 'POST'
  });
  
  const data = await response.json();
  
  if (data.success) {
    // Payment confirmed! Show success message
    showSuccessMessage('Payment confirmed! You are now registered.');
    // Redirect to competition detail or dashboard
  }
}
```

## Testing

### Test with Simulated Payments
1. Set `simulate: true` in initiate payment request
2. Get a simulated checkout_request_id
3. Call confirm_simulated_payment endpoint to manually trigger success
4. Verify CompetitionRegistration.payment_status changes to 'completed'
5. Verify email is sent to gamer

### Test with Real M-Pesa (Sandbox)
1. Use valid Safaricom sandbox credentials
2. Set up valid Paybill/Till number
3. Use test phone numbers provided by Safaricom
4. Pay from M-Pesa app
5. Verify callback is received and processed

## Security Considerations

1. **CSRF Protection:** Only the callback endpoint is CSRF exempt (required for Safaricom)
2. **Authentication:** Payment endpoints require login to prevent abuse
3. **Atomicity:** All database updates use `transaction.atomic()` to prevent race conditions
4. **Validation:** Phone number format validated before sending to M-Pesa
5. **Concurrency:** `select_for_update()` prevents overselling of competition slots

## Error Handling

### Common Errors

**"Registration is already [status]"**
- User is trying to pay for a registration that's already processing or completed
- Solution: Clear any cached registration and start over

**"Missing required fields"**
- One of: phone_number, amount, competition_id, registration_id is missing
- Verify all fields are being sent in the request

**"STK Push failed: Invalid phone number"**
- Phone number is not in valid format (0712345678 or 254712345678)
- Ask user to correct their phone number

**"M-Pesa timeout"**
- User didn't complete payment within 2 minutes
- Transaction will remain in PENDING status
- User can try again with a new payment initiation

## Troubleshooting

### Payment stuck in PENDING
- Check MpesaTransaction.status in Django admin
- If real payment: Wait up to 2 hours for delayed callback
- If simulated: Use confirm_simulated_payment endpoint
- Check Safaricom callback logs (production)

### Email not sent
- Check core/email_service.py EmailManager configuration
- Verify email templates exist at accounts/email_templates/
- Check Django logs for SMTP errors

### Registration not completed
- Verify CompetitionRegistration.payment_status in admin
- Check if MpesaTransaction.receipt_number was set
- Verify callback was received (check logs)
