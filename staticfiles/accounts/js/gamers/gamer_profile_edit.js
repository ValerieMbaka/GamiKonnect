class ProfileEditManager {
    constructor() {
        this.cacheDOM();
        if (this.form) this.init();
    }

    cacheDOM() {
        this.form = document.getElementById('editProfileForm');
        this.submitBtn = document.getElementById('editProfileSubmitBtn');
        this.selectedGamesContainer = document.getElementById('selectedGames');
        this.gamesInputHidden = document.getElementById('id_games');
        this.gameInput = document.getElementById('games_input');
        this.suggestionsList = document.getElementById('gameSuggestionsEdit');
    }

    init() {
        this.bindEvents();
        this.updateHiddenGamesInput();
    }

    bindEvents() {
        if (this.form) {
            this.form.addEventListener('submit', (e) => this.handleSubmit(e));
        }
        
        if (this.selectedGamesContainer) {
            this.selectedGamesContainer.addEventListener('click', (e) => {
                if (e.target.classList.contains('remove')) {
                    this.removeGameChip(e.target.closest('.chip'));
                }
            });
        }
        
        if (this.gameInput) {
            this.gameInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    this.addGameChip(this.gameInput.value.trim());
                    this.gameInput.value = '';
                }
            });
        }
    }

    addGameChip(gameName) {
        if (!gameName || !this.selectedGamesContainer) return;
        const currentGames = this.gamesInputHidden.value.split(',').map(g => g.trim().toLowerCase());
        if (currentGames.includes(gameName.toLowerCase())) {
            if(window.toastManager) window.toastManager.warning('Duplicate', `${gameName} is already added.`);
            return;
        }

        const chip = document.createElement('span');
        chip.className = 'chip active chip-just-added';
        
        const textNode = document.createTextNode(gameName + ' ');
        const removeBtn = document.createElement('span');
        removeBtn.className = 'remove';
        removeBtn.dataset.game = gameName;
        removeBtn.textContent = '×';
        
        chip.appendChild(textNode);
        chip.appendChild(removeBtn);
        
        this.selectedGamesContainer.appendChild(chip);
        setTimeout(() => chip.classList.remove('chip-just-added'), 700);
        this.updateHiddenGamesInput();
    }

    removeGameChip(chipElement) {
        if (!chipElement) return;
        const gameName = chipElement.querySelector('.remove').dataset.game;
        chipElement.remove();
        this.updateHiddenGamesInput();
        if(window.toastManager) window.toastManager.info('Game Removed', `${gameName} removed from list.`);
    }

    updateHiddenGamesInput() {
        if (!this.selectedGamesContainer || !this.gamesInputHidden) return;
        const chips = this.selectedGamesContainer.querySelectorAll('.chip');
        const gameNames = Array.from(chips).map(chip => {
            const removeBtn = chip.querySelector('.remove');
            return removeBtn ? removeBtn.dataset.game : '';
        }).filter(Boolean);
        this.gamesInputHidden.value = gameNames.join(',');
    }

    async handleSubmit(e) {
        e.preventDefault();
        if (!this.submitBtn) return;
        
        const originalHTML = this.submitBtn.innerHTML;
        this.submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> <span>Saving...</span>';
        this.submitBtn.disabled = true;

        try {
            const formData = new FormData(this.form);
            const response = await fetch(this.form.dataset.url || this.form.action, {
                method: 'POST',
                body: formData,
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });

            let data = {};
            try { data = await response.json(); } catch(err) {}

            if (response.ok && data.success) {
                if(window.toastManager) window.toastManager.success('Success', data.message || 'Profile updated successfully!');
                setTimeout(() => { window.location.href = '/accounts/gamer-settings/'; }, 1200);
            } else {
                if(window.toastManager) window.toastManager.error('Update Failed', data.message || 'Failed to update profile.');
            }
        } catch (err) {
            console.error(err);
            if(window.toastManager) window.toastManager.error('Network Error', 'Unexpected error occurred.');
        } finally {
            this.submitBtn.innerHTML = originalHTML;
            this.submitBtn.disabled = false;
        }
    }
}

document.addEventListener('DOMContentLoaded', () => new ProfileEditManager());