class ErrorPages {
    constructor() {
        this.init();
    }

    init() {
        this.addParticles();
        this.addTypewriterEffect();
        this.addButtonAnimations();
        this.addAutoRefresh();
        this.addSearchFunctionality();
    }

    // Add floating particles animation
    addParticles() {
        const container = document.querySelector('.error-container');
        if (!container) return;

        const particlesCount = 15;
        
        for (let i = 0; i < particlesCount; i++) {
            this.createParticle(container);
        }
    }

    createParticle(container) {
        const particle = document.createElement('div');
        particle.className = 'error-particle';
        
        // Random properties
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

        // Add CSS for animation if not exists
        if (!document.querySelector('#particle-animation')) {
            const style = document.createElement('style');
            style.id = 'particle-animation';
            style.textContent = `
                @keyframes floatParticle {
                    0% {
                        transform: translateY(0) rotate(0deg);
                        opacity: 0;
                    }
                    10% {
                        opacity: ${Math.random() * 0.3 + 0.1};
                    }
                    90% {
                        opacity: ${Math.random() * 0.3 + 0.1};
                    }
                    100% {
                        transform: translateY(100vh) rotate(360deg);
                        opacity: 0;
                    }
                }
            `;
            document.head.appendChild(style);
        }

        container.appendChild(particle);

        // Remove particle after animation
        setTimeout(() => {
            if (particle.parentNode) {
                particle.parentNode.removeChild(particle);
            }
        }, (duration + delay) * 1000);
    }

    // Add typewriter effect to error messages
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

        // Start typing after a short delay
        setTimeout(typeWriter, 1000);
    }

    // Add interactive button animations
    addButtonAnimations() {
        const buttons = document.querySelectorAll('.error-actions .btn');
        
        buttons.forEach(button => {
            button.addEventListener('mouseenter', function() {
                this.style.transform = 'translateY(-3px) scale(1.05)';
            });
            
            button.addEventListener('mouseleave', function() {
                this.style.transform = 'translateY(0) scale(1)';
            });
            
            button.addEventListener('click', function() {
                this.style.transform = 'scale(0.95)';
                setTimeout(() => {
                    this.style.transform = 'scale(1)';
                }, 150);
            });
        });
    }

    // Auto-refresh for maintenance pages
    addAutoRefresh() {
        const maintenancePage = document.querySelector('.maintenance-info');
        if (maintenancePage) {
            // Refresh every 30 seconds
            setInterval(() => {
                window.location.reload();
            }, 30000);
        }
    }

    // Enhanced search functionality
    addSearchFunctionality() {
        const searchForm = document.querySelector('.search-form');
        if (!searchForm) return;

        searchForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const searchInput = searchForm.querySelector('input[name="q"]');
            const query = searchInput.value.trim();
            
            if (query) {
                // Add loading state
                const submitBtn = searchForm.querySelector('.search-btn');
                const originalHTML = submitBtn.innerHTML;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
                submitBtn.disabled = true;
                
                // Simulate search delay
                setTimeout(() => {
                    window.location.href = `${searchForm.action}?q=${encodeURIComponent(query)}`;
                }, 1000);
            }
        });
    }

    // Utility function to check if element is in viewport
    isInViewport(element) {
        const rect = element.getBoundingClientRect();
        return (
            rect.top >= 0 &&
            rect.left >= 0 &&
            rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
            rect.right <= (window.innerWidth || document.documentElement.clientWidth)
        );
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new ErrorPages();
});

// Add service worker check for offline support
if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        navigator.serviceWorker.register('/sw.js').then(function(registration) {
            console.log('ServiceWorker registration successful');
        }, function(err) {
            console.log('ServiceWorker registration failed: ', err);
        });
    });
}

// Network status detection
window.addEventListener('online', function() {
    const statusElement = document.createElement('div');
    statusElement.className = 'network-status online';
    statusElement.innerHTML = '<i class="fas fa-wifi"></i> Connection restored';
    document.body.appendChild(statusElement);
    
    setTimeout(() => {
        statusElement.remove();
    }, 3000);
});

window.addEventListener('offline', function() {
    const statusElement = document.createElement('div');
    statusElement.className = 'network-status offline';
    statusElement.innerHTML = '<i class="fas fa-wifi-slash"></i> You are offline';
    document.body.appendChild(statusElement);
});