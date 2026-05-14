from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
import json
from .models import Activity, ActivityLog, Level, Achievement, GamerAchievement


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    """
    Gamer-centric activity tracking for progression, achievements, and gaming milestones.
    """
    list_display = (
        'gamer_link', 'activity_type_badge', 'description_short',
        'timestamp', 'has_metadata_indicator'
    )
    list_filter = (
        'activity_type', 'timestamp',
        ('gamer', admin.RelatedOnlyFieldListFilter),
    )
    search_fields = (
        'gamer__email', 'gamer__custom_username', 'gamer__first_name',
        'gamer__last_name', 'description'
    )
    readonly_fields = ('timestamp', 'gamer', 'activity_type', 'description', 'metadata_display')
    date_hierarchy = 'timestamp'
    list_per_page = 30
    ordering = ('-timestamp',)
    
    fieldsets = (
        ('Activity Information', {
            'fields': ('gamer_link_display', 'activity_type_badge_display', 'description')
        }),
        ('Metadata', {
            'fields': ('metadata_display',),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': ('timestamp',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('gamer')
    
    def gamer_link(self, obj):
        """Display gamer email with link to gamer admin"""
        if obj.gamer:
            return format_html(
                '<a href="/admin/accounts/gamer/{}/change/">{}</a>',
                obj.gamer.id,
                obj.gamer.email
            )
        return '—'
    gamer_link.short_description = 'Gamer'
    
    def gamer_link_display(self, obj):
        return f"{obj.gamer.email} ({obj.gamer.custom_username})" if obj.gamer else "—"
    gamer_link_display.short_description = 'Gamer'
    
    def activity_type_badge(self, obj):
        """Display activity type as a colored badge"""
        badge_colors = {
            'level_up': '#10b981',
            'achievement_earned': '#f59e0b',
            'profile_completed': '#3b82f6',
            'profile_updated': '#8b5cf6',
            'game_added': '#06b6d4',
            'game_removed': '#ef4444',
            'competition_registered': '#0891b2',
            'competition_checkedin': '#ec4899',
            'competition_completed': '#14b8a6',
            'competition_won': '#d97706',
            'login': '#059669',
            'logout': '#6366f1',
            'system': '#6b7280',
        }
        color = badge_colors.get(obj.activity_type, '#6b7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 8px;border-radius:3px;font-size:11px;font-weight:600;">{}</span>',
            color, obj.get_activity_type_display()
        )
    activity_type_badge.short_description = 'Type'
    
    def activity_type_badge_display(self, obj):
        return obj.get_activity_type_display()
    activity_type_badge_display.short_description = 'Activity Type'
    
    def description_short(self, obj):
        """Show truncated description"""
        if len(obj.description) > 60:
            return obj.description[:60] + '...'
        return obj.description
    description_short.short_description = 'Description'
    
    def has_metadata_indicator(self, obj):
        """Show indicator if metadata exists"""
        if obj.metadata:
            return format_html('<span style="color:#10b981;font-weight:bold;">✓ Has Data</span>')
        return '—'
    has_metadata_indicator.short_description = 'Metadata'
    
    def metadata_display(self, obj):
        """Pretty-print JSON metadata"""
        if obj.metadata:
            try:
                json_str = json.dumps(obj.metadata, indent=2, ensure_ascii=False)
                return format_html(
                    '<pre style="background:#f3f4f6;padding:10px;border-radius:4px;overflow:auto;max-width:500px;">{}</pre>',
                    mark_safe(json_str)
                )
            except Exception:
                return str(obj.metadata)
        return '—'
    metadata_display.short_description = 'Metadata'
    
    def has_add_permission(self, request):
        """Prevent manual creation of activities"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of activity logs"""
        return False


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    """
    System-wide activity logging for audit trails and security events.
    """
    list_display = (
        'action_type_badge', 'actor_link', 'gamer_link', 'description_short',
        'timestamp'
    )
    list_filter = (
        'action_type', 'timestamp',
        ('actor', admin.RelatedOnlyFieldListFilter),
        ('gamer', admin.RelatedOnlyFieldListFilter),
    )
    search_fields = (
        'description', 'actor__email', 'gamer__email',
        'gamer__custom_username'
    )
    readonly_fields = (
        'timestamp', 'action_type', 'actor', 'gamer',
        'description', 'meta_data_display'
    )
    date_hierarchy = 'timestamp'
    list_per_page = 30
    ordering = ('-timestamp',)
    
    fieldsets = (
        ('Action Information', {
            'fields': ('action_type', 'actor_link_display', 'gamer_link_display', 'description')
        }),
        ('Metadata', {
            'fields': ('meta_data_display',),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': ('timestamp',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('actor', 'gamer')
    
    def action_type_badge(self, obj):
        """Display action type as a colored badge"""
        badge_colors = {
            'CREATE': '#10b981',
            'UPDATE': '#3b82f6',
            'DELETE': '#ef4444',
            'SECURITY': '#f59e0b',
            'SYSTEM': '#6b7280',
        }
        color = badge_colors.get(obj.action_type, '#6b7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 8px;border-radius:3px;font-size:11px;font-weight:600;">{}</span>',
            color, obj.get_action_type_display()
        )
    action_type_badge.short_description = 'Action'
    
    def actor_link(self, obj):
        """Display actor with link if possible"""
        if obj.actor:
            return format_html(
                '<a href="/admin/accounts/account/{}/change/">{}</a>',
                obj.actor.id, obj.actor.email
            )
        return format_html('<span style="color:#999;">System</span>')
    actor_link.short_description = 'Actor'
    
    def actor_link_display(self, obj):
        return f"{obj.actor.email}" if obj.actor else "System"
    actor_link_display.short_description = 'Actor'
    
    def gamer_link(self, obj):
        """Display gamer with link if present"""
        if obj.gamer:
            return format_html(
                '<a href="/admin/accounts/gamer/{}/change/">{}</a>',
                obj.gamer.id, obj.gamer.email
            )
        return '—'
    gamer_link.short_description = 'Gamer'
    
    def gamer_link_display(self, obj):
        return f"{obj.gamer.email}" if obj.gamer else "—"
    gamer_link_display.short_description = 'Related Gamer'
    
    def description_short(self, obj):
        """Show truncated description"""
        if len(obj.description) > 60:
            return obj.description[:60] + '...'
        return obj.description
    description_short.short_description = 'Description'
    
    def meta_data_display(self, obj):
        """Pretty-print JSON metadata"""
        if obj.meta_data:
            try:
                json_str = json.dumps(obj.meta_data, indent=2, ensure_ascii=False)
                return format_html(
                    '<pre style="background:#f3f4f6;padding:10px;border-radius:4px;overflow:auto;max-width:500px;">{}</pre>',
                    mark_safe(json_str)
                )
            except Exception:
                return str(obj.meta_data)
        return '—'
    meta_data_display.short_description = 'Metadata'
    
    def has_add_permission(self, request):
        """Prevent manual creation of activity logs"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of activity logs"""
        return False


@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
    """
    Progression levels for gamer advancement.
    """
    list_display = ('order', 'name', 'required_points', 'gamer_count_display', 'has_badge_indicator')
    list_display_links = ('name',)
    list_filter = ('order',)
    search_fields = ('name',)
    readonly_fields = ('gamer_count_display', 'badge_preview')
    list_editable = ('order',)
    ordering = ('order',)
    
    fieldsets = (
        ('Level Information', {
            'fields': ('name', 'order', 'required_points')
        }),
        ('Badge', {
            'fields': ('badge_image', 'badge_preview'),
            'classes': ('collapse',)
        }),
    )
    
    def gamer_count_display(self, obj):
        """Display number of gamers at this level"""
        from accounts.models import Gamer
        count = Gamer.objects.filter(current_level=obj).count()
        return format_html(
            '<span style="background:#e0e7ff;color:#4338ca;padding:3px 8px;border-radius:3px;font-weight:600;">{}</span>',
            count
        )
    gamer_count_display.short_description = 'Gamers at Level'
    
    def has_badge_indicator(self, obj):
        """Show indicator if badge exists"""
        if obj.badge_image:
            return format_html('<span style="color:#10b981;font-weight:bold;">✓</span>')
        return '—'
    has_badge_indicator.short_description = 'Badge'
    
    def badge_preview(self, obj):
        """Preview badge image"""
        if obj.badge_image:
            return format_html(
                '<img src="{}" style="max-width:100px;max-height:100px;border-radius:4px;" />',
                obj.badge_image.url
            )
        return '—'
    badge_preview.short_description = 'Badge Preview'


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    """
    Gamification achievements that users can unlock.
    """
    list_display = ('name', 'xp', 'unlock_count_display', 'condition_key', 'has_badge_indicator')
    list_filter = ('xp',)
    search_fields = ('name', 'description', 'condition_key')
    readonly_fields = ('unlock_count_display', 'badge_preview')
    
    fieldsets = (
        ('Achievement Information', {
            'fields': ('name', 'description', 'condition_key')
        }),
        ('Rewards', {
            'fields': ('xp',)
        }),
        ('Badge', {
            'fields': ('badge_image', 'badge_preview'),
            'classes': ('collapse',)
        }),
    )
    
    def unlock_count_display(self, obj):
        """Display number of times unlocked"""
        count = GamerAchievement.objects.filter(achievement=obj).count()
        return format_html(
            '<span style="background:#dcfce7;color:#166534;padding:3px 8px;border-radius:3px;font-weight:600;">{}</span>',
            count
        )
    unlock_count_display.short_description = 'Times Unlocked'
    
    def has_badge_indicator(self, obj):
        """Show indicator if badge exists"""
        if obj.badge_image:
            return format_html('<span style="color:#10b981;font-weight:bold;">✓</span>')
        return '—'
    has_badge_indicator.short_description = 'Badge'
    
    def badge_preview(self, obj):
        """Preview badge image"""
        if obj.badge_image:
            return format_html(
                '<img src="{}" style="max-width:100px;max-height:100px;border-radius:4px;" />',
                obj.badge_image.url
            )
        return '—'
    badge_preview.short_description = 'Badge Preview'


@admin.register(GamerAchievement)
class GamerAchievementAdmin(admin.ModelAdmin):
    """
    Track which achievements each gamer has unlocked.
    """
    list_display = ('gamer_link', 'achievement_link', 'unlocked_at', 'xp_display')
    list_filter = (
        ('achievement', admin.RelatedOnlyFieldListFilter),
        ('gamer', admin.RelatedOnlyFieldListFilter),
        'unlocked_at',
    )
    search_fields = (
        'gamer__email', 'gamer__custom_username',
        'gamer__first_name', 'gamer__last_name',
        'achievement__name'
    )
    readonly_fields = ('unlocked_at', 'gamer', 'achievement')
    date_hierarchy = 'unlocked_at'
    list_per_page = 30
    ordering = ('-unlocked_at',)
    
    fieldsets = (
        ('Achievement Award', {
            'fields': ('gamer_link_display', 'achievement_link_display', 'unlocked_at')
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('gamer', 'achievement')
    
    def gamer_link(self, obj):
        """Display gamer with link"""
        return format_html(
            '<a href="/admin/accounts/gamer/{}/change/">{}</a>',
            obj.gamer.id, obj.gamer.email
        )
    gamer_link.short_description = 'Gamer'
    
    def gamer_link_display(self, obj):
        return f"{obj.gamer.email} ({obj.gamer.custom_username})"
    gamer_link_display.short_description = 'Gamer'
    
    def achievement_link(self, obj):
        """Display achievement with link"""
        return format_html(
            '<a href="/admin/activities/achievement/{}/change/">{}</a>',
            obj.achievement.id, obj.achievement.name
        )
    achievement_link.short_description = 'Achievement'
    
    def achievement_link_display(self, obj):
        return obj.achievement.name
    achievement_link_display.short_description = 'Achievement'
    
    def xp_display(self, obj):
        """Display XP earned"""
        return format_html(
            '<span style="background:#fef08a;color:#854d0e;padding:3px 8px;border-radius:3px;font-weight:600;">+{} XP</span>',
            obj.achievement.xp
        )
    xp_display.short_description = 'XP Earned'
    
    def has_add_permission(self, request):
        """Prevent manual creation - awards should only come from signals"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of achievement records"""
        return False