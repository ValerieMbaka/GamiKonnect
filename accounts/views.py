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


# GAMER VIEWS
def gamer_dashboard(request):
    # Check if the user is a a gamer and is logged in
    if request.session.get('role') != 'gamer':
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    try:
        gamer = Gamer.objects.get(id=request.session['user_id'])
        
        # Check if they have been upgraded to shop owner recently
        try:
            from shops.models import Shop
            shop_owner = ShopOwner.objects.filter(uid=gamer.uid).first()
            if shop_owner:
                # If they have the role, go to Shop Owner Dashboard by default
                # Use a 'gamer_mode' session flag to allow Shop Owners to stay.
                if not request.session.get('gamer_mode'):
                    request.session['role'] = 'shop_owner'
                    request.session['user_id'] = shop_owner.id
                    return redirect('accounts:shop_owner_dashboard')
        except Exception as e:
            logger.error(f"Error checking for shop owner upgrade: {e}")
            pass

        # Check profile completion
        profile_complete = gamer.profile_completed
        if not profile_complete:
            messages.info(request, 'Please complete your profile to access full dashboard features')
        
        # Determine if gamer has pending or approved shops
        from shops.models import Shop
        has_pending_or_approved_shops = Shop.objects.filter(submitted_by_uid=gamer.uid).exists()

        context = {
            **base_site_context(),
            'gamer': gamer,
            'profile_complete': profile_complete,
            'gamer_stats': {
                'join_date': gamer.date_joined.strftime('%b %Y'),
                'games_count': gamer.games.count(),
            },
            'has_owner_access': has_pending_or_approved_shops,
        }
        return render(request, 'accounts/gamers/gamer_dashboard.html', context)
    
    except Gamer.DoesNotExist:
        messages.error(request, 'Gamer profile not found.')
        return redirect('core:home')


@csrf_exempt
def gamer_profile_completion(request):
    if request.session.get('role') != 'gamer':
        return JsonResponse({'success': False, 'message': 'Access denied'})
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                gamer = Gamer.objects.get(id=request.session['user_id'])
                
                # Handle profile picture
                if 'profile_picture' in request.FILES:
                    gamer.profile_picture = request.FILES['profile_picture']
                
                # Update basic info
                gamer.custom_username = request.POST.get('custom_username')
                gamer.bio = request.POST.get('bio')
                gamer.about = request.POST.get('about', '')
                gamer.location = request.POST.get('location')
                
                # Support JSON body or form-encoded
                raw_body = None
                if request.headers.get('Content-Type', '').startswith('application/json'):
                    try:
                        raw_body = json.loads(request.body.decode('utf-8'))
                    except Exception:
                        raw_body = {}
                    get_val = lambda k, default=None: raw_body.get(k, default)
                else:
                    get_val = lambda k, default=None: request.POST.get(k, default)
                
                errors = {}
                
                # Username validation
                username = get_val('custom_username') or get_val('username') or ''
                username = username.strip()
                if not username:
                    errors['custom_username'] = 'Username is required'
                else:
                    if not re.match(r'^[A-Za-z0-9_]{3,15}$', username):
                        errors['custom_username'] = 'Username must be 3-15 chars (letters, numbers, underscores)'
                    else:
                        # Case-insensitive uniqueness
                        exists = Gamer.objects.filter(custom_username__iexact=username).exclude(pk=gamer.pk).exists()
                        if exists:
                            errors['custom_username'] = 'Username already taken'
                
                # Bio validation
                bio = get_val('bio') or ''
                bio = bio.strip()
                if not bio:
                    errors['bio'] = 'Bio is required'
                elif len(bio) < 5 or len(bio) > 30:
                    errors['bio'] = 'Bio must be 5-30 characters'
                
                # About validation
                about = get_val('about') or ''
                if about:
                    about = about.strip()
                    if len(about) < 5 or len(about) > 200:
                        errors['about'] = 'About must be 5-200 characters when provided'
                
                # Location
                location = get_val('location') or ''
                location = location.strip()
                if not location:
                    errors['location'] = 'Location is required'
                
                # Date of birth
                dob_year = get_val('dob_year')
                dob_month = get_val('dob_month')
                dob_day = get_val('dob_day')
                dob_iso = get_val('date_of_birth')
                date_of_birth = None
                try:
                    if dob_year and dob_month and dob_day:
                        date_of_birth = datetime.date(int(dob_year), int(dob_month), int(dob_day))
                    elif dob_iso:
                        date_of_birth = datetime.date.fromisoformat(dob_iso)
                    else:
                        errors['date_of_birth'] = 'Date of birth is required'
                except Exception:
                    errors['date_of_birth'] = 'Invalid date of birth'
                
                # Platforms JSON list
                platforms_raw = get_val('platforms', '[]') or '[]'
                try:
                    platforms_list = platforms_raw if isinstance(platforms_raw, list) else json.loads(platforms_raw)
                except Exception:
                    platforms_list = []
                if not platforms_list:
                    errors['platforms'] = 'Select at least one platform'
                
                # Games
                games_raw = get_val('games', '[]') or '[]'
                try:
                    games_list = games_raw if isinstance(games_raw, list) else json.loads(games_raw)
                except Exception:
                    games_list = []
                if not games_list:
                    errors['games'] = 'Select or enter at least one game'
                
                # If validation failed, return errors
                if errors:
                    return JsonResponse({'success': False, 'message': 'Validation errors', 'errors': errors})
                
                # Apply validated fields
                gamer.custom_username = username
                gamer.bio = bio
                gamer.about = about or ''
                gamer.location = location
                if date_of_birth:
                    gamer.date_of_birth = date_of_birth
                gamer.platforms = platforms_list
                
                # Resolve games - only attach existing Game objects.
                # For unknown names, create GameSuggestion records so they can be approved later.
                attached_games = []
                pending_custom_names = []
                for entry in games_list:
                    game_obj = None
                    # Accept UUID string IDs for existing games
                    if isinstance(entry, str) and len(entry) > 20 and '-' in entry:
                        try:
                            game_obj = Game.objects.get(id=entry)
                        except Game.DoesNotExist:
                            game_obj = None
                    # Accept ints as legacy ids (no-op if not found)
                    if not game_obj and (isinstance(entry, int) or (isinstance(entry, str) and entry.isdigit())):
                        try:
                            game_obj = Game.objects.get(id=int(entry))
                        except (Game.DoesNotExist, ValueError):
                            game_obj = None
                    # Accept names
                    if not game_obj and isinstance(entry, str):
                        name = entry.strip()
                        if not name:
                            continue
                        existing = Game.objects.filter(name__iexact=name).first()
                        if existing:
                            game_obj = existing
                            
                    if game_obj:
                        attached_games.append(game_obj)
                if attached_games:
                    gamer.games.set(attached_games)
                
                gamer.profile_completed = True
                gamer.save()
                
            
                send_profile_completion_email(gamer.email, gamer.custom_username)
                
                profile_picture_url = gamer.profile_picture.url if gamer.profile_picture else '/static/core/images/player.jpeg'
                return JsonResponse({
                    'success': True,
                    'message': 'Profile completed successfully!',
                    'profile_picture_url': profile_picture_url,
                    'custom_username': gamer.custom_username or '',
                    'username': gamer.custom_username or '',
                    'bio': gamer.bio or '',
                    'about': gamer.about or '',
                    'location': gamer.location or '',
                    'platforms': gamer.platforms or [],
                    # Include pending custom names
                    'games': [g.name for g in gamer.games.all()] + pending_custom_names,
                    'date_of_birth': gamer.date_of_birth.isoformat() if gamer.date_of_birth else None
                })
        except Exception as e:
            logger.error(f"Gamer profile completion error: {e}")
            return JsonResponse({'success': False, 'message': 'Failed to complete profile. Please try again.'})
    # Non-POST request
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


@csrf_exempt
def check_username(request):
    # AJAX endpoint to validate gamer custom_username availability and format
    username = (request.GET.get('username') or '').strip()
    pattern = re.compile(r'^[A-Za-z0-9_]{3,15}$')
    
    # Rate limiting - 20 checks per rolling minute per IP
    ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() or request.META.get(
        'REMOTE_ADDR') or 'unknown'
    cache_key = f"check_username_rl:{ip}"
    data = cache.get(cache_key)
    now_ts = timezone.now().timestamp()
    window_seconds = 60
    limit = 20
    if not data:
        data = {'count': 0, 'reset': now_ts + window_seconds}
    # Reset if window passed
    if now_ts > data['reset']:
        data = {'count': 0, 'reset': now_ts + window_seconds}
    if data['count'] >= limit:
        retry_after = int(data['reset'] - now_ts)
        resp = JsonResponse({'available': False, 'reason': 'rate_limited', 'retry_after': retry_after})
        resp.status_code = 429
        resp['X-RateLimit-Limit'] = str(limit)
        resp['X-RateLimit-Remaining'] = '0'
        resp['X-RateLimit-Reset'] = str(int(data['reset']))
        return resp
    # Increment and persist
    data['count'] += 1
    cache.set(cache_key, data, timeout=window_seconds)
    
    if not pattern.match(username):
        resp = JsonResponse({'available': False, 'reason': 'invalid_format'})
        resp['X-RateLimit-Limit'] = str(limit)
        resp['X-RateLimit-Remaining'] = str(limit - data['count'])
        resp['X-RateLimit-Reset'] = str(int(data['reset']))
        return resp
    exists = Gamer.objects.filter(custom_username__iexact=username).exists()
    resp = JsonResponse({'available': not exists, 'reason': 'taken' if exists else 'ok'})
    resp['X-RateLimit-Limit'] = str(limit)
    resp['X-RateLimit-Remaining'] = str(limit - data['count'])
    resp['X-RateLimit-Reset'] = str(int(data['reset']))
    return resp


def gamer_profile_edit(request):
    if request.session.get('role') != 'gamer':
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    gamer = get_object_or_404(Gamer, id=request.session['user_id'])
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Handle profile picture
                if 'profile_picture' in request.FILES:
                    gamer.profile_picture = request.FILES['profile_picture']
                errors = {}
                username = request.POST.get('custom_username', '').strip()
                if not username:
                    errors['custom_username'] = 'Username is required'
                elif not re.match(r'^[A-Za-z0-9_]{3,15}$', username):
                    errors['custom_username'] = 'Username must be 3-15 chars (letters, numbers, underscores)'
                else:
                    exists = Gamer.objects.filter(custom_username__iexact=username).exclude(pk=gamer.pk).exists()
                    if exists:
                        errors['custom_username'] = 'Username already taken'
                
                bio = request.POST.get('bio', '').strip()
                if not bio:
                    errors['bio'] = 'Bio is required'
                elif len(bio) < 5 or len(bio) > 30:
                    errors['bio'] = 'Bio must be 5-30 characters'
                
                about = request.POST.get('about', '').strip()
                if about and (len(about) < 5 or len(about) > 200):
                    errors['about'] = 'About must be 5-200 characters when provided'
                
                location = request.POST.get('location', '').strip()
                if not location:
                    errors['location'] = 'Location is required'
                
                raw_platforms = request.POST.get('platforms', '').strip()
                platforms = []
                if raw_platforms:
                    try:
                        # Expect JSON list from the edit JS
                        parsed = json.loads(raw_platforms)
                        if isinstance(parsed, list):
                            # Coerce everything to simple strings
                            platforms = [str(p).strip() for p in parsed if str(p).strip()]
                    except (TypeError, ValueError, json.JSONDecodeError):
                        # Fallback: treat as comma-separated string
                        platforms = [p.strip() for p in raw_platforms.split(',') if p.strip()]
                
                if not platforms:
                    errors['platforms'] = 'Select at least one platform'
                
                games_data = request.POST.get('games', '').strip()
                games_entries = []
                if games_data:
                    # Could be comma separated ids or names
                    for token in [t.strip() for t in games_data.split(',') if t.strip()]:
                        games_entries.append(token)
                if not games_entries:
                    errors['games'] = 'Select or enter at least one game'
                
                if errors:
                    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                        return JsonResponse({'success': False, 'message': 'Validation errors', 'errors': errors})
                    for k, v in errors.items():
                        messages.error(request, v)
                    return redirect('accounts:gamer_profile_edit')
                
                # Track previous games and platforms
                prev_games = set(gamer.games.values_list('id', flat=True))
                prev_platforms = set(gamer.platforms or [])
                
                gamer.custom_username = username
                gamer.bio = bio
                gamer.about = about or ''
                gamer.location = location
                gamer.platforms = platforms
                
                # Resolve games - only attach existing Game objects.
                attached_games = []
                pending_custom_names = []
                for entry in games_entries:
                    game_obj = None
                    token = entry
                    # Accept UUIDs
                    if isinstance(token, str) and '-' in token and len(token) > 20:
                        try:
                            game_obj = Game.objects.get(id=token)
                        except Game.DoesNotExist:
                            game_obj = None
                    # Accept numeric ids
                    if not game_obj and token.isdigit():
                        try:
                            game_obj = Game.objects.get(id=int(token))
                        except (Game.DoesNotExist, ValueError):
                            game_obj = None
                    # Accept names
                    if not game_obj:
                        name = token.strip()
                        if not name:
                            continue
                        existing = Game.objects.filter(name__iexact=name).first()
                        if existing:
                            game_obj = existing
                        
                    if game_obj:
                        attached_games.append(game_obj)
                if attached_games:
                    gamer.games.set(attached_games)
                
                gamer.save()
                
                
                # AJAX / fetch-based submission support
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    profile_picture_url = gamer.profile_picture.url if gamer.profile_picture else '/static/core/images/player.jpeg'
                    return JsonResponse({
                        'success': True,
                        'message': 'Profile updated successfully!',
                        'user': {
                            'profile_picture_url': profile_picture_url,
                            'custom_username': gamer.custom_username or '',
                            'bio': gamer.bio or '',
                            'about': gamer.about or '',
                            'location': gamer.location or '',
                            'platforms': gamer.platforms or [],
                            # Include pending custom names
                            'games': [g.name for g in gamer.games.all()] + pending_custom_names,
                        },
                        'user_stats': {
                            'games_count': gamer.games.count(),
                            'platforms_count': len(gamer.platforms or []),
                        }
                    })
                
                messages.success(request, 'Profile updated successfully!')
                return redirect('accounts:gamer_settings')
        
        except Exception as e:
            logger.error(f"Profile edit error: {e}")
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': 'Failed to update profile. Please try again.'})
            messages.error(request, 'Failed to update profile. Please try again.')
    
    context = {
        **base_site_context(),
        'gamer': gamer
    }
    return render(request, 'accounts/gamers/gamer_profile_edit.html', context)


def gamer_settings(request):
    if request.session.get('role') != 'gamer':
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    gamer = get_object_or_404(Gamer, id=request.session['user_id'])
    context = {
        **base_site_context(),
        'gamer': gamer
    }
    return render(request, 'accounts/gamers/gamer_settings.html', context)


def gamer_public_profile(request, username=None):
    if request.session.get('role') != 'gamer':
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    if username:
        gamer = get_object_or_404(Gamer, custom_username=username)
    else:
        gamer = get_object_or_404(Gamer, id=request.session['user_id'])
    
    context = {
        **base_site_context(),
        'gamer': gamer
    }
    return render(request, 'accounts/gamers/gamer_public_profile.html', context)


def gamer_games(request):
    if request.session.get('role') != 'gamer':
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    gamer = get_object_or_404(Gamer, id=request.session['user_id'])
    
    # Prepare richer context for the gamer games page
    gamer_games_qs = gamer.games.filter(is_active=True).prefetch_related('genres')
    
    # Platforms saved on the gamer's profile completion
    profile_platforms = gamer.platforms or []
    gamer_platforms = sorted({p for p in profile_platforms if p})
    
    # Distinct genres across the gamer games
    from games.models import Genre  # local import to avoid circulars at module load
    gamer_genres = (
        Genre.objects.filter(games__in=gamer_games_qs)
        .distinct()
        .order_by('name')
    )
    
    context = {
        **base_site_context(),
        'gamer': gamer,
        'gamer_games': gamer_games_qs,
        'gamer_platforms': gamer_platforms,
        'gamer_genres': gamer_genres,
    }
    return render(request, 'accounts/gamers/gamer_games.html', context)


# SHOP OWNER VIEWS
def shop_owner_dashboard(request):
    # If entering owner dashboard, clear gamer_mode flag
    if 'gamer_mode' in request.session:
        del request.session['gamer_mode']
    
    role = request.session.get('role')
    # If true owner i.e at least 1 approved shop, render full dashboard
    if role == 'shop_owner':
        try:
            shop_owner = ShopOwner.objects.get(id=request.session['user_id'])
            # Ensure session role is set correctly
            request.session['role'] = 'shop_owner'
            request.session['user_id'] = shop_owner.id
            request.session.modified = True
            
            shops = (
                Shop.objects.filter(owners=shop_owner)
                .prefetch_related('games_available', 'consoles', 'game_prices__game')
                .order_by('-created_at')
            )
            has_shops = shops.exists()
            verified_shops = shops.filter(is_active=True)
            pending_shops = shops.filter(is_active=False)
            shop_stats = {
                'total_screens': sum(shop.total_consoles() for shop in shops),
                'total_games': sum(shop.games_available.count() for shop in shops),
                'premium_games': sum(shop.premium_games_count() for shop in shops),
                'pending_shops': pending_shops.count(),
            }
            recent_activity = []
            for shop in shops[:4]:
                recent_activity.append({
                    'title': f"{shop.name} registration",
                    'status': 'Live' if shop.is_active else 'Awaiting approval',
                    'timestamp': shop.created_at.strftime('%b %d, %Y'),
                    'meta': f"{shop.games_available.count()} games · {shop.total_consoles()} screens",
                    'is_active': shop.is_active,
                })
            verification_percent = 0
            if shops.count() > 0:
                verification_percent = round((verified_shops.count() / shops.count()) * 100)
            
            # Fetch actual pending counts
            pending_total = pending_shops.count()
            
            context = {
                **base_site_context(),
                'shop_owner': shop_owner,
                'shops': shops,
                'has_shops': has_shops,
                'shops_verified': verified_shops.exists(),
                'shop_count': shops.count(),
                'verified_shop_count': verified_shops.count(),
                'pending_shop_count': pending_total,
                'shop_stats': shop_stats,
                'recent_activity': recent_activity,
                'verification_percent': verification_percent,
                'inactive_mode': False,
            }
            return render(request, 'accounts/shop_owners/shop_owner_dashboard.html', context)
        except ShopOwner.DoesNotExist:
            messages.error(request, 'Shop owner profile not found.')
            return redirect('core:home')

    # Allow gamers with pending shops to view an inactive dashboard
    if role == 'gamer':
        try:
            gamer = Gamer.objects.get(id=request.session['user_id'])
            # Check if they actually have a ShopOwner record now (i.e just approved)
            try:
                shop_owner = ShopOwner.objects.filter(uid=gamer.uid).first()
                if shop_owner and Shop.objects.filter(owners=shop_owner, is_active=True).exists():
                    request.session['role'] = 'shop_owner'
                    request.session['user_id'] = shop_owner.id
                    return redirect('accounts:shop_owner_dashboard')
            except Exception:
                pass
            
            pending_shops = Shop.objects.filter(submitted_by_uid=gamer.uid).order_by('-created_at')
            if not pending_shops.exists():
                messages.error(request, 'Access denied.')
                return redirect('core:home')
            # Inactive mode
            shops = pending_shops
            verified_shops = shops.filter(is_active=True)
            shop_stats = {
                'total_screens': sum(shop.total_consoles() for shop in shops),
                'total_games': sum(shop.games_available.count() for shop in shops),
                'premium_games': sum(shop.premium_games_count() for shop in shops),
                'pending_shops': shops.count(),
            }
            recent_activity = []
            for shop in shops[:4]:
                recent_activity.append({
                    'title': f"{shop.name} status update",
                    'status': 'Awaiting approval',
                    'timestamp': shop.updated_at.strftime('%b %d, %Y'),
                    'meta': f"{shop.games_available.count()} games · {shop.total_consoles()} consoles",
                    'is_active': False,
                })
            verification_percent = 0
            context = {
                **base_site_context(),
                # Provide gamer info to template via expected variables
                'shop_owner': gamer,  # use gamer names where template reads shop_owner
                'shop_owner_avatar': getattr(gamer, 'profile_picture', None),
                'shops': shops,
                'has_shops': shops.exists(),
                'shops_verified': verified_shops.exists(),
                'shop_count': shops.count(),
                'verified_shop_count': verified_shops.count(),
                'pending_shop_count': shops.count(),
                'shop_stats': shop_stats,
                'recent_activity': recent_activity,
                'verification_percent': verification_percent,
                'inactive_mode': True,
            }
            return render(request, 'accounts/shop_owners/shop_owner_dashboard.html', context)
        except Gamer.DoesNotExist:
            messages.error(request, 'Access denied.')
            return redirect('core:home')

    messages.error(request, 'Access denied.')
    return redirect('core:home')


def shop_owner_profile(request):
    if request.session.get('role') != 'shop_owner':
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    shop_owner = get_object_or_404(ShopOwner, id=request.session['user_id'])
    shops = Shop.objects.filter(owners=shop_owner)
    
    context = {
        **base_site_context(),
        'shop_owner': shop_owner,
        'shops': shops,
        'shop_metrics': {
            'total_shops': shops.count(),
            'verified_shops': shops.filter(is_active=True).count(),
            'total_games': sum(shop.games_available.count() for shop in shops),
            'total_consoles': sum(shop.total_consoles() for shop in shops),
        }
    }
    return render(request, 'accounts/shop_owners/shop_owner_profile.html', context)


def shop_owner_profile_edit(request):
    if request.session.get('role') != 'shop_owner':
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    shop_owner = get_object_or_404(ShopOwner, id=request.session['user_id'])
    
    if request.method == 'POST':
        try:
            shop_owner.first_name = request.POST.get('first_name')
            shop_owner.last_name = request.POST.get('last_name')
            
            # Handle profile picture
            if 'profile_picture' in request.FILES:
                shop_owner.profile_picture = request.FILES['profile_picture']
            
            shop_owner.save()
            
            # Update session data
            request.session['first_name'] = shop_owner.first_name
            request.session['last_name'] = shop_owner.last_name
            
            messages.success(request, 'Profile updated successfully!')
            return redirect('accounts:shop_owner_profile')
        
        except Exception as e:
            logger.error(f"Shop owner profile edit error: {e}")
            messages.error(request, 'Failed to update profile. Please try again.')
    
    context = {
        **base_site_context(),
        'shop_owner': shop_owner,
    }
    return render(request, 'accounts/shop_owners/shop_owner_profile_edit.html', context)


def shop_owner_shop_detail(request, pk):
    if request.session.get('role') != 'shop_owner':
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    shop_owner = get_object_or_404(ShopOwner, id=request.session['user_id'])
    shop = get_object_or_404(
        Shop.objects.prefetch_related('games_available', 'consoles', 'game_prices__game', 'owners'),
        pk=pk,
        owners=shop_owner
    )
    
    pricing = shop.game_prices.select_related('game')
    context = {
        **base_site_context(),
        'shop_owner': shop_owner,
        'shop': shop,
        'consoles': shop.consoles.all(),
        'pricing': pricing,
        'games': shop.games_available.all(),
        'metrics': {
            'total_games': shop.games_available.count(),
            'premium_games': shop.premium_games_count(),
            'total_screens': shop.total_consoles(),
            'custom_prices': pricing.count(),
        }
    }
    return render(request, 'accounts/shop_owners/shop_owner_shop_detail.html', context)


def shop_owner_settings(request):
    if request.session.get('role') != 'shop_owner':
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    shop_owner = get_object_or_404(ShopOwner, id=request.session['user_id'])
    shops = Shop.objects.filter(owners=shop_owner)
    
    context = {
        **base_site_context(),
        'shop_owner': shop_owner,
        'shops': shops,
        'security_state': {
            'multi_factor': False,
            'last_password_change': shop_owner.updated_at.strftime('%b %d, %Y'),
            'active_sessions': 3
        }
    }
    return render(request, 'accounts/shop_owners/shop_owner_settings.html', context)


@csrf_exempt
def create_shop(request):
    role = request.session.get('role')
    if role not in ['gamer', 'shop_owner']:
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    # Fetch the appropriate account object for context
    account_obj = None
    if role == 'shop_owner':
        account_obj = get_object_or_404(ShopOwner, id=request.session['user_id'])
    else:
        # Gamer submitting intent to become shop owner
        account_obj = get_object_or_404(Gamer, id=request.session['user_id'])
    
    if request.method == 'POST':
        # Server-side validation
        shop_name = request.POST.get('shop_name')
        description = request.POST.get('description')
        city = request.POST.get('city')
        building = request.POST.get('building')
        floor = request.POST.get('floor')
        room_number = request.POST.get('room_number')
        shop_location = request.POST.get('shop_location')
        screen_number = request.POST.get('screen_number')
        base_price_per_hour = request.POST.get('base_price_per_hour')
        opening_hours = request.POST.get('opening_hours')
        closing_hours = request.POST.get('closing_hours')
        logo = request.FILES.get('logo')
        business_permit = request.FILES.get('business_permit')
        
        console_types = request.POST.getlist('console_types')
        games_available_data = request.POST.get('games_available', '[]')
        
        # Basic field validation
        if not all([shop_name, description, city, building, floor, room_number,
                    shop_location, screen_number, base_price_per_hour,
                    opening_hours, closing_hours, logo, business_permit]):
            messages.error(request, 'Please fill in all compulsory fields and upload both logo and business permit.')
            return render(request, 'accounts/shop_owners/create_shop.html', {
                **base_site_context(),
                'consoles_platforms': Platform.objects.filter(category__name='Console')
            })

        # At least one console must be selected
        if not console_types:
            messages.error(request, 'Please select at least one console type.')
            return render(request, 'accounts/shop_owners/create_shop.html', {
                **base_site_context(),
                'consoles_platforms': Platform.objects.filter(category__name='Console')
            })
            
        # At least one game must be selected
        try:
            if not json.loads(games_available_data):
                messages.error(request, 'Please select at least one game.')
                return render(request, 'accounts/shop_owners/create_shop.html', {
                    **base_site_context(),
                    'consoles_platforms': Platform.objects.filter(category__name='Console')
                })
        except:
            messages.error(request, 'Invalid game data provided.')
            return render(request, 'accounts/shop_owners/create_shop.html', {
                **base_site_context(),
                'consoles_platforms': Platform.objects.filter(category__name='Console')
            })

        try:
            with transaction.atomic():
                # Create shop
                shop = Shop.objects.create(
                    name=shop_name,
                    logo=logo,
                    description=description,
                    city=city,
                    building=building,
                    floor=floor,
                    room_number=room_number,
                    location=shop_location,
                    address=shop_location,
                    screen_number=int(screen_number),
                    base_price_per_hour=float(base_price_per_hour),
                    opening_hours=opening_hours,
                    closing_hours=closing_hours,
                    business_permit=business_permit,
                    is_active=False  # Wait for admin approval
                )
                
                # Track submitter for admin approval flow
                shop.submitted_by_uid = account_obj.uid
                shop.submitted_by_email = account_obj.email
                shop.save(update_fields=['submitted_by_uid', 'submitted_by_email'])

                if role == 'shop_owner':
                    # Add shop owner as owner
                    shop.owners.add(account_obj)
                
                # Handle consoles
                console_types = request.POST.getlist('console_types')
                for c_slug in console_types:
                    try:
                        platform = get_platform_by_string(c_slug)
                        if not platform:
                            continue
                        
                        quantity = int(request.POST.get(f'console_quantity_{c_slug}', 1))
                        
                        Console.objects.create(
                            shop=shop,
                            console_type=platform,
                            quantity=quantity
                        )
                    except Exception as ce:
                        logger.error(f"Error creating console: {ce}")
                        continue
                
                # Handle games available
                games_available_data = request.POST.get('games_available', '[]')
                games_to_add = []
                if games_available_data:
                    try:
                        game_identifiers = json.loads(games_available_data)
                        for identifier in game_identifiers:
                            # Try to find by ID first
                            game = Game.objects.filter(models.Q(id=identifier) if is_valid_uuid(identifier) else models.Q(integer_id=identifier) if str(identifier).isdigit() else models.Q(pk=None)).first()
                            
                            if game:
                                games_to_add.append(game)
                            else:
                                # Treat as a custom game name if it's a string
                                if isinstance(identifier, str) and identifier.strip():
                                    name = identifier.strip()
                                    # Create or get custom game
                                    custom_game, created = Game.objects.get_or_create(
                                        name__iexact=name,
                                        defaults={'name': name, 'is_verified': False, 'is_active': True}
                                    )
                                    games_to_add.append(custom_game)
                    except (json.JSONDecodeError, TypeError, ValidationError) as e:
                        logger.error(f"Error parsing games_available in create_shop: {e} | data: {games_available_data}")
                
                # Handle new custom games
                new_games_payload = request.POST.get('new_games', '[]')
                if new_games_payload:
                    custom_games = json.loads(new_games_payload)
                    for custom in custom_games:
                        name = custom.get('name', '').strip()
                        platforms = custom.get('platforms', [])
                        if not name or not platforms:
                            continue
                        existing_game = Game.objects.filter(name__iexact=name, is_verified=False).first()
                        if existing_game:
                            games_to_add.append(existing_game)
                            continue
                        
                        game = Game.objects.create(
                            name=name,
                            is_verified=False,
                            is_active=True
                        )
                        
                        # Resolve platform objects from names/slugs
                        if platforms:
                            resolved_platforms = []
                            for p_str in platforms:
                                p_obj = get_platform_by_string(p_str)
                                if p_obj:
                                    resolved_platforms.append(p_obj)
                            if resolved_platforms:
                                game.supported_platforms.set(resolved_platforms)
                        
                        games_to_add.append(game)
                
                if games_to_add:
                    shop.games_available.set(games_to_add)
                
                # Notify admin about new shop submission
                notify_admin_new_shop(shop)
                
                # Handle game pricing
                pricing_data = request.POST.get('game_pricing', '[]')
                if pricing_data:
                    pricing_list = json.loads(pricing_data)
                    # Create a mapping of custom game indices to actual game objects
                    custom_games_map = {}
                    if new_games_payload:
                        custom_games_list = json.loads(new_games_payload)
                        for idx, custom in enumerate(custom_games_list):
                            name = custom.get('name', '').strip()
                            if name:
                                # Find the created game (either existing or newly created)
                                game = Game.objects.filter(name__iexact=name).first()
                                if game:
                                    custom_games_map[f'custom_{idx}'] = game
                    
                    for price_data in pricing_list:
                        game_id = price_data.get('game_id')
                        price = float(price_data.get('price_per_hour', 0))
                        is_premium = price_data.get('is_premium', False)
                        
                        # Handle custom game IDs
                        if game_id and game_id.startswith('custom_'):
                            game = custom_games_map.get(game_id)
                            if not game:
                                continue
                        else:
                            try:
                                game = Game.objects.get(id=game_id)
                            except (Game.DoesNotExist, ValueError):
                                continue
                        
                        if game:
                            GamePricing.objects.create(
                                shop=shop,
                                game=game,
                                price_per_hour=price,
                                is_premium=is_premium
                            )
                
                messages.success(
                    request,
                    'Registration in progress. Check your email for shop verification status'
                )
                
                # Redirect based on role - default to gamer dashboard
                return redirect('accounts:gamer_dashboard')
        
        except Exception as e:
            logger.error(f"Shop creation error: {e}")
            messages.error(request, 'Failed to create shop. Please try again.')
    
    # Get all games for the form
    games = Game.objects.filter(is_verified=True, is_active=True).order_by('name')
    consoles_platforms = Platform.objects.filter(category__name='Console').order_by('name')
    context = {
        **base_site_context(),
        'shop_owner': account_obj if role == 'shop_owner' else None,
        'gamer': account_obj if role == 'gamer' else None,
        'games': games,
        'consoles_platforms': consoles_platforms
    }
    return render(request, 'accounts/shop_owners/create_shop.html', context)


def edit_shop(request, pk):
    if request.session.get('role') != 'shop_owner':
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    shop_owner = get_object_or_404(ShopOwner, id=request.session['user_id'])
    shop = get_object_or_404(Shop.objects.prefetch_related('games_available', 'consoles', 'game_prices__game'), pk=pk,
                             owners=shop_owner)
    
    if request.method == 'POST':
        # Server-side validation
        shop_name = request.POST.get('shop_name')
        description = request.POST.get('description')
        city = request.POST.get('city')
        building = request.POST.get('building')
        floor = request.POST.get('floor')
        room_number = request.POST.get('room_number')
        shop_location = request.POST.get('shop_location')
        screen_number = request.POST.get('screen_number')
        base_price_per_hour = request.POST.get('base_price_per_hour')
        opening_hours = request.POST.get('opening_hours')
        closing_hours = request.POST.get('closing_hours')
        
        console_types = request.POST.getlist('console_types')
        games_available_data = request.POST.get('games_available', '[]')
        
        # Basic field validation
        if not all([shop_name, description, city, building, floor, room_number,
                    shop_location, screen_number, base_price_per_hour,
                    opening_hours, closing_hours]):
            messages.error(request, 'Please fill in all compulsory fields.')
            return redirect('accounts:edit_shop', pk=shop.pk)

        # At least one console must be selected
        if not console_types:
            messages.error(request, 'Please select at least one console type.')
            return redirect('accounts:edit_shop', pk=shop.pk)
            
        # At least one game must be selected
        try:
            if not json.loads(games_available_data):
                messages.error(request, 'Please select at least one game.')
                return redirect('accounts:edit_shop', pk=shop.pk)
        except:
            messages.error(request, 'Invalid game data provided.')
            return redirect('accounts:edit_shop', pk=shop.pk)

        try:
            with transaction.atomic():
                # Update shop basic info
                shop.name = shop_name
                if request.FILES.get('logo'):
                    shop.logo = request.FILES.get('logo')
                shop.description = description
                shop.city = city
                shop.building = building
                shop.floor = floor
                shop.room_number = room_number
                shop.location = shop_location
                shop.address = shop_location
                shop.screen_number = int(screen_number)
                shop.base_price_per_hour = float(base_price_per_hour)
                shop.opening_hours = opening_hours
                shop.closing_hours = closing_hours
                if request.FILES.get('business_permit'):
                    shop.business_permit = request.FILES.get('business_permit')
                shop.save()
                
                # Handle consoles - delete existing and recreate
                shop.consoles.all().delete()
                console_types = request.POST.getlist('console_types')
                for c_slug in console_types:
                    try:
                        platform = get_platform_by_string(c_slug)
                        if not platform:
                            continue
                        
                        quantity = int(request.POST.get(f'console_quantity_{c_slug}', 1))
                        
                        Console.objects.create(
                            shop=shop,
                            console_type=platform,
                            quantity=quantity
                        )
                    except Exception as ce:
                        logger.error(f"Error updating console: {ce}")
                        continue
                
                # Handle games available
                games_available_data = request.POST.get('games_available', '[]')
                games_to_add = []
                if games_available_data:
                    try:
                        game_identifiers = json.loads(games_available_data)
                        for identifier in game_identifiers:
                            game = Game.objects.filter(models.Q(id=identifier) if is_valid_uuid(identifier) else models.Q(integer_id=identifier) if str(identifier).isdigit() else models.Q(pk=None)).first()
                            if game:
                                games_to_add.append(game)
                            else:
                                if isinstance(identifier, str) and identifier.strip():
                                    name = identifier.strip()
                                    custom_game, created = Game.objects.get_or_create(
                                        name__iexact=name,
                                        defaults={'name': name, 'is_verified': False, 'is_active': True}
                                    )
                                    games_to_add.append(custom_game)
                    except (json.JSONDecodeError, TypeError, ValidationError) as e:
                        logger.error(f"Error parsing games_available in edit_shop: {e}")
                
                # Handle new custom games (legacy support)
                new_games_payload = request.POST.get('new_games', '[]')
                if new_games_payload:
                    custom_games = json.loads(new_games_payload)
                    for custom in custom_games:
                        name = custom.get('name', '').strip()
                        platforms = custom.get('platforms', [])
                        if not name or not platforms:
                            continue
                        existing_game = Game.objects.filter(name__iexact=name, is_verified=False).first()
                        if existing_game:
                            games_to_add.append(existing_game)
                            continue
                        
                        game = Game.objects.create(
                            name=name,
                            is_verified=False,
                            is_active=True
                        )
                        
                        # Resolve platform objects from names/slugs
                        if platforms:
                            resolved_platforms = []
                            for p_str in platforms:
                                p_obj = get_platform_by_string(p_str)
                                if p_obj:
                                    resolved_platforms.append(p_obj)
                            if resolved_platforms:
                                game.supported_platforms.set(resolved_platforms)
                        
                        games_to_add.append(game)
                
                if games_to_add:
                    shop.games_available.set(games_to_add)
                
                # Handle game pricing - delete existing and recreate
                shop.game_prices.all().delete()
                pricing_data = request.POST.get('game_pricing', '[]')
                if pricing_data:
                    pricing_list = json.loads(pricing_data)
                    custom_games_map = {}
                    if new_games_payload:
                        custom_games_list = json.loads(new_games_payload)
                        for idx, custom in enumerate(custom_games_list):
                            name = custom.get('name', '').strip()
                            if name:
                                game = Game.objects.filter(name__iexact=name).first()
                                if game:
                                    custom_games_map[f'custom_{idx}'] = game
                    
                    for price_data in pricing_list:
                        game_id = price_data.get('game_id')
                        price = float(price_data.get('price_per_hour', 0))
                        is_premium = price_data.get('is_premium', False)
                        
                        if game_id and game_id.startswith('custom_'):
                            game = custom_games_map.get(game_id)
                            if not game:
                                continue
                        else:
                            try:
                                game = Game.objects.get(id=game_id)
                            except (Game.DoesNotExist, ValueError):
                                continue
                        
                        if game:
                            GamePricing.objects.create(
                                shop=shop,
                                game=game,
                                price_per_hour=price,
                                is_premium=is_premium
                            )
                
                messages.success(request, 'Shop updated successfully!')
                return redirect('accounts:shop_owner_shop_detail', pk=shop.pk)
        
        except Exception as e:
            logger.error(f"Shop edit error: {e}")
            messages.error(request, 'Failed to update shop. Please try again.')
    
    # Get all games for the form
    games = Game.objects.filter(is_verified=True, is_active=True).order_by('name')
    consoles_platforms = Platform.objects.filter(category__name='Console').order_by('name')
    pricing = shop.game_prices.select_related('game')
    
    existing_consoles_objs = shop.consoles.all()
    existing_console_platform_ids = [c.console_type.id for c in existing_consoles_objs]
    existing_console_quantities = {c.console_type.slug: c.quantity for c in existing_consoles_objs}
    
    context = {
        **base_site_context(),
        'shop_owner': shop_owner,
        'shop': shop,
        'games': games,
        'consoles_platforms': consoles_platforms,
        'existing_console_platform_ids': existing_console_platform_ids,
        'existing_console_quantities': existing_console_quantities,
        'existing_games': list(shop.games_available.values_list('id', flat=True)),
        'existing_pricing': json.dumps(
            [{'game_id': str(p.game.id), 'price_per_hour': float(p.price_per_hour), 'is_premium': p.is_premium} for p in
             pricing])
    }
    return render(request, 'accounts/shop_owners/edit_shop.html', context)


def toggle_gamer_mode(request):
    # Toggle a shop owner into gamer dashboard mode
    try:
        # Check if they have a gamer record
        gamer = Gamer.objects.get(uid=request.session['firebase_uid'])
        request.session['role'] = 'gamer'
        request.session['user_id'] = gamer.id
        request.session['gamer_mode'] = True
        return redirect('accounts:gamer_dashboard')
    except Exception as e:
        logger.error(f"Error toggling to gamer mode: {e}")
        messages.error(request, "Failed to switch dashboards.")
        return redirect('accounts:shop_owner_dashboard')


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