document.addEventListener('DOMContentLoaded', function() {
    const feedPosts = document.getElementById('feedPosts');
    const loadMoreBtn = document.querySelector('.load-more-btn');
    const filterChips = document.querySelectorAll('.filter-chip');
    const modalPostForm = document.getElementById('modalPostForm');
    const modalPostContent = document.getElementById('modalPostContent');
    const modalPhotoInput = document.getElementById('modalPhotoInput');
    const modalVideoInput = document.getElementById('modalVideoInput');
    const modalImagePreview = document.getElementById('modalImagePreview');
    const modalMediaPreview = document.getElementById('modalMediaPreview');
    const membersSearch = document.getElementById('membersSearchFull');
  
    // Tab switching
    document.querySelectorAll('.feeds-tab').forEach(tab => {
        tab.addEventListener('click', function () {
            document.querySelectorAll('.feeds-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            const target = tab.getAttribute('data-tab');
            document.querySelectorAll('.feeds-tab-content').forEach(c => c.classList.remove('active'));
            document.getElementById(target).classList.add('active');
            
            if (target === 'members') {
                setTimeout(() => {
                    ensureMembersLoaded();
                }, 100);
            }
        });
    });
  
    // CSRF + API helper
    function getCSRFToken() {
        const name = 'csrftoken=';
        const cookies = document.cookie ? document.cookie.split(';') : [];
        for (let i = 0; i < cookies.length; i++) {
            const c = cookies[i].trim();
            if (c.startsWith(name)) return decodeURIComponent(c.substring(name.length));
        }
        return null;
    }
    
    async function apiFetch(url, options) {
        const headers = options && options.headers ? options.headers : {};
        if (options && options.method && options.method.toUpperCase() !== 'GET') {
            headers['X-CSRFToken'] = getCSRFToken();
        }
        return fetch(url, Object.assign({}, options, { headers }));
    }

    // Posts loading & rendering
    let currentPage = 2;
    let currentCategory = 'all';
    let loading = false;

    function renderPostHTML(post) {
        const pid = post.id;
        const avatar = post.author.avatar || '/static/core/images/player.jpeg';
        const displayName = post.author.is_current_user ? 'You' : post.author.name;
        let media = '';
        if (post.image) {
            media = `<div class="post-image"><img src="${post.image}" alt="Post image"></div>`;
        } else if (post.video) {
            media = `<div class="post-video"><video controls><source src="${post.video}" type="video/mp4"></video></div>`;
        } else if (post.video_url) {
            media = `<div class="post-video"><video controls src="${post.video_url}"></video></div>`;
        }
        const likedClass = post.liked_by_me ? 'liked' : '';
        const ownerMenu = post.author.is_current_user ? `
            <div class="post-actions">
                <button class="btn btn-sm btn-light post-menu-btn" data-bs-toggle="dropdown" aria-expanded="false">
                    <i class="fas fa-ellipsis-h"></i>
                </button>
                <ul class="dropdown-menu dropdown-menu-end">
                    <li><button class="dropdown-item post-edit-btn" data-post-id="${pid}"><i class="fas fa-pen me-2"></i>Edit</button></li>
                    <li><button class="dropdown-item post-delete-btn" data-post-id="${pid}"><i class="fas fa-trash me-2"></i>Delete</button></li>
                </ul>
            </div>` : '';
        return (
            `<div class="post-card" data-post-id="${pid}" data-category="${post.category || 'all'}">
                <div class="post-header">
                    <div class="user-info">
                        <div class="user-avatar">
                            <img src="${avatar}" alt="${escapeHtml(displayName)}">
                        </div>
                        <div class="user-details">
                            <h5 class="username">${escapeHtml(displayName)}</h5>
                            <span class="post-time">${timeAgo(post.created_at)}</span>
                        </div>
                    </div>
                    ${ownerMenu}
                </div>
                <div class="post-content">
                    ${post.content ? `<p class="post-text">${linkify(escapeHtml(post.content))}</p>` : ''}
                    ${media}
                </div>
                <div class="post-stats-row">
                    <div class="post-stats">
                        <div class="stat-item like-stat ${likedClass}" data-post-id="${pid}"><i class="fas fa-heart"></i><span>${post.likes}</span></div>
                        <div class="stat-item comments-stat" data-post-id="${pid}"><i class="fas fa-comment"></i><span>${post.comments}</span></div>
                        <div class="stat-item share-stat" data-post-id="${pid}"><i class="fas fa-share"></i><span>${post.shares}</span></div>
                    </div>
                </div>
                <div class="comments-section" id="comments-${pid}" style="display: none;">
                    <div class="comment-input">
                        <img src="${avatar}" alt="User Avatar" class="comment-avatar">
                        <input type="text" placeholder="Write a comment..." class="comment-text">
                        <button class="comment-send" data-post-id="${pid}">
                            <i class="fas fa-paper-plane"></i>
                        </button>
                    </div>
                    <div class="comments-list"></div>
                </div>
            </div>`
        );
    }
    
    function escapeHtml(str) {
        return String(str).replace(/[&<>\"']/g, function(s) {
            return {
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                '\"': '&quot;'
            }[s];
        });
    }

    function linkify(text) {
        return text.replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank">$1</a>');
    }

    function timeAgo(iso) {
        const then = new Date(iso);
        const diff = Math.floor((Date.now() - then.getTime()) / 1000);
        if (diff < 60) return `${diff}s ago`;
        if (diff < 3600) return `${Math.floor(diff/60)}m ago`;
        if (diff < 86400) return `${Math.floor(diff/3600)}h ago`;
        return `${Math.floor(diff/86400)}d ago`;
    }

    async function loadPosts(reset = false) {
        if (loading) return;
        loading = true;
        
        if (reset) {
            currentPage = 1;
            if (feedPosts) feedPosts.innerHTML = '';
        }
        
        try {
            const resp = await apiFetch(`/feeds/api/posts/?page=${currentPage}&page_size=10&category=${currentCategory}`);
            if (!resp.ok) {
                console.error('Failed to load posts:', resp.status);
                return;
            }
            
            const data = await resp.json();
            console.log('Loaded posts:', data.results.length);
            
            if (feedPosts) {
                // Remove any initial loading placeholder element
                const loadingEl = document.getElementById('feedLoading');
                if (loadingEl) loadingEl.remove();

                if (data.results.length > 0) {
                    data.results.forEach(p => {
                        feedPosts.insertAdjacentHTML('beforeend', renderPostHTML(p));
                    });

                    // Load comments for all posts immediately
                    setTimeout(() => {
                        loadInitialCommentsForAllPosts();
                        wireDynamicHandlers();
                    }, 100);
                } else if (currentPage === 1 && !data.has_next) {
                    // No posts at all for this filter
                    feedPosts.innerHTML = `
                        <div class="no-posts-message text-center py-5 text-muted">
                            <i class="fas fa-gamepad fa-2x mb-3"></i>
                            <h5>No posts yet</h5>
                            <p class="mb-0">Be the first to share something with the community.</p>
                        </div>
                    `;
                }
            }
            
            if (loadMoreBtn) {
                loadMoreBtn.style.display = data.has_next ? 'block' : 'none';
            }
            
            currentPage += 1;
        } catch (error) {
            console.error('Error loading posts:', error);
        } finally {
            loading = false;
        }
    }

    // Load initial comments for ALL posts automatically
    function loadInitialCommentsForAllPosts() {
        console.log('Loading initial comments for all posts...');
        document.querySelectorAll('.post-card').forEach(postCard => {
            const postId = postCard.getAttribute('data-post-id');
            if (postId) {
                const commentsSection = document.getElementById(`comments-${postId}`);
                if (commentsSection) {
                    const commentsList = commentsSection.querySelector('.comments-list');
                    // Always load initial 3 comments for every post
                    fetchAndRenderInitialComments(postId, commentsList);
                }
            }
        });
    }

    // Fetch and render initial 3 comments
    async function fetchAndRenderInitialComments(postId, list) {
        if (!list) return;
        
        console.log(`Loading initial comments for post ${postId}`);
        
        try {
            const resp = await apiFetch(`/feeds/api/posts/${postId}/comments/?page=1&page_size=50`);
            if (!resp.ok) {
                console.error('Failed to load comments for post', postId);
                return;
            }

            const data = await resp.json();
            const allComments = data.results;
            console.log(`Post ${postId}: Found ${allComments.length} total comments`);

            // Clear existing content
            list.innerHTML = '';

            // Show first 3 comments
            const commentsToShow = allComments.slice(0, 3);
            commentsToShow.forEach(c => renderComment(list, c));

            // Show load more button if there are more than 3 comments
            if (allComments.length > 3) {
                const remainingCount = allComments.length - 3;
                const loadBtn = document.createElement('button');
                loadBtn.className = 'btn btn-link p-0 load-more-comments mt-2';
                loadBtn.textContent = `Load ${remainingCount} more comments`;
                
                loadBtn.addEventListener('click', function() {
                    // Load all remaining comments when clicked
                    const remainingComments = allComments.slice(3);
                    remainingComments.forEach(c => renderComment(list, c));
                    this.remove();
                });

                list.insertAdjacentElement('afterend', loadBtn);
            }

            list.dataset.loaded = '1';
            
        } catch (error) {
            console.error('Error loading initial comments for post', postId, error);
        }
    }

    // Fetch and render comments with load more functionality
    async function fetchAndRenderComments(postId, list, loadAll = false) {
        if (!list) return;
        
        const spinner = document.createElement('div');
        spinner.className = 'comments-loading text-center my-2';
        spinner.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Loading comments...`;
        list.insertAdjacentElement('beforebegin', spinner);

        try {
            const resp = await apiFetch(`/feeds/api/posts/${postId}/comments/?page=1&page_size=50`);
            if (!resp.ok) {
                spinner.textContent = "Failed to load comments";
                return;
            }

            const data = await resp.json();
            spinner.remove();

            const allComments = data.results;
            console.log(`Post ${postId}: Found ${allComments.length} total comments`);

            if (loadAll) {
                // Load all comments
                list.innerHTML = '';
                allComments.forEach(c => renderComment(list, c));
            } else {
                // For manual load more (when clicking comments stat)
                const existingComments = list.querySelectorAll('.comment');
                const currentlyDisplayed = existingComments.length;
                
                if (currentlyDisplayed === 0) {
                    // Show first 3 comments
                    const commentsToShow = allComments.slice(0, 3);
                    commentsToShow.forEach(c => renderComment(list, c));
                    
                    // Show load more if there are more comments
                    if (allComments.length > 3) {
                        const remainingCount = allComments.length - 3;
                        const loadBtn = document.createElement('button');
                        loadBtn.className = 'btn btn-link p-0 load-more-comments mt-2';
                        loadBtn.textContent = `Load ${remainingCount} more comments`;
                        
                        loadBtn.addEventListener('click', function() {
                            const remainingComments = allComments.slice(3);
                            remainingComments.forEach(c => renderComment(list, c));
                            this.remove();
                        });

                        list.insertAdjacentElement('afterend', loadBtn);
                    }
                } else {
                    // Already has comments, load all remaining
                    const remainingComments = allComments.slice(currentlyDisplayed);
                    remainingComments.forEach(c => renderComment(list, c));
                    
                    // Remove load more button if it exists
                    const existingLoadBtn = list.parentElement.querySelector('.load-more-comments');
                    if (existingLoadBtn) {
                        existingLoadBtn.remove();
                    }
                }
            }

            list.dataset.loaded = '1';
            
        } catch (error) {
            console.error('Error loading comments:', error);
            spinner.textContent = "Failed to load comments";
        }
    }

    function renderComment(list, c) {
        if (!list || !c) return;
        
        const avatar = c.author_avatar || c.author?.avatar || '/static/core/images/player.jpeg';
        const displayName = c.author_name || c.author?.name || 'Unknown';
        const commentHTML = `
            <div class="comment">
                <img src="${avatar}" alt="User Avatar" class="comment-avatar">
                <div class="comment-content">
                    <div class="comment-header">
                        <span class="comment-username">${escapeHtml(displayName)}</span>
                        <span class="comment-time">${timeAgo(c.created_at)}</span>
                    </div>
                    <p class="comment-text">${escapeHtml(c.content)}</p>
                </div>
            </div>`;
        
        list.insertAdjacentHTML('beforeend', commentHTML);
    }
    
    // Track which comment sections are expanded
    const expandedComments = new Set();

    // Dynamic handlers for likes and comments
    function wireDynamicHandlers() {
        // Like stat toggle
        document.querySelectorAll('.like-stat').forEach(stat => {
            if (stat.dataset.bound === '1') return;
            stat.dataset.bound = '1';
            stat.addEventListener('click', async function(){
                const postId = stat.getAttribute('data-post-id');
                try {
                    const resp = await apiFetch(`/feeds/api/posts/${postId}/like/`, {
                        method: 'POST'
                    });
                    if (!resp.ok) {
                        if (resp.status === 401) {
                            alert('Please log in to like posts.');
                            return;
                        }
                        console.error('Failed to like post');
                        return;
                    }
                    const d = await resp.json();
                    stat.querySelector('span').textContent = d.likes;
                    stat.classList.toggle('liked', d.liked);
                } catch (error) {
                    console.error('Error liking post:', error);
                }
            });
        });

        // Comments stat - load all comments when clicked
        document.querySelectorAll('.comments-stat').forEach(stat => {
            if (stat.dataset.bound === '1') return;
            stat.dataset.bound = '1';
            stat.addEventListener('click', async function(){
                const postId = stat.getAttribute('data-post-id');
                const section = document.getElementById(`comments-${postId}`);
                if (!section) return;
                
                // Toggle comments section visibility
                if (section.style.display === 'none' || section.style.display === '') {
                    // Show comments
                    section.style.display = 'block';
                    expandedComments.add(postId);
                    
                    const list = section.querySelector('.comments-list');
                    // Load all comments when showing the section
                    await fetchAndRenderComments(postId, list, true);
                    
                    // Smooth scroll to comments section
                    section.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                } else {
                    // Hide comments
                    section.style.display = 'none';
                    expandedComments.delete(postId);
                }
            });
        });

        // Send comment
        document.querySelectorAll('.comment-send').forEach(btn => {
            if (btn.dataset.bound === '1') return;
            btn.dataset.bound = '1';
            btn.addEventListener('click', async function(){
                const postId = this.getAttribute('data-post-id');
                const section = document.getElementById(`comments-${postId}`);
                if (!section) return;
                
                const input = section.querySelector('input.comment-text');
                const content = (input && input.value.trim()) || '';
                if (!content) return;
                
                try {
                    const form = new FormData();
                    form.append('content', content);
                    const resp = await apiFetch(`/feeds/api/posts/${postId}/comments/create/`, {
                        method: 'POST',
                        body: form
                    });
                    
                    if (!resp.ok) {
                        if (resp.status === 401) {
                            alert('Please log in to comment.');
                            return;
                        }
                        console.error('Failed to create comment');
                        return;
                    }
                    
                    const data = await resp.json();
                    input.value = '';
                    
                    const list = section.querySelector('.comments-list');
                    
                    // Use the data from the API response
                    const userAvatar = data.comment.author_avatar || '/static/core/images/player.jpeg';
                    
                    // Render the new comment with actual user data
                    const newCommentHTML = `
                        <div class="comment">
                            <img src="${userAvatar}" alt="User Avatar" class="comment-avatar">
                            <div class="comment-content">
                                <div class="comment-header">
                                    <span class="comment-username">You</span>
                                    <span class="comment-time">just now</span>
                                </div>
                                <p class="comment-text">${escapeHtml(content)}</p>
                            </div>
                        </div>`;
                    
                    // Insert new comment at the top
                    list.insertAdjacentHTML('afterbegin', newCommentHTML);
                    
                    // Update comments count
                    const postCard = section.closest('.post-card');
                    const statSpan = postCard && postCard.querySelector('.comments-stat span');
                    if (statSpan) {
                        statSpan.textContent = data.comment_count;
                    }
                } catch (error) {
                    console.error('Error creating comment:', error);
                }
            });
        });

        // Comment input enter key support
        document.querySelectorAll('.comment-text').forEach(input => {
            if (input.dataset.bound === '1') return;
            input.dataset.bound = '1';
            
            input.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    const sendBtn = this.closest('.comment-input').querySelector('.comment-send');
                    if (sendBtn) sendBtn.click();
                }
            });
        });

        // Delete post (author only)
        document.querySelectorAll('.post-delete-btn').forEach(btn => {
            if (btn.dataset.bound === '1') return;
            btn.dataset.bound = '1';
            btn.addEventListener('click', async function(){
                const postId = this.getAttribute('data-post-id');
                if (!postId) return;
                if (!confirm('Delete this post? This can be undone by admins but will be hidden from feeds.')) return;
                try {
                    const resp = await apiFetch(`/feeds/api/posts/${postId}/delete/`, { method: 'POST' });
                    if (!resp.ok) {
                        if (resp.status === 401) { alert('Please log in.'); return; }
                        if (resp.status === 403) { alert('You can only delete your own posts.'); return; }
                        alert('Failed to delete post.');
                        return;
                    }
                    const card = document.querySelector(`.post-card[data-post-id="${postId}"]`);
                    if (card) card.remove();
                    // Offer undo via Toast manager if available
                    if (window.Toast && typeof window.Toast.show === 'function') {
                        window.Toast.show({
                            type: 'info',
                            title: 'Post deleted',
                            message: 'Your post was hidden. Undo?',
                            primaryActionText: 'Undo',
                            primaryAction: async () => {
                                const r = await apiFetch(`/feeds/api/posts/${postId}/restore/`, { method: 'POST' });
                                if (r.ok) {
                                    await loadPosts(true);
                                    window.Toast.success('Restored', 'Your post is visible again.');
                                } else {
                                    window.Toast.error('Restore failed', 'Could not restore post.');
                                }
                            },
                            duration: 10000
                        });
                    }
                } catch (e) {
                    console.error('Error deleting post', e);
                    alert('Failed to delete post.');
                }
            });
        });

        // Edit handlers
        document.querySelectorAll('.post-edit-btn').forEach(btn => {
            if (btn.dataset.bound === '1') return;
            btn.dataset.bound = '1';
            btn.addEventListener('click', function(){
                const postId = this.getAttribute('data-post-id');
                enterEditMode(postId);
            });
        });
    }
  
    // Load more posts
    if (loadMoreBtn) {
        loadMoreBtn.addEventListener('click', function(){
            loadPosts(false);
        });
        // Infinite scroll using IntersectionObserver
        if ('IntersectionObserver' in window) {
            const io = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        loadPosts(false);
                    }
                });
            }, { rootMargin: '200px' });
            io.observe(loadMoreBtn);
        }
    }
  
    // Filters
    if (filterChips) {
        filterChips.forEach(chip => {
            chip.addEventListener('click', function(){
                filterChips.forEach(c => c.classList.remove('active'));
                chip.classList.add('active');
                currentCategory = chip.dataset.filter || 'all';
                loadPosts(true);
            });
        });
    }
  
    // Create Post Modal
    if (modalPostForm) {
        modalPostForm.addEventListener('submit', async function(e){
            e.preventDefault();
            const content = modalPostContent.value.trim();
            const image = modalPhotoInput.files[0];
            const video = modalVideoInput && modalVideoInput.files ? modalVideoInput.files[0] : null;

            if (!content && !image && !video) {
                alert('Please add some content or media to your post');
                return;
            }
            if (video && video.size > 5 * 1024 * 1024) {
                alert('Video must be 5MB or smaller.');
                return;
            }

            try {
                const form = new FormData();
                form.append('content', content);
                if (image) form.append('image', image);
                if (video) form.append('video', video);

                const resp = await apiFetch('/feeds/api/create-post/', { method: 'POST', body: form });

                if (!resp.ok) {
                    if (resp.status === 401) {
                        alert('Please log in.');
                        return;
                    }
                    const errorData = await resp.json().catch(()=>({error:'Unknown error'}));
                    alert('Failed: ' + (errorData.error || errorData.message || 'Unknown error'));
                    return;
                }

                // Reset form and close modal
                modalPostContent.value = '';
                if (modalPhotoInput) modalPhotoInput.value = '';
                if (modalVideoInput) modalVideoInput.value = '';
                if (modalMediaPreview) modalMediaPreview.style.display = 'none';

                const modal = bootstrap.Modal.getInstance(document.getElementById('createPostModal'));
                if (modal) modal.hide();

                await loadPosts(true);
            } catch (error) {
                console.error('Error submitting post:', error);
                alert('Failed. Please try again.');
            }
        });
    }

    // Preview selected image
    if (modalPhotoInput && modalImagePreview && modalMediaPreview) {
        modalPhotoInput.addEventListener('change', function(){
            const file = modalPhotoInput.files && modalPhotoInput.files[0];
            if (!file) {
                modalMediaPreview.style.display = 'none';
                return;
            }
            const reader = new FileReader();
            reader.onload = function(evt) {
                modalImagePreview.src = evt.target.result;
                modalMediaPreview.innerHTML = '';
                modalMediaPreview.appendChild(modalImagePreview);
                modalMediaPreview.style.display = 'block';
            };
            reader.readAsDataURL(file);
        });
    }

    // Preview selected video
    if (modalVideoInput && modalMediaPreview) {
        modalVideoInput.addEventListener('change', function(){
            const file = modalVideoInput.files && modalVideoInput.files[0];
            if (!file) {
                modalMediaPreview.style.display = 'none';
                return;
            }
            if (file.size > 5 * 1024 * 1024) {
                alert('Video must be 5MB or smaller.');
                modalVideoInput.value = '';
                modalMediaPreview.style.display = 'none';
                return;
            }
            const videoPreview = document.createElement('video');
            videoPreview.controls = true;
            videoPreview.style.maxWidth = "100%";
            videoPreview.style.borderRadius = "12px";
            const reader = new FileReader();
            reader.onload = function(evt) {
                videoPreview.src = evt.target.result;
                modalMediaPreview.innerHTML = '';
                modalMediaPreview.appendChild(videoPreview);
                modalMediaPreview.style.display = 'block';
            };
            reader.readAsDataURL(file);
        });
    }

    // Edit mode launcher
    function enterEditMode(postId) {
        const card = document.querySelector(`.post-card[data-post-id="${postId}"]`);
        if (!card || !modalPostForm) return;
        const text = card.querySelector('.post-text');
        modalPostContent.value = text ? text.textContent : '';
        if (modalPhotoInput) modalPhotoInput.value = '';
        if (modalVideoInput) modalVideoInput.value = '';
        if (modalMediaPreview) modalMediaPreview.style.display = 'none';
        modalPostForm.dataset.editing = '1';
        modalPostForm.dataset.postId = String(postId);
        const modal = new bootstrap.Modal(document.getElementById('createPostModal'));
        modal.show();
    }
  
    // Members viewing
    async function ensureMembersLoaded() {
        const container = document.getElementById('membersHorizontalList');
        if (!container || container.dataset.loaded === '1') return;
        await loadMembers();
    }

    async function loadMembers(query = '', community = 'all') {
        const container = document.getElementById('membersHorizontalList');
        if (!container) return;
        
        // Show loading state only if it's the initial load
        if (!container.dataset.loaded) {
            container.innerHTML = `
                <div class="members-loading">
                    <i class="fas fa-spinner fa-spin"></i>
                    <div>Loading members...</div>
                </div>
            `;
        }
        
        try {
            const resp = await apiFetch(`/feeds/api/members/?q=${encodeURIComponent(query)}&community=${encodeURIComponent(community)}`);
            if (!resp.ok) {
                container.innerHTML = `
                    <div class="members-empty">
                        <i class="fas fa-exclamation-circle"></i>
                        <div>Failed to load members</div>
                    </div>
                `;
                return;
            }
            
            const data = await resp.json();
            
            if (!data.results || data.results.length === 0) {
                container.innerHTML = `
                    <div class="members-empty">
                        <i class="fas fa-users"></i>
                        <div>No members found</div>
                    </div>
                `;
                return;
            }
            
            // Clear the container and render members
            container.innerHTML = '';
            
            data.results.forEach(m => {
                const avatar = m.avatar || '/static/core/images/player.jpeg';
                const username = m.is_current_user ? 'You' : (m.username || m.name);
                
                container.insertAdjacentHTML('beforeend', `
                    <div class="member-list-item" data-member-id="${m.id}">
                        <img src="${avatar}" alt="${escapeHtml(username)}" class="member-avatar">
                        <div class="member-info">
                            <div class="username">${escapeHtml(username)}</div>
                            <div class="date-joined">Joined ${escapeHtml(m.date_joined)}</div>
                        </div>
                        <button class="view-profile-btn" data-member-username="${escapeHtml(username)}">
                            View Profile
                        </button>
                    </div>
                `);
            });
            
            // Add click handlers for view profile buttons
            container.querySelectorAll('.view-profile-btn').forEach(btn => {
                btn.addEventListener('click', function() {
                    const memberUsername = this.getAttribute('data-member-username');
                    viewMemberProfile(memberUsername);
                });
            });
            
            // Mark as loaded
            container.dataset.loaded = '1';
            
        } catch (error) {
            console.error('Error loading members:', error);
            container.innerHTML = `
                <div class="members-empty">
                    <i class="fas fa-exclamation-circle"></i>
                    <div>Failed to load members</div>
                </div>
            `;
        }
    }

    // View member profile function
    function viewMemberProfile(username) {
        const profileUrl = `/users/profile/${username}/`;
        console.log(`Redirecting to profile: ${profileUrl}`);
        window.location.href = profileUrl;
    }

    // Members search functionality
    if (membersSearch) {
        membersSearch.addEventListener('input', function(){
            const container = document.getElementById('membersHorizontalList');
            if (container) {
                container.dataset.loaded = '';
            }
            loadMembers(membersSearch.value || '');
        });
    }

    // Members filter functionality
    document.querySelectorAll('.members-filters .chip').forEach(chip => {
        chip.addEventListener('click', function(){
            document.querySelectorAll('.members-filters .chip').forEach(c => c.classList.remove('active'));
            chip.classList.add('active');
            
            const container = document.getElementById('membersHorizontalList');
            if (container) {
                container.dataset.loaded = '';
            }
            
            loadMembers(membersSearch ? membersSearch.value : '', chip.dataset.community || 'all');
        });
    });

    // Handle initial tab load
    function handleInitialTabLoad() {
        const activeTab = document.querySelector('.feeds-tab.active');
        if (activeTab && activeTab.getAttribute('data-tab') === 'members') {
            ensureMembersLoaded();
        }
    }

    // Initial load - load posts immediately without skeleton loaders
    loadPosts(true);
    handleInitialTabLoad();
});