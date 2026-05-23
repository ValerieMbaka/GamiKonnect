from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.utils import timezone
from django.contrib import messages
from admin_panel.decorators import admin_required
from .services import ActivityFeedService
from .models import Activity, ActivityLog
from accounts.models import Gamer, Account


@admin_required
def all_activity(request):
    """Combined site-wide activity for admin users."""
    # Use a larger limit and paginate
    feed = ActivityFeedService.get_admin_feed(limit=200)
    page = request.GET.get('page', 1)
    paginator = Paginator(feed, 20)
    page_obj = paginator.get_page(page)
    context = {
        'feed_items': page_obj,
        'title': 'All Activity',
    }
    return render(request, 'activities/all_activity.html', context)


def gamer_activity_list(request, gamer_id):
    gamer = get_object_or_404(Gamer, id=gamer_id)
    # Allow gamer themselves or admin/staff to view
    user_is_admin = getattr(request.user, 'is_staff', False) or getattr(request.user, 'is_superuser', False)
    session_user_id = request.session.get('user_id')
    if not user_is_admin and session_user_id != gamer.id:
        messages.error(request, "Access denied.")
        return redirect('accounts:gamer_dashboard')

    activities = Activity.objects.filter(gamer=gamer).order_by('-timestamp')
    paginator = Paginator(activities, 20)
    page = request.GET.get('page', 1)
    page_obj = paginator.get_page(page)
    context = {
        'gamer': gamer,
        'feed_items': page_obj,
        'title': f"{gamer.custom_username or gamer.email} - Activity",
    }
    return render(request, 'activities/gamer_activity_list.html', context)


def actor_activity_logs(request, actor_id):
    actor = get_object_or_404(Account, id=actor_id)
    # Allow owner (session) or admin/staff
    user_is_admin = getattr(request.user, 'is_staff', False) or getattr(request.user, 'is_superuser', False)
    session_user_id = request.session.get('user_id')
    if not user_is_admin and session_user_id != actor.id:
        messages.error(request, "Access denied.")
        return redirect('core:home')

    logs = ActivityLog.objects.filter(actor=actor).order_by('-timestamp')
    paginator = Paginator(logs, 20)
    page = request.GET.get('page', 1)
    page_obj = paginator.get_page(page)
    context = {
        'actor': actor,
        'feed_items': page_obj,
        'title': f"{actor.email} - Activity Logs",
    }
    return render(request, 'activities/actor_activity_list.html', context)
from django.shortcuts import render

# Create your views here.
