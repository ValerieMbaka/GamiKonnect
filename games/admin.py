from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count
from .models import Counter, PlatformCategory, Platform, Genre, Game
from core.admin_utils import SafeDateHierarchyAdmin


@admin.register(Counter)
class CounterAdmin(admin.ModelAdmin):
    list_display = ('model_name', 'last_id')
    readonly_fields = ('model_name', 'last_id')
    ordering = ('model_name',)
    
    def has_add_permission(self, request):
        # Prevent manual addition of counters
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of counters
        return False


@admin.register(PlatformCategory)
class PlatformCategoryAdmin(SafeDateHierarchyAdmin):
    list_display = ('integer_id', 'name', 'slug', 'platform_count_badge', 'game_count_badge')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'slug', 'description', 'integer_id')
    readonly_fields = ('id', 'integer_id', 'game_count_display', 'created_at', 'updated_at')
    list_filter = ('name', 'created_at')
    ordering = ('integer_id',)
    list_per_page = 20
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Category Information', {
            'fields': ('name', 'slug', 'description')
        }),
        ('Statistics', {
            'fields': ('platform_count_badge', 'game_count_display'),
            'classes': ('collapse',)
        }),
        ('Identifiers', {
            'fields': ('id', 'integer_id'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            platform_count=Count('platforms', distinct=True)
        ).prefetch_related('platforms')
    
    def platform_count_badge(self, obj):
        count = obj.platforms.count()
        return format_html(
            '<span style="background:#3b82f6;color:#fff;padding:3px 8px;border-radius:3px;font-weight:600;">{}</span>',
            count
        )
    platform_count_badge.short_description = 'Platforms'
    
    def game_count_badge(self, obj):
        count = obj.game_count()
        return format_html(
            '<span style="background:#10b981;color:#fff;padding:3px 8px;border-radius:3px;font-weight:600;">{}</span>',
            count
        )
    game_count_badge.short_description = 'Games'
    
    def game_count_display(self, obj):
        return obj.game_count()
    game_count_display.short_description = 'Total Games Available'


@admin.register(Platform)
class PlatformAdmin(SafeDateHierarchyAdmin):
    list_display = (
        'integer_id', 'name', 'category_link',
        'slug', 'game_count_badge'
    )
    list_filter = (
        ('category', admin.RelatedOnlyFieldListFilter),
        'created_at'
    )
    search_fields = ('name', 'slug', 'description', 'category__name', 'integer_id')
    readonly_fields = (
        'id', 'integer_id', 'slug', 'game_count_display',
        'created_at', 'updated_at'
    )
    list_per_page = 20
    ordering = ('integer_id',)
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Platform Information', {
            'fields': ('name', 'category', 'description')
        }),
        ('Game Availability', {
            'fields': ('game_count_display',)
        }),
        ('Identifiers', {
            'fields': ('id', 'integer_id', 'slug'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'category'
        ).prefetch_related('games').annotate(game_count=Count('games', distinct=True))
    
    def category_link(self, obj):
        """Display category with link"""
        if obj.category:
            return format_html(
                '<a href="/admin/games/platformcategory/{}/change/">{}</a>',
                obj.category.id, obj.category.name
            )
        return '—'
    category_link.short_description = 'Category'
    
    def game_count_badge(self, obj):
        """Display game count as badge"""
        count = obj.game_count() if hasattr(obj, 'game_count') and callable(obj.game_count) else obj.games.count()
        return format_html(
            '<span style="background:#10b981;color:#fff;padding:3px 8px;border-radius:3px;font-weight:600;">{}</span>',
            count
        )
    game_count_badge.short_description = 'Games'
    
    def game_count_display(self, obj):
        return obj.game_count() if hasattr(obj, 'game_count') and callable(obj.game_count) else obj.games.count()
    game_count_display.short_description = 'Games Available'


@admin.register(Genre)
class GenreAdmin(SafeDateHierarchyAdmin):
    list_display = (
        'integer_id', 'name', 'slug', 'game_count_badge',
        'created_at'
    )
    prepopulated_fields = {'slug': ('name',)}
    list_filter = ('name', 'created_at')
    search_fields = ('name', 'slug', 'description', 'integer_id')
    readonly_fields = (
        'id', 'integer_id', 'game_count_display',
        'created_at', 'updated_at'
    )
    list_per_page = 20
    ordering = ('integer_id',)
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Genre Information', {
            'fields': ('name', 'slug', 'description')
        }),
        ('Game Count', {
            'fields': ('game_count_display',)
        }),
        ('Identifiers', {
            'fields': ('id', 'integer_id'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            game_count=Count('games', distinct=True)
        ).prefetch_related('games')
    
    def game_count_badge(self, obj):
        """Display game count as badge"""
        count = obj.game_count() if hasattr(obj, 'game_count') and callable(obj.game_count) else obj.games.count()
        return format_html(
            '<span style="background:#10b981;color:#fff;padding:3px 8px;border-radius:3px;font-weight:600;">{}</span>',
            count
        )
    game_count_badge.short_description = 'Games'
    
    def game_count_display(self, obj):
        return obj.game_count() if hasattr(obj, 'game_count') and callable(obj.game_count) else obj.games.count()
    game_count_display.short_description = 'Number of Games'


@admin.register(Game)
class GameAdmin(SafeDateHierarchyAdmin):
    list_display = (
        'integer_id', 'name', 'genres_display', 'status_badge',
        'verification_badge', 'is_verified', 'is_active', 'created_at'
    )
    list_filter = (
        'is_verified', 'is_active', ('genres', admin.RelatedOnlyFieldListFilter),
        ('supported_platforms__category', admin.RelatedOnlyFieldListFilter),
        'created_at'
    )
    search_fields = ('name', 'slug', 'description', 'integer_id')
    list_editable = ('is_verified', 'is_active')
    readonly_fields = (
        'id', 'integer_id', 'platform_categories_list_display',
        'image_preview', 'created_at', 'updated_at'
    )
    filter_horizontal = ('genres', 'supported_platforms')
    list_per_page = 20
    ordering = ('integer_id',)
    date_hierarchy = 'created_at'
    actions = ['verify_games', 'unverify_games', 'activate_games', 'deactivate_games']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'slug')
        }),
        ('Media', {
            'fields': ('image', 'image_preview')
        }),
        ('Categorization', {
            'fields': ('genres', 'supported_platforms', 'platform_categories_list_display')
        }),
        ('Status', {
            'fields': ('is_verified', 'is_active')
        }),
        ('Identifiers', {
            'fields': ('id', 'integer_id'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related(
            'supported_platforms',
            'supported_platforms__category',
            'genres',
        )
    
    def genres_display(self, obj):
        """Display genres as badges"""
        genres = obj.genres.all()
        if not genres:
            return '—'
        return format_html(' '.join([
            f'<span style="background:#8b5cf6;color:#fff;padding:2px 6px;border-radius:3px;font-size:10px;margin-right:2px;display:inline-block;">{g.name}</span>'
            for g in genres
        ]))
    genres_display.short_description = 'Genres'
    
    def status_badge(self, obj):
        """Display active status as badge"""
        if obj.is_active:
            return format_html(
                '<span style="background:#10b981;color:#fff;padding:3px 8px;border-radius:3px;font-size:11px;font-weight:600;">▶ Active</span>'
            )
        return format_html(
            '<span style="background:#ef4444;color:#fff;padding:3px 8px;border-radius:3px;font-size:11px;font-weight:600;">⏸ Inactive</span>'
        )
    status_badge.short_description = 'Status'
    
    def verification_badge(self, obj):
        """Display verification status as badge"""
        if obj.is_verified:
            return format_html(
                '<span style="background:#10b981;color:#fff;padding:3px 8px;border-radius:3px;font-size:11px;font-weight:600;">✓ Verified</span>'
            )
        return format_html(
            '<span style="background:#f59e0b;color:#fff;padding:3px 8px;border-radius:3px;font-size:11px;font-weight:600;">⏳ Unverified</span>'
        )
    verification_badge.short_description = 'Verification'
    
    def image_preview(self, obj):
        """Preview game image"""
        if obj.image:
            return format_html(
                '<img src="{}" style="max-width:150px;max-height:150px;border-radius:4px;" />',
                obj.image.url
            )
        return '—'
    image_preview.short_description = 'Image Preview'
    
    def platform_categories_list_display(self, obj):
        """Show platform categories"""
        categories = obj.platform_categories_list()
        if not categories:
            return '—'
        return ", ".join(categories)
    platform_categories_list_display.short_description = 'Available On Categories'
    
    @admin.action(description='✓ Verify selected games')
    def verify_games(self, request, queryset):
        """Verify selected games"""
        count = queryset.filter(is_verified=False).update(is_verified=True)
        self.message_user(request, f"✓ Verified {count} game(s).")
    
    @admin.action(description='✗ Unverify selected games')
    def unverify_games(self, request, queryset):
        """Unverify selected games"""
        count = queryset.filter(is_verified=True).update(is_verified=False)
        self.message_user(request, f"✗ Unverified {count} game(s).")
    
    @admin.action(description='▶ Activate selected games')
    def activate_games(self, request, queryset):
        """Activate selected games"""
        count = queryset.filter(is_active=False).update(is_active=True)
        self.message_user(request, f"▶ Activated {count} game(s).")
    
    @admin.action(description='⏸ Deactivate selected games')
    def deactivate_games(self, request, queryset):
        """Deactivate selected games"""
        count = queryset.filter(is_active=True).update(is_active=False)
        self.message_user(request, f"⏸ Deactivated {count} game(s).")
