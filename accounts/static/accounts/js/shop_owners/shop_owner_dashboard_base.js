/**
 * Manages custom tooltip behavior for the Shop Owner Dashboard.
 * Utilizes ES6 class structure for clean encapsulation.
 */
class DashboardTooltipManager {
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
            const sidebar = document.querySelector('.dashboard-sidebar');
            
            // Safety check in case the sidebar isn't in the DOM yet
            if (isSidebarLink && sidebar && !sidebar.classList.contains('collapsed')) {
                return;
            }

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
        if (element.closest('.dashboard-sidebar')) {
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

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', () => {
    new DashboardTooltipManager();
});