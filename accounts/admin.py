from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Q
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Account, Gamer, ShopOwner, PendingRegistration
from core.admin_utils import SafeDateHierarchyAdmin


@admin.register(Account)
class AccountAdmin(SafeDateHierarchyAdmin):
    list_display = ('email', 'first_name', 'last_name', 'phone', 'created_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('first_name', 'last_name', 'email', 'phone', 'uid')
    readonly_fields = ('created_at', 'updated_at', 'uid')
    ordering = ('-created_at',)
    list_per_page = 20
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'email', 'phone', 'uid')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Gamer)
class GamerAdmin(SafeDateHierarchyAdmin):
    list_display = (
        'email', 'custom_username', 'profile_completed_badge',
        'points_display', 'games_count', 'level_display',
        'created_at'
    )
    list_filter = (
        'profile_completed', 'date_joined', 'created_at',
        ('current_level', admin.RelatedOnlyFieldListFilter)
    )
    search_fields = (
        'first_name', 'last_name', 'email', 'custom_username',
        'location', 'bio'
    )
    readonly_fields = (
        'date_joined', 'last_login', 'created_at', 'updated_at',
        'activity_feed_link', 'points_history'
    )
    filter_horizontal = ('games',)
    list_per_page = 20
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Personal Info', {
            'fields': ('first_name', 'last_name', 'email', 'phone', 'uid')
        }),
        ('Gamer Profile', {
            'fields': ('custom_username', 'profile_picture', 'bio', 'about', 'date_of_birth', 'location')
        }),
        ('Gaming Info', {
            'fields': ('platforms', 'games', 'points', 'current_level')
        }),
        ('Account Status', {
            'fields': ('profile_completed', 'date_joined', 'last_login')
        }),
        ('Activity & History', {
            'fields': ('activity_feed_link', 'points_history'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related(
            'games', 'unlocked_achievements'
        ).select_related('current_level')
    
    def profile_completed_badge(self, obj):
        """Display profile completion status as badge"""
        if obj.profile_completed:
            return format_html(
                '<span style="background:#10b981;color:#fff;padding:3px 8px;border-radius:3px;font-size:11px;font-weight:600;">✓ Complete</span>'
            )
        return format_html(
            '<span style="background:#ef4444;color:#fff;padding:3px 8px;border-radius:3px;font-size:11px;font-weight:600;">⚠ Incomplete</span>'
        )
    profile_completed_badge.short_description = 'Profile'
    
    def points_display(self, obj):
        """Display points with color"""
        if obj.points >= 1000:
            color = '#d97706'  # gold
        elif obj.points >= 500:
            color = '#3b82f6'  # blue
        elif obj.points >= 100:
            color = '#10b981'  # green
        else:
            color = '#6b7280'  # gray
        
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 8px;border-radius:3px;font-weight:600;">{} pts</span>',
            color, obj.points
        )
    points_display.short_description = 'Points'
    
    def games_count(self, obj):
        """Display number of games with color"""
        count = obj.games.count()
        return format_html(
            '<span style="background:#e0e7ff;color:#4338ca;padding:3px 8px;border-radius:3px;font-weight:600;">{}</span>',
            count
        )
    games_count.short_description = 'Games'
    
    def level_display(self, obj):
        """Display current level if set"""
        if obj.current_level:
            return format_html(
                '<a href="/admin/activities/level/{}/change/" style="color:#f59e0b;font-weight:600;">{}</a>',
                obj.current_level.id, obj.current_level.name
            )
        return format_html('<span style="color:#999;">{}</span>', '—')
    level_display.short_description = 'Level'
    
    def activity_feed_link(self, obj):
        """Link to gamer's activity feed in admin"""
        url = f"/admin/activities/activity/?gamer__id={obj.id}"
        return format_html(
            '<a href="{}" target="_blank" class="button">View Activity Feed →</a>',
            url
        )
    activity_feed_link.short_description = 'Activity Timeline'
    
    def points_history(self, obj):
        """Display recent points awards"""
        from activities.models import Activity
        recent_activities = Activity.objects.filter(
            gamer=obj,
            activity_type__in=['level_up', 'achievement_earned', 'competition_won']
        ).order_by('-timestamp')[:5]
        
        if not recent_activities:
            return format_html('<span style="color:#999;">{}</span>', 'No recent activities')
        
        html = '<ul style="list-style:none;padding:0;margin:0;">'
        for activity in recent_activities:
            html += f'<li style="padding:3px 0;border-bottom:1px solid #e5e7eb;">'
            html += f'<strong>{activity.get_activity_type_display()}</strong> - {activity.timestamp.strftime("%b %d, %H:%M")}'
            html += '</li>'
        html += '</ul>'
        return mark_safe(html)
    points_history.short_description = 'Recent Activities'
    
    def platforms_display(self, obj):
        """Render JSONField list of platforms as a comma-separated string"""
        if not obj.platforms:
            return "—"
        try:
            return ", ".join([str(p) for p in obj.platforms])
        except Exception:
            return str(obj.platforms)
    platforms_display.short_description = 'Platforms'


@admin.register(ShopOwner)
class ShopOwnerAdmin(SafeDateHierarchyAdmin):
    list_display = (
        'email', 'shop_count_badge', 'approval_status',
        'date_joined', 'created_at'
    )
    list_filter = (
        'date_joined', 'created_at',
        ('shops', admin.RelatedOnlyFieldListFilter)
    )
    search_fields = ('first_name', 'last_name', 'email', 'shops__name')
    readonly_fields = (
        'date_joined', 'last_login', 'created_at', 'updated_at',
        'shops_list_display'
    )
    list_per_page = 20
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Personal Info', {
            'fields': ('first_name', 'last_name', 'email', 'phone', 'uid')
        }),
        ('Account Status', {
            'fields': ('date_joined', 'last_login', 'shops_list_display')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('shops')
    
    def shop_count_badge(self, obj):
        """Display shop count as badge"""
        count = obj.shops.count()
        return format_html(
            '<span style="background:#3b82f6;color:#fff;padding:3px 8px;border-radius:3px;font-weight:600;">{} Shop(s)</span>',
            count
        )
    shop_count_badge.short_description = 'Shops'
    
    def approval_status(self, obj):
        """Display approval status of owned shops"""
        approved = obj.shops.filter(is_approved=True).count()
        total = obj.shops.count()
        
        if total == 0:
            return format_html('<span style="color:#999;">{}</span>', '—')
        
        if approved == total:
            return format_html(
                '<span style="background:#10b981;color:#fff;padding:3px 8px;border-radius:3px;font-size:11px;font-weight:600;">{}</span>',
                '✓ All Approved'
            )
        return format_html(
            '<span style="background:#f59e0b;color:#fff;padding:3px 8px;border-radius:3px;font-size:11px;font-weight:600;">{}/{} Approved</span>',
            approved, total
        )
    approval_status.short_description = 'Shop Status'
    
    def shops_list_display(self, obj):
        """Display shops with links"""
        shops = obj.shops.all()
        if not shops:
            return '—'
        
        html = '<ul style="list-style:none;padding:0;margin:0;">'
        for shop in shops:
            approval_badge = '✓' if shop.is_approved else '⏳'
            html += f'<li style="padding:3px 0;">'
            html += f'<a href="/admin/shops/shop/{shop.id}/change/">{approval_badge} {shop.name}</a>'
            html += '</li>'
        html += '</ul>'
        return mark_safe(html)
    shops_list_display.short_description = 'Managed Shops'


@admin.register(PendingRegistration)
class PendingRegistrationAdmin(SafeDateHierarchyAdmin):
    list_display = (
        'email', 'first_name', 'last_name', 'role_badge', 'is_gwds_badge',
        'created_at'
    )
    list_filter = ('role', 'created_at')
    search_fields = ('email', 'first_name', 'last_name', 'phone', 'uid')
    readonly_fields = ('created_at', 'updated_at', 'uid')
    list_per_page = 20
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    actions = ['convert_to_gamer', 'convert_to_shop_owner', 'delete_pending']
    
    fieldsets = (
        ('Registration Details', {
            'fields': ('email', 'first_name', 'last_name', 'phone', 'is_gwds', 'role', 'uid')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def role_badge(self, obj):
        """Display role as colored badge"""
        colors = {
            'gamer': '#3b82f6',
            'shop_owner': '#10b981',
        }
        color = colors.get(obj.role, '#6b7280')
        label = obj.get_role_display() if hasattr(obj, 'get_role_display') else obj.role.replace('_', ' ').title()
        
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 8px;border-radius:3px;font-size:11px;font-weight:600;">{}</span>',
            color, label
        )
    role_badge.short_description = 'Role'

    def is_gwds_badge(self, obj):
        """Display PWD status as colored badge"""
        label = 'Yes' if obj.is_gwds else 'No'
        color = '#10b981' if obj.is_gwds else '#6b7280'
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 8px;border-radius:3px;font-size:11px;font-weight:600;">{}</span>',
            color, label
        )
    is_gwds_badge.short_description = 'GWDS'
    
    @admin.action(description='✓ Convert to Gamer Account')
    def convert_to_gamer(self, request, queryset):
        """Convert pending registrations to actual gamer accounts"""
        from .views import provision_account_from_pending
        count = 0
        
        for pending in queryset.filter(role='gamer'):
            try:
                provision_account_from_pending(pending)
                count += 1
            except Exception as e:
                pass
        
        self.message_user(request, f"✓ Converted {count} registration(s) to Gamer account(s).")
    
    @admin.action(description='✓ Convert to Shop Owner Account')
    def convert_to_shop_owner(self, request, queryset):
        """Convert pending registrations to shop owner accounts"""
        from .views import provision_account_from_pending
        count = 0
        
        for pending in queryset.filter(role='shop_owner'):
            try:
                provision_account_from_pending(pending)
                count += 1
            except Exception as e:
                pass
        
        self.message_user(request, f"✓ Converted {count} registration(s) to Shop Owner account(s).")
    
    @admin.action(description='✗ Delete Selected Pending Registrations')
    def delete_pending(self, request, queryset):
        """Delete pending registrations"""
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"✗ Deleted {count} pending registration(s).")