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
    
    return render(request, 'feeds/feeds.html', context)


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


# ---------------------------------------------------------------------------
# AJAX API Endpoints for Modal-Based UI
# ---------------------------------------------------------------------------

@require_http_methods(["POST"])
def api_create_post(request):
    """
    API endpoint for creating posts via AJAX (modal form).
    Returns JSON response with success status.
    """
    gamer = get_gamer(request)
    if not gamer:
        return JsonResponse({'success': False, 'message': 'Not authenticated'}, status=401)
    
    content = request.POST.get('content', '').strip()
    image_file = request.FILES.get('image')
    video_file = request.FILES.get('video')
    
    if not content and not image_file and not video_file:
        return JsonResponse({
            'success': False, 
            'message': 'Please write something or add media to post.'
        }, status=400)
    
    try:
        # Create the post
        post = Post.objects.create(
            author=gamer,
            content=content,
        )
        
        # Handle media files (image and video uploaded separately)
        order = 0
        if image_file:
            PostMedia.objects.create(
                post=post,
                file=image_file,
                media_type='image',
                order=order
            )
            order += 1
        
        if video_file:
            PostMedia.objects.create(
                post=post,
                file=video_file,
                media_type='video',
                order=order
            )
        
        return JsonResponse({
            'success': True,
            'message': 'Post created successfully!',
            'post_id': str(post.id)
        })
    
    except Exception as e:
        logger.error(f"Error creating post: {e}")
        return JsonResponse({
            'success': False,
            'message': 'Failed to create post. Please try again.'
        }, status=500)


@require_http_methods(["GET"])
def api_get_post_comments(request, post_id):
    """
    API endpoint to fetch comments for a post (modal comments list).
    Returns JSON with list of comments.
    """
    try:
        post = get_object_or_404(Post, id=post_id)
    except:
        return JsonResponse({'success': False, 'message': 'Post not found'}, status=404)
    
    comments = Comment.objects.filter(post=post).select_related('author').order_by('created_at')
    
    comments_data = [
        {
            'id': str(comment.id),
            'author_id': str(comment.author.id),
            'author_name': comment.author.get_full_name() or comment.author.username,
            'content': comment.content,
            'created_at': comment.created_at.isoformat(),
        }
        for comment in comments
    ]
    
    return JsonResponse({
        'success': True,
        'post_id': str(post_id),
        'comments': comments_data,
        'comment_count': len(comments_data)
    })


@require_http_methods(["POST"])
def api_add_comment(request, post_id):
    """
    API endpoint for adding comments via modal.
    Returns JSON response with new comment data.
    """
    gamer = get_gamer(request)
    if not gamer:
        return JsonResponse({'success': False, 'message': 'Not authenticated'}, status=401)
    
    post = get_object_or_404(Post, id=post_id)
    content = request.POST.get('content', '').strip()
    
    if not content:
        return JsonResponse({
            'success': False,
            'message': 'Comment cannot be empty.'
        }, status=400)
    
    try:
        comment = Comment.objects.create(
            post=post,
            author=gamer,
            content=content
        )
        
        # Update post comment count
        post.comment_count = post.comments.count()
        post.save(update_fields=['comment_count'])
        
        # Broadcast via Pusher
        broadcast_user_notification(
            f'feed-post-{post.id}',
            'feed-post-comment-created',
            {
                'post_id': str(post.id),
                'comment_id': str(comment.id),
                'author_id': str(gamer.id),
                'author_name': gamer.get_full_name() or gamer.username,
                'content': comment.content,
                'created_at': comment.created_at.isoformat(),
                'comment_count': post.comment_count,
            }
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Comment posted!',
            'comment_id': str(comment.id),
            'comment': {
                'id': str(comment.id),
                'author_name': gamer.get_full_name() or gamer.username,
                'content': comment.content,
                'created_at': comment.created_at.isoformat(),
            }
        })
    
    except Exception as e:
        logger.error(f"Error adding comment: {e}")
        return JsonResponse({
            'success': False,
            'message': 'Failed to post comment. Please try again.'
        }, status=500)


# ---------------------------------------------------------------------------
# API Endpoints for New Feeds Architecture
# ---------------------------------------------------------------------------

@require_http_methods(["GET"])
def api_posts_list(request):
    """
    API endpoint to list posts with pagination.
    Query params: page, page_size, category
    """
    page = request.GET.get('page', 1)
    page_size = request.GET.get('page_size', 10)
    category = request.GET.get('category', 'all')
    
    try:
        page_size = min(int(page_size), 50)  # Cap at 50
    except (ValueError, TypeError):
        page_size = 10
    
    # Get posts with optimization
    comments_prefetch = Prefetch(
        'comments',
        Comment.objects.select_related('author').order_by('-created_at')
    )
    likes_prefetch = Prefetch(
        'likes',
        Like.objects.select_related('gamer')
    )
    media_prefetch = Prefetch(
        'media',
        PostMedia.objects.order_by('order')
    )
    
    posts_qs = Post.objects.select_related('author').prefetch_related(
        comments_prefetch,
        likes_prefetch,
        media_prefetch
    ).order_by('-created_at')
    
    current_gamer = get_gamer(request)
    
    # Paginate
    paginator = Paginator(posts_qs, page_size)
    try:
        page_obj = paginator.page(page)
    except (EmptyPage, PageNotAnInteger):
        page_obj = paginator.page(1)
    
    # Serialize posts
    posts_data = []
    for post in page_obj.object_list:
        post_dict = {
            'id': str(post.id),
            'content': post.content,
            'created_at': post.created_at.isoformat(),
            'category': post.category if hasattr(post, 'category') else 'all',
            'author': {
                'id': post.author.id,
                'name': post.author.get_full_name() or post.author.username,
                'avatar': post.author.profile_picture.url if post.author.profile_picture else '/static/core/images/player.jpeg',
                'is_current_user': current_gamer and current_gamer.id == post.author.id,
            },
            'image': post.media.filter(media_type='image').first().file.url if post.media.filter(media_type='image').exists() else None,
            'video': None,
            'likes': post.likes.count(),
            'comments': post.comments.count(),
            'shares': 0,
            'liked_by_me': current_gamer and post.likes.filter(gamer=current_gamer).exists(),
        }
        posts_data.append(post_dict)
    
    return JsonResponse({
        'results': posts_data,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
        'current_page': page_obj.number,
        'total_pages': page_obj.paginator.num_pages,
    })


@require_http_methods(["GET"])
def api_post_comments_list(request, post_id):
    """
    API endpoint to list comments for a post with pagination.
    """
    post = get_object_or_404(Post, id=post_id)
    page = request.GET.get('page', 1)
    page_size = request.GET.get('page_size', 50)
    
    try:
        page_size = min(int(page_size), 100)
    except (ValueError, TypeError):
        page_size = 50
    
    comments_qs = Comment.objects.filter(post=post).select_related('author').order_by('-created_at')
    
    paginator = Paginator(comments_qs, page_size)
    try:
        page_obj = paginator.page(page)
    except (EmptyPage, PageNotAnInteger):
        page_obj = paginator.page(1)
    
    # Serialize comments
    comments_data = [
        {
            'id': str(c.id),
            'author_id': c.author.id,
            'author_name': c.author.get_full_name() or c.author.username,
            'author_avatar': c.author.profile_picture.url if c.author.profile_picture else '/static/core/images/player.jpeg',
            'content': c.content,
            'created_at': c.created_at.isoformat(),
        }
        for c in page_obj.object_list
    ]
    
    return JsonResponse({
        'results': comments_data,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
        'current_page': page_obj.number,
        'total_pages': page_obj.paginator.num_pages,
    })


@require_http_methods(["POST"])
def api_create_comment(request, post_id):
    """
    API endpoint to create a comment.
    """
    gamer = get_gamer(request)
    if not gamer:
        return JsonResponse({'success': False, 'message': 'Not authenticated'}, status=401)
    
    post = get_object_or_404(Post, id=post_id)
    content = request.POST.get('content', '').strip()
    
    if not content:
        return JsonResponse({'success': False, 'message': 'Comment cannot be empty'}, status=400)
    
    try:
        comment = Comment.objects.create(
            post=post,
            author=gamer,
            content=content
        )
        
        # Update post comment count
        post.comment_count = post.comments.count()
        post.save(update_fields=['comment_count'])
        
        return JsonResponse({
            'success': True,
            'comment': {
                'id': str(comment.id),
                'author_id': gamer.id,
                'author_name': gamer.get_full_name() or gamer.username,
                'author_avatar': gamer.profile_picture.url if gamer.profile_picture else '/static/core/images/player.jpeg',
                'content': comment.content,
                'created_at': comment.created_at.isoformat(),
            },
            'comment_count': post.comment_count,
        })
    except Exception as e:
        logger.error(f"Error creating comment: {e}")
        return JsonResponse({'success': False, 'message': 'Failed to create comment'}, status=500)


@require_http_methods(["POST"])
def api_like_post(request, post_id):
    """
    API endpoint to toggle like on a post.
    """
    gamer = get_gamer(request)
    if not gamer:
        return JsonResponse({'success': False, 'message': 'Not authenticated'}, status=401)
    
    post = get_object_or_404(Post, id=post_id)
    
    try:
        like = Like.objects.filter(post=post, gamer=gamer).first()
        
        if like:
            like.delete()
            is_liked = False
        else:
            Like.objects.create(post=post, gamer=gamer)
            is_liked = True
        
        # Update count
        post.like_count = post.likes.count()
        post.save(update_fields=['like_count'])
        
        return JsonResponse({
            'success': True,
            'liked': is_liked,
            'likes': post.like_count,
        })
    except Exception as e:
        logger.error(f"Error toggling like: {e}")
        return JsonResponse({'success': False, 'message': 'Failed to like post'}, status=500)


@require_http_methods(["POST"])
def api_delete_post(request, post_id):
    """
    API endpoint to delete a post.
    """
    gamer = get_gamer(request)
    if not gamer:
        return JsonResponse({'success': False, 'message': 'Not authenticated'}, status=401)
    
    post = get_object_or_404(Post, id=post_id)
    
    # Check ownership
    if post.author.id != gamer.id:
        return JsonResponse({'success': False, 'message': 'Permission denied'}, status=403)
    
    try:
        post.delete()
        return JsonResponse({'success': True, 'message': 'Post deleted'})
    except Exception as e:
        logger.error(f"Error deleting post: {e}")
        return JsonResponse({'success': False, 'message': 'Failed to delete post'}, status=500)


@require_http_methods(["GET"])
def api_members_list(request):
    """
    API endpoint to list members with search and filtering.
    """
    search_query = request.GET.get('q', '').strip()
    community = request.GET.get('community', 'all').strip()
    
    # Base query
    members_qs = Gamer.objects.all()
    
    # Search filter
    if search_query:
        from django.db.models import Q
        members_qs = members_qs.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(username__icontains=search_query) |
            Q(custom_username__icontains=search_query)
        )
    
    # Community filter (if implemented in your Gamer model)
    # if community != 'all' and hasattr(Gamer, 'community'):
    #     members_qs = members_qs.filter(community=community)
    
    # Limit results
    members_qs = members_qs[:20]
    
    members_data = [
        {
            'id': m.id,
            'name': m.get_full_name() or m.username,
            'username': m.custom_username or m.username,
            'avatar': m.profile_picture.url if m.profile_picture else '/static/core/images/player.jpeg',
            'date_joined': m.date_joined.strftime('%B %Y') if hasattr(m, 'date_joined') else 'Unknown',
        }
        for m in members_qs
    ]
    
    return JsonResponse({'results': members_data})
