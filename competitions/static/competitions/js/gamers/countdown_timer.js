class CountdownTimer {
    constructor() {
        this.timers = new Map();
        this.init();
    }

    init() {
        console.log('CountdownTimer initialized');
        this.startAllTimers();
    }

    startAllTimers() {
        const countdownElements = document.querySelectorAll('.countdown-timer');
        
        console.log(`Starting ${countdownElements.length} countdown timers`);
        
        countdownElements.forEach((element, index) => {
            const startDate = new Date(element.dataset.startDate);
            if (this.isValidDate(startDate)) {
                this.startTimer(element, startDate, `timer-${index}`);
            } else {
                console.warn('Invalid start date for countdown timer:', element.dataset.startDate);
                element.style.display = 'none';
            }
        });
    }

    isValidDate(date) {
        return date instanceof Date && !isNaN(date);
    }

    startTimer(element, startDate, timerId) {
        const updateTimer = () => {
            const now = new Date();
            const timeDiff = startDate - now;

            if (timeDiff <= 0) {
                // Competition has started, remove countdown and update status
                this.handleCountdownComplete(element);
                this.timers.delete(timerId);
                return;
            }

            const days = Math.floor(timeDiff / (1000 * 60 * 60 * 24));
            const hours = Math.floor((timeDiff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            const minutes = Math.floor((timeDiff % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((timeDiff % (1000 * 60)) / 1000);

            this.updateDisplay(element, days, hours, minutes, seconds);
            
            // Update urgency styling
            this.updateUrgencyStyling(element, days, hours, minutes);
        };

        // Update immediately and then every second for smooth countdown
        updateTimer();
        const intervalId = setInterval(updateTimer, 1000);
        
        this.timers.set(timerId, intervalId);
    }

    updateDisplay(element, days, hours, minutes, seconds) {
        const daysElement = element.querySelector('.countdown-days');
        const hoursElement = element.querySelector('.countdown-hours');
        const minutesElement = element.querySelector('.countdown-minutes');
        const secondsElement = element.querySelector('.countdown-seconds');

        if (daysElement) daysElement.textContent = this.formatTime(days);
        if (hoursElement) hoursElement.textContent = this.formatTime(hours);
        if (minutesElement) minutesElement.textContent = this.formatTime(minutes);
        if (secondsElement) secondsElement.textContent = this.formatTime(seconds);
    }

    formatTime(value) {
        return value < 10 ? `0${value}` : value.toString();
    }

    updateUrgencyStyling(element, days, hours, minutes) {
        // Remove all urgency classes first
        element.classList.remove('urgent', 'very-urgent', 'critical');
        
        // Add appropriate urgency class based on time remaining
        if (days === 0) {
            if (hours < 1) {
                element.classList.add('critical');
            } else if (hours < 6) {
                element.classList.add('very-urgent');
            } else {
                element.classList.add('urgent');
            }
        }
    }

    handleCountdownComplete(element) {
        console.log('Countdown completed for competition');
        
        // Hide the countdown timer
        element.style.display = 'none';
        
        // Update the time status text to reflect that competition has started
        const card = element.closest('.competition-card');
        if (card) {
            const timeStatusElement = card.querySelector('.time-status');
            if (timeStatusElement) {
                timeStatusElement.textContent = 'Starting now...';
                timeStatusElement.classList.add('starting-now');
            }
            
            // Update card status if needed
            this.updateCardStatus(card, 'ongoing');
        }
        
        // Trigger a refresh of competition data
        if (window.competitionsManager) {
            setTimeout(() => {
                window.competitionsManager.refreshCompetitions();
            }, 2000); // Refresh after 2 seconds
        }
    }

    updateCardStatus(card, newStatus) {
        // Update the data-status attribute
        card.dataset.status = newStatus;
        
        // Update the status badge
        const statusBadge = card.querySelector('.competition-status');
        if (statusBadge) {
            // Remove all status classes
            statusBadge.classList.remove('upcoming', 'ongoing', 'completed');
            // Add new status class
            statusBadge.classList.add(newStatus);
            
            // Update status text and icon
            const statusIcon = statusBadge.querySelector('i');
            const statusText = statusBadge.querySelector('span') || statusBadge;
            
            if (newStatus === 'ongoing') {
                if (statusIcon) statusIcon.className = 'fas fa-play-circle';
                if (statusText.textContent) statusText.textContent = statusText.textContent.replace('Upcoming', 'Ongoing');
            }
        }
    }

    // Add a new countdown timer dynamically
    addTimer(element, startDate) {
        const timerId = `timer-dynamic-${Date.now()}`;
        if (this.isValidDate(startDate)) {
            this.startTimer(element, startDate, timerId);
        }
    }

    // Stop a specific timer
    stopTimer(timerId) {
        const intervalId = this.timers.get(timerId);
        if (intervalId) {
            clearInterval(intervalId);
            this.timers.delete(timerId);
        }
    }

    destroy() {
        // Clear all intervals
        this.timers.forEach((intervalId, timerId) => {
            clearInterval(intervalId);
            this.timers.delete(timerId);
        });
        
        console.log('CountdownTimer destroyed');
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing CountdownTimer');
    window.countdownTimer = new CountdownTimer();
});

// Make CountdownTimer available globally
window.CountdownTimer = CountdownTimer;