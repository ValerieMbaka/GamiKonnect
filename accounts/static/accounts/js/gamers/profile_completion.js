function getRandomLastPlayed() {
    const options = ['Today', 'Yesterday', '2d ago', '3d ago', '1w ago', '2w ago', '1m ago'];
    return options[Math.floor(Math.random() * options.length)];
}

function getGameImage(gameName) {
    const gameNameLower = gameName.toLowerCase();
    
    // FPS Games
    if (gameNameLower.includes('valorant') || gameNameLower.includes('csgo') || gameNameLower.includes('cs:go') || gameNameLower.includes('counter-strike')) {
        return '/static/core/images/cod.jpeg';
    }
    if (gameNameLower.includes('cod') || gameNameLower.includes('call of duty') || gameNameLower.includes('warzone')) {
        return '/static/core/images/codwarzone.jpeg';
    }
    if (gameNameLower.includes('cod mobile') || gameNameLower.includes('call of duty mobile')) {
        return '/static/core/images/codmobile.jpeg';
    }
    if (gameNameLower.includes('black ops')) {
        return '/static/core/images/codblackops.jpeg';
    }
    
    // Sports Games
    if (gameNameLower.includes('fifa') || gameNameLower.includes('football') || gameNameLower.includes('soccer')) {
        return '/static/core/images/fc.jpeg';
    }
    if (gameNameLower.includes('pes') || gameNameLower.includes('efootball') || gameNameLower.includes('pro evolution soccer')) {
        return '/static/core/images/pes.jpeg';
    }
    
    // Racing Games
    if (gameNameLower.includes('nfs') || gameNameLower.includes('need for speed')) {
        return '/static/core/images/nfs.jpeg';
    }
    if (gameNameLower.includes('racing') || gameNameLower.includes('asphalt')) {
        return '/static/core/images/racing.jpeg';
    }
    if (gameNameLower.includes('asphalt legends')) {
        return '/static/core/images/asphaltlegends.jpeg';
    }
    
    // Fighting Games
    if (gameNameLower.includes('tekken') || gameNameLower.includes('fighting')) {
        return '/static/core/images/tekken.jpeg';
    }
    
    // Battle Royale Games
    if (gameNameLower.includes('pubg') || gameNameLower.includes('playerunknown')) {
        return '/static/core/images/pubg.jpeg';
    }
    if (gameNameLower.includes('fortnite')) {
        return '/static/core/images/fortnite.jpeg';
    }
    if (gameNameLower.includes('freefire') || gameNameLower.includes('free fire')) {
        return '/static/core/images/freefire.jpeg';
    }
    
    // Mobile Games
    if (gameNameLower.includes('roblox')) {
        return '/static/core/images/roblox.jpeg';
    }
    if (gameNameLower.includes('dream league') || gameNameLower.includes('dream league soccer')) {
        return '/static/core/images/fc.jpeg';
    }
    
    // Action Games
    if (gameNameLower.includes('action') || gameNameLower.includes('adventure')) {
        return '/static/core/images/actiongame.jpeg';
    }
    
    // Default fallback
    return '/static/core/images/gamepad.jpeg';
}

document.addEventListener('DOMContentLoaded', function() {
    // Inject minimal styles for clearer selection feedback
    (function injectProfileCompletionStyles(){
        if (document.getElementById('pc-enhance-styles')) return;
        const style = document.createElement('style');
        style.id = 'pc-enhance-styles';
        style.textContent = `
            .game-suggestions .suggestion-item.selected { background: #e6ffed; border-left: 3px solid #22c55e; }
            .chips .chip.chip-just-added { box-shadow: 0 0 0 3px rgba(34,197,94,.25); transition: box-shadow .6s ease; }
            .game-suggestions { max-height: 220px; overflow-y: auto; }
            .game-suggestions .suggestion-item { padding: 8px 10px; cursor: pointer; transition: background .15s ease, color .15s ease; }
            .game-suggestions .suggestion-item:hover { background:#f0f7ff; }
            .game-suggestions .suggestion-item.active { background:#2563eb; color:#fff; }
            .game-suggestions .suggestion-item.active:hover { background:#1d4ed8; }
        `;
        document.head.appendChild(style);
    })();
    // Profile completion form handling
    const modal = document.getElementById('profileCompletionModal');
    const about = document.getElementById('id_about');
    
    // About counter
    const aboutCounter = document.getElementById('aboutCounter');
    const updateAboutCounter = () => { 
        if (aboutCounter) {
            const length = (about.value||'').length;
            aboutCounter.textContent = `${length}/500`;
            console.log('About counter updated:', length);
        }
    };
    if (about) { 
        about.addEventListener('input', updateAboutCounter); 
        updateAboutCounter(); 
    }
    
    // Username generator and availability check
    const usernameInput = document.getElementById('id_custom_username');
    const usernameError = document.getElementById('custom_username-error');
    const generateBtn = document.getElementById('generateUsernameBtn');
    const usernamePattern = /^[A-Za-z0-9_]{3,15}$/;
    const adjectives = ['Swift','Nova','Crimson','Shadow','Aero','Frost','Blaze','Quantum','Pixel','Hyper','Omega','Ultra'];
    const nouns = ['Ranger','Ninja','Falcon','Viper','Phoenix','Comet','Drifter','Guardian','Samurai','Spectre','Voyager','Gamer'];

    function generateUsernameCandidate() {
        const a = adjectives[Math.floor(Math.random()*adjectives.length)];
        const n = nouns[Math.floor(Math.random()*nouns.length)];
        const num = Math.floor(Math.random()*9999).toString().padStart(2,'0');
        let candidate = `${a}${n}${num}`;
        if (candidate.length > 15) candidate = candidate.slice(0, 15);
        return candidate;
    }
    
    // Platform selection
    const platformsContainer = document.getElementById('platformsTags');
    const platformsHidden = document.getElementById('id_platforms');
    let selectedPlatforms = [];
    let allPlatforms = [];

    function renderPlatforms() {
        if (!platformsContainer) return;
        platformsContainer.innerHTML = '';
        allPlatforms.forEach(p => {
            const chip = document.createElement('span');
            chip.className = 'chip' + (selectedPlatforms.includes(p.name) ? ' active' : '');
            chip.textContent = p.name;
            chip.dataset.id = p.id;
            chip.addEventListener('click', () => {
                if (selectedPlatforms.includes(p.name)) {
                    selectedPlatforms = selectedPlatforms.filter(k => k !== p.name);
                } else {
                    selectedPlatforms.push(p.name);
                }
                platformsHidden.value = JSON.stringify(selectedPlatforms);
                renderPlatforms();
                validateField('platforms', selectedPlatforms.length > 0);
            });
            platformsContainer.appendChild(chip);
        });
        platformsHidden.value = JSON.stringify(selectedPlatforms);
    }

    // Game selection
    const gamesContainer = document.getElementById('gamesTags');
    const gamesHidden = document.getElementById('id_games');
    const gameInput = document.getElementById('gameInput');
    let selectedGames = [];
    let defaultGames = [];
    let lastAddedGameId = null;

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
            const custom = { id: `custom_${gameName}`, name: value.trim() };
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
            gamesHidden.value = JSON.stringify(selectedGames.map(g => g.name));
        }
        validateField('games', selectedGames.length > 0);
        renderGames();
    }

    function renderGames() {
        if (!gamesContainer) return;
        gamesContainer.innerHTML = '';
        // Only render chips for games the user has explicitly selected
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

    // Safe JSON fetch (handles HTML redirect/error pages gracefully)
    async function safeFetchJson(url) {
        const res = await fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
        const text = await res.text();
        if (text.trim().startsWith('<')) {
            console.warn('Expected JSON but received HTML from', url);
            return { success: false, html: true, status: res.status };
        }
        try { return JSON.parse(text); } catch (e) { return { success: false, parse_error: true }; }
    }

    async function fetchFormData() {
        try {
            const data = await safeFetchJson('/games/get-profile-form-data/');
            if (!data.success) {
                if (data.html) {
                    showToast('Session expired or access blocked. Please log in again.', 'error');
                } else {
                    showToast('Failed to load platforms/games.', 'error');
                }
                return;
            }
            // Build from platform categories; replace Console category with specific console platforms
            const categories = Array.isArray(data.platform_categories) ? data.platform_categories : [];
            const built = [];
            categories.forEach(c => {
                const cname = (c.name || '').toLowerCase();
                if (cname === 'console' || cname === 'consoles') {
                    built.push({ id: 'console_ps', name: 'PlayStation' });
                    built.push({ id: 'console_xbox', name: 'Xbox' });
                    built.push({ id: 'console_switch', name: 'Nintendo Switch' });
                } else {
                    built.push({ id: `cat_${c.id}`, name: c.name });
                }
            });
            allPlatforms = built;
            defaultGames = Array.isArray(data.games) ? data.games : [];
            buildGameSuggestions();
            renderPlatforms();
            renderGames(); // compact rendering (only selected chips)
        } catch (error) {
            console.error('Error fetching form data:', error);
            showToast('Network error loading form data.', 'error');
        }
    }

    // Trigger initial data load
    if (platformsContainer && platformsHidden) {
        fetchFormData();
    }

    // Build datalist suggestions for game input (compact UI)
    function buildGameSuggestions() {
        const dl = document.getElementById('gameSuggestions');
        if (!dl) return;
        dl.innerHTML = '';
        defaultGames.slice(0,300).forEach(g => {
            const opt = document.createElement('option');
            opt.value = g.name;
            dl.appendChild(opt);
        });
    }

    // LinkedIn-style inline suggestions
    const gameSuggestionsList = document.getElementById('gameSuggestionsList');
    let suggestionData = [];
    let activeSuggestionIndex = -1;

    function setActiveSuggestion(index, autoScroll) {
        const items = gameSuggestionsList ? Array.from(gameSuggestionsList.children) : [];
        items.forEach((el,i) => {
            if (i === index) {
                el.classList.add('active');
                el.setAttribute('aria-selected','true');
                if (autoScroll) {
                    // Use scrollIntoView for reliable keyboard navigation without overriding manual scroll when hovering
                    el.scrollIntoView({ block: 'nearest' });
                }
            } else {
                el.classList.remove('active');
                el.setAttribute('aria-selected','false');
            }
        });
    }

    function updateGameSuggestions(query) {
        if (!gameSuggestionsList) return;
        const term = (query || '').toLowerCase();
        gameSuggestionsList.innerHTML = '';
        if (!term) { gameSuggestionsList.style.display = 'none'; return; }
        suggestionData = defaultGames.filter(g => g.name.toLowerCase().includes(term)).slice(0, 8);
        if (suggestionData.length === 0) { gameSuggestionsList.style.display = 'none'; return; }
        suggestionData.forEach((g, i) => {
            const item = document.createElement('div');
            item.className = 'suggestion-item';
            item.textContent = g.name;
            item.setAttribute('role','option');
            item.dataset.index = i;
            item.addEventListener('mouseenter', () => {
                activeSuggestionIndex = i;
                // Do not auto-scroll on hover to avoid jumpy scrollbar behavior
                setActiveSuggestion(activeSuggestionIndex, false);
            });
            item.addEventListener('mousedown', (e) => { // mousedown to fire before input blur
                e.preventDefault();
                item.classList.add('selected');
                item.textContent = `✓ ${g.name} added`;
                addGame(g.name);
                gameInput.value = '';
                setTimeout(() => { gameSuggestionsList.style.display = 'none'; }, 450);
            });
            gameSuggestionsList.appendChild(item);
        });
        gameSuggestionsList.style.display = 'block';
        activeSuggestionIndex = -1; // do not preselect first; user can arrow-down
        setActiveSuggestion(activeSuggestionIndex, false);
    }
    if (gameInput) {
        gameInput.addEventListener('input', () => updateGameSuggestions(gameInput.value));
        gameInput.addEventListener('keydown', (e) => {
            const listHidden = !gameSuggestionsList || gameSuggestionsList.style.display === 'none';
            if (listHidden) {
                if (e.key === 'ArrowDown') {
                    updateGameSuggestions(gameInput.value);
                    return;
                }
                if (e.key === 'Enter') {
                    e.preventDefault();
                    const val = (gameInput.value || '').trim();
                    if (val) { addGame(val); }
                    gameInput.value = '';
                    return;
                }
                if (e.key === 'Escape') { return; }
            }
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                if (suggestionData.length) {
                    activeSuggestionIndex = (activeSuggestionIndex + 1) % suggestionData.length;
                    setActiveSuggestion(activeSuggestionIndex, true);
                }
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                if (suggestionData.length) {
                    activeSuggestionIndex = (activeSuggestionIndex - 1 + suggestionData.length) % suggestionData.length;
                    setActiveSuggestion(activeSuggestionIndex, true);
                }
            } else if (e.key === 'Enter') {
                e.preventDefault();
                if (activeSuggestionIndex >= 0 && suggestionData[activeSuggestionIndex]) {
                    addGame(suggestionData[activeSuggestionIndex].name);
                } else if (suggestionData.length) {
                    addGame(suggestionData[0].name);
                } else {
                    const val = (gameInput.value || '').trim();
                    if (val) { addGame(val); }
                }
                gameInput.value = '';
                gameSuggestionsList.style.display = 'none';
            } else if (e.key === 'Escape') {
                gameSuggestionsList.style.display = 'none';
            }
        });
        gameInput.addEventListener('blur', () => setTimeout(() => { gameSuggestionsList.style.display = 'none'; }, 150));
    }

    // Re-add missing date helper functions (lost in previous merge)
    // Date of birth elements (ensure defined before helper functions)
    const dobDay = document.getElementById('dobDay');
    const dobMonth = document.getElementById('dobMonth');
    const dobYear = document.getElementById('dobYear');
    const dateOfBirthHidden = document.getElementById('id_date_of_birth');

    function populateYearDropdown() {
        if (!dobYear) return;
        const currentYear = new Date().getFullYear();
        const minYear = currentYear - 80;
        const maxYear = currentYear - 13;
        dobYear.innerHTML = '<option value="">Year</option>';
        for (let year = maxYear; year >= minYear; year--) {
            const option = document.createElement('option');
            option.value = year;
            option.textContent = year;
            dobYear.appendChild(option);
        }
    }
    function populateDayDropdown() {
        if (!dobDay || !dobMonth || !dobYear) return;
        const selectedMonth = parseInt(dobMonth.value);
        const selectedYear = parseInt(dobYear.value);
        const currentDay = dobDay.value;
        dobDay.innerHTML = '<option value="">Date</option>';
        if (selectedMonth && selectedYear) {
            const daysInMonth = new Date(selectedYear, selectedMonth, 0).getDate();
            for (let day = 1; day <= daysInMonth; day++) {
                const option = document.createElement('option');
                option.value = day;
                option.textContent = day;
                dobDay.appendChild(option);
            }
            if (currentDay) {
                dobDay.value = currentDay;
            }
        }
    }

    function updateHiddenDate() {
        if (!dobDay || !dobMonth || !dobYear || !dateOfBirthHidden) return;
        const day = dobDay.value;
        const month = dobMonth.value;
        const year = dobYear.value;

        if (day && month && year) {
            const formattedDate = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
            dateOfBirthHidden.value = formattedDate;
        } else {
            dateOfBirthHidden.value = '';
        }
    }

    if (dobDay && dobMonth && dobYear) {
        populateYearDropdown();
        dobMonth.addEventListener('change', () => {
            populateDayDropdown();
            updateHiddenDate();
        });
        dobYear.addEventListener('change', () => {
            populateDayDropdown();
            updateHiddenDate();
        });
        dobDay.addEventListener('change', updateHiddenDate);
    }
    
    // Avatar upload with preview functionality
    const profilePicInput = document.getElementById('id_profile_picture');
    const avatarPreview = document.getElementById('avatarPreview');
    const avatarPlaceholder = document.getElementById('avatarPlaceholder');

    if (profilePicInput && avatarPreview && avatarPlaceholder) {
        profilePicInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                if (!file.type.startsWith('image/')) {
                    showToast('Please select an image file.', 'error');
                    return;
                }
                if (file.size > 5 * 1024 * 1024) { // 5MB
                    showToast('File size must be less than 5MB.', 'error');
                    return;
                }
                const reader = new FileReader();
                reader.onload = function(event) {
                    avatarPreview.src = event.target.result;
                    avatarPreview.style.display = 'block';
                    avatarPlaceholder.style.display = 'none';
                };
                reader.readAsDataURL(file);
            }
        });
    }

    // Username availability check
    async function checkAvailability(username) {
        const value = username || (usernameInput.value || '').trim();
        console.log('Checking username availability for:', value);
        // Client-side cooldown if rate limited previously
        if (window.usernameRateLimitedUntil && Date.now() < window.usernameRateLimitedUntil) {
            console.log('Skipping availability check due to client cooldown');
            return false;
        }
        if (!usernamePattern.test(value)) {
            usernameError.textContent = 'Use 3–20 letters, numbers, or underscores';
            usernameError.classList.add('show');
            console.log('Username format invalid');
            return false;
        }
        try {
            // Get check username URL from form or use default
            const checkUsernameUrl = document.getElementById('profileForm')?.dataset.checkUsernameUrl || '/accounts/check-username/';
            const data = await safeFetchJson(checkUsernameUrl + '?username=' + encodeURIComponent(value));
            if (data.html) {
                showToast('Session expired. Please reload.', 'error');
                return false;
            }
            console.log('Username check response:', data);
            
            if (data.reason === 'rate_limited') {
                const retry = (data.retry_after || 30) * 1000;
                window.usernameRateLimitedUntil = Date.now() + retry;
                showToast('Too many username checks. Please wait ' + data.retry_after + 's.', 'warning');
                return false;
            }
            if (!data.available) {
                const errorMessage = data.reason === 'invalid_format' ? 'Invalid username format' : 'This username is already taken';
                usernameError.textContent = errorMessage;
                usernameError.classList.add('show');
                console.log('Username not available, error message:', errorMessage);
                return false;
            }
            usernameError.textContent = '';
            usernameError.classList.remove('show');
            console.log('Username is available');
            return true;
        } catch (e) {
            console.error('Error checking username availability:', e);
            return false;
        }
    }

    let usernameTimer;
    function debouncedCheck() {
        clearTimeout(usernameTimer);
        usernameTimer = setTimeout(() => checkAvailability(), 400);
    }

    if (usernameInput) {
        usernameInput.addEventListener('input', debouncedCheck);
        usernameInput.addEventListener('blur', () => checkAvailability());
    }
    if (generateBtn) {
        generateBtn.addEventListener('click', async () => {
            generateBtn.disabled = true;
            const originalText = generateBtn.textContent;
            generateBtn.textContent = 'Generating...';
            let finalCandidate = null;
            for (let i = 0; i < 10; i++) {
                const candidate = generateUsernameCandidate();
                // eslint-disable-next-line no-await-in-loop
                const ok = await checkAvailability(candidate);
                if (ok) { finalCandidate = candidate; break; }
            }
            if (finalCandidate) {
                usernameInput.value = finalCandidate;
                usernameError.textContent = '';
                usernameError.classList.remove('show');
            } else {
                showToast('Could not generate a unique username. Try manually.', 'error');
            }
            generateBtn.disabled = false;
            generateBtn.textContent = originalText;
        });
    }

    // Validation helpers
    const fields = {
        'custom_username': document.getElementById('id_custom_username'),
        'bio': document.getElementById('id_bio'),
        'date_of_birth': document.getElementById('id_date_of_birth'),
        'location': document.getElementById('id_location'),
        'platforms': document.getElementById('id_platforms'),
        'games': document.getElementById('id_games')
    };
    
    function validateField(fieldName, isValid) {
        const errorElement = document.getElementById(`${fieldName}-error`);
        if (errorElement) {
            if (isValid) {
                errorElement.textContent = '';
                errorElement.classList.remove('show');
            } else {
                errorElement.textContent = `${fieldName.replace('_', ' ')} is required`;
                errorElement.classList.add('show');
            }
        }
        return isValid;
    }
    
    function updateDashboardUI(data) {
        // Update avatar
        const profilePictures = document.querySelectorAll('.profile-avatar, .sidebar-avatar, .profile-main-avatar');
        profilePictures.forEach(img => {
            if (data.profile_picture_url) {
                img.src = data.profile_picture_url;
            }
        });
        
        // Update username displays
        const usernameElements = document.querySelectorAll('.profile-name, .username, .sidebar-profile-info h4');
        usernameElements.forEach(el => {
            el.textContent = data.username;
        });
        
        // Update bio/title
        const bioElements = document.querySelectorAll('.profile-title');
        bioElements.forEach(el => {
            el.textContent = data.bio && data.bio !== 'Bio' ? data.bio : 'Gaming Enthusiast';
        });
        
        // Update about text
        const aboutElements = document.querySelectorAll('.about-text');
        aboutElements.forEach(el => {
            el.textContent = data.about && data.about !== 'About' ? data.about : 'Gaming enthusiast passionate about competitive play and community building.';
        });
        
        // Update location
        const locationElements = document.querySelectorAll('.profile-location span');
        locationElements.forEach(el => {
            el.textContent = data.location && data.location !== 'Nairobi' ? data.location : 'Location not set';
        });
        
        // Update games in about section
        const gamesElements = document.querySelectorAll('.about-details .detail-item:has(i.fa-gamepad) strong');
        gamesElements.forEach(el => {
            if (data.games && data.games.length > 0) {
                el.textContent = data.games.join(', ');
            } else {
                el.textContent = 'No games added';
            }
        });
        
        // Update platforms in about section
        const platformsElements = document.querySelectorAll('.about-details .detail-item:has(i.fa-desktop) strong');
        platformsElements.forEach(el => {
            if (data.platforms && data.platforms.length > 0) {
                el.textContent = data.platforms.join(', ');
            } else {
                el.textContent = 'No platforms added';
            }
        });
        
        // Update games count in stats
        const gamesCountElements = document.querySelectorAll('.stats-grid-horizontal .communities .stat-value');
        gamesCountElements.forEach(el => {
            el.textContent = data.platforms ? data.platforms.length : 0;
        });
        
        // Update recent activity
        const activityElements = document.querySelectorAll('.activity-description');
        activityElements.forEach(el => {
            if (el.textContent.includes('Added') && data.games && data.games.length > 0) {
                el.textContent = `Added ${data.games.length} game${data.games.length > 1 ? 's' : ''} to your profile`;
            }
        });
        
        // Update activity stats
        const activityStatsElements = document.querySelectorAll('.activity-stats .activity-stat');
        activityStatsElements.forEach(el => {
            if (el.textContent.includes('Game')) {
                el.innerHTML = `<i class="fas fa-gamepad"></i><span>${data.games ? data.games.length : 0} Game${data.games && data.games.length > 1 ? 's' : ''}</span>`;
            } else if (el.textContent.includes('Platform')) {
                el.innerHTML = `<i class="fas fa-desktop"></i><span>${data.platforms ? data.platforms.length : 0} Platform${data.platforms && data.platforms.length > 1 ? 's' : ''}</span>`;
            }
        });
        
        // Update games tab content if it exists
        const gamesTabContent = document.querySelector('#games .game-carousel');
        if (gamesTabContent && data.games && data.games.length > 0) {
            gamesTabContent.innerHTML = data.games.map(game => `
                <div class="game-card">
                    <div class="game-status">Active</div>
                    <div class="platform-badges">
                        ${data.platforms ? data.platforms.slice(0, 3).map(platform => 
                            `<span class="platform-badge">${platform.toUpperCase()}</span>`
                        ).join('') : '<span class="platform-badge">PC</span>'}
                    </div>
                    <img src="${getGameImage(game)}" alt="${game}">
                    <div class="game-info">
                        <h4>${game}</h4>
                        <div class="game-stats">
                        <div class="stat-item hours" title="Total hours played">
                            <span class="stat-value">${Math.floor(Math.random() * 200) + 50}h</span>
                            <span class="stat-label">Hours</span>
                        </div>
                        <div class="stat-item win-rate" title="Win rate percentage">
                            <span class="stat-value">${Math.floor(Math.random() * 30) + 70}%</span>
                            <span class="stat-label">Win Rate</span>
                        </div>
                        <div class="stat-item achievements" title="Achievements unlocked">
                            <span class="stat-value">${Math.floor(Math.random() * 20) + 5}</span>
                            <span class="stat-label">Achievements</span>
                        </div>
                        <div class="stat-item last-played" title="Last time played">
                            <span class="stat-value">${getRandomLastPlayed()}</span>
                            <span class="stat-label">Last Played</span>
                        </div>
                        </div>
                    </div>
                </div>
            `).join('');
        }
        
        // Update empty states
        const emptyStates = document.querySelectorAll('.empty-state');
        emptyStates.forEach(emptyState => {
            if (emptyState.textContent.includes('No games added yet') && data.games && data.games.length > 0) {
                emptyState.style.display = 'none';
            }
        });
    }
    
    function repopulateFormFields(data) {
        console.log('Repopulating form fields with data:', data);
        if (fields.custom_username) {
            fields.custom_username.value = data.username || '';
        }
        if (fields.bio) {
            fields.bio.value = data.bio || '';
        }
        if (fields.location) {
            fields.location.value = data.location || '';
        }
      
        const aboutField = document.getElementById('id_about');
        if (aboutField) {
            aboutField.value = data.about || '';
        }
        
        const dobField = document.getElementById('id_date_of_birth');
        if (dobField && data.date_of_birth) {
            dobField.value = data.date_of_birth;
        }
        
        if (data.platforms) {
            selectedPlatforms = data.platforms;
            if (platformsContainer && platformsHidden) {
                renderPlatforms();
            }
        }
        
        if (data.games) {
            // Normalize stored names into game objects
            selectedGames = data.games.map(name => ({
                id: 'saved_' + name.toLowerCase().replace(/\s+/g,'_'),
                name: name
            }));
            if (gamesContainer && gamesHidden) {
                renderGames();
            }
        }
        
        console.log('Form fields repopulated with saved data');
    }

    function preventClose(e) {
        if (e.target === modal) {
            e.stopPropagation();
        }
    }
    
    // Submit
    const form = document.getElementById('profileForm');
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        let ok = true;
        ok = (await checkAvailability()) && ok;
        const bio = (fields.bio.value || '').trim();
        const bioError = document.getElementById('bio-error');
        if (bio.length < 5 || bio.length > 30) { 
            bioError.textContent = 'Bio must be 5–30 characters'; 
            bioError.classList.add('show');
            ok = false; 
        } else { 
            bioError.textContent = ''; 
            bioError.classList.remove('show');
        }
        const aboutVal = (about ? about.value : '').trim();
        if (aboutVal && (aboutVal.length < 5 || aboutVal.length > 200)) { showToast('About must be 5–200 characters if provided', 'error'); ok = false; }
        if (selectedPlatforms.length === 0) { validateField('platforms', false); ok = false; }
        if (selectedGames.length === 0) { validateField('games', false); ok = false; }
        
        const location = (fields.location.value || '').trim();
        const locationError = document.getElementById('location-error');
        if (!location || location === '') {
            if (locationError) {
                locationError.textContent = 'Please enter your location';
                locationError.classList.add('show');
            }
            ok = false;
        } else {
            if (locationError) {
                locationError.textContent = '';
                locationError.classList.remove('show');
            }
        }
        
        const day = dobDay.value;
        const month = dobMonth.value;
        const year = dobYear.value;
        
        if (!day || !month || !year || !dateOfBirthHidden.value || dateOfBirthHidden.value === '') {
            showToast('Please select a complete date of birth (day, month, and year).', 'error');
            
            // Highlight incomplete fields
            if (!day) dobDay.classList.add('error');
            if (!month) dobMonth.classList.add('error');
            if (!year) dobYear.classList.add('error');
            
            return;
        }
        
        if (!ok) {
            showToast('Please correct the errors in the form before submitting.', 'error');
            return;
        }
        
        const formData = new FormData(form);
       
        console.log('Form data being sent:');
        for (let [key, value] of formData.entries()) {
            console.log(`${key}: ${value}`);
        }
        
        try {
            showToast('Saving profile details...', 'info');
            
            // Convert FormData to JSON for profile completion
            const formDataObj = {};
            formData.forEach((value, key) => {
                if (key === 'platforms' || key === 'games') {
                    try {
                        formDataObj[key] = JSON.parse(value);
                    } catch (e) {
                        formDataObj[key] = value;
                    }
                } else {
                    formDataObj[key] = value;
                }
            });
            
            // Get URL from form data attribute or use default
            const profileCompletionUrl = form.dataset.url || '/accounts/gamer-profile-completion/';
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
            
            // Handle profile picture separately if it exists
            const profilePicture = formData.get('profile_picture');
            if (profilePicture && profilePicture.size > 0) {
                // For file upload, we'll need to use FormData
                const response = await fetch(profileCompletionUrl, {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-CSRFToken': csrfToken,
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });
                const data = await response.json();
                handleProfileResponse(data, response.ok);
            } else {
                // For JSON data without file
                const response = await fetch(profileCompletionUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken,
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    body: JSON.stringify(formDataObj)
                });
                const data = await response.json();
                handleProfileResponse(data, response.ok);
            }
        } catch (error) {
            console.error(error);
            showToast('Network error. Please try again.', 'error');
        }
    });
    
    function handleProfileResponse(data, isOk) {
        if (isOk && data.success) {
            // Store updated profile data
            localStorage.setItem('updatedProfile', JSON.stringify({
                profile_picture_url: data.profile_picture_url || '/static/core/images/player.jpeg',
                username: data.username || data.custom_username,
                custom_username: data.custom_username,
                bio: data.bio,
                about: data.about,
                location: data.location,
                platforms: data.platforms,
                games: data.games
            }));
            
            const modal = document.getElementById('profileCompletionModal');
            if (modal) {
                modal.classList.remove('show', 'mandatory');
                modal.style.display = 'none';
                modal.style.visibility = 'hidden';
                modal.style.opacity = '0';
                
                modal.removeEventListener('click', preventClose);
                
                console.log('Modal hidden successfully');
            }
            
            updateDashboardUI(data);
            repopulateFormFields(data);
            
            showToast('Profile completed successfully!', 'success');
            
            // Reload page to show updated dashboard
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            if (data.errors) {
                let errorMessages = [];
                for (const field in data.errors) {
                    const errorElement = document.getElementById(`${field}-error`);
                    if (errorElement) {
                        errorElement.textContent = data.errors[field][0];
                        errorElement.classList.add('show');
                        errorMessages.push(`${field}: ${data.errors[field][0]}`);
                    }
                }
                showToast(`Please correct the following errors: ${errorMessages.join(', ')}`, 'error');
            } else {
                showToast(data.message || 'Error updating profile. Please try again.', 'error');
            }
        }
    }
});