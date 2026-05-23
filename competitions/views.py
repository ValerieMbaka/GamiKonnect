import logging
from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db import transaction
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q

# Site context
from core.views import base_site_context

# Models
from accounts.models import Gamer, ShopOwner
from shops.models import Shop
from games.models import Game, Platform
from activities.models import ActivityLog
from .models import Competition, CompetitionRegistration, CompetitionResult
from .services import CompetitionService

# Forms
from .forms import (
    CompetitionCreateForm,
    CompetitionEditForm,
    CompetitionApprovalForm,
    CompetitionRejectionForm,
    CompetitionRegistrationForm,
    GamerCheckInForm,
    CompetitionResultForm,
)

# Email service
from core.email_service import EmailManager

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Access Helpers
# ---------------------------------------------------------------------------

def get_gamer(request):
    """Returns the Gamer object for the current session, or None."""
    if request.session.get('role') not in ['gamer', 'shop_owner']:
        return None
    try:
        return Gamer.objects.get(id=request.session['user_id'])
    except Gamer.DoesNotExist:
        try:
            shop_owner = ShopOwner.objects.get(id=request.session['user_id'])
            return Gamer.objects.get(uid=shop_owner.uid)
        except (ShopOwner.DoesNotExist, Gamer.DoesNotExist):
            return None


def get_shop_owner(request):
    """Returns the ShopOwner object for the current session, or None."""
    if request.session.get('role') != 'shop_owner':
        return None
    try:
        return ShopOwner.objects.get(id=request.session['user_id'])
    except ShopOwner.DoesNotExist:
        return None


# ---------------------------------------------------------------------------
# Public / Gamer-Facing Views
# ---------------------------------------------------------------------------

def competition_list(request):
    competitions = Competition.objects.filter(
        status__in=['live', 'registration_open', 'registration_closed', 'ongoing']
    ).select_related('game', 'platform', 'shop').order_by('-scheduled_time')
    
    query = request.GET.get('q')
    game_id = request.GET.get('game')
    platform_id = request.GET.get('platform')
    status = request.GET.get('status')
    prize_type = request.GET.get('prize_type')
    
    if query:
        competitions = competitions.filter(
            Q(name__icontains=query) |
            Q(game__name__icontains=query) |
            Q(shop__name__icontains=query)
        )
    if game_id:
        competitions = competitions.filter(game__id=game_id)
    if platform_id:
        competitions = competitions.filter(platform__id=platform_id)
    if status:
        competitions = competitions.filter(status=status)
    if prize_type:
        competitions = competitions.filter(prize_type=prize_type)
    
    paginator = Paginator(competitions, 12)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    
    registered_ids = set()
    pending_payment_ids = set()
    gamer = get_gamer(request)
    if gamer:
        gamer_registrations = CompetitionRegistration.objects.filter(
            gamer=gamer, is_cancelled=False
        ).values('competition_id', 'payment_status')
        for item in gamer_registrations:
            competition_id = item['competition_id']
            if item['payment_status'] == 'completed':
                registered_ids.add(competition_id)
            else:
                pending_payment_ids.add(competition_id)
    
    context = {
        **base_site_context(),
        'competitions': page,
        'registered_ids': registered_ids,
        'pending_payment_ids': pending_payment_ids,
        'all_games': Game.objects.filter(is_active=True, is_verified=True).order_by('name'),
        'all_platforms': Platform.objects.all().order_by('name'),
        'gamer': gamer,
    }
    return render(request, 'competitions/competition_list.html', context)


def competition_detail(request, slug):
    # Try to find by slug first, then by integer_id for backward compatibility
    try:
        competition = Competition.objects.select_related('game', 'platform', 'shop', 'created_by').get(slug=slug)
    except Competition.DoesNotExist:
        try:
            competition = Competition.objects.select_related('game', 'platform', 'shop', 'created_by').get(integer_id=int(slug))
        except (Competition.DoesNotExist, ValueError):
            raise Http404("Competition not found.")

    if competition.status not in [
        'live', 'registration_open', 'registration_closed',
        'ongoing', 'checkin_submitted', 'results_pending',
        'results_submitted', 'pending_prize_verification', 'completed'
    ]:
        raise Http404("Competition not accessible.")
    
    gamer = get_gamer(request)
    shop_owner = get_shop_owner(request)
    
    # Access control: Only registered gamers or the shop owner or admin can view detail page
    is_shop_owner_of_competition = False
    if shop_owner:
        is_shop_owner_of_competition = competition.shop.owners.filter(pk=shop_owner.pk).exists()
    
    registration = None
    if gamer:
        registration = CompetitionRegistration.objects.filter(
            competition=competition, gamer=gamer, is_cancelled=False
        ).first()
    
    # Check access permission
    is_admin = request.session.get('role') == 'admin' # Assuming session contains role
    if not (registration or is_shop_owner_of_competition or is_admin):
        messages.warning(request, "You must be registered for this competition to view its details.")
        return redirect('competitions:list')

    # Get all registered gamers (participants) for all users to see
    participants = competition.registrations.filter(
        is_cancelled=False
    ).select_related('gamer').order_by('registered_at')
    
    registrations = None
    if is_shop_owner_of_competition:
        registrations = competition.registrations.filter(
            is_cancelled=False
        ).select_related('gamer').order_by('registered_at')
    
    # Get verified results for display (available when competition is completed)
    results = None
    if competition.status == 'completed':
        results = competition.results.filter(
            verified=True
        ).select_related('gamer').order_by('rank')
    
    context = {
        **base_site_context(),
        'competition': competition,
        'full_rules': competition.get_full_rules(),
        'gamer': gamer,
        'shop_owner': shop_owner,
        'is_shop_owner_of_competition': is_shop_owner_of_competition,
        'registration': registration,
        'participants': participants,
        'registrations': registrations,
        'results': results,
        'registered_count': competition.registered_count(),
        'is_full': competition.is_registration_full(),
        'profile_complete': gamer.profile_completed if gamer else False,
        'has_owner_access': shop_owner is not None,
    }
    return render(request, 'competitions/competition_detail.html', context)


# ---------------------------------------------------------------------------
# Gamer Registration Views
# ---------------------------------------------------------------------------

@csrf_exempt
def competition_register(request, slug):
    """
    GET: Returns the registration modal HTML
    POST: Processes the registration and returns JSON response
    """
    try:
        competition = Competition.objects.select_related('game', 'platform', 'shop').get(slug=slug)
        if competition.status not in ['live', 'registration_open']:
            raise Competition.DoesNotExist
    except Competition.DoesNotExist:
        if request.method == 'GET':
            return render(request, 'competitions/competition_list.html', {'message': 'Competition not found'}, status=404)
        return JsonResponse({'success': False, 'message': 'Competition not found.'}, status=404)
    
    # GET: Return the registration modal HTML
    if request.method == 'GET':
        gamer = get_gamer(request)
        if not gamer:
            return JsonResponse({'success': False, 'message': 'You must be logged in.'}, status=403)
        
        # Check if already registered
        existing_registration = CompetitionRegistration.objects.filter(
            competition=competition,
            gamer=gamer,
            is_cancelled=False
        ).first()
        
        if existing_registration and existing_registration.payment_status == 'completed':
            return JsonResponse({'success': False, 'message': 'Already registered'}, status=400)
        
        context = {
            'competition': competition,
            'gamer': gamer,
            'existing_registration': existing_registration,
            'pending_payment': bool(existing_registration and existing_registration.payment_status != 'completed'),
        }
        return render(request, 'competitions/competition_registration.html', context)
    
    # POST: Process the registration
    if request.method == 'POST':
        if request.session.get('role') not in ['gamer', 'shop_owner']:
            return JsonResponse({'success': False, 'message': 'You must be logged in to register.'}, status=403)
        
        gamer = get_gamer(request)
        if not gamer:
            return JsonResponse({'success': False, 'message': 'Gamer profile not found.'}, status=403)
        
        try:
            # THE LOCK: Ensure concurrency safety for max_participants
            with transaction.atomic():
                competition = Competition.objects.select_for_update().get(slug=slug)
                
                if competition.is_registration_full():
                    return JsonResponse({
                        'success': False,
                        'message': 'Sorry, this competition is already full.'
                    }, status=400)

                existing_registration = CompetitionRegistration.objects.filter(
                    competition=competition,
                    gamer=gamer,
                    is_cancelled=False,
                ).first()

                if existing_registration:
                    if existing_registration.payment_status == 'completed':
                        return JsonResponse({
                            'success': False,
                            'message': 'You are already registered for this competition.'
                        }, status=400)

                    if competition.entry_fee > 0:
                        phone_number = request.POST.get('phone_number')
                        if phone_number:
                            existing_registration.payment_phone_number = phone_number
                            existing_registration.save(update_fields=['payment_phone_number'])

                        return JsonResponse({
                            'success': True,
                            'message': 'Registration is pending payment. Continue to secure checkout.',
                            'competition_id': competition.integer_id,
                            'competition_slug': competition.slug,
                            'competition_title': competition.name,
                            'payment_required': True,
                            'registration': {
                                'id': str(existing_registration.id),
                                'unique_code': existing_registration.unique_code,
                            }
                        })

                    # Safety fallback for free competitions.
                    existing_registration.payment_status = 'completed'
                    existing_registration.paid_at = timezone.now()
                    existing_registration.save(update_fields=['payment_status', 'paid_at'])

                    return JsonResponse({
                        'success': True,
                        'message': f'Registration successful! Your unique access code has been sent to {gamer.email}.',
                        'competition_id': competition.integer_id,
                        'competition_slug': competition.slug,
                        'competition_title': competition.name,
                        'access_code': existing_registration.unique_code,
                        'redirect_url': reverse('competitions:detail', args=[competition.slug]),
                        'registration': {
                            'id': str(existing_registration.id),
                            'unique_code': existing_registration.unique_code,
                        }
                    })
                
                form = CompetitionRegistrationForm(request.POST, competition=competition, gamer=gamer)
                
                if form.is_valid():
                    # Create registration and leave paid competitions pending until gateway verification.
                    registration = form.save(commit=False)
                    if competition.entry_fee > 0:
                        registration.payment_status = 'pending'
                        registration.payment_phone_number = request.POST.get('phone_number')
                    else:
                        registration.payment_status = 'completed'
                        registration.paid_at = timezone.now()
                    
                    registration.save()
                    
                    # Log the registration initiation
                    try:
                        ActivityLog.objects.create(
                            actor=gamer,
                            gamer=gamer,
                            action_type=ActivityLog.ActionTypes.CREATE,
                            target=registration,
                            description=f"Registered for: {competition.name}",
                            meta_data={
                                'competition_id': competition.integer_id,
                                'competition_slug': competition.slug,
                                'competition_name': competition.name,
                                'registration_id': str(registration.id),
                                'unique_code': registration.unique_code,
                            }
                        )
                    except Exception:
                        logger.exception('Failed to log competition registration activity')

                    # Send registration confirmation only for completed (free) entries.
                    if registration.payment_status == 'completed':
                        try:
                            EmailManager.send_competition_registration(gamer, competition, registration)
                        except Exception:
                            logger.exception('Failed to send competition registration email')
                    
                    # Return registration data with all necessary information for frontend
                    return JsonResponse({
                        'success': True,
                        'message': (
                            'Registration created. Continue to secure payment to complete your entry.'
                            if competition.entry_fee > 0
                            else f'Registration successful! Your unique access code has been sent to {gamer.email}.'
                        ),
                        'competition_id': competition.integer_id,
                        'competition_slug': competition.slug,
                        'competition_title': competition.name,
                        'access_code': registration.unique_code if competition.entry_fee <= 0 else None,
                        'payment_required': competition.entry_fee > 0,
                        'redirect_url': reverse('competitions:detail', args=[competition.slug]),
                        'registration': {
                            'id': str(registration.id),
                            'unique_code': registration.unique_code,
                        }
                    })
                else:
                    errors = {field: error[0] for field, error in form.errors.items()}
                    return JsonResponse({
                        'success': False,
                        'message': list(form.errors.values())[0][0],
                        'errors': errors
                    }, status=400)
        
        except Competition.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Competition not found.'}, status=404)
        except Exception as e:
            logger.error(f"Competition registration error: {str(e)}", exc_info=True)
            return JsonResponse({'success': False, 'message': 'Registration failed. Please try again.'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)


def check_registration_status(request, competition_id):
    """
    AJAX endpoint to check if gamer is already registered for a competition.
    Used by the modal to prevent duplicate registrations.
    """
    if request.method != 'GET':
        return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)
    
    if request.session.get('role') not in ['gamer', 'shop_owner']:
        return JsonResponse({'already_registered': False})
    
    gamer = get_gamer(request)
    if not gamer:
        return JsonResponse({'already_registered': False})
    
    try:
        # Try to find the competition by UUID, slug, or integer_id
        try:
            competition = Competition.objects.get(id=competition_id)
        except (Competition.DoesNotExist, ValidationError, ValueError):
            try:
                competition = Competition.objects.get(slug=competition_id)
            except Competition.DoesNotExist:
                try:
                    competition = Competition.objects.get(integer_id=int(competition_id))
                except (Competition.DoesNotExist, ValueError):
                    return JsonResponse({'already_registered': False})
        
        existing_registration = CompetitionRegistration.objects.filter(
            competition=competition,
            gamer=gamer,
            is_cancelled=False
        ).first()

        is_registered = bool(existing_registration and existing_registration.payment_status == 'completed')
        pending_payment = bool(existing_registration and existing_registration.payment_status != 'completed')
        
        return JsonResponse({
            'already_registered': is_registered,
            'pending_payment': pending_payment,
            'payment_status': existing_registration.payment_status if existing_registration else None,
            'competition_id': str(competition.id),
            'integer_id': competition.integer_id,
            'slug': competition.slug,
        })
    except Exception as e:
        logger.error(f"Error checking registration status: {e}")
        return JsonResponse({'already_registered': False})


# ---------------------------------------------------------------------------
# Gamer Dashboard — Competition Views
# ---------------------------------------------------------------------------

def gamer_competitions(request):
    if request.session.get('role') not in ['gamer', 'shop_owner']:
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    gamer = get_gamer(request)
    if not gamer:
        messages.error(request, 'Gamer profile not found.')
        return redirect('core:home')
    
    registrations = CompetitionRegistration.objects.filter(
        gamer=gamer, is_cancelled=False
    ).select_related('competition__game', 'competition__platform', 'competition__shop').order_by(
        '-competition__scheduled_time'
    )
    
    now = timezone.now()
    upcoming = registrations.filter(competition__scheduled_time__gte=now)
    past = registrations.filter(competition__scheduled_time__lt=now)
    
    context = {
        **base_site_context(),
        'gamer': gamer,
        'upcoming_registrations': upcoming,
        'past_registrations': past,
    }
    return render(request, 'competitions/gamer_competitions.html', context)


def gamer_competition_result(request, slug):
    if request.session.get('role') not in ['gamer', 'shop_owner']:
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    gamer = get_gamer(request)
    if not gamer:
        messages.error(request, 'Gamer profile not found.')
        return redirect('core:home')
    
    # Try to find by slug first, then by integer_id for backward compatibility
    try:
        competition = Competition.objects.get(slug=slug, status='completed')
    except Competition.DoesNotExist:
        try:
            competition = Competition.objects.get(integer_id=int(slug), status='completed')
        except (Competition.DoesNotExist, ValueError):
            raise Http404("Competition not found or not completed.")

    result = get_object_or_404(CompetitionResult, competition=competition, gamer=gamer, verified=True)
    results = competition.results.filter(verified=True).select_related('gamer').order_by('rank')
    
    context = {
        **base_site_context(),
        'gamer': gamer,
        'competition': competition,
        'result': result,
        'results': results,
    }
    return render(request, 'competitions/competition_results.html', context)


# ---------------------------------------------------------------------------
# Shop Owner — Competition Management Views
# ---------------------------------------------------------------------------

def shop_owner_competitions(request):
    if request.session.get('role') != 'shop_owner':
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    shop_owner = get_shop_owner(request)
    if not shop_owner:
        messages.error(request, 'Shop owner profile not found.')
        return redirect('core:home')
    
    competitions = Competition.objects.filter(
        shop__in=shop_owner.shops.all()
    ).select_related('game', 'platform', 'shop').order_by('-created_at')

    ongoing_competitions = competitions.filter(status='ongoing').order_by('scheduled_time')
    
    context = {
        **base_site_context(),
        'shop_owner': shop_owner,
        'shop_owner_avatar': getattr(shop_owner, 'profile_picture', None),
        'competitions': competitions,
        'ongoing_competitions': ongoing_competitions,
        'total': competitions.count(),
        'pending': competitions.filter(status='pending').count(),
        'live': competitions.filter(status__in=['live', 'registration_open']).count(),
        'completed': competitions.filter(status='completed').count(),
        'all_games': Game.objects.filter(
            is_active=True, is_verified=True
        ).prefetch_related('supported_platforms').order_by('name'),
    }
    return render(request, 'competitions/shop_owner_competitions.html', context)


@csrf_exempt
def shop_owner_competition_create(request):
    if request.session.get('role') != 'shop_owner':
        return JsonResponse({'success': False, 'message': 'Access denied.'}, status=403)
    
    shop_owner = get_shop_owner(request)
    if not shop_owner:
        return JsonResponse({'success': False, 'message': 'Shop owner profile not found.'}, status=403)

    approved_shops = shop_owner.shops.filter(is_approved=True).prefetch_related(
        'games_available__supported_platforms',
        'consoles__console_type'
    )

    shop_games_data = {}
    shop_consoles_data = {}

    for shop in approved_shops:
        valid_games = shop.games_available.filter(is_active=True).prefetch_related(
            'supported_platforms'
        ).order_by('name')

        shop_games_data[str(shop.id)] = [
            {
                'id': str(game.id),
                'name': game.name,
                'platforms': [
                    {'id': str(platform.id), 'name': platform.name}
                    for platform in game.supported_platforms.all()
                ],
            }
            for game in valid_games
        ]

        shop_consoles_data[str(shop.id)] = [
            str(console.console_type.id)
            for console in shop.consoles.all()
        ]
    
    if request.method == 'GET':
        context = {
            'approved_shops': approved_shops,
            'shop_games_data': shop_games_data,
            'shop_consoles_data': shop_consoles_data,
        }
        return render(request, 'competitions/create_competition.html', context)

    if request.method == 'POST':
        import logging
        logger = logging.getLogger(__name__)
        
        form = CompetitionCreateForm(request.POST, shop_owner=shop_owner)
        if form.is_valid():
            try:
                with transaction.atomic():
                    competition = form.save(commit=False)
                    competition.created_by = shop_owner
                    competition.status = 'pending_review'
                    
                    # Log the submitted data if it fails validation for debugging
                    logger.debug(f"Competition creation form data: {request.POST}")
                    
                    competition.save()

                    try:
                        ActivityLog.objects.create(
                            actor=shop_owner,
                            action_type=ActivityLog.ActionTypes.CREATE,
                            target=competition,
                            description=f"Created competition: {competition.name}",
                            meta_data={
                                'shop_id': str(competition.shop_id),
                                'game_id': str(competition.game_id),
                                'status': competition.status,
                            }
                        )
                    except Exception:
                        logger.exception('Failed to log competition creation activity')
                    
                    EmailManager.send_competition_submitted(competition)
                    EmailManager.send_competition_submission_confirmation(
                        shop_owner=shop_owner,
                        competition=competition
                    )
                
                return JsonResponse({
                    'success': True,
                    'message': f"'{competition.name}' submitted for review!",
                })
            except Exception as e:
                logger.error(f"Competition creation error: {e}")
                return JsonResponse({'success': False, 'message': 'Failed to submit. Please try again.'})
        else:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Competition form errors: {form.errors}")
            # Log the full POST data to see what's missing
            logger.error(f"POST data: {request.POST}")
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    
    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)


@csrf_exempt
def shop_owner_competition_edit(request, slug):
    if request.session.get('role') != 'shop_owner':
        return JsonResponse({'success': False, 'message': 'Access denied.'}, status=403)
    
    shop_owner = get_shop_owner(request)
    if not shop_owner:
        return JsonResponse({'success': False, 'message': 'Shop owner profile not found.'}, status=403)
    
    competition = get_object_or_404(
        Competition,
        slug=slug,
        shop__in=shop_owner.shops.all(),
        status='rejected'
    )
    
    if request.method == 'GET':
        return JsonResponse({
            'success': True,
            'data': {
                'name': competition.name,
                'description': competition.description,
                'game': str(competition.game.id),
                'platform': str(competition.platform.id),
                'shop': competition.shop.id,
                'scheduled_time': competition.scheduled_time.strftime('%Y-%m-%dT%H:%M'),
                'competition_end_time': competition.competition_end_time.strftime(
                    '%Y-%m-%dT%H:%M') if competition.competition_end_time else '',
                'entry_fee': str(competition.entry_fee),
                'max_participants': competition.max_participants,
                'team_size': competition.team_size,
                'gender_rules': competition.gender_rules,
                'is_pwa_only': competition.is_pwa_only,
                'age_restricted': competition.age_restricted,
                'rules': competition.rules,
                'timeline': competition.timeline,
                'rejection_reason': competition.rejection_reason,
            }
        })
    
    if request.method == 'POST':
        form = CompetitionEditForm(request.POST, instance=competition, shop_owner=shop_owner)
        if form.is_valid():
            try:
                with transaction.atomic():
                    competition = form.save(commit=False)
                    competition.status = 'pending_review'
                    competition.rejection_reason = ''
                    competition.save()

                    try:
                        ActivityLog.objects.create(
                            actor=shop_owner,
                            action_type=ActivityLog.ActionTypes.UPDATE,
                            target=competition,
                            description=f"Resubmitted competition: {competition.name}",
                            meta_data={
                                'shop_id': str(competition.shop_id),
                                'game_id': str(competition.game_id),
                                'status': competition.status,
                            }
                        )
                    except Exception:
                        logger.exception('Failed to log competition resubmission activity')
                    
                    EmailManager.send_competition_resubmitted(competition)
                    EmailManager.send_competition_submission_confirmation(
                        shop_owner=shop_owner,
                        competition=competition,
                        is_resubmission=True
                    )
                
                return JsonResponse({
                    'success': True,
                    'message': f"'{competition.name}' has been resubmitted for admin review.",
                })
            except Exception as e:
                logger.error(f"Competition edit error: {e}")
                return JsonResponse({'success': False, 'message': 'Failed to resubmit. Please try again.'})
        else:
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    
    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)


def shop_owner_competition_detail(request, slug):
    if request.session.get('role') != 'shop_owner':
        messages.error(request, 'Access denied.')
        return redirect('core:home')
    
    shop_owner = get_shop_owner(request)
    if not shop_owner:
        messages.error(request, 'Shop owner profile not found.')
        return redirect('core:home')
    
    competition = get_object_or_404(
        Competition.objects.select_related('game', 'platform', 'shop'),
        slug=slug,
        shop__in=shop_owner.shops.all()
    )
    
    registrations = competition.registrations.filter(
        is_cancelled=False
    ).select_related('gamer').order_by('registered_at')
    
    results = competition.results.select_related('gamer').order_by('rank')
    
    context = {
        **base_site_context(),
        'shop_owner': shop_owner,
        'competition': competition,
        'registrations': registrations,
        'results': results,
        'registered_count': competition.registered_count(),
        'is_shop_owner_of_competition': True,
    }
    return render(request, 'competitions/shop_owner_competition_detail.html', context)


@csrf_exempt
def shop_owner_verify_gamer(request, slug):
    if request.session.get('role') != 'shop_owner':
        return JsonResponse({'success': False, 'message': 'Access denied.'}, status=403)
    
    shop_owner = get_shop_owner(request)
    competition = get_object_or_404(
        Competition,
        slug=slug,
        shop__in=shop_owner.shops.all(),
        status='ongoing'
    )
    
    if request.method == 'POST':
        unique_code = request.POST.get('unique_code', '').strip()
        if not unique_code:
            return JsonResponse({'success': False, 'message': 'No code provided.'}, status=400)
        
        try:
            registration = CompetitionRegistration.objects.get(
                unique_code=unique_code,
                competition=competition,
                is_cancelled=False,
                code_expired=False
            )
        except CompetitionRegistration.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Invalid or already used code. Please check and try again.'
            }, status=404)
        
        if registration.checked_in:
            return JsonResponse({
                'success': False,
                'message': f"{registration.gamer.first_name} {registration.gamer.last_name} is already checked in."
            })
        
        registration.checked_in = True
        registration.checked_in_at = timezone.now()
        registration.code_expired = True
        registration.save()
        
        # Log check-in activity
        from activities.models import Activity
        Activity.objects.create(
            gamer=registration.gamer,
            activity_type=Activity.ActivityTypes.COMPETITION_CHECKEDIN,
            description=f"Checked in for {competition.name}",
            metadata={
                'competition_id': competition.integer_id,
                'competition_name': competition.name,
                'checked_in_at': registration.checked_in_at.isoformat()
            }
        )

        try:
            ActivityLog.objects.create(
                actor=shop_owner,
                gamer=registration.gamer,
                action_type=ActivityLog.ActionTypes.UPDATE,
                target=registration,
                description=f"Verified gamer check-in for {competition.name}",
                meta_data={
                    'competition_id': competition.integer_id,
                    'competition_name': competition.name,
                    'gamer_name': f"{registration.gamer.first_name} {registration.gamer.last_name}",
                    'registration_id': str(registration.id),
                }
            )
        except Exception:
            logger.exception('Failed to log gamer check-in verification activity')
        
        return JsonResponse({
            'success': True,
            'message': f"{registration.gamer.first_name} {registration.gamer.last_name} verified and checked in.",
            'gamer': {
                'id': registration.gamer.id,
                'name': f"{registration.gamer.first_name} {registration.gamer.last_name}",
                'username': registration.gamer.custom_username,
                'checked_in_at': registration.checked_in_at.strftime('%H:%M %p'),
                'profile_picture': registration.gamer.profile_picture.url if registration.gamer.profile_picture else None,
            },
            'registration_id': registration.id
        })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)


@csrf_exempt
def shop_owner_submit_checkins(request, slug):
    if request.session.get('role') != 'shop_owner':
        return JsonResponse({'success': False, 'message': 'Access denied.'}, status=403)
    
    shop_owner = get_shop_owner(request)
    competition = get_object_or_404(
        Competition,
        slug=slug,
        shop__in=shop_owner.shops.all(),
        status='ongoing'
    )
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                competition.status = 'checkin_submitted'
                competition.save()
                
                checked_in_count = competition.registrations.filter(checked_in=True).count()
                registered_count = competition.registered_count()
                EmailManager.send_competition_checkins_submitted(
                    competition=competition,
                    checked_in_count=checked_in_count,
                    registered_count=registered_count
                )

                try:
                    ActivityLog.objects.create(
                        actor=shop_owner,
                        action_type=ActivityLog.ActionTypes.UPDATE,
                        target=competition,
                        description=f"Submitted check-ins for competition: {competition.name}",
                        meta_data={
                            'checked_in_count': checked_in_count,
                            'registered_count': registered_count,
                        }
                    )
                except Exception:
                    logger.exception('Failed to log check-in submission activity')
            
            return JsonResponse({
                'success': True,
                'message': 'Check-in list submitted to admin for review.',
            })
        except Exception as e:
            logger.error(f"Check-in submission error: {e}")
            return JsonResponse({'success': False, 'message': 'Submission failed. Please try again.'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)


@csrf_exempt
def shop_owner_submit_results(request, slug):
    if request.session.get('role') != 'shop_owner':
        return JsonResponse({'success': False, 'message': 'Access denied.'}, status=403)
    
    shop_owner = get_shop_owner(request)
    competition = get_object_or_404(
        Competition,
        slug=slug,
        shop__in=shop_owner.shops.all(),
        status='results_pending'
    )
    
    if request.method == 'POST':
        try:
            import json
            results_data = json.loads(request.POST.get('results', '[]'))
            
            if not results_data:
                return JsonResponse({'success': False, 'message': 'No results provided.'}, status=400)
            
            CompetitionService.submit_results(competition, results_data)

            try:
                ActivityLog.objects.create(
                    actor=shop_owner,
                    action_type=ActivityLog.ActionTypes.UPDATE,
                    target=competition,
                    description=f"Submitted results for competition: {competition.name}",
                    meta_data={
                        'results_count': len(results_data),
                        'prize_type': competition.prize_type,
                    }
                )
            except Exception:
                logger.exception('Failed to log results submission activity')

            try:
                ActivityLog.objects.create(
                    actor=shop_owner,
                    action_type=ActivityLog.ActionTypes.UPDATE,
                    target=competition,
                    description=f"Submitted results for competition: {competition.name}",
                    meta_data={
                        'results_count': len(results_data),
                        'prize_type': competition.prize_type,
                    }
                )
            except Exception:
                logger.exception('Failed to log results submission activity')

            try:
                ActivityLog.objects.create(
                    actor=shop_owner,
                    action_type=ActivityLog.ActionTypes.UPDATE,
                    target=competition,
                    description=f"Submitted results for competition: {competition.name}",
                    meta_data={
                        'results_count': len(results_data),
                        'prize_type': competition.prize_type,
                    }
                )
            except Exception:
                logger.exception('Failed to log results submission activity')
            
            if competition.prize_type == 'points':
                return JsonResponse({
                    'success': True,
                    'message': 'Results submitted. Points have been automatically allocated to gamers.',
                })
            else:
                return JsonResponse({
                    'success': True,
                    'message': 'Results submitted. Awaiting admin verification for prize distribution.',
                })
        
        except Exception as e:
            logger.error(f"Results submission error: {e}")
            return JsonResponse({'success': False, 'message': 'Failed to submit results. Please try again.'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)


# ---------------------------------------------------------------------------
# Admin — Competition Management Views
# ---------------------------------------------------------------------------

@csrf_exempt
def admin_competition_approve(request, integer_id):
    if not (request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser)):
        return JsonResponse({'success': False, 'message': 'Access denied.'}, status=403)
    
    competition = get_object_or_404(Competition, integer_id=integer_id, status='pending_review')
    
    if request.method == 'POST':
        form = CompetitionApprovalForm(request.POST, instance=competition)
        if form.is_valid():
            try:
                CompetitionService.approve_competition(
                    competition,
                    form,
                    performed_by_label=getattr(request.user, 'username', ''),
                )
                return JsonResponse({
                    'success': True,
                    'message': f"'{competition.name}' has been approved and is now live.",
                })
            except Exception as e:
                logger.error(f"Competition approval error: {e}")
                return JsonResponse({'success': False, 'message': 'Approval failed. Please try again.'})
        else:
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    
    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)


@csrf_exempt
def admin_competition_reject(request, integer_id):
    if not (request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser)):
        return JsonResponse({'success': False, 'message': 'Access denied.'}, status=403)
    
    competition = get_object_or_404(Competition, integer_id=integer_id, status='pending_review')
    
    if request.method == 'POST':
        form = CompetitionRejectionForm(request.POST, instance=competition)
        if form.is_valid():
            try:
                CompetitionService.reject_competition(
                    competition,
                    form,
                    performed_by_label=getattr(request.user, 'username', ''),
                )
                return JsonResponse({
                    'success': True,
                    'message': f"'{competition.name}' has been rejected. Shop owner has been notified.",
                })
            except Exception as e:
                logger.error(f"Competition rejection error: {e}")
                return JsonResponse({'success': False, 'message': 'Rejection failed. Please try again.'})
        else:
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    
    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)


@csrf_exempt
def admin_confirm_checkins(request, integer_id):
    if not (request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser)):
        return JsonResponse({'success': False, 'message': 'Access denied.'}, status=403)
    
    competition = get_object_or_404(Competition, integer_id=integer_id, status='checkin_submitted')
    
    if request.method == 'POST':
        try:
            CompetitionService.confirm_checkins(
                competition,
                performed_by_label=getattr(request.user, 'username', ''),
            )
            return JsonResponse({
                'success': True,
                'message': 'Check-ins confirmed. Shop owner notified to submit results.',
            })
        except Exception as e:
            logger.error(f"Check-in confirmation error: {e}")
            return JsonResponse({'success': False, 'message': 'Confirmation failed. Please try again.'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)


@csrf_exempt
def admin_verify_results(request, integer_id):
    if not (request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser)):
        return JsonResponse({'success': False, 'message': 'Access denied.'}, status=403)
    
    competition = get_object_or_404(
        Competition,
        integer_id=integer_id,
        status__in=['pending_prize_verification', 'completed']
    )
    
    if request.method == 'POST':
        try:
            CompetitionService.verify_results(
                competition,
                performed_by_label=getattr(request.user, 'username', ''),
            )
            return JsonResponse({
                'success': True,
                'message': f"Results for '{competition.name}' verified and published.",
            })
        except Exception as e:
            logger.error(f"Results verification error: {e}")
            return JsonResponse({'success': False, 'message': 'Verification failed. Please try again.'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)


def admin_competition_detail_data(request, integer_id):
    if not (request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser)):
        return JsonResponse({'success': False, 'message': 'Access denied.'}, status=403)
    
    competition = get_object_or_404(
        Competition.objects.select_related('game', 'platform', 'shop', 'created_by'),
        integer_id=integer_id
    )
    
    registrations = competition.registrations.filter(
        is_cancelled=False
    ).select_related('gamer').order_by('registered_at')
    
    results = competition.results.select_related('gamer').order_by('rank')
    
    return JsonResponse({
        'success': True,
        'data': {
            'integer_id': competition.integer_id,
            'name': competition.name,
            'description': competition.description,
            'game': competition.game.name,
            'platform': competition.platform.name,
            'shop': competition.shop.name,
            'scheduled_time': competition.scheduled_time.strftime('%Y-%m-%d %H:%M'),
            'competition_end_time': competition.competition_end_time.strftime(
                '%Y-%m-%d %H:%M') if competition.competition_end_time else None,
            'entry_fee': str(competition.entry_fee),
            'max_participants': competition.max_participants,
            'registered_count': competition.registered_count(),
            'age_restricted': competition.age_restricted,
            'rules': competition.get_full_rules(),
            'timeline': competition.timeline,
            'status': competition.status,
            'status_display': competition.get_status_display(),
            'prize_type': competition.prize_type,
            'points_1st': competition.points_1st,
            'points_2nd': competition.points_2nd,
            'points_3rd': competition.points_3rd,
            'points_4_to_10': competition.points_4_to_10,
            'points_beyond_10': competition.points_beyond_10,
            'prize_money_total': str(competition.prize_money_total) if competition.prize_money_total else None,
            'prize_money_1st_pct': competition.prize_money_1st_pct,
            'prize_money_2nd_pct': competition.prize_money_2nd_pct,
            'prize_money_3rd_pct': competition.prize_money_3rd_pct,
            'prize_gift_description': competition.prize_gift_description,
            'registration_opens_at': competition.registration_opens_at.strftime(
                '%Y-%m-%d %H:%M') if competition.registration_opens_at else None,
            'registration_closes_at': competition.registration_closes_at.strftime(
                '%Y-%m-%d %H:%M') if competition.registration_closes_at else None,
            'rejection_reason': competition.rejection_reason,
            'created_by': f"{competition.created_by.first_name} {competition.created_by.last_name}",
            'approved_at': competition.approved_at.strftime('%Y-%m-%d %H:%M') if competition.approved_at else None,
            'registrations': [
                {
                    'gamer': f"{r.gamer.first_name} {r.gamer.last_name}",
                    'username': r.gamer.custom_username,
                    'registered_at': r.registered_at.strftime('%Y-%m-%d %H:%M'),
                    'checked_in': r.checked_in,
                    'checked_in_at': r.checked_in_at.strftime('%Y-%m-%d %H:%M') if r.checked_in_at else None,
                    'participation_hours': r.participation_hours(),
                }
                for r in registrations
            ],
            'results': [
                {
                    'gamer': f"{r.gamer.first_name} {r.gamer.last_name}",
                    'username': r.gamer.custom_username,
                    'rank': r.rank,
                    'points_awarded': r.points_awarded,
                    'is_no_show': r.is_no_show,
                    'is_win': r.is_win(),
                    'verified': r.verified,
                }
                for r in results
            ],
        }
    })