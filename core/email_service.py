from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from gami_konnect.settings import BASE_DIR
import environ
import os
import logging

logger = logging.getLogger(__name__)

# Initialize environ
env = environ.Env()
environ.Env.read_env()

# Read the .env file
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

def send_support_contact_email(subject, message, from_email=None):
    # Send a contact/support email to the configured support/admin address.
    try:
        support_email = getattr(settings, 'SUPPORT_EMAIL', None) or getattr(
            settings, 'ADMIN_EMAIL', settings.DEFAULT_FROM_EMAIL
        )
        
        send_mail(
            subject,
            message,
            from_email or settings.DEFAULT_FROM_EMAIL,
            [support_email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        logger.error(f"Error sending support contact email: {e}")
        return False


def send_verification_email(email, uid, role):
    try:
        # Generate email verification link
        verification_link = f"{env('SITE_URL')}/accounts/verify-email/{uid}"
        
        subject = f"Verify Your {role.title()} Account - {env('PROJECT_NAME')}"
        
        # Use the project's custom-designed email template
        html_message = render_to_string('accounts/email_templates/verification_email.html',
                                        {
                                            'verification_link': verification_link,
                                            'role': role,
                                            'project_name': env('PROJECT_NAME')
                                        })
        
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        logger.error(f"Error sending verification email: {e}")
        return False


def send_welcome_email(email, role, username=None):
    try:
        subject = f"Welcome to {env('PROJECT_NAME')}!"
        
        html_message = render_to_string('accounts/email_templates/welcome_email.html', {
            'role': role,
            'username': username,
            'project_name': settings.PROJECT_NAME
        })
        
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        logger.error(f"Error sending welcome email: {e}")
        return False


def send_profile_completion_email(email, username):
    try:
        subject = f"Profile Completed - {env('PROJECT_NAME')}"
        
        html_message = render_to_string('accounts/email_templates/profile_completion_email.html', {
            'username': username,
            'project_name': env('PROJECT_NAME')
        })
        
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        logger.error(f"Error sending profile completion email: {e}")
        return False


def send_shop_approval_email(shop, approved=True):
    try:
        owners_emails = [owner.email for owner in shop.owners.all()]
        
        if approved:
            subject = f"Shop Approved - {settings.PROJECT_NAME}"
            html_message = render_to_string('accounts/email_templates/shop_approved.html', {
                'shop': shop,
                'project_name': settings.PROJECT_NAME,
                'site_url': settings.SITE_URL
            })
        else:
            subject = f"Shop Application Update - {settings.PROJECT_NAME}"
            html_message = render_to_string('accounts/email_templates/shop_rejected.html', {
                'shop': shop,
                'project_name': settings.PROJECT_NAME
            })
        
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            owners_emails,
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        logger.error(f"Error sending shop approval email: {e}")
        return False


def send_password_change_email(email):
    try:
        subject = f"Password Changed - {env('PROJECT_NAME')}"
        
        html_message = render_to_string('accounts/email_templates/password_change.html', {
            'project_name': env('PROJECT_NAME')
        })
        
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        logger.error(f"Error sending password change email: {e}")
        return False


def send_account_deletion_email(email):
    try:
        subject = f"Account Deleted - {env('PROJECT_NAME')}"
        
        message = f"""
        Dear User,

        Your account has been successfully deleted from {env('PROJECT_NAME')}.

        We're sorry to see you go. If you change your mind, you can always create a new account.

        All your personal data has been permanently removed from our systems in accordance with our privacy policy.

        If you didn't request this deletion or have any concerns, please contact our support team immediately.

        Thank you for being part of {env('PROJECT_NAME')}.

        Best regards,
        The {env('PROJECT_NAME')} Team
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        logger.error(f"Error sending account deletion email: {e}")
        return False


def send_competition_result_notification(competition_result):
    """Send notification to admin when shop owner submits competition results"""
    try:
        from django.conf import settings
        
        admin_email = getattr(settings, 'ADMIN_EMAIL', settings.DEFAULT_FROM_EMAIL)
        competition = competition_result.competition
        shop_owner = competition_result.submitted_by
        
        subject = f"New Competition Results Submitted - {competition.title}"
        
        message = f"""
        A new competition result has been submitted for review.

        Competition: {competition.title}
        Shop: {competition.shop.name}
        Submitted by: {shop_owner.first_name} {shop_owner.last_name} ({shop_owner.email})
        Submitted at: {competition_result.submitted_at.strftime('%Y-%m-%d %H:%M:%S')}

        Summary: {competition_result.results_summary[:200]}

        Please review the results file and approve or reject it in the admin panel.

        Results File: {competition_result.results_file.url if competition_result.results_file else 'N/A'}

        Best regards,
        {settings.PROJECT_NAME} System
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [admin_email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        logger.error(f"Error sending competition result notification: {e}")
        return False