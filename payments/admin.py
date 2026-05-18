from django.contrib import admin
from django.utils.html import format_html
from .models import MpesaTransaction


@admin.register(MpesaTransaction)
class MpesaTransactionAdmin(admin.ModelAdmin):
    list_display = ('receipt_number_or_pending', 'gamer', 'phone_number', 'amount', 'status_badge', 'is_simulated', 'created_at')
    list_filter = ('status', 'is_simulated', 'created_at')
    search_fields = ('receipt_number', 'phone_number', 'gamer__email')
    readonly_fields = ('checkout_request_id', 'created_at', 'updated_at')
    list_per_page = 50
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Transaction Details', {
            'fields': ('gamer', 'phone_number', 'amount', 'receipt_number', 'checkout_request_id')
        }),
        ('Status', {
            'fields': ('status', 'is_simulated')
        }),
        ('Registration Link', {
            'fields': ('competition_registration',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def receipt_number_or_pending(self, obj):
        """Display receipt number or 'Pending' status"""
        if obj.receipt_number:
            return format_html(
                '<span style="background:#10b981;color:#fff;padding:3px 8px;border-radius:3px;font-weight:600;">{}</span>',
                obj.receipt_number
            )
        return format_html(
            '<span style="background:#f59e0b;color:#fff;padding:3px 8px;border-radius:3px;font-weight:600;">Pending</span>'
        )
    receipt_number_or_pending.short_description = 'Receipt Number'
    
    def status_badge(self, obj):
        """Display status as a colored badge"""
        colors = {
            'PENDING': '#f59e0b',
            'SUCCESS': '#10b981',
            'FAILED': '#ef4444',
        }
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 8px;border-radius:3px;font-weight:600;">{}</span>',
            colors.get(obj.status, '#6b7280'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
