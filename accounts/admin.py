from django.contrib import admin
from django.utils.html import format_html
from .models import Account, Gamer, ShopOwner, PendingRegistration


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('email', 'first_name', 'last_name', 'phone')
    list_filter = ('created_at',)
    search_fields = ('first_name', 'last_name', 'email', 'phone', 'uid')
    readonly_fields = ('created_at', 'updated_at', 'uid')
    ordering = ('-created_at',)
    list_per_page = 20
    
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
class GamerAdmin(admin.ModelAdmin):
    list_display = ('email', 'first_name', 'last_name', 'custom_username', 'profile_completed', 'points',
                    'games_count', 'platforms_display', 'created_at')
    list_filter = ('profile_completed', 'date_joined', 'created_at')
    search_fields = ('first_name', 'last_name', 'email', 'custom_username', 'location')
    readonly_fields = ('date_joined', 'last_login', 'created_at', 'updated_at')
    filter_horizontal = ('games',)
    list_per_page = 20
    
    fieldsets = (
        ('Personal Info', {
            'fields': ('first_name', 'last_name', 'email', 'phone', 'uid')
        }),
        ('Gamer Profile', {
            'fields': ('custom_username', 'profile_picture', 'bio', 'about', 'date_of_birth', 'location')
        }),
        ('Gaming Info', {
            'fields': ('platforms', 'games', 'points')
        }),
        ('Account Status', {
            'fields': ('profile_completed', 'date_joined', 'last_login')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('games')
    
    def games_count(self, obj):
        return obj.games.count()
    
    games_count.short_description = 'Games Playing'
    
    def platforms_display(self, obj):
        # Render JSONField list of platforms as a comma-separated string
        if not obj.platforms:
            return "-"
        try:
            return ", ".join([str(p) for p in obj.platforms])
        except Exception:
            return str(obj.platforms)
    
    platforms_display.short_description = 'Platforms'


@admin.register(ShopOwner)
class ShopOwnerAdmin(admin.ModelAdmin):
    list_display = ('email', 'first_name', 'last_name', 'shop_count', 'date_joined', 'created_at')
    list_filter = ('date_joined', 'created_at')
    search_fields = ('first_name', 'last_name', 'email')
    readonly_fields = ('date_joined', 'last_login', 'created_at', 'updated_at')
    list_per_page = 20
    
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('shops')
    
    def shop_count(self, obj):
        return obj.shops.count()
    
    shop_count.short_description = 'Number of Shops'


@admin.register(PendingRegistration)
class PendingRegistrationAdmin(admin.ModelAdmin):
    list_display = ('email', 'first_name', 'last_name', 'role', 'created_at')
    list_filter = ('role', 'created_at')
    search_fields = ('email', 'first_name', 'last_name', 'phone')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 20
    
    fieldsets = (
        ('Registration Details', {
            'fields': ('email', 'first_name', 'last_name', 'phone', 'role', 'uid')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )