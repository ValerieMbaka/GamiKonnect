class AdminLayoutManager {
    constructor() {
        this.sidebar = document.getElementById('adminSidebar');
        this.topbar = document.getElementById('adminTopbar');
        this.mainContent = document.getElementById('adminMainContent');
        this.toggleBtn = document.getElementById('adminSidebarToggle');
        
        if (this.sidebar) this.init();
    }

    init() {
        this.bindEvents();
        this.checkViewport();
    }

    bindEvents() {
        if (this.toggleBtn) {
            this.toggleBtn.addEventListener('click', () => this.toggleSidebar());
        }

        window.addEventListener('resize', () => this.checkViewport());
    }

    toggleSidebar() {
        if (window.innerWidth <= 992) {
            this.sidebar.classList.toggle('mobile-open');
        } else {
            this.sidebar.classList.toggle('collapsed');
            this.topbar.classList.toggle('expanded');
            this.mainContent.classList.toggle('expanded');
        }
    }

    checkViewport() {
        if (window.innerWidth <= 992) {
            this.sidebar.classList.remove('collapsed');
            this.topbar.classList.add('expanded');
            this.mainContent.classList.add('expanded');
        } else {
            this.sidebar.classList.remove('mobile-open');
            this.topbar.classList.remove('expanded');
            this.mainContent.classList.remove('expanded');
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.adminLayout = new AdminLayoutManager();
});