from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm, UserCreationForm
from django.contrib.auth.models import User, Group, Permission
from django.contrib import messages
from django.http import HttpResponse, JsonResponse, Http404
from django.utils import timezone
from datetime import timedelta
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count, F, Value, Case, When, IntegerField
from django.core.management import call_command
from django.contrib.contenttypes.models import ContentType
import json
import logging
import os
from io import StringIO
from django.db import transaction

from core.email_service import EmailManager

# Model imports
from core.models import (
    About, Event, FeatureCard, Footer, FooterLink,
    FooterSection, NavigationLink, ProjectDetail,
    Section, SectionHeading, SiteStyle, Slider,
)
from games.models import Game, Genre, Platform, PlatformCategory
from accounts.models import Gamer, ShopOwner, Account
from activities.models import ActivityLog, Activity
from progression.models import Level, Achievement, GamerStats
from shops.models import Shop
from payments.models import MpesaTransaction
from competitions.models import Competition, CompetitionAuditLog, CompetitionRegistration, CompetitionResult
from competitions.forms import (
    CompetitionApprovalForm, CompetitionRejectionForm,
    CompetitionAdminCreateForm, CompetitionSuspendForm, CompetitionEditPrizesForm,
)
from competitions.scheduler import schedule_competition_jobs, remove_competition_jobs
from competitions.services import CompetitionService
from activities.services import ActivityFeedService
from notifications.models import Notification, NotificationGroup, NotificationRecipient, NotificationSchedule

# Imports for custom logic
from .decorators import admin_required
from .forms import (
    AboutForm, AdminProfileUpdateForm, AdminUserUpdateForm,
    AchievementForm, EventForm, FeatureCardForm, FooterForm,
    FooterLinkForm, FooterSectionForm, GameForm, LevelForm,
    NavigationLinkForm, NotificationForm, NotificationGroupForm,
    NotificationScheduleForm, ProjectDetailForm, SectionForm,
    SectionHeadingForm, ShopForm, SiteStyleForm, SliderForm,
    StaffUserCreateForm, StaffUserEditForm,
)

logger = logging.getLogger(__name__)


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
    # KPI Metrics
    total_gamers = Gamer.objects.count()
    total_arenas = Shop.objects.filter(is_approved=True).count()
    total_competitions = Competition.objects.count()
    total_earnings = MpesaTransaction.objects.filter(status='SUCCESS').aggregate(Sum('amount'))['amount__sum'] or 0

    # Recent Activity
    recent_activity_feed = ActivityFeedService.get_admin_feed(limit=5)

    # Upcoming Events (Competitions starting soon)
    upcoming_events = Competition.objects.filter(
        scheduled_time__gte=timezone.now()
    ).order_by('scheduled_time')[:5]

    # Top Players (Based on points)
    top_players = Gamer.objects.all().order_by('-points')[:5]

    # Site Activity Chart Data (Last 7 days - daily logins)
    today = timezone.now().date()
    activity_labels = []
    activity_data = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        count = ActivityLog.objects.filter(timestamp__date=day).count()
        activity_labels.append(day.strftime('%a'))
        activity_data.append(count)

    # Revenue by Category (Last 4 months)
    rev_labels = []
    rev_competitions = []
    rev_ads = []
    rev_subscriptions = []
    rev_arena_fees = []
    for i in range(3, -1, -1):
        month_ago = timezone.now() - timedelta(days=i * 30)
        month_str = month_ago.strftime('%b')
        rev_labels.append(month_str)
        # Competition payments
        comp_rev = MpesaTransaction.objects.filter(
            status='SUCCESS',
            created_at__year=month_ago.year,
            created_at__month=month_ago.month,
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        rev_competitions.append(float(comp_rev))
        
        # Placeholders for other categories as they might not have models yet
        rev_ads.append(float(comp_rev) * 0.1) # Placeholder 10%
        rev_subscriptions.append(float(comp_rev) * 0.15) # Placeholder 15%
        rev_arena_fees.append(float(comp_rev) * 0.2) # Placeholder 20%

    # APScheduler Jobs Monitoring
    from competitions.scheduler import get_scheduler
    scheduler = get_scheduler()
    scheduled_jobs = []
    if scheduler:
        for job in scheduler.get_jobs():
            scheduled_jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run': job.next_run_time,
                'trigger': str(job.trigger)
            })

    context = {
        'total_gamers': total_gamers,
        'total_arenas': total_arenas,
        'total_competitions': total_competitions,
        'total_earnings': total_earnings,
        'recent_activity_feed': recent_activity_feed,
        'upcoming_events': upcoming_events,
        'top_players': top_players,
        'scheduled_jobs': scheduled_jobs,
        'today': timezone.now(),
        'chart_data_json': json.dumps({
            'activity_labels': activity_labels,
            'activity_data': activity_data,
            'rev_labels': rev_labels,
            'rev_competitions': rev_competitions,
            'rev_ads': rev_ads,
            'rev_subscriptions': rev_subscriptions,
            'rev_arena_fees': rev_arena_fees,
        }),
        'admin_unread_notifications_count': NotificationRecipient.objects.filter(
            admin_user__email=request.user.email,
            is_read=False
        ).count(),
        'admin_recent_notifications': NotificationRecipient.objects.filter(
            admin_user__email=request.user.email
        ).select_related('notification').order_by('-created_at')[:5],
        'pusher_key': os.environ.get('PUSHER_KEY', ''),
        'pusher_cluster': os.environ.get('PUSHER_CLUSTER', ''),
        'pending_competitions_count': Competition.objects.filter(status='pending').count(),
    }
    return render(request, 'admin_panel/base/admin_dashboard.html', context)


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

    # Content library sections (merged into site settings)
    content_sections = [
        {'key': 'navigation_links', 'title': 'Navigation Links', 'icon': 'fas fa-compass',
         'model': NavigationLink, 'form_class': NavigationLinkForm,
         'queryset': lambda: NavigationLink.objects.all().order_by('order', 'id'),
         'summary': lambda item: item.link_text, 'detail': lambda item: item.link or 'No destination set'},
        {'key': 'footer_sections', 'title': 'Footer Sections', 'icon': 'fas fa-layer-group',
         'model': FooterSection, 'form_class': FooterSectionForm,
         'queryset': lambda: FooterSection.objects.all().order_by('order', 'id'),
         'summary': lambda item: item.title, 'detail': lambda item: f'Order #{item.order}'},
        {'key': 'footer_links', 'title': 'Footer Links', 'icon': 'fas fa-link',
         'model': FooterLink, 'form_class': FooterLinkForm,
         'queryset': lambda: FooterLink.objects.select_related('section').all().order_by('order', 'id'),
         'summary': lambda item: item.link_text, 'detail': lambda item: item.section.title},
        {'key': 'sections', 'title': 'Content Sections', 'icon': 'fas fa-square-poll-horizontal',
         'model': Section, 'form_class': SectionForm,
         'queryset': lambda: Section.objects.all().order_by('order', 'name'),
         'summary': lambda item: item.name, 'detail': lambda item: item.slug},
        {'key': 'section_headings', 'title': 'Section Headings', 'icon': 'fas fa-heading',
         'model': SectionHeading, 'form_class': SectionHeadingForm,
         'queryset': lambda: SectionHeading.objects.select_related('section').all().order_by('section__order'),
         'summary': lambda item: item.heading, 'detail': lambda item: item.section.name},
        {'key': 'sliders', 'title': 'Hero Sliders', 'icon': 'fas fa-images',
         'model': Slider, 'form_class': SliderForm,
         'queryset': lambda: Slider.objects.all().order_by('order', 'id'),
         'summary': lambda item: item.title, 'detail': lambda item: item.cta_text or 'No CTA'},
        {'key': 'about', 'title': 'About Section', 'icon': 'fas fa-circle-info',
         'model': About, 'form_class': AboutForm,
         'queryset': lambda: About.objects.all().order_by('-id'),
         'summary': lambda item: item.heading, 'detail': lambda item: item.badge_text},
        {'key': 'feature_cards', 'title': 'Feature Cards', 'icon': 'fas fa-star',
         'model': FeatureCard, 'form_class': FeatureCardForm,
         'queryset': lambda: FeatureCard.objects.all().order_by('order', 'id'),
         'summary': lambda item: item.feature_name, 'detail': lambda item: f'Order #{item.order}'},
        {'key': 'events', 'title': 'Events', 'icon': 'fas fa-calendar-days',
         'model': Event, 'form_class': EventForm,
         'queryset': lambda: Event.objects.all().order_by('-id'),
         'summary': lambda item: item.title, 'detail': lambda item: 'Active' if item.is_active else 'Inactive'},
        {'key': 'footer', 'title': 'Footer Copy', 'icon': 'fas fa-shield-heart',
         'model': Footer, 'form_class': FooterForm,
         'queryset': lambda: Footer.objects.all().order_by('-id'),
         'summary': lambda item: item.copy_right_text, 'detail': lambda item: item.ownership_text},
    ]

    if request.method == 'POST':
        # Check if this is a content form submission
        content_form_key = request.POST.get('content_form_key')
        if content_form_key:
            selected_config = next((item for item in content_sections if item['key'] == content_form_key), None)
            if selected_config:
                object_id = request.POST.get('object_id')
                instance = None
                if object_id:
                    instance = selected_config['model'].objects.filter(pk=object_id).first()
                form = selected_config['form_class'](request.POST, request.FILES, instance=instance, prefix=selected_config['key'])
                if form.is_valid():
                    saved_object = form.save()
                    messages.success(request, f"{selected_config['title']} saved successfully.")
                    return redirect(f"{reverse('admin_panel:site_settings')}?section={selected_config['key']}&object_id={saved_object.pk}")
                else:
                    messages.error(request, f"Please correct the errors in {selected_config['title']}.")
            # Ensure forms are defined for the template
            project_form = ProjectDetailForm(instance=project_detail)
            style_form = SiteStyleForm(instance=site_style)
        else:
            # Site settings form submission
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
                project_form = ProjectDetailForm(instance=project_detail)
                style_form = SiteStyleForm(instance=site_style)
    else:
        project_form = ProjectDetailForm(instance=project_detail)
        style_form = SiteStyleForm(instance=site_style)

    # Build rendered content sections
    active_section = request.GET.get('section')
    active_object_id = request.GET.get('object_id')
    rendered_sections = []
    for section_config in content_sections:
        instance = None
        if active_section == section_config['key'] and active_object_id:
            instance = section_config['model'].objects.filter(pk=active_object_id).first()
        form = section_config['form_class'](instance=instance, prefix=section_config['key'])
        queryset = section_config['queryset']()
        rendered_sections.append({
            'key': section_config['key'],
            'title': section_config['title'],
            'icon': section_config['icon'],
            'form': form,
            'count': queryset.count(),
            'items': [
                {'id': item.pk, 'summary': section_config['summary'](item),
                 'detail': section_config['detail'](item), 'is_active': getattr(item, 'is_active', True)}
                for item in queryset[:8]
            ],
        })

    context = {
        'project_form': project_form,
        'style_form': style_form,
        'current_logo': project_detail.logo if project_detail.logo else None,
        'content_sections': rendered_sections,
        'active_section': active_section,
        'active_object_id': active_object_id,
        'content_counts': {
            'navigation_links': NavigationLink.objects.count(),
            'footer_sections': FooterSection.objects.count(),
            'footer_links': FooterLink.objects.count(),
            'sections': Section.objects.count(),
            'sliders': Slider.objects.count(),
            'feature_cards': FeatureCard.objects.count(),
            'events': Event.objects.count(),
        },
    }
    return render(request, 'admin_panel/settings/site_settings.html', context)


# --- SYSTEM AUDIT VIEW ---
@admin_required
def admin_system_audit(request):
    """Combined view for admin logs, gamer activities, and background jobs."""
    tab = request.GET.get('tab', 'admin_logs')

    # Admin Logs (ActivityLog)
    admin_logs = ActivityLog.objects.all().order_by('-timestamp')
    admin_logs_paginator = Paginator(admin_logs, 30)
    admin_logs_page = admin_logs_paginator.get_page(request.GET.get('admin_page'))

    # Gamer Activities (Activity model)
    gamer_activities = Activity.objects.all().order_by('-timestamp')
    gamer_paginator = Paginator(gamer_activities, 30)
    gamer_page = gamer_paginator.get_page(request.GET.get('gamer_page'))

    # Background Jobs
    from competitions.scheduler import get_scheduler
    scheduler = get_scheduler()
    scheduled_jobs = []
    if scheduler:
        for job in scheduler.get_jobs():
            scheduled_jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run': job.next_run_time,
                'trigger': str(job.trigger)
            })

    context = {
        'active_tab': tab,
        'admin_logs': admin_logs_page,
        'gamer_activities': gamer_page,
        'scheduled_jobs': scheduled_jobs,
        'admin_logs_count': ActivityLog.objects.count(),
        'gamer_activities_count': Activity.objects.count(),
        'pending_competitions_count': Competition.objects.filter(status='pending').count(),
    }
    return render(request, 'admin_panel/audit/system_audit.html', context)


# --- STAFF MANAGEMENT VIEWS ---
@admin_required
def admin_staff_list(request):
    """Manage staff users (admin/staff Django users)."""
    staff_users = User.objects.filter(is_staff=True).order_by('-date_joined')

    if request.method == 'POST':
        form = StaffUserCreateForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    user = form.save(commit=False)
                    user.is_staff = True
                    user.save()
                    # Assign selected groups/permissions
                    groups = form.cleaned_data.get('groups', [])
                    user.groups.set(groups)
                    messages.success(request, f"Staff user '{user.username}' created successfully.")
                    return redirect('admin_panel:staff_list')
            except Exception as e:
                logger.error(f"Staff creation error: {e}")
                messages.error(request, f"Failed to create staff user: {str(e)}")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = StaffUserCreateForm()

    context = {
        'staff_users': staff_users,
        'form': form,
        'staff_count': staff_users.count(),
        'admin_count': User.objects.filter(is_superuser=True).count(),
        'staff_active_count': staff_users.filter(is_active=True).count(),
        'staff_inactive_count': staff_users.filter(is_active=False).count(),
        'pending_competitions_count': Competition.objects.filter(status='pending').count(),
    }
    return render(request, 'admin_panel/staff/staff_list.html', context)


@admin_required
def admin_staff_edit(request, user_id):
    """Edit a staff user."""
    staff_user = get_object_or_404(User, id=user_id, is_staff=True)

    if request.method == 'POST':
        form = StaffUserEditForm(request.POST, instance=staff_user)
        if form.is_valid():
            form.save()
            messages.success(request, f"Staff user '{staff_user.username}' updated successfully.")
            return redirect('admin_panel:staff_list')
        else:
            messages.error(request, "Please correct the errors.")
    else:
        form = StaffUserEditForm(instance=staff_user)

    context = {
        'form': form,
        'staff_user': staff_user,
        'pending_competitions_count': Competition.objects.filter(status='pending').count(),
    }
    return render(request, 'admin_panel/staff/staff_edit.html', context)


@admin_required
def admin_staff_toggle_active(request, user_id):
    """Toggle staff user active status."""
    if request.method == 'POST':
        staff_user = get_object_or_404(User, id=user_id, is_staff=True)
        staff_user.is_active = not staff_user.is_active
        staff_user.save()
        status = "activated" if staff_user.is_active else "deactivated"
        return JsonResponse({'success': True, 'message': f"Staff user '{staff_user.username}' {status}."})
    return JsonResponse({'success': False, 'message': 'Invalid method.'}, status=405)


# --- UPDATED USER LIST (Gamers + Shop Owners only) ---
@admin_required
def admin_user_list(request):
    query = request.GET.get('q', '')
    user_type = request.GET.get('type', '')
    gender = request.GET.get('gender', '')
    status_filter = request.GET.get('status', '')
    pwd_filter = request.GET.get('pwd', '')

    gamers = Gamer.objects.all()
    shop_owners = ShopOwner.objects.all()

    if query:
        gamers = gamers.filter(
            Q(email__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(custom_username__icontains=query)
        )
        shop_owners = shop_owners.filter(
            Q(email__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        )

    if gender:
        gamers = gamers.filter(gender=gender)
        shop_owners = shop_owners.filter(gender=gender)

    if status_filter == 'active':
        # Active = has logged in recently (within 30 days)
        cutoff = timezone.now() - timedelta(days=30)
        gamers = gamers.filter(last_login__gte=cutoff)
    elif status_filter == 'inactive':
        cutoff = timezone.now() - timedelta(days=30)
        gamers = gamers.filter(Q(last_login__isnull=True) | Q(last_login__lt=cutoff))

    if pwd_filter == 'yes':
        gamers = gamers.filter(is_gwds=True)
    elif pwd_filter == 'no':
        gamers = gamers.filter(is_gwds=False)

    # KPI stats
    total_gamers = Gamer.objects.count()
    total_shop_owners = ShopOwner.objects.count()
    male_count = Gamer.objects.filter(gender='male').count() + ShopOwner.objects.filter(gender='male').count()
    female_count = Gamer.objects.filter(gender='female').count() + ShopOwner.objects.filter(gender='female').count()
    pwd_count = Gamer.objects.filter(is_gwds=True).count()
    active_count = Gamer.objects.filter(last_login__gte=timezone.now() - timedelta(days=30)).count()
    inactive_count = total_gamers - active_count

    # Combine and paginate
    user_list = []
    for g in gamers:
        user_list.append({
            'id': g.id,
            'uid': g.uid,
            'email': g.email,
            'first_name': g.first_name,
            'last_name': g.last_name,
            'username': g.custom_username or f"{g.first_name} {g.last_name}".strip(),
            'role': 'Gamer',
            'gender': g.gender,
            'is_gwds': g.is_gwds,
            'profile_completed': g.profile_completed,
            'last_login': g.last_login,
            'points': g.points,
            'date_joined': g.created_at,
            'profile_picture': g.profile_picture,
        })
    for s in shop_owners:
        user_list.append({
            'id': s.id,
            'uid': s.uid,
            'email': s.email,
            'first_name': s.first_name,
            'last_name': s.last_name,
            'username': f"{s.first_name} {s.last_name}".strip(),
            'role': 'Shop Owner',
            'gender': s.gender,
            'is_gwds': False,
            'profile_completed': True,
            'last_login': s.last_login,
            'points': 0,
            'date_joined': s.created_at,
            'profile_picture': None,
        })

    # Sort by date joined (newest first)
    user_list.sort(key=lambda x: x['date_joined'], reverse=True)

    paginator = Paginator(user_list, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'users': page_obj,
        'query': query,
        'user_type': user_type,
        'selected_gender': gender,
        'selected_status': status_filter,
        'selected_pwd': pwd_filter,
        'total_users': total_gamers + total_shop_owners,
        'total_gamers': total_gamers,
        'total_shop_owners': total_shop_owners,
        'male_count': male_count,
        'female_count': female_count,
        'pwd_count': pwd_count,
        'active_count': active_count,
        'inactive_count': inactive_count,
        'pending_competitions_count': Competition.objects.filter(status='pending').count(),
    }
    return render(request, 'admin_panel/users/admin_user_list.html', context)


@admin_required
def admin_user_detail(request, user_id):
    # Try Gamer first, then ShopOwner
    user_obj = None
    profile_type = ''
    try:
        user_obj = Gamer.objects.get(id=user_id)
        profile_type = 'gamer'
    except Gamer.DoesNotExist:
        try:
            user_obj = ShopOwner.objects.get(id=user_id)
            profile_type = 'shop_owner'
        except ShopOwner.DoesNotExist:
            raise Http404("User not found.")

    # Get registrations/competitions for gamers
    registrations = []
    if profile_type == 'gamer':
        registrations = CompetitionRegistration.objects.filter(
            gamer=user_obj, is_cancelled=False
        ).select_related('competition').order_by('-registered_at')[:10]

    # Get recent activity
    activities = ActivityLog.objects.filter(
        actor__email=user_obj.email
    ).order_by('-timestamp')[:5]

    context = {
        'user_obj': user_obj,
        'profile_type': profile_type,
        'registrations': registrations,
        'activities': activities,
        'pending_competitions_count': Competition.objects.filter(status='pending').count(),
    }
    return render(request, 'admin_panel/users/admin_user_detail.html', context)


# Content Library
@admin_required
def admin_content_library(request):
    content_sections = [
        {'key': 'navigation_links', 'title': 'Navigation Links', 'icon': 'fas fa-compass',
         'model': NavigationLink, 'form_class': NavigationLinkForm,
         'queryset': lambda: NavigationLink.objects.all().order_by('order', 'id'),
         'summary': lambda item: item.link_text, 'detail': lambda item: item.link or 'No destination set'},
        {'key': 'footer_sections', 'title': 'Footer Sections', 'icon': 'fas fa-layer-group',
         'model': FooterSection, 'form_class': FooterSectionForm,
         'queryset': lambda: FooterSection.objects.all().order_by('order', 'id'),
         'summary': lambda item: item.title, 'detail': lambda item: f'Order #{item.order}'},
        {'key': 'footer_links', 'title': 'Footer Links', 'icon': 'fas fa-link',
         'model': FooterLink, 'form_class': FooterLinkForm,
         'queryset': lambda: FooterLink.objects.select_related('section').all().order_by('order', 'id'),
         'summary': lambda item: item.link_text, 'detail': lambda item: item.section.title},
        {'key': 'sections', 'title': 'Content Sections', 'icon': 'fas fa-square-poll-horizontal',
         'model': Section, 'form_class': SectionForm,
         'queryset': lambda: Section.objects.all().order_by('order', 'name'),
         'summary': lambda item: item.name, 'detail': lambda item: item.slug},
        {'key': 'section_headings', 'title': 'Section Headings', 'icon': 'fas fa-heading',
         'model': SectionHeading, 'form_class': SectionHeadingForm,
         'queryset': lambda: SectionHeading.objects.select_related('section').all().order_by('section__order'),
         'summary': lambda item: item.heading, 'detail': lambda item: item.section.name},
        {'key': 'sliders', 'title': 'Hero Sliders', 'icon': 'fas fa-images',
         'model': Slider, 'form_class': SliderForm,
         'queryset': lambda: Slider.objects.all().order_by('order', 'id'),
         'summary': lambda item: item.title, 'detail': lambda item: item.cta_text or 'No CTA'},
        {'key': 'about', 'title': 'About Section', 'icon': 'fas fa-circle-info',
         'model': About, 'form_class': AboutForm,
         'queryset': lambda: About.objects.all().order_by('-id'),
         'summary': lambda item: item.heading, 'detail': lambda item: item.badge_text},
        {'key': 'feature_cards', 'title': 'Feature Cards', 'icon': 'fas fa-star',
         'model': FeatureCard, 'form_class': FeatureCardForm,
         'queryset': lambda: FeatureCard.objects.all().order_by('order', 'id'),
         'summary': lambda item: item.feature_name, 'detail': lambda item: f'Order #{item.order}'},
        {'key': 'events', 'title': 'Events', 'icon': 'fas fa-calendar-days',
         'model': Event, 'form_class': EventForm,
         'queryset': lambda: Event.objects.all().order_by('-id'),
         'summary': lambda item: item.title, 'detail': lambda item: 'Active' if item.is_active else 'Inactive'},
        {'key': 'footer', 'title': 'Footer Copy', 'icon': 'fas fa-shield-heart',
         'model': Footer, 'form_class': FooterForm,
         'queryset': lambda: Footer.objects.all().order_by('-id'),
         'summary': lambda item: item.copy_right_text, 'detail': lambda item: item.ownership_text},
    ]

    if request.method == 'POST':
        form_key = request.POST.get('content_form_key')
        selected_config = next((item for item in content_sections if item['key'] == form_key), None)
        if selected_config:
            object_id = request.POST.get('object_id')
            instance = None
            if object_id:
                instance = selected_config['model'].objects.filter(pk=object_id).first()

            form = selected_config['form_class'](request.POST, request.FILES, instance=instance, prefix=selected_config['key'])
            if form.is_valid():
                saved_object = form.save()
                messages.success(request, f"{selected_config['title']} saved successfully.")
                return redirect(f"{reverse('admin_panel:content_library')}?section={selected_config['key']}&object_id={saved_object.pk}")

            messages.error(request, f"Please correct the errors in {selected_config['title']}.")

    active_section = request.GET.get('section')
    active_object_id = request.GET.get('object_id')
    rendered_sections = []

    for section_config in content_sections:
        instance = None
        if active_section == section_config['key'] and active_object_id:
            instance = section_config['model'].objects.filter(pk=active_object_id).first()

        form = section_config['form_class'](instance=instance, prefix=section_config['key'])
        queryset = section_config['queryset']()
        rendered_sections.append({
            'key': section_config['key'],
            'title': section_config['title'],
            'icon': section_config['icon'],
            'form': form,
            'count': queryset.count(),
            'items': [
                {'id': item.pk, 'summary': section_config['summary'](item),
                 'detail': section_config['detail'](item), 'is_active': getattr(item, 'is_active', True)}
                for item in queryset[:8]
            ],
        })

    context = {
        'content_sections': rendered_sections,
        'active_section': active_section,
        'active_object_id': active_object_id,
        'content_counts': {
            'navigation_links': NavigationLink.objects.count(),
            'footer_sections': FooterSection.objects.count(),
            'footer_links': FooterLink.objects.count(),
            'sections': Section.objects.count(),
            'sliders': Slider.objects.count(),
            'feature_cards': FeatureCard.objects.count(),
            'events': Event.objects.count(),
        },
        'pending_competitions_count': Competition.objects.filter(status='pending').count(),
    }
    return render(request, 'admin_panel/content/admin_content_library.html', context)


# Notification Hub
@admin_required
def admin_notification_hub(request):
    notification_sections = [
        {'key': 'notifications', 'title': 'Notifications', 'icon': 'fas fa-bell',
         'model': Notification, 'form_class': NotificationForm,
         'queryset': lambda: Notification.objects.all().order_by('-created_at'),
         'summary': lambda item: item.title, 'detail': lambda item: f'{item.get_category_display()} · {item.get_importance_display()}'},
        {'key': 'groups', 'title': 'Targeting Groups', 'icon': 'fas fa-object-group',
         'model': NotificationGroup, 'form_class': NotificationGroupForm,
         'queryset': lambda: NotificationGroup.objects.all().order_by('name'),
         'summary': lambda item: item.name, 'detail': lambda item: item.get_criteria_type_display()},
        {'key': 'schedules', 'title': 'Schedules', 'icon': 'fas fa-calendar-check',
         'model': NotificationSchedule, 'form_class': NotificationScheduleForm,
         'queryset': lambda: NotificationSchedule.objects.select_related('notification').all().order_by('-scheduled_at'),
         'summary': lambda item: item.notification.title, 'detail': lambda item: item.get_status_display()},
    ]

    if request.method == 'POST':
        form_key = request.POST.get('notification_form_key')
        selected_config = next((item for item in notification_sections if item['key'] == form_key), None)
        if selected_config:
            object_id = request.POST.get('object_id')
            instance = None
            if object_id:
                instance = selected_config['model'].objects.filter(pk=object_id).first()
            form = selected_config['form_class'](request.POST, request.FILES, instance=instance, prefix=selected_config['key'])
            if form.is_valid():
                saved_object = form.save()
                if isinstance(saved_object, Notification) and not saved_object.expires_at:
                    saved_object.set_expiry()
                    saved_object.save(update_fields=['expires_at'])
                messages.success(request, f"{selected_config['title']} saved successfully.")
                return redirect(f"{reverse('admin_panel:notification_hub')}?section={selected_config['key']}&object_id={saved_object.pk}")
            messages.error(request, f"Please correct the errors in {selected_config['title']}.")

    active_section = request.GET.get('section')
    active_object_id = request.GET.get('object_id')
    rendered_sections = []

    for section_config in notification_sections:
        instance = None
        if active_section == section_config['key'] and active_object_id:
            instance = section_config['model'].objects.filter(pk=active_object_id).first()
        form = section_config['form_class'](instance=instance, prefix=section_config['key'])
        queryset = section_config['queryset']()
        rendered_sections.append({
            'key': section_config['key'], 'title': section_config['title'],
            'icon': section_config['icon'], 'form': form, 'count': queryset.count(),
            'items': [{'id': item.pk, 'summary': section_config['summary'](item),
                       'detail': section_config['detail'](item), 'is_active': getattr(item, 'is_active', True)}
                      for item in queryset[:8]],
        })

    recent_recipients = NotificationRecipient.objects.select_related('notification').order_by('-created_at')[:8]

    context = {
        'notification_sections': rendered_sections,
        'recent_recipients': recent_recipients,
        'notification_counts': {
            'notifications': Notification.objects.count(),
            'groups': NotificationGroup.objects.count(),
            'schedules': NotificationSchedule.objects.count(),
            'unread_admin': NotificationRecipient.objects.filter(admin_user__email=request.user.email, is_read=False).count(),
        },
        'all_notification_groups': NotificationGroup.objects.filter(is_active=True).order_by('name'),
        'pending_competitions_count': Competition.objects.filter(status='pending').count(),
    }
    return render(request, 'admin_panel/notifications/admin_notification_hub.html', context)


@admin_required
def admin_notification_compose(request):
    """Display the compose notification page."""
    from notifications.forms import BulkNotificationForm as ComposeForm
    from notifications.models import NotificationGroup

    form = ComposeForm()
    context = {
        'form': form,
        'all_notification_groups': NotificationGroup.objects.filter(is_active=True).order_by('name'),
        'pending_competitions_count': Competition.objects.filter(status='pending').count(),
    }
    return render(request, 'admin_panel/notifications/admin_notification_compose.html', context)


@admin_required
def admin_notification_compose_send(request):
    """Handle the compose notification form submission."""
    from notifications.forms import BulkNotificationForm as ComposeForm
    from notifications.services import send_notification_to_users, get_group_users
    from notifications.models import Notification, NotificationGroup
    from accounts.models import Gamer

    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect(reverse('admin_panel:notification_compose'))

    form = ComposeForm(request.POST)
    if not form.is_valid():
        messages.error(request, 'Please correct the errors below.')
        return redirect(reverse('admin_panel:notification_compose'))

    # Create the notification
    notification = Notification.objects.create(
        title=form.cleaned_data['title'],
        message=form.cleaned_data['message'],
        category=form.cleaned_data['category'],
        importance=form.cleaned_data['importance'],
    )
    notification.set_expiry()
    notification.save(update_fields=['expires_at'])

    # Determine target audience
    target_type = request.POST.get('target_type', 'all')
    target_group_id = request.POST.get('target_group')
    send_email = form.cleaned_data.get('send_email', False)

    if target_type == 'all':
        users = Gamer.objects.all()
    elif target_type == 'group' and target_group_id:
        group = NotificationGroup.objects.filter(pk=target_group_id, is_active=True).first()
        if not group:
            messages.error(request, 'Selected group not found or inactive.')
            return redirect(reverse('admin_panel:notification_compose'))
        users = get_group_users(group)
    else:
        messages.error(request, 'No audience selected.')
        return redirect(reverse('admin_panel:notification_compose'))

    # Send the notification
    stats = send_notification_to_users(notification, users, send_email=send_email, user_type='gamer')
    messages.success(
        request,
        f"✅ Notification sent successfully! "
        f"{stats['created']} users notified, {stats['failed']} failed."
    )
    return redirect(reverse('admin_panel:notification_hub'))


@admin_required
def admin_send_notification(request):
    from notifications.services import send_notification_to_users, get_group_users
    from notifications.models import NotificationGroup, Notification
    from accounts.models import Gamer

    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)

    object_id = request.POST.get('object_id') or request.POST.get('notification_id')
    if not object_id:
        messages.error(request, 'No notification specified to send.')
        return redirect(reverse('admin_panel:notification_hub'))

    notification = Notification.objects.filter(pk=object_id).first()
    if not notification:
        messages.error(request, 'Notification not found.')
        return redirect(reverse('admin_panel:notification_hub'))

    send_email = request.POST.get('send_email') == 'on'
    target_all = request.POST.get('target_all') == 'on'
    target_group_id = request.POST.get('target_group')

    if target_all:
        users = Gamer.objects.all()
    elif target_group_id:
        group = NotificationGroup.objects.filter(pk=target_group_id, is_active=True).first()
        if not group:
            messages.error(request, 'Selected group not found or inactive.')
            return redirect(f"{reverse('admin_panel:notification_hub')}?section=notifications&object_id={notification.pk}")
        users = get_group_users(group)
    else:
        messages.error(request, 'No audience selected.')
        return redirect(f"{reverse('admin_panel:notification_hub')}?section=notifications&object_id={notification.pk}")

    stats = send_notification_to_users(notification, users, send_email=send_email, user_type='gamer')
    messages.success(request, f"Notification queued: {stats['created']} created, {stats['failed']} failed.")
    return redirect(f"{reverse('admin_panel:notification_hub')}?section=notifications&object_id={notification.pk}")


# Game Management Views
@admin_required
def admin_game_list(request):
    games_list = Game.objects.all().order_by('-created_at')
    query = request.GET.get('q')
    genre_id = request.GET.get('genre')
    platform_id = request.GET.get('platform')
    status = request.GET.get('status')

    if query:
        games_list = games_list.filter(Q(name__icontains=query) | Q(integer_id__icontains=query))
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

    paginator = Paginator(games_list, 15)
    page_number = request.GET.get('page')
    games = paginator.get_page(page_number)

    seven_days_ago = timezone.now() - timedelta(days=7)

    context = {
        'games': games,
        'all_genres': Genre.objects.all().order_by('name'),
        'all_platforms': Platform.objects.all().order_by('name'),
        'total_games': Game.objects.count(),
        'total_categories': PlatformCategory.objects.count(),
        'total_platforms': Platform.objects.count(),
        'total_genres': Genre.objects.count(),
        'new_games_this_week': Game.objects.filter(created_at__gte=seven_days_ago).count(),
        'new_platforms_this_week': Platform.objects.filter(created_at__gte=seven_days_ago).count(),
        'form': GameForm(),
        'pending_competitions_count': Competition.objects.filter(status='pending').count(),
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
            'game_id': game.integer_id, 'name': game.name, 'description': game.description,
            'is_verified': game.is_verified, 'is_active': game.is_active,
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


# --- COMPETITION MANAGEMENT ---
@admin_required
def admin_competition_create(request):
    if request.method == 'POST':
        form = CompetitionAdminCreateForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    competition = form.save(commit=False)
                    competition.created_by = request.user
                    competition.status = 'registration'
                    competition.approved_at = timezone.now()
                    competition.save()
                    try:
                        CompetitionAuditLog.objects.create(
                            competition=competition, action='approve',
                            performed_by_label=request.user.get_username(),
                            details='Competition created and approved by admin.'
                        )
                    except Exception:
                        logger.exception('Failed to create audit log for admin-created competition')
                    schedule_competition_jobs(competition)
                    EmailManager.send_competition_announced_to_gamers(competition)
                    EmailManager.send_competition_approved(competition)
                messages.success(request, f"Competition '{competition.name}' created and scheduled successfully.")
                return redirect('admin_panel:competition_detail', slug=competition.slug)
            except Exception as e:
                logger.error(f"Competition creation error: {e}")
                messages.error(request, f"Error creating competition: {str(e)}")
    else:
        form = CompetitionAdminCreateForm()

    context = {
        'form': form, 'page_title': 'Create Competition',
        'all_shops': Shop.objects.filter(is_approved=True).order_by('name'),
        'pending_competitions_count': Competition.objects.filter(status='pending').count(),
    }
    return render(request, 'admin_panel/competitions/admin_competition_create.html', context)


@admin_required
def get_shop_resources(request):
    shop_id = request.GET.get('shop_id')
    if not shop_id:
        return JsonResponse({'error': 'Missing shop_id'}, status=400)

    try:
        shop = Shop.objects.get(id=shop_id, is_approved=True)
    except Shop.DoesNotExist:
        return JsonResponse({'error': 'Shop not found'}, status=404)

    games = list(shop.games_available.filter(is_active=True).values('id', 'name'))
    platforms = list(Platform.objects.filter(shop_consoles__shop=shop).values('id', 'name'))

    return JsonResponse({
        'games': games,
        'platforms': platforms
    })


@admin_required
def admin_competition_list(request):
    competitions_list = Competition.objects.all().select_related(
        'game', 'platform', 'shop', 'created_by'
    ).order_by('-created_at')

    query = request.GET.get('q')
    status = request.GET.get('status')
    prize_type = request.GET.get('prize_type')
    shop_id = request.GET.get('shop')

    if query:
        competitions_list = competitions_list.filter(
            Q(name__icontains=query) | Q(game__name__icontains=query) | Q(shop__name__icontains=query))
    if status:
        competitions_list = competitions_list.filter(status=status)
    if prize_type:
        competitions_list = competitions_list.filter(prize_type=prize_type)
    if shop_id:
        competitions_list = competitions_list.filter(shop__id=shop_id)

    paginator = Paginator(competitions_list, 20)
    page_number = request.GET.get('page')
    competitions = paginator.get_page(page_number)
    seven_days_ago = timezone.now() - timedelta(days=7)

    context = {
        'competitions': competitions,
        'all_shops': Shop.objects.filter(is_approved=True).order_by('name'),
        'total_competitions': Competition.objects.count(),
        'pending_competitions_count': Competition.objects.filter(status='pending').count(),
        'live_competitions': Competition.objects.filter(status__in=['registration', 'ongoing']).count(),
        'completed_competitions': Competition.objects.filter(status='completed').count(),
        'new_this_week': Competition.objects.filter(created_at__gte=seven_days_ago).count(),
    }
    return render(request, 'admin_panel/competitions/admin_competitions.html', context)


@admin_required
def admin_competition_detail(request, slug):
    try:
        competition = Competition.objects.select_related('game', 'platform', 'shop', 'created_by').get(slug=slug)
    except Competition.DoesNotExist:
        try:
            competition = Competition.objects.select_related('game', 'platform', 'shop', 'created_by').get(integer_id=int(slug))
        except (Competition.DoesNotExist, ValueError):
            raise Http404("Competition not found.")

    registrations = competition.registrations.filter(is_cancelled=False).select_related('gamer').order_by('registered_at')
    results = competition.results.select_related('gamer').order_by('rank')
    checked_in_count = registrations.filter(checked_in=True).count()
    no_show_count = registrations.count() - checked_in_count

    approval_form = None
    edit_prizes_form = None
    if competition.status == 'pending':
        initial_data = {'rules': competition.get_rules_for_admin_editing()}
        approval_form = CompetitionApprovalForm(instance=competition, initial=initial_data)
    elif competition.status in ['registration', 'ongoing']:
        edit_prizes_form = CompetitionEditPrizesForm(instance=competition)

    context = {
        'competition': competition, 'registrations': registrations, 'results': results,
        'registered_count': competition.registered_count(), 'checked_in_count': checked_in_count,
        'no_show_count': no_show_count, 'approval_form': approval_form,
        'edit_prizes_form': edit_prizes_form, 'full_rules': competition.get_full_rules(),
        'pending_competitions_count': Competition.objects.filter(status='pending').count(),
    }
    return render(request, 'admin_panel/competitions/admin_competition_detail.html', context)


# Admin competition action views
@admin_required
def admin_competition_approve(request, slug):
    try:
        competition = Competition.objects.get(slug=slug)
        if competition.status not in ['pending', 'rejected']:
            return JsonResponse({'success': False, 'message': f'Competition is already {competition.status}.'}, status=400)
    except Competition.DoesNotExist:
        try:
            competition = Competition.objects.get(integer_id=int(slug))
            if competition.status not in ['pending', 'rejected']:
                return JsonResponse({'success': False, 'message': f'Competition is already {competition.status}.'}, status=400)
        except (Competition.DoesNotExist, ValueError):
            return JsonResponse({'success': False, 'message': 'Competition not found.'}, status=404)

    if request.method == 'POST':
        if request.content_type == 'application/json':
            form = CompetitionApprovalForm(instance=competition)
        else:
            form = CompetitionApprovalForm(request.POST, instance=competition)
        if form.is_valid():
            try:
                CompetitionService.approve_competition(competition, form, performed_by_label=request.user.get_username())
                return JsonResponse({'success': True, 'message': f"'{competition.name}' approved and is now in registration."})
            except Exception as e:
                logger.error(f"Competition approval error: {e}")
                return JsonResponse({'success': False, 'message': 'Approval failed. Please try again.'})
        else:
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    return JsonResponse({'success': False, 'message': 'Invalid request.'}, status=405)


@admin_required
def admin_competition_reject(request, slug):
    try:
        competition = Competition.objects.get(slug=slug)
        if competition.status != 'pending':
            return JsonResponse({'success': False, 'message': f'Competition is already {competition.status}.'}, status=400)
    except Competition.DoesNotExist:
        try:
            competition = Competition.objects.get(integer_id=int(slug))
            if competition.status != 'pending':
                return JsonResponse({'success': False, 'message': f'Competition is already {competition.status}.'}, status=400)
        except (Competition.DoesNotExist, ValueError):
            return JsonResponse({'success': False, 'message': 'Competition not found.'}, status=404)

    if request.method == 'POST':
        if request.content_type == 'application/json':
            import json as _json
            try:
                payload = _json.loads(request.body.decode('utf-8') or '{}')
            except Exception:
                payload = {}
            form = CompetitionRejectionForm(payload, instance=competition)
        else:
            form = CompetitionRejectionForm(request.POST, instance=competition)
        if form.is_valid():
            try:
                CompetitionService.reject_competition(competition, form, performed_by_label=request.user.get_username())
                return JsonResponse({'success': True, 'message': f"'{competition.name}' rejected. Arena owner notified."})
            except Exception as e:
                logger.error(f"Competition rejection error: {e}")
                return JsonResponse({'success': False, 'message': 'Rejection failed. Please try again.'})
        else:
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    return JsonResponse({'success': False, 'message': 'Invalid request.'}, status=405)


@admin_required
def admin_confirm_checkins(request, slug):
    try:
        competition = Competition.objects.get(slug=slug)
        if competition.status != 'ongoing':
            return JsonResponse({'success': False, 'message': f'Competition is in {competition.status} status, not ongoing.'}, status=400)
    except Competition.DoesNotExist:
        try:
            competition = Competition.objects.get(integer_id=int(slug))
            if competition.status != 'ongoing':
                return JsonResponse({'success': False, 'message': f'Competition is in {competition.status} status, not ongoing.'}, status=400)
        except (Competition.DoesNotExist, ValueError):
            return JsonResponse({'success': False, 'message': 'Competition not found.'}, status=404)

    if request.method == 'POST':
        try:
            CompetitionService.confirm_checkins(competition, performed_by_label=request.user.get_username())
            return JsonResponse({'success': True, 'message': 'Check-ins confirmed. Arena owner notified to submit results.'})
        except Exception as e:
            logger.error(f"Confirm checkins error: {e}")
            return JsonResponse({'success': False, 'message': 'Failed. Please try again.'})
    return JsonResponse({'success': False, 'message': 'Invalid request.'}, status=405)


@admin_required
def admin_verify_results(request, slug):
    competition = get_object_or_404(Competition, slug=slug)
    if request.method == 'POST':
        try:
            CompetitionService.verify_results(competition, performed_by=request.user, performed_by_label=request.user.get_username())
            return JsonResponse({'success': True, 'message': 'Results verified and winners notified.'})
        except Exception as e:
            logger.error(f"Verify results error: {e}")
            return JsonResponse({'success': False, 'message': f'Failed: {str(e)}'})
    return JsonResponse({'success': False, 'message': 'Invalid request.'}, status=405)


@admin_required
def admin_competition_suspend(request, slug):
    try:
        competition = Competition.objects.get(slug=slug)
    except Competition.DoesNotExist:
        try:
            competition = Competition.objects.get(integer_id=int(slug))
        except (Competition.DoesNotExist, ValueError):
            return JsonResponse({'success': False, 'message': 'Competition not found.'}, status=404)

    if competition.status in ['completed', 'suspended', 'rejected']:
        return JsonResponse({'success': False, 'message': f'Cannot suspend a competition in {competition.status} status.'}, status=400)

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request.'}, status=405)

    if request.content_type == 'application/json':
        import json as _json
        try:
            payload = _json.loads(request.body.decode('utf-8') or '{}')
        except Exception:
            payload = {}
        form = CompetitionSuspendForm(payload)
    else:
        form = CompetitionSuspendForm(request.POST)

    if not form.is_valid():
        return JsonResponse({'success': False, 'errors': form.errors}, status=400)

    try:
        competition, refund_results = CompetitionService.suspend_competition(
            competition, reason=form.cleaned_data['suspension_reason'],
            performed_by=request.user, performed_by_label=request.user.get_username(),
        )
        return JsonResponse({'success': True, 'message': f"'{competition.name}' suspended. {refund_results['refunded']} refund(s) processed.", 'refund_results': refund_results})
    except Exception as e:
        logger.error(f"Competition suspension error: {e}")
        return JsonResponse({'success': False, 'message': 'Suspension failed. Please try again.'})


@admin_required
def admin_competition_edit_prizes(request, slug):
    try:
        competition = Competition.objects.get(slug=slug)
    except Competition.DoesNotExist:
        try:
            competition = Competition.objects.get(integer_id=int(slug))
        except (Competition.DoesNotExist, ValueError):
            return JsonResponse({'success': False, 'message': 'Competition not found.'}, status=404)

    if competition.status not in ['registration', 'ongoing', 'pending']:
        return JsonResponse({'success': False, 'message': f'Cannot edit prizes for competition in {competition.status} status.'}, status=400)

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request.'}, status=405)

    form = CompetitionEditPrizesForm(request.POST, instance=competition)
    if not form.is_valid():
        return JsonResponse({'success': False, 'errors': form.errors}, status=400)

    try:
        CompetitionService.edit_prizes(competition, form, performed_by=request.user, performed_by_label=request.user.get_username())
        return JsonResponse({'success': True, 'message': 'Prize details updated successfully.'})
    except Exception as e:
        logger.error(f"Edit prizes error: {e}")
        return JsonResponse({'success': False, 'message': 'Failed to update prize details.'})


@admin_required
def admin_competition_edit_results(request, slug):
    competition = get_object_or_404(Competition, slug=slug)
    if not competition.results.exists():
        return JsonResponse({'success': False, 'message': 'No results to edit.'}, status=400)
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request.'}, status=405)

    import json as _json
    try:
        payload = _json.loads(request.body.decode('utf-8') or '{}')
        results_data = payload.get('results', [])
    except Exception:
        return JsonResponse({'success': False, 'message': 'Invalid JSON payload.'}, status=400)

    if not results_data:
        return JsonResponse({'success': False, 'message': 'No result data provided.'}, status=400)

    try:
        CompetitionService.edit_results(competition, results_data, performed_by=request.user, performed_by_label=request.user.get_username())
        return JsonResponse({'success': True, 'message': 'Results updated and gamers notified.'})
    except Exception as e:
        logger.error(f"Edit results error: {e}")
        return JsonResponse({'success': False, 'message': f'Failed: {str(e)}'})


# Updated User Detail (removed previous simple version)
@admin_required
def admin_user_toggle_status(request, user_id):
    messages.warning(request, "Status toggle is currently disabled due to model constraints.")
    return redirect('admin_panel:user_detail', user_id=user_id)


# Shop Management
@admin_required
def admin_shop_list(request):
    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    city_filter = request.GET.get('city', '')

    shops = Shop.objects.all().order_by('-created_at')

    if query:
        shops = shops.filter(Q(name__icontains=query) | Q(city__icontains=query) | Q(location__icontains=query))
    if status_filter == 'approved':
        shops = shops.filter(is_approved=True)
    elif status_filter == 'pending':
        shops = shops.filter(is_approved=False)
    if city_filter:
        shops = shops.filter(city__icontains=city_filter)

    paginator = Paginator(shops, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # KPI stats
    total_shops = Shop.objects.count()
    approved_shops = Shop.objects.filter(is_approved=True).count()
    pending_shops = Shop.objects.filter(is_approved=False).count()

    # Get all unique cities for filter
    cities = Shop.objects.values_list('city', flat=True).distinct().order_by('city')

    context = {
        'shops': page_obj, 'query': query, 'selected_status': status_filter,
        'selected_city': city_filter, 'total_shops': total_shops,
        'approved_shops': approved_shops, 'pending_shops': pending_shops,
        'cities': cities,
        'pending_competitions_count': Competition.objects.filter(status='pending').count(),
    }
    return render(request, 'admin_panel/shops/admin_shop_list.html', context)


@admin_required
def admin_shop_detail(request, shop_id):
    shop = get_object_or_404(Shop, id=shop_id)
    if request.method == 'POST':
        form = ShopForm(request.POST, instance=shop)
        if form.is_valid():
            form.save()
            messages.success(request, "Arena details updated.")
            return redirect('admin_panel:shop_detail', shop_id=shop_id)
    else:
        form = ShopForm(instance=shop)

    context = {
        'shop': shop, 'form': form,
        'pending_competitions_count': Competition.objects.filter(status='pending').count(),
    }
    return render(request, 'admin_panel/shops/admin_shop_detail.html', context)


@admin_required
def admin_shop_approve(request, shop_id):
    shop = get_object_or_404(Shop, id=shop_id)
    shop.is_approved = True
    shop.approved_at = timezone.now()
    shop.save()
    messages.success(request, f"Shop '{shop.name}' has been approved.")
    return redirect('admin_panel:shop_detail', shop_id=shop_id)


@admin_required
def admin_shop_reject(request, shop_id):
    shop = get_object_or_404(Shop, id=shop_id)
    shop.is_approved = False
    shop.save()
    messages.warning(request, f"Shop '{shop.name}' has been rejected.")
    return redirect('admin_panel:shop_detail', shop_id=shop_id)


# Payment Management
@admin_required
def admin_payment_list(request):
    transactions = MpesaTransaction.objects.all().order_by('-created_at')
    paginator = Paginator(transactions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'transactions': page_obj,
        'pending_competitions_count': Competition.objects.filter(status='pending').count(),
    }
    return render(request, 'admin_panel/payments/admin_payment_list.html', context)


@admin_required
def admin_payment_detail(request, transaction_id):
    transaction_obj = get_object_or_404(MpesaTransaction, id=transaction_id)
    context = {
        'transaction': transaction_obj,
        'pending_competitions_count': Competition.objects.filter(status='pending').count(),
    }
    return render(request, 'admin_panel/payments/admin_payment_detail.html', context)


# Progression Management
@admin_required
def admin_level_list(request):
    levels = Level.objects.all().order_by('order')
    context = {
        'levels': levels,
        'pending_competitions_count': Competition.objects.filter(status='pending').count(),
    }
    return render(request, 'admin_panel/progression/admin_level_list.html', context)


@admin_required
def admin_level_save(request):
    level_id = request.POST.get('level_id')
    if level_id:
        level = get_object_or_404(Level, id=level_id)
        form = LevelForm(request.POST, request.FILES, instance=level)
    else:
        form = LevelForm(request.POST, request.FILES)
    if form.is_valid():
        form.save()
        messages.success(request, "Level saved successfully.")
    else:
        messages.error(request, "Error saving level.")
    return redirect('admin_panel:level_list')


@admin_required
def admin_achievement_list(request):
    achievements = Achievement.objects.all().order_by('category', 'target_value', 'name')
    context = {
        'achievements': achievements,
        'category_choices': Achievement.CATEGORY_CHOICES,
        'pending_competitions_count': Competition.objects.filter(status='pending').count(),
    }
    return render(request, 'admin_panel/progression/admin_achievement_list.html', context)


@admin_required
def admin_achievement_save(request):
    achievement_id = request.POST.get('achievement_id')
    if achievement_id:
        achievement = get_object_or_404(Achievement, id=achievement_id)
        form = AchievementForm(request.POST, request.FILES, instance=achievement)
    else:
        form = AchievementForm(request.POST, request.FILES)
    if form.is_valid():
        form.save()
        messages.success(request, "Achievement saved successfully.")
    else:
        logger.warning(f"Achievement form errors: {form.errors.as_json()}")
        messages.error(request, "Error saving achievement.")
    return redirect('admin_panel:achievement_list')


@admin_required
def admin_progression_stats(request):
    query = request.GET.get('q', '').strip()
    stats_qs = GamerStats.objects.select_related('gamer').order_by('-updated_at')
    if query:
        stats_qs = stats_qs.filter(
            Q(gamer__custom_username__icontains=query) | Q(gamer__first_name__icontains=query) |
            Q(gamer__last_name__icontains=query) | Q(gamer__email__icontains=query)
        )
    paginator = Paginator(stats_qs, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'stats': page_obj, 'query': query,
        'total_gamers_with_stats': stats_qs.count(),
        'pending_competitions_count': Competition.objects.filter(status='pending').count(),
    }
    return render(request, 'admin_panel/progression/admin_progression_stats.html', context)


@admin_required
def admin_progression_seed(request):
    if request.method != 'POST':
        raise Http404
    action = request.POST.get('seed_action', '').strip()
    command_map = {'levels': ['seed_levels'], 'achievements': ['seed_achievements'], 'all': ['seed_levels', 'seed_achievements']}
    commands = command_map.get(action)
    if not commands:
        messages.error(request, 'Invalid seed action selected.')
        return redirect('admin_panel:progression_stats')
    buffer = StringIO()
    try:
        for command_name in commands:
            call_command(command_name, stdout=buffer)
        messages.success(request, f"Seed completed for: {', '.join(commands)}")
    except Exception as exc:
        logger.exception('Progression seed failed.')
        messages.error(request, f"Seeding failed: {exc}")
    output_lines = [line for line in buffer.getvalue().splitlines() if line.strip()]
    if output_lines:
        messages.info(request, f"Seeder output: {' | '.join(output_lines[-3:])}")
    return redirect('admin_panel:progression_stats')


@admin_required
def admin_progression_stats_action(request, stats_id):
    if request.method != 'POST':
        raise Http404
    stats = get_object_or_404(GamerStats, id=stats_id)
    metric = request.POST.get('metric', '').strip()
    operation = request.POST.get('operation', '').strip()
    amount_raw = request.POST.get('amount', '1').strip()
    editable_metrics = {
        'communities_joined', 'gamers_invited', 'comments_made', 'posts_made',
        'posts_with_10_likes', 'posts_with_25_likes', 'posts_with_75_likes',
        'competitions_joined', 'competitions_won', 'leagues_joined', 'leagues_won', 'login_streak_days',
    }
    if metric not in editable_metrics:
        messages.error(request, 'Invalid metric selected.')
        return redirect('admin_panel:progression_stats')
    try:
        amount = int(amount_raw)
    except ValueError:
        amount = 1
    if amount < 1:
        amount = 1
    if operation == 'increment':
        GamerStats.objects.filter(id=stats.id).update(**{metric: F(metric) + amount})
        messages.success(request, f"Incremented {metric} by {amount} for {stats.gamer}.")
    elif operation == 'decrement':
        current_value = getattr(stats, metric)
        new_value = max(current_value - amount, 0)
        setattr(stats, metric, new_value)
        stats.save(update_fields=[metric])
        messages.success(request, f"Decremented {metric} by {amount} for {stats.gamer}.")
    elif operation == 'reset':
        setattr(stats, metric, 0)
        stats.save(update_fields=[metric])
        messages.success(request, f"Reset {metric} for {stats.gamer}.")
    else:
        messages.error(request, 'Invalid operation selected.')
    query = request.POST.get('q', '').strip()
    page = request.POST.get('page', '').strip()
    params = []
    if query:
        params.append(f"q={query}")
    if page:
        params.append(f"page={page}")
    if params:
        return redirect(f"{reverse('admin_panel:progression_stats')}?{'&'.join(params)}")
    return redirect('admin_panel:progression_stats')