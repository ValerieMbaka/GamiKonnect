class AdminGamesController {
    constructor() {
        this.cacheDOM();
        this.bindEvents();
        this.initViewPreference();
        
        const tokenInput = document.querySelector('[name=csrfmiddlewaretoken]');
        this.csrfToken = tokenInput ? tokenInput.value : '';
    }

    cacheDOM() {
        this.modal = document.getElementById('gameModal');
        this.form = document.getElementById('gameForm');
        this.modalTitle = document.getElementById('modalTitle');
        this.saveBtn = document.getElementById('saveGameBtn');
        this.gameIdInput = document.getElementById('game_id_input');
        
        this.btnGrid = document.getElementById('btnGrid');
        this.btnList = document.getElementById('btnList');
        this.gridView = document.getElementById('gridView');
        this.listView = document.getElementById('listView');
    }

    bindEvents() {
        if (this.form) {
            this.form.addEventListener('submit', (e) => this.saveGame(e));
        }
        
        if (this.btnGrid && this.btnList) {
            this.btnGrid.addEventListener('click', () => this.switchView('grid'));
            this.btnList.addEventListener('click', () => this.switchView('list'));
        }

        document.querySelectorAll('.admin-modal select').forEach(select => {
            select.classList.add('form-control');
        });
    }

    initViewPreference() {
        const savedView = localStorage.getItem('gamesAdminView') || 'grid';
        this.switchView(savedView);
    }

    switchView(viewType) {
        if (viewType === 'grid') {
            this.gridView.classList.remove('hidden');
            this.listView.classList.add('hidden');
            this.btnGrid.classList.add('active');
            this.btnList.classList.remove('active');
            localStorage.setItem('gamesAdminView', 'grid');
        } else {
            this.gridView.classList.add('hidden');
            this.listView.classList.remove('hidden');
            this.btnGrid.classList.remove('active');
            this.btnList.classList.add('active');
            localStorage.setItem('gamesAdminView', 'list');
        }
    }

    async openModal(gameId = null) {
        this.form.reset();
        this.clearErrors();
        this.gameIdInput.value = '';
        
        if (gameId) {
            this.modalTitle.innerHTML = '<i class="fas fa-pen"></i> Edit Game';
            await this.loadGameData(gameId);
        } else {
            this.modalTitle.innerHTML = '<i class="fas fa-gamepad"></i> Add New Game';
        }

        this.modal.classList.add('active');
        document.body.style.overflow = 'hidden';
    }

    closeModal() {
        this.modal.classList.remove('active');
        document.body.style.overflow = '';
    }

    clearErrors() {
        this.form.querySelectorAll('.error-msg').forEach(el => el.textContent = '');
    }

    async loadGameData(gameId) {
        try {
            const response = await fetch(`/admin_panel/games/api/${gameId}/`);
            const data = await response.json();
            
            if (data.success) {
                const game = data.data;
                this.gameIdInput.value = game.game_id;
                document.getElementById('id_name').value = game.name;
                document.getElementById('id_description').value = game.description;
                document.getElementById('id_is_active').checked = game.is_active;
                document.getElementById('id_is_verified').checked = game.is_verified;
                
                this.setSelectMultiple('id_genres', game.genres);
                this.setSelectMultiple('id_supported_platforms', game.supported_platforms);
            }
        } catch (error) {
            console.error('Error loading game:', error);
            if(typeof showToast === "function") showToast('Failed to load game data.', 'error');
        }
    }

    setSelectMultiple(selectId, valuesArray) {
        const select = document.getElementById(selectId);
        if (!select) return;
        Array.from(select.options).forEach(option => {
            option.selected = valuesArray.includes(parseInt(option.value));
        });
    }

    async saveGame(e) {
        e.preventDefault();
        const originalText = this.saveBtn.innerHTML;
        this.saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
        this.saveBtn.disabled = true;
        this.clearErrors();

        try {
            const formData = new FormData(this.form);
            const response = await fetch('/admin_panel/games/api/save/', {
                method: 'POST',
                body: formData,
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });

            const data = await response.json();

            if (response.ok && data.success) {
                this.closeModal();
                if(typeof showToast === "function") showToast(data.message, 'success');
                setTimeout(() => window.location.reload(), 1000);
            } else if (data.errors) {
                Object.entries(data.errors).forEach(([field, messages]) => {
                    const errorDiv = document.getElementById(`error-${field}`);
                    if (errorDiv) errorDiv.textContent = messages[0];
                });
            }
        } catch (error) {
            console.error('Save error:', error);
            if(typeof showToast === "function") showToast('A network error occurred.', 'error');
        } finally {
            this.saveBtn.innerHTML = originalText;
            this.saveBtn.disabled = false;
        }
    }
}

const gameManager = new AdminGamesController();