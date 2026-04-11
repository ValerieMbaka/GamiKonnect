from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from datetime import timedelta
from django.core.paginator import Paginator
from django.db.models import Q

# Model imports
from core.models import ProjectDetail, SiteStyle
from games.models import Game, Genre, Platform, PlatformCategory

# Imports for custom logic
from .decorators import admin_required
from .forms import AdminUserUpdateForm, AdminProfileUpdateForm, ProjectDetailForm, SiteStyleForm, GameForm


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
    return render(request, 'admin_panel/base/admin_dashboard.html')


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