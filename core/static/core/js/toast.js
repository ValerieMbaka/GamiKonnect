class ToastManager {
    constructor() {
        this.container = null;
        this.template = null;
        this.recentToasts = [];
        this.dedupeWindowMs = 2000;
        this.init();
    }

    init() {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setup());
        } else {
            this.setup();
        }
    }

    setup() {
        this.ensureContainer();
        this.template = document.getElementById('toast-template');
        this.processDjangoMessages();
    }

    ensureContainer() {
        this.container = document.getElementById('toast-container');
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.id = 'toast-container';
            document.body.appendChild(this.container);
        }
    }

    processDjangoMessages() {
        const messageElement = document.getElementById('django-messages');
        if (!messageElement) return;

        try {
            const data = JSON.parse(messageElement.textContent);
            data.forEach(m => {
                const tags = (m.tags || '').split(' ');
                let type = 'info';
                if (tags.includes('error')) type = 'error';
                else if (tags.includes('success')) type = 'success';
                else if (tags.includes('warning')) type = 'warning';
                
                this.show({
                    type: type,
                    title: type.charAt(0).toUpperCase() + type.slice(1),
                    message: m.text
                });
            });
        } catch (e) {
            console.error('Failed to parse Django messages', e);
        }
    }

    show(options) {
        const {
            type = 'info', title = '', message = '', duration = 8000,
            showCountdown = false, countdown = 10, redirectUrl = null,
            primaryAction = null, primaryActionText = 'Action'
        } = options;

        const now = Date.now();
        const key = `${type}|${message}`;
        this.recentToasts = this.recentToasts.filter(entry => now - entry.time < this.dedupeWindowMs);
        if (this.recentToasts.some(entry => entry.key === key)) return null;
        
        this.recentToasts.push({ key, time: now });

        const toastElement = this.createToastFromTemplate({
            type, title, message, showCountdown, countdown, primaryAction, primaryActionText
        });

        this.container.appendChild(toastElement);
        setTimeout(() => { toastElement.classList.add('show'); }, 10);

        if (showCountdown && redirectUrl) this.startCountdown(toastElement, countdown, redirectUrl);
        if (duration > 0 && !showCountdown) setTimeout(() => { this.hide(toastElement); }, duration);

        return toastElement;
    }

    createToastFromTemplate(data) {
        const clone = this.template.content.cloneNode(true);
        const toast = clone.querySelector('.toast');
        
        toast.classList.add(data.type);
        toast.dataset.toastId = Date.now().toString();
        
        const iconMap = {
            success: 'fas fa-check-circle', error: 'fas fa-exclamation-circle',
            info: 'fas fa-info-circle', warning: 'fas fa-exclamation-triangle',
            registration_success: 'fas fa-trophy'
        };
        
        clone.querySelector('.toast-icon i').className = iconMap[data.type] || 'fas fa-info-circle';
        clone.querySelector('.toast-title').textContent = data.title;
        clone.querySelector('.toast-message').textContent = data.message;
        
        const countdownSection = clone.querySelector('.toast-countdown');
        if (data.showCountdown) {
            countdownSection.classList.remove('hidden');
            clone.querySelector('.countdown-timer').textContent = `${data.countdown}s`;
        }
        
        const actionBtn = clone.querySelector('.btn-toast-action');
        if (data.primaryAction) {
            actionBtn.classList.remove('hidden');
            actionBtn.querySelector('.action-text').textContent = data.primaryActionText;
            actionBtn.onclick = data.primaryAction;
        }
        
        clone.querySelector('.btn-toast-close').onclick = () => this.hide(toast);
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
        toastElement.countdownInterval = countdownInterval;
    }

    hide(toastElement) {
        if (!toastElement) return;
        if (toastElement.countdownInterval) clearInterval(toastElement.countdownInterval);
        toastElement.classList.remove('show');
        setTimeout(() => {
            if (toastElement.parentElement) toastElement.parentElement.removeChild(toastElement);
        }, 400);
    }

    success(title, message, duration = 5000) { return this.show({ type: 'success', title, message, duration }); }
    error(title, message, duration = 5000) { return this.show({ type: 'error', title, message, duration }); }
    info(title, message, duration = 5000) { return this.show({ type: 'info', title, message, duration }); }
    warning(title, message, duration = 5000) { return this.show({ type: 'warning', title, message, duration }); }
}

window.toastManager = new ToastManager();