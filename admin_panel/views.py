from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.http import HttpResponse, JsonResponse

# Model imports
from core.models import ProjectDetail, SiteStyle
from games.models import Game

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
    # Handles the display of the profile page and AJAX POST requests for updates.
    if request.method == 'POST':
        u_form = AdminUserUpdateForm(request.POST, instance=request.user)
        p_form = AdminProfileUpdateForm(request.POST, request.FILES, instance=request.user.admin_profile)
        
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            
            # Return fresh data so JavaScript can update the UI instantly
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
            # Merge errors from both forms and send them back to the modal
            errors = dict(u_form.errors)
            errors.update(dict(p_form.errors))
            return JsonResponse({'success': False, 'errors': errors}, status=400)
    
    # GET Request: Render the page with empty forms for the modals
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
    # AJAX endpoint for secure password rotation via modal.
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Prevents logging the admin out
            return JsonResponse({
                'success': True,
                'message': 'Your password was securely rotated.'
            })
        else:
            return JsonResponse({'success': False, 'errors': dict(form.errors)}, status=400)
    
    return JsonResponse({'error': 'Invalid request method.'}, status=405)


@admin_required
def admin_site_settings(request):
    # Manages global platform identity and theme styling.
    # Fetch the active instances, or instantiate empty ones if the DB is blank
    project_detail = ProjectDetail.objects.filter(is_active=True).first() or ProjectDetail()
    site_style = SiteStyle.get_active() or SiteStyle()
    
    if request.method == 'POST':
        project_form = ProjectDetailForm(request.POST, request.FILES, instance=project_detail)
        style_form = SiteStyleForm(request.POST, instance=site_style)
        
        if project_form.is_valid() and style_form.is_valid():
            # Save Project Details
            p_detail = project_form.save(commit=False)
            p_detail.is_active = True
            p_detail.save()
            
            # Save Site Style
            s_style = style_form.save(commit=False)
            s_style.pk = None  # Forces a new object to track historical changes based on updated_at
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


@admin_required
def admin_game_list(request):
    """Displays the main Game Database table."""
    games = Game.objects.all().order_by('-created_at')
    
    context = {
        'games': games,
    }
    # Updated Template Path
    return render(request, 'admin_panel/games/admin_game_list.html', context)


@admin_required
def admin_game_create(request):
    """Handles the creation of a new game."""
    if request.method == 'POST':
        form = GameForm(request.POST, request.FILES)
        if form.is_valid():
            game = form.save()
            messages.success(request, f'Game "{game.name}" was added successfully.')
            return redirect('admin_panel:game_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = GameForm()
    
    context = {
        'form': form,
        'page_title': 'Add New Game',
        'is_edit': False
    }
    # Updated Template Path
    return render(request, 'admin_panel/games/admin_game_form.html', context)


@admin_required
def admin_game_edit(request, game_id):
    """Handles updating an existing game."""
    game = get_object_or_404(Game, id=game_id)
    
    if request.method == 'POST':
        form = GameForm(request.POST, request.FILES, instance=game)
        if form.is_valid():
            form.save()
            messages.success(request, f'Game "{game.name}" was updated successfully.')
            return redirect('admin_panel:game_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = GameForm(instance=game)
    
    context = {
        'form': form,
        'game': game,
        'page_title': 'Edit Game',
        'is_edit': True
    }
    # Updated Template Path
    return render(request, 'admin_panel/games/admin_game_form.html', context)


@admin_required
def admin_game_delete(request, game_id):
    """Secure endpoint to delete a game."""
    if request.method == 'POST':
        game = get_object_or_404(Game, id=game_id)
        game_name = game.name
        game.delete()
        messages.success(request, f'Game "{game_name}" was permanently deleted.')
    return redirect('admin_panel:game_list')