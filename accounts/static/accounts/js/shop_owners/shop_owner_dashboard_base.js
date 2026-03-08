document.addEventListener('DOMContentLoaded', function () {
    // Dark Mode Toggle
    class DarkMode {
        constructor() {
            this.toggleButton = document.getElementById('darkModeToggle');
            this.body = document.body;
            if (this.toggleButton) this.init();
        }

        init() {
            this.loadTheme();
            this.toggleButton.addEventListener('click', () => this.toggle());
        }

        loadTheme() {
            const savedTheme = localStorage.getItem('gk-dashboard-theme') || 'light';
            document.documentElement.setAttribute('data-theme', savedTheme);
            this.body.dataset.dashboardTheme = savedTheme;
        }

        toggle() {
            const current = document.documentElement.getAttribute('data-theme');
            const newTheme = current === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', newTheme);
            this.body.dataset.dashboardTheme = newTheme;
            localStorage.setItem('gk-dashboard-theme', newTheme);
        }
    }

    new DarkMode();

    // Tooltip Manager
    class TooltipManager {
        constructor() {
            this.tooltips = [];
            this.init();
        }

        init() {
            this.createTooltips();
            this.setupEventListeners();
        }

        createTooltips() {
            document.querySelectorAll('[data-tooltip]:not(.tooltip-initialized)').forEach(item => {
                item.classList.add('tooltip-initialized');

                const tooltip = document.createElement('div');
                tooltip.className = 'custom-tooltip';
                tooltip.textContent = item.getAttribute('data-tooltip');
                document.body.appendChild(tooltip);

                this.tooltips.push({ element: item, tooltip });
            });
        }

        setupEventListeners() {
            this.tooltips.forEach(({ element, tooltip }) => {
                const positionTooltip = () => {
                    const rect = element.getBoundingClientRect();
                    tooltip.style.left = `${rect.left + (rect.width / 2)}px`;
                    tooltip.style.top = `${rect.top - 10}px`;
                };

                element.addEventListener('mouseenter', () => {
                    positionTooltip();
                    tooltip.style.display = 'block';
                });

                element.addEventListener('mouseleave', () => {
                    tooltip.style.display = 'none';
                });

                window.addEventListener('resize', positionTooltip);
            });
        }
    }

    // Sidebar Manager
    class SidebarManager {
        constructor() {
            this.toggleButton = document.querySelector('.sidebar-toggle-btn');
            this.sidebar = document.querySelector('.dashboard-sidebar');
            this.topNav = document.querySelector('.top-nav');
            this.dashboardContent = document.querySelector('.dashboard-content');
            this.isTransitioning = false;
            
            if (this.toggleButton && this.sidebar) this.init();
        }

        init() {
            this.applyStateImmediately();
            this.setupEventListeners();
            this.setupActiveStateManagement();
            this.setupTransitionListeners();
        }

        applyStateImmediately() {
            const isCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
            
            if (isCollapsed && window.innerWidth > 992) {
                this.sidebar.style.transition = 'none';
                this.topNav.style.transition = 'none';
                this.dashboardContent.style.transition = 'none';
                
                this.sidebar.classList.add('collapsed');
                this.topNav.classList.add('sidebar-collapsed');
                this.dashboardContent.classList.add('sidebar-collapsed');
                
                setTimeout(() => {
                    this.sidebar.style.transition = '';
                    this.topNav.style.transition = '';
                    this.dashboardContent.style.transition = '';
                }, 50);
            }
        }

        setupEventListeners() {
            this.toggleButton.addEventListener('click', () => this.toggle());
        }

        setupActiveStateManagement() {
            this.setInitialActiveState();
        }

        setupTransitionListeners() {
            this.sidebar.addEventListener('transitionstart', (e) => {
                if (e.propertyName === 'width') {
                    this.isTransitioning = true;
                }
            });

            this.sidebar.addEventListener('transitionend', (e) => {
                if (e.propertyName === 'width') {
                    this.isTransitioning = false;
                }
            });
        }

        setInitialActiveState() {
            const currentPath = window.location.pathname;
            const navLinks = document.querySelectorAll('.nav-link[href]');
            
            navLinks.forEach(link => {
                const href = link.getAttribute('href');
                if (href && href !== '#' && currentPath.includes(new URL(href, window.location.origin).pathname)) {
                    link.classList.add('active');
                }
            });
        }

        toggle() {
            if (this.isTransitioning) return;

            if (window.innerWidth <= 992) {
                this.sidebar.classList.toggle('open');
            } else {
                this.sidebar.classList.toggle('collapsed');
                this.topNav.classList.toggle('sidebar-collapsed');
                this.dashboardContent.classList.toggle('sidebar-collapsed');
                localStorage.setItem('sidebarCollapsed', this.sidebar.classList.contains('collapsed'));
            }
        }
    }

    // Initialize managers
    window.tooltipManager = new TooltipManager();
    new SidebarManager();

    // Close sidebar when clicking outside on mobile
    document.addEventListener('click', (event) => {
        const sidebar = document.querySelector('.dashboard-sidebar');
        const toggleBtn = document.querySelector('.sidebar-toggle-btn');
        
        if (window.innerWidth <= 992 && 
            sidebar.classList.contains('open') && 
            !sidebar.contains(event.target) && 
            !toggleBtn.contains(event.target)) {
            sidebar.classList.remove('open');
        }
    });
});

window.showDashboardToast = function showDashboardToast(message, type = 'info') {
    if (window.Toast) {
        window.Toast.show({
            type,
            title: type.charAt(0).toUpperCase() + type.slice(1),
            message,
        });
        return;
    }
    alert(message);
};