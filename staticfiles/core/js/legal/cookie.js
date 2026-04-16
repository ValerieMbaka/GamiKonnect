document.addEventListener('DOMContentLoaded', function() {
    initializeCookiePolicy();
});

function initializeCookiePolicy() {
    animateCookieBadges();
    initializeCookiePreferenceDemo();
}

function animateCookieBadges() {
    const badges = document.querySelectorAll('.cookie-type-badge');
    badges.forEach((badge, index) => {
        badge.style.animationDelay = `${index * 0.1}s`;
        badge.classList.add('animate__animated', 'animate__fadeInUp');
    });
}

function initializeCookiePreferenceDemo() {
    const preferenceButtons = document.querySelectorAll('.cookie-preference-btn');
    preferenceButtons.forEach(button => {
        button.addEventListener('click', function() {
            const preference = this.getAttribute('data-preference');
            simulatePreferenceUpdate(preference);
        });
    });
}

function simulatePreferenceUpdate(preference) {
    const message = `Cookie preferences updated to: ${preference}`;
    window.toastManager.success('Preferences Saved', message);
    updatePreferenceUI(preference);
}

function updatePreferenceUI(preference) {
    const indicators = document.querySelectorAll('.preference-indicator');
    indicators.forEach(indicator => {
        indicator.classList.remove('active');
        if (indicator.getAttribute('data-preference') === preference) {
            indicator.classList.add('active');
        }
    });
}