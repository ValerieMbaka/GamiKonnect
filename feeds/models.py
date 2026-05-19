"""
Feeds app models for GamiKonnect.
Enables gamers to post images/videos and interact via comments and likes.
All media is stored on Cloudinary to handle Render's ephemeral filesystem.
"""
import uuid
from django.db import models
from django.utils import timezone
from django.core.validators import FileExtensionValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from cloudinary_storage.storage import MediaCloudinaryStorage
from accounts.models import Gamer


def validate_image_size(file):
    """Validate that image files don't exceed 3MB."""
    file_size = file.size
    limit_mb = 3
    if file_size > limit_mb * 1024 * 1024:
        raise ValidationError(f'Image file size must not exceed {limit_mb}MB')


def validate_video_size(file):
    """Validate that video files don't exceed 10MB."""
    file_size = file.size
    limit_mb = 10
    if file_size > limit_mb * 1024 * 1024:
        raise ValidationError(f'Video file size must not exceed {limit_mb}MB')


class Post(models.Model):
    """
    Main feed post model.
    Contains the text content and author info.
    Media (images/videos) are stored separately in PostMedia model.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = models.ForeignKey(
        Gamer,
        on_delete=models.CASCADE,
        related_name='posts',
        help_text="The gamer who created this post"
    )
    content = models.TextField(
        max_length=5000,
        blank=True,
        help_text="Text content of the post"
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Engagement metrics (denormalized for performance)
    comment_count = models.PositiveIntegerField(default=0)
    like_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        verbose_name = 'Post'
        verbose_name_plural = 'Posts'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['author', '-created_at']),
        ]
    
    def __str__(self):
        return f"Post by {self.author.custom_username} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class PostMedia(models.Model):
    """
    Media (images/videos) for a post.
    Separate model allows multiple media files per post.
    All files stored on Cloudinary.
    """
    
    MEDIA_TYPE_CHOICES = [
        ('image', 'Image'),
        ('video', 'Video'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='media',
        help_text="The post this media belongs to"
    )
    media_type = models.CharField(
        max_length=10,
        choices=MEDIA_TYPE_CHOICES,
        help_text="Whether this is an image or video"
    )
    file = models.FileField(
        upload_to='feeds/',
        storage=MediaCloudinaryStorage(),
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'gif', 'webp', 'mp4', 'webm', 'mov', 'avi'])],
        help_text="Image or video file stored on Cloudinary"
    )
    image_file = models.ImageField(
        upload_to='feeds/',
        storage=MediaCloudinaryStorage(),
        blank=True,
        null=True,
        validators=[validate_image_size],
        help_text="Use this for image uploads (auto-validates 3MB limit)"
    )
    video_file = models.FileField(
        upload_to='feeds/',
        storage=MediaCloudinaryStorage(),
        blank=True,
        null=True,
        validators=[validate_video_size],
        help_text="Use this for video uploads (auto-validates 10MB limit)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    order = models.PositiveSmallIntegerField(
        default=0,
        help_text="Order of media in the post (for display)"
    )
    
    class Meta:
        verbose_name = 'Post Media'
        verbose_name_plural = 'Post Media'
        ordering = ['order']
        indexes = [
            models.Index(fields=['post', 'order']),
        ]
    
    def clean(self):
        """Validate that either image_file or video_file is provided."""
        if not self.image_file and not self.video_file:
            raise ValidationError('Either image_file or video_file must be provided.')
        if self.image_file and self.video_file:
            raise ValidationError('Provide either image_file or video_file, not both.')
    
    def save(self, *args, **kwargs):
        """Set media_type based on file type before saving."""
        self.full_clean()
        if self.image_file:
            self.media_type = 'image'
        elif self.video_file:
            self.media_type = 'video'
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.get_media_type_display()} - {self.post.id} #{self.order}"


class Comment(models.Model):
    """
    Comments on posts.
    Links a gamer to a post, enabling discussions.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='comments',
        help_text="The post being commented on"
    )
    author = models.ForeignKey(
        Gamer,
        on_delete=models.CASCADE,
        related_name='comments',
        help_text="The gamer who made this comment"
    )
    content = models.TextField(
        max_length=1000,
        help_text="Comment text"
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Comment'
        verbose_name_plural = 'Comments'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['post', 'created_at']),
            models.Index(fields=['author', 'created_at']),
        ]
    
    def __str__(self):
        return f"Comment by {self.author.custom_username} on post {self.post.id}"


class Like(models.Model):
    """
    Likes junction table.
    Records which gamers liked which posts.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='likes',
        help_text="The post being liked"
    )
    gamer = models.ForeignKey(
        Gamer,
        on_delete=models.CASCADE,
        related_name='liked_posts',
        help_text="The gamer who liked this post"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Like'
        verbose_name_plural = 'Likes'
        unique_together = ('post', 'gamer')  # Prevent duplicate likes
        indexes = [
            models.Index(fields=['post', 'gamer']),
            models.Index(fields=['gamer', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.gamer.custom_username} liked {self.post.id}"
