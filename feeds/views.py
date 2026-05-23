"""
Views for the feeds app.
Handles feed listing, post creation, comments, and likes with optimized queries.
"""
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Prefetch, Count
from django.db import IntegrityError, transaction
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib import messages
from django.utils import timezone

# Site context
from core.views import base_site_context

# Models
from accounts.models import Gamer
from .models import Post, PostMedia, Comment, Like
from notifications.models import Notification, NotificationRecipient, NotificationCategory, NotificationImportance
from notifications.pusher_client import broadcast_notification, broadcast_user_notification

# Forms
from .forms import PostForm, PostMediaForm, CommentForm

logger = logging.getLogger(__name__)


def get_gamer(request):
    """Returns the Gamer object for the current session, or None."""
    if request.session.get('role') not in ['gamer', 'shop_owner']:
        return None
    try:
        return Gamer.objects.get(id=request.session.get('user_id'))
    except Gamer.DoesNotExist:
        return None


def create_notification(title, message, category, importance, recipient_gamer, related_post=None):
    """
    Create and send a notification to a gamer.
    
    Args:
        title: Notification title
        message: Notification message
        category: NotificationCategory choice
        importance: NotificationImportance choice
        recipient_gamer: Gamer to receive notification
        actor_gamer: Gamer who triggered the notification (optional)
        related_post: Post related to the notification (optional)
    """
    try:
        notification = Notification.objects.create(
            title=title,
            message=message,
            category=category,
            importance=importance,
        )
        
        # Create recipient record
        NotificationRecipient.objects.create(
            notification=notification,
            gamer=recipient_gamer,
            delivery_status='sent',
            sent_at=timezone.now(),
        )
        
        return notification
    except Exception as e:
        logger.error(f"Failed to create notification: {e}")
        return None


def get_optimized_feed_posts(page=1, posts_per_page=10):
    """
    Get optimized feed posts using select_related and prefetch_related.
    This is the "Cheat Code" to prevent N+1 query problems.
    """
    # Prefetch comments with their authors
    comments_prefetch = Prefetch(
        'comments',
        Comment.objects.select_related('author').order_by('created_at')
    )
    
    # Prefetch likes
    likes_prefetch = Prefetch(
        'likes',
        Like.objects.select_related('gamer')
    )
    
    # Prefetch media
    media_prefetch = Prefetch(
        'media',
        PostMedia.objects.order_by('order')
    )
    
    # Main query with all optimizations
    posts = Post.objects.select_related('author').prefetch_related(
        comments_prefetch,
        likes_prefetch,
        media_prefetch
    ).order_by('-created_at')
    
    # Paginate
    paginator = Paginator(posts, posts_per_page)
    try:
        page_obj = paginator.page(page)
    except (EmptyPage, PageNotAnInteger):
        page_obj = paginator.page(1)
    
    return page_obj


# ---------------------------------------------------------------------------
# Public Feed View
# ---------------------------------------------------------------------------

def feed_list(request):
    """
    Display the main feed with all posts.
    Uses optimized queries to prevent N+1 problems.
    """
    current_gamer = get_gamer(request)
    
    # Get page number from query params
    page = request.GET.get('page', 1)
    page_obj = get_optimized_feed_posts(page=page)
    
    # Prepare context
    context = base_site_context()
    context.update({
        'page_obj': page_obj,
        'posts': page_obj.object_list,
        'current_gamer': current_gamer,
        'is_feed': True,
    })
    
    return render(request, 'feeds/feed_list.html', context)


# ---------------------------------------------------------------------------
# Post Creation
# ---------------------------------------------------------------------------

@require_http_methods(["GET", "POST"])
def create_post(request):
    """
    Create a new post with optional media uploads.
    """
    gamer = get_gamer(request)
    if not gamer:
        messages.error(request, 'You must be logged in as a gamer to create posts.')
        return redirect('login')
    
    if request.method == 'POST':
        form = PostForm(request.POST)
        
        if form.is_valid():
            # Create the post
            post = Post.objects.create(
                author=gamer,
                content=form.cleaned_data.get('content', '').strip()
            )
            
            # Handle media uploads (if provided via AJAX or form)
            media_files = request.FILES.getlist('media')
            if media_files:
                for idx, file in enumerate(media_files):
                    # Determine if it's image or video based on mime type
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
            
            messages.success(request, 'Post created successfully!')
            return redirect('feeds:feed_list')
        else:
            messages.error(request, 'Error creating post. Please check your input.')
    else:
        form = PostForm()
    
    context = base_site_context()
    context.update({
        'form': form,
        'title': 'Create a Post',
    })
    
    return render(request, 'feeds/create_post.html', context)


# ---------------------------------------------------------------------------
# Post Detail View
# ---------------------------------------------------------------------------

def post_detail(request, post_id):
    """
    Display a single post with all comments and likes.
    """
    current_gamer = get_gamer(request)
    
    # Fetch post with optimizations
    post = get_object_or_404(
        Post.objects.select_related('author').prefetch_related(
            'media',
            'comments__author',
            'likes'
        ),
        id=post_id
    )
    
    # Get comment form
    comment_form = CommentForm() if request.method == 'GET' else None
    
    context = base_site_context()
    context.update({
        'post': post,
        'current_gamer': current_gamer,
        'comment_form': comment_form,
        'media': post.media.all(),
        'comments': post.comments.all(),
        'likes': post.likes.all(),
    })
    
    return render(request, 'feeds/post_detail.html', context)


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------

@require_http_methods(["POST"])
def add_comment(request, post_id):
    """
    Add a comment to a post.
    Can be called via regular form submit or AJAX.
    """
    gamer = get_gamer(request)
    if not gamer:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Not authenticated'}, status=401)
        messages.error(request, 'You must be logged in to comment.')
        return redirect('login')
    
    post = get_object_or_404(Post, id=post_id)
    
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = Comment.objects.create(
            post=post,
            author=gamer,
            content=form.cleaned_data['content']
        )
        post_channel = f'feed-post-{post.id}'
        
        # Update post's comment count
        post.comment_count = post.comments.count()
        post.save(update_fields=['comment_count'])
        
        # Send notification to post author if they're different
        if post.author != gamer:
            gamer_name = gamer.custom_username or f"{gamer.first_name} {gamer.last_name}"
            create_notification(
                title=f"New comment from {gamer_name}",
                message=f"{gamer_name} commented on your post",
                category=NotificationCategory.GENERAL,
                importance=NotificationImportance.MEDIUM,
                recipient_gamer=post.author,
                related_post=post
            )
            broadcast_user_notification(
                post.author.id,
                'gamer',
                {
                    'title': f'New comment from {gamer_name}',
                    'message': f'{gamer_name} commented on your post',
                    'post_id': str(post.id),
                    'comment_id': str(comment.id),
                    'comment_count': post.comment_count,
                    'actor_name': gamer_name,
                    'content': comment.content,
                    'timestamp': comment.created_at.isoformat(),
                }
            )

        broadcast_notification(
            post_channel,
            'feed-post-comment-created',
            {
                'post_id': str(post.id),
                'comment_id': str(comment.id),
                'author_id': gamer.id,
                'author_name': gamer.custom_username or f"{gamer.first_name} {gamer.last_name}",
                'content': comment.content,
                'comment_count': post.comment_count,
                'timestamp': comment.created_at.isoformat(),
            }
        )

        broadcast_notification(
            'gamikonnect-global',
            'feed-comment-created',
            {
                'post_id': str(post.id),
                'comment_id': str(comment.id),
                'author_id': gamer.id,
                'author_name': gamer.custom_username or f"{gamer.first_name} {gamer.last_name}",
                'content': comment.content,
                'comment_count': post.comment_count,
                'timestamp': comment.created_at.isoformat(),
            }
        )
        
        # Return JSON if AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'comment': {
                    'id': str(comment.id),
                    'author': gamer.custom_username or f"{gamer.first_name} {gamer.last_name}",
                    'content': comment.content,
                    'created_at': comment.created_at.isoformat(),
                }
            })
        
        messages.success(request, 'Comment added successfully!')
    else:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Invalid comment'}, status=400)
        messages.error(request, 'Error adding comment.')
    
    return redirect('feeds:post_detail', post_id=post_id)


@require_http_methods(["POST"])
def delete_comment(request, comment_id):
    """
    Delete a comment (only by the author or admin).
    """
    gamer = get_gamer(request)
    if not gamer:
        return HttpResponseForbidden('Not authenticated')
    
    comment = get_object_or_404(Comment, id=comment_id)
    post_id = comment.post.id
    
    # Only allow deletion by comment author
    if comment.author != gamer:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Permission denied'}, status=403)
        return HttpResponseForbidden('You can only delete your own comments.')
    
    comment.delete()
    
    # Update post's comment count
    post = comment.post
    post.comment_count = post.comments.count()
    post.save(update_fields=['comment_count'])
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    
    messages.success(request, 'Comment deleted.')
    return redirect('post_detail', post_id=post_id)


# ---------------------------------------------------------------------------
# Likes
# ---------------------------------------------------------------------------

@require_http_methods(["POST"])
def toggle_like(request, post_id):
    """
    Toggle a like on a post (AJAX endpoint).
    Returns JSON with updated like count.
    """
    gamer = get_gamer(request)
    if not gamer:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    post = get_object_or_404(Post, id=post_id)
    post_channel = f'feed-post-{post.id}'
    
    with transaction.atomic():
        # Check if gamer already liked this post
        like = Like.objects.select_for_update().filter(post=post, gamer=gamer).first()
        
        if like:
            # Unlike
            like.delete()
            liked = False
        else:
            # Like
            try:
                Like.objects.create(post=post, gamer=gamer)
                liked = True
            except IntegrityError:
                # Another request created the like first; treat as liked.
                liked = True
        
    # Send notification to post author if they're different
    if liked and post.author != gamer:
        gamer_name = gamer.custom_username or f"{gamer.first_name} {gamer.last_name}"
        create_notification(
            title=f"{gamer_name} liked your post",
            message=f"{gamer_name} liked one of your posts",
            category=NotificationCategory.GENERAL,
            importance=NotificationImportance.LOW,
            recipient_gamer=post.author,
            related_post=post
        )

        broadcast_user_notification(
            post.author.id,
            'gamer',
            {
                'title': f'{gamer_name} liked your post',
                'message': f'{gamer_name} liked one of your posts',
                'post_id': str(post.id),
                'like_count': post.like_count,
                'actor_name': gamer_name,
                'liked': liked,
                'timestamp': timezone.now().isoformat(),
            }
        )

    broadcast_notification(
        post_channel,
        'feed-post-like-updated',
        {
            'post_id': str(post.id),
            'liked': liked,
            'like_count': post.like_count,
            'actor_id': gamer.id,
            'actor_name': gamer.custom_username or f"{gamer.first_name} {gamer.last_name}",
            'timestamp': timezone.now().isoformat(),
        }
    )

    broadcast_notification(
        'gamikonnect-global',
        'feed-like-updated',
        {
            'post_id': str(post.id),
            'liked': liked,
            'like_count': post.like_count,
            'actor_id': gamer.id,
            'actor_name': gamer.custom_username or f"{gamer.first_name} {gamer.last_name}",
            'timestamp': timezone.now().isoformat(),
        }
    )
    
    # Update post's like count
    post.like_count = post.likes.count()
    post.save(update_fields=['like_count'])
    
    return JsonResponse({
        'success': True,
        'liked': liked,
        'like_count': post.like_count,
    })


# ---------------------------------------------------------------------------
# Gamer Profile Feed
# ---------------------------------------------------------------------------

def gamer_feed(request, gamer_id):
    """
    Display posts from a specific gamer.
    """
    current_gamer = get_gamer(request)
    target_gamer = get_object_or_404(Gamer, id=gamer_id)
    
    # Get gamer's posts with optimizations
    page = request.GET.get('page', 1)
    
    comments_prefetch = Prefetch(
        'comments',
        Comment.objects.select_related('author').order_by('created_at')
    )
    media_prefetch = Prefetch('media', PostMedia.objects.order_by('order'))
    
    posts = Post.objects.filter(author=target_gamer).select_related('author').prefetch_related(
        comments_prefetch,
        'likes',
        media_prefetch
    ).order_by('-created_at')
    
    paginator = Paginator(posts, 10)
    try:
        page_obj = paginator.page(page)
    except (EmptyPage, PageNotAnInteger):
        page_obj = paginator.page(1)
    
    context = base_site_context()
    context.update({
        'target_gamer': target_gamer,
        'current_gamer': current_gamer,
        'page_obj': page_obj,
        'posts': page_obj.object_list,
        'is_gamer_feed': True,
    })
    
    return render(request, 'feeds/gamer_feed.html', context)
