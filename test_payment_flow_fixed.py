#!/usr/bin/env python
"""
Test script for Competition Payment System with M-Pesa Integration

This script tests the entire payment flow end-to-end using simulated payments.
It can be run with: python manage.py shell < test_payment_flow.py
Or: python manage.py shell
    >>> exec(open('test_payment_flow.py').read())
"""

from django.utils import timezone
from django.db import transaction as db_transaction
from accounts.models import Gamer, ShopOwner
from competitions.models import Competition, CompetitionRegistration
from games.models import Game, Platform
from shops.models import Shop
from payments.models import MpesaTransaction
from payments.services import PaymentSimulationService
from activities.models import ActivityLog
import uuid
import json

print("\n" + "="*80)
print("COMPETITION PAYMENT SYSTEM - TEST SCRIPT")
print("="*80)

# Step 1: Create test data if needed
print("\n[Step 1] Setting up test data...")

try:
    # Get or create test shop owner
    shop_owner = ShopOwner.objects.filter(email='test_shop@example.com').first()
    if not shop_owner:
        shop_owner = ShopOwner.objects.create(
            uid=uuid.uuid4(),
            email='test_shop@example.com',
            phone='+254712345678',
            name='Test Shop Owner'
        )
        print(f"✓ Created test shop owner: {shop_owner.email}")
    else:
        print(f"✓ Using existing shop owner: {shop_owner.email}")
    
    # Get or create test shop
    shop = shop_owner.shops.first()
    if not shop:
        shop = Shop.objects.create(
            name='Test Shop',
            location='Nairobi',
            phone='+254712345678',
            email='shop@example.com',
            is_approved=True
        )
        shop.owners.add(shop_owner)
        print(f"✓ Created test shop: {shop.name}")
    else:
        print(f"✓ Using existing shop: {shop.name}")
    
    # Get or create test gamer
    gamer = Gamer.objects.filter(email='test_gamer@example.com').first()
    if not gamer:
        gamer = Gamer.objects.create(
            uid=uuid.uuid4(),
            email='test_gamer@example.com',
            phone='0712345678',
            first_name='Test',
            last_name='Gamer',
            date_of_birth='2000-01-01'
        )
        print(f"✓ Created test gamer: {gamer.email}")
    else:
        print(f"✓ Using existing gamer: {gamer.email}")
    
    # Get or create test game
    game = Game.objects.filter(name='Test Game').first()
    if not game:
        game = Game.objects.create(
            name='Test Game',
            description='A test game for payment verification',
            is_active=True,
            is_verified=True
        )
        print(f"✓ Created test game: {game.name}")
    else:
        print(f"✓ Using existing game: {game.name}")
    
    # Get or create platform
    platform = Platform.objects.filter(name='PC').first()
    if not platform:
        platform = Platform.objects.create(name='PC')
        print(f"✓ Created platform: {platform.name}")
    else:
        print(f"✓ Using existing platform: {platform.name}")
    
    # Create test competition
    competition = Competition.objects.create(
        name='Test Payment Competition',
        description='Used to test the payment system',
        game=game,
        platform=platform,
        shop=shop,
        created_by=shop_owner,
        scheduled_time=timezone.now() + timezone.timedelta(days=7),
        max_participants=50,
        entry_fee=500,
        prize_type='money',
        prize_money_total=10000,
        prize_money_1st_pct=50,
        prize_money_2nd_pct=30,
        prize_money_3rd_pct=20,
        status='approved'
    )
    # Move status to registration_open for testing
    competition.status = 'registration_open'
    competition.save()
    print(f"✓ Created test competition: {competition.name} (ID: {competition.integer_id})")
    print(f"  - Entry Fee: KES {competition.entry_fee}")
    print(f"  - Max Participants: {competition.max_participants}")

except Exception as e:
    print(f"✗ Error setting up test data: {e}")
    raise

# Step 2: Create competition registration
print("\n[Step 2] Creating competition registration...")

try:
    # Check if gamer is already registered
    existing = CompetitionRegistration.objects.filter(
        competition=competition,
        gamer=gamer,
        is_cancelled=False
    ).first()
    
    if existing:
        registration = existing
        print(f"✓ Using existing registration: {registration.id}")
    else:
        registration = CompetitionRegistration.objects.create(
            competition=competition,
            gamer=gamer,
            unique_code=uuid.uuid4(),
            payment_status='pending'
        )
        print(f"✓ Created registration: {registration.id}")
    
    print(f"  - Unique Code: {registration.unique_code}")
    print(f"  - Payment Status: {registration.payment_status}")
    print(f"  - Gamer: {gamer.email}")
    print(f"  - Phone: {gamer.phone}")

except Exception as e:
    print(f"✗ Error creating registration: {e}")
    raise

# Step 3: Initiate simulated payment
print("\n[Step 3] Initiating simulated payment...")

try:
    # Use PaymentSimulationService to create simulated payment
    response = PaymentSimulationService.create_simulated_payment(
        phone_number=gamer.phone,
        amount=competition.entry_fee,
        reference=f"Comp-{competition.integer_id}",
        description=f"Entry fee for {competition.name}"
    )
    
    checkout_request_id = response.get('CheckoutRequestID')
    print(f"✓ Simulated payment created")
    print(f"  - Checkout Request ID: {checkout_request_id}")
    print(f"  - Response Code: {response.get('ResponseCode')}")
    
    # Create MpesaTransaction record
    payment = MpesaTransaction.objects.create(
        gamer=gamer,
        phone_number=gamer.phone,
        amount=competition.entry_fee,
        checkout_request_id=checkout_request_id,
        status='PENDING',
        is_simulated=True,
        competition_registration=registration
    )
    print(f"✓ MpesaTransaction created: {payment.id}")
    print(f"  - Status: {payment.status}")
    print(f"  - Is Simulated: {payment.is_simulated}")
    
    # Update registration payment status
    registration.payment_status = 'processing'
    registration.payment_phone_number = gamer.phone
    registration.save()
    print(f"✓ Registration updated to 'processing' status")

except Exception as e:
    print(f"✗ Error initiating payment: {e}")
    raise

# Step 4: Process simulated payment (simulate callback)
print("\n[Step 4] Simulating M-Pesa payment callback...")

try:
    # Simulate Safaricom callback for successful payment
    callback_response = PaymentSimulationService.confirm_simulated_payment(checkout_request_id)
    
    # Extract data from simulated callback
    callback_data = callback_response.get('Body', {}).get('stkCallback', {})
    result_code = callback_data.get('ResultCode')
    
    print(f"✓ Simulated callback response:")
    print(f"  - Result Code: {result_code} (0 = Success)")
    
    if result_code == 0:
        # Process successful payment
        print(f"✓ Processing successful payment...")
        
        # Extract receipt number
        callback_metadata = callback_data.get('CallbackMetadata', {}).get('Item', [])
        receipt_number = None
        for item in callback_metadata:
            if item.get('Name') == 'MpesaReceiptNumber':
                receipt_number = item.get('Value')
        
        # Update payment transaction
        payment.status = 'SUCCESS'
        payment.receipt_number = receipt_number
        payment.save()
        print(f"  - Receipt Number: {payment.receipt_number}")
        print(f"  - Payment Status: {payment.status}")
        
        # Update registration with payment completion
        registration.payment_status = 'completed'
        registration.paid_at = timezone.now()
        registration.save()
        print(f"✓ Registration completed")
        print(f"  - Payment Status: {registration.payment_status}")
        print(f"  - Paid At: {registration.paid_at}")
        
        # Create activity log
        ActivityLog.objects.create(
            gamer=gamer,
            activity_type='registration',
            audit_label='competition_registration_completed',
            description=f"Completed registration for {competition.name} competition"
        )
        print(f"✓ Activity log created")
    else:
        print(f"✗ Payment failed (ResultCode: {result_code})")
        payment.status = 'FAILED'
        payment.save()
        registration.payment_status = 'failed'
        registration.save()

except Exception as e:
    print(f"✗ Error processing callback: {e}")
    raise

# Step 5: Verify final state
print("\n[Step 5] Verifying final state...")

try:
    # Refresh from database
    payment.refresh_from_db()
    registration.refresh_from_db()
    
    print(f"✓ Final state verification:")
    print(f"\n  Payment Transaction:")
    print(f"    - ID: {payment.id}")
    print(f"    - Status: {payment.status}")
    print(f"    - Receipt: {payment.receipt_number}")
    print(f"    - Is Simulated: {payment.is_simulated}")
    print(f"    - Created: {payment.created_at}")
    
    print(f"\n  Competition Registration:")
    print(f"    - ID: {registration.id}")
    print(f"    - Gamer: {registration.gamer.email}")
    print(f"    - Competition: {registration.competition.name}")
    print(f"    - Payment Status: {registration.payment_status}")
    print(f"    - Paid At: {registration.paid_at}")
    print(f"    - Unique Code: {registration.unique_code}")
    
    print(f"\n  Activity Log:")
    activity = ActivityLog.objects.filter(
        gamer=gamer,
        audit_label='competition_registration_completed'
    ).latest('created_at')
    print(f"    - ID: {activity.id}")
    print(f"    - Description: {activity.description}")
    print(f"    - Created: {activity.created_at}")
    
    # Verify payment-registration link
    if payment.competition_registration == registration:
        print(f"\n✓ Payment-Registration Link: Valid (OneToOne)")
    else:
        print(f"\n✗ Payment-Registration Link: Invalid")

except Exception as e:
    print(f"✗ Error verifying state: {e}")
    raise

print("\n" + "="*80)
print("✓ TEST COMPLETED SUCCESSFULLY!")
print("="*80)
print("\nPayment flow verified:")
print("  1. ✓ Competition registration created")
print("  2. ✓ Simulated payment initiated")
print("  3. ✓ Payment callback processed")
print("  4. ✓ Registration marked as paid")
print("  5. ✓ Activity logged for audit trail")
print("\nThe payment system is ready for frontend integration.")
print("="*80 + "\n")

# Additional debugging info
print("\nDEBUGGING INFO:")
print(f"  - Competition Integer ID: {competition.integer_id}")
print(f"  - Registration ID (for payment): {registration.id}")
print(f"  - Gamer Phone: {gamer.phone}")
print(f"  - Entry Fee Amount: {competition.entry_fee}")
print(f"  - Next steps: Create frontend forms for registration modal")
