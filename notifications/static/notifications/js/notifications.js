/**
 * WebSocket client for real-time notifications
 * Manages WebSocket connection with fallback to polling
 */
class NotificationClient {
    constructor(options = {}) {
        this.options = {
            reconnectAttempts: 5,
            reconnectDelay: 3000,
            heartbeatInterval: 30000,
            pollInterval: 5000,
            useWebSocket: true,
            ...options
        };
        
        this.ws = null;
        this.reconnectCount = 0;
        this.heartbeatTimer = null;
        this.pollTimer = null;
        this.connected = false;
    }
    
    /**
     * Initialize the notification client
     */
    init() {
        if (this.options.useWebSocket && this.supportsWebSocket()) {
            this.connectWebSocket();
        } else {
            this.startPolling();
        }
    }
    
    /**
     * Check if browser supports WebSocket
     */
    supportsWebSocket() {
        return 'WebSocket' in window || 'MozWebSocket' in window;
    }
    
    /**
     * Connect to WebSocket
     */
    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/notifications/`;
        
        try {
            this.ws = new WebSocket(wsUrl);
            
            this.ws.onopen = () => {
                console.log('✓ WebSocket connected');
                this.connected = true;
                this.reconnectCount = 0;
                this.setupHeartbeat();
                this.onConnect();
            };
            
            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleMessage(data);
                } catch (e) {
                    console.error('Failed to parse WebSocket message:', e);
                }
            };
            
            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.onError(error);
            };
            
            this.ws.onclose = () => {
                console.log('WebSocket disconnected');
                this.connected = false;
                this.clearHeartbeat();
                this.attemptReconnect();
            };
        } catch (error) {
            console.error('Failed to create WebSocket:', error);
            this.startPolling();
        }
    }
    
    /**
     * Attempt to reconnect to WebSocket
     */
    attemptReconnect() {
        if (this.reconnectCount < this.options.reconnectAttempts) {
            this.reconnectCount++;
            const delay = this.options.reconnectDelay * this.reconnectCount;
            console.log(`Reconnecting in ${delay}ms...`);
            setTimeout(() => this.connectWebSocket(), delay);
        } else {
            console.log('Max reconnection attempts reached, falling back to polling');
            this.startPolling();
        }
    }
    
    /**
     * Setup heartbeat to keep connection alive
     */
    setupHeartbeat() {
        this.heartbeatTimer = setInterval(() => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify({ type: 'ping' }));
            }
        }, this.options.heartbeatInterval);
    }
    
    /**
     * Clear heartbeat timer
     */
    clearHeartbeat() {
        if (this.heartbeatTimer) {
            clearInterval(this.heartbeatTimer);
            this.heartbeatTimer = null;
        }
    }
    
    /**
     * Start polling for notifications (fallback)
     */
    startPolling() {
        if (this.pollTimer) return;  // Already polling
        
        console.log('Starting notification polling');
        this.pollTimer = setInterval(() => {
            this.fetchNotifications();
        }, this.options.pollInterval);
    }
    
    /**
     * Stop polling
     */
    stopPolling() {
        if (this.pollTimer) {
            clearInterval(this.pollTimer);
            this.pollTimer = null;
        }
    }
    
    /**
     * Fetch notifications via HTTP (polling)
     */
    async fetchNotifications() {
        try {
            const response = await fetch('/notifications/api/unread-count/');
            const data = await response.json();
            this.updateUnreadBadge(data.unread_count);
        } catch (error) {
            console.error('Failed to fetch notifications:', error);
        }
    }
    
    /**
     * Handle incoming WebSocket message
     */
    handleMessage(data) {
        if (data.type === 'notification') {
            this.onNotification(data.notification);
            this.updateUnreadBadge();
        } else if (data.type === 'unread_count_update') {
            this.updateUnreadBadge(data.unread_count);
        } else if (data.type === 'pong') {
            // Heartbeat response
        }
    }
    
    /**
     * Update unread notification badge
     */
    updateUnreadBadge(count = null) {
        const badge = document.getElementById('notification-badge');
        if (!badge) return;
        
        if (count === null) {
            // Fetch current count
            fetch('/notifications/api/unread-count/')
                .then(r => r.json())
                .then(data => {
                    const count = data.unread_count;
                    if (count > 0) {
                        badge.textContent = count > 99 ? '99+' : count;
                        badge.style.display = 'inline-block';
                    } else {
                        badge.style.display = 'none';
                    }
                });
        } else {
            if (count > 0) {
                badge.textContent = count > 99 ? '99+' : count;
                badge.style.display = 'inline-block';
            } else {
                badge.style.display = 'none';
            }
        }
    }
    
    /**
     * Show notification toast
     */
    showToast(notification) {
        const toast = document.createElement('div');
        toast.className = 'notification-toast';
        toast.innerHTML = `
            <div class="toast-icon">📬</div>
            <div class="toast-content">
                <strong>${notification.title}</strong>
                <p>${notification.category}</p>
            </div>
        `;
        
        document.body.appendChild(toast);
        
        // Remove after 5 seconds
        setTimeout(() => {
            toast.remove();
        }, 5000);
    }
    
    /**
     * Disconnect from WebSocket
     */
    disconnect() {
        this.stopPolling();
        this.clearHeartbeat();
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }
    
    // Override these methods in your app
    onConnect() {}
    onNotification(notification) {
        this.showToast(notification);
    }
    onError(error) {}
}

// Auto-initialize if DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Initialize notification client
    if (document.getElementById('notification-badge')) {
        window.notificationClient = new NotificationClient();
        window.notificationClient.init();
    }
    
    // Initialize dropdown toggle
    initNotificationDropdown();
});

/**
 * Initialize notification dropdown toggle functionality
 */
function initNotificationDropdown() {
    const notifBtn = document.querySelector('.notifications-btn');
    if (!notifBtn) return;
    
    const navDropdown = notifBtn.closest('.nav-dropdown');
    if (!navDropdown) return;
    
    // Toggle dropdown on button click
    notifBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        navDropdown.classList.toggle('open');
    });
    
    // Close dropdown when clicking outside
    document.addEventListener('click', (e) => {
        if (!navDropdown.contains(e.target)) {
            navDropdown.classList.remove('open');
        }
    });
    
    // Close dropdown when clicking on a notification
    const notifItems = navDropdown.querySelectorAll('.notification-item');
    notifItems.forEach(item => {
        item.addEventListener('click', () => {
            navDropdown.classList.remove('open');
        });
    });
}
