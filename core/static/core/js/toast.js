// Toast Manager
class ToastManager {
    constructor() {
        this.container = null;
        this.template = null;
        this.recentToasts = [];
        this.dedupeWindowMs = 2000; // suppress identical toasts within 2s
        this.init();
    }

    init() {
        // Ensure toast container exists
        this.ensureContainer();
        // Get the toast template
        this.template = document.getElementById('toast-template');
    }

    ensureContainer() {
        this.container = document.getElementById('toast-container');
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.id = 'toast-container';
            document.body.appendChild(this.container);
        }
    }

    show(options) {
        const {
            type = 'info',
            title = '',
            message = '',
            duration = 8000,
            showCountdown = false,
            countdown = 10,
            redirectUrl = null,
            primaryAction = null,
            primaryActionText = 'Action'
        } = options;

        // Dedupe - suppress identical toasts within a short window
        const now = Date.now();
        const key = `${type}|${message}`;
        // purge old entries
        this.recentToasts = this.recentToasts.filter(entry => now - entry.time < this.dedupeWindowMs);
        if (this.recentToasts.some(entry => entry.key === key)) {
            return null;
        }
        this.recentToasts.push({ key, time: now });

        // Create toast from template
        const toastElement = this.createToastFromTemplate({
            type,
            title,
            message,
            showCountdown,
            countdown,
            primaryAction,
            primaryActionText
        });

        this.container.appendChild(toastElement);

        // Animate in
        setTimeout(() => {
            toastElement.classList.add('show');
        }, 10);

        // Handle countdown
        if (showCountdown && redirectUrl) {
            this.startCountdown(toastElement, countdown, redirectUrl);
        }

        // Auto-hide for non-countdown toasts
        if (duration > 0 && !showCountdown) {
            setTimeout(() => {
                this.hide(toastElement);
            }, duration);
        }

        return toastElement;
    }

    createToastFromTemplate(data) {
        const clone = this.template.content.cloneNode(true);
        const toast = clone.querySelector('.toast');
        
        // Set basic attributes
        toast.classList.add(data.type);
        toast.dataset.toastId = Date.now().toString();
        
        // Set icon based on type
        const iconMap = {
            success: 'fas fa-check-circle',
            error: 'fas fa-exclamation-circle',
            info: 'fas fa-info-circle',
            warning: 'fas fa-exclamation-triangle',
            registration_success: 'fas fa-trophy'
        };
        
        const iconElement = clone.querySelector('.toast-icon i');
        iconElement.className = iconMap[data.type] || 'fas fa-info-circle';
        
        // Set content
        clone.querySelector('.toast-title').textContent = data.title;
        clone.querySelector('.toast-message').textContent = data.message;
        
        // Handle countdown section
        const countdownSection = clone.querySelector('.toast-countdown');
        if (data.showCountdown) {
            countdownSection.classList.remove('hidden');
            clone.querySelector('.countdown-timer').textContent = `${data.countdown}s`;
        }
        
        // Handle action button
        const actionBtn = clone.querySelector('.btn-toast-action');
        if (data.primaryAction) {
            actionBtn.classList.remove('hidden');
            actionBtn.querySelector('.action-text').textContent = data.primaryActionText;
            actionBtn.onclick = data.primaryAction;
        }
        
        // Close button
        const closeBtn = clone.querySelector('.btn-toast-close');
        closeBtn.onclick = () => this.hide(toast);
        
        return toast;
    }

    startCountdown(toastElement, countdown, redirectUrl) {
        const timerElement = toastElement.querySelector('.countdown-timer');
        const progressBar = toastElement.querySelector('.countdown-progress-bar');
        let timeLeft = countdown;
        
        const countdownInterval = setInterval(() => {
            timeLeft--;
            const progress = ((countdown - timeLeft) / countdown) * 100;
            
            timerElement.textContent = `${timeLeft}s`;
            progressBar.style.width = `${100 - progress}%`;
            
            if (timeLeft <= 0) {
                clearInterval(countdownInterval);
                window.location.href = redirectUrl;
            }
        }, 1000);
        
        // Store interval reference for cleanup
        toastElement.countdownInterval = countdownInterval;
    }

    hide(toastElement) {
        if (!toastElement) return;
        
        // Clear countdown if exists
        if (toastElement.countdownInterval) {
            clearInterval(toastElement.countdownInterval);
        }
        
        toastElement.classList.remove('show');
        
        // Remove after animation
        setTimeout(() => {
            if (toastElement.parentElement) {
                toastElement.parentElement.removeChild(toastElement);
            }
        }, 400);
    }

    // Convenience methods
    success(title, message, duration = 5000) {
        return this.show({ type: 'success', title, message, duration });
    }

    error(title, message, duration = 5000) {
        return this.show({ type: 'error', title, message, duration });
    }

    info(title, message, duration = 5000) {
        return this.show({ type: 'info', title, message, duration });
    }

    warning(title, message, duration = 5000) {
        return this.show({ type: 'warning', title, message, duration });
    }

    registrationSuccess(competitionSlug, competitionTitle) {
        return this.show({
            type: 'registration_success',
            title: 'Registration Successful! ',
            message: `You have successfully registered for "${competitionTitle}"!`,
            showCountdown: true,
            countdown: 10,
            redirectUrl: `/competitions/${competitionSlug}/`,
            primaryAction: () => {
                window.location.href = `/competitions/${competitionSlug}/`;
            },
            primaryActionText: 'View Now'
        });
    }
}

// Initialize Toast Manager
const Toast = new ToastManager();

// Legacy function for backward compatibility
function showToast(message, type = 'info', duration = 5000) {
    return Toast.show({
        type: type,
        title: type.charAt(0).toUpperCase() + type.slice(1),
        message: message,
        duration: duration
    });
}

function hideToast(toastElement) {
    Toast.hide(toastElement);
}

// Expose for scripts referencing window.toastManager
window.toastManager = Toast;