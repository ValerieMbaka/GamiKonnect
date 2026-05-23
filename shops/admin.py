from django.contrib import admin
from django.contrib import messages
from django.utils import timezone
from django.utils.html import format_html
from .models import Shop, Console, GamePricing
from core.email_service import EmailManager
from core.admin_utils import SafeDateHierarchyAdmin


class ConsoleInline(admin.TabularInline):
    """Inline editor for shop consoles"""
    model = Console
    extra = 1
    fields = ('console_type', 'quantity', 'notes')
    verbose_name = 'Console'
    verbose_name_plural = 'Consoles'


class GamePricingInline(admin.TabularInline):
    """Inline editor for game pricing"""
    model = GamePricing
    extra = 0
    fields = ('game', 'price_per_hour', 'is_premium', 'notes')
    verbose_name = 'Game Pricing'
    verbose_name_plural = 'Game Pricing'
    raw_id_fields = ('game',)


@admin.register(Shop)
class ShopAdmin(SafeDateHierarchyAdmin):
    list_display = ('name', 'location', 'approval_badge', 'is_active', 'base_price_display', 'created_at')
    list_filter = ('is_approved', 'is_active', 'created_at')
    search_fields = ('name', 'location', 'submitted_by_email', 'address')
    inlines = [ConsoleInline, GamePricingInline]
    
    # Register the custom dropdown actions
    actions = ['approve_shops', 'reject_shops', 'activate_shops', 'deactivate_shops']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'logo')
        }),
        ('Location & Details', {
            'fields': ('city', 'location', 'building', 'floor', 'room_number', 'address', 'screen_number')
        }),
        ('Business Information', {
            'fields': ('base_price_per_hour', 'opening_hours', 'closing_hours', 'business_permit')
        }),
        ('Status & Approval', {
            'fields': ('is_approved', 'is_active', 'approved_at')
        }),
        ('Submission Details', {
            'fields': ('submitted_by_uid', 'submitted_by_email', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('submitted_by_uid', 'submitted_by_email', 'created_at', 'updated_at', 'approved_at')
    list_per_page = 20
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    
    def approval_badge(self, obj):
        """Display approval status as badge"""
        if obj.is_approved:
            return format_html(
                '<span style="background:#10b981;color:#fff;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:600;">✓ Approved</span>'
            )
        return format_html(
            '<span style="background:#f59e0b;color:#fff;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:600;">⏳ Pending</span>'
        )
    approval_badge.short_description = 'Status'
    
    def base_price_display(self, obj):
        """Display base price formatted"""
        return format_html('₱{:,.2f}/hr', obj.base_price_per_hour)
    base_price_display.short_description = 'Base Price'
    
    def save_model(self, request, obj, form, change):
        """Handles manual state changes inside the individual shop edit page"""
        if change:
            old_shop = Shop.objects.get(pk=obj.pk)
            
            # If the admin just changed 'is_approved' from False to True
            if not old_shop.is_approved and obj.is_approved:
                obj.is_active = True
                if hasattr(obj, 'approved_at'):
                    obj.approved_at = timezone.now()
                EmailManager.send_shop_approval(obj, approved=True)
            
            # If the admin just revoked the approval (True to False)
            elif old_shop.is_approved and not obj.is_approved:
                obj.is_active = False
                EmailManager.send_shop_approval(obj, approved=False)
        
        # Proceed with saving the object to the database
        super().save_model(request, obj, form, change)
    
    @admin.action(description='✓ Approve selected shops')
    def approve_shops(self, request, queryset):
        """Allows 1-click approval from the main list view"""
        count = 0
        for shop in queryset.filter(is_approved=False):
            shop.is_approved = True
            shop.is_active = True
            if hasattr(shop, 'approved_at'):
                shop.approved_at = timezone.now()
            shop.save(update_fields=['is_approved', 'is_active', 'approved_at'])
            
            # Trigger the approval email
            EmailManager.send_shop_approval(shop, approved=True)
            count += 1
        
        self.message_user(request, f"✓ Successfully approved {count} shop(s).", messages.SUCCESS)
    
    @admin.action(description='✗ Reject selected pending shops')
    def reject_shops(self, request, queryset):
        """Allows explicitly triggering rejection emails for pending shops"""
        count = 0
        # Only process shops that are currently pending/unapproved
        for shop in queryset.filter(is_approved=False):
            
            # Trigger the rejection email using your EmailManager
            email_sent = EmailManager.send_shop_approval(shop, approved=False)
            
            if email_sent:
                count += 1
        
        self.message_user(
            request,
            f"✗ Successfully processed {count} shop(s) and sent rejection notifications.",
            messages.SUCCESS
        )
    
    @admin.action(description='▶ Activate selected shops')
    def activate_shops(self, request, queryset):
        """Activate selected shops"""
        count = queryset.filter(is_active=False).update(is_active=True)
        self.message_user(request, f"▶ Activated {count} shop(s).", messages.SUCCESS)
    
    @admin.action(description='⏸ Deactivate selected shops')
    def deactivate_shops(self, request, queryset):
        """Deactivate selected shops"""
        count = queryset.filter(is_active=True).update(is_active=False)
        self.message_user(request, f"⏸ Deactivated {count} shop(s).", messages.SUCCESS)


@admin.register(Console)
class ConsoleAdmin(SafeDateHierarchyAdmin):
    """
    Manage gaming consoles available in shops.
    """
    list_display = ('console_type', 'shop_link', 'quantity_display', 'notes_short', 'created_at')
    list_filter = (
        ('console_type', admin.RelatedOnlyFieldListFilter),
        ('shop', admin.RelatedOnlyFieldListFilter),
        'created_at'
    )
    search_fields = ('shop__name', 'console_type__name', 'notes')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 30
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Console Information', {
            'fields': ('shop', 'console_type', 'quantity', 'notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('shop', 'console_type')
    
    def shop_link(self, obj):
        """Display shop with link"""
        return format_html(
            '<a href="/admin/shops/shop/{}/change/">{}</a>',
            obj.shop.id, obj.shop.name
        )
    shop_link.short_description = 'Shop'
    
    def quantity_display(self, obj):
        """Display quantity with color coding"""
        if obj.quantity == 0:
            color = '#ef4444'  # red
        elif obj.quantity <= 2:
            color = '#f59e0b'  # orange
        else:
            color = '#10b981'  # green
        
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 8px;border-radius:3px;font-weight:600;">{}</span>',
            color, obj.quantity
        )
    quantity_display.short_description = 'Quantity'
    
    def notes_short(self, obj):
        """Show truncated notes"""
        if obj.notes:
            if len(obj.notes) > 40:
                return obj.notes[:40] + '...'
            return obj.notes
        return '—'
    notes_short.short_description = 'Notes'


@admin.register(GamePricing)
class GamePricingAdmin(SafeDateHierarchyAdmin):
    """
    Manage game pricing across different shops.
    """
    list_display = ('game_link', 'shop_link', 'price_display', 'premium_badge', 'created_at')
    list_filter = (
        ('shop', admin.RelatedOnlyFieldListFilter),
        ('game', admin.RelatedOnlyFieldListFilter),
        'is_premium',
        'created_at'
    )
    search_fields = ('game__name', 'shop__name', 'notes')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 30
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Pricing Information', {
            'fields': ('shop', 'game', 'price_per_hour', 'is_premium', 'notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('shop', 'game')
    
    def game_link(self, obj):
        """Display game with link"""
        return format_html(
            '<a href="/admin/games/game/{}/change/">{}</a>',
            obj.game.id, obj.game.name
        )
    game_link.short_description = 'Game'
    
    def shop_link(self, obj):
        """Display shop with link"""
        return format_html(
            '<a href="/admin/shops/shop/{}/change/">{}</a>',
            obj.shop.id, obj.shop.name
        )
    shop_link.short_description = 'Shop'
    
    def price_display(self, obj):
        """Display price formatted"""
        return format_html('₱{:,.2f}/hr', obj.price_per_hour)
    price_display.short_description = 'Price/Hour'
    
    def premium_badge(self, obj):
        """Show if premium"""
        if obj.is_premium:
            return format_html(
                '<span style="background:#f59e0b;color:#fff;padding:2px 6px;border-radius:3px;font-size:10px;font-weight:600;">{}</span>',
                'PREMIUM'
            )
        return '—'
    premium_badge.short_description = 'Premium'