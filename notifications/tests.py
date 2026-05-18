"""
Comprehensive tests for the notifications app.

Tests cover:
1. Signal handlers (notification creation on user events)
2. Services (email delivery, group filtering, cleanup)
3. Integration tests (full notification flow)
"""

from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from django.core import mail
from datetime import timedelta
from accounts.models import Gamer, Account
from games.models import Game
from competitions.models import Competition, CompetitionRegistration, CompetitionResult
from progression.models import GamerLevel, Level, GamerAchievement, Achievement
from payments.models import MpesaTransaction
from .models import Notification, NotificationRecipient, NotificationGroup
from .services import (
    send_notification_to_users,
    get_group_users,
    cleanup_expired_notifications,
    render_notification_message,
)


class NotificationSignalHandlerTests(TransactionTestCase):
    """Test notification creation via Django signals."""

    def setUp(self):
        """Create test data."""
        self.account = Account.objects.create_user(
            email='gamer@test.com',
            password='testpass123'
        )
        self.gamer = Gamer.objects.create(
            account_ptr=self.account,
            uid='test_uid',
            profile_completed=False
        )

    def test_gamer_registration_notification(self):
        """Test that a notification is created when a gamer registers."""
        # This happens via the on_gamer_registered signal
        initial_count = Notification.objects.count()
        
        # Create a new gamer (simulating registration)
        account2 = Account.objects.create_user(
            email='newgamer@test.com',
            password='testpass123'
        )
        gamer2 = Gamer.objects.create(
            account_ptr=account2,
            uid='test_uid_2',
            profile_completed=False
        )
        
        # Check if notification was created
        new_notifications = Notification.objects.filter(
            title__icontains='Welcome'
        )
        self.assertGreater(new_notifications.count(), 0)

    def test_profile_completion_notification(self):
        """Test that a notification is created when profile is completed."""
        # Update gamer profile to mark as complete
        self.gamer.profile_completed = True
        self.gamer.save()
        
        # Check if profile completion notification was created
        notifications = Notification.objects.filter(
            title__icontains='Profile'
        )
        self.assertTrue(notifications.exists())

    def test_level_up_notification(self):
        """Test that a notification is created when gamer levels up."""
        # Create a level
        level1 = Level.objects.create(name='Level 1', required_points=0)
        level2 = Level.objects.create(name='Level 2', required_points=100)
        
        # Create gamer level
        gamer_level = GamerLevel.objects.create(
            gamer=self.gamer,
            level=level1,
            points=0
        )
        
        # Level up
        gamer_level.level = level2
        gamer_level.points = 100
        gamer_level.save()
        
        # Check if level up notification was created
        notifications = Notification.objects.filter(
            title__icontains='Level Up'
        )
        self.assertTrue(notifications.exists())

    def test_achievement_unlocked_notification(self):
        """Test that a notification is created when achievement is unlocked."""
        # Create an achievement
        achievement = Achievement.objects.create(
            name='First Win',
            description='Win your first competition'
        )
        
        # Unlock achievement
        gamer_achievement = GamerAchievement.objects.create(
            gamer=self.gamer,
            achievement=achievement
        )
        
        # Check if achievement notification was created
        notifications = Notification.objects.filter(
            title__icontains='Achievement'
        )
        self.assertTrue(notifications.exists())


class NotificationServiceTests(TestCase):
    """Test notification services."""

    def setUp(self):
        """Create test data."""
        self.account = Account.objects.create_user(
            email='gamer@test.com',
            password='testpass123'
        )
        self.gamer = Gamer.objects.create(
            account_ptr=self.account,
            uid='test_uid',
            profile_completed=True
        )
        
        self.notification = Notification.objects.create(
            title='Test Notification',
            message='This is a test message',
            category='general',
            importance='medium'
        )

    def test_send_notification_to_users(self):
        """Test sending notification to multiple users."""
        stats = send_notification_to_users(
            notification=self.notification,
            user_list=[self.gamer],
            send_email=False,
            send_in_app=True
        )
        
        # Check statistics
        self.assertEqual(stats['created'], 1)
        self.assertEqual(stats['updated'], 0)
        
        # Check recipient was created
        recipient = NotificationRecipient.objects.get(
            notification=self.notification,
            user=self.gamer
        )
        self.assertFalse(recipient.is_read)
        self.assertEqual(recipient.delivery_status, 'pending')

    def test_send_notification_email(self):
        """Test sending notification via email."""
        stats = send_notification_to_users(
            notification=self.notification,
            user_list=[self.gamer],
            send_email=True,
            send_in_app=True
        )
        
        # Check email was sent
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertIn(self.gamer.email, email.to)
        self.assertIn(self.notification.title, email.subject)

    def test_mark_as_read(self):
        """Test marking notification as read."""
        recipient = NotificationRecipient.objects.create(
            notification=self.notification,
            user=self.gamer,
            is_read=False
        )
        
        # Mark as read
        recipient.mark_as_read()
        
        # Check status
        recipient.refresh_from_db()
        self.assertTrue(recipient.is_read)
        self.assertIsNotNone(recipient.read_at)

    def test_render_notification_message(self):
        """Test template rendering for notifications."""
        template = "Hello {{username}}, welcome to {{platform}}"
        context = {
            'username': 'TestUser',
            'platform': 'GamiKonnect'
        }
        
        rendered = render_notification_message(template, context)
        self.assertEqual(rendered, "Hello TestUser, welcome to GamiKonnect")

    def test_notification_expiry(self):
        """Test that notifications expire based on importance."""
        # Create notifications with different importance levels
        low_notif = Notification.objects.create(
            title='Low Priority',
            message='Low priority message',
            category='general',
            importance='low'
        )
        
        critical_notif = Notification.objects.create(
            title='Critical Alert',
            message='Critical alert message',
            category='system',
            importance='critical'
        )
        
        # Check expiry dates
        now = timezone.now()
        
        # Low should expire in ~7 days
        low_delta = (low_notif.expires_at - now).days
        self.assertIn(low_delta, [6, 7, 8])  # Allow small variance
        
        # Critical should expire in ~90 days
        critical_delta = (critical_notif.expires_at - now).days
        self.assertGreater(critical_delta, 80)


class NotificationGroupTests(TestCase):
    """Test notification group filtering."""

    def setUp(self):
        """Create test data."""
        # Create multiple gamers
        self.accounts = []
        self.gamers = []
        for i in range(3):
            account = Account.objects.create_user(
                email=f'gamer{i}@test.com',
                password='testpass123'
            )
            gamer = Gamer.objects.create(
                account_ptr=account,
                uid=f'uid_{i}',
                profile_completed=True
            )
            self.accounts.append(account)
            self.gamers.append(gamer)
        
        # Create a game
        self.game = Game.objects.create(
            name='TestGame',
            is_active=True
        )
        
        # Add game to first gamer
        self.gamers[0].games.add(self.game)

    def test_group_all_users(self):
        """Test filtering all users."""
        group = NotificationGroup.objects.create(
            name='All Users',
            criteria_type='all_users',
            criteria_data={}
        )
        
        users = get_group_users(group)
        self.assertIn(self.gamers[0], users)
        self.assertIn(self.gamers[1], users)

    def test_group_by_game(self):
        """Test filtering users by game."""
        group = NotificationGroup.objects.create(
            name='Game Players',
            criteria_type='game',
            criteria_data={'games': [self.game.name]}
        )
        
        users = get_group_users(group)
        self.assertIn(self.gamers[0], users)
        self.assertNotIn(self.gamers[1], users)

    def test_group_by_custom_users(self):
        """Test filtering by custom user IDs."""
        group = NotificationGroup.objects.create(
            name='Custom Group',
            criteria_type='custom',
            criteria_data={'user_ids': [self.gamers[0].id, self.gamers[1].id]}
        )
        
        users = get_group_users(group)
        self.assertIn(self.gamers[0], users)
        self.assertIn(self.gamers[1], users)
        self.assertNotIn(self.gamers[2], users)


class NotificationCleanupTests(TestCase):
    """Test expired notification cleanup."""

    def setUp(self):
        """Create test data."""
        self.account = Account.objects.create_user(
            email='gamer@test.com',
            password='testpass123'
        )
        self.gamer = Gamer.objects.create(
            account_ptr=self.account,
            uid='test_uid',
            profile_completed=True
        )

    def test_cleanup_expired_notifications(self):
        """Test that expired notifications are deleted."""
        now = timezone.now()
        
        # Create an expired notification
        expired = Notification.objects.create(
            title='Expired',
            message='This should be deleted',
            category='general',
            importance='low',
            expires_at=now - timedelta(days=1)
        )
        
        # Create a fresh notification
        fresh = Notification.objects.create(
            title='Fresh',
            message='This should remain',
            category='general',
            importance='medium',
            expires_at=now + timedelta(days=7)
        )
        
        # Create recipients
        NotificationRecipient.objects.create(
            notification=expired,
            user=self.gamer
        )
        NotificationRecipient.objects.create(
            notification=fresh,
            user=self.gamer
        )
        
        # Run cleanup
        stats = cleanup_expired_notifications()
        
        # Check results
        self.assertEqual(stats['deleted_notifications'], 1)
        self.assertTrue(
            Notification.objects.filter(id=fresh.id).exists()
        )
        self.assertFalse(
            Notification.objects.filter(id=expired.id).exists()
        )

    def test_cleanup_preserves_critical(self):
        """Test that critical notifications are preserved longer."""
        now = timezone.now()
        
        # Create a critical notification that expired 30 days ago
        critical = Notification.objects.create(
            title='Critical Alert',
            message='Critical message',
            category='system',
            importance='critical',
            expires_at=now - timedelta(days=30)
        )
        
        # Create a low importance notification that expired 10 days ago
        low = Notification.objects.create(
            title='Low Priority',
            message='Low message',
            category='general',
            importance='low',
            expires_at=now - timedelta(days=10)
        )
        
        # Run cleanup
        stats = cleanup_expired_notifications()
        
        # Critical should be deleted (after 90 days)
        # Low should definitely be deleted (after 7 days)
        self.assertEqual(stats['deleted_notifications'], 1)


class NotificationIntegrationTests(TransactionTestCase):
    """Integration tests for complete notification flow."""

    def setUp(self):
        """Create test data."""
        self.account = Account.objects.create_user(
            email='gamer@test.com',
            password='testpass123'
        )
        self.gamer = Gamer.objects.create(
            account_ptr=self.account,
            uid='test_uid',
            profile_completed=True
        )

    def test_complete_notification_flow(self):
        """Test complete flow: create → send → read → cleanup."""
        # 1. Create notification
        notification = Notification.objects.create(
            title='Test Flow',
            message='Testing complete flow',
            category='general',
            importance='medium'
        )
        
        # 2. Send to user
        stats = send_notification_to_users(
            notification=notification,
            user_list=[self.gamer],
            send_email=False,
            send_in_app=True
        )
        self.assertEqual(stats['created'], 1)
        
        # 3. Check notification exists
        recipient = NotificationRecipient.objects.get(
            notification=notification,
            user=self.gamer
        )
        self.assertFalse(recipient.is_read)
        
        # 4. Mark as read
        recipient.mark_as_read()
        recipient.refresh_from_db()
        self.assertTrue(recipient.is_read)
        
        # 5. Verify notification count
        unread_count = NotificationRecipient.objects.filter(
            user=self.gamer,
            is_read=False
        ).count()
        self.assertEqual(unread_count, 0)

    def test_notification_group_bulk_send(self):
        """Test sending notification to a group of users."""
        # Create multiple gamers
        gamers = []
        for i in range(3):
            account = Account.objects.create_user(
                email=f'gamer{i}@test.com',
                password='testpass123'
            )
            gamer = Gamer.objects.create(
                account_ptr=account,
                uid=f'uid_{i}',
                profile_completed=True
            )
            gamers.append(gamer)
        
        # Create group
        group = NotificationGroup.objects.create(
            name='All Users',
            criteria_type='all_users',
            criteria_data={}
        )
        
        # Get group users
        users = get_group_users(group)
        
        # Create and send notification
        notification = Notification.objects.create(
            title='Group Message',
            message='Message to all users',
            category='general',
            importance='low'
        )
        
        stats = send_notification_to_users(
            notification=notification,
            user_list=users,
            send_email=False,
            send_in_app=True
        )
        
        # Check all recipients created
        recipient_count = NotificationRecipient.objects.filter(
            notification=notification
        ).count()
        self.assertGreaterEqual(recipient_count, 3)
