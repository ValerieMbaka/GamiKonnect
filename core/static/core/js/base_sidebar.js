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
            const savedTheme = localStorage.getItem('gamikonnect_theme') || 'light';
            document.documentElement.setAttribute('data-theme', savedTheme);
            if (this.body) this.body.dataset.dashboardTheme = savedTheme;
        }

        toggle() {
            const current = document.documentElement.getAttribute('data-theme');
            const newTheme = current === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', newTheme);
            if (this.body) this.body.dataset.dashboardTheme = newTheme;
            localStorage.setItem('gamikonnect_theme', newTheme);
        }
    }
    
    // Dropdown Manager
    class DropdownManager {
        constructor() {
            this.dropdowns = document.querySelectorAll('.nav-dropdown');
            if (this.dropdowns.length > 0) this.init();
        }

        init() {
            this.dropdowns.forEach(dropdown => {
                const btn = dropdown.querySelector('button');
                if (btn) {
                    btn.addEventListener('click', (e) => {
                        e.preventDefault();
                        e.stopPropagation(); // Stop click from immediately closing it
                        
                        // Close any other open dropdowns first
                        this.dropdowns.forEach(d => {
                            if (d !== dropdown) d.classList.remove('show');
                        });
                        
                        // Toggle the one we just clicked
                        dropdown.classList.toggle('show');
                    });
                }
            });

            // Close dropdowns if the user clicks anywhere else on the page
            document.addEventListener('click', (e) => {
                if (!e.target.closest('.nav-dropdown')) {
                    this.dropdowns.forEach(dropdown => dropdown.classList.remove('show'));
                }
            });
        }
    }

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
            this.overlay = document.querySelector('.sidebar-overlay');
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
            
            // Only apply collapsed state on desktop sizes
            if (isCollapsed && window.innerWidth > 992) {
                this.sidebar.style.transition = 'none';
                if (this.topNav) this.topNav.style.transition = 'none';
                if (this.dashboardContent) this.dashboardContent.style.transition = 'none';
                
                this.sidebar.classList.add('collapsed');
                if (this.topNav) this.topNav.classList.add('sidebar-collapsed');
                if (this.dashboardContent) this.dashboardContent.classList.add('sidebar-collapsed');
                
                setTimeout(() => {
                    this.sidebar.style.transition = '';
                    if (this.topNav) this.topNav.style.transition = '';
                    if (this.dashboardContent) this.dashboardContent.style.transition = '';
                }, 50);
            }
            this.updateToggleButtonIcon();
        }

        setupEventListeners() {
            this.toggleButton.addEventListener('click', () => this.toggle());
            this.sidebar.addEventListener('transitionend', () => this.updateToggleButtonIcon());

            // Close sidebar when clicking the dark overlay
            if (this.overlay) {
                this.overlay.addEventListener('click', () => this.closeMobileSidebar());
            }

            // Fallback: Close sidebar when clicking outside on mobile
            document.addEventListener('click', (event) => {
                if (window.innerWidth <= 992 &&
                    this.sidebar.classList.contains('sidebar-open') &&
                    !this.sidebar.contains(event.target) &&
                    !this.toggleButton.contains(event.target)) {
                    this.closeMobileSidebar();
                }
            });

            // Handle window resizing to switch between mobile and desktop states smoothly
            window.addEventListener('resize', () => this.handleResize());
        }

        setupActiveStateManagement() {
            const currentPath = window.location.pathname;
            const navLinks = document.querySelectorAll('.nav-link[href]');
            
            navLinks.forEach(link => {
                link.classList.remove('active');
                const href = link.getAttribute('href');
                if (href && href !== '#' && currentPath.includes(new URL(href, window.location.origin).pathname)) {
                    link.classList.add('active');
                }
            });

            document.addEventListener('click', (e) => {
                const navLink = e.target.closest('.nav-link');
                if (navLink && !navLink.classList.contains('logout-link') && !navLink.getAttribute('href').startsWith('http')) {
                    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
                    navLink.classList.add('active');
                }
            });
        }

        setupTransitionListeners() {
            this.sidebar.addEventListener('transitionstart', (e) => {
                if (e.propertyName === 'width' || e.propertyName === 'transform') {
                    this.isTransitioning = true;
                    this.sidebar.style.pointerEvents = 'none';
                }
            });

            this.sidebar.addEventListener('transitionend', (e) => {
                if (e.propertyName === 'width' || e.propertyName === 'transform') {
                    this.isTransitioning = false;
                    this.sidebar.style.pointerEvents = 'auto';
                    if (window.tooltipManager) window.tooltipManager.createTooltips();
                }
            });
        }

        updateToggleButtonIcon() {
            const icon = this.toggleButton.querySelector('i');
            if(icon) {
                if (this.sidebar.classList.contains('collapsed')) {
                    icon.className = 'fas fa-bars';
                    this.toggleButton.setAttribute('aria-label', 'Expand sidebar');
                } else {
                    icon.className = 'fas fa-bars';
                    this.toggleButton.setAttribute('aria-label', 'Collapse sidebar');
                }
            }
        }

        toggle() {
            if (this.isTransitioning) return;

            if (window.innerWidth <= 992) {
                // Slide sidebar in and show dark overlay
                this.sidebar.classList.toggle('sidebar-open');
                if (this.overlay) this.overlay.classList.toggle('active');
            } else {
                // Shrink sidebar to icons
                this.sidebar.classList.toggle('collapsed');
                if (this.topNav) this.topNav.classList.toggle('sidebar-collapsed');
                if (this.dashboardContent) this.dashboardContent.classList.toggle('sidebar-collapsed');
                
                // Remember the user's preference
                localStorage.setItem('sidebarCollapsed', this.sidebar.classList.contains('collapsed'));
            }
            this.closeAllDropdowns();
        }

        closeMobileSidebar() {
            this.sidebar.classList.remove('sidebar-open');
            if (this.overlay) this.overlay.classList.remove('active');
        }

        handleResize() {
            if (window.innerWidth > 992) {
                // Remove mobile classes
                this.closeMobileSidebar();
                
                // Re-apply saved desktop state
                if (localStorage.getItem('sidebarCollapsed') === 'true') {
                    this.sidebar.classList.add('collapsed');
                    if (this.topNav) this.topNav.classList.add('sidebar-collapsed');
                    if (this.dashboardContent) this.dashboardContent.classList.add('sidebar-collapsed');
                }
            } else {
                // Remove desktop shrink classes so it can slide fully out
                this.sidebar.classList.remove('collapsed');
                if (this.topNav) this.topNav.classList.remove('sidebar-collapsed');
                if (this.dashboardContent) this.dashboardContent.classList.remove('sidebar-collapsed');
            }
        }
        
        closeAllDropdowns() {
            document.querySelectorAll('.nav-dropdown').forEach(dropdown => {
                dropdown.classList.remove('show');
            });
        }
    }

    // Initialize Global Managers
    new DarkMode();
    window.tooltipManager = new TooltipManager();
    new DropdownManager();
    new SidebarManager();

    // Sidebar dropdown functionality
    document.querySelectorAll('.nav-group').forEach(group => {
        const header = group.querySelector('.nav-header');
        if(header) {
            header.addEventListener('click', (e) => {
                e.stopPropagation();
                group.classList.toggle('active');
            });
        }
    });
});

// Global Toast function
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