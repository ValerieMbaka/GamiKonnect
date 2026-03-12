import logging
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.core.signing import TimestampSigner

logger = logging.getLogger(__name__)


class EmailManager:
    # Centralized service for dispatching application emails
    
    @staticmethod
    def _send_html_email(subject, template_path, context, recipient_list, from_email=None):
        try:
            if 'project_name' not in context:
                context['project_name'] = getattr(settings, 'PROJECT_NAME', 'GamiKonnect')
            if 'support_email' not in context:
                context['support_email'] = getattr(settings, 'SUPPORT_EMAIL', 'support@gamikonnect.com')
            
            html_message = render_to_string(f'accounts/email_templates/{template_path}', context)
            plain_message = strip_tags(html_message)
            sender = from_email or getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@gamikonnect.com')
            
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=sender,
                recipient_list=recipient_list,
                html_message=html_message,
                fail_silently=False,
            )
            return True
        except Exception as e:
            logger.error(f"Error sending email '{subject}' to {recipient_list}: {e}")
            return False
    
    @classmethod
    def send_support_contact(cls, subject, message, from_email=None):
        support_email = getattr(settings, 'SUPPORT_EMAIL', getattr(settings, 'ADMIN_EMAIL'))
        try:
            send_mail(subject, message, from_email or settings.DEFAULT_FROM_EMAIL, [support_email], fail_silently=False)
            return True
        except Exception as e:
            logger.error(f"Error sending support contact email: {e}")
            return False
    
    # Shared emails
    @classmethod
    def send_verification(cls, email, uid, role):
        site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
        context = {
            'verification_link': f"{site_url}/accounts/verify-email/{uid}",
            'role': role
        }
        subject = f"Verify Your {role.title()} Account - {settings.PROJECT_NAME}"
        return cls._send_html_email(subject, 'shared/verification_email.html', context, [email])
    
    @classmethod
    def send_welcome(cls, email, role, username=None):
        subject = f"Welcome to {settings.PROJECT_NAME}!"
        context = {
            'role': role,
            'username': username,
            'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000')
        }
        return cls._send_html_email(subject, 'shared/welcome_email.html', context, [email])
    
    @classmethod
    def send_password_change(cls, email, username=None):
        subject = f"Password Changed - {settings.PROJECT_NAME}"
        return cls._send_html_email(subject, 'shared/password_change.html', {'username': username}, [email])
    
    @classmethod
    def send_password_reset(cls, email, reset_link, username=None):
        subject = f"Password Reset Request - {settings.PROJECT_NAME}"
        context = {'username': username, 'reset_link': reset_link, 'expiration_minutes': 30}
        return cls._send_html_email(subject, 'shared/password_reset.html', context, [email])
    
    @classmethod
    def send_account_deletion(cls, email):
        subject = f"Account Deleted - {settings.PROJECT_NAME}"
        return cls._send_html_email(subject, 'shared/account_deleted.html', {}, [email])
    
    # Gamer emails
    @classmethod
    def send_profile_completion(cls, email, username):
        subject = f"Profile Completed Successfully - {settings.PROJECT_NAME}"
        site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
        context = {
            'gamer_name': username,
            'dashboard_link': f"{site_url}/accounts/gamer-dashboard/"  # <-- Swapped to dashboard link
        }
        return cls._send_html_email(subject, 'gamers/profile_completion_email.html', context, [email])
    
    # Shop Owner emails
    @classmethod
    def send_shop_approval(cls, shop, approved=True):
        owners_emails = [owner.email for owner in shop.owners.all()]
        if not owners_emails and getattr(shop, 'submitted_by_email', None):
            owners_emails = [shop.submitted_by_email]
        
        context = {'shop': shop, 'site_url': settings.SITE_URL}
        
        if approved:
            subject = f"Shop Approved - {settings.PROJECT_NAME}"
            return cls._send_html_email(subject, 'shop_owners/shop_approved.html', context, owners_emails)
        else:
            subject = f"Shop Application Update - {settings.PROJECT_NAME}"
            return cls._send_html_email(subject, 'shop_owners/shop_rejected.html', context, owners_emails)
    
    # Admin emails
    @classmethod
    def send_admin_new_shop(cls, shop):
        subject = f"ACTION REQUIRED: New Shop Submission - {settings.PROJECT_NAME}"
        admin_email = getattr(settings, 'ADMIN_EMAIL', settings.DEFAULT_FROM_EMAIL)
        
        signer = TimestampSigner()
        # Bind the action securely into the token payload
        approve_token = signer.sign_object({'shop_id': shop.id, 'action': 'approve'})
        reject_token = signer.sign_object({'shop_id': shop.id, 'action': 'reject'})
        
        quick_approve_url = f"{settings.SITE_URL}/accounts/quick-approve-shop/{approve_token}/"
        quick_reject_url = f"{settings.SITE_URL}/accounts/quick-reject-shop/{reject_token}/"
        
        context = {
            'shop': shop,
            'submitter_email': shop.submitted_by_email or 'N/A',
            'submitter_uid': shop.submitted_by_uid or 'N/A',
            'admin_dashboard_url': f"{settings.SITE_URL}/admin/shops/shop/",
            'quick_approve_url': quick_approve_url,
            'quick_reject_url': quick_reject_url
        }
        return cls._send_html_email(subject, 'admin/admin_new_shop.html', context, [admin_email])
    
    @classmethod
    def send_admin_account_deletion(cls, email):
        subject = f"SYSTEM ALERT: Account Deletion - {settings.PROJECT_NAME}"
        admin_email = getattr(settings, 'ADMIN_EMAIL', settings.DEFAULT_FROM_EMAIL)
        context = {'deleted_email': email}
        return cls._send_html_email(subject, 'admin/admin_account_deletion.html', context, [admin_email])
    
    @classmethod
    def send_competition_result_notification(cls, competition_result):
        admin_email = getattr(settings, 'ADMIN_EMAIL', settings.DEFAULT_FROM_EMAIL)
        competition = competition_result.competition
        shop_owner = competition_result.submitted_by
        subject = f"SYSTEM ALERT: Competition Results Submitted - {competition.title}"
        context = {
            'competition': competition,
            'shop_owner': shop_owner,
            'summary': competition_result.results_summary,
            'admin_dashboard_url': f"{settings.SITE_URL}/admin/"
        }
        return cls._send_html_email(subject, 'admin/admin_competition_result.html', context, [admin_email])