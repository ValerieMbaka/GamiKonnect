class ShopWizardManager {
    constructor() {
        this.form = document.getElementById('createShopForm');
        this.steps = document.querySelectorAll('.wizard-step');
        this.indicators = document.querySelectorAll('.step-indicator');
        this.lines = document.querySelectorAll('.step-line');
        
        this.btnNext = document.getElementById('btnNext');
        this.btnPrev = document.getElementById('btnPrev');
        this.btnSubmit = document.getElementById('btnSubmit');
        
        this.currentStep = 0;
        this.totalSteps = this.steps.length;

        // Game Library State
        this.selectedGames = [];
        this.defaultGames = [];
        this.suggestionData = [];
        this.activeSuggestionIndex = -1;
        
        // DOM Elements
        this.gameInput = document.getElementById('gameSearchInput');
        this.gameSuggestionsList = document.getElementById('gameSearchSuggestions');
        this.gamesContainer = document.getElementById('selectedGamesTags');
        this.gamesHidden = document.getElementById('games_available');

        if (this.form) this.init();
    }

    async init() {
        this.bindWizardEvents();
        this.bindConsoleEvents();
        this.bindOtherConsolesEvents();
        
        await this.fetchGames();
        this.bindGameSearchEvents();
        
        this.updateWizardUI();
    }

    // Wizard Logic
    bindWizardEvents() {
        if (this.btnNext) {
            this.btnNext.addEventListener('click', () => {
                if (this.validateCurrentStep()) {
                    this.currentStep++;
                    this.updateWizardUI();
                } else {
                    if (window.toastManager) {
                        window.toastManager.error('Validation Error', 'Please fill in all required fields correctly before proceeding.');
                    }
                }
            });
        }

        if (this.btnPrev) {
            this.btnPrev.addEventListener('click', () => {
                if (this.currentStep > 0) {
                    this.currentStep--;
                    this.updateWizardUI();
                }
            });
        }

        if (this.form) {
            this.form.addEventListener('submit', (e) => {
                if (!this.validateCurrentStep()) {
                    e.preventDefault();
                    if (window.toastManager) window.toastManager.error('Validation Error', 'Please check your inputs.');
                    return;
                }

                const parsedGames = this.gamesHidden && this.gamesHidden.value ? JSON.parse(this.gamesHidden.value) : [];
                if (parsedGames.length === 0) {
                    e.preventDefault();
                    if (window.toastManager) window.toastManager.warning('Missing Games', 'Please add at least one game to your library.');
                    return;
                }

                if (this.btnSubmit) {
                    this.btnSubmit.disabled = true;
                    this.btnSubmit.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> Deploying Venue...';
                }
            });
        }
    }

    validateCurrentStep() {
        const currentStepEl = this.steps[this.currentStep];
        if (!currentStepEl) return false;
        
        const inputs = currentStepEl.querySelectorAll('input[required], textarea[required], select[required]');
        let isValid = true;
        
        inputs.forEach(input => {
            if (!input.checkValidity()) {
                isValid = false;
                input.reportValidity();
            }
        });
        return isValid;
    }

    updateWizardUI() {
        this.steps.forEach((step, index) => {
            step.classList.toggle('active', index === this.currentStep);
        });

        this.indicators.forEach((indicator, index) => {
            if (index < this.currentStep) {
                indicator.classList.add('completed');
                indicator.classList.remove('active');
            } else if (index === this.currentStep) {
                indicator.classList.add('active');
                indicator.classList.remove('completed');
            } else {
                indicator.classList.remove('active', 'completed');
            }
        });

        this.lines.forEach((line, index) => {
            line.classList.toggle('completed', index < this.currentStep);
        });

        if (this.btnPrev) this.btnPrev.style.display = this.currentStep > 0 ? 'inline-flex' : 'none';
        
        if (this.currentStep === this.totalSteps - 1) {
            if (this.btnNext) this.btnNext.style.display = 'none';
            if (this.btnSubmit) this.btnSubmit.style.display = 'inline-flex';
        } else {
            if (this.btnNext) this.btnNext.style.display = 'inline-flex';
            if (this.btnSubmit) this.btnSubmit.style.display = 'none';
        }
    }

    // Console Management Logic
    bindConsoleEvents() {
        document.addEventListener('change', (e) => {
            if (e.target && e.target.classList.contains('console-checkbox')) {
                const checkbox = e.target;
                const slug = checkbox.value;
                const quantityInput = document.querySelector(`input[name="console_quantity_${slug}"]`);
                if (quantityInput) {
                    quantityInput.disabled = !checkbox.checked;
                    if (checkbox.checked && !quantityInput.value) quantityInput.value = 1;
                }
                this.updateConsolesState();
            }
        });

        document.addEventListener('input', (e) => {
            if (e.target && e.target.classList.contains('quantity-input')) {
                this.updateConsolesState();
            }
        });
    }

    updateConsolesState() {
        const consoles = [];
        document.querySelectorAll('.console-checkbox:checked').forEach(checkbox => {
            const slug = checkbox.value;
            const quantityInput = document.querySelector(`input[name="console_quantity_${slug}"]`);
            const quantity = quantityInput ? quantityInput.value : 1;
            consoles.push({ type: slug, quantity: parseInt(quantity) });
        });
        
        const consolesHidden = document.getElementById('consoles');
        if (consolesHidden) consolesHidden.value = JSON.stringify(consoles);
    }

    bindOtherConsolesEvents() {
        const dropdown = document.getElementById('otherConsolesDropdown');
        const addBtn = document.getElementById('addOtherConsoleBtn');
        const selectedList = document.getElementById('selectedOtherConsolesList');

        if (addBtn && dropdown && selectedList) {
            addBtn.addEventListener('click', () => {
                const selectedOption = dropdown.options[dropdown.selectedIndex];
                const slug = selectedOption.value;
                const name = selectedOption.dataset.name;

                if (!slug) return;

                if (document.querySelector(`.console-checkbox-item[data-platform-slug="${slug}"]`)) {
                    if (window.toastManager) window.toastManager.info('Duplicate', `${name} is already in the list.`);
                    return;
                }

                const item = document.createElement('div');
                item.className = 'console-checkbox-item other-console-item mt-2';
                item.dataset.platformSlug = slug;
                item.innerHTML = `
                    <div class="console-info">
                        <label class="checkbox-label">
                            <input type="checkbox" name="console_types" value="${slug}" class="console-checkbox" checked>
                            ${name}
                        </label>
                    </div>
                    <div class="console-quantity-input d-flex align-items-center">
                        <input type="number" name="console_quantity_${slug}" min="1" value="1" class="form-control quantity-input">
                        <button type="button" class="btn btn-sm btn-outline-danger remove-other-console ms-3"><i class="fas fa-times"></i></button>
                    </div>
                `;

                selectedList.appendChild(item);
                this.updateConsolesState();
                dropdown.value = '';
            });

            selectedList.addEventListener('click', (e) => {
                const removeBtn = e.target.closest('.remove-other-console');
                if (removeBtn) {
                    removeBtn.closest('.console-checkbox-item').remove();
                    this.updateConsolesState();
                }
            });
        }
    }

    // Game Library Logic
    async fetchGames() {
        try {
            // Try to read from the securely injected DOM script
            const dataEl = document.getElementById('games-data');
            
            if (dataEl) {
                try {
                    this.defaultGames = JSON.parse(dataEl.textContent);
                    if (!Array.isArray(this.defaultGames)) this.defaultGames = [];
                } catch (e) {
                    console.error("DOM games parse error:", e);
                    this.defaultGames = [];
                }
            } else {
                // Fallback to API ONLY if DOM element is completely missing
                try {
                    const res = await fetch('/games/get-profile-form-data/');
                    if (res.ok) {
                        const data = await res.json();
                        if (data.success) this.defaultGames = data.games || [];
                    }
                } catch (e) {
                    console.warn("API fallback blocked by permissions. Using empty library.");
                    this.defaultGames = [];
                }
            }
            
            if (!this.defaultGames) this.defaultGames = [];
            
            // Pre-populate if editing
            const existingVal = this.gamesHidden ? this.gamesHidden.value : null;
            if (existingVal && existingVal !== '[]') {
                try {
                    const existingNames = JSON.parse(existingVal);
                    existingNames.forEach(name => {
                        const found = this.defaultGames.find(g => g.name === name);
                        if (found) {
                            this.selectedGames.push(found);
                        } else {
                            // If it's a custom game not in the default list
                            this.selectedGames.push({ id: `custom_${name.replace(/\s+/g,'_')}`, name: name });
                        }
                    });
                    this.renderGames();
                } catch (e) {
                    console.error('Error parsing existing games:', e);
                }
            }
        } catch (e) {
            console.error('Master fetchGames error:', e);
            this.defaultGames = [];
        }
    }

    addGame(value) {
        if (!value) return;
        const gameName = value.trim();
        
        // Prevent exact name duplicates
        if (this.selectedGames.some(g => g.name.toLowerCase() === gameName.toLowerCase())) return;

        const existingGame = this.defaultGames.find(g => g.name.toLowerCase() === gameName.toLowerCase());
        if (existingGame) {
            this.selectedGames.push(existingGame);
        } else {
            const custom = { id: `custom_${gameName.replace(/\s+/g,'_')}`, name: gameName };
            this.selectedGames.push(custom);
        }
        this.updateGamesState();
    }

    removeGame(gameName) {
        // Remove by exact name to prevent UUID mixups
        this.selectedGames = this.selectedGames.filter(g => g.name !== gameName);
        this.updateGamesState();
    }

    updateGamesState() {
        if (this.gamesHidden) {
            // Ensure we are ONLY sending an array of String Names to the backend
            const gameNames = this.selectedGames.map(g => g.name);
            this.gamesHidden.value = JSON.stringify(gameNames);
        }
        this.renderGames();
    }

    renderGames() {
        if (!this.gamesContainer) return;
        this.gamesContainer.innerHTML = '';
        
        this.selectedGames.forEach(g => {
            const chip = document.createElement('span');
            chip.className = 'chip active';
            chip.innerHTML = `${g.name} <span class="remove ms-2">&times;</span>`;
            
            // Bind removal
            chip.querySelector('.remove').addEventListener('click', () => this.removeGame(g.name));
            this.gamesContainer.appendChild(chip);
        });
    }

    bindGameSearchEvents() {
        if (!this.gameInput) return;

        this.gameInput.addEventListener('input', () => {
            const term = this.gameInput.value.toLowerCase();
            this.gameSuggestionsList.innerHTML = '';
            this.activeSuggestionIndex = -1;
            
            if (!term) {
                this.gameSuggestionsList.style.display = 'none';
                return;
            }

            this.suggestionData = this.defaultGames.filter(g =>
                g.name.toLowerCase().includes(term) &&
                !this.selectedGames.some(sg => sg.name.toLowerCase() === g.name.toLowerCase())
            ).slice(0, 10);

            if (this.suggestionData.length > 0) {
                this.suggestionData.forEach((g, index) => {
                    const item = document.createElement('div');
                    item.className = 'suggestion-item';
                    item.textContent = g.name;
                    
                    item.addEventListener('mouseenter', () => {
                        this.activeSuggestionIndex = index;
                        this.setActiveSuggestion();
                    });
                    
                    item.addEventListener('mousedown', (e) => {
                        e.preventDefault();
                        this.addGame(g.name);
                        this.gameInput.value = '';
                        this.gameSuggestionsList.style.display = 'none';
                    });
                    this.gameSuggestionsList.appendChild(item);
                });
                this.gameSuggestionsList.style.display = 'block';
            } else {
                this.gameSuggestionsList.style.display = 'none';
            }
        });

        this.gameInput.addEventListener('keydown', (e) => {
            const listHidden = !this.gameSuggestionsList || this.gameSuggestionsList.style.display === 'none';

            if (listHidden) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    const val = (this.gameInput.value || '').trim();
                    if (val) this.addGame(val);
                    this.gameInput.value = '';
                }
            } else {
                if (e.key === 'ArrowDown') {
                    e.preventDefault();
                    this.activeSuggestionIndex = (this.activeSuggestionIndex + 1) % this.suggestionData.length;
                    this.setActiveSuggestion();
                } else if (e.key === 'ArrowUp') {
                    e.preventDefault();
                    this.activeSuggestionIndex = (this.activeSuggestionIndex - 1 + this.suggestionData.length) % this.suggestionData.length;
                    this.setActiveSuggestion();
                } else if (e.key === 'Enter') {
                    e.preventDefault();
                    if (this.activeSuggestionIndex >= 0 && this.suggestionData[this.activeSuggestionIndex]) {
                        this.addGame(this.suggestionData[this.activeSuggestionIndex].name);
                    } else {
                        const val = (this.gameInput.value || '').trim();
                        if (val) this.addGame(val);
                    }
                    this.gameInput.value = '';
                    this.gameSuggestionsList.style.display = 'none';
                } else if (e.key === 'Escape') {
                    this.gameSuggestionsList.style.display = 'none';
                }
            }
        });

        document.addEventListener('click', (e) => {
            if (this.gameInput && !this.gameInput.contains(e.target)) {
                if (this.gameSuggestionsList) this.gameSuggestionsList.style.display = 'none';
            }
        });
    }

    setActiveSuggestion() {
        if (!this.gameSuggestionsList) return;
        const items = Array.from(this.gameSuggestionsList.children);
        items.forEach((el, i) => {
            if (i === this.activeSuggestionIndex) el.classList.add('active');
            else el.classList.remove('active');
        });
    }
}

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', () => {
    window.shopWizardManager = new ShopWizardManager();
});