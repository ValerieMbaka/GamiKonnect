from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from datetime import timedelta
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
import json
import logging
from django.db import transaction

from core.email_service import EmailManager

# Model imports
from core.models import ProjectDetail, SiteStyle
from games.models import Game, Genre, Platform, PlatformCategory
from accounts.models import Gamer, ShopOwner, Account
from activities.models import ActivityLog
from competitions.models import Competition, CompetitionAuditLog
from shops.models import Shop
from competitions.models import Competition, CompetitionRegistration, CompetitionResult
from competitions.forms import CompetitionApprovalForm, CompetitionRejectionForm, CompetitionAdminCreateForm
from competitions.scheduler import schedule_competition_jobs
from competitions.services import CompetitionService
from activities.services import ActivityFeedService

# Imports for custom logic
from .decorators import admin_required
from .forms import AdminUserUpdateForm, AdminProfileUpdateForm, ProjectDetailForm, SiteStyleForm, GameForm


logger = logging.getLogger(__name__)


# Admin Authentication Views
def admin_login(request):
    if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
        return redirect('admin_panel:dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if user.is_staff or user.is_superuser:
                login(request, user)
                messages.success(request, f"Welcome to the Admin Panel, {user.username}.")
                return redirect('admin_panel:dashboard')
            else:
                messages.error(request, "Access denied. Authorized personnel only.")
                return redirect('admin_panel:login')
        else:
            messages.error(request, "Invalid username or password. Please try again.")
            return redirect('admin_panel:login')
    
    return render(request, 'admin_panel/base/admin_login.html')


@admin_required
def admin_logout(request):
    logout(request)
    messages.info(request, "You have been securely logged out of the Admin Panel.")
    return redirect('admin_panel:login')


# Admin Management & Profile Views
@admin_required
def admin_dashboard(request):
    # KPI Metrics
    total_gamers = Gamer.objects.count()
    total_competitions = Competition.objects.count()
    
    # Revenue/Earnings (Placeholder logic as actual transaction model is not verified)
    # For now, let's assume earnings might be tied to something, but we'll use a placeholder or 0
    total_earnings = 0 # Placeholder for now
    
    # Recent Activity (Last 5 logs)
    recent_activity_feed = ActivityFeedService.get_admin_feed(limit=5)
    
    # Upcoming Events (Competitions starting soon)
    upcoming_events = Competition.objects.filter(
        scheduled_time__gte=timezone.now()
    ).order_by('scheduled_time')[:5]
    
    # Top Players (Based on points)
    top_players = Gamer.objects.all().order_by('-points')[:5]
    
    # Site Activity Chart Data (Last 7 days)
    today = timezone.now().date()
    activity_labels = []
    activity_data = []
    
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        count = ActivityLog.objects.filter(timestamp__date=day).count()
        activity_labels.append(day.strftime('%a'))
        activity_data.append(count)
        
    # Revenue Chart Data (Placeholder)
    revenue_data = [5400, 3200, 2850, 1000] # Mock data until revenue model is confirmed
    
    # APScheduler Jobs Monitoring
    from competitions.scheduler import get_scheduler
    scheduler = get_scheduler()
    scheduled_jobs = []
    if scheduler:
        for job in scheduler.get_jobs():
            scheduled_jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run': job.next_run_time,
                'trigger': str(job.trigger)
            })

    context = {
        'total_gamers': total_gamers,
        'total_competitions': total_competitions,
        'total_earnings': total_earnings,
        'recent_activity_feed': recent_activity_feed,
        'upcoming_events': upcoming_events,
        'top_players': top_players,
        'scheduled_jobs': scheduled_jobs,
        'today': timezone.now(),
        'chart_data': {
            'activity_labels': activity_labels,
            'activity_data': activity_data,
            'revenue_data': revenue_data,
        }
    }
    return render(request, 'admin_panel/base/admin_dashboard.html', context)


@admin_required
def admin_profile(request):
    if request.method == 'POST':
        u_form = AdminUserUpdateForm(request.POST, instance=request.user)
        p_form = AdminProfileUpdateForm(request.POST, request.FILES, instance=request.user.admin_profile)
        
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            avatar_url = request.user.admin_profile.avatar.url if request.user.admin_profile.avatar else None
            return JsonResponse({
                'success': True,
                'message': 'Your profile has been successfully updated.',
                'data': {
                    'first_name': request.user.first_name,
                    'last_name': request.user.last_name,
                    'email': request.user.email,
                    'job_title': request.user.admin_profile.job_title,
                    'timezone': request.user.admin_profile.timezone,
                    'avatar_url': avatar_url
                }
            })
        else:
            errors = dict(u_form.errors)
            errors.update(dict(p_form.errors))
            return JsonResponse({'success': False, 'errors': errors}, status=400)
    
    u_form = AdminUserUpdateForm(instance=request.user)
    p_form = AdminProfileUpdateForm(instance=request.user.admin_profile)
    password_form = PasswordChangeForm(request.user)
    
    context = {
        'u_form': u_form,
        'p_form': p_form,
        'password_form': password_form,
    }
    return render(request, 'admin_panel/base/admin_profile.html', context)


@admin_required
def admin_change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            return JsonResponse({'success': True, 'message': 'Your password was securely rotated.'})
        else:
            return JsonResponse({'success': False, 'errors': dict(form.errors)}, status=400)
    return JsonResponse({'error': 'Invalid request method.'}, status=405)


@admin_required
def admin_site_settings(request):
    project_detail = ProjectDetail.objects.filter(is_active=True).first() or ProjectDetail()
    site_style = SiteStyle.get_active() or SiteStyle()
    
    if request.method == 'POST':
        project_form = ProjectDetailForm(request.POST, request.FILES, instance=project_detail)
        style_form = SiteStyleForm(request.POST, instance=site_style)
        
        if project_form.is_valid() and style_form.is_valid():
            p_detail = project_form.save(commit=False)
            p_detail.is_active = True
            p_detail.save()
            
            s_style = style_form.save(commit=False)
            s_style.pk = None
            s_style.save()
            
            messages.success(request, 'Global site settings updated successfully.')
            return redirect('admin_panel:site_settings')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        project_form = ProjectDetailForm(instance=project_detail)
        style_form = SiteStyleForm(instance=site_style)
    
    context = {
        'project_form': project_form,
        'style_form': style_form,
        'current_logo': project_detail.logo if project_detail.logo else None
    }
    return render(request, 'admin_panel/settings/site_settings.html', context)


# Game Management Views
@admin_required
def admin_game_list(request):
    # Start with all games
    games_list = Game.objects.all().order_by('-created_at')
    
    # Filtering Logic
    query = request.GET.get('q')
    genre_id = request.GET.get('genre')
    platform_id = request.GET.get('platform')
    status = request.GET.get('status')
    
    if query:
        games_list = games_list.filter(
            Q(name__icontains=query) | Q(integer_id__icontains=query)
        )
    if genre_id:
        games_list = games_list.filter(genres__id=genre_id)
    if platform_id:
        games_list = games_list.filter(supported_platforms__id=platform_id)
    
    if status == 'active':
        games_list = games_list.filter(is_active=True)
    elif status == 'inactive':
        games_list = games_list.filter(is_active=False)
    elif status == 'verified':
        games_list = games_list.filter(is_verified=True)
    elif status == 'unverified':
        games_list = games_list.filter(is_verified=False)
    
    # Pagination
    paginator = Paginator(games_list, 15)
    page_number = request.GET.get('page')
    games = paginator.get_page(page_number)
    
    # KPI Calculations
    total_games = Game.objects.count()
    total_categories = PlatformCategory.objects.count()
    total_platforms = Platform.objects.count()
    total_genres = Genre.objects.count()
    
    seven_days_ago = timezone.now() - timedelta(days=7)
    new_games_this_week = Game.objects.filter(created_at__gte=seven_days_ago).count()
    new_platforms_this_week = Platform.objects.filter(created_at__gte=seven_days_ago).count()
    
    context = {
        'games': games,
        'all_genres': Genre.objects.all().order_by('name'),
        'all_platforms': Platform.objects.all().order_by('name'),
        
        # KPI Context Variables
        'total_games': total_games,
        'total_categories': total_categories,
        'total_platforms': total_platforms,
        'total_genres': total_genres,
        'new_games_this_week': new_games_this_week,
        'new_platforms_this_week': new_platforms_this_week,
        'form': GameForm()
    }
    return render(request, 'admin_panel/games/admin_games.html', context)


@admin_required
def admin_game_save(request):
    if request.method == 'POST':
        game_id = request.POST.get('game_id')
        if game_id:
            game = get_object_or_404(Game, integer_id=game_id)
            form = GameForm(request.POST, request.FILES, instance=game)
        else:
            form = GameForm(request.POST, request.FILES)
        
        if form.is_valid():
            game = form.save()
            return JsonResponse({'success': True, 'message': f"Game '{game.name}' saved successfully."})
        else:
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    return JsonResponse({'error': 'Invalid request'}, status=400)


@admin_required
def admin_game_detail(request, game_id):
    game = get_object_or_404(Game, integer_id=game_id)
    return JsonResponse({
        'success': True,
        'data': {
            'game_id': game.integer_id,
            'name': game.name,
            'description': game.description,
            'is_verified': game.is_verified,
            'is_active': game.is_active,
            'genres': list(game.genres.values_list('id', flat=True)),
            'supported_platforms': list(game.supported_platforms.values_list('id', flat=True))
        }
    })


@admin_required
def admin_game_delete(request, game_id):
    if request.method == 'POST':
        game = get_object_or_404(Game, integer_id=game_id)
        name = game.name
        game.delete()
        return JsonResponse({'success': True, 'message': f"Game '{name}' deleted."})
    return JsonResponse({'error': 'Invalid request'}, status=400)


@admin_required
def admin_game_toggle_status(request, game_id):
    if request.method == 'POST':
        game = get_object_or_404(Game, integer_id=game_id)
        game.is_active = not game.is_active
        game.save()
        status_text = "Activated" if game.is_active else "Deactivated"
        return JsonResponse({'success': True, 'message': f"Game {status_text}."})
    return JsonResponse({'error': 'Invalid request'}, status=400)



@admin_required
def admin_competition_create(request):
    """Allows admin to create a competition directly (already approved, with all fields)."""
    if request.method == 'POST':
        form = CompetitionAdminCreateForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    competition = form.save(commit=False)
                    # Set the creator and status to 'approved' (admin-created competitions skip review)
                    competition.created_by = request.user
                    competition.status = 'approved'
                    competition.approved_at = timezone.now()
                    competition.save()

                    # Audit the admin-created competition
                    try:
                        CompetitionAuditLog.objects.create(
                            competition=competition,
                            action='approve',
                            performed_by_label=request.user.get_username(),
                            details='Competition created and approved by admin.'
                        )
                    except Exception:
                        logger.exception('Failed to create audit log for admin-created competition')

                    # Schedule all the background jobs for status transitions
                    schedule_competition_jobs(competition)

                    # Notify shop owner that their competition has been created by admin
                    EmailManager.send_competition_approved(competition)

                messages.success(request, f"Competition '{competition.name}' created and scheduled successfully.")
                return redirect('admin_panel:competition_detail', competition_id=competition.integer_id)
            except Exception as e:
                logger.error(f"Competition creation error: {e}")
                messages.error(request, f"Error creating competition: {str(e)}")
    else:
        form = CompetitionAdminCreateForm()
    
    context = {
        'form': form,
        'page_title': 'Create Competition',
        'all_shops': Shop.objects.filter(is_approved=True).order_by('name'),
    }
    return render(request, 'admin_panel/competitions/admin_competition_create.html', context)


@admin_required
def admin_competition_list(request):
    competitions_list = Competition.objects.all().select_related(
        'game', 'platform', 'shop', 'created_by'
    ).order_by('-created_at')
    
    # Filters
    query = request.GET.get('q')
    status = request.GET.get('status')
    prize_type = request.GET.get('prize_type')
    shop_id = request.GET.get('shop')
    
    if query:
        competitions_list = competitions_list.filter(
            Q(name__icontains=query) |
            Q(game__name__icontains=query) |
            Q(shop__name__icontains=query)
        )
    if status:
        competitions_list = competitions_list.filter(status=status)
    if prize_type:
        competitions_list = competitions_list.filter(prize_type=prize_type)
    if shop_id:
        competitions_list = competitions_list.filter(shop__id=shop_id)
    
    # Pagination
    paginator = Paginator(competitions_list, 20)
    page_number = request.GET.get('page')
    competitions = paginator.get_page(page_number)
    
    # KPIs
    seven_days_ago = timezone.now() - timedelta(days=7)
    
    context = {
        'competitions': competitions,
        'all_shops': Shop.objects.filter(is_approved=True).order_by('name'),
        'total_competitions': Competition.objects.count(),
        'pending_review': Competition.objects.filter(status='pending_review').count(),
        'live_competitions': Competition.objects.filter(
            status__in=['approved', 'registration_open', 'registration_closed', 'ongoing']
        ).count(),
        'completed_competitions': Competition.objects.filter(status='completed').count(),
        'new_this_week': Competition.objects.filter(created_at__gte=seven_days_ago).count(),
    }
    return render(request, 'admin_panel/competitions/admin_competitions.html', context)


@admin_required
def admin_competition_detail(request, competition_id):
    competition = get_object_or_404(
        Competition.objects.select_related('game', 'platform', 'shop', 'created_by'),
        integer_id=competition_id
    )
    
    registrations = competition.registrations.filter(
        is_cancelled=False
    ).select_related('gamer').order_by('registered_at')
    
    results = competition.results.select_related('gamer').order_by('rank')
    
    checked_in_count = registrations.filter(checked_in=True).count()
    no_show_count = registrations.count() - checked_in_count
    
    context = {
        'competition': competition,
        'registrations': registrations,
        'results': results,
        'registered_count': competition.registered_count(),
        'checked_in_count': checked_in_count,
        'no_show_count': no_show_count,
    }
    return render(request, 'admin_panel/competitions/admin_competition_detail.html', context)


@admin_required
def admin_competition_approve(request, competition_id):
    competition = get_object_or_404(Competition, integer_id=competition_id, status='pending_review')
    
    if request.method == 'POST':
        # Support JSON from inline AJAX (quick-approve) as well as normal form posts
        if request.content_type == 'application/json':
            # Quick approve: use existing values from instance
            form = CompetitionApprovalForm(instance=competition)
        else:
            form = CompetitionApprovalForm(request.POST, instance=competition)

        if form.is_valid():
            try:
                CompetitionService.approve_competition(
                    competition,
                    form,
                    performed_by_label=request.user.get_username(),
                )
                return JsonResponse({
                    'success': True,
                    'message': f"'{competition.name}' approved and is now live.",
                })
            except Exception as e:
                logger.error(f"Competition approval error: {e}")
                return JsonResponse({'success': False, 'message': 'Approval failed. Please try again.'})
        else:
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    
    return JsonResponse({'success': False, 'message': 'Invalid request.'}, status=405)


@admin_required
def admin_competition_reject(request, competition_id):
    competition = get_object_or_404(Competition, integer_id=competition_id, status='pending_review')
    
    if request.method == 'POST':
        # Support JSON from inline AJAX (quick-reject) and normal form posts
        if request.content_type == 'application/json':
            import json as _json
            try:
                payload = _json.loads(request.body.decode('utf-8') or '{}')
            except Exception:
                payload = {}
            form = CompetitionRejectionForm(payload, instance=competition)
        else:
            form = CompetitionRejectionForm(request.POST, instance=competition)

        if form.is_valid():
            try:
                CompetitionService.reject_competition(
                    competition,
                    form,
                    performed_by_label=request.user.get_username(),
                )
                return JsonResponse({
                    'success': True,
                    'message': f"'{competition.name}' rejected. Shop owner notified.",
                })
            except Exception as e:
                logger.error(f"Competition rejection error: {e}")
                return JsonResponse({'success': False, 'message': 'Rejection failed. Please try again.'})
        else:
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    
    return JsonResponse({'success': False, 'message': 'Invalid request.'}, status=405)


@admin_required
def admin_confirm_checkins(request, competition_id):
    competition = get_object_or_404(Competition, integer_id=competition_id, status='checkin_submitted')
    
    if request.method == 'POST':
        try:
            CompetitionService.confirm_checkins(
                competition,
                performed_by_label=request.user.get_username(),
            )
            return JsonResponse({
                'success': True,
                'message': 'Check-ins confirmed. Shop owner notified to submit results.',
            })
        except Exception as e:
            logger.error(f"Confirm checkins error: {e}")
            return JsonResponse({'success': False, 'message': 'Failed. Please try again.'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request.'}, status=405)


@admin_required
def admin_verify_results(request, competition_id):
    competition = get_object_or_404(
        Competition,
        integer_id=competition_id,
        status__in=['pending_prize_verification', 'completed']
    )
    
    if request.method == 'POST':
        try:
            CompetitionService.verify_results(
                competition,
                performed_by_label=request.user.get_username(),
            )
            return JsonResponse({
                'success': True,
                'message': f"Results verified and published for '{competition.name}'.",
            })
        except Exception as e:
            logger.error(f"Verify results error: {e}")
            return JsonResponse({'success': False, 'message': 'Verification failed. Please try again.'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request.'}, status=405)
