class AdminLibraryManager {
    constructor() {
        // Tabs
        this.tabs = document.querySelectorAll('.admin-tab');
        this.tabContents = document.querySelectorAll('.tab-content');
        
        // Filters
        this.searchInput = document.getElementById('librarySearch');
        this.gameCards = document.querySelectorAll('.admin-game-card');
        
        // Modals
        this.gameModal = document.getElementById('addGameModal');
        this.consoleModal = document.getElementById('addConsoleModal');
        this.gameForm = document.getElementById('addGameForm');
        this.consoleForm = document.getElementById('addConsoleForm');
        
        this.init();
    }

    init() {
        this.bindTabs();
        this.bindFilters();
        this.bindModals();
        this.bindForms();
    }

    bindTabs() {
        this.tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                this.tabs.forEach(t => t.classList.remove('active'));
                this.tabContents.forEach(c => c.classList.remove('active'));
                
                tab.classList.add('active');
                const targetId = tab.dataset.target;
                const targetContent = document.getElementById(targetId);
                if (targetContent) targetContent.classList.add('active');
            });
        });
    }

    bindFilters() {
        if (!this.searchInput) return;
        
        this.searchInput.addEventListener('input', () => {
            const query = this.searchInput.value.toLowerCase().trim();
            
            this.gameCards.forEach(card => {
                const title = card.querySelector('.game-title')?.textContent.toLowerCase() || '';
                if (title.includes(query)) {
                    card.style.display = 'block';
                } else {
                    card.style.display = 'none';
                }
            });
        });
    }

    bindModals() {
        // Open Game Modal
        document.querySelectorAll('.js-add-game').forEach(btn => {
            btn.addEventListener('click', () => this.gameModal?.classList.add('show'));
        });

        // Open Console Modal
        document.querySelectorAll('.js-add-console').forEach(btn => {
            btn.addEventListener('click', () => this.consoleModal?.classList.add('show'));
        });

        // Close Modals
        document.querySelectorAll('.js-close-modal').forEach(btn => {
            btn.addEventListener('click', () => {
                this.gameModal?.classList.remove('show');
                this.consoleModal?.classList.remove('show');
            });
        });

        // Click outside to close
        window.addEventListener('click', (e) => {
            if (e.target === this.gameModal) this.gameModal.classList.remove('show');
            if (e.target === this.consoleModal) this.consoleModal.classList.remove('show');
        });
    }

    bindForms() {
        if (this.gameForm) {
            this.gameForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const submitBtn = this.gameForm.querySelector('button[type="submit"]');
                const originalHtml = submitBtn.innerHTML;
                
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> Saving...';
                submitBtn.disabled = true;

                // Simulate API Call for saving game
                setTimeout(() => {
                    window.toastManager.success('Success', 'Game added to global library.');
                    submitBtn.innerHTML = originalHtml;
                    submitBtn.disabled = false;
                    this.gameForm.reset();
                    this.gameModal.classList.remove('show');
                }, 1000);
            });
        }

        if (this.consoleForm) {
            this.consoleForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const submitBtn = this.consoleForm.querySelector('button[type="submit"]');
                const originalHtml = submitBtn.innerHTML;
                
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> Saving...';
                submitBtn.disabled = true;

                // Simulate API Call for saving console
                setTimeout(() => {
                    window.toastManager.success('Success', 'Hardware platform registered.');
                    submitBtn.innerHTML = originalHtml;
                    submitBtn.disabled = false;
                    this.consoleForm.reset();
                    this.consoleModal.classList.remove('show');
                }, 800);
            });
        }
    }
}

document.addEventListener('DOMContentLoaded', () => new AdminLibraryManager());