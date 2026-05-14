document.addEventListener('DOMContentLoaded', () => {
    
    // --- CONSOLE MANAGEMENT ---
    document.querySelectorAll('.console-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', (e) => {
            const slug = e.target.value;
            const quantityInput = document.querySelector(`input[name="console_quantity_${slug}"]`);
            if (quantityInput) {
                quantityInput.disabled = !e.target.checked;
                if (e.target.checked && (!quantityInput.value || quantityInput.value === "0")) {
                    quantityInput.value = 1;
                }
            }
        });
    });

    // --- GAME LIBRARY & PRICING MANAGEMENT ---
    const gameInput = document.getElementById('gameSearchInput');
    const suggestionsList = document.getElementById('gameSearchSuggestions');
    const tagsContainer = document.getElementById('selectedGamesTags');
    const gamesHidden = document.getElementById('games_available');
    
    const pricingContainer = document.getElementById('pricingContainer');
    const pricingHidden = document.getElementById('game_pricing');
    const addPricingBtn = document.getElementById('addPricingBtn');
    
    let defaultGames = [];
    let selectedGames = [];
    let pricingDataArray = [];

    // Initialize from DOM JSON script payloads
    function init() {
        try {
            const dataEl = document.getElementById('games-data');
            if (dataEl) defaultGames = JSON.parse(dataEl.textContent);
        } catch (e) { console.error(e); }

        let existingGamesData = [];
        let existingPricingData = [];

        try {
            const existingGamesEl = document.getElementById('existing-games-data');
            if (existingGamesEl) existingGamesData = JSON.parse(existingGamesEl.textContent);
        } catch (e) { console.error(e); }

        try {
            const existingPricingEl = document.getElementById('existing-pricing-data');
            if (existingPricingEl) existingPricingData = JSON.parse(existingPricingEl.textContent);
        } catch (e) { console.error(e); }

        if (Array.isArray(existingGamesData)) {
            existingGamesData.forEach(name => addGame(name, false));
        }

        if (Array.isArray(existingPricingData)) {
            existingPricingData.forEach(data => addPricingRow(data));
        }
        
        updateHiddenFields();
        bindSearchEvents();
    }

    // Add a game to the library
    function addGame(name, focusPricing = true) {
        name = name.trim();
        if (!name || selectedGames.includes(name)) return;
        
        selectedGames.push(name);
        
        const chip = document.createElement('div');
        chip.className = 'game-chip text-dark';
        chip.innerHTML = `${name} <i class="fas fa-times remove-chip ms-1"></i>`;
        
        chip.querySelector('.remove-chip').addEventListener('click', () => {
            selectedGames = selectedGames.filter(g => g !== name);
            chip.remove();
            
            // Also remove any custom pricing associated with this game
            const pricingRows = pricingContainer.querySelectorAll('.pricing-row');
            pricingRows.forEach(row => {
                const select = row.querySelector('.pricing-game-select');
                if (select.value === name) row.remove();
            });
            
            updateHiddenFields();
            updatePricingDropdowns();
        });
        
        tagsContainer.appendChild(chip);
        updateHiddenFields();
        updatePricingDropdowns();
    }

    // Custom Pricing Row Builder
    function addPricingRow(data = { game_id: '', price_per_hour: '', is_premium: false }) {
        const rowId = 'pricing_' + Date.now();
        const row = document.createElement('div');
        row.className = 'pricing-row row g-3 align-items-center position-relative';
        row.id = rowId;
        
        row.innerHTML = `
            <div class="col-md-5">
                <label class="small text-muted fw-bold mb-1">Select Game</label>
                <select class="form-select bg-white border-light pricing-game-select">
                    <option value="">Choose...</option>
                    ${selectedGames.map(g => `<option value="${g}" ${data.game_id === g ? 'selected' : ''}>${g}</option>`).join('')}
                </select>
            </div>
            <div class="col-md-3">
                <label class="small text-muted fw-bold mb-1">Custom Rate</label>
                <input type="number" step="0.01" class="form-control bg-white border-light text-success fw-bold pricing-rate" placeholder="Ksh" value="${data.price_per_hour}">
            </div>
            <div class="col-md-3 d-flex align-items-end h-100 pb-2">
                <div class="form-check form-switch mt-2">
                    <input class="form-check-input pricing-premium" type="checkbox" role="switch" id="prem_${rowId}" ${data.is_premium ? 'checked' : ''}>
                    <label class="form-check-label small fw-bold text-dark" for="prem_${rowId}">Premium</label>
                </div>
            </div>
            <div class="col-md-1 d-flex align-items-end h-100 pb-1 justify-content-end">
                <button type="button" class="btn btn-light text-danger rounded-circle remove-pricing border remove-pricing-btn">
                    <i class="fas fa-trash-alt"></i>
                </button>
            </div>
        `;
        
        row.querySelector('.remove-pricing').addEventListener('click', () => {
            row.remove();
            updateHiddenFields();
        });
        
        // Listen for changes to trigger hidden field update
        row.querySelectorAll('select, input').forEach(el => {
            el.addEventListener('change', updateHiddenFields);
            el.addEventListener('input', updateHiddenFields);
        });

        pricingContainer.appendChild(row);
    }

    function updatePricingDropdowns() {
        document.querySelectorAll('.pricing-game-select').forEach(select => {
            const currentVal = select.value;
            select.innerHTML = '<option value="">Choose...</option>' +
                selectedGames.map(g => `<option value="${g}" ${currentVal === g ? 'selected' : ''}>${g}</option>`).join('');
        });
    }

    function updateHiddenFields() {
        gamesHidden.value = JSON.stringify(selectedGames);
        
        const newPricingData = [];
        pricingContainer.querySelectorAll('.pricing-row').forEach(row => {
            const game = row.querySelector('.pricing-game-select').value;
            const price = row.querySelector('.pricing-rate').value;
            const isPremium = row.querySelector('.pricing-premium').checked;
            
            if (game && price) {
                newPricingData.push({
                    game_id: game,
                    price_per_hour: parseFloat(price),
                    is_premium: isPremium
                });
            }
        });
        pricingHidden.value = JSON.stringify(newPricingData);
    }

    function bindSearchEvents() {
        gameInput.addEventListener('input', (e) => {
            const term = e.target.value.toLowerCase();
            suggestionsList.innerHTML = '';
            
            if (!term) {
                suggestionsList.classList.add('d-none');
                return;
            }

            const matches = defaultGames.filter(g =>
                g.name.toLowerCase().includes(term) && !selectedGames.includes(g.name)
            ).slice(0, 8);

            if (matches.length > 0) {
                matches.forEach(g => {
                    const item = document.createElement('div');
                    item.className = 'suggestion-item';
                    item.textContent = g.name;
                    item.addEventListener('mousedown', (ev) => {
                        ev.preventDefault();
                        addGame(g.name);
                        gameInput.value = '';
                        suggestionsList.classList.add('d-none');
                    });
                    suggestionsList.appendChild(item);
                });
                suggestionsList.classList.remove('d-none');
            } else {
                suggestionsList.classList.add('d-none');
            }
        });

        gameInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                const val = gameInput.value.trim();
                if (val) addGame(val);
                gameInput.value = '';
                suggestionsList.classList.add('d-none');
            }
        });

        document.addEventListener('click', (e) => {
            if (!gameInput.contains(e.target)) {
                suggestionsList.classList.add('d-none');
            }
        });

        addPricingBtn.addEventListener('click', () => addPricingRow());
        
        // Prevent form submission if inputs are invalid
        document.getElementById('editShopForm').addEventListener('submit', () => {
            document.getElementById('btnSubmit').disabled = true;
            document.getElementById('btnSubmit').innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> Saving...';
        });
    }

    init();
});