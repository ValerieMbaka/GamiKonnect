class AdminThemeManager {
    constructor() {
        this.toggleBtn = document.getElementById('darkModeToggle');
        this.htmlElement = document.documentElement;
        this.init();
    }

    init() {
        if (!this.toggleBtn) return;

        const savedTheme = localStorage.getItem('adminTheme');
        if (savedTheme === 'dark') {
            this.htmlElement.setAttribute('data-theme', 'dark');
        }

        this.toggleBtn.addEventListener('click', () => this.toggleTheme());
    }

    toggleTheme() {
        const isDark = this.htmlElement.getAttribute('data-theme') === 'dark';
        if (isDark) {
            this.htmlElement.removeAttribute('data-theme');
            localStorage.setItem('adminTheme', 'light');
        } else {
            this.htmlElement.setAttribute('data-theme', 'dark');
            localStorage.setItem('adminTheme', 'dark');
        }
    }
}

class AdminTooltipManager {
    constructor() {
        this.tooltipEl = document.createElement('div');
        this.tooltipEl.className = 'custom-tooltip';
        document.body.appendChild(this.tooltipEl);
        this.bindEvents();
    }

    bindEvents() {
        document.addEventListener('mouseover', (e) => {
            const target = e.target.closest('[data-tooltip]');
            if (!target) return;

            // Only show sidebar tooltips if the sidebar is actually collapsed
            const isSidebarLink = target.classList.contains('nav-link');
            const sidebarIsCollapsed = document.querySelector('.admin-sidebar').classList.contains('collapsed');
            if (isSidebarLink && !sidebarIsCollapsed) return;

            this.showTooltip(target);
        });

        document.addEventListener('mouseout', (e) => {
            if (e.target.closest('[data-tooltip]')) {
                this.hideTooltip();
            }
        });
    }

    showTooltip(element) {
        const text = element.getAttribute('data-tooltip');
        if (!text) return;

        this.tooltipEl.textContent = text;
        this.tooltipEl.classList.add('show');

        const rect = element.getBoundingClientRect();
        let top = rect.bottom + 10;
        let left = rect.left + (rect.width / 2);

        // If it's a sidebar icon, show tooltip to the right instead of below
        if (element.closest('.admin-sidebar')) {
            top = rect.top + (rect.height / 2);
            left = rect.right + 10;
            this.tooltipEl.style.transform = 'translate(0, -50%)';
        } else {
            this.tooltipEl.style.transform = 'translate(-50%, 0)';
        }

        this.tooltipEl.style.top = `${top}px`;
        this.tooltipEl.style.left = `${left}px`;
    }

    hideTooltip() {
        this.tooltipEl.classList.remove('show');
    }
}

class AdminDropdownManager {
    constructor() {
        this.dropdowns = document.querySelectorAll('.nav-dropdown');
        this.init();
    }

    init() {
        this.dropdowns.forEach(dropdown => {
            const btn = dropdown.querySelector('button');
            
            // Hover to open
            dropdown.addEventListener('mouseenter', () => {
                dropdown.classList.add('show');
            });

            // Mouse leave to disappear
            dropdown.addEventListener('mouseleave', () => {
                dropdown.classList.remove('show');
            });

            // Prevent click-conflict on desktop
            if (btn) {
                btn.addEventListener('click', (e) => {
                    // If the device supports hovering (desktop), intercept the click
                    if (window.matchMedia('(pointer: fine)').matches) {
                        e.stopPropagation();
                        dropdown.classList.add('show');
                    }
                }, true); // Use the capture phase to trigger before base_sidebar
            }
        });
    }
}

// Initialize all features when the DOM is fully loaded
document.addEventListener('DOMContentLoaded', () => {
    new AdminThemeManager();
    new AdminTooltipManager();
    new AdminDropdownManager();
});