from django.contrib import admin
from .models import (
    ProjectDetail,
    SiteStyle,
    NavigationLink,
    FooterSection,
    FooterLink,
    Slider,
    About,
    FeatureCard,
    Game,
    Platform,
    Event,
    Footer,
    Section,
    SectionHeading
)


@admin.register(ProjectDetail)
class ProjectDetailAdmin(admin.ModelAdmin):
    list_display = ['title', 'description', 'is_active']
    list_editable = ['is_active']
    fieldsets = (
        ('Main Content', {
            'fields': ('title', 'description', 'logo', 'short_description', 'is_active')
        }),
    )
    search_fields = ['title']
    ordering = ['title']
    list_filter = ['title']


@admin.register(NavigationLink)
class NavigationLinkAdmin(admin.ModelAdmin):
    list_display = ['link_text', 'link_icon', 'link', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    fieldsets = (
        ('Main Content', {
            'fields': ('link_text', 'link_icon', 'link', 'order', 'is_active')
        }),
    )
    search_fields = ['link_text']
    ordering = ['order']
    list_filter = ['is_active']


class FooterLinkInline(admin.TabularInline):
    model = FooterLink
    extra = 1
    ordering = ['order']


@admin.register(FooterSection)
class FooterSectionAdmin(admin.ModelAdmin):
    list_display = ['title', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    inlines = [FooterLinkInline]
    fieldsets = (
        ('Main Content', {
            'fields': ('title', 'order', 'is_active')
        }),
    )
    search_fields = ['title']
    ordering = ['order']
    list_filter = ['is_active']


@admin.register(FooterLink)
class FooterLinkAdmin(admin.ModelAdmin):
    list_display = ['link_text', 'section', 'link', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    list_filter = ['section', 'is_active']
    search_fields = ['link_text', 'section__title']
    ordering = ['section__order', 'order']


@admin.register(Slider)
class SliderAdmin(admin.ModelAdmin):
    list_display = ['title', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    list_filter = ['is_active']
    fieldsets = (
        ('Main Content', {
            'fields': ('title', 'subtitle', 'background_image', 'cta_text', 'cta_link', 'is_active')
        }),
    )
    search_fields = ['title']
    ordering = ['order']


@admin.register(About)
class AboutAdmin(admin.ModelAdmin):
    list_display = ['badge_text', 'heading', 'content', 'is_active']
    list_editable = ['is_active']
    list_filter = ['is_active']
    fieldsets = (
        ('Main Content', {
            'fields': ('badge_text', 'heading', 'content', 'image', 'is_active')
        }),
        ('Statistics', {
            'fields': ('active_players', 'active_players_count', 'competitions', 'competitions_count',
                       'platforms', 'platforms_count')
        }),
    )


@admin.register(FeatureCard)
class FeatureCardAdmin(admin.ModelAdmin):
    list_display = ['feature_name', 'feature_description', 'order', 'is_active']
    list_editable = ['is_active', 'order']
    fieldsets = (
        ('Main Content', {
            'fields': ('feature_name', 'feature_description', 'feature_icon', 'order', 'is_active')
        }),
    )
    search_fields = ['feature_name']
    ordering = ['order']
    list_filter = ['feature_name']


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    fieldsets = (
        ('Section Info', {
            'fields': ('name', 'slug', 'description', 'order', 'is_active')
        }),
    )


@admin.register(SectionHeading)
class SectionHeadingAdmin(admin.ModelAdmin):
    list_display = ['section', 'badge_text', 'heading', 'is_active']
    list_editable = ['is_active']
    list_filter = ['section', 'is_active']
    search_fields = ['heading', 'section__name']
    fieldsets = (
        ('Section Selection', {
            'fields': ('section',)
        }),
        ('Heading Content', {
            'fields': ('badge_text', 'heading', 'subheading', 'content')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ['status', 'name', 'type', 'image', 'is_active']
    list_editable = ['is_active']
    fieldsets = (
        ('Main Content', {
            'fields': ('image', 'status', 'name', 'type', 'is_active')
        }),
    )
    search_fields = ['name']
    ordering = ['name']
    list_filter = ['name']


@admin.register(Platform)
class PlatformAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'order', 'is_active']
    list_editable = ['is_active', 'order']
    fieldsets = (
        ('Main Content', {
            'fields': ('name', 'logo', 'description', 'stats', 'order', 'is_active')
        }),
    )
    search_fields = ['name']
    ordering = ['order']
    list_filter = ['name']


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['title', 'content', 'is_active']
    list_editable = ['is_active']
    fieldsets = (
        ('Main Content', {
            'fields': ('title', 'content', 'is_active')
        }),
    )
    search_fields = ['title']
    ordering = ['title']
    list_filter = ['title']


@admin.register(Footer)
class FooterAdmin(admin.ModelAdmin):
    list_display = ['copy_right_text', 'ownership_text', 'is_active']
    fieldsets = (
        ('Main Content', {
            'fields': ('copy_right_text', 'ownership_text', 'is_active')
        }),
    )
    search_fields = ['copy_right_text']
    ordering = ['copy_right_text']
    list_filter = ['copy_right_text']
    

@admin.register(SiteStyle)
class SiteStyleAdmin(admin.ModelAdmin):
    list_display = ("font_family", "font_color", "font_size", "background_color", "primary_color",
                    "secondary_color", "updated_at")
    readonly_fields = ("updated_at",)
    fieldsets = (
        ("Font", {"fields": ("font_family", "custom_font_family", "font_color", "font_size")}),
        ("Colors", {"fields": ("background_color", "primary_color", "secondary_color", "link_color",
                               "button_color", "button_text_color")}),
        ("Meta", {"fields": ("updated_at",)}),
    )