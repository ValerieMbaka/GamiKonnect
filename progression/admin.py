from django.contrib import admin
from django.utils.html import format_html
from .models import Level, GamerStats, Achievement, GamerAchievement, GamerLevel


# ---------------------------------------------------------------------------
# Level Admin
# ---------------------------------------------------------------------------

@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
    list_display = ['order', 'name', 'min_xp', 'color_preview', 'gamer_count']
    list_editable = ['min_xp']
    ordering = ['order']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Level Details', {
            'fields': ('name', 'order', 'min_xp', 'color_hex', 'badge_image'),
        }),
        ('Timestamps', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at'),
        }),
    )

    @admin.display(description='Colour')
    def color_preview(self, obj):
        return format_html(
            '<span style="display:inline-block;width:16px;height:16px;'
            'border-radius:50%;background:{};border:1px solid #ccc;"></span> {}',
            obj.color_hex, obj.color_hex
        )

    @admin.display(description='Gamers at Level')
    def gamer_count(self, obj):
        return obj.gamers_at_level.count()


# ---------------------------------------------------------------------------
# Achievement Admin
# ---------------------------------------------------------------------------

@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'metric_key', 'target_value', 'xp_reward', 'is_active', 'is_hidden', 'earned_count']
    list_filter = ['category', 'is_active', 'is_hidden']
    list_editable = ['is_active', 'is_hidden']
    search_fields = ['name', 'description']
    ordering = ['category', 'target_value']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Achievement Details', {
            'fields': ('name', 'description', 'category', 'badge_image'),
        }),
        ('Rules Engine', {
            'fields': ('metric_key', 'target_value', 'xp_reward'),
            'description': 'metric_key must match a field on GamerStats such as communities_joined or competitions_won.',
        }),
        ('Legacy Compatibility', {
            'fields': ('achievement_type', 'threshold'),
            'classes': ('collapse',),
        }),
        ('Visibility', {
            'fields': ('is_active', 'is_hidden'),
        }),
        ('Timestamps', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at'),
        }),
    )

    @admin.display(description='Times Earned')
    def earned_count(self, obj):
        return obj.earned_by.count()


# ---------------------------------------------------------------------------
# GamerStats Admin
# ---------------------------------------------------------------------------

@admin.register(GamerStats)
class GamerStatsAdmin(admin.ModelAdmin):
    list_display = [
        'gamer',
        'communities_joined',
        'comments_made',
        'posts_made',
        'competitions_joined',
        'competitions_won',
        'leagues_joined',
        'leagues_won',
        'login_streak_days',
        'updated_at',
    ]
    search_fields = ['gamer__first_name', 'gamer__last_name', 'gamer__custom_username', 'gamer__email']
    readonly_fields = ['updated_at']
    ordering = ['-updated_at']

    fieldsets = (
        ('Gamer', {
            'fields': ('gamer',),
        }),
        ('Community & Social', {
            'fields': ('communities_joined', 'gamers_invited', 'comments_made'),
        }),
        ('Content Quality', {
            'fields': ('posts_made', 'posts_with_10_likes', 'posts_with_25_likes', 'posts_with_75_likes'),
        }),
        ('Competition', {
            'fields': ('competitions_joined', 'competitions_won'),
        }),
        ('Leagues & Loyalty', {
            'fields': ('leagues_joined', 'leagues_won', 'login_streak_days'),
        }),
        ('Timestamps', {
            'classes': ('collapse',),
            'fields': ('updated_at',),
        }),
    )


# ---------------------------------------------------------------------------
# GamerAchievement Admin
# ---------------------------------------------------------------------------

@admin.register(GamerAchievement)
class GamerAchievementAdmin(admin.ModelAdmin):
    list_display = ['gamer', 'achievement', 'earned_at']
    list_filter = ['achievement__achievement_type', 'earned_at']
    search_fields = ['gamer__first_name', 'gamer__last_name', 'achievement__name']
    ordering = ['-earned_at']
    readonly_fields = ['earned_at']


# ---------------------------------------------------------------------------
# GamerLevel Admin
# ---------------------------------------------------------------------------

@admin.register(GamerLevel)
class GamerLevelAdmin(admin.ModelAdmin):
    list_display = ['gamer', 'level', 'reached_at', 'gamer_points']
    list_filter = ['level']
    search_fields = ['gamer__first_name', 'gamer__last_name', 'gamer__custom_username']
    ordering = ['-reached_at']
    readonly_fields = ['reached_at', 'updated_at']

    @admin.display(description='Current XP')
    def gamer_points(self, obj):
        return f"{obj.gamer.points} XP"