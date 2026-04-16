class ErrorPageManager {
    constructor() {
        this.init();
    }

    init() {
        this.addParticles();
        this.addTypewriterEffect();
        this.addButtonAnimations();
        this.addAutoRefresh();
        this.addSearchFunctionality();
        this.setupActionButtons();
        this.setupNetworkMonitoring();
    }

    addParticles() {
        const container = document.querySelector('.error-container');
        if (!container) return;

        for (let i = 0; i < 15; i++) {
            const particle = document.createElement('div');
            particle.className = 'error-particle';
            
            const size = Math.random() * 6 + 2;
            const posX = Math.random() * 100;
            const delay = Math.random() * 5;
            const duration = Math.random() * 10 + 10;
            
            particle.style.cssText = `
                position: absolute;
                width: ${size}px;
                height: ${size}px;
                background: var(--primary);
                border-radius: 50%;
                left: ${posX}%;
                top: -10px;
                opacity: ${Math.random() * 0.3 + 0.1};
                animation: floatParticle ${duration}s linear ${delay}s infinite;
            `;

            container.appendChild(particle);

            setTimeout(() => {
                if (particle.parentNode) particle.remove();
            }, (duration + delay) * 1000);
        }
    }

    addTypewriterEffect() {
        const errorMessage = document.querySelector('.error-message');
        if (!errorMessage) return;

        const text = errorMessage.textContent;
        errorMessage.textContent = '';
        
        let i = 0;
        const typeWriter = () => {
            if (i < text.length) {
                errorMessage.textContent += text.charAt(i);
                i++;
                setTimeout(typeWriter, 50);
            }
        };

        setTimeout(typeWriter, 1000);
    }

    addButtonAnimations() {
        document.querySelectorAll('.error-actions .btn').forEach(button => {
            button.addEventListener('mouseenter', (e) => {
                e.currentTarget.style.transform = 'translateY(-3px) scale(1.05)';
            });
            
            button.addEventListener('mouseleave', (e) => {
                e.currentTarget.style.transform = 'translateY(0) scale(1)';
            });
            
            button.addEventListener('click', (e) => {
                e.currentTarget.style.transform = 'scale(0.95)';
                setTimeout(() => e.currentTarget.style.transform = 'scale(1)', 150);
            });
        });
    }

    addAutoRefresh() {
        const maintenancePage = document.querySelector('.maintenance-info');
        if (maintenancePage) {
            setInterval(() => window.location.reload(), 30000);
        }
    }

    addSearchFunctionality() {
        const searchForm = document.querySelector('.search-form');
        if (!searchForm) return;

        searchForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const searchInput = searchForm.querySelector('input[name="q"]');
            const query = searchInput.value.trim();
            
            if (query) {
                const submitBtn = searchForm.querySelector('.search-btn');
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
                submitBtn.disabled = true;
                
                setTimeout(() => {
                    window.location.href = `${searchForm.action}?q=${encodeURIComponent(query)}`;
                }, 1000);
            }
        });
    }

    setupActionButtons() {
        document.querySelectorAll('.action-go-back').forEach(btn => {
            btn.addEventListener('click', () => history.back());
        });

        document.querySelectorAll('.action-reload').forEach(btn => {
            btn.addEventListener('click', () => window.location.reload());
        });
    }

    setupNetworkMonitoring() {
        window.addEventListener('online', () => {
            if (window.toastManager) {
                window.toastManager.success('Online', 'Connection restored');
            }
        });

        window.addEventListener('offline', () => {
            if (window.toastManager) {
                window.toastManager.error('Offline', 'You are currently offline');
            }
        });

        if ('serviceWorker' in navigator) {
            window.addEventListener('load', () => {
                navigator.serviceWorker.register('/sw.js')
                    .catch(err => console.log('ServiceWorker registration failed: ', err));
            });
        }
    }
}

document.addEventListener('DOMContentLoaded', () => new ErrorPageManager());