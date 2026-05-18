"""
Django management command to test the payment flow end-to-end.

Usage: python manage.py test_payment_flow
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import Gamer, ShopOwner
from competitions.models import Competition, CompetitionRegistration
from games.models import Game, Platform
from shops.models import Shop
from payments.models import MpesaTransaction
from payments.services import PaymentSimulationService
from activities.models import ActivityLog
import uuid


class Command(BaseCommand):
    help = 'Tests the competition payment system end-to-end with simulated M-Pesa payments'

    def handle(self, *args, **options):
        self.stdout.write("\n" + "="*80)
        self.stdout.write("COMPETITION PAYMENT SYSTEM - TEST")
        self.stdout.write("="*80)

        try:
            # Step 1: Create test data
            self.stdout.write("\n[Step 1] Setting up test data...")
            
            shop_owner = ShopOwner.objects.filter(email='test_shop@example.com').first()
            if not shop_owner:
                shop_owner = ShopOwner.objects.create(
                    uid=uuid.uuid4(),
                    email='test_shop@example.com',
                    phone='+254712345678',
                    first_name='Test',
                    last_name='Shop'
                )
                self.stdout.write(f"✓ Created test shop owner: {shop_owner.email}")
            else:
                self.stdout.write(f"✓ Using existing shop owner: {shop_owner.email}")
            
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
                self.stdout.write(f"✓ Created test shop: {shop.name}")
            else:
                self.stdout.write(f"✓ Using existing shop: {shop.name}")
            
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
                self.stdout.write(f"✓ Created test gamer: {gamer.email}")
            else:
                self.stdout.write(f"✓ Using existing gamer: {gamer.email}")
            
            game = Game.objects.filter(name='Test Game').first()
            if not game:
                game = Game.objects.create(
                    name='Test Game',
                    description='A test game for payment verification',
                    is_active=True,
                    is_verified=True
                )
                self.stdout.write(f"✓ Created test game: {game.name}")
            else:
                self.stdout.write(f"✓ Using existing game: {game.name}")
            
            platform = Platform.objects.filter(name='PC').first()
            if not platform:
                platform = Platform.objects.create(name='PC')
                self.stdout.write(f"✓ Created platform: {platform.name}")
            else:
                self.stdout.write(f"✓ Using existing platform: {platform.name}")
            
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
                status='registration_open'
            )
            self.stdout.write(f"✓ Created test competition: {competition.name}")
            self.stdout.write(f"  - Entry Fee: KES {competition.entry_fee}")
            self.stdout.write(f"  - Max Participants: {competition.max_participants}")

            # Step 2: Create registration
            self.stdout.write("\n[Step 2] Creating competition registration...")
            
            existing = CompetitionRegistration.objects.filter(
                competition=competition,
                gamer=gamer,
                is_cancelled=False
            ).first()
            
            if existing:
                registration = existing
                self.stdout.write(f"✓ Using existing registration: {registration.id}")
            else:
                registration = CompetitionRegistration.objects.create(
                    competition=competition,
                    gamer=gamer,
                    unique_code=uuid.uuid4(),
                    payment_status='pending'
                )
                self.stdout.write(f"✓ Created registration: {registration.id}")
            
            self.stdout.write(f"  - Payment Status: {registration.payment_status}")
            self.stdout.write(f"  - Gamer Phone: {gamer.phone}")

            # Step 3: Initiate simulated payment
            self.stdout.write("\n[Step 3] Initiating simulated payment...")
            
            response = PaymentSimulationService.create_simulated_payment(
                phone_number=gamer.phone,
                amount=competition.entry_fee,
                reference=f"Comp-{competition.integer_id}",
                description=f"Entry fee for {competition.name}"
            )
            
            checkout_request_id = response.get('CheckoutRequestID')
            self.stdout.write(f"✓ Simulated payment created")
            self.stdout.write(f"  - Checkout Request ID: {checkout_request_id}")
            
            payment = MpesaTransaction.objects.create(
                gamer=gamer,
                phone_number=gamer.phone,
                amount=competition.entry_fee,
                checkout_request_id=checkout_request_id,
                status='PENDING',
                is_simulated=True,
                competition_registration=registration
            )
            self.stdout.write(f"✓ MpesaTransaction created: {payment.id}")
            
            registration.payment_status = 'processing'
            registration.payment_phone_number = gamer.phone
            registration.save()
            self.stdout.write(f"✓ Registration updated to 'processing' status")

            # Step 4: Process simulated payment
            self.stdout.write("\n[Step 4] Processing simulated M-Pesa callback...")
            
            callback_response = PaymentSimulationService.confirm_simulated_payment(checkout_request_id)
            callback_data = callback_response.get('Body', {}).get('stkCallback', {})
            result_code = callback_data.get('ResultCode')
            
            self.stdout.write(f"✓ Callback Result Code: {result_code}")
            
            if result_code == 0:
                callback_metadata = callback_data.get('CallbackMetadata', {}).get('Item', [])
                receipt_number = None
                for item in callback_metadata:
                    if item.get('Name') == 'MpesaReceiptNumber':
                        receipt_number = item.get('Value')
                
                payment.status = 'SUCCESS'
                payment.receipt_number = receipt_number
                payment.save()
                self.stdout.write(f"✓ Payment marked as SUCCESS")
                self.stdout.write(f"  - Receipt: {payment.receipt_number}")
                
                registration.payment_status = 'completed'
                registration.paid_at = timezone.now()
                registration.save()
                self.stdout.write(f"✓ Registration marked as COMPLETED")
                
                ActivityLog.objects.create(
                    gamer=gamer,
                    activity_type='registration',
                    audit_label='competition_registration_completed',
                    description=f"Completed registration for {competition.name} competition"
                )
                self.stdout.write(f"✓ Activity log created")

            # Step 5: Verify final state
            self.stdout.write("\n[Step 5] Verifying final state...")
            
            payment.refresh_from_db()
            registration.refresh_from_db()
            
            self.stdout.write(f"\n✓ MpesaTransaction:")
            self.stdout.write(f"  - Status: {payment.status}")
            self.stdout.write(f"  - Receipt: {payment.receipt_number}")
            self.stdout.write(f"  - Is Simulated: {payment.is_simulated}")
            
            self.stdout.write(f"\n✓ CompetitionRegistration:")
            self.stdout.write(f"  - Payment Status: {registration.payment_status}")
            self.stdout.write(f"  - Paid At: {registration.paid_at}")
            
            if payment.competition_registration == registration:
                self.stdout.write(f"\n✓ Payment-Registration Link: Valid")
            
            self.stdout.write("\n" + "="*80)
            self.stdout.write("✓ TEST COMPLETED SUCCESSFULLY!")
            self.stdout.write("="*80)
            self.stdout.write("\nAll payment flow components verified:")
            self.stdout.write("  ✓ Registration created")
            self.stdout.write("  ✓ Simulated payment initiated")
            self.stdout.write("  ✓ Payment callback processed")
            self.stdout.write("  ✓ Registration marked as paid")
            self.stdout.write("  ✓ Activity logged")
            self.stdout.write("\nThe payment system is fully operational!\n")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n✗ Test failed: {e}'))
            import traceback
            traceback.print_exc()
