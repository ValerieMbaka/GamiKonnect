/**
 * Feeds App - AJAX & Real-Time Interactions
 * Handles likes, comments, and real-time updates using Pusher
 */

class FeedsManager {
    constructor() {
        this.csrfToken = this.getCsrfToken();
        this.activePostId = document.querySelector('[data-active-post-id]')?.dataset.activePostId || null;
        this.init();
    }

    getCsrfToken() {
        const cookieValue = document.cookie
            .split('; ')
            .find((row) => row.startsWith('csrftoken='));

        if (cookieValue) {
            return decodeURIComponent(cookieValue.split('=')[1]);
        }

        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }

    init() {
        this.attachEventListeners();
        this.attachRealtimeListeners();
        this.initializeToastContainer();
    }

    setActivePost(postId) {
        this.activePostId = postId;
    }

    attachRealtimeListeners() {
        const pusherClient = window.notificationClient?.pusher;
        if (!pusherClient) {
            return;
        }

        if (this.realtimeChannel || this.activePostChannel) {
            return;
        }

        if (this.activePostId) {
            this.activePostChannel = pusherClient.subscribe(`feed-post-${this.activePostId}`);
            this.activePostChannel.bind('feed-post-comment-created', (data) => {
                this.handleLiveCommentCreated(data);
            });
            this.activePostChannel.bind('feed-post-like-updated', (data) => {
                this.handleLiveLikeUpdated(data);
            });
            return;
        }

        this.realtimeChannel = pusherClient.subscribe('gamikonnect-global');
        this.realtimeChannel.bind('feed-comment-created', (data) => {
            this.handleLiveCommentCreated(data);
        });
        this.realtimeChannel.bind('feed-like-updated', (data) => {
            this.handleLiveLikeUpdated(data);
        });
    }

    /**
     * Attach event listeners to feed elements
     */
    attachEventListeners() {
        // Like buttons
        document.addEventListener('click', (e) => {
            if (e.target.closest('.like-btn')) {
                e.preventDefault();
                const btn = e.target.closest('.like-btn');
                const postId = btn.closest('[data-post-id]')?.dataset.postId;
                if (postId) {
                    this.toggleLike(postId, btn);
                }
            }
        });

        // Comment form submit guard
        document.addEventListener('submit', (e) => {
            const form = e.target;
            if (!form || form.id !== 'commentForm') {
                return;
            }

            const submitBtn = form.querySelector('.comment-submit-btn');
            if (!submitBtn) {
                return;
            }

            if (submitBtn.dataset.loading === 'true') {
                e.preventDefault();
                return;
            }

            submitBtn.dataset.loading = 'true';
            submitBtn.disabled = true;
            submitBtn.dataset.originalHtml = submitBtn.innerHTML;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Posting...';
        });

        // Comment deletion
        document.addEventListener('click', (e) => {
            if (e.target.closest('[data-delete-comment]')) {
                e.preventDefault();
                const commentId = e.target.closest('[data-delete-comment]')?.dataset.deleteComment;
                if (commentId) {
                    this.deleteCommentAjax(commentId);
                }
            }
        });
    }

    /**
     * Toggle like on a post via AJAX
     * @param {string} postId - UUID of the post
     * @param {HTMLElement} btn - Like button element
     */
    async toggleLike(postId, btn) {
        if (btn.dataset.loading === 'true') {
            return;
        }

        btn.dataset.loading = 'true';
        try {
            const response = await fetch(`/feeds/post/${postId}/like/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.csrfToken,
                    'X-Requested-With': 'XMLHttpRequest',
                },
                credentials: 'same-origin',
            });

            if (!response.ok) {
                if (response.status === 401) {
                    this.showToast('Please log in to like posts', 'info');
                    window.location.href = '/accounts/login/';
                } else {
                    throw new Error('Like toggle failed');
                }
                return;
            }

            const data = await response.json();
            
            // Update button state
            this.updateLikeButton(btn, data.liked);

            // Update like count in the post card
            const postCard = btn.closest('[data-post-id]');
            const statNumber = postCard?.querySelector('.stat-number');
            if (statNumber) {
                statNumber.textContent = data.like_count;
            }

            // Show feedback
            const message = data.liked ? 'Post liked!' : 'Like removed';
            this.showToast(message, 'success');

        } catch (error) {
            console.error('Like error:', error);
            this.showToast('Failed to like post. Please try again.', 'error');
        } finally {
            btn.dataset.loading = 'false';
        }
    }

    /**
     * Update like button UI
     * @param {HTMLElement} btn - Like button element
     * @param {boolean} liked - Whether post is now liked
     */
    updateLikeButton(btn, liked) {
        const icon = btn.querySelector('i');
        btn.dataset.liked = liked ? 'true' : 'false';

        if (liked) {
            icon.classList.remove('far');
            icon.classList.add('fas');
            btn.style.color = '#ff6b6b';
        } else {
            icon.classList.remove('fas');
            icon.classList.add('far');
            btn.style.color = '';
        }
    }

    handleLiveCommentCreated(data) {
        const postCard = document.querySelector(`[data-post-id="${data.post_id}"]`);
        if (postCard) {
            const commentCount = postCard.querySelector('[data-comment-count]');
            if (commentCount && data.comment_count !== undefined) {
                commentCount.textContent = data.comment_count;
            }
        }

        if (this.activePostId === data.post_id) {
            const commentsList = document.querySelector('[data-comments-list]');
            if (commentsList) {
                const emptyState = commentsList.querySelector('.empty-comments');
                if (emptyState) {
                    emptyState.remove();
                }

                const commentElement = document.createElement('div');
                commentElement.className = 'comment';
                commentElement.dataset.commentId = data.comment_id;
                commentElement.innerHTML = `
                    <div class="comment-header">
                        <div class="comment-author-info">
                            <div class="comment-avatar comment-avatar-placeholder">
                                <i class="fas fa-user"></i>
                            </div>
                            <div>
                                <span class="comment-author-name">${data.author_name}</span>
                                <span class="comment-time">just now</span>
                            </div>
                        </div>
                    </div>
                    <div class="comment-content">${this.escapeHtml(data.content).replace(/\n/g, '<br>')}</div>
                `;
                commentsList.prepend(commentElement);
            }
        }

        if (!this.isCurrentUser(data.author_id)) {
            this.showToast('New comment posted', 'info');
        }
    }

    handleLiveLikeUpdated(data) {
        const postCard = document.querySelector(`[data-post-id="${data.post_id}"]`);
        if (postCard) {
            const likeCount = postCard.querySelector('[data-like-count]');
            if (likeCount && data.like_count !== undefined) {
                likeCount.textContent = data.like_count;
            }
        }

        if (!this.isCurrentUser(data.actor_id)) {
            const message = data.liked ? 'Your post got a new like' : 'A like was removed';
            this.showToast(message, 'info');
        }
    }

    isCurrentUser(userId) {
        const currentUserId = document.querySelector('[data-user-id]')?.dataset.userId;
        return currentUserId && String(currentUserId) === String(userId);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text || '';
        return div.innerHTML;
    }

    /**
     * Delete comment via AJAX
     * @param {string} commentId - UUID of the comment
     */
    async deleteCommentAjax(commentId) {
        if (!confirm('Delete this comment?')) {
            return;
        }

        try {
            const response = await fetch(`/feeds/comment/${commentId}/delete/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.csrfToken,
                    'X-Requested-With': 'XMLHttpRequest',
                },
                credentials: 'same-origin',
            });

            if (!response.ok) {
                throw new Error('Delete failed');
            }

            // Find and remove comment element with animation
            const commentElement = document.querySelector(`[data-comment-id="${commentId}"]`);
            if (commentElement) {
                commentElement.style.opacity = '0';
                commentElement.style.transform = 'translateX(-20px)';
                setTimeout(() => {
                    commentElement.remove();
                    this.showToast('Comment deleted', 'success');
                }, 300);
            }

        } catch (error) {
            console.error('Delete error:', error);
            this.showToast('Failed to delete comment', 'error');
        }
    }

    /**
     * Show toast notification
     * @param {string} message - Message to display
     * @param {string} type - Type: 'success', 'error', 'info', 'warning'
     */
    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        
        const icons = {
            success: 'fas fa-check-circle',
            error: 'fas fa-exclamation-circle',
            info: 'fas fa-info-circle',
            warning: 'fas fa-exclamation-triangle',
        };

        toast.innerHTML = `
            <i class="${icons[type]}"></i>
            <span>${message}</span>
            <button class="toast-close">&times;</button>
        `;

        this.toastContainer.appendChild(toast);

        // Auto remove after 3 seconds
        const timeout = setTimeout(() => {
            toast.classList.add('removing');
            setTimeout(() => toast.remove(), 300);
        }, 3000);

        // Manual close
        toast.querySelector('.toast-close').addEventListener('click', () => {
            clearTimeout(timeout);
            toast.classList.add('removing');
            setTimeout(() => toast.remove(), 300);
        });
    }

    /**
     * Initialize toast container
     */
    initializeToastContainer() {
        this.toastContainer = document.getElementById('toastContainer');
        if (!this.toastContainer) {
            this.toastContainer = document.createElement('div');
            this.toastContainer.id = 'toastContainer';
            this.toastContainer.className = 'toast-container';
            document.body.appendChild(this.toastContainer);
        }
    }
}

/**
 * Global functions for backward compatibility
 */

function toggleLike(postId, btn) {
    window.feedsManager.toggleLike(postId, btn);
}

function deleteComment(commentId) {
    window.feedsManager.deleteCommentAjax(commentId);
}

function deletePost(postId) {
    if (confirm('Delete this post? This cannot be undone.')) {
        // TODO: Implement post deletion
        alert('Post deletion not yet implemented');
    }
}

function sharePost(postId) {
    // TODO: Implement share functionality
    const url = `${window.location.origin}/feeds/post/${postId}/`;
    
    if (navigator.share) {
        navigator.share({
            title: 'Check out this post',
            url: url,
        }).catch(err => console.log('Share error:', err));
    } else {
        // Fallback: copy to clipboard
        navigator.clipboard.writeText(url).then(() => {
            window.feedsManager.showToast('Post link copied to clipboard!', 'success');
        });
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.feedsManager = new FeedsManager();
});
