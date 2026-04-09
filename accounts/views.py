from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.utils import timezone
from django.db import transaction, models
from django.core.signing import TimestampSigner, SignatureExpired, BadSignature
import json
import logging
import re

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
    if not pending:
        return None
    
    with transaction.atomic():
        try:
            if pending.role == 'gamer':
                gamer = Gamer.objects.create(
                    uid=pending.uid,
                    email=pending.email,
                    first_name=pending.first_name,
                    last_name=pending.last_name,
                    phone=pending.phone,
                    custom_username=f"user{pending.uid[:8]}",
                    bio="Bio",
                    about="About",
                    location="Unknown"
                )
                account = gamer
                logger.info(f"Successfully created Gamer account: {gamer.email}")
            
            else:
                account = Account.objects.filter(uid=pending.uid).first()
                if account:
                    shop_owner = promote_account_to_shop_owner(account)
                else:
                    shop_owner = ShopOwner.objects.create(
                        uid=pending.uid,
                        email=pending.email,
                        first_name=pending.first_name,
                        last_name=pending.last_name,
                        phone=pending.phone
                    )
                account = shop_owner
                logger.info(f"Successfully created ShopOwner account: {account.email}")
            
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
    
    return Platform.objects.filter(
        models.Q(category__name__iexact=platform_str.replace('_', ' ')) |
        models.Q(category__slug__iexact=platform_str.lower().replace('_', '-'))
    ).first()


# Authentication Views
def register_view(request):
    role = request.GET.get('role', 'gamer').lower()
    if role != 'gamer':
        role = 'gamer'
    
    context = {
        **base_site_context(),
        'role': role,
        'role_label': "Gamer"
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
            
            if Account.objects.filter(email=email).exists():
                return JsonResponse({'success': False, 'message': 'Email already registered'})
            
            pending = PendingRegistration.objects.filter(uid=uid).first()
            
            if not pending:
                if PendingRegistration.objects.filter(email=email).exists():
                    return JsonResponse({'success': False,
                                         'message': 'A verification email was already sent. Please verify your email.'})
                if PendingRegistration.objects.filter(phone=phone).exists():
                    return JsonResponse(
                        {'success': False, 'message': 'Phone number already in use'})
            
            if pending:
                pending.email = email
                pending.first_name = first_name
                pending.last_name = last_name
                pending.phone = phone
                pending.role = role
                pending.save()
            else:
                PendingRegistration.objects.create(
                    uid=uid, email=email, first_name=first_name,
                    last_name=last_name, phone=phone, role=role,
                )
            
            username = f"{first_name} {last_name}".strip()
            email_sent = EmailManager.send_verification(email, uid, role, username=username)
            if not email_sent:
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
            return JsonResponse({'success': False, 'message': 'Registration failed. Please try again.'})
    
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
            
            try:
                decoded_token = firebase_auth.verify_id_token(id_token, clock_skew_seconds=60)
            except Exception as ve:
                message = str(ve)
                if 'Token used too early' in message or 'clock' in message.lower():
                    return JsonResponse({'success': False,
                                         'message': 'Temporary clock sync issue detected. Please try again in a few seconds.'})
                return JsonResponse({'success': False, 'message': 'Login failed. Please try again.'})
            
            uid = decoded_token['uid']
            
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
                    pending = PendingRegistration.objects.filter(uid=uid).first()
                    
                    if not pending and firebase_user.email:
                        pending = PendingRegistration.objects.filter(email=firebase_user.email).first()
                    
                    if pending:
                        if not firebase_user.email_verified:
                            request.session['show_resend'] = pending.email
                            return JsonResponse(
                                {'success': False, 'message': 'Please verify your account first to login'})
                        
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
                return JsonResponse({'success': False, 'message': 'Please verify your account first to login'})
            
            request.session['user_id'] = account.id
            request.session['firebase_uid'] = uid
            request.session['email'] = account.email
            request.session['role'] = role
            request.session['first_name'] = account.first_name
            request.session['last_name'] = account.last_name
            
            # Upgrade role immediately if they have a Shop Owner profile
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
            return JsonResponse({'success': True, 'message': success_message, 'role': role, 'next': next_url})
        
        except Exception as e:
            logger.error(f"Login error: {e}", exc_info=True)
            return JsonResponse({'success': False, 'message': 'Login failed. Please try again.'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})


def verify_email(request, uid):
    try:
        next_url = request.GET.get('next')
        if next_url:
            request.session['post_login_redirect'] = next_url
        
        firebase_user = firebase_auth.get_user(uid)
        if not firebase_user.email_verified:
            firebase_auth.update_user(uid, email_verified=True)
        
        account_exists = Gamer.objects.filter(uid=uid).exists() or ShopOwner.objects.filter(uid=uid).exists()
        
        if not account_exists:
            pending = PendingRegistration.objects.filter(uid=uid).first()
            if not pending and firebase_user.email:
                pending = PendingRegistration.objects.filter(email=firebase_user.email).first()
            
            if pending:
                provision_account_from_pending(pending)
            else:
                messages.error(request, 'Verification record not found. Please register again.')
                return redirect('accounts:register')
        
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
                
                email_sent = EmailManager.send_verification(email, uid, role)
                if not email_sent:
                    return JsonResponse(
                        {'success': False, 'message': 'Could not send verification email. Try again later.'})
            
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
                    
                    email_sent = EmailManager.send_verification(email, firebase_user.uid, role)
                    if not email_sent:
                        return JsonResponse(
                            {'success': False, 'message': 'Could not send verification email. Try again later.'})
                
                except (Gamer.DoesNotExist, ShopOwner.DoesNotExist):
                    firebase_user = firebase_auth.get_user_by_email(email)
                    EmailManager.send_verification(email, firebase_user.uid, 'gamer')
            
            return JsonResponse({'success': True, 'message': 'Verification email sent successfully'})
        
        except Exception as e:
            logger.error(f"Resend verification error: {e}")
            return JsonResponse({'success': False, 'message': 'Failed to resend verification email'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})


def logout_view(request):
    request.session.flush()
    messages.success(request, 'Logged out successfully.')
    return redirect('core:home')


# Password and Account management
@csrf_exempt
def change_password(request):
    if request.method == 'POST':
        try:
            if request.headers.get('Content-Type', '').startswith('application/json'):
                body = json.loads(request.body.decode('utf-8'))
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
            
            EmailManager.send_password_change(account.email, account.first_name)
            return JsonResponse({'success': True, 'message': 'Password changed successfully'})
        
        except Exception as e:
            logger.error(f"Password change error: {e}")
            return JsonResponse({'success': False, 'message': 'Failed to change password. Please try again.'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})


@csrf_exempt
def delete_account(request):
    if request.method == 'POST':
        try:
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
            except Exception:
                return JsonResponse({'success': False, 'message': 'Account not found'})
            
            user_email = account.email
            firebase_uid_to_delete = request.session.get('firebase_uid') or firebase_uid or getattr(account, 'uid',
                                                                                                    None)
            
            if firebase_uid_to_delete:
                try:
                    firebase_auth.delete_user(firebase_uid_to_delete)
                except Exception as e:
                    logger.error(f"Error deleting Firebase user: {e}")
            
            account.delete()
            request.session.flush()
            
            EmailManager.send_account_deletion(user_email)
            EmailManager.send_admin_account_deletion(user_email)
            
            return JsonResponse(
                {'success': True, 'message': 'Account permanently deleted', 'redirect_url': '/accounts/login/'})
        
        except Exception as e:
            logger.error(f"Account deletion error: {e}")
            return JsonResponse({'success': False, 'message': 'Failed to delete account. Please try again.'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})


# Gamer Views
def gamer_dashboard(request):
    if request.session.get('role') != 'gamer':
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    try:
        gamer = Gamer.objects.get(id=request.session['user_id'])
        
        # Check if they have been approved as a shop owner behind the scenes
        shop_owner = ShopOwner.objects.filter(uid=gamer.uid).first()
        if shop_owner and not request.session.get('gamer_mode'):
            request.session['role'] = 'shop_owner'
            request.session['user_id'] = shop_owner.id
            return redirect('accounts:shop_owner_dashboard')
        
        profile_complete = gamer.profile_completed
        if not profile_complete:
            messages.info(request, 'Please complete your profile to access full dashboard features')
        
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
                
                get_val = lambda k, default=None: request.POST.get(k, default)
                errors = {}
                
                username = get_val('custom_username', '').strip()
                if not username:
                    errors['custom_username'] = 'Username is required'
                else:
                    if not re.match(r'^[A-Za-z0-9_]{3,15}$', username):
                        errors['custom_username'] = 'Username must be 3-15 chars (letters, numbers, underscores)'
                    elif Gamer.objects.filter(custom_username__iexact=username).exclude(pk=gamer.pk).exists():
                        errors['custom_username'] = 'Username already taken'
                
                bio = get_val('bio', '').strip()
                if not bio:
                    errors['bio'] = 'Bio is required'
                
                location = get_val('location', '').strip()
                if not location:
                    errors['location'] = 'Location is required'
                
                platforms_raw = get_val('platforms', '[]') or '[]'
                platforms_list = json.loads(platforms_raw) if not isinstance(platforms_raw, list) else platforms_raw
                if not platforms_list:
                    errors['platforms'] = 'Select at least one platform'
                
                games_raw = get_val('games', '[]') or '[]'
                games_list = json.loads(games_raw) if not isinstance(games_raw, list) else games_raw
                if not games_list:
                    errors['games'] = 'Select or enter at least one game'
                
                if errors:
                    return JsonResponse({'success': False, 'message': 'Validation errors', 'errors': errors})
                
                gamer.custom_username = username
                gamer.bio = bio
                gamer.about = get_val('about', '').strip()
                gamer.location = location
                gamer.platforms = platforms_list
                
                attached_games = []
                for entry in games_list:
                    name = entry.strip() if isinstance(entry, str) else str(entry).strip()
                    if name:
                        existing = Game.objects.filter(name__iexact=name).first()
                        if existing:
                            attached_games.append(existing)
                
                if attached_games:
                    gamer.games.set(attached_games)
                
                gamer.profile_completed = True
                gamer.save()
                
                EmailManager.send_profile_completion(gamer.email, gamer.custom_username)
                
                return JsonResponse({
                    'success': True,
                    'message': 'Profile completed successfully!',
                    'profile_picture_url': gamer.profile_picture.url if gamer.profile_picture else '/static/core/images/player.jpeg',
                    'username': gamer.custom_username,
                })
        except Exception as e:
            logger.error(f"Gamer profile completion error: {e}")
            return JsonResponse({'success': False, 'message': 'Failed to complete profile.'})
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


@csrf_exempt
def check_username(request):
    username = (request.GET.get('username') or '').strip()
    pattern = re.compile(r'^[A-Za-z0-9_]{3,15}$')
    if not pattern.match(username):
        return JsonResponse({'available': False, 'reason': 'invalid_format'})
    exists = Gamer.objects.filter(custom_username__iexact=username).exists()
    return JsonResponse({'available': not exists, 'reason': 'taken' if exists else 'ok'})


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
                
                username = request.POST.get('custom_username', '').strip()
                if username and re.match(r'^[A-Za-z0-9_]{3,15}$', username):
                    if not Gamer.objects.filter(custom_username__iexact=username).exclude(pk=gamer.pk).exists():
                        gamer.custom_username = username
                
                gamer.bio = request.POST.get('bio', '').strip()
                gamer.about = request.POST.get('about', '').strip()
                gamer.location = request.POST.get('location', '').strip()
                
                gamer.save()
                messages.success(request, 'Profile updated successfully!')
                return redirect('accounts:gamer_settings')
        
        except Exception as e:
            logger.error(f"Profile edit error: {e}")
            messages.error(request, 'Failed to update profile. Please try again.')
    
    context = {**base_site_context(), 'gamer': gamer}
    return render(request, 'accounts/gamers/gamer_profile_edit.html', context)


def gamer_settings(request):
    if request.session.get('role') != 'gamer':
        return redirect('core:home')
    
    gamer = get_object_or_404(Gamer, id=request.session['user_id'])
    
    security_state = {
        'last_password_change': 'recently',
    }
    
    context = {
        **base_site_context(),
        'gamer': gamer,
        'security_state': security_state,
    }
    return render(request, 'accounts/gamers/gamer_settings.html', context)


def gamer_public_profile(request, username=None):
    if request.session.get('role') != 'gamer':
        return redirect('core:home')
    gamer = get_object_or_404(Gamer, custom_username=username) if username else get_object_or_404(Gamer,
                                                                                                  id=request.session[
                                                                                                      'user_id'])
    return render(request, 'accounts/gamers/gamer_public_profile.html', {**base_site_context(), 'gamer': gamer})


def gamer_games(request):
    if request.session.get('role') != 'gamer':
        return redirect('core:home')
    
    gamer = get_object_or_404(Gamer, id=request.session['user_id'])
    context = {
        **base_site_context(),
        'gamer': gamer,
        'gamer_games': gamer.games.filter(is_active=True).prefetch_related('genres'),
        'gamer_platforms': sorted({p for p in (gamer.platforms or []) if p}),
    }
    return render(request, 'accounts/gamers/gamer_games.html', context)


# Shop owner views
@csrf_exempt
def create_shop(request):
    role = request.session.get('role')
    if role not in ['gamer', 'shop_owner']:
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    account_obj = get_object_or_404(ShopOwner if role == 'shop_owner' else Gamer, id=request.session['user_id'])
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Extract Base Details
                shop = Shop.objects.create(
                    name=request.POST.get('shop_name'),
                    logo=request.FILES.get('logo'),
                    description=request.POST.get('description'),
                    city=request.POST.get('city'),
                    building=request.POST.get('building'),
                    floor=request.POST.get('floor'),
                    room_number=request.POST.get('room_number'),
                    location=request.POST.get('shop_location'),
                    address=request.POST.get('shop_location'),
                    screen_number=int(request.POST.get('screen_number', 0)),
                    base_price_per_hour=float(request.POST.get('base_price_per_hour', 0)),
                    opening_hours=request.POST.get('opening_hours'),
                    closing_hours=request.POST.get('closing_hours'),
                    business_permit=request.FILES.get('business_permit'),
                    is_active=False
                )
                
                shop.submitted_by_uid = account_obj.uid
                shop.submitted_by_email = account_obj.email
                shop.save(update_fields=['submitted_by_uid', 'submitted_by_email'])
                
                if role == 'shop_owner':
                    shop.owners.add(account_obj)
                
                # Consoles
                console_types = request.POST.getlist('console_types')
                for c_slug in console_types:
                    platform = get_platform_by_string(c_slug)
                    if platform:
                        Console.objects.create(
                            shop=shop,
                            console_type=platform,
                            quantity=int(request.POST.get(f'console_quantity_{c_slug}', 1))
                        )
                
                # Games
                games_available_data = request.POST.get('games_available', '[]')
                games_to_add = []
                if games_available_data:
                    try:
                        game_names = json.loads(games_available_data)
                        for name in game_names:
                            name = str(name).strip()
                            if name:
                                game, created = Game.objects.get_or_create(
                                    name__iexact=name,
                                    defaults={'name': name, 'is_verified': False, 'is_active': True}
                                )
                                games_to_add.append(game)
                    except Exception as e:
                        logger.error(f"Error parsing games: {e}")
                
                if games_to_add:
                    shop.games_available.set(games_to_add)
                
                # Pricing
                pricing_data = request.POST.get('game_pricing', '[]')
                if pricing_data:
                    try:
                        pricing_list = json.loads(pricing_data)
                        for price_data in pricing_list:
                            game_name = price_data.get('game_id')
                            if not game_name: continue
                            
                            game = Game.objects.filter(name__iexact=str(game_name).strip()).first()
                            if game:
                                GamePricing.objects.create(
                                    shop=shop,
                                    game=game,
                                    price_per_hour=float(price_data.get('price_per_hour', 0)),
                                    is_premium=price_data.get('is_premium', False)
                                )
                    except Exception as e:
                        logger.error(f"Error parsing pricing: {e}")
                
                EmailManager.send_admin_new_shop(shop)
                messages.success(request, 'Venue deployment in progress! Awaiting admin verification.')
                
                if role == 'shop_owner':
                    return redirect('accounts:shop_owner_dashboard')
                return redirect('accounts:gamer_dashboard')
        
        except Exception as e:
            logger.error(f"Shop creation error: {e}")
            messages.error(request, 'Failed to deploy venue. Please check your inputs and try again.')
    
    games = Game.objects.filter(is_active=True).order_by('name')
    games_json = []
    for g in games:
        if not is_valid_uuid(g.name):
            games_json.append({'id': str(g.id), 'name': g.name})
    
    context = {
        **base_site_context(),
        'shop_owner': account_obj if role == 'shop_owner' else None,
        'gamer': account_obj if role == 'gamer' else None,
        'games': games,
        'games_json': games_json,
        'consoles_platforms': Platform.objects.filter(category__name='Console').order_by('name')
    }
    return render(request, 'accounts/shop_owners/shops/create_shop.html', context)


def promote_account_to_shop_owner(account):
    # Safely promotes Gamer account to a ShopOwner
    try:
        return ShopOwner.objects.get(id=account.id)
    except ShopOwner.DoesNotExist:
        # Promote an existing parent to a child in Django MTI, instantiate
        # the child with the parent's pointer ID and copy the dictionary state.
        shop_owner = ShopOwner(
            account_ptr_id=account.id,
            date_joined=timezone.now()
        )
        shop_owner.__dict__.update(account.__dict__)
        shop_owner.save()
        return shop_owner


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


def shop_owner_dashboard(request):
    if 'gamer_mode' in request.session:
        del request.session['gamer_mode']
    
    role = request.session.get('role')
    
    # Shop owner mode
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
            total_unique_games = Game.objects.filter(shops__in=shops).distinct().count()
            premium_games = GamePricing.objects.filter(shop__in=shops, is_premium=True).values(
                'game').distinct().count()
            
            shop_stats = {
                'total_screens': sum(shop.total_consoles() for shop in shops),
                'total_games': total_unique_games,
                'premium_games': premium_games,
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
    
    # Gamer mode i.e Pending Shop Owner
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
            total_unique_games = Game.objects.filter(shops__in=shops).distinct().count()
            premium_games = GamePricing.objects.filter(shop__in=shops, is_premium=True).values(
                'game').distinct().count()
            
            shop_stats = {
                'total_screens': sum(shop.total_consoles() for shop in shops),
                'total_games': total_unique_games,
                'premium_games': premium_games,
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
    
    # Fetch shops for the overview tab
    shops = Shop.objects.filter(owners=shop_owner).order_by('-created_at')
    verified_shops = shops.filter(is_active=True)
    
    # Calculate metrics for the profile summary cards
    total_games = Game.objects.filter(shops__in=shops).distinct().count()
    total_consoles = sum(shop.total_consoles() for shop in shops)
    
    shop_metrics = {
        'total_shops': shops.count(),
        'verified_shops': verified_shops.count(),
        'total_games': total_games,
        'total_consoles': total_consoles,
    }
    
    # Security state placeholder (adjust based on your actual models if needed)
    security_state = {
        'multi_factor': False,
        'last_password_change': 'recently',
        'active_sessions': 1
    }
    
    context = {
        **base_site_context(),
        'shop_owner': shop_owner,
        'shop_owner_avatar': getattr(shop_owner, 'profile_picture', None),
        'shops': shops,
        'shop_metrics': shop_metrics,
        'security_state': security_state,
    }
    return render(request, 'accounts/shop_owners/shop_owner_account.html', context)


def shop_owner_profile_edit(request):
    if request.session.get('role') != 'shop_owner':
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    shop_owner = get_object_or_404(ShopOwner, id=request.session['user_id'])
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Handle avatar upload
                if 'profile_picture' in request.FILES:
                    shop_owner.profile_picture = request.FILES['profile_picture']
                
                # Handle text fields from the modal form
                first_name = request.POST.get('first_name', '').strip()
                last_name = request.POST.get('last_name', '').strip()
                phone = request.POST.get('phone', '').strip()
                
                if first_name:
                    shop_owner.first_name = first_name
                if last_name:
                    shop_owner.last_name = last_name
                if phone:
                    shop_owner.phone = phone
                
                shop_owner.save()
                
                # Update session variables to reflect the new name instantly
                request.session['first_name'] = shop_owner.first_name
                request.session['last_name'] = shop_owner.last_name
                request.session.modified = True
                
                messages.success(request, 'Profile updated successfully!')
        
        except Exception as e:
            logger.error(f"Shop owner profile edit error: {e}")
            messages.error(request, 'Failed to update profile. Please try again.')
    
    # Always redirect back to the profile hub
    return redirect('accounts:shop_owner_profile')


def shop_owner_venues(request):
    if request.session.get('role') != 'shop_owner':
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    shop_owner = get_object_or_404(ShopOwner, id=request.session['user_id'])
    
    # Fetch all shops with their related data optimized
    shops = (
        Shop.objects.filter(owners=shop_owner)
        .prefetch_related('games_available', 'consoles')
        .order_by('-created_at')
    )
    
    context = {
        **base_site_context(),
        'shop_owner': shop_owner,
        'shops': shops,
        'total_count': shops.count(),
        'active_count': shops.filter(is_active=True).count(),
        'pending_count': shops.filter(is_active=False).count(),
    }
    return render(request, 'accounts/shop_owners/shops/shop_owner_venues.html', context)


def shop_owner_shop_detail(request, pk):
    if request.session.get('role') != 'shop_owner':
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    shop_owner = get_object_or_404(ShopOwner, id=request.session['user_id'])
    
    # Fetch the specific shop, securely ensuring this owner actually owns it
    shop = get_object_or_404(
        Shop.objects.prefetch_related('games_available', 'consoles__console_type', 'game_prices'),
        pk=pk,
        owners=shop_owner
    )
    
    # Fetch all games and pricing
    games = shop.games_available.all().order_by('name')
    prices = shop.game_prices.all()
    
    # Create a dictionary for instant pricing lookups
    pricing_dict = {price.game_id: price for price in prices}
    
    # Attach the specific shop's pricing directly to the game object for the template
    for game in games:
        game.shop_pricing = pricing_dict.get(game.id, None)
    
    context = {
        **base_site_context(),
        'shop_owner': shop_owner,
        'shop': shop,
        'games': games,
    }
    return render(request, 'accounts/shop_owners/shops/shop_owner_shop_detail.html', context)


def edit_shop(request, pk):
    if request.session.get('role') != 'shop_owner':
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    shop_owner = get_object_or_404(ShopOwner, id=request.session['user_id'])
    # Securely fetch the shop ensuring it belongs to this owner
    shop = get_object_or_404(
        Shop.objects.prefetch_related('games_available', 'consoles', 'game_prices__game'),
        pk=pk,
        owners=shop_owner
    )
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Update ONLY the allowed operational fields
                shop.description = request.POST.get('description', shop.description)
                shop.opening_hours = request.POST.get('opening_hours', shop.opening_hours)
                shop.closing_hours = request.POST.get('closing_hours', shop.closing_hours)
                shop.base_price_per_hour = float(request.POST.get('base_price_per_hour', shop.base_price_per_hour))
                shop.screen_number = int(request.POST.get('screen_number', shop.screen_number))
                shop.save()
                
                # Update Consoles
                Console.objects.filter(shop=shop).delete()
                console_types = request.POST.getlist('console_types')
                for c_slug in console_types:
                    platform = get_platform_by_string(c_slug)
                    if platform:
                        Console.objects.create(
                            shop=shop,
                            console_type=platform,
                            quantity=int(request.POST.get(f'console_quantity_{c_slug}', 1))
                        )
                
                # Update Games Library
                games_available_data = request.POST.get('games_available', '[]')
                games_to_add = []
                if games_available_data:
                    game_names = json.loads(games_available_data)
                    for name in game_names:
                        name = str(name).strip()
                        if name:
                            game, _ = Game.objects.get_or_create(
                                name__iexact=name,
                                defaults={'name': name, 'is_verified': False, 'is_active': True}
                            )
                            games_to_add.append(game)
                shop.games_available.set(games_to_add)
                
                # Update Custom Pricing
                GamePricing.objects.filter(shop=shop).delete()
                pricing_data = request.POST.get('game_pricing', '[]')
                if pricing_data:
                    pricing_list = json.loads(pricing_data)
                    for price_data in pricing_list:
                        game_name = price_data.get('game_id')  # use name as ID
                        if not game_name: continue
                        
                        game = Game.objects.filter(name__iexact=str(game_name).strip()).first()
                        if game:
                            GamePricing.objects.create(
                                shop=shop,
                                game=game,
                                price_per_hour=float(price_data.get('price_per_hour', shop.base_price_per_hour)),
                                is_premium=price_data.get('is_premium', False)
                            )
                
                messages.success(request, f'{shop.name} settings updated successfully.')
                return redirect('accounts:shop_owner_shop_detail', pk=shop.pk)
        
        except Exception as e:
            logger.error(f"Shop edit error: {e}")
            messages.error(request, 'Failed to update venue. Please check your inputs.')
    
    games = Game.objects.filter(is_active=True).order_by('name')
    games_json = [{'id': str(g.id), 'name': g.name} for g in games if not is_valid_uuid(g.name)]
    
    existing_consoles = shop.consoles.all()
    pricing = shop.game_prices.select_related('game')
    
    # Pack quantities into a dictionary for easy template lookup
    quantities_dict = {c.console_type.slug: c.quantity for c in existing_consoles}
    
    context = {
        **base_site_context(),
        'shop_owner': shop_owner,
        'shop': shop,
        'games_json': games_json,
        'consoles_platforms': Platform.objects.filter(category__name='Console').order_by('name'),
        'existing_console_slugs': [c.console_type.slug for c in existing_consoles],
        'existing_quantities': quantities_dict,
        'existing_games': json.dumps(list(shop.games_available.values_list('name', flat=True))),
        'existing_pricing': json.dumps(
            [{'game_id': p.game.name, 'price_per_hour': float(p.price_per_hour), 'is_premium': p.is_premium} for p in
             pricing])
    }
    return render(request, 'accounts/shop_owners/shops/edit_shop.html', context)


# Admin Quick Actions
def quick_approve_shop(request, token):
    # Handles 1-click approvals directly from the admin email
    signer = TimestampSigner()
    template_name = 'accounts/admin_shop_action.html'
    
    try:
        data = signer.unsign_object(token, max_age=604800)  # 7-day expiry
        if data.get('action') != 'approve':
            raise BadSignature("Invalid action type.")
        
        shop = Shop.objects.get(id=data.get('shop_id'))
        
        if shop.is_approved:
            return render(request, template_name, {'status': 'info', 'title': 'Already Approved',
                                                   'message': f"Shop '{shop.name}' is already active."})
        
        shop.is_approved = True
        shop.is_active = True
        shop.approved_at = timezone.now()
        shop.save(update_fields=['is_approved', 'is_active', 'approved_at'])
        
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
                            shop_owner = promote_account_to_shop_owner(account)
                    except Exception as e:
                        logger.error(f"Failed to promote Account to ShopOwner via quick link: {e}")
            
            if shop_owner:
                shop.owners.add(shop_owner)
        
        EmailManager.send_shop_approval(shop, approved=True)
        return render(request, template_name,
                      {'status': 'success', 'title': 'Success!', 'message': f"<b>{shop.name}</b> is now live."})
    
    except SignatureExpired:
        return render(request, template_name,
                      {'status': 'error', 'title': 'Link Expired', 'message': 'This link has expired.'})
    except (BadSignature, Shop.DoesNotExist):
        return render(request, template_name,
                      {'status': 'error', 'title': 'Invalid Link', 'message': 'Malformed link.'})


def quick_reject_shop(request, token):
    # Handles 1-click rejections directly from the admin email
    signer = TimestampSigner()
    template_name = 'accounts/admin_shop_action.html'
    
    try:
        data = signer.unsign_object(token, max_age=604800)
        if data.get('action') != 'reject':
            raise BadSignature("Invalid action type.")
        
        shop = Shop.objects.get(id=data.get('shop_id'))
        
        if shop.is_approved:
            return render(request, template_name, {'status': 'warning', 'title': 'Action Blocked',
                                                   'message': f"Shop '{shop.name}' is already approved."})
        
        EmailManager.send_shop_approval(shop, approved=False)
        return render(request, template_name, {'status': 'success', 'title': 'Shop Rejected',
                                               'message': f"<b>{shop.name}</b> has been rejected."})
    
    except SignatureExpired:
        return render(request, template_name, {'status': 'error', 'title': 'Link Expired'})
    except (BadSignature, Shop.DoesNotExist):
        return render(request, template_name, {'status': 'error', 'title': 'Invalid Link'})