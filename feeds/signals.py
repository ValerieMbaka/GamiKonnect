"""
Django signals for the feeds app.
Handles automatic updates to denormalized fields and cleanup.
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Count
from .models import Post, PostMedia, Comment, Like


@receiver(post_save, sender=Comment)
def update_post_comment_count_on_comment_save(sender, instance, created, **kwargs):
    """
    Update post's comment_count when a new comment is created.
    """
    if created:
        post = instance.post
        post.comment_count = post.comments.count()
        post.save(update_fields=['comment_count'])


@receiver(post_delete, sender=Comment)
def update_post_comment_count_on_comment_delete(sender, instance, **kwargs):
    """
    Update post's comment_count when a comment is deleted.
    """
    post = instance.post
    post.comment_count = post.comments.count()
    post.save(update_fields=['comment_count'])


@receiver(post_save, sender=Like)
def update_post_like_count_on_like_save(sender, instance, created, **kwargs):
    """
    Update post's like_count when a new like is created.
    """
    if created:
        post = instance.post
        post.like_count = post.likes.count()
        post.save(update_fields=['like_count'])


@receiver(post_delete, sender=Like)
def update_post_like_count_on_like_delete(sender, instance, **kwargs):
    """
    Update post's like_count when a like is deleted.
    """
    post = instance.post
    post.like_count = post.likes.count()
    post.save(update_fields=['like_count'])


@receiver(post_delete, sender=Post)
def cleanup_post_media_on_post_delete(sender, instance, **kwargs):
    """
    Clean up media files when a post is deleted.
    Cloudinary handles file deletion automatically, but we log it.
    """
    # PostMedia instances will be cascade deleted due to ForeignKey on_delete=CASCADE
    # Cloudinary will automatically handle file cleanup
    pass
