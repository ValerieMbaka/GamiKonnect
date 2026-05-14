"""
View utilities for accounts app - DRY helpers for role-based access control and user retrieval.
Consolidates repeated patterns from accounts/views.py for better maintainability.
"""

from functools import wraps
from django.shortcuts import redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from .models import Gamer, ShopOwner


# ============================================================================
# User Retrieval Helpers
# ============================================================================

def get_current_gamer(request):
    """
    Get the current logged-in Gamer from session, or None.
    Safe wrapper that handles missing user_id.
    """
    if request.session.get('role') != 'gamer':
        return None
    try:
        return Gamer.objects.get(id=request.session['user_id'])
    except Gamer.DoesNotExist:
        return None


def get_current_shop_owner(request):
    """
    Get the current logged-in ShopOwner from session, or None.
    Safe wrapper that handles missing user_id.
    """
    if request.session.get('role') != 'shop_owner':
        return None
    try:
        return ShopOwner.objects.get(id=request.session['user_id'])
    except ShopOwner.DoesNotExist:
        return None


def get_current_user(request):
    """
    Get the current user (Gamer or ShopOwner) based on session role.
    Returns (user_object, role) tuple or (None, None) if not authenticated.
    """
    role = request.session.get('role')
    user_id = request.session.get('user_id')
    
    if not user_id or role not in ['gamer', 'shop_owner']:
        return None, None
    
    try:
        if role == 'gamer':
            user = Gamer.objects.get(id=user_id)
        else:
            user = ShopOwner.objects.get(id=user_id)
        return user, role
    except (Gamer.DoesNotExist, ShopOwner.DoesNotExist):
        return None, None


# ============================================================================
# Role-Based Access Control Decorators
# ============================================================================

def require_gamer_role(view_func):
    """
    Decorator to restrict view to gamers only.
    Redirects with error message if user is not a gamer.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.session.get('role') != 'gamer':
            messages.error(request, 'Access denied.')
            return redirect('core:home')
        return view_func(request, *args, **kwargs)
    return wrapper


def require_shop_owner_role(view_func):
    """
    Decorator to restrict view to shop owners only.
    Redirects with error message if user is not a shop owner.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.session.get('role') != 'shop_owner':
            messages.error(request, 'Access denied.')
            return redirect('core:home')
        return view_func(request, *args, **kwargs)
    return wrapper


def require_authenticated(view_func):
    """
    Decorator to require user to be logged in (either gamer or shop owner).
    Redirects to home with error message if not authenticated.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        role = request.session.get('role')
        user_id = request.session.get('user_id')
        
        if not user_id or role not in ['gamer', 'shop_owner']:
            messages.error(request, 'Access denied.')
            return redirect('core:home')
        return view_func(request, *args, **kwargs)
    return wrapper


def require_gamer_or_shop_owner(view_func):
    """
    Decorator to allow both gamers and shop owners.
    Alias for require_authenticated with clearer name.
    """
    return require_authenticated(view_func)


# ============================================================================
# JSON Response Helpers (for AJAX endpoints)
# ============================================================================

def require_gamer_json(view_func):
    """
    Decorator for AJAX endpoints that require gamer role.
    Returns JSON error response instead of redirect.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.session.get('role') not in ['gamer', 'shop_owner']:
            return JsonResponse(
                {'success': False, 'message': 'You must be logged in to perform this action.'},
                status=403
            )
        
        gamer = get_current_gamer(request)
        if not gamer:
            return JsonResponse(
                {'success': False, 'message': 'Gamer profile not found.'},
                status=403
            )
        
        return view_func(request, *args, **kwargs)
    return wrapper


def require_shop_owner_json(view_func):
    """
    Decorator for AJAX endpoints that require shop owner role.
    Returns JSON error response instead of redirect.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.session.get('role') != 'shop_owner':
            return JsonResponse(
                {'success': False, 'message': 'Access denied.'},
                status=403
            )
        return view_func(request, *args, **kwargs)
    return wrapper


# ============================================================================
# Validation Helpers
# ============================================================================

def is_authenticated(request):
    """Check if user is authenticated (has valid session)."""
    return bool(
        request.session.get('user_id') and 
        request.session.get('role') in ['gamer', 'shop_owner']
    )


def is_gamer(request):
    """Check if current user is a gamer."""
    return request.session.get('role') == 'gamer'


def is_shop_owner(request):
    """Check if current user is a shop owner."""
    return request.session.get('role') == 'shop_owner'
