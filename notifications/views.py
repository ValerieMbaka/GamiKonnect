"""Views for notifications app."""
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.db.models import Q

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
    gamer = request.session.get('gamer_instance')
    
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
    
    context = {
        'page_obj': page_obj,
        'total_unread': total_unread,
        'current_category': category,
        'current_is_read': is_read,
    }
    
    return render(request, 'notifications/notification_center.html', context)


@require_gamer_role
@require_http_methods(['POST'])
def mark_notification_as_read(request, notification_id):
    """Mark a single notification as read (AJAX endpoint)."""
    gamer = request.session.get('gamer_instance')
    
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
    gamer = request.session.get('gamer_instance')
    
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
    gamer = request.session.get('gamer_instance')
    
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
    gamer = request.session.get('gamer_instance')
    
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
