document.addEventListener('DOMContentLoaded', function() {
    // Inject minimal styles for game suggestions and chips
    (function injectStyles(){
        if (document.getElementById('create-shop-enhanced-styles')) return;
        const style = document.createElement('style');
        style.id = 'create-shop-enhanced-styles';
        style.textContent = `
            .game-suggestions { 
                position: absolute;
                z-index: 1000;
                background: var(--bg-primary);
                border: 1px solid var(--border-color);
                border-radius: 8px;
                width: 100%;
                max-height: 200px;
                overflow-y: auto;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                display: none;
            }
            .suggestion-item {
                padding: 10px 15px;
                cursor: pointer;
                transition: all 0.2s;
            }
            .suggestion-item:hover, .suggestion-item.active {
                background: var(--bg-secondary);
                color: var(--primary-color);
            }
            .chips {
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
                margin-top: 10px;
            }
            .chip {
                background: var(--bg-secondary);
                padding: 5px 12px;
                border-radius: 20px;
                display: flex;
                align-items: center;
                gap: 8px;
                font-size: 0.9rem;
                color: var(--text-primary);
                border: 1px solid var(--border-color);
            }
            .chip.active {
                background: var(--primary-color);
                color: white;
                border-color: var(--primary-color);
            }
            .chip .remove {
                cursor: pointer;
                font-weight: bold;
            }
            .game-input-section { position: relative; }
        `;
        document.head.appendChild(style);
    })();

    // Game selection
    const gamesContainer = document.getElementById('selectedGamesTags');
    const gamesHidden = document.getElementById('games_available');
    const gameInput = document.getElementById('gameSearchInput');
    const gameSuggestionsList = document.getElementById('gameSearchSuggestions');
    let selectedGames = [];
    let defaultGames = [];
    let lastAddedGameId = null;
    let suggestionData = [];
    let activeSuggestionIndex = -1;

    function addGame(value) {
        if (!value) return;
        const gameName = value.trim().toLowerCase();
        if (!gameName) return;

        // 1. Check if it's already selected
        if (selectedGames.some(g => g.name.toLowerCase() === gameName)) {
            showToast('Game already selected.', 'info');
            return;
        }

        // 2. Check if it exists in the default list
        const existingGame = defaultGames.find(g => g.name.toLowerCase() === gameName);
        if (existingGame) {
            // If it exists but isn't selected, add it to selectedGames
            selectedGames.push(existingGame);
            lastAddedGameId = existingGame.id;
        } else {
            // 3. If it's a new custom game, add it
            const custom = { id: `custom_${gameName.replace(/\s+/g,'_')}`, name: value.trim() };
            selectedGames.push(custom);
            lastAddedGameId = custom.id;
        }
        updateGames();
    }

    function removeGame(gameId) {
        selectedGames = selectedGames.filter(g => g.id !== gameId);
        updateGames();
    }

    function updateGames() {
        if(gamesHidden) {
            // Extract IDs for hidden input (or names if needed by backend, but IDs/names mix is handled)
            const gameData = selectedGames.map(g => ({ id: g.id, name: g.name }));
            gamesHidden.value = JSON.stringify(gameData.map(g => g.id.toString().startsWith('custom_') ? g.name : g.id));
        }
        renderGames();
        updatePricingDropdowns();
    }

    function renderGames() {
        if (!gamesContainer) return;
        gamesContainer.innerHTML = '';
        selectedGames.forEach(g => {
            const chip = document.createElement('span');
            chip.className = 'chip active' + (lastAddedGameId === g.id ? ' chip-just-added' : '');
            chip.textContent = g.name;
            chip.dataset.id = g.id;
            const remove = document.createElement('span');
            remove.className = 'remove';
            remove.textContent = '×';
            remove.addEventListener('click', (e) => { e.stopPropagation(); removeGame(g.id); });
            chip.appendChild(remove);
            gamesContainer.appendChild(chip);
            if (lastAddedGameId === g.id) {
                setTimeout(() => {
                    chip.classList.remove('chip-just-added');
                }, 700);
            }
        });
    }

    function updateGameSuggestions(query) {
        if (!gameSuggestionsList) return;
        const term = (query || '').toLowerCase();
        gameSuggestionsList.innerHTML = '';
        if (!term) { gameSuggestionsList.style.display = 'none'; return; }
        suggestionData = defaultGames.filter(g => 
            g.name.toLowerCase().includes(term) && 
            !selectedGames.some(sg => sg.name.toLowerCase() === g.name.toLowerCase())
        ).slice(0, 10);

        if (suggestionData.length === 0) { 
            gameSuggestionsList.style.display = 'none'; 
            return; 
        }

        suggestionData.forEach((g, i) => {
            const item = document.createElement('div');
            item.className = 'suggestion-item' + (i === activeSuggestionIndex ? ' active' : '');
            item.textContent = g.name;
            item.addEventListener('mouseenter', () => {
                activeSuggestionIndex = i;
                setActiveSuggestion(activeSuggestionIndex);
            });
            item.addEventListener('mousedown', (e) => {
                e.preventDefault();
                addGame(g.name);
                gameInput.value = '';
                gameSuggestionsList.style.display = 'none';
            });
            gameSuggestionsList.appendChild(item);
        });
        gameSuggestionsList.style.display = 'block';
    }

    function setActiveSuggestion(index) {
        const items = gameSuggestionsList ? Array.from(gameSuggestionsList.children) : [];
        items.forEach((el, i) => {
            if (i === index) el.classList.add('active');
            else el.classList.remove('active');
        });
    }

    // Initialize data
    async function fetchGames() {
        try {
            const res = await fetch('/games/get-profile-form-data/');
            const data = await res.json();
            if (data.success) {
                defaultGames = data.games || [];
                
                // If in Edit mode, pre-populate selectedGames from hidden input
                const existingVal = gamesHidden.value;
                if (existingVal && existingVal !== '[]') {
                    try {
                        const existingIds = JSON.parse(existingVal);
                        existingIds.forEach(id => {
                            const found = defaultGames.find(g => g.id == id);
                            if (found) {
                                selectedGames.push(found);
                            } else if (typeof id === 'string') {
                                // Assume it's a custom game name if it's a string not in defaultGames
                                selectedGames.push({ id: `custom_${id.replace(/\s+/g,'_')}`, name: id });
                            }
                        });
                        renderGames();
                    } catch (e) { console.error('Error parsing existing games:', e); }
                }
            }
        } catch (e) {
            console.error('Failed to fetch games:', e);
        }
    }
    fetchGames();

    if (gameInput) {
        gameInput.addEventListener('input', () => {
            activeSuggestionIndex = -1;
            updateGameSuggestions(gameInput.value);
        });

        gameInput.addEventListener('keydown', (e) => {
            const listHidden = !gameSuggestionsList || gameSuggestionsList.style.display === 'none';
            if (listHidden) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    const val = (gameInput.value || '').trim();
                    if (val) addGame(val);
                    gameInput.value = '';
                    return;
                }
            } else {
                if (e.key === 'ArrowDown') {
                    e.preventDefault();
                    activeSuggestionIndex = (activeSuggestionIndex + 1) % suggestionData.length;
                    setActiveSuggestion(activeSuggestionIndex);
                } else if (e.key === 'ArrowUp') {
                    e.preventDefault();
                    activeSuggestionIndex = (activeSuggestionIndex - 1 + suggestionData.length) % suggestionData.length;
                    setActiveSuggestion(activeSuggestionIndex);
                } else if (e.key === 'Enter') {
                    e.preventDefault();
                    if (activeSuggestionIndex >= 0 && suggestionData[activeSuggestionIndex]) {
                        addGame(suggestionData[activeSuggestionIndex].name);
                    } else if (suggestionData.length > 0) {
                        addGame(suggestionData[0].name);
                    } else {
                        const val = (gameInput.value || '').trim();
                        if (val) addGame(val);
                    }
                    gameInput.value = '';
                    gameSuggestionsList.style.display = 'none';
                } else if (e.key === 'Escape') {
                    gameSuggestionsList.style.display = 'none';
                }
            }
        });

        gameInput.addEventListener('blur', () => {
            setTimeout(() => { 
                if (gameSuggestionsList) gameSuggestionsList.style.display = 'none'; 
            }, 200);
        });
    }

    // Initialize selectize only if element exists (deprecated now but keep for safety or remove)
    if ($('#gamesSelect').length) {
        $('#gamesSelect').hide(); // Hide the selectize target since we use custom UI
    }

    // Console management - Handled by checkboxes and inputs
    function updateConsolesData() {
        const consoles = [];
        document.querySelectorAll('.console-checkbox:checked').forEach(checkbox => {
            const slug = checkbox.value;
            const quantityInput = document.querySelector(`input[name="console_quantity_${slug}"]`);
            const quantity = quantityInput ? quantityInput.value : 1;
            
            consoles.push({
                type: slug,
                quantity: parseInt(quantity)
            });
        });
        const consolesHidden = document.getElementById('consoles');
        if (consolesHidden) {
            consolesHidden.value = JSON.stringify(consoles);
        }
    }

    // Delegate console events
    document.addEventListener('change', function(e) {
        if (e.target && e.target.classList.contains('console-checkbox')) {
            const checkbox = e.target;
            const slug = checkbox.value;
            const quantityInput = document.querySelector(`input[name="console_quantity_${slug}"]`);
            if (quantityInput) {
                quantityInput.disabled = !checkbox.checked;
                if (checkbox.checked && !quantityInput.value) {
                    quantityInput.value = 1;
                }
            }
            updateConsolesData();
        }
        
        if (e.target && e.target.classList.contains('quantity-input')) {
            updateConsolesData();
        }
    });

    document.addEventListener('input', function(e) {
        if (e.target && e.target.classList.contains('quantity-input')) {
            updateConsolesData();
        }
    });

    // Other consoles dropdown logic
    const otherConsolesDropdown = document.getElementById('otherConsolesDropdown');
    const addOtherConsoleBtn = document.getElementById('addOtherConsoleBtn');
    const selectedOtherConsolesList = document.getElementById('selectedOtherConsolesList');

    if (addOtherConsoleBtn && otherConsolesDropdown && selectedOtherConsolesList) {
        addOtherConsoleBtn.addEventListener('click', function() {
            const selectedOption = otherConsolesDropdown.options[otherConsolesDropdown.selectedIndex];
            const slug = selectedOption.value;
            const name = selectedOption.dataset.name;

            if (!slug) {
                showToast('Please select a platform first', 'info');
                return;
            }

            // Check if already in the list (either popular or already added to other)
            const existing = document.querySelector(`.console-checkbox-item[data-platform-slug="${slug}"]`);
            if (existing) {
                showToast(`${name} is already in the list`, 'info');
                return;
            }

            const item = document.createElement('div');
            item.className = 'console-checkbox-item other-console-item';
            item.dataset.platformSlug = slug;
            item.innerHTML = `
                <div class="console-info">
                    <label class="checkbox-label">
                        <input type="checkbox" name="console_types" value="${slug}" class="console-checkbox" checked>
                        <span class="checkmark"></span>
                        ${name}
                    </label>
                </div>
                <div class="console-quantity-input">
                    <input type="number" name="console_quantity_${slug}" 
                           min="1" value="1" class="form-control quantity-input">
                </div>
                <button type="button" class="btn btn-sm btn-outline-danger remove-other-console ms-2">
                    <i class="fas fa-times"></i>
                </button>
            `;

            selectedOtherConsolesList.appendChild(item);
            updateConsolesData();
            
            // Reset dropdown
            otherConsolesDropdown.value = '';
        });

        // Handle removal of other consoles
        selectedOtherConsolesList.addEventListener('click', function(e) {
            const removeBtn = e.target.closest('.remove-other-console');
            if (removeBtn) {
                const item = removeBtn.closest('.console-checkbox-item');
                item.remove();
                updateConsolesData();
            }
        });
    }

    // Initialize console data on load
    updateConsolesData();

    // Close suggestions on click outside
    document.addEventListener('click', (e) => {
        if (gameInput && !gameInput.contains(e.target) && gameSuggestionsList && !gameSuggestionsList.contains(e.target)) {
            gameSuggestionsList.style.display = 'none';
        }
    });

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
        const existingGamesList = [];
        
        // Use the newly selected games from search suggestions
        selectedGames.forEach(game => {
            existingGamesList.push({ id: game.id, name: game.name });
        });
        
        // Add custom games with temporary IDs (will be handled server-side)
        const customGamesList = customGames.map((game, index) => ({
            id: `custom_${index}`,
            name: game.name,
            isCustom: true
        }));
        
        return [...existingGamesList, ...customGamesList];
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

    // Add hidden inputs for consoles and pricing if they don't exist
    if (!document.getElementById('game_pricing')) {
        const pricingInput = document.createElement('input');
        pricingInput.type = 'hidden';
        pricingInput.name = 'game_pricing';
        pricingInput.id = 'game_pricing';
        pricingInput.value = '[]';
        document.getElementById('createShopForm').appendChild(pricingInput);
    }

    // Event listeners for add buttons
    document.getElementById('addPricingBtn')?.addEventListener('click', function() {
        addPricing();
    });

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