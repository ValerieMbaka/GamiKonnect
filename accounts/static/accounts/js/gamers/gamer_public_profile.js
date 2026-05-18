class PublicProfileManager {
    constructor() {
        this.init();
    }

    init() {
        this.initializeScrollLinks();
        this.applyLevelBadgeColor();
        this.initializeIntersectionObserver();
    }

    applyLevelBadgeColor() {
        document.querySelectorAll('.profile-level-badge[data-level-color]').forEach((badge) => {
            const levelColor = badge.getAttribute('data-level-color');
            if (levelColor) {
                badge.style.setProperty('--level-badge-color', levelColor);
            }
        });
    }

    initializeScrollLinks() {
        document.querySelectorAll('a[href^="#"]').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const targetId = link.getAttribute('href');
                if (targetId === '#') return;
                
                const target = document.querySelector(targetId);
                if (target) {
                    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            });
        });
    }

    initializeIntersectionObserver() {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('is-visible');
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.1, rootMargin: '0px 0px -50px 0px' });
        
        document.querySelectorAll('.profile-card, .featured-game-card, .achievement-item').forEach(el => {
            el.classList.add('profile-reveal-target');
            observer.observe(el);
        });
    }
}

document.addEventListener('DOMContentLoaded', () => new PublicProfileManager());