from django.contrib import admin
from django.utils.html import format_html
from .models import Level, Achievement, GamerAchievement, GamerLevel


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
    list_display = ['name', 'achievement_type', 'threshold', 'is_active', 'earned_count']
    list_filter = ['achievement_type', 'is_active']
    list_editable = ['is_active']
    search_fields = ['name', 'description']
    ordering = ['achievement_type', 'threshold']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Achievement Details', {
            'fields': ('name', 'description', 'badge_image'),
        }),
        ('Trigger Condition', {
            'fields': ('achievement_type', 'threshold', 'is_active'),
            'description': (
                'The threshold meaning depends on the type: '
                'competition_count = number of competitions; '
                'xp_milestone = XP amount; '
                'level_reached = level order number; '
                'participation_hours = total hours. '
                'For first_* types, threshold is always 1.'
            ),
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