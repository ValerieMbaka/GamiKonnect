import hmac
import hashlib
import json
from decimal import Decimal
from unittest.mock import patch

from django.conf import settings
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import Gamer
from activities.models import Level
from competitions.models import Competition, CompetitionRegistration
from games.models import Counter, Game, Platform, PlatformCategory
from shops.models import Console, Shop

from .models import MpesaTransaction
from .views import initiate_payment, paystack_callback, paystack_webhook


def attach_session_and_messages(request):
	middleware = SessionMiddleware(lambda req: None)
	middleware.process_request(request)
	request.session.save()
	request._messages = FallbackStorage(request)
	return request


class PaystackPaymentFlowTests(TestCase):
	def setUp(self):
		Counter.objects.all().delete()

		self.factory = RequestFactory()

		self.level = Level.objects.create(name='Bronze', required_points=0, order=1)
		self.gamer = Gamer.objects.create(
			uid='uid-001',
			first_name='Test',
			last_name='Player',
			email='test@example.com',
			phone='0712345678',
			date_of_birth='2000-01-01',
			location='Nairobi',
			bio='Bio',
			about='About',
		)
		self.gamer.current_level = self.level
		self.gamer.save(update_fields=['current_level'])

		category = PlatformCategory.objects.create(name='Console', description='Console gaming')
		self.platform = Platform.objects.create(name='PlayStation 5', category=category, description='PS5')
		self.game = Game.objects.create(name='FIFA 26', description='Football game')
		self.game.supported_platforms.add(self.platform)

		self.shop = Shop.objects.create(
			name='Gami Hub',
			description='Main shop',
			city='Nairobi',
			location='CBD',
			building='Tower',
			floor='1',
			room_number='101',
			address='Nairobi CBD',
			opening_hours='9am',
			closing_hours='9pm',
			screen_number=4,
		)
		self.shop.games_available.add(self.game)
		Console.objects.create(shop=self.shop, console_type=self.platform, quantity=2)

		self.competition = Competition.objects.create(
			name='Friday Cup',
			description='Weekly competition',
			game=self.game,
			platform=self.platform,
			shop=self.shop,
			scheduled_time=timezone.now() + timezone.timedelta(days=2),
			max_participants=16,
			team_size=1,
			created_by=self.gamer,
			status='registration_open',
			entry_fee=Decimal('500.00'),
			registration_opens_at=timezone.now() - timezone.timedelta(hours=1),
			registration_closes_at=timezone.now() + timezone.timedelta(days=1),
		)

		self.registration = CompetitionRegistration.objects.create(
			competition=self.competition,
			gamer=self.gamer,
			payment_status='pending',
			payment_phone_number=self.gamer.phone,
		)

	def _authenticated_request(self, method, path, data=None, content_type='application/json'):
		request = getattr(self.factory, method.lower())(
			path,
			data=json.dumps(data or {}) if content_type == 'application/json' else data or {},
			content_type=content_type,
		)
		attach_session_and_messages(request)
		request.session['role'] = 'gamer'
		request.session['user_id'] = self.gamer.id
		return request

	@patch('payments.views.PaystackService.initialize_transaction')
	def test_initiate_payment_returns_authorization_url(self, mock_initialize):
		mock_initialize.return_value = {
			'status': True,
			'data': {
				'authorization_url': 'https://paystack.example/checkout',
				'reference': 'GK-ABC123',
			}
		}

		request = self._authenticated_request('post', reverse('payments:initiate_payment'), {
			'registration_id': str(self.registration.id),
			'phone_number': self.gamer.phone,
		})

		response = initiate_payment(request)
		payload = json.loads(response.content)

		self.assertEqual(response.status_code, 200)
		self.assertTrue(payload['success'])
		self.assertEqual(payload['authorization_url'], 'https://paystack.example/checkout')

		self.registration.refresh_from_db()
		self.assertEqual(self.registration.payment_status, 'processing')
		self.assertEqual(MpesaTransaction.objects.count(), 1)

	@patch('payments.views.PaystackService.verify_transaction')
	def test_paystack_callback_completes_registration(self, mock_verify):
		transaction = MpesaTransaction.objects.create(
			gamer=self.gamer,
			phone_number=self.gamer.phone,
			amount=self.competition.entry_fee,
			checkout_request_id='GK-REF-001',
			status='PENDING',
			competition_registration=self.registration,
		)

		mock_verify.return_value = {
			'status': True,
			'data': {
				'status': 'success',
				'id': 987654321,
				'reference': transaction.checkout_request_id,
			}
		}

		request = self.factory.get(reverse('payments:paystack_callback'), {'reference': transaction.checkout_request_id})
		attach_session_and_messages(request)
		response = paystack_callback(request)

		self.assertEqual(response.status_code, 302)
		self.registration.refresh_from_db()
		transaction.refresh_from_db()
		self.assertEqual(self.registration.payment_status, 'completed')
		self.assertEqual(transaction.status, 'SUCCESS')

	@patch('payments.views.PaystackService.verify_transaction')
	def test_paystack_webhook_valid_signature_confirms_payment(self, mock_verify):
		transaction = MpesaTransaction.objects.create(
			gamer=self.gamer,
			phone_number=self.gamer.phone,
			amount=self.competition.entry_fee,
			checkout_request_id='GK-WEBHOOK-001',
			status='PENDING',
			competition_registration=self.registration,
		)

		mock_verify.return_value = {
			'status': True,
			'data': {
				'status': 'success',
				'id': 111222333,
				'reference': transaction.checkout_request_id,
			}
		}

		payload = {
			'event': 'charge.success',
			'data': {
				'reference': transaction.checkout_request_id,
			},
		}
		raw_body = json.dumps(payload).encode('utf-8')
		signature = hmac.new(
			(settings.PAYSTACK_SECRET_KEY or '').encode('utf-8'),
			raw_body,
			hashlib.sha512,
		).hexdigest()

		request = self.factory.post(
			reverse('payments:paystack_webhook'),
			data=raw_body,
			content_type='application/json',
			HTTP_X_PAYSTACK_SIGNATURE=signature,
		)
		response = paystack_webhook(request)

		self.assertEqual(response.status_code, 200)
		self.registration.refresh_from_db()
		transaction.refresh_from_db()
		self.assertEqual(self.registration.payment_status, 'completed')
		self.assertEqual(transaction.status, 'SUCCESS')

	def test_paystack_webhook_rejects_invalid_signature(self):
		request = self.factory.post(
			reverse('payments:paystack_webhook'),
			data=json.dumps({'event': 'charge.success', 'data': {'reference': 'GK-123'}}),
			content_type='application/json',
			HTTP_X_PAYSTACK_SIGNATURE='bad-signature',
		)

		response = paystack_webhook(request)
		self.assertEqual(response.status_code, 401)
