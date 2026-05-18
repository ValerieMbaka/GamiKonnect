from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
import json
from .models import Gamer


class RoleAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        return response
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        # Skip middleware for static files and media
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return None
        
        # Resolve current route name for accurate checks
        resolver_match = getattr(request, 'resolver_match', None)
        current_name = None
        if resolver_match:
            if resolver_match.app_name:
                current_name = f"{resolver_match.app_name}:{resolver_match.url_name}"
            else:
                current_name = resolver_match.url_name
        
        """
        Always allow access to Django admin URLs (including its own login)
        This prevents the custom auth gating from hijacking /admin/ flows.
        """
        # Always allow access to Django admin and our Custom Admin Panel
        if resolver_match and resolver_match.app_name in ['admin', 'admin_panel']:
            return None
        if request.path.startswith('/admin/') or request.path.startswith('/admin-panel/'):
            return None
        
        if resolver_match and resolver_match.app_name == 'admin':
            return None
        if request.path.startswith('/admin/'):
            return None
        
        """ Allow access to the custom admin_panel app so staff-only checks in those views can handle
        authentication/authorization. This prevents the session-based role gating from redirecting to
        the gamer/shop-owner login when staff want to access admin_panel.
        """
        if resolver_match and resolver_match.app_name == 'admin_panel':
            return None
        if request.path.startswith('/admin_panel/'):
            return None
        
        # Central role-based route configuration
        # Users who are not logged in can always access these views
        allowed_anonymous = {
            'core:home',
            'competitions:list',
            'competitions:detail',
            
            # Core legal pages
            'core:cookie_policy',
            'core:terms_conditions',
            'core:privacy_policy',
            
            # Core support/help pages
            'core:faqs',
            'core:contact_us',
            'core:help_center',
            'core:help_creating_account',
            'core:help_platform_navigation',
            'core:help_first_tournament',
            'accounts:login',
            'accounts:session_login',
            'accounts:register',
            'accounts:register_submit',
            'accounts:select_role',
            'accounts:verify_email',
            'accounts:resend_verification',
            
            # Admin Email Quick Actions
            'accounts:quick_approve_shop',
            'accounts:quick_reject_shop',
        }
        
        # Explicit gamer and shop-owner URL names
        gamer_allowed_names = {
            'accounts:gamer_dashboard',
            'accounts:gamer_games',
            'accounts:gamer_profile_edit',
            'accounts:gamer_settings',
            'accounts:gamer_profile_completion',
            'accounts:check_username',
            'accounts:gamer_public_profile',
            'accounts:gamer_public_profile_username',
            'games:get_profile_form_data',
            'competitions:list',
            'competitions:detail',
            'competitions:register',
            'competitions:check_registration',
            'competitions:gamer_competitions',
            'competitions:gamer_result',
        }
        
        shop_owner_allowed_names = {
            'accounts:shop_owner_dashboard',
            'accounts:shop_owner_profile',
            'accounts:shop_owner_profile_edit',
            'accounts:shop_owner_settings',
            'accounts:shop_owner_shop_detail',
            'accounts:edit_shop',
            'accounts:shop_owner_venues',
            'competitions:shop_owner_competitions',
            'competitions:shop_owner_detail',
            'competitions:shop_owner_create',
            'competitions:shop_owner_edit',
            'competitions:shop_owner_verify_gamer',
            'competitions:shop_owner_submit_checkins',
            'competitions:shop_owner_submit_results',
            'accounts:submit_competition_result',
            'accounts:submit_competition_result_no_pk',
        }
        
        # Views allowed for both authenticated gamers and shop owners
        common_authenticated_allowed = {
            'accounts:create_shop',
        }
        
        role_allowed_map = {
            'gamer': gamer_allowed_names,
            'shop_owner': shop_owner_allowed_names,
        }
        
        if current_name in allowed_anonymous:
            return None
        
        # Check if user is authenticated
        user_id = request.session.get('user_id')
        if not user_id:
            # Preserve intent (next URL) for any protected route
            # Use full path so query strings are retained
            try:
                request.session['post_login_redirect'] = request.get_full_path()
            except Exception:
                # Best effort only
                pass
            
            # Show toast prompting login
            if current_name not in allowed_anonymous and current_name != 'core:home':
                messages.warning(request, 'Login to access this page')
                return redirect('accounts:login')
            return None
        
        # Role-based access control using explicit route-name allowlists
        user_role = request.session.get('role')
        
        # Allow common authenticated views for both roles
        if current_name in common_authenticated_allowed:
            return None
        
        # If a gamer-only view is requested by a non-gamer, block it
        if current_name in gamer_allowed_names and user_role != 'gamer':
            messages.error(request, 'Access denied. This page is for gamers only.')
            return redirect('core:home')
        
        # If a shop-owner-only view is requested by a non-shop-owner, block it
        if current_name in shop_owner_allowed_names and user_role != 'shop_owner':
            # Exception: Allow gamers with pending shops to access shop_owner_dashboard (inactive mode)
            if current_name == 'accounts:shop_owner_dashboard' and user_role == 'gamer':
                from shops.models import Shop
                try:
                    gamer = Gamer.objects.get(id=user_id)
                    if Shop.objects.filter(submitted_by_uid=gamer.uid).exists():
                        return None
                except Gamer.DoesNotExist:
                    pass
            
            messages.error(request, 'Access denied. This page is for shop owners only.')
            return redirect('core:home')
        
        # Gamer profile completion enforcement
        if user_role == 'gamer':
            try:
                gamer = Gamer.objects.get(id=user_id)
                if not gamer.profile_completed:
                    # Allowed paths for incomplete profile
                    allowed_names = [
                        reverse('accounts:gamer_dashboard'),
                        reverse('accounts:gamer_settings'),
                        reverse('accounts:gamer_public_profile'),
                        
                        # Allow profile completion modal view itself
                        reverse('accounts:gamer_profile_completion'),
                        
                        # Allow username availability checks
                        reverse('accounts:check_username'),
                        reverse('core:home'),
                        reverse('games:get_profile_form_data'),
                    ]
                    # Also allow static media and auth/logout
                    allowed_prefixes = [
                        '/static/', '/media/',
                        reverse('accounts:logout'),
                    ]
                    current_path = request.path
                    allowed = current_path in allowed_names or any(current_path.startswith(p) for p in allowed_prefixes)
                    
                    if not allowed:
                        messages.warning(request, 'Complete your profile to access this page')
                        return redirect('accounts:gamer_dashboard')
            except Gamer.DoesNotExist:
                pass
        
        return None