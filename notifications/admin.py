"""Admin interface for notifications app."""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Q
from .models import (
    Notification, NotificationRecipient, NotificationGroup, NotificationSchedule
)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Admin interface for managing notifications."""
    
    list_display = [
        'title_with_icon',
        'category',
        'importance_badge',
        'recipient_count',
        'created_at',
        'delivery_status_summary'
    ]
    list_filter = ['category', 'importance', 'is_system', 'created_at']
    search_fields = ['title', 'message']
    readonly_fields = [
        'created_at', 'updated_at', 'total_recipients', 'recipient_stats'
    ]
    
    fieldsets = (
        ('Content', {
            'fields': ('title', 'message', 'message_template')
        }),
        ('Categorization', {
            'fields': ('category', 'importance', 'is_system')
        }),
        ('Expiration', {
            'fields': ('expires_at',),
            'description': 'Auto-cleanup schedule: Critical (90d), High (30d), Medium (14d), Low (7d)'
        }),
        ('Statistics', {
            'fields': ('total_recipients', 'recipient_stats'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    ordering = ['-created_at']
    
    def title_with_icon(self, obj):
        """Display title with category icon."""
        icons = {
            'general': '📢',
            'system': '⚙️',
            'competition': '🏆',
            'payment': '💳',
            'achievement': '🎖️',
            'level_up': '⬆️',
            'account': '👤',
        }
        icon = icons.get(obj.category, '📧')
        return f"{icon} {obj.title}"
    title_with_icon.short_description = 'Notification'
    
    def importance_badge(self, obj):
        """Display importance as colored badge."""
        colors = {
            'low': '#6c757d',
            'medium': '#0dcaf0',
            'high': '#ffc107',
            'critical': '#dc3545',
        }
        color = colors.get(obj.importance, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_importance_display()
        )
    importance_badge.short_description = 'Importance'
    
    def recipient_count(self, obj):
        """Display total recipient count with link to recipients."""
        url = reverse('admin:notifications_notificationrecipient_changelist')
        return format_html(
            '<a href="{}?notification__id__exact={}">{} recipients</a>',
            url,
            obj.id,
            obj.total_recipients
        )
    recipient_count.short_description = 'Recipients'
    
    def delivery_status_summary(self, obj):
        """Display delivery status breakdown."""
        stats = obj.recipients.values('delivery_status').annotate(count=Count('id'))
        status_dict = {item['delivery_status']: item['count'] for item in stats}
        
        sent = status_dict.get('sent', 0)
        pending = status_dict.get('pending', 0)
        failed = status_dict.get('failed', 0)
        
        html = f"✅ {sent} sent"
        if pending > 0:
            html += f" | ⏳ {pending} pending"
        if failed > 0:
            html += f" | ❌ {failed} failed"
        
        return html
    delivery_status_summary.short_description = 'Delivery Status'
    
    def recipient_stats(self, obj):
        """Show statistics about recipients."""
        total = obj.recipients.count()
        read = obj.recipients.filter(is_read=True).count()
        unread = total - read
        
        read_rate = (read / total * 100) if total > 0 else 0
        
        return format_html(
            '<strong>Total:</strong> {}<br>'
            '<strong>Read:</strong> {} ({:.1f}%)<br>'
            '<strong>Unread:</strong> {}<br>',
            total, read, read_rate, unread
        )
    recipient_stats.short_description = 'Recipient Statistics'
    
    def get_queryset(self, request):
        """Optimize queryset with prefetch."""
        qs = super().get_queryset(request)
        return qs.prefetch_related('recipients')


@admin.register(NotificationRecipient)
class NotificationRecipientAdmin(admin.ModelAdmin):
    """Admin for tracking notification delivery to individual users."""
    
    list_display = [
        'notification_title',
        'user_link',
        'read_status_badge',
        'delivery_badge',
        'sent_at',
        'created_at'
    ]
    list_filter = ['is_read', 'delivery_status', 'created_at', 'notification__category']
    search_fields = ['notification__title', 'gamer__custom_username', 'gamer__email', 'shop_owner__email', 'admin_user__username']
    readonly_fields = ['notification', 'gamer', 'shop_owner', 'admin_user', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Notification & Recipient', {
            'fields': ('notification', 'gamer', 'shop_owner', 'admin_user')
        }),
        ('Read Status', {
            'fields': ('is_read', 'read_at')
        }),
        ('Delivery', {
            'fields': ('delivery_status', 'sent_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    ordering = ['-created_at']
    
    def notification_title(self, obj):
        """Link to notification."""
        url = reverse('admin:notifications_notification_change', args=[obj.notification.id])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            obj.notification.title
        )
    notification_title.short_description = 'Notification'
    
    def user_link(self, obj):
        """Link to user."""
        if obj.gamer:
            url = reverse('admin:accounts_gamer_change', args=[obj.gamer.id])
            return format_html(
                '<a href="{}">{}</a>',
                url,
                obj.gamer.custom_username
            )
        elif obj.shop_owner:
            url = reverse('admin:accounts_shopowner_change', args=[obj.shop_owner.id])
            return format_html(
                '<a href="{}">{}</a>',
                url,
                f"{obj.shop_owner.first_name} {obj.shop_owner.last_name}"
            )
        elif obj.admin_user:
            return obj.admin_user.username
        return "Unknown"
    user_link.short_description = 'User'
    
    def read_status_badge(self, obj):
        """Display read/unread status."""
        if obj.is_read:
            return format_html(
                '<span style="color: green; font-weight: bold;">✅ Read</span><br>'
                '<small>{}</small>',
                obj.read_at.strftime('%Y-%m-%d %H:%M') if obj.read_at else ''
            )
        return format_html('<span style="color: gray;">{}</span>', '○ Unread')
    read_status_badge.short_description = 'Read Status'
    
    def delivery_badge(self, obj):
        """Display delivery status with color."""
        colors = {
            'pending': ('#0dcaf0', '⏳'),
            'sent': ('#198754', '✅'),
            'failed': ('#dc3545', '❌'),
        }
        color, icon = colors.get(obj.delivery_status, ('#6c757d', '?'))
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color,
            icon,
            obj.get_delivery_status_display()
        )
    delivery_badge.short_description = 'Delivery'
    
    def has_add_permission(self, request):
        """Prevent manual creation of recipients (created programmatically)."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Allow deletion for cleanup."""
        return True
    
    def get_queryset(self, request):
        """Optimize with select_related."""
        qs = super().get_queryset(request)
        return qs.select_related('notification', 'gamer', 'shop_owner', 'admin_user')


@admin.register(NotificationGroup)
class NotificationGroupAdmin(admin.ModelAdmin):
    """Admin interface for managing notification groups."""
    
    list_display = [
        'name',
        'criteria_type_display',
        'member_count',
        'is_active',
        'created_at'
    ]
    list_filter = ['criteria_type', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['member_count', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Group Info', {
            'fields': ('name', 'description', 'is_active')
        }),
        ('Targeting Criteria', {
            'fields': ('criteria_type', 'criteria_data'),
            'description': 'Define who should receive notifications. '
                          'See help text for criteria_data format.'
        }),
        ('Statistics', {
            'fields': ('member_count',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    ordering = ['name']
    
    def criteria_type_display(self, obj):
        """Display criteria type with icon."""
        icons = {
            'level': '📊',
            'game': '🎮',
            'competition': '🏆',
            'custom': '👥',
            'payment_status': '💳',
            'all_users': '🌐',
        }
        icon = icons.get(obj.criteria_type, '?')
        return f"{icon} {obj.get_criteria_type_display()}"
    criteria_type_display.short_description = 'Criteria Type'


@admin.register(NotificationSchedule)
class NotificationScheduleAdmin(admin.ModelAdmin):
    """Admin for managing scheduled notifications."""
    
    list_display = [
        'notification_title',
        'scheduled_at',
        'status_badge',
        'days_until'
    ]
    list_filter = ['status', 'scheduled_at']
    search_fields = ['notification__title']
    readonly_fields = ['notification', 'created_at', 'sent_at']
    
    fieldsets = (
        ('Notification', {
            'fields': ('notification',)
        }),
        ('Schedule', {
            'fields': ('scheduled_at', 'status')
        }),
        ('Metadata', {
            'fields': ('created_at', 'sent_at'),
            'classes': ('collapse',)
        }),
    )
    
    ordering = ['scheduled_at']
    
    def notification_title(self, obj):
        """Link to notification."""
        url = reverse('admin:notifications_notification_change', args=[obj.notification.id])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            obj.notification.title
        )
    notification_title.short_description = 'Notification'
    
    def status_badge(self, obj):
        """Display status as colored badge."""
        colors = {
            'scheduled': '#0dcaf0',
            'sent': '#198754',
            'cancelled': '#6c757d',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def days_until(self, obj):
        """Show days until scheduled send."""
        from django.utils import timezone
        delta = (obj.scheduled_at - timezone.now()).days
        if delta < 0:
            return format_html('<span style="color: red;">{}</span>', 'Already passed')
        elif delta == 0:
            return format_html('<span style="color: orange;">{}</span>', 'Today')
        else:
            return f"In {delta} days"
    days_until.short_description = 'Days Until Send'
