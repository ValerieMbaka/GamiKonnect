document.addEventListener('DOMContentLoaded', function() {
    // Initialize games selectize
    $('#gamesSelect').selectize({
        plugins: ['remove_button'],
        delimiter: ',',
        persist: false,
        maxItems: null,
        create: false,
        onChange: function(value) {
            document.getElementById('games_available').value = JSON.stringify(value);
            // Update pricing dropdowns when games selection changes
            updatePricingDropdowns();
        }
    });

    // Console management
    const consolesContainer = document.getElementById('consolesContainer');
    const consoleTypes = [
        {value: 'PLAYSTATION_5', label: 'PlayStation 5'},
        {value: 'PLAYSTATION_4', label: 'PlayStation 4'},
        {value: 'XBOX_SERIES_X', label: 'Xbox Series X'},
        {value: 'XBOX_ONE', label: 'Xbox One'},
        {value: 'NINTENDO_SWITCH', label: 'Nintendo Switch'},
        {value: 'PC', label: 'Gaming PC'},
        {value: 'OCULUS', label: 'Oculus/Meta Quest'},
        {value: 'VR', label: 'Other VR Headset'},
        {value: 'ARCADE', label: 'Arcade Machine'},
        {value: 'OTHER', label: 'Other Console'}
    ];

    function addConsole(consoleData = {}) {
        const consoleId = Date.now();
        const consoleElement = document.createElement('div');
        consoleElement.className = 'console-item';
        consoleElement.innerHTML = `
            <div class="console-header">
                <h4>Console</h4>
                <button type="button" class="btn btn-sm btn-danger remove-console" data-id="${consoleId}">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Console Type</label>
                    <select name="console_type_${consoleId}" class="console-type" required>
                        <option value="">Select Console Type</option>
                        ${consoleTypes.map(type =>
                            `<option value="${type.value}" ${consoleData.type === type.value ? 'selected' : ''}>
                                ${type.label}
                            </option>`
                        ).join('')}
                    </select>
                </div>
                <div class="form-group">
                    <label>Quantity</label>
                    <input type="number" name="console_quantity_${consoleId}"
                           class="console-quantity" min="1" value="${consoleData.quantity || 1}" required>
                </div>
            </div>
            <div class="form-group">
                <label>Notes (Optional)</label>
                <input type="text" name="console_notes_${consoleId}" class="console-notes"
                       placeholder="e.g., Special editions, models, etc." value="${consoleData.notes || ''}">
            </div>
        `;
        consolesContainer.appendChild(consoleElement);

        // Add remove event listener
        consoleElement.querySelector('.remove-console').addEventListener('click', function() {
            consoleElement.remove();
            updateConsolesData();
        });

        // Add change event listeners
        consoleElement.querySelector('.console-type').addEventListener('change', updateConsolesData);
        consoleElement.querySelector('.console-quantity').addEventListener('input', updateConsolesData);
        consoleElement.querySelector('.console-notes').addEventListener('input', updateConsolesData);

        updateConsolesData();
    }

    function updateConsolesData() {
        const consoles = [];
        document.querySelectorAll('.console-item').forEach(item => {
            const type = item.querySelector('.console-type').value;
            const quantity = item.querySelector('.console-quantity').value;
            const notes = item.querySelector('.console-notes').value;

            if (type) {
                consoles.push({
                    type: type,
                    quantity: parseInt(quantity),
                    notes: notes
                });
            }
        });
        document.getElementById('consoles').value = JSON.stringify(consoles);
    }

    // Custom games management
    const newGamesList = document.getElementById('newGamesList');
    const newGamesInput = document.getElementById('new_games');
    const newGameNameInput = document.getElementById('newGameName');
    const platformPicker = document.getElementById('platformPicker');
    const addNewGameBtn = document.getElementById('addNewGameBtn');
    let selectedPlatforms = [];
    const customGames = [];

    if (platformPicker) {
        platformPicker.querySelectorAll('span').forEach(span => {
            span.addEventListener('click', () => {
                const value = span.dataset.value;
                if (selectedPlatforms.includes(value)) {
                    selectedPlatforms = selectedPlatforms.filter(item => item !== value);
                    span.classList.remove('active');
                } else {
                    selectedPlatforms.push(value);
                    span.classList.add('active');
                }
            });
        });
    }

    function renderCustomGames() {
        if (!newGamesList) return;
        newGamesList.innerHTML = '';
        customGames.forEach((game, index) => {
            const pill = document.createElement('div');
            pill.className = 'new-game-pill';
            pill.innerHTML = `
                <div>
                    <strong>${game.name}</strong>
                    <small>${game.platforms.join(', ')}</small>
                </div>
                <button type="button" class="btn btn-sm btn-outline-danger" data-index="${index}">
                    <i class="fas fa-times"></i>
                </button>
            `;
            pill.querySelector('button').addEventListener('click', (event) => {
                const idx = parseInt(event.currentTarget.dataset.index, 10);
                customGames.splice(idx, 1);
                newGamesInput.value = JSON.stringify(customGames);
                renderCustomGames();
            });
            newGamesList.appendChild(pill);
        });
    }

    addNewGameBtn?.addEventListener('click', () => {
        const name = newGameNameInput.value.trim();
        if (!name) {
            showToast('Enter a game name to continue', 'error');
            return;
        }
        if (selectedPlatforms.length === 0) {
            showToast('Select at least one platform', 'error');
            return;
        }
        customGames.push({ name, platforms: [...selectedPlatforms] });
        newGameNameInput.value = '';
        selectedPlatforms = [];
        platformPicker?.querySelectorAll('span').forEach(span => span.classList.remove('active'));
        newGamesInput.value = JSON.stringify(customGames);
        renderCustomGames();
        // Update pricing dropdowns to include the new custom game
        updatePricingDropdowns();
    });

    // Pricing management
    const pricingContainer = document.getElementById('pricingContainer');

    // Function to get all available games (existing + custom)
    function getAllAvailableGames() {
        const existingGames = [];
        const gamesSelect = document.getElementById('gamesSelect');
        if (gamesSelect && gamesSelect.selectize) {
            const selectize = gamesSelect.selectize;
            // Get all options from selectize
            Object.keys(selectize.options).forEach(value => {
                const option = selectize.options[value];
                existingGames.push({ id: value, name: option.text || option });
            });
        } else if (gamesSelect) {
            // Fallback: get options from the select element directly
            Array.from(gamesSelect.options).forEach(option => {
                if (option.value) {
                    existingGames.push({ id: option.value, name: option.text });
                }
            });
        }
        
        // Add custom games with temporary IDs (will be handled server-side)
        const customGamesList = customGames.map((game, index) => ({
            id: `custom_${index}`,
            name: game.name,
            isCustom: true
        }));
        
        return [...existingGames, ...customGamesList];
    }

    // Function to update all pricing dropdowns with current games
    function updatePricingDropdowns() {
        const allGames = getAllAvailableGames();
        document.querySelectorAll('.pricing-game').forEach(select => {
            const currentValue = select.value;
            const currentOptions = Array.from(select.options).map(opt => opt.value);
            
            // Add custom games that aren't already in the dropdown
            allGames.forEach(game => {
                if (!currentOptions.includes(game.id)) {
                    const option = document.createElement('option');
                    option.value = game.id;
                    option.textContent = game.name + (game.isCustom ? ' (Custom)' : '');
                    select.appendChild(option);
                }
            });
        });
    }

    function addPricing(pricingData = {}) {
        const pricingId = Date.now();
        const allGames = getAllAvailableGames();
        const pricingElement = document.createElement('div');
        pricingElement.className = 'pricing-item';
        
        let gameOptions = '<option value="">Select Game</option>';
        allGames.forEach(game => {
            const selected = pricingData.game_id == game.id ? 'selected' : '';
            gameOptions += `<option value="${game.id}" ${selected}>${game.name}${game.isCustom ? ' (Custom)' : ''}</option>`;
        });
        
        pricingElement.innerHTML = `
            <div class="pricing-header">
                <h4>Game Pricing</h4>
                <button type="button" class="btn btn-sm btn-danger remove-pricing" data-id="${pricingId}">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Game</label>
                    <select name="pricing_game_${pricingId}" class="pricing-game" required>
                        ${gameOptions}
                    </select>
                </div>
                <div class="form-group">
                    <label>Price per Hour (Ksh)</label>
                    <input type="number" name="pricing_price_${pricingId}"
                           class="pricing-price" step="0.01" min="0"
                           value="${pricingData.price_per_hour || ''}" required>
                </div>
            </div>
            <div class="form-group">
                <label class="checkbox-label">
                    <input type="checkbox" name="pricing_premium_${pricingId}"
                           class="pricing-premium" ${pricingData.is_premium ? 'checked' : ''}>
                    <span class="checkmark"></span>
                    Premium Game (Special pricing)
                </label>
            </div>
        `;
        pricingContainer.appendChild(pricingElement);

        // Add remove event listener
        pricingElement.querySelector('.remove-pricing').addEventListener('click', function() {
            pricingElement.remove();
            updatePricingData();
        });

        // Add change event listeners
        pricingElement.querySelector('.pricing-game').addEventListener('change', updatePricingData);
        pricingElement.querySelector('.pricing-price').addEventListener('input', updatePricingData);
        pricingElement.querySelector('.pricing-premium').addEventListener('change', updatePricingData);

        updatePricingData();
    }

    function updatePricingData() {
        const pricing = [];
        document.querySelectorAll('.pricing-item').forEach(item => {
            const gameSelect = item.querySelector('.pricing-game');
            const gameId = gameSelect ? gameSelect.value : null;
            const priceInput = item.querySelector('.pricing-price');
            const price = priceInput ? priceInput.value : null;
            const premiumCheck = item.querySelector('.pricing-premium');
            const isPremium = premiumCheck ? premiumCheck.checked : false;

            if (gameId && price) {
                pricing.push({
                    game_id: gameId,
                    price_per_hour: parseFloat(price),
                    is_premium: isPremium
                });
            }
        });
        const pricingInput = document.getElementById('game_pricing');
        if (pricingInput) {
            pricingInput.value = JSON.stringify(pricing);
        }
    }

    // Add hidden inputs for consoles and pricing
    const consolesInput = document.createElement('input');
    consolesInput.type = 'hidden';
    consolesInput.name = 'consoles';
    consolesInput.id = 'consoles';
    consolesInput.value = '[]';
    document.getElementById('createShopForm').appendChild(consolesInput);

    const pricingInput = document.createElement('input');
    pricingInput.type = 'hidden';
    pricingInput.name = 'game_pricing';
    pricingInput.id = 'game_pricing';
    pricingInput.value = '[]';
    document.getElementById('createShopForm').appendChild(pricingInput);

    // Event listeners for add buttons
    document.getElementById('addConsoleBtn').addEventListener('click', function() {
        addConsole();
    });

    document.getElementById('addPricingBtn').addEventListener('click', function() {
        addPricing();
    });

    // Add one initial console
    addConsole();

    // Form submission
    document.getElementById('createShopForm').addEventListener('submit', function(e) {
        // Validate at least one game is selected
        const gamesAvailable = document.getElementById('games_available').value;
        const parsedGames = gamesAvailable ? JSON.parse(gamesAvailable) : [];
        if (parsedGames.length === 0 && customGames.length === 0) {
            e.preventDefault();
            showToast('Add at least one existing or custom game', 'error');
            return;
        }

        // Validate base price
        const basePrice = document.getElementById('base_price_per_hour').value;
        if (!basePrice || parseFloat(basePrice) <= 0) {
            e.preventDefault();
            showToast('Please enter a valid base price per hour', 'error');
            return;
        }

        // Show loading state
        const submitBtn = this.querySelector('button[type="submit"]');
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creating Shop...';
    });
});

function showToast(message, type = 'info') {
    // Prefer the centralized toast manager, fall back to legacy showToast, otherwise log
    const title = type.charAt(0).toUpperCase() + type.slice(1);
    if (window.toastManager && typeof window.toastManager.show === 'function') {
        window.toastManager.show({ type, title, message });
    } else if (typeof window.showToast === 'function') {
        window.showToast(message, type);
    } else {
        // As last resort avoid blocking alert; log for devs
        console[type === 'error' ? 'error' : 'log'](`[${title}] ${message}`);
    }
}