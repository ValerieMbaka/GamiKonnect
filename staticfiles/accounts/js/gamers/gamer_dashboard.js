/**
 * Gamer Dashboard Core Functionality
 */

class GamerProfileManager {
    constructor() {
        this.modal = document.getElementById('profileCompletionModal');
        this.avatarUpload = document.getElementById('avatarUpload');
        this.statusData = document.getElementById('profile-status');
        this.isComplete = this.statusData ? JSON.parse(this.statusData.textContent).isComplete : true;
        
        this.init();
    }

    init() {
        this.bindEvents();
        this.checkInitialState();
    }

    bindEvents() {
        document.querySelectorAll('[data-action="open-modal"]').forEach(btn => {
            btn.addEventListener('click', () => this.openModal());
        });

        document.querySelectorAll('[data-action="close-modal"]').forEach(btn => {
            btn.addEventListener('click', () => this.closeModal());
        });

        document.querySelectorAll('.profile-restricted').forEach(link => {
            link.addEventListener('click', (e) => {
                if (!this.isComplete) {
                    e.preventDefault();
                    if (window.toastManager) {
                        window.toastManager.error('Profile Incomplete', 'Please complete your profile first.');
                    }
                    this.openModal();
                }
            });
        });

        if (this.avatarUpload) {
            this.avatarUpload.addEventListener('change', (e) => this.handleAvatarUpload(e));
        }
    }

    checkInitialState() {
        if (!this.isComplete && this.modal) {
            this.modal.classList.add('show', 'mandatory');
        }
    }

    openModal() {
        if (this.modal) this.modal.classList.add('show');
    }

    closeModal() {
        if (this.modal && !this.modal.classList.contains('mandatory')) {
            this.modal.classList.remove('show');
        }
    }

    async handleAvatarUpload(event) {
        const file = event.target.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('profile_picture', file);
        formData.append('csrfmiddlewaretoken', document.querySelector('[name=csrfmiddlewaretoken]').value);

        try {
            const response = await fetch('/users/complete-profile/', {
                method: 'POST',
                body: formData,
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });
            const data = await response.json();
            
            if (data.success) {
                this.updateUI(data);
                if (window.toastManager) window.toastManager.success('Success', 'Avatar updated successfully!');
            } else {
                if (window.toastManager) window.toastManager.error('Error', data.message || 'Failed to update avatar.');
            }
        } catch (error) {
            console.error('Upload error:', error);
            if (window.toastManager) window.toastManager.error('Upload Failed', 'A network error occurred.');
        }
    }

    updateUI(data) {
        if (data.profile_picture_url) {
            document.querySelectorAll('.profile-main-avatar, .profile-avatar, .sidebar-avatar, .dropdown-avatar')
                .forEach(img => img.src = data.profile_picture_url);
        }
    }
}

class DashboardTabManager {
    constructor() {
        this.tabs = document.querySelectorAll('.profile-tab');
        this.contents = document.querySelectorAll('.profile-tab-content');
        if (this.tabs.length) this.init();
    }

    init() {
        this.tabs.forEach(tab => {
            tab.addEventListener('click', (e) => this.switchTab(e, tab));
        });
    }

    switchTab(event, selectedTab) {
        if (selectedTab.classList.contains('profile-restricted')) return;

        event.preventDefault();
        const targetId = selectedTab.getAttribute('data-tab');

        this.tabs.forEach(t => t.classList.remove('active'));
        this.contents.forEach(c => c.classList.remove('active'));

        selectedTab.classList.add('active');
        const targetContent = document.getElementById(targetId);
        if (targetContent) targetContent.classList.add('active');
    }
}

class CompetitionManager {
    constructor() {
        this.filters = document.querySelectorAll('.filter-btn');
        this.cards = document.querySelectorAll('.competition-card');
        this.timers = document.querySelectorAll('.countdown-timer');
        this.init();
    }

    init() {
        if (this.filters.length) this.initFilters();
        if (this.timers.length) {
            this.timers.forEach(timer => this.setupTimerData(timer));
            setInterval(() => this.updateTimers(), 60000);
        }
    }

    initFilters() {
        this.filters.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const filterValue = btn.getAttribute('data-filter');
                
                this.filters.forEach(f => f.classList.remove('active'));
                btn.classList.add('active');

                this.cards.forEach(card => {
                    const status = card.getAttribute('data-status');
                    card.style.display = (filterValue === 'all' || status === filterValue) ? 'block' : 'none';
                });
            });
        });
    }

    setupTimerData(timerContainer) {
        const segments = timerContainer.querySelectorAll('.countdown-segment');
        let totalMinutes = 0;

        segments.forEach(segment => {
            const val = parseInt(segment.querySelector('.countdown-value').textContent) || 0;
            const label = segment.querySelector('.countdown-label').textContent.toLowerCase();
            
            if (label.includes('day')) totalMinutes += val * 24 * 60;
            else if (label.includes('hour')) totalMinutes += val * 60;
            else if (label.includes('minute')) totalMinutes += val;
        });

        timerContainer.dataset.totalMinutes = totalMinutes;
    }

    updateTimers() {
        this.timers.forEach(timer => {
            let minutesLeft = parseInt(timer.dataset.totalMinutes);
            if (minutesLeft <= 0) return;
            
            minutesLeft--;
            timer.dataset.totalMinutes = minutesLeft;

            const d = Math.floor(minutesLeft / (24 * 60));
            const h = Math.floor((minutesLeft % (24 * 60)) / 60);
            const m = Math.floor(minutesLeft % 60);

            const segments = timer.querySelectorAll('.countdown-segment');
            if(segments.length === 3) {
                segments[0].querySelector('.countdown-value').textContent = d;
                segments[1].querySelector('.countdown-value').textContent = h;
                segments[2].querySelector('.countdown-value').textContent = m;
            } else if (segments.length === 2) {
                segments[0].querySelector('.countdown-value').textContent = d;
                segments[1].querySelector('.countdown-value').textContent = h;
            }
        });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.gamerDashboard = {
        profile: new GamerProfileManager(),
        tabs: new DashboardTabManager(),
        competitions: new CompetitionManager()
    };
});