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
from django.core.paginator import Paginator
from django.core.signing import TimestampSigner, SignatureExpired, BadSignature
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

# Core Email Manager
from core.email_service import EmailManager

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
                        shop_owner = ShopOwner.objects.filter(uid=pending.uid).first()
                        if not shop_owner:
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
    
    platform_str = platform_str.strip().upper()
    
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
    
    for candidate in candidates:
        platform = Platform.objects.filter(
            models.Q(name__iexact=candidate) |
            models.Q(slug__iexact=candidate.lower().replace(' ', '-').replace('_', '-'))
        ).first()
        if platform:
            return platform
    
    platform = Platform.objects.filter(
        models.Q(category__name__iexact=platform_str.replace('_', ' ')) |
        models.Q(category__slug__iexact=platform_str.lower().replace('_', '-'))
    ).first()
    
    return platform


# AUTHENTICATION VIEWS
def register_view(request):
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
            
            if role not in ['gamer', 'shop_owner']:
                return JsonResponse({'success': False, 'message': 'Invalid role'})
            
            if Account.objects.filter(email=email).exists():
                logger.warning("Registration blocked: Email %s already exists in Account table", email)
                return JsonResponse({'success': False, 'message': 'Email already registered'})
            
            pending = None
            try:
                pending = PendingRegistration.objects.get(uid=uid)
            except PendingRegistration.DoesNotExist:
                pending = None
            
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
            
            # Use EmailManager
            email_sent = EmailManager.send_verification(email, uid, role)
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
    request.session.pop('show_resend', None)
    context = base_site_context()
    return render(request, 'accounts/login.html', context)


@csrf_exempt
def session_login(request):
    if request.method == 'POST':
        try:
            id_token = request.POST.get('id_token')
            firebase_uid = request.POST.get('firebase_uid')
            
            try:
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
            
            account = None
            role = None
            user_obj = None
            
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
                        
                        logger.info("Provisioning account during login uid=%s", uid)
                        account = provision_account_from_pending(pending)
                        if account:
                            if isinstance(account, Gamer):
                                role = 'gamer'
                                user_obj = account
                            else:
                                role = 'shop_owner'
                                user_obj = account
                        else:
                            return JsonResponse({'success': False, 'message': 'Failed to create user record'})
                    else:
                        return JsonResponse({
                            'success': False,
                            'message': 'Account not found. Please create an account to proceed',
                            'redirect': reverse('accounts:register')
                        })
            
            firebase_user = firebase_auth.get_user(uid)
            if not firebase_user.email_verified:
                request.session['show_resend'] = account.email
                return JsonResponse({
                    'success': False,
                    'message': 'Please verify your account first to login'
                })
            
            request.session['user_id'] = account.id
            request.session['firebase_uid'] = uid
            request.session['email'] = account.email
            request.session['role'] = role
            request.session['first_name'] = account.first_name
            request.session['last_name'] = account.last_name
            
            try:
                shop_owner = ShopOwner.objects.get(uid=uid)
                request.session['user_id'] = shop_owner.id
                request.session['role'] = 'shop_owner'
                role = 'shop_owner'
                account = shop_owner
            except ShopOwner.DoesNotExist:
                pass
            
            request.session.set_expiry(86400)
            
            if not user_obj.last_login:
                # Use EmailManager
                EmailManager.send_welcome(account.email, role, account.first_name)
                user_obj.last_login = timezone.now()
                user_obj.save()
            
            next_url = request.session.pop('post_login_redirect', None)
            
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
        next_url = request.GET.get('next')
        if next_url:
            try:
                request.session['post_login_redirect'] = next_url
            except Exception:
                pass
        
        firebase_user = firebase_auth.get_user(uid)
        
        if not firebase_user.email_verified:
            firebase_auth.update_user(uid, email_verified=True)
            logger.info("Marked firebase user as verified: uid=%s", uid)
        
        account_exists = Gamer.objects.filter(uid=uid).exists() or ShopOwner.objects.filter(uid=uid).exists()
        
        if not account_exists:
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
            
            try:
                pending = PendingRegistration.objects.get(email=email)
                uid = pending.uid
                role = pending.role
                firebase_user = firebase_auth.get_user(uid)
                if firebase_user.email_verified:
                    return JsonResponse({'success': False, 'message': 'Email already verified'})
                
                # Use EmailManager
                EmailManager.send_verification(email, uid, role)
            
            except PendingRegistration.DoesNotExist:
                try:
                    try:
                        account = Gamer.objects.get(email=email)
                    except Gamer.DoesNotExist:
                        account = ShopOwner.objects.get(email=email)
                    
                    firebase_user = firebase_auth.get_user_by_email(email)
                    if firebase_user.email_verified:
                        return JsonResponse({'success': False, 'message': 'Email already verified'})
                    role = 'gamer' if hasattr(account, 'gamer') else 'shop_owner'
                    
                    # Use EmailManager
                    EmailManager.send_verification(email, firebase_user.uid, role)
                
                except (Gamer.DoesNotExist, ShopOwner.DoesNotExist):
                    firebase_user = firebase_auth.get_user_by_email(email)
                    EmailManager.send_verification(email, firebase_user.uid, 'gamer')
            
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
    request.session.flush()
    messages.success(request, 'Logged out successfully.')
    return redirect('core:home')


# PASSWORD & ACCOUNT MANAGEMENT
@csrf_exempt
def change_password(request):
    if request.method == 'POST':
        try:
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
            
            firebase_auth.update_user(firebase_uid, password=new_password)
            
            try:
                account = Gamer.objects.get(uid=firebase_uid)
            except Gamer.DoesNotExist:
                account = ShopOwner.objects.get(uid=firebase_uid)
            
            # Use EmailManager
            EmailManager.send_password_change(account.email, account.first_name)
            
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
            if request.headers.get('Content-Type', '').startswith('application/json'):
                try:
                    body = json.loads(request.body.decode('utf-8'))
                except Exception:
                    body = {}
                firebase_uid = (body.get('firebase_uid') or '').strip()
            else:
                firebase_uid = (request.POST.get('firebase_uid') or '').strip()
            
            role = request.session.get('role')
            user_id = request.session.get('user_id')
            
            if not role or not user_id:
                return JsonResponse({'success': False, 'message': 'Not authenticated'})
            
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
            
            firebase_uid_to_delete = request.session.get('firebase_uid') or firebase_uid or getattr(account, 'uid',
                                                                                                    None)
            
            if firebase_uid_to_delete:
                try:
                    firebase_auth.delete_user(firebase_uid_to_delete)
                except Exception as e:
                    logger.error(f"Error deleting Firebase user during account deletion: {e}")
            
            account.delete()
            request.session.flush()
            
            # Use EmailManager
            EmailManager.send_account_deletion(user_email)
            EmailManager.send_admin_account_deletion(user_email)
            
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


# GAMER VIEWS
def gamer_dashboard(request):
    if request.session.get('role') != 'gamer':
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    try:
        gamer = Gamer.objects.get(id=request.session['user_id'])
        
        try:
            from shops.models import Shop
            shop_owner = ShopOwner.objects.filter(uid=gamer.uid).first()
            if shop_owner:
                if not request.session.get('gamer_mode'):
                    request.session['role'] = 'shop_owner'
                    request.session['user_id'] = shop_owner.id
                    return redirect('accounts:shop_owner_dashboard')
        except Exception as e:
            logger.error(f"Error checking for shop owner upgrade: {e}")
            pass
        
        profile_complete = gamer.profile_completed
        if not profile_complete:
            messages.info(request, 'Please complete your profile to access full dashboard features')
        
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
                
                if 'profile_picture' in request.FILES:
                    gamer.profile_picture = request.FILES['profile_picture']
                
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
                
                username = get_val('custom_username') or get_val('username') or ''
                username = username.strip()
                if not username:
                    errors['custom_username'] = 'Username is required'
                else:
                    if not re.match(r'^[A-Za-z0-9_]{3,15}$', username):
                        errors['custom_username'] = 'Username must be 3-15 chars (letters, numbers, underscores)'
                    else:
                        exists = Gamer.objects.filter(custom_username__iexact=username).exclude(pk=gamer.pk).exists()
                        if exists:
                            errors['custom_username'] = 'Username already taken'
                
                bio = get_val('bio') or ''
                bio = bio.strip()
                if not bio:
                    errors['bio'] = 'Bio is required'
                elif len(bio) < 5 or len(bio) > 30:
                    errors['bio'] = 'Bio must be 5-30 characters'
                
                about = get_val('about') or ''
                if about:
                    about = about.strip()
                    if len(about) < 5 or len(about) > 200:
                        errors['about'] = 'About must be 5-200 characters when provided'
                
                location = get_val('location') or ''
                location = location.strip()
                if not location:
                    errors['location'] = 'Location is required'
                
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
                
                platforms_raw = get_val('platforms', '[]') or '[]'
                try:
                    platforms_list = platforms_raw if isinstance(platforms_raw, list) else json.loads(platforms_raw)
                except Exception:
                    platforms_list = []
                if not platforms_list:
                    errors['platforms'] = 'Select at least one platform'
                
                games_raw = get_val('games', '[]') or '[]'
                try:
                    games_list = games_raw if isinstance(games_raw, list) else json.loads(games_raw)
                except Exception:
                    games_list = []
                if not games_list:
                    errors['games'] = 'Select or enter at least one game'
                
                if errors:
                    return JsonResponse({'success': False, 'message': 'Validation errors', 'errors': errors})
                
                gamer.custom_username = username
                gamer.bio = bio
                gamer.about = about or ''
                gamer.location = location
                if date_of_birth:
                    gamer.date_of_birth = date_of_birth
                gamer.platforms = platforms_list
                
                attached_games = []
                pending_custom_names = []
                for entry in games_list:
                    game_obj = None
                    if isinstance(entry, str) and len(entry) > 20 and '-' in entry:
                        try:
                            game_obj = Game.objects.get(id=entry)
                        except Game.DoesNotExist:
                            game_obj = None
                    if not game_obj and (isinstance(entry, int) or (isinstance(entry, str) and entry.isdigit())):
                        try:
                            game_obj = Game.objects.get(id=int(entry))
                        except (Game.DoesNotExist, ValueError):
                            game_obj = None
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
                
                # Use EmailManager
                EmailManager.send_profile_completion(gamer.email, gamer.custom_username)
                
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
                    'games': [g.name for g in gamer.games.all()] + pending_custom_names,
                    'date_of_birth': gamer.date_of_birth.isoformat() if gamer.date_of_birth else None
                })
        except Exception as e:
            logger.error(f"Gamer profile completion error: {e}")
            return JsonResponse({'success': False, 'message': 'Failed to complete profile. Please try again.'})
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


@csrf_exempt
def check_username(request):
    username = (request.GET.get('username') or '').strip()
    pattern = re.compile(r'^[A-Za-z0-9_]{3,15}$')
    
    ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() or request.META.get(
        'REMOTE_ADDR') or 'unknown'
    cache_key = f"check_username_rl:{ip}"
    data = cache.get(cache_key)
    now_ts = timezone.now().timestamp()
    window_seconds = 60
    limit = 20
    if not data:
        data = {'count': 0, 'reset': now_ts + window_seconds}
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
                        parsed = json.loads(raw_platforms)
                        if isinstance(parsed, list):
                            platforms = [str(p).strip() for p in parsed if str(p).strip()]
                    except (TypeError, ValueError, json.JSONDecodeError):
                        platforms = [p.strip() for p in raw_platforms.split(',') if p.strip()]
                
                if not platforms:
                    errors['platforms'] = 'Select at least one platform'
                
                games_data = request.POST.get('games', '').strip()
                games_entries = []
                if games_data:
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
                
                gamer.custom_username = username
                gamer.bio = bio
                gamer.about = about or ''
                gamer.location = location
                gamer.platforms = platforms
                
                attached_games = []
                pending_custom_names = []
                for entry in games_entries:
                    game_obj = None
                    token = entry
                    if isinstance(token, str) and '-' in token and len(token) > 20:
                        try:
                            game_obj = Game.objects.get(id=token)
                        except Game.DoesNotExist:
                            game_obj = None
                    if not game_obj and token.isdigit():
                        try:
                            game_obj = Game.objects.get(id=int(token))
                        except (Game.DoesNotExist, ValueError):
                            game_obj = None
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
    gamer_games_qs = gamer.games.filter(is_active=True).prefetch_related('genres')
    profile_platforms = gamer.platforms or []
    gamer_platforms = sorted({p for p in profile_platforms if p})
    
    from games.models import Genre
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
    if 'gamer_mode' in request.session:
        del request.session['gamer_mode']
    
    role = request.session.get('role')
    if role == 'shop_owner':
        try:
            shop_owner = ShopOwner.objects.get(id=request.session['user_id'])
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
    
    if role == 'gamer':
        try:
            gamer = Gamer.objects.get(id=request.session['user_id'])
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
                'shop_owner': gamer,
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
            
            if 'profile_picture' in request.FILES:
                shop_owner.profile_picture = request.FILES['profile_picture']
            
            shop_owner.save()
            
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
    
    account_obj = None
    if role == 'shop_owner':
        account_obj = get_object_or_404(ShopOwner, id=request.session['user_id'])
    else:
        account_obj = get_object_or_404(Gamer, id=request.session['user_id'])
    
    if request.method == 'POST':
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
        
        if not all([shop_name, description, city, building, floor, room_number,
                    shop_location, screen_number, base_price_per_hour,
                    opening_hours, closing_hours, logo, business_permit]):
            messages.error(request, 'Please fill in all compulsory fields and upload both logo and business permit.')
            return render(request, 'accounts/shop_owners/create_shop.html', {
                **base_site_context(),
                'consoles_platforms': Platform.objects.filter(category__name='Console')
            })
        
        if not console_types:
            messages.error(request, 'Please select at least one console type.')
            return render(request, 'accounts/shop_owners/create_shop.html', {
                **base_site_context(),
                'consoles_platforms': Platform.objects.filter(category__name='Console')
            })
        
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
                    is_active=False
                )
                
                shop.submitted_by_uid = account_obj.uid
                shop.submitted_by_email = account_obj.email
                shop.save(update_fields=['submitted_by_uid', 'submitted_by_email'])
                
                if role == 'shop_owner':
                    shop.owners.add(account_obj)
                
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
                
                games_available_data = request.POST.get('games_available', '[]')
                games_to_add = []
                if games_available_data:
                    try:
                        game_identifiers = json.loads(games_available_data)
                        for identifier in game_identifiers:
                            game = Game.objects.filter(
                                models.Q(id=identifier) if is_valid_uuid(identifier) else models.Q(
                                    integer_id=identifier) if str(identifier).isdigit() else models.Q(pk=None)).first()
                            
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
                        logger.error(
                            f"Error parsing games_available in create_shop: {e} | data: {games_available_data}")
                
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
                
                # Use EmailManager for admin notification
                EmailManager.send_admin_new_shop(shop)
                
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
                
                messages.success(
                    request,
                    'Registration in progress. Check your email for shop verification status'
                )
                
                return redirect('accounts:gamer_dashboard')
        
        except Exception as e:
            logger.error(f"Shop creation error: {e}")
            messages.error(request, 'Failed to create shop. Please try again.')
    
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
        
        if not all([shop_name, description, city, building, floor, room_number,
                    shop_location, screen_number, base_price_per_hour,
                    opening_hours, closing_hours]):
            messages.error(request, 'Please fill in all compulsory fields.')
            return redirect('accounts:edit_shop', pk=shop.pk)
        
        if not console_types:
            messages.error(request, 'Please select at least one console type.')
            return redirect('accounts:edit_shop', pk=shop.pk)
        
        try:
            if not json.loads(games_available_data):
                messages.error(request, 'Please select at least one game.')
                return redirect('accounts:edit_shop', pk=shop.pk)
        except:
            messages.error(request, 'Invalid game data provided.')
            return redirect('accounts:edit_shop', pk=shop.pk)
        
        try:
            with transaction.atomic():
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
                
                games_available_data = request.POST.get('games_available', '[]')
                games_to_add = []
                if games_available_data:
                    try:
                        game_identifiers = json.loads(games_available_data)
                        for identifier in game_identifiers:
                            game = Game.objects.filter(
                                models.Q(id=identifier) if is_valid_uuid(identifier) else models.Q(
                                    integer_id=identifier) if str(identifier).isdigit() else models.Q(pk=None)).first()
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
    try:
        gamer = Gamer.objects.get(uid=request.session['firebase_uid'])
        request.session['role'] = 'gamer'
        request.session['user_id'] = gamer.id
        request.session['gamer_mode'] = True
        return redirect('accounts:gamer_dashboard')
    except Exception as e:
        logger.error(f"Error toggling to gamer mode: {e}")
        messages.error(request, "Failed to switch dashboards.")
        return redirect('accounts:shop_owner_dashboard')


def test_firebase(request):
    try:
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


# --- Admin Quick Actions ---

def quick_approve_shop(request, token):
    """Handles 1-click approvals directly from the admin email."""
    signer = TimestampSigner()
    template_name = 'accounts/admin_shop_action.html'
    
    try:
        data = signer.unsign_object(token, max_age=604800)  # 7-day expiry
        
        # Verify the token is specifically for approval
        if data.get('action') != 'approve':
            raise BadSignature("Invalid action type for this token.")
        
        shop_id = data.get('shop_id')
        shop = Shop.objects.get(id=shop_id)
        
        if shop.is_approved:
            context = {'status': 'info', 'title': 'Already Approved',
                       'message': f"Shop '{shop.name}' is already approved. No action needed."}
            return render(request, template_name, context)
        
        # 1. Approve the shop
        shop.is_approved = True
        shop.is_active = True
        shop.approved_at = timezone.now()
        shop.save(update_fields=['is_approved', 'is_active', 'approved_at'])
        
        # 2. Promote user to ShopOwner if needed
        if shop.owners.count() == 0 and (shop.submitted_by_email or shop.submitted_by_uid):
            shop_owner = None
            if shop.submitted_by_uid:
                shop_owner = ShopOwner.objects.filter(uid=shop.submitted_by_uid).first()
            if not shop_owner and shop.submitted_by_email:
                shop_owner = ShopOwner.objects.filter(email=shop.submitted_by_email).first()
            
            if not shop_owner:
                account = None
                if shop.submitted_by_uid:
                    account = Account.objects.filter(uid=shop.submitted_by_uid).first()
                if not account and shop.submitted_by_email:
                    account = Account.objects.filter(email=shop.submitted_by_email).first()
                
                if account:
                    try:
                        with transaction.atomic():
                            shop_owner = ShopOwner(account_ptr_id=account.id, date_joined=timezone.now())
                            for field in Account._meta.fields:
                                if field.name != 'id':
                                    setattr(shop_owner, field.name, getattr(account, field.name))
                            shop_owner.save()
                    except Exception as e:
                        logger.error(f"Failed to promote Account to ShopOwner via quick link: {e}")
                        if shop.submitted_by_uid:
                            shop_owner = ShopOwner.objects.filter(uid=shop.submitted_by_uid).first()
            
            if shop_owner:
                shop.owners.add(shop_owner)
        
        # 3. Send the notification email
        EmailManager.send_shop_approval(shop, approved=True)
        
        context = {'status': 'success', 'title': 'Success!',
                   'message': f"<b>{shop.name}</b> has been securely approved and is now live."}
        return render(request, template_name, context)
    
    except SignatureExpired:
        context = {'status': 'error', 'title': 'Link Expired',
                   'message': 'This approval link has expired. Please log in to the admin panel.'}
        return render(request, template_name, context)
    except (BadSignature, Shop.DoesNotExist):
        context = {'status': 'error', 'title': 'Invalid Link',
                   'message': 'The link may be malformed or the shop no longer exists.'}
        return render(request, template_name, context)
    except Exception as e:
        logger.error(f"Quick approve error: {e}")
        context = {'status': 'error', 'title': 'System Error',
                   'message': 'An unexpected error occurred while processing your request.'}
        return render(request, template_name, context)


def quick_reject_shop(request, token):
    """Handles 1-click rejections directly from the admin email."""
    signer = TimestampSigner()
    template_name = 'accounts/admin_shop_action.html'
    
    try:
        data = signer.unsign_object(token, max_age=604800)
        
        # Verify the token is specifically for rejection
        if data.get('action') != 'reject':
            raise BadSignature("Invalid action type for this token.")
        
        shop_id = data.get('shop_id')
        shop = Shop.objects.get(id=shop_id)
        
        if shop.is_approved:
            context = {'status': 'warning', 'title': 'Action Blocked',
                       'message': f"Shop '{shop.name}' is already approved and active. To revoke access, please use the admin panel."}
            return render(request, template_name, context)
        
        # We don't alter the shop database states here because pending shops are inactive by default.
        # We simply dispatch the rejection communication to the owner.
        EmailManager.send_shop_approval(shop, approved=False)
        
        context = {'status': 'success', 'title': 'Shop Rejected',
                   'message': f"<b>{shop.name}</b> has been rejected and the owner has been notified."}
        return render(request, template_name, context)
    
    except SignatureExpired:
        context = {'status': 'error', 'title': 'Link Expired',
                   'message': 'This rejection link has expired. Please log in to the admin panel.'}
        return render(request, template_name, context)
    except (BadSignature, Shop.DoesNotExist):
        context = {'status': 'error', 'title': 'Invalid Link',
                   'message': 'The link may be malformed or the shop no longer exists.'}
        return render(request, template_name, context)
    except Exception as e:
        logger.error(f"Quick reject error: {e}")
        context = {'status': 'error', 'title': 'System Error',
                   'message': 'An unexpected error occurred while processing your request.'}
        return render(request, template_name, context)