from django.contrib import admin
from .models import Counter, PlatformCategory, Platform, Genre, Game


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
class PlatformCategoryAdmin(admin.ModelAdmin):
    list_display = ('integer_id', 'name', 'slug', 'platform_count', 'game_count')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'slug', 'description', 'integer_id')
    readonly_fields = ('id', 'integer_id', 'game_count', 'created_at', 'updated_at')
    list_filter = ('name',)
    ordering = ('integer_id',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('platforms')
    
    def platform_count(self, obj):
        return obj.platforms.count()
    
    platform_count.short_description = 'Number of Platforms'
    
    def game_count(self, obj):
        return obj.game_count()
    
    game_count.short_description = 'Number of Games'
    
    def game_count_display(self, obj):
        return obj.game_count()
    
    game_count_display.short_description = 'Total Games Available'


@admin.register(Platform)
class PlatformAdmin(admin.ModelAdmin):
    list_display = ('integer_id', 'name', 'category__name', 'slug', 'game_count')
    list_filter = ('category__name',)
    search_fields = ('name', 'slug', 'description', 'category__name', 'integer_id')
    readonly_fields = ('id', 'integer_id', 'slug', 'game_count', 'created_at', 'updated_at')
    list_per_page = 20
    ordering = ('integer_id',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('category').prefetch_related('games')
    
    def game_count(self, obj):
        return obj.game_count()
    
    game_count.short_description = 'Games Available'


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ('integer_id', 'name', 'slug', 'game_count', 'created_at')
    prepopulated_fields = {'slug': ('name',)}
    list_filter = ('name', 'created_at')
    search_fields = ('name', 'slug', 'description', 'integer_id')
    readonly_fields = ('id', 'integer_id', 'game_count', 'created_at', 'updated_at')
    ordering = ('integer_id',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('games')
    
    def game_count(self, obj):
        return obj.game_count()
    
    game_count.short_description = 'Number of Games'


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ('integer_id', 'name', 'platform_categories_list', 'display_genres', 'is_verified', 'is_active')
    list_filter = ('is_verified', 'is_active', 'genres', 'supported_platforms__category')
    search_fields = ('name', 'slug', 'description', 'integer_id')
    list_editable = ('is_verified', 'is_active')
    readonly_fields = ('id', 'integer_id', 'platform_categories_list_display', 'created_at', 'updated_at')
    filter_horizontal = ('genres', 'supported_platforms')
    list_per_page = 20
    ordering = ('integer_id',)
    
    fieldsets = (
        ('Identifiers', {
            'fields': ('id', 'integer_id', 'slug'),
            'classes': ('collapse',)
        }),
        ('Basic Information', {
            'fields': ('name', 'genres', 'description', 'image')
        }),
        ('Platforms & Availability', {
            'fields': ('supported_platforms', 'platform_categories_list_display', 'is_verified', 'is_active')
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
    
    def display_genres(self, obj):
        return ", ".join([g.name for g in obj.genres.all()])
    
    display_genres.short_description = 'Genres'
    
    def platforms_list(self, obj):
        return ", ".join([platform.name for platform in obj.supported_platforms.all()])
    
    platforms_list.short_description = 'Platforms'
    
    def platform_categories_list(self, obj):
        return obj.platform_categories_list()
    
    platform_categories_list.short_description = 'Platform Categories'
    
    def platform_categories_list_display(self, obj):
        return obj.platform_categories_list()
    
    platform_categories_list_display.short_description = 'Available On Categories'
