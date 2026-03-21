class LegalUtils {
    static init() {
        this.initializeTooltips();
        this.initializePopovers();
        this.setActiveNavigation();
        this.setupAnimations();
    }

    static smoothScrollTo(target, offset = 100) {
        const element = document.querySelector(target);
        if (element) {
            const elementPosition = element.getBoundingClientRect().top;
            const offsetPosition = elementPosition + window.pageYOffset - offset;
            window.scrollTo({ top: offsetPosition, behavior: 'smooth' });
        }
    }

    static isInViewport(element) {
        const rect = element.getBoundingClientRect();
        return (
            rect.top >= 0 && rect.left >= 0 &&
            rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
            rect.right <= (window.innerWidth || document.documentElement.clientWidth)
        );
    }

    static setButtonLoading(button, isLoading) {
        if (isLoading) {
            button.setAttribute('data-original-text', button.innerHTML);
            button.disabled = true;
            button.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Loading...';
        } else {
            button.disabled = false;
            button.innerHTML = button.getAttribute('data-original-text') || button.textContent;
        }
    }

    static formatDate(date) {
        return new Date(date).toLocaleDateString('en-US', {
            year: 'numeric', month: 'long', day: 'numeric'
        });
    }

    static debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    static initializeTooltips() {
        if (typeof bootstrap !== 'undefined') {
            const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
            tooltipTriggerList.map(el => new bootstrap.Tooltip(el));
        }
    }

    static initializePopovers() {
        if (typeof bootstrap !== 'undefined') {
            const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
            popoverTriggerList.map(el => new bootstrap.Popover(el));
        }
    }

    static setActiveNavigation() {
        const currentPath = window.location.pathname;
        document.querySelectorAll('.nav-link').forEach(link => {
            if (link.getAttribute('href') === currentPath) link.classList.add('active');
            else link.classList.remove('active');
        });
    }

    static setupAnimations() {
        document.querySelectorAll('[data-animate]').forEach((element, index) => {
            setTimeout(() => {
                element.classList.add('animate__animated', `animate__${element.getAttribute('data-animate')}`);
            }, index * 100);
        });
    }
}

document.addEventListener('DOMContentLoaded', () => LegalUtils.init());