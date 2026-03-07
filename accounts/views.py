from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import transaction, connection, IntegrityError, models
from django.core.mail import send_mail
from django.core.paginator import Paginator
import json
import logging
import re
import datetime

# Import site-context
from core.views import base_site_context

# Firebase imports
from firebase_config import initialize_firebase
from firebase_admin import auth as firebase_auth

# Model imports
from .models import Account, Gamer, ShopOwner, PendingRegistration
from games.models import Game, Platform
from shops.models import Shop, Console, GamePricing

# Email service imports
from core.email_service import (
    send_verification_email, send_welcome_email, send_profile_completion_email,
    send_shop_approval_email, send_password_change_email, send_account_deletion_email,
    send_competition_result_notification
)

logger = logging.getLogger(__name__)


def is_valid_uuid(val):
    if not val:
        return False
    try:
        import uuid as uuid_pkg
        uuid_pkg.UUID(str(val))
        return True
    except (ValueError, AttributeError, TypeError, ImportError):
        return False


# Ensure Firebase is initialized
firebase_app = initialize_firebase()
import uuid as uuid_pkg # Avoid conflict with is_valid_uuid logic / just use uuid module

# Account provisioning helpers
def provision_account_from_pending(pending):
    # Create an Account from a Pending Registration
    if not pending:
        return None
    
    with transaction.atomic():
        try:
            # Create the appropriate child model directly
            if pending.role == 'gamer':
                # Create Gamer directly
                gamer = Gamer.objects.create(
                    uid=pending.uid,
                    email=pending.email,
                    first_name=pending.first_name,
                    last_name=pending.last_name,
                    phone=pending.phone,
                    
                    # Set default gamer fields
                    custom_username=f"user{pending.uid[:8]}",  # Temporary username
                    bio="Bio",
                    about="About",
                    location="Unknown"
                )
                account = gamer
                logger.info(f"Successfully created Gamer account: {gamer.email}")
            
            else:
                # Create ShopOwner directly
                try:
                    with transaction.atomic():
                        """
                        Try to create as base Account first, but PendingRegistration already has details
                        Although, if we are in provisioning, the Account might not exist yet.
                        Therefore to be safe against IntegrityError if it DOES exist:
                        """
                        shop_owner = ShopOwner.objects.filter(uid=pending.uid).first()
                        if not shop_owner:
                            # Check if Account exists
                            account = Account.objects.filter(uid=pending.uid).first()
                            if account:
                                shop_owner = ShopOwner(
                                    account_ptr_id=account.id,
                                    uid=account.uid,
                                    email=account.email,
                                    first_name=account.first_name,
                                    last_name=account.last_name,
                                    phone=account.phone,
                                    date_joined=timezone.now()
                                )
                                shop_owner.save()
                            else:
                                shop_owner = ShopOwner.objects.create(
                                    uid=pending.uid,
                                    email=pending.email,
                                    first_name=pending.first_name,
                                    last_name=pending.last_name,
                                    phone=pending.phone
                                )
                        account = shop_owner
                except IntegrityError:
                    shop_owner = ShopOwner.objects.filter(uid=pending.uid).first()
                    account = shop_owner

                logger.info(f"Successfully created ShopOwner account: {account.email}")
            
            # Delete the pending registration
            pending.delete()
            return account
        
        except Exception as e:
            logger.error(f"Failed to provision account from pending: {e}")
            raise


# Helper to resolve platforms from common names
def get_platform_by_string(platform_str):
    if not platform_str:
        return None

    # Normalize input
    platform_str = platform_str.strip().upper()

    # Common mappings for gaming consoles and categories
    mappings = {
        'PLAYSTATION_5': ['PS5', 'playstation-5', 'playstation 5'],
        'PLAYSTATION_4': ['PS4', 'playstation-4', 'playstation 4'],
        'PLAYSTATION': ['PS5', 'PS4', 'playstation'],
        'XBOX_SERIES_X': ['Xbox Series X', 'xbox-series-x'],
        'XBOX_SERIES_S': ['Xbox Series S', 'xbox-series-s', 'Xbox Series X|S'],
        'XBOX_ONE': ['Xbox One', 'xbox-one'],
        'XBOX': ['Xbox Series X', 'Xbox One', 'xbox'],
        'NINTENDO_SWITCH': ['Nintendo Switch', 'nintendo-switch'],
        'NINTENDO': ['Nintendo Switch', 'nintendo'],
        'PC': ['Gaming PC', 'pc', 'steam'],
    }

    candidates = mappings.get(platform_str, [platform_str])

    # Try direct match on name or slug
    for candidate in candidates:
        platform = Platform.objects.filter(
            models.Q(name__iexact=candidate) |
            models.Q(slug__iexact=candidate.lower().replace(' ', '-').replace('_', '-'))
        ).first()
        if platform:
            return platform

    # Fallback to category if it's a category name being sent
    platform = Platform.objects.filter(
        models.Q(category__name__iexact=platform_str.replace('_', ' ')) |
        models.Q(category__slug__iexact=platform_str.lower().replace('_', '-'))
    ).first()

    return platform


# Notify admin about a new shop submission
def notify_admin_new_shop(shop):
    try:
        subject = f"New Shop Submission: {shop.name} - {settings.PROJECT_NAME}"
        message = f"""
        Admin Notification:

        A new shop has been submitted for approval:
        - Shop Name: {shop.name}
        - Location: {shop.location}
        - Submitter Email: {shop.submitted_by_email or 'N/A'}
        - Submitter UID: {shop.submitted_by_uid or 'N/A'}
        - Time: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}

        Please review the shop details in the admin dashboard.
        """
        admin_email = getattr(settings, 'ADMIN_EMAIL', settings.DEFAULT_FROM_EMAIL)
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [admin_email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        logger.error(f"Error sending admin notification for new shop: {e}")
        return False


# AUTHENTICATION VIEWS
def register_view(request):
    # Create all users first as gamers
    role = request.GET.get('role', 'gamer').lower()
    if role != 'gamer':
        role = 'gamer'
    role_label = "Gamer"
    
    context = {
        **base_site_context(),
        'role': role,
        'role_label': role_label
    }
    return render(request, 'accounts/register.html', context)


@csrf_exempt
def register_submit(request):
    if request.method == 'POST':
        try:
            uid = request.POST.get('uid')
            email = request.POST.get('email')
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            phone = request.POST.get('phone_number')
            role = 'gamer'
            
            logger.info("Starting registration for email=%s, uid=%s", email, uid)
            
            # Validate role
            if role not in ['gamer', 'shop_owner']:
                return JsonResponse({'success': False, 'message': 'Invalid role'})
            
            # If the email already has a verified Account, block duplicate
            if Account.objects.filter(email=email).exists():
                logger.warning("Registration blocked: Email %s already exists in Account table", email)
                return JsonResponse({'success': False, 'message': 'Email already registered'})
            
            # If the UID or email/phone has a pending registration, update details
            pending = None
            try:
                pending = PendingRegistration.objects.get(uid=uid)
            except PendingRegistration.DoesNotExist:
                pending = None
            
            # Prevent duplicate pending by email/phone
            if not pending:
                if PendingRegistration.objects.filter(email=email).exists():
                    logger.info("Registration: Found existing pending registration for %s by email", email)
                    return JsonResponse({'success': False,
                                         'message': 'A verification email was already sent. Please verify your email or '
                                                    'resend the verification email from the login page.'})
                if PendingRegistration.objects.filter(phone=phone).exists():
                    return JsonResponse(
                        {'success': False, 'message': 'Phone number already used in a pending registration'})
            
            if pending:
                logger.info("Updating existing pending registration for uid=%s", uid)
                pending.email = email
                pending.first_name = first_name
                pending.last_name = last_name
                pending.phone = phone
                pending.role = role
                pending.save()
            else:
                logger.info("Creating new pending registration for uid=%s", uid)
                PendingRegistration.objects.create(
                    uid=uid,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    phone=phone,
                    role=role,
                )
            
            # Send verification email via Firebase link
            email_sent = send_verification_email(email, uid, role)
            if not email_sent:
                logger.error("Failed to send verification email during registration for %s", email)
                return JsonResponse({
                    'success': False,
                    'message': 'We could not send the verification email. Please try again or contact support.'
                })
            return JsonResponse({
                'success': True,
                'message': 'Registration successful. Please check your email to verify your account.'
            })
        
        except Exception as e:
            logger.error(f"Registration error: {e}")
            return JsonResponse({
                'success': False,
                'message': 'Registration failed. Please try again.'
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})


def login_view(request):
    # Ensure any previous resend flag does not persist across sessions unexpectedly
    request.session.pop('show_resend', None)
    context = base_site_context()
    return render(request, 'accounts/login.html', context)


@csrf_exempt
def session_login(request):
    if request.method == 'POST':
        try:
            id_token = request.POST.get('id_token')
            firebase_uid = request.POST.get('firebase_uid')
            
            # Verify Firebase token
            try:
                # Allow a small clock skew (max 60s per Firebase Admin SDK)
                decoded_token = firebase_auth.verify_id_token(id_token, clock_skew_seconds=60)
            except Exception as ve:
                logger.error(f"Login error during token verify: {ve}")
                message = str(ve)
                if 'Token used too early' in message or 'clock' in message.lower():
                    return JsonResponse({
                        'success': False,
                        'message': 'Temporary clock sync issue detected. Please try again in a few seconds.'
                    })
                return JsonResponse({
                    'success': False,
                    'message': 'Login failed. Please try again.'
                })
            uid = decoded_token['uid']
            
            # Check if user exists in database
            account = None
            role = None
            user_obj = None

            # Try to find as Gamer first, then ShopOwner
            try:
                user_obj = Gamer.objects.get(uid=uid)
                role = 'gamer'
                account = user_obj
            except Gamer.DoesNotExist:
                try:
                    user_obj = ShopOwner.objects.get(uid=uid)
                    role = 'shop_owner'
                    account = user_obj
                except ShopOwner.DoesNotExist:
                    # Account missing in database. Try to provision if verified in Firebase.
                    firebase_user = firebase_auth.get_user(uid)
                    pending = None
                    try:
                        pending = PendingRegistration.objects.get(uid=uid)
                    except PendingRegistration.DoesNotExist:
                        if firebase_user.email:
                            try:
                                pending = PendingRegistration.objects.get(email=firebase_user.email)
                            except PendingRegistration.DoesNotExist:
                                pending = None
                    
                    if pending:
                        if not firebase_user.email_verified:
                            request.session['show_resend'] = pending.email
                            return JsonResponse({
                                'success': False,
                                'message': 'Please verify your account first to login'
                            })
                        
                        # Provision verified user
                        logger.info("Provisioning account during login uid=%s", uid)
                        account = provision_account_from_pending(pending)
                        if account:
                            if isinstance(account, Gamer):
                                role = 'gamer'
                                user_obj = account
                            else:
                                # If they chose shop_owner in registration, start as a gamer until shop approval.
                                # However, keep 'shop_owner' role
                                # The redirect logic below handles the actual dashboard routing.
                                role = 'shop_owner'
                                user_obj = account
                        else:
                            return JsonResponse({'success': False, 'message': 'Failed to create user record'})
                    else:
                        # No pending registration found
                        return JsonResponse({
                            'success': False,
                            'message': 'Account not found. Please create an account to proceed',
                            'redirect': reverse('accounts:register')
                        })
            
            # Re-check email verification state for existing users
            firebase_user = firebase_auth.get_user(uid)
            if not firebase_user.email_verified:
                request.session['show_resend'] = account.email
                return JsonResponse({
                    'success': False,
                    'message': 'Please verify your account first to login'
                })
            
            # Create session
            request.session['user_id'] = account.id
            request.session['firebase_uid'] = uid
            request.session['email'] = account.email
            request.session['role'] = role
            request.session['first_name'] = account.first_name
            request.session['last_name'] = account.last_name
            
            # If user is both a gamer and a shop owner, ensure they use the shop_owner role if they have approved shops
            # Only switch to 'shop_owner' role if they have at least ONE ACTIVE shop.
            try:
                shop_owner = ShopOwner.objects.get(uid=uid)
                request.session['user_id'] = shop_owner.id
                request.session['role'] = 'shop_owner'
                role = 'shop_owner'
                account = shop_owner
            except ShopOwner.DoesNotExist:
                # If they only have a Gamer record, role remains 'gamer'
                pass
            
            # Set session expiry
            request.session.set_expiry(86400)  # 24 hours
            
            # Send welcome email on first login
            if not user_obj.last_login:
                send_welcome_email(account.email, role, account.first_name)
                user_obj.last_login = timezone.now()
                user_obj.save()
            
            # Determine next redirect
            next_url = request.session.pop('post_login_redirect', None)
            
            # Redirect based on role
            # If no preserved intent, always go to gamer dashboard unless they are an active shop owner
            if not next_url:
                if role == 'shop_owner':
                    next_url = reverse('accounts:shop_owner_dashboard')
                else:
                    next_url = reverse('accounts:gamer_dashboard')
            
            success_message = 'Login successful, loading dashboard' if role == 'gamer' else 'Login successful, please upload your game shop details to proceed'
            return JsonResponse({
                'success': True,
                'message': success_message,
                'role': role,
                'next': next_url
            })
        
        except Exception as e:
            logger.error(f"Login error: {e}", exc_info=True)
            return JsonResponse({
                'success': False,
                'message': 'Login failed. Please try again.'
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})


def verify_email(request, uid):
    try:
        # Preserve intent if provided, so post-login can resume the intended action
        next_url = request.GET.get('next')
        if next_url:
            try:
                request.session['post_login_redirect'] = next_url
            except Exception:
                pass
        
        firebase_user = firebase_auth.get_user(uid)
        
        # Mark verified in Firebase if not already
        if not firebase_user.email_verified:
            firebase_auth.update_user(uid, email_verified=True)
            logger.info("Marked firebase user as verified: uid=%s", uid)
        
        # Ensure account record exists in database
        account_exists = Gamer.objects.filter(uid=uid).exists() or ShopOwner.objects.filter(uid=uid).exists()
        
        if not account_exists:
            # Recovery/Provisioning flow
            pending = None
            try:
                pending = PendingRegistration.objects.get(uid=uid)
            except PendingRegistration.DoesNotExist:
                if firebase_user.email:
                    try:
                        pending = PendingRegistration.objects.get(email=firebase_user.email)
                    except PendingRegistration.DoesNotExist:
                        pending = None
            
            if pending:
                logger.info("verify_email: Provisioning missing account for verified user uid=%s", uid)
                provision_account_from_pending(pending)
            else:
                # If neither account nor pending exists, check if Account base exists
                if not Account.objects.filter(uid=uid).exists():
                    logger.warning("verify_email: No pending or account found for uid=%s", uid)
                    messages.error(request, 'Verification record not found. Please register again.')
                    return redirect('accounts:select_role')
        
        messages.success(request, 'Email verified successfully. Please login to continue')
        return redirect('accounts:login')

    except Exception as e:
        logger.error(f"Email verification error for uid={uid}: {e}", exc_info=True)
        messages.error(request, 'Email verification failed. Please try again.')
        return redirect('accounts:login')


@csrf_exempt
def resend_verification(request):
    if request.method == 'POST':
        try:
            email = request.POST.get('email')
            
            # Prefer PendingRegistration
            try:
                pending = PendingRegistration.objects.get(email=email)
                uid = pending.uid
                role = pending.role
                # Ensure Firebase user exists
                firebase_user = firebase_auth.get_user(uid)
                if firebase_user.email_verified:
                    return JsonResponse({'success': False, 'message': 'Email already verified'})
                send_verification_email(email, uid, role)
            except PendingRegistration.DoesNotExist:
                # Fallback: Account exists but not verified
                try:
                    # Check both Gamer and ShopOwner
                    try:
                        account = Gamer.objects.get(email=email)
                    except Gamer.DoesNotExist:
                        account = ShopOwner.objects.get(email=email)
                    
                    firebase_user = firebase_auth.get_user_by_email(email)
                    if firebase_user.email_verified:
                        return JsonResponse({'success': False, 'message': 'Email already verified'})
                    role = 'gamer' if hasattr(account, 'gamer') else 'shop_owner'
                    send_verification_email(email, firebase_user.uid, role)
                except (Gamer.DoesNotExist, ShopOwner.DoesNotExist):
                    # Try Firebase lookup
                    firebase_user = firebase_auth.get_user_by_email(email)
                    # Can't infer role, default to gamer
                    send_verification_email(email, firebase_user.uid, 'gamer')
            
            return JsonResponse({
                'success': True,
                'message': 'Verification email sent successfully'
            })
        
        except Exception as e:
            logger.error(f"Resend verification error: {e}")
            return JsonResponse({
                'success': False,
                'message': 'Failed to resend verification email'
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})


def logout_view(request):
    # Clear session
    request.session.flush()
    messages.success(request, 'Logged out successfully.')
    return redirect('core:home')


# PASSWORD & ACCOUNT MANAGEMENT
@csrf_exempt
def change_password(request):
    if request.method == 'POST':
        try:
            # Support both form-encoded and JSON bodies
            if request.headers.get('Content-Type', '').startswith('application/json'):
                try:
                    body = json.loads(request.body.decode('utf-8'))
                except Exception:
                    body = {}
                firebase_uid = body.get('firebase_uid')
                new_password = body.get('new_password')
            else:
                firebase_uid = request.POST.get('firebase_uid')
                new_password = request.POST.get('new_password')
            
            # Update password in Firebase
            firebase_auth.update_user(firebase_uid, password=new_password)
            
            # Send confirmation email
            # Find account by UID
            try:
                account = Gamer.objects.get(uid=firebase_uid)
            except Gamer.DoesNotExist:
                account = ShopOwner.objects.get(uid=firebase_uid)
            
            send_password_change_email(account.email)
            
            return JsonResponse({
                'success': True,
                'message': 'Password changed successfully'
            })
        
        except Exception as e:
            logger.error(f"Password change error: {e}")
            return JsonResponse({
                'success': False,
                'message': 'Failed to change password. Please try again.'
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})


@csrf_exempt
def delete_account(request):
    if request.method == 'POST':
        try:
            # Support both form-encoded and JSON bodies
            if request.headers.get('Content-Type', '').startswith('application/json'):
                try:
                    body = json.loads(request.body.decode('utf-8'))
                except Exception:
                    body = {}
                firebase_uid = (body.get('firebase_uid') or '').strip()
                password = (body.get('password') or '').strip()
            else:
                firebase_uid = (request.POST.get('firebase_uid') or '').strip()
                password = (request.POST.get('password') or '').strip()
            
            role = request.session.get('role')
            user_id = request.session.get('user_id')
            
            if not role or not user_id:
                return JsonResponse({'success': False, 'message': 'Not authenticated'})
            
            # Resolve the account based on role and session id
            try:
                if role == 'gamer':
                    account = Gamer.objects.get(id=user_id)
                elif role == 'shop_owner':
                    account = ShopOwner.objects.get(id=user_id)
                else:
                    return JsonResponse({'success': False, 'message': 'Unknown role'})
            except (Gamer.DoesNotExist, ShopOwner.DoesNotExist):
                return JsonResponse({'success': False, 'message': 'Account not found'})
            
            user_email = account.email
            
            # Use Firebase UID from session or payload as best-effort
            firebase_uid_to_delete = request.session.get('firebase_uid') or firebase_uid or getattr(account, 'uid',
                                                                                                    None)
            
            if firebase_uid_to_delete:
                try:
                    firebase_auth.delete_user(firebase_uid_to_delete)
                except Exception as e:
                    # Log but do not block database-side deletion
                    logger.error(f"Error deleting Firebase user during account deletion: {e}")
            
            # Delete from database
            account.delete()
            
            # Clear session
            request.session.flush()
            
            # Send deletion notification email
            send_account_deletion_email(user_email)
            
            # Notify admin
            notify_admin_account_deletion(user_email)
            
            return JsonResponse({
                'success': True,
                'message': 'Account permanently deleted',
                'redirect_url': '/accounts/login/'
            })
        
        except Exception as e:
            logger.error(f"Account deletion error: {e}")
            return JsonResponse({
                'success': False,
                'message': 'Failed to delete account. Please try again.'
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})


def notify_admin_account_deletion(email):
    try:
        subject = f"Account Deletion Notification - {settings.PROJECT_NAME}"
        
        message = f"""
        Admin Notification:

        User account has been deleted:
        - Email: {email}
        - Time: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}

        This is an automated notification.
        """
        
        # Send to admin email (configure this in settings)
        admin_email = getattr(settings, 'ADMIN_EMAIL', settings.DEFAULT_FROM_EMAIL)
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [admin_email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        logger.error(f"Error sending admin notification: {e}")
        return False


# Test view to verify Firebase integration
def test_firebase(request):
    try:
        # Test Firebase Admin SDK
        users = firebase_auth.list_users(max_results=5)
        user_count = len(users.users)
        
        return JsonResponse({
            'status': 'success',
            'message': 'Firebase integration working',
            'user_count': user_count
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })