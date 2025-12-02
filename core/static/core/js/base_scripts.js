// Scroll to Top Button
class ScrollToTop {
    constructor() {
        this.backToTop = document.getElementById('backToTop');
        if (this.backToTop) this.init();
    }

    init() {
        window.addEventListener('scroll', this.toggleButton.bind(this));
        this.backToTop.addEventListener('click', this.scrollToTop.bind(this));
    }

    toggleButton() {
        if (window.pageYOffset > 300) {
            this.backToTop.classList.add('active');
        } else {
            this.backToTop.classList.remove('active');
        }
    }

    scrollToTop(e) {
        e.preventDefault();
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    }
}

// Smooth Scrolling for Anchor Links
class SmoothScroller {
    constructor() {
        this.links = document.querySelectorAll('a[href^="#"]');
        if (this.links.length) this.init();
    }

    init() {
        this.links.forEach(link => {
            link.addEventListener('click', this.handleClick.bind(this));
        });
    }

    handleClick(e) {
        const targetId = this.getAttribute('href');
        if (targetId === '#') return;
        
        const targetElement = document.querySelector(targetId);
        if (targetElement) {
            e.preventDefault();
            window.scrollTo({
                top: targetElement.offsetTop - 80,
                behavior: 'smooth'
            });
        }
    }
}

// Scroll-based Animations
class ScrollAnimator {
    constructor() {
        this.elements = document.querySelectorAll('.fade-in-up');
        if (this.elements.length) this.init();
    }

    init() {
        window.addEventListener('scroll', this.checkElements.bind(this));
        this.checkElements(); // Check on load
    }

    checkElements() {
        const windowHeight = window.innerHeight;
        
        this.elements.forEach(element => {
            const elementPosition = element.getBoundingClientRect().top;
            
            if (elementPosition < windowHeight - 100) {
                element.classList.add('animated');
            }
        });
    }
}

// Initialize tooltips
var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl);
});

// Theme Management
class ThemeManager {
    constructor() {
        this.themeToggle = document.getElementById('themeToggle');
        this.lightIcon = document.getElementById('lightIcon');
        this.darkIcon = document.getElementById('darkIcon');
        this.html = document.documentElement;
        
        if (this.themeToggle) this.init();
    }

    init() {
        const savedTheme = localStorage.getItem('theme') || 'light';
        this.setTheme(savedTheme);
        this.themeToggle.addEventListener('click', () => this.toggleTheme());
    }

    setTheme(theme) {
        this.html.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
        this.updateIcons(theme);
    }

    toggleTheme() {
        const currentTheme = this.html.getAttribute('data-theme') || 'light';
        this.setTheme(currentTheme === 'dark' ? 'light' : 'dark');
    }

    updateIcons(theme) {
        if (!this.lightIcon || !this.darkIcon) return;
        
        const isDark = theme === 'dark';
        this.lightIcon.style.display = isDark ? 'none' : 'inline';
        this.darkIcon.style.display = isDark ? 'inline' : 'none';
    }
}

// Navigation Management
class NavigationManager {
    constructor() {
        this.navLinks = document.querySelectorAll('nav a');
        if (this.navLinks.length) this.init();
    }

    init() {
        this.updateActiveNavLink();
        this.addClickHandlers();
        window.addEventListener('scroll', () => this.updateActiveNavLink());
    }

    updateActiveNavLink() {
        const sections = document.querySelectorAll('section[id]');
        let current = '';

        sections.forEach(section => {
            const sectionTop = section.offsetTop;
            if (pageYOffset >= sectionTop - 100) {
                current = section.getAttribute('id');
            }
        });

        this.navLinks.forEach(link => {
            const href = link.getAttribute('href') || '';

            // Only auto-toggle active state for same-page hash links.
            if (href.startsWith('#')) {
                link.classList.toggle('active', href === `#${current}`);
            }
        });
    }

    addClickHandlers() {
        this.navLinks.forEach(link => {
            link.addEventListener('click', (event) => {
                const href = link.getAttribute('href') || '';

                // For full-page navigations let the browser handle navigation normally.
                if (!href.startsWith('#')) {
                    return;
                }

                // For on-page hash navigation, manage the active state manually.
                this.navLinks.forEach(l => l.classList.remove('active'));
                link.classList.add('active');
            });
        });
    }
}

// Enhanced Link States
class LinkStateManager {
    constructor() {
        this.links = document.querySelectorAll('a, button, [role="button"]');
        if (this.links.length) this.init();
    }

    init() {
        this.addInteractionStates();
    }

    addInteractionStates() {
        this.links.forEach(element => {
            // Mouse interactions
            element.addEventListener('mousedown', () => element.classList.add('active'));
            element.addEventListener('mouseup', () => element.classList.remove('active'));
            element.addEventListener('mouseleave', () => element.classList.remove('active'));
            
            // Keyboard navigation
            element.addEventListener('focus', (e) => {
                if (e.relatedTarget?.matches('a, button, [role="button"]')) {
                    element.classList.add('keyboard-focus');
                }
            });
            
            element.addEventListener('blur', () => {
                element.classList.remove('keyboard-focus', 'active');
            });
        });
    }
}

// Django Messages Manager 
class DjangoMessagesManager {
    constructor() {
        this.init();
    }
    
    init() {
        try {
            const messagesElement = document.getElementById('django-messages');
            const authElement = document.getElementById('user-auth-status');
            
            if (messagesElement && authElement) {
                const djangoMessages = JSON.parse(messagesElement.textContent);
                const authStatus = JSON.parse(authElement.textContent);
                
                this.handleDjangoMessages(djangoMessages);
                this.handleAuthStatus(authStatus);
            }
        } catch (error) {
            console.error('Error processing Django messages:', error);
        }
    }
    
    handleDjangoMessages(messages) {
        if (messages && messages.length > 0) {
            messages.forEach(message => {
                if (message && message.text) {
                    // Check if showToast function exists
                    if (typeof showToast === 'function') {
                        showToast(message.text, message.tags || 'info');
                    } else {
                        console.log('Toast message:', message.text);
                    }
                }
            });
        }
    }
    
    handleAuthStatus(authStatus) {
        // Clear profile completion data if user is not authenticated
        if (!authStatus.authenticated) {
            localStorage.removeItem('profileCompleted');
            localStorage.removeItem('updatedProfile');
        }
    }
}

// Main Initialization
document.addEventListener('DOMContentLoaded', function() {
    // Initialize core components
    const components = [
        new ScrollToTop(),
        new SmoothScroller(),
        new ScrollAnimator(),
        new ThemeManager(),
        new NavigationManager(),
        new DjangoMessagesManager(),
        new LinkStateManager()
    ];
    
    // Expose components to window for debugging
    window.appComponents = {
        scrollToTop: components[0],
        smoothScroller: components[1],
        scrollAnimator: components[2],
        themeManager: components[3],
        navigationManager: components[4],
        messagesManager: components[5],
        linkStateManager: components[6]
    };
    
    console.log('GameHub Base Scripts Initialized Successfully!');
});