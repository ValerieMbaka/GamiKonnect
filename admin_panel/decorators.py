from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps


def admin_required(view_func):
    # Checks that the user is logged in and is either a superuser or staff
    
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Logged in and have the right clearance
        if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
            return view_func(request, *args, **kwargs)
        
        # Logged in, but are a regular user
        if request.user.is_authenticated:
            messages.error(request, "Access Denied! Authorized personnel only.")
        
        # Redirect everyone else back to login
        return redirect('admin_panel:login')
    
    return _wrapped_view