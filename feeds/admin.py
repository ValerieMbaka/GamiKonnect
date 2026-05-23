"""
Admin configuration for the feeds app.
Registers Post, PostMedia, Comment, and Like models.
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import Post, PostMedia, Comment, Like


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    """Admin interface for Post model."""
    
    list_display = ('get_author_name', 'get_content_preview', 'like_count', 'comment_count', 'created_at')
    list_filter = ('created_at', 'author')
    search_fields = ('content', 'author__first_name', 'author__last_name')
    readonly_fields = ('id', 'created_at', 'updated_at', 'like_count', 'comment_count')
    fieldsets = (
        ('Post Information', {
            'fields': ('id', 'author', 'content'),
        }),
        ('Engagement', {
            'fields': ('like_count', 'comment_count'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    def get_author_name(self, obj):
        """Display author's custom username."""
        return obj.author.custom_username or f"{obj.author.first_name} {obj.author.last_name}"
    get_author_name.short_description = 'Author'
    
    def get_content_preview(self, obj):
        """Display a preview of the post content."""
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
    get_content_preview.short_description = 'Content'


@admin.register(PostMedia)
class PostMediaAdmin(admin.ModelAdmin):
    """Admin interface for PostMedia model."""
    
    list_display = ('get_media_display', 'media_type', 'post_link', 'created_at')
    list_filter = ('media_type', 'created_at')
    readonly_fields = ('id', 'created_at', 'media_type')
    fieldsets = (
        ('Media Information', {
            'fields': ('id', 'post', 'media_type', 'order'),
        }),
        ('File Upload', {
            'fields': ('image_file', 'video_file'),
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )
    
    def get_media_display(self, obj):
        """Display a thumbnail for images."""
        if obj.image_file:
            return format_html(
                '<img src="{}" width="100" height="100" style="object-fit: cover;" />',
                obj.image_file.url
            )
        elif obj.video_file:
            return format_html('<span style="color: #0066cc;">{}</span>', '🎬 Video')
        return '-'
    get_media_display.short_description = 'Media'
    
    def post_link(self, obj):
        """Link to the post."""
        return format_html('<a href="/admin/feeds/post/{}/change/">{}</a>', obj.post.id, str(obj.post.id)[:8])
    post_link.short_description = 'Post'


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    """Admin interface for Comment model."""
    
    list_display = ('get_author_name', 'get_content_preview', 'post_link', 'created_at')
    list_filter = ('created_at', 'author')
    search_fields = ('content', 'author__first_name', 'author__last_name')
    readonly_fields = ('id', 'created_at', 'updated_at')
    fieldsets = (
        ('Comment Information', {
            'fields': ('id', 'post', 'author', 'content'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    def get_author_name(self, obj):
        """Display author's custom username."""
        return obj.author.custom_username or f"{obj.author.first_name} {obj.author.last_name}"
    get_author_name.short_description = 'Author'
    
    def get_content_preview(self, obj):
        """Display a preview of the comment."""
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
    get_content_preview.short_description = 'Content'
    
    def post_link(self, obj):
        """Link to the post."""
        return format_html('<a href="/admin/feeds/post/{}/change/">{}</a>', obj.post.id, str(obj.post.id)[:8])
    post_link.short_description = 'Post'


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    """Admin interface for Like model."""
    
    list_display = ('get_gamer_name', 'post_link', 'created_at')
    list_filter = ('created_at', 'gamer')
    search_fields = ('gamer__first_name', 'gamer__last_name')
    readonly_fields = ('id', 'created_at')
    fieldsets = (
        ('Like Information', {
            'fields': ('id', 'post', 'gamer'),
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )
    
    def get_gamer_name(self, obj):
        """Display gamer's custom username."""
        return obj.gamer.custom_username or f"{obj.gamer.first_name} {obj.gamer.last_name}"
    get_gamer_name.short_description = 'Gamer'
    
    def post_link(self, obj):
        """Link to the post."""
        return format_html('<a href="/admin/feeds/post/{}/change/">{}</a>', obj.post.id, str(obj.post.id)[:8])
    post_link.short_description = 'Post'
