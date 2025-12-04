from django.contrib import admin
from .models import PlatformCategory, Platform, Genre, Game


@admin.register(PlatformCategory)
class PlatformCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'platform_count', 'game_count', 'created_at', 'updated_at')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'slug', 'description')
    readonly_fields = ('id', 'game_count', 'created_at', 'updated_at')
    list_per_page = 20
    ordering = ('name',)
    
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
    list_display = ('name', 'category', 'slug', 'game_count', 'description')
    prepopulated_fields = {'slug': ('name',)}
    list_filter = ('category',)
    search_fields = ('name', 'slug', 'description', 'category__name')
    readonly_fields = ('id', 'slug', 'game_count', 'created_at', 'updated_at')
    list_per_page = 20
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('category').prefetch_related('games')
    
    def game_count(self, obj):
        return obj.game_count()
    
    game_count.short_description = 'Games Available'


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'game_count', 'description', 'created_at')
    prepopulated_fields = {'slug': ('name',)}
    list_filter = ('name', 'created_at')
    search_fields = ('name', 'slug', 'description')
    readonly_fields = ('id', 'slug', 'created_at', 'updated_at')
    list_per_page = 20
    
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('games')
    
    def game_count(self, obj):
        return obj.game_count()
    
    game_count.short_description = 'Number of Games'
    

@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ('name', 'platform_categories_list', 'display_genres','is_active')
    prepopulated_fields = {'slug': ('name',)}
    list_filter = ('is_active', 'genres', 'supported_platforms__category')
    search_fields = ('name', 'slug', 'description')
    list_editable = ('is_active',)
    readonly_fields = ('id', 'platform_categories_list_display')
    filter_horizontal = ('genres', 'supported_platforms')
    list_per_page = 20
    
    
    fieldsets = (
        ('Identifiers', {
            'fields': ('id', 'slug'),
            'classes': ('collapse',)
        }),
        ('Basic Information', {
            'fields': ('name', 'genres', 'description', 'image')
        }),
        ('Platforms & Availability', {
            'fields': ('supported_platforms', 'platform_categories_list_display', 'is_active')
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
            'gamers'
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


