/**
 * Real-time Notifications using Pusher
 * 
 * Replaces Django Channels + custom WebSocket with Pusher's managed service.
 * Provides real-time notification updates without database polling or page refresh.
 * 
 * Architecture:
 * - Subscribes to 'gamikonnect-global' channel for system-wide events
 * - Subscribes to private user channels for personal notifications
 * - Updates notification badge and dropdown instantly
 * - Logs events to console for debugging
 */

class PusherNotifications {
    constructor(pusherKey, pusherCluster) {
        this.pusherKey = pusherKey;
        this.pusherCluster = pusherCluster;
        this.pusher = null;
        this.channels = new Set();
        this.unreadCount = 0;
        
        // Check if Pusher library is loaded
        if (typeof Pusher === 'undefined') {
            console.warn('🎮 Pusher library not loaded. Notifications disabled.');
            return;
        }
        
        this.init();
    }
    
    /**
     * Initialize Pusher connection and subscribe to channels
     */
    init() {
        try {
            // Configure Pusher with logging enabled for debugging
            Pusher.logToConsole = true;
            
            this.pusher = new Pusher(this.pusherKey, {
                cluster: this.pusherCluster,
                encrypted: true
            });
            
            console.log('🎮 Pusher connected to cluster:', this.pusherCluster);
            
            // Subscribe to global activity feed
            this.subscribeToGlobal();
            
            // Subscribe to user-specific private channel if user is logged in
            this.subscribeToUserChannel();
            
            // Set up connection event handlers
            this.setupConnectionHandlers();
            
        } catch (error) {
            console.error('🎮 Pusher initialization error:', error);
        }
    }
    
    /**
     * Subscribe to global activity and system notifications
     */
    subscribeToGlobal() {
        try {
            const channel = this.pusher.subscribe('gamikonnect-global');
            
            // Listen for new general notifications
            channel.bind('new-notification', (data) => {
                this.handleNewNotification(data);
            });
            
            // Listen for activity updates (achievements, level ups, competition results)
            channel.bind('activity-feed', (data) => {
                this.handleActivityUpdate(data);
            });
            
            // Listen for system-wide notifications
            channel.bind('new-system-notification', (data) => {
                this.handleSystemNotification(data);
            });
            
            // Listen for competition updates
            channel.bind('competition-update', (data) => {
                this.handleCompetitionUpdate(data);
            });

            channel.bind('feed-comment-created', (data) => {
                this.handleFeedCommentCreated(data);
            });

            channel.bind('feed-like-updated', (data) => {
                this.handleFeedLikeUpdated(data);
            });
            
            this.channels.add('gamikonnect-global');
            console.log('🎮 Subscribed to global notifications channel');
            
        } catch (error) {
            console.error('🎮 Error subscribing to global channel:', error);
        }
    }
    
    /**
     * Subscribe to user-specific private channel for personal notifications
     */
    subscribeToUserChannel() {
        try {
            // Get user type and ID from DOM (set by template)
            const userElement = document.querySelector('[data-user-id][data-user-type]');
            if (!userElement) {
                console.log('🎮 No user data found, skipping private channel subscription');
                return;
            }
            
            const userId = userElement.getAttribute('data-user-id');
            const userType = userElement.getAttribute('data-user-type');
            
            if (!userId || !userType) {
                console.warn('🎮 User ID or type missing from data attributes');
                return;
            }
            
            // Subscribe to private channel: private-{usertype}-{userid}
            const channelName = `private-${userType}-${userId}`;
            const channel = this.pusher.subscribe(channelName);
            
            // Listen for notifications sent to this specific user
            channel.bind('new-notification', (data) => {
                this.handleUserNotification(data);
            });
            
            this.channels.add(channelName);
            console.log(`🎮 Subscribed to user channel: ${channelName}`);
            
        } catch (error) {
            console.error('🎮 Error subscribing to user channel:', error);
        }
    }
    
    /**
     * Set up Pusher connection event handlers
     */
    setupConnectionHandlers() {
        this.pusher.connection.bind('connected', () => {
            console.log('🎮 Pusher connection established');
            this.updateConnectionStatus(true);
        });
        
        this.pusher.connection.bind('disconnected', () => {
            console.warn('🎮 Pusher disconnected');
            this.updateConnectionStatus(false);
        });
        
        this.pusher.connection.bind('error', (error) => {
            console.error('🎮 Pusher connection error:', error);
        });
    }
    
    /**
     * Handle a new general notification
     */
    handleNewNotification(data) {
        console.log('🎮 New notification:', data.title, data.message);
        this.showToast(data.title, data.message);
        this.incrementUnreadCount();
    }
    
    /**
     * Handle a system-wide notification
     */
    handleSystemNotification(data) {
        console.log('🎮 System notification:', data.title);
        this.showToast(
            `🔔 ${data.title}`,
            data.message,
            'system'
        );
    }
    
    /**
     * Handle activity feed updates (achievements, level ups, etc.)
     */
    handleActivityUpdate(data) {
        console.log('🎮 Activity update:', data.message);
        
        // Format the toast based on activity type
        const icon = this.getActivityIcon(data.activity_type);
        const title = `${icon} ${data.message}`;
        
        this.showToast(title, data.actor ? `by ${data.actor}` : '', 'activity');
    }
    
    /**
     * Handle user-specific notifications
     */
    handleUserNotification(data) {
        console.log('🎮 Personal notification:', data.title);
        this.showToast(
            `📩 ${data.title}`,
            data.message,
            'personal'
        );
        this.incrementUnreadCount();
    }
    
    /**
     * Handle competition updates
     */
    handleCompetitionUpdate(data) {
        console.log('🎮 Competition update:', data.title);
        this.showToast(
            `🏆 ${data.title}`,
            data.status || data.message,
            'competition'
        );
    }

    /**
     * Handle live feed comment events.
     */
    handleFeedCommentCreated(data) {
        console.log('🎮 Feed comment event:', data.post_id);
        if (window.feedsManager && typeof window.feedsManager.handleLiveCommentCreated === 'function') {
            window.feedsManager.handleLiveCommentCreated(data);
            return;
        }

        this.showToast(`💬 New comment from ${data.author_name}`, data.content || '', 'activity');
    }

    /**
     * Handle live feed like events.
     */
    handleFeedLikeUpdated(data) {
        console.log('🎮 Feed like event:', data.post_id);
        if (window.feedsManager && typeof window.feedsManager.handleLiveLikeUpdated === 'function') {
            window.feedsManager.handleLiveLikeUpdated(data);
            return;
        }

        this.showToast(`❤️ ${data.actor_name || 'Someone'} liked a post`, '', 'activity');
    }
    
    /**
     * Show a toast notification
     */
    showToast(title, message = '', type = 'default') {
        // Create toast element
        const toast = document.createElement('div');
        toast.className = `notification-toast toast-${type}`;
        
        // Determine background color based on type
        const bgColor = {
            'system': '#2c3e50',
            'activity': '#3498db',
            'personal': '#e74c3c',
            'competition': '#f39c12',
            'default': '#27ae60'
        }[type] || '#27ae60';
        
        toast.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            background-color: ${bgColor};
            color: white;
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            font-family: Arial, sans-serif;
            z-index: 9999;
            max-width: 350px;
            animation: slideIn 0.3s ease-out;
            margin-bottom: 10px;
        `;
        
        // Add CSS animation if not already in document
        if (!document.querySelector('style[data-toast-styles]')) {
            const style = document.createElement('style');
            style.setAttribute('data-toast-styles', 'true');
            style.textContent = `
                @keyframes slideIn {
                    from {
                        transform: translateX(400px);
                        opacity: 0;
                    }
                    to {
                        transform: translateX(0);
                        opacity: 1;
                    }
                }
                @keyframes slideOut {
                    from {
                        transform: translateX(0);
                        opacity: 1;
                    }
                    to {
                        transform: translateX(400px);
                        opacity: 0;
                    }
                }
            `;
            document.head.appendChild(style);
        }
        
        // Set content
        toast.innerHTML = `<strong>${title}</strong>${message ? '<br>' + message : ''}`;
        
        // Add to page
        document.body.appendChild(toast);
        
        // Auto-remove after 5 seconds with animation
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => {
                toast.remove();
            }, 300);
        }, 5000);
    }
    
    /**
     * Get emoji icon for activity type
     */
    getActivityIcon(activityType) {
        const icons = {
            'achievement': '🏅',
            'level_up': '⬆️',
            'competition_won': '🥇',
            'competition_completed': '✅',
            'competition_registered': '📋',
            'default': '⭐'
        };
        return icons[activityType] || icons['default'];
    }
    
    /**
     * Increment unread notification count
     */
    incrementUnreadCount() {
        const badge = document.querySelector('#notification-badge .notification-bubble');
        if (badge) {
            const currentCount = parseInt(badge.textContent) || 0;
            badge.textContent = currentCount + 1;
            badge.style.display = 'flex'; // Ensure it's visible
        }
    }
    
    /**
     * Update UI to reflect connection status
     */
    updateConnectionStatus(isConnected) {
        const statusEl = document.querySelector('[data-pusher-status]');
        if (statusEl) {
            statusEl.setAttribute('data-pusher-status', isConnected ? 'connected' : 'disconnected');
            statusEl.style.color = isConnected ? '#27ae60' : '#e74c3c';
            statusEl.textContent = isConnected ? '● Online' : '● Offline';
        }
    }
    
    /**
     * Get current Pusher connection state
     */
    isConnected() {
        return this.pusher && this.pusher.connection.state === 'connected';
    }
    
    /**
     * Manually trigger a test notification (for debugging)
     */
    testNotification() {
        console.log('🎮 Sending test notification');
        this.showToast(
            '🎮 Test Notification',
            'Pusher is working correctly!',
            'default'
        );
    }
}

/**
 * Initialize Pusher notifications when DOM is ready
 */
document.addEventListener('DOMContentLoaded', function() {
    // Get Pusher credentials from window object (set by template)
    if (window.PUSHER_KEY && window.PUSHER_CLUSTER) {
        window.notificationClient = new PusherNotifications(
            window.PUSHER_KEY,
            window.PUSHER_CLUSTER
        );
        
        // Expose test method for debugging in console
        window.testNotification = () => {
            if (window.notificationClient) {
                window.notificationClient.testNotification();
            }
        };
        
        console.log('🎮 Real-time notifications initialized');
        console.log('💡 Tip: Run testNotification() in console to test');
    } else {
        console.warn('🎮 Pusher credentials not found. Notifications disabled.');
    }
});
