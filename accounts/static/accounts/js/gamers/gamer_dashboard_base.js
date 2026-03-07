document.addEventListener('DOMContentLoaded', function () {
    // Dark Mode Toggle
    class DarkMode {
        constructor() {
            this.toggleButton = document.getElementById('darkModeToggle');
            if (this.toggleButton) this.init();
        }

        init() {
            this.loadTheme();
            this.toggleButton.addEventListener('click', () => this.toggle());
        }

        loadTheme() {
            const savedTheme = localStorage.getItem('theme') || 'light';
            document.documentElement.setAttribute('data-theme', savedTheme);
        }

        toggle() {
            const current = document.documentElement.getAttribute('data-theme');
            const newTheme = current === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
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
                    const isSidebarCollapsed = document.querySelector('.dashboard-sidebar.collapsed');
                    const offset = isSidebarCollapsed ? 70 : 280;

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
            this.applyStateImmediately(); // Apply state before page renders
            this.setupEventListeners();
            this.setupActiveStateManagement();
            this.setupTransitionListeners();
        }

        applyStateImmediately() {
            // Check localStorage and apply state immediately
            const isCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
            
            if (isCollapsed) {
                // Apply classes immediately without transition
                this.sidebar.style.transition = 'none';
                this.topNav.style.transition = 'none';
                this.dashboardContent.style.transition = 'none';
                
                this.sidebar.classList.add('collapsed');
                this.topNav.classList.add('sidebar-collapsed');
                this.dashboardContent.classList.add('sidebar-collapsed');
                
                // Re-enable transitions after a brief delay
                setTimeout(() => {
                    this.sidebar.style.transition = '';
                    this.topNav.style.transition = '';
                    this.dashboardContent.style.transition = '';
                }, 50);
            }
            
            this.updateToggleButtonIcon();
        }

        setupEventListeners() {
            this.toggleButton.addEventListener('click', () => this.toggle());
            
            // Update toggle button icon based on state
            this.sidebar.addEventListener('transitionend', () => {
                this.updateToggleButtonIcon();
            });
        }

        setupActiveStateManagement() {
            // Handle active states for both expanded and collapsed modes
            document.addEventListener('click', (e) => {
                const navLink = e.target.closest('.nav-link');
                if (navLink && !navLink.classList.contains('logout-link')) {
                    this.setActiveNavItem(navLink);
                }
            });

            // Set initial active state based on current page
            this.setInitialActiveState();
        }

        setupTransitionListeners() {
            // Handle transition start and end
            this.sidebar.addEventListener('transitionstart', (e) => {
                if (e.propertyName === 'width') {
                    this.isTransitioning = true;
                    this.sidebar.style.pointerEvents = 'none';
                }
            });

            this.sidebar.addEventListener('transitionend', (e) => {
                if (e.propertyName === 'width') {
                    this.isTransitioning = false;
                    this.sidebar.style.pointerEvents = 'auto';
                    
                    // Refresh tooltips after transition
                    if (window.tooltipManager) {
                        window.tooltipManager.createTooltips();
                    }
                }
            });
        }

        setActiveNavItem(activeLink) {
            // Remove active class from all nav links in the same section
            const navSection = activeLink.closest('.nav-section');
            if (navSection) {
                navSection.querySelectorAll('.nav-link').forEach(link => {
                    link.classList.remove('active');
                });
            }
            
            // Add active class to clicked link
            activeLink.classList.add('active');
            
            // Store active state for persistence if needed
            const href = activeLink.getAttribute('href');
            if (href && href !== '#') {
                localStorage.setItem('lastActiveNav', href);
            }
        }

        setInitialActiveState() {
            // Set active state based on current URL or stored state
            const currentPath = window.location.pathname;
            const navLinks = document.querySelectorAll('.nav-link[href]');
            
            navLinks.forEach(link => {
                const linkPath = link.getAttribute('href');
                if (linkPath && currentPath.includes(linkPath.split('?')[0])) {
                    this.setActiveNavItem(link);
                }
            });
        }

        updateToggleButtonIcon() {
            const icon = this.toggleButton.querySelector('i');
            if (this.sidebar.classList.contains('collapsed')) {
                icon.className = 'fas fa-bars';
                this.toggleButton.setAttribute('aria-label', 'Expand sidebar');
            } else {
                icon.className = 'fas fa-bars';
                this.toggleButton.setAttribute('aria-label', 'Collapse sidebar');
            }
        }

        collapseSidebar() {
            if (this.isTransitioning) return;
            
            this.sidebar.classList.add('collapsed');
            this.topNav.classList.add('sidebar-collapsed');
            this.dashboardContent.classList.add('sidebar-collapsed');
            
            // Close any open dropdowns
            this.closeAllDropdowns();
        }

        expandSidebar() {
            if (this.isTransitioning) return;
            
            this.sidebar.classList.remove('collapsed');
            this.topNav.classList.remove('sidebar-collapsed');
            this.dashboardContent.classList.remove('sidebar-collapsed');
        }

        closeAllDropdowns() {
            document.querySelectorAll('.nav-dropdown-content').forEach(dropdown => {
                dropdown.style.opacity = '0';
                dropdown.style.visibility = 'hidden';
            });
        }

        toggle() {
            if (this.isTransitioning) return;
            
            if (this.sidebar.classList.contains('collapsed')) {
                this.expandSidebar();
            } else {
                this.collapseSidebar();
            }
            
            localStorage.setItem('sidebarCollapsed', this.sidebar.classList.contains('collapsed'));
        }
    }

    // Initialize managers
    new TooltipManager();
    new SidebarManager();

    // Sidebar dropdown functionality
    const navGroups = document.querySelectorAll('.nav-group');

    navGroups.forEach(group => {
        const header = group.querySelector('.nav-header');

        header.addEventListener('click', (e) => {
            e.stopPropagation();
            group.classList.toggle('active');
        });
    });
    
});