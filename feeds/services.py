"""
Business logic and utility functions for the feeds app.
Includes feed aggregation, engagement calculations, and helpers.
"""
from django.db.models import Prefetch, Count, Q
from django.utils import timezone
from datetime import timedelta
from .models import Post, Comment, Like, PostMedia


class FeedService:
    """Service class for feed-related operations."""
    
    @staticmethod
    def get_feed_posts_optimized(gamer=None, hours=7*24):
        """
        Get feed posts from the last N hours with full optimizations.
        Optionally filter for a specific gamer's posts.
        
        Args:
            gamer: Gamer instance to filter by (optional)
            hours: Number of hours to look back (default: 7 days)
        
        Returns:
            QuerySet of optimized Post objects
        """
        # Calculate cutoff time
        cutoff_time = timezone.now() - timedelta(hours=hours)
        
        # Prefetch comments with their authors
        comments_prefetch = Prefetch(
            'comments',
            Comment.objects.select_related('author').order_by('created_at')
        )
        
        # Prefetch likes with their gamers
        likes_prefetch = Prefetch(
            'likes',
            Like.objects.select_related('gamer')
        )
        
        # Prefetch media
        media_prefetch = Prefetch(
            'media',
            PostMedia.objects.order_by('order')
        )
        
        # Build base query
        posts = Post.objects.select_related('author').prefetch_related(
            comments_prefetch,
            likes_prefetch,
            media_prefetch
        ).filter(created_at__gte=cutoff_time)
        
        # Filter by gamer if provided
        if gamer:
            posts = posts.filter(author=gamer)
        
        # Order by recency
        posts = posts.order_by('-created_at')
        
        return posts
    
    @staticmethod
    def get_post_engagement_stats(post):
        """
        Get engagement statistics for a post.
        
        Args:
            post: Post instance
        
        Returns:
            Dictionary with engagement metrics
        """
        return {
            'like_count': post.like_count,
            'comment_count': post.comment_count,
            'total_engagement': post.like_count + post.comment_count,
            'comments': post.comments.all(),
            'likes': post.likes.all(),
        }
    
    @staticmethod
    def create_post_with_media(gamer, content, media_files=None):
        """
        Create a new post with optional media files.
        Handles file type detection and validation.
        
        Args:
            gamer: Gamer instance (post author)
            content: Post text content
            media_files: List of file objects (optional)
        
        Returns:
            Post instance
        """
        # Create the post
        post = Post.objects.create(
            author=gamer,
            content=content.strip() if content else ''
        )
        
        # Add media if provided
        if media_files:
            for idx, file in enumerate(media_files):
                # Determine type from MIME type
                if file.content_type.startswith('image/'):
                    PostMedia.objects.create(
                        post=post,
                        image_file=file,
                        order=idx
                    )
                elif file.content_type.startswith('video/'):
                    PostMedia.objects.create(
                        post=post,
                        video_file=file,
                        order=idx
                    )
        
        return post
    
    @staticmethod
    def add_like(post, gamer):
        """
        Add a like to a post.
        Updates denormalized like_count.
        
        Args:
            post: Post instance
            gamer: Gamer instance
        
        Returns:
            Tuple of (Like instance, created: bool)
        """
        like, created = Like.objects.get_or_create(post=post, gamer=gamer)
        
        if created:
            # Update post's like count
            post.like_count = post.likes.count()
            post.save(update_fields=['like_count'])
        
        return like, created
    
    @staticmethod
    def remove_like(post, gamer):
        """
        Remove a like from a post.
        Updates denormalized like_count.
        
        Args:
            post: Post instance
            gamer: Gamer instance
        
        Returns:
            bool: True if like was deleted, False if it didn't exist
        """
        like = Like.objects.filter(post=post, gamer=gamer).first()
        
        if like:
            like.delete()
            # Update post's like count
            post.like_count = post.likes.count()
            post.save(update_fields=['like_count'])
            return True
        
        return False
    
    @staticmethod
    def toggle_like(post, gamer):
        """
        Toggle a like on a post.
        
        Args:
            post: Post instance
            gamer: Gamer instance
        
        Returns:
            bool: True if now liked, False if now unliked
        """
        like = Like.objects.filter(post=post, gamer=gamer).first()
        
        if like:
            like.delete()
            post.like_count = post.likes.count()
            post.save(update_fields=['like_count'])
            return False  # Unliked
        else:
            Like.objects.create(post=post, gamer=gamer)
            post.like_count = post.likes.count()
            post.save(update_fields=['like_count'])
            return True  # Liked
    
    @staticmethod
    def add_comment(post, gamer, content):
        """
        Add a comment to a post.
        Updates denormalized comment_count.
        
        Args:
            post: Post instance
            gamer: Gamer instance
            content: Comment text
        
        Returns:
            Comment instance
        """
        comment = Comment.objects.create(
            post=post,
            author=gamer,
            content=content.strip()
        )
        
        # Update post's comment count
        post.comment_count = post.comments.count()
        post.save(update_fields=['comment_count'])
        
        return comment
    
    @staticmethod
    def get_gamer_activity_score(gamer, days=30):
        """
        Calculate a gamer's engagement activity score.
        Based on posts, comments, and likes in the last N days.
        
        Args:
            gamer: Gamer instance
            days: Number of days to look back (default: 30)
        
        Returns:
            int: Activity score
        """
        cutoff_date = timezone.now() - timedelta(days=days)
        
        posts = gamer.posts.filter(created_at__gte=cutoff_date).count()
        comments = gamer.comments.filter(created_at__gte=cutoff_date).count()
        likes = gamer.liked_posts.filter(created_at__gte=cutoff_date).count()
        
        # Weighted scoring: posts worth more than comments, comments worth more than likes
        score = (posts * 5) + (comments * 2) + (likes * 1)
        
        return score
    
    @staticmethod
    def get_trending_posts(hours=24, limit=10):
        """
        Get trending posts based on engagement in the last N hours.
        
        Args:
            hours: Number of hours to look back (default: 24)
            limit: Number of posts to return (default: 10)
        
        Returns:
            QuerySet of Post objects ordered by engagement
        """
        cutoff_time = timezone.now() - timedelta(hours=hours)
        
        comments_prefetch = Prefetch(
            'comments',
            Comment.objects.select_related('author').order_by('created_at')
        )
        likes_prefetch = Prefetch(
            'likes',
            Like.objects.select_related('gamer')
        )
        media_prefetch = Prefetch(
            'media',
            PostMedia.objects.order_by('order')
        )
        
        posts = Post.objects.filter(
            created_at__gte=cutoff_time
        ).select_related('author').prefetch_related(
            comments_prefetch,
            likes_prefetch,
            media_prefetch
        ).order_by('-like_count', '-comment_count')[:limit]
        
        return posts
