from django.contrib import admin
from django.utils.html import format_html
from django.db import transaction, IntegrityError
from django.utils import timezone
from .models import Shop, Console, GamePricing
from accounts.models import ShopOwner, Account
from core.email_service import send_shop_approval_email


import logging

logger = logging.getLogger(__name__)


class ConsoleInline(admin.TabularInline):
    model = Console
    extra = 0
    fields = ('console_type', 'quantity')
    classes = ('collapse',)
    
    def has_add_permission(self, request, obj=None):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


class GamePricingInline(admin.TabularInline):
    model = GamePricing
    extra = 0
    fields = ('game', 'price_per_hour', 'is_premium')
    classes = ('collapse',)
    
    def has_add_permission(self, request, obj=None):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'location', 'screen_number', 'console_platforms_list',
                    'premium_games_count', 'base_price_per_hour', 'is_active', 'is_approved', 'owner_count')
    list_filter = ('is_active', 'is_approved', 'city', 'location', 'consoles__console_type', 'created_at')
    search_fields = ('name', 'city', 'location', 'address', 'owners__first_name', 'owners__last_name')
    list_editable = ('is_active', 'is_approved')
    readonly_fields = ('name', 'owners', 'city', 'location', 'building', 'floor', 'room_number', 
                       'address', 'screen_number', 'games_available', 'base_price_per_hour', 
                       'opening_hours', 'closing_hours', 'logo', 'description', 
                       'business_permit', 'submitted_by_uid', 'submitted_by_email', 
                       'created_at', 'updated_at', 'approved_at', 'total_consoles_display', 
                       'console_summary_display', 'supported_platform_categories_display')
    filter_horizontal = ('owners', 'games_available')
    inlines = [ConsoleInline, GamePricingInline]
    list_per_page = 20
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'logo', 'description', 'owners', 'is_active', 'is_approved')
        }),
        ('Location Details', {
            'fields': ('city', 'location', 'building', 'floor', 'room_number', 'address')
        }),
        ('Shop Facilities', {
            'fields': ('screen_number', 'games_available', 'business_permit', 'total_consoles_display', 
                       'console_summary_display', 'supported_platform_categories_display')
        }),
        ('Pricing & Hours', {
            'fields': ('base_price_per_hour', 'opening_hours', 'closing_hours')
        }),
        ('Submission Details', {
            'fields': ('submitted_by_uid', 'submitted_by_email'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'approved_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related(
            'owners',
            'consoles',
            'consoles__console_type',
            'game_prices__game'
        )
    
    def owner_count(self, obj):
        return obj.owners.count()
    
    owner_count.short_description = 'Owners'
    
    def total_consoles_display(self, obj):
        return obj.total_consoles()
    
    total_consoles_display.short_description = 'Total Consoles'
    
    def console_summary_display(self, obj):
        return obj.console_summary()
    
    console_summary_display.short_description = 'Console Summary'
    
    def console_platforms_list(self, obj):
        platforms = obj.available_console_platforms()
        return ", ".join(platforms) if platforms else "None"
    
    console_platforms_list.short_description = 'Console Platforms'
    
    def supported_platform_categories_display(self, obj):
        categories = obj.supported_platform_categories()
        return ", ".join([category.name for category in categories]) if categories else "None"
    
    supported_platform_categories_display.short_description = 'Supported Platform Categories'
    
    def premium_games_count(self, obj):
        return obj.premium_games_count()
    
    premium_games_count.short_description = 'Premium Games'

    def save_model(self, request, obj, form, change):
        # Track prior approval state
        previous_approved = None
        if obj.pk and change:
            try:
                previous = Shop.objects.get(pk=obj.pk)
                previous_approved = previous.is_approved
            except Shop.DoesNotExist:
                previous_approved = None
        
        super().save_model(request, obj, form, change)
        
        # Handle approval transitions
        if obj.is_approved and previous_approved is not True:
            # Set approved timestamp if missing
            if not obj.approved_at:
                obj.approved_at = timezone.now()
            
            # Activate the shop upon approval
            obj.is_active = True
            obj.save(update_fields=['approved_at', 'is_active'])
            
            # If no owners yet but we have submitter, create ShopOwner and attach
            if obj.owners.count() == 0 and (obj.submitted_by_email or obj.submitted_by_uid):
                # Try to find an existing ShopOwner or Account by email or UID
                shop_owner = None
                
                # Check for ShopOwner first
                if obj.submitted_by_uid:
                    shop_owner = ShopOwner.objects.filter(uid=obj.submitted_by_uid).first()
                if not shop_owner and obj.submitted_by_email:
                    shop_owner = ShopOwner.objects.filter(email=obj.submitted_by_email).first()
                
                # If not a ShopOwner, check if they have an Account to promote
                if not shop_owner:
                    account = None
                    if obj.submitted_by_uid:
                        account = Account.objects.filter(uid=obj.submitted_by_uid).first()
                    if not account and obj.submitted_by_email:
                        account = Account.objects.filter(email=obj.submitted_by_email).first()
                    
                    if account:
                        try:
                            with transaction.atomic():
                                # Promote Account to ShopOwner
                                shop_owner = ShopOwner(
                                    account_ptr_id=account.id,
                                    date_joined=timezone.now()
                                )
                                # Fill up inherited fields
                                for field in Account._meta.fields:
                                    if field.name != 'id':
                                        setattr(shop_owner, field.name, getattr(account, field.name))
                                
                                shop_owner.save()
                                logger.info(f"Promoted Account {account.id} to ShopOwner (UID: {account.uid})")
                        except Exception as e:
                            logger.error(f"Failed to promote Account to ShopOwner: {e}")
                            # Fallback re-fetch in case of race condition
                            if obj.submitted_by_uid:
                                shop_owner = ShopOwner.objects.filter(uid=obj.submitted_by_uid).first()
                
                if shop_owner:
                    obj.owners.add(shop_owner)
                    logger.info(f"Added owner {shop_owner.email} to shop {obj.name}")
            
            # Send approval email to owner/submitter
            send_shop_approval_email(obj, approved=True)
        elif previous_approved is True and not obj.is_approved:
            # Send rejection email when toggled off
            send_shop_approval_email(obj, approved=False)


@admin.register(Console)
class ConsoleAdmin(admin.ModelAdmin):
    list_display = ('shop', 'console_type', 'quantity', 'notes')
    list_filter = ('console_type', 'shop', 'created_at')
    search_fields = ('shop__name', 'notes', 'console_type__name')
    readonly_fields = ('shop', 'console_type', 'quantity', 'notes', 'created_at', 'updated_at')
    list_per_page = 20
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('shop', 'console_type')


@admin.register(GamePricing)
class GamePricingAdmin(admin.ModelAdmin):
    list_display = ('shop', 'game', 'price_per_hour', 'is_premium')
    list_filter = ('is_premium', 'shop', 'created_at')
    search_fields = ('game__name', 'shop__name', 'notes')
    readonly_fields = ('shop', 'game', 'price_per_hour', 'is_premium', 'notes', 'created_at', 'updated_at')
    list_per_page = 20
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('shop', 'game')