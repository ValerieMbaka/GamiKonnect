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
                    e.stopPropagation();
                    this.dropdowns.forEach(d => { if (d !== dropdown) d.classList.remove('show'); });
                    dropdown.classList.toggle('show');
                });
            }
        });

        document.addEventListener('click', (e) => {
            if (!e.target.closest('.nav-dropdown')) {
                this.dropdowns.forEach(dropdown => dropdown.classList.remove('show'));
            }
        });
    }
}

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
        if (isCollapsed && window.innerWidth > 992) {
            [this.sidebar, this.topNav, this.dashboardContent].forEach(el => {
                if (el) el.style.transition = 'none';
            });
            
            this.sidebar.classList.add('collapsed');
            if (this.topNav) this.topNav.classList.add('sidebar-collapsed');
            if (this.dashboardContent) this.dashboardContent.classList.add('sidebar-collapsed');
            
            setTimeout(() => {
                [this.sidebar, this.topNav, this.dashboardContent].forEach(el => {
                    if (el) el.style.transition = '';
                });
            }, 50);
        }
        this.updateToggleButtonIcon();
    }

    setupEventListeners() {
        this.toggleButton.addEventListener('click', () => this.toggle());
        this.sidebar.addEventListener('transitionend', () => this.updateToggleButtonIcon());

        if (this.overlay) {
            this.overlay.addEventListener('click', () => this.closeMobileSidebar());
        }

        document.addEventListener('click', (event) => {
            if (window.innerWidth <= 992 &&
                this.sidebar.classList.contains('sidebar-open') &&
                !this.sidebar.contains(event.target) &&
                !this.toggleButton.contains(event.target)) {
                this.closeMobileSidebar();
            }
        });

        window.addEventListener('resize', () => this.handleResize());
    }

    setupActiveStateManagement() {
        const currentPath = window.location.pathname;
        document.querySelectorAll('.dashboard-sidebar .nav-link[href]').forEach(link => {
            link.classList.remove('active');
            const href = link.getAttribute('href');
            if (href && href !== '#' && currentPath.includes(new URL(href, window.location.origin).pathname)) {
                link.classList.add('active');
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
            }
        });
    }

    updateToggleButtonIcon() {
        const icon = this.toggleButton.querySelector('i');
        if(icon) {
            icon.className = 'fas fa-bars';
            this.toggleButton.setAttribute('aria-label', this.sidebar.classList.contains('collapsed') ? 'Expand sidebar' : 'Collapse sidebar');
        }
    }

    toggle() {
        if (this.isTransitioning) return;
        
        if (window.innerWidth <= 992) {
            this.sidebar.classList.toggle('sidebar-open');
            if (this.overlay) this.overlay.classList.toggle('active');
        } else {
            this.sidebar.classList.toggle('collapsed');
            if (this.topNav) this.topNav.classList.toggle('sidebar-collapsed');
            if (this.dashboardContent) this.dashboardContent.classList.toggle('sidebar-collapsed');
            localStorage.setItem('sidebarCollapsed', this.sidebar.classList.contains('collapsed'));
        }
        
        document.querySelectorAll('.nav-dropdown').forEach(d => d.classList.remove('show'));
    }

    closeMobileSidebar() {
        this.sidebar.classList.remove('sidebar-open');
        if (this.overlay) this.overlay.classList.remove('active');
    }

    handleResize() {
        if (window.innerWidth > 992) {
            this.closeMobileSidebar();
            if (localStorage.getItem('sidebarCollapsed') === 'true') {
                this.sidebar.classList.add('collapsed');
                if (this.topNav) this.topNav.classList.add('sidebar-collapsed');
                if (this.dashboardContent) this.dashboardContent.classList.add('sidebar-collapsed');
            }
        } else {
            this.sidebar.classList.remove('collapsed');
            if (this.topNav) this.topNav.classList.remove('sidebar-collapsed');
            if (this.dashboardContent) this.dashboardContent.classList.remove('sidebar-collapsed');
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new DropdownManager();
    new SidebarManager();

    document.querySelectorAll('.nav-group .nav-header').forEach(header => {
        header.addEventListener('click', (e) => {
            e.stopPropagation();
            header.parentElement.classList.toggle('active');
        });
    });
});