from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.http import HttpResponse, JsonResponse

# Imports for custom logic
from .decorators import admin_required
from .forms import AdminUserUpdateForm, AdminProfileUpdateForm


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
    return render(request, 'admin_panel/base/includes/admin_base.html')


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