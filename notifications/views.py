"""Views for notifications app."""
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.conf import settings
from django.db.models import Q
from accounts.view_utils import require_gamer_role, get_current_gamer, require_shop_owner_role, get_current_shop_owner
from .models import NotificationRecipient

@csrf_exempt
def pusher_auth(request):
    """
    Authenticate Pusher private channels.
    """
    # Check if user is authenticated via standard auth or session-based roles
    is_auth = request.user.is_authenticated or request.session.get('user_id')
    if not is_auth:
        return JsonResponse({'message': 'Forbidden'}, status=403)

    channel_name = request.POST.get('channel_name')
    socket_id = request.POST.get('socket_id')

    if not channel_name or not socket_id:
        return JsonResponse({'message': 'Invalid parameters'}, status=400)

    # Basic authorization check: users can only join their own private channels
    user_id = str(request.session.get('user_id'))
    if channel_name.startswith('private-gamer-'):
        if channel_name != f'private-gamer-{user_id}':
             return JsonResponse({'message': 'Forbidden'}, status=403)
    
    elif channel_name.startswith('private-shop_owner-'):
        if channel_name != f'private-shop_owner-{user_id}':
             return JsonResponse({'message': 'Forbidden'}, status=403)

    try:
        auth = settings.PUSHER_CLIENT.authenticate(
            channel=channel_name,
            socket_id=socket_id
        )
        return JsonResponse(auth)
    except Exception as e:
        return JsonResponse({'message': str(e)}, status=403)


@require_gamer_role
def notification_center(request):
    """Display all notifications for the logged-in gamer."""
    from core.views import base_site_context
    
    gamer = get_current_gamer(request)
    if not gamer:
        from django.contrib import messages
        messages.error(request, 'Gamer profile not found.')
        return redirect('core:home')
    
    # Get filter parameters
    category = request.GET.get('category')
    is_read = request.GET.get('is_read')  # 'read', 'unread', or None for all
    
    # Base queryset
    notifications = NotificationRecipient.objects.filter(
        gamer=gamer
    ).select_related('notification').order_by('-created_at')
    
    # Apply filters
    if category:
        notifications = notifications.filter(notification__category=category)
    
    if is_read == 'read':
        notifications = notifications.filter(is_read=True)
    elif is_read == 'unread':
        notifications = notifications.filter(is_read=False)
    
    # Pagination
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Get stats
    total_unread = NotificationRecipient.objects.filter(
        gamer=gamer, is_read=False
    ).count()
    
    # Get recent notifications for the dropdown in base template
    recent_notifications = NotificationRecipient.objects.filter(
        gamer=gamer
    ).select_related('notification').order_by('-created_at')[:5]
    
    context = {
        **base_site_context(),
        'gamer': gamer,
        'page_obj': page_obj,
        'total_unread': total_unread,
        'current_category': category,
        'current_is_read': is_read,
        'gamer_unread_notifications_count': total_unread,
        'gamer_recent_notifications': recent_notifications,
    }
    
    return render(request, 'notifications/notification_center.html', context)


@require_gamer_role
@require_http_methods(['POST'])
def mark_notification_as_read(request, notification_id):
    """Mark a single notification as read (AJAX endpoint)."""
    gamer = get_current_gamer(request)
    if not gamer:
        return JsonResponse({'status': 'error', 'message': 'Gamer not found'}, status=403)
    
    notification_recipient = get_object_or_404(
        NotificationRecipient,
        id=notification_id,
        gamer=gamer
    )
    notification_recipient.mark_as_read()
    
    # Return unread count
    unread_count = NotificationRecipient.objects.filter(
        gamer=gamer, is_read=False
    ).count()
    
    return JsonResponse({
        'status': 'success',
        'unread_count': unread_count
    })


@require_gamer_role
@require_http_methods(['POST'])
def mark_all_as_read(request):
    """Mark all notifications as read for the gamer."""
    gamer = get_current_gamer(request)
    if not gamer:
        return JsonResponse({'status': 'error', 'message': 'Gamer not found'}, status=403)
    
    NotificationRecipient.objects.filter(
        gamer=gamer,
        is_read=False
    ).update(is_read=True)
    
    return JsonResponse({
        'status': 'success',
        'message': 'All notifications marked as read'
    })


@require_gamer_role
@require_http_methods(['GET'])
def get_unread_count(request):
    """Get unread notification count (AJAX endpoint)."""
    gamer = get_current_gamer(request)
    if not gamer:
        return JsonResponse({'unread_count': 0})
    
    unread_count = NotificationRecipient.objects.filter(
        gamer=gamer, is_read=False
    ).count()
    
    return JsonResponse({
        'unread_count': unread_count
    })


@require_gamer_role
@require_http_methods(['GET'])
def get_recent_notifications(request):
    """Get 5 most recent notifications for dashboard (AJAX)."""
    gamer = get_current_gamer(request)
    if not gamer:
        return JsonResponse({'notifications': []})
    
    notifications = NotificationRecipient.objects.filter(
        gamer=gamer
    ).select_related('notification').order_by('-created_at')[:5]
    
    data = {
        'notifications': [
            {
                'id': notif.id,
                'title': notif.notification.title,
                'category': notif.notification.get_category_display(),
                'is_read': notif.is_read,
                'created_at': notif.created_at.isoformat(),
            }
            for notif in notifications
        ]
    }
    
    return JsonResponse(data)


# ============================================================================
# Shop Owner Notification Views
# ============================================================================

@require_shop_owner_role
def shop_owner_notification_center(request):
    """Display all notifications for the logged-in shop owner."""
    from core.views import base_site_context
    
    shop_owner = get_current_shop_owner(request)
    if not shop_owner:
        from django.contrib import messages
        messages.error(request, 'Shop owner profile not found.')
        return redirect('core:home')
    
    # Get filter parameters
    category = request.GET.get('category')
    is_read = request.GET.get('is_read')
    
    # Base queryset
    notifications = NotificationRecipient.objects.filter(
        shop_owner=shop_owner
    ).select_related('notification').order_by('-created_at')
    
    # Apply filters
    if category:
        notifications = notifications.filter(notification__category=category)
    
    if is_read == 'read':
        notifications = notifications.filter(is_read=True)
    elif is_read == 'unread':
        notifications = notifications.filter(is_read=False)
    
    # Pagination
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Get stats
    total_unread = NotificationRecipient.objects.filter(
        shop_owner=shop_owner, is_read=False
    ).count()
    
    # Get recent notifications for the dropdown in base template
    recent_notifications = NotificationRecipient.objects.filter(
        shop_owner=shop_owner
    ).select_related('notification').order_by('-created_at')[:5]
    
    context = {
        **base_site_context(),
        'shop_owner': shop_owner,
        'page_obj': page_obj,
        'total_unread': total_unread,
        'current_category': category,
        'current_is_read': is_read,
        'shop_owner_unread_notifications_count': total_unread,
        'shop_owner_recent_notifications': recent_notifications,
    }
    
    return render(request, 'notifications/shop_owner_notification_center.html', context)


@require_shop_owner_role
@require_http_methods(['POST'])
def shop_owner_mark_notification_as_read(request, notification_id):
    """Mark a single notification as read for shop owner (AJAX endpoint)."""
    shop_owner = get_current_shop_owner(request)
    if not shop_owner:
        return JsonResponse({'status': 'error', 'message': 'Shop owner not found'}, status=403)
    
    notification_recipient = get_object_or_404(
        NotificationRecipient,
        id=notification_id,
        shop_owner=shop_owner
    )
    notification_recipient.mark_as_read()
    
    unread_count = NotificationRecipient.objects.filter(
        shop_owner=shop_owner, is_read=False
    ).count()
    
    return JsonResponse({
        'status': 'success',
        'unread_count': unread_count
    })


@require_shop_owner_role
@require_http_methods(['POST'])
def shop_owner_mark_all_as_read(request):
    """Mark all notifications as read for the shop owner."""
    shop_owner = get_current_shop_owner(request)
    if not shop_owner:
        return JsonResponse({'status': 'error', 'message': 'Shop owner not found'}, status=403)
    
    NotificationRecipient.objects.filter(
        shop_owner=shop_owner,
        is_read=False
    ).update(is_read=True)
    
    return JsonResponse({
        'status': 'success',
        'message': 'All notifications marked as read'
    })


@require_shop_owner_role
@require_http_methods(['GET'])
def shop_owner_get_unread_count(request):
    """Get unread notification count for shop owner (AJAX endpoint)."""
    shop_owner = get_current_shop_owner(request)
    if not shop_owner:
        return JsonResponse({'unread_count': 0})
    
    unread_count = NotificationRecipient.objects.filter(
        shop_owner=shop_owner, is_read=False
    ).count()
    
    return JsonResponse({
        'unread_count': unread_count
    })
