from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.http import HttpResponse

# Import security decorator
from .decorators import admin_required


# Admin Authentication Views
def admin_login(request):
    # Handles the admin panel authentication flow
    # If an authorized admin is already logged in, skip the login page
    if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
        return redirect('admin_panel:dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # Attempt to authenticate via Django's built-in system
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # Verify the authenticated user has the correct clearance
            if user.is_staff or user.is_superuser:
                login(request, user)
                messages.success(request, f"Welcome to the Admin Dashboard, {user.username}.")
                return redirect('admin_panel:dashboard')
            else:
                # Valid credentials, but lacks admin clearance
                messages.error(request, "Access denied. Authorized personnel only.")
                return redirect('admin_panel:login')
        else:
            # Invalid credentials
            messages.error(request, "Invalid username or password. Please try again.")
            return redirect('admin_panel:login')
    
    return render(request, 'admin_panel/base/admin_login.html')


# Admin Management Views
@admin_required
def admin_dashboard(request):
    # The main landing page after a successful admin login.
    return render(request, 'admin_panel/base/admin_dashboard.html')