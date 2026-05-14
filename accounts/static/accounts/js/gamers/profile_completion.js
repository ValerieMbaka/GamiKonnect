class ProfileCompletionManager {
    constructor() {
        this.cacheDOM();
        
        if (this.form) {
            this.state = {
                selectedPlatforms: [],
                allPlatforms: [],
                selectedGames: [],
                defaultGames: [],
                lastAddedGameId: null,
                suggestionData: [],
                activeSuggestionIndex: -1,
                usernameRateLimitedUntil: 0
            };
            
            this.init();
        }
    }

    cacheDOM() {
        this.form = document.getElementById('profileForm');
        this.modal = document.getElementById('profileCompletionModal');
        
        this.fields = {
            custom_username: document.getElementById('id_custom_username'),
            bio: document.getElementById('id_bio'),
            about: document.getElementById('id_about'),
            date_of_birth: document.getElementById('id_date_of_birth'),
            location: document.getElementById('id_location'),
            platforms: document.getElementById('id_platforms'),
            games: document.getElementById('id_games')
        };
        
        this.ui = {
            aboutCounter: document.getElementById('aboutCounter'),
            generateBtn: document.getElementById('generateUsernameBtn'),
            usernameError: document.getElementById('custom_username-error'),
            platformsContainer: document.getElementById('platformsTags'),
            gamesContainer: document.getElementById('gamesTags'),
            gameInput: document.getElementById('gameInput'),
            gameSuggestionsList: document.getElementById('gameSuggestionsList'),
            dobDay: document.getElementById('dobDay'),
            dobMonth: document.getElementById('dobMonth'),
            dobYear: document.getElementById('dobYear'),
            profilePicInput: document.getElementById('id_profile_picture'),
            avatarPreview: document.getElementById('avatarPreview'),
            avatarPlaceholder: document.getElementById('avatarPlaceholder')
        };
    }

    init() {
        this.bindEvents();
        if (this.ui.platformsContainer && this.fields.platforms) {
            // Added .catch() to explicitly handle the ignored promise warning
            this.fetchFormData().catch(err => console.error('Initialization fetch error:', err));
        }
        if (this.ui.dobYear && this.ui.dobMonth && this.ui.dobDay) {
            this.populateYearDropdown();
        }
    }

    bindEvents() {
        if (this.form) this.form.addEventListener('submit', (e) => this.handleSubmit(e));
        
        if (this.fields.about) {
            this.fields.about.addEventListener('input', () => this.updateAboutCounter());
            this.updateAboutCounter();
        }

        if (this.fields.custom_username) {
            let timer;
            this.fields.custom_username.addEventListener('input', () => {
                clearTimeout(timer);
                timer = setTimeout(() => this.checkUsernameAvailability(), 400);
            });
            this.fields.custom_username.addEventListener('blur', () => this.checkUsernameAvailability());
        }

        if (this.ui.generateBtn) {
            this.ui.generateBtn.addEventListener('click', () => this.handleGenerateUsername());
        }

        if (this.ui.dobMonth) {
            this.ui.dobMonth.addEventListener('change', () => {
                this.populateDayDropdown();
                this.updateHiddenDate();
            });
        }
        if (this.ui.dobYear) {
            this.ui.dobYear.addEventListener('change', () => {
                this.populateDayDropdown();
                this.updateHiddenDate();
            });
        }
        if (this.ui.dobDay) {
            this.ui.dobDay.addEventListener('change', () => this.updateHiddenDate());
        }

        if (this.ui.gameInput) {
            this.ui.gameInput.addEventListener('input', () => this.updateGameSuggestions(this.ui.gameInput.value));
            this.ui.gameInput.addEventListener('keydown', (e) => this.handleGameInputKeyDown(e));
            this.ui.gameInput.addEventListener('blur', () => setTimeout(() => { this.ui.gameSuggestionsList.style.display = 'none'; }, 150));
        }

        if (this.ui.profilePicInput) {
            this.ui.profilePicInput.addEventListener('change', (e) => this.handleAvatarUpload(e));
        }
    }

    async safeFetchJson(url) {
        const res = await fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
        const text = await res.text();
        if (text.trim().startsWith('<')) return { success: false, html: true, status: res.status };
        try { return JSON.parse(text); } catch (e) { return { success: false, parse_error: true }; }
    }

    validateField(fieldName, isValid) {
        const err = document.getElementById(`${fieldName}-error`);
        if (err) {
            if (isValid) {
                err.textContent = '';
                err.classList.remove('show');
            } else {
                err.textContent = `${fieldName.replace('_', ' ')} is required`;
                err.classList.add('show');
            }
        }
        return isValid;
    }

    async fetchFormData() {
        try {
            /** @type {{success: boolean, html?: boolean, platform_categories?: Array<{id: string, name: string}>, games?: Array<{id: string, name: string}>}} */
            const data = await this.safeFetchJson('/games/get-profile-form-data/');
            
            if (!data.success) {
                window.toastManager.error('Data Error', data.html ? 'Session expired. Please log in again.' : 'Failed to load platforms/games.');
                return;
            }
            
            const cats = Array.isArray(data.platform_categories) ? data.platform_categories : [];
            this.state.allPlatforms = cats.reduce((acc, c) => {
                const name = (c.name || '').toLowerCase();
                if (['console', 'consoles'].includes(name)) {
                    acc.push({ id: 'console_ps', name: 'PlayStation' }, { id: 'console_xbox', name: 'Xbox' }, { id: 'console_switch', name: 'Nintendo Switch' });
                } else {
                    acc.push({ id: `cat_${c.id}`, name: c.name });
                }
                return acc;
            }, []);
            
            this.state.defaultGames = Array.isArray(data.games) ? data.games : [];
            this.renderPlatforms();
            this.renderGames();
        } catch (e) {
            window.toastManager.error('Network Error', 'Network error loading form data.');
        }
    }

    renderPlatforms() {
        if (!this.ui.platformsContainer) return;
        this.ui.platformsContainer.innerHTML = '';
        this.state.allPlatforms.forEach(p => {
            const chip = document.createElement('span');
            chip.className = `chip ${this.state.selectedPlatforms.includes(p.name) ? 'active' : ''}`;
            chip.textContent = p.name;
            chip.addEventListener('click', () => {
                if (this.state.selectedPlatforms.includes(p.name)) {
                    this.state.selectedPlatforms = this.state.selectedPlatforms.filter(k => k !== p.name);
                } else {
                    this.state.selectedPlatforms.push(p.name);
                }
                this.fields.platforms.value = JSON.stringify(this.state.selectedPlatforms);
                this.renderPlatforms();
                this.validateField('platforms', this.state.selectedPlatforms.length > 0);
            });
            this.ui.platformsContainer.appendChild(chip);
        });
        this.fields.platforms.value = JSON.stringify(this.state.selectedPlatforms);
    }

    renderGames() {
        if (!this.ui.gamesContainer) return;
        this.ui.gamesContainer.innerHTML = '';
        this.state.selectedGames.forEach(g => {
            const chip = document.createElement('span');
            chip.className = `chip active ${this.state.lastAddedGameId === g.id ? 'chip-just-added' : ''}`;
            chip.textContent = g.name;
            
            const remove = document.createElement('span');
            remove.className = 'remove';
            remove.textContent = '×';
            remove.addEventListener('click', (e) => {
                e.stopPropagation();
                this.state.selectedGames = this.state.selectedGames.filter(xg => xg.id !== g.id);
                if (this.fields.games) this.fields.games.value = JSON.stringify(this.state.selectedGames.map(x => x.name));
                this.renderGames();
            });
            
            chip.appendChild(remove);
            this.ui.gamesContainer.appendChild(chip);
            
            if (this.state.lastAddedGameId === g.id) {
                setTimeout(() => chip.classList.remove('chip-just-added'), 700);
            }
        });
    }

    updateAboutCounter() {
        if (this.ui.aboutCounter && this.fields.about) {
            this.ui.aboutCounter.textContent = `${this.fields.about.value.length}/500`;
        }
    }

    async checkUsernameAvailability() {
        const val = (this.fields.custom_username.value || '').trim();
        if (Date.now() < this.state.usernameRateLimitedUntil) return false;
        if (!/^[A-Za-z0-9_]{3,15}$/.test(val)) {
            this.ui.usernameError.textContent = 'Use 3–15 letters, numbers, or underscores';
            this.ui.usernameError.classList.add('show');
            return false;
        }

        try {
            const url = (this.form.dataset.checkUsernameUrl || '/accounts/check-username/') + '?username=' + encodeURIComponent(val);
            
            /** @type {{available: boolean, reason: string, retry_after?: number}} */
            const data = await this.safeFetchJson(url);
            
            if (data.reason === 'rate_limited') {
                this.state.usernameRateLimitedUntil = Date.now() + ((data.retry_after || 30) * 1000);
                window.toastManager.warning('Rate Limited', `Too many checks. Please wait ${data.retry_after}s.`);
                return false;
            }
            if (!data.available) {
                this.ui.usernameError.textContent = data.reason === 'invalid_format' ? 'Invalid format' : 'Username taken';
                this.ui.usernameError.classList.add('show');
                return false;
            }
            this.ui.usernameError.textContent = '';
            this.ui.usernameError.classList.remove('show');
            return true;
        } catch (e) {
            return false;
        }
    }

    async handleGenerateUsername() {
        this.ui.generateBtn.disabled = true;
        const oText = this.ui.generateBtn.textContent;
        this.ui.generateBtn.textContent = 'Generating...';
        
        const adjs = ['Swift','Nova','Crimson','Shadow','Aero','Frost','Blaze','Pixel'];
        const nouns = ['Ranger','Ninja','Falcon','Viper','Phoenix','Comet','Gamer'];
        let final = null;
        
        for (let i = 0; i < 5; i++) {
            const cand = `${adjs[Math.floor(Math.random()*adjs.length)]}${nouns[Math.floor(Math.random()*nouns.length)]}${Math.floor(Math.random()*999)}`.slice(0, 15);
            this.fields.custom_username.value = cand;
            if (await this.checkUsernameAvailability()) {
                final = cand; break;
            }
        }
        
        if (!final) window.toastManager.error('Generation Failed', 'Could not generate a unique username.');
        
        this.ui.generateBtn.disabled = false;
        this.ui.generateBtn.textContent = oText;
    }

    addGame(val) {
        if (!val || !val.trim()) return;
        const name = val.trim().toLowerCase();
        
        if (this.state.selectedGames.some(g => g.name.toLowerCase() === name)) {
            window.toastManager.info('Duplicate', 'Game already selected.');
            return;
        }

        const existing = this.state.defaultGames.find(g => g.name.toLowerCase() === name);
        if (existing) {
            this.state.selectedGames.push(existing);
            this.state.lastAddedGameId = existing.id;
        } else {
            const custom = { id: `custom_${name}`, name: val.trim() };
            this.state.selectedGames.push(custom);
            this.state.lastAddedGameId = custom.id;
        }
        
        if (this.fields.games) this.fields.games.value = JSON.stringify(this.state.selectedGames.map(x => x.name));
        this.validateField('games', this.state.selectedGames.length > 0);
        this.renderGames();
    }

    updateGameSuggestions(query) {
        if (!this.ui.gameSuggestionsList) return;
        const term = (query || '').toLowerCase();
        this.ui.gameSuggestionsList.innerHTML = '';
        
        if (!term) { this.ui.gameSuggestionsList.style.display = 'none'; return; }
        
        this.state.suggestionData = this.state.defaultGames.filter(g => g.name.toLowerCase().includes(term)).slice(0, 8);
        if (this.state.suggestionData.length === 0) { this.ui.gameSuggestionsList.style.display = 'none'; return; }
        
        this.state.suggestionData.forEach((g, i) => {
            const item = document.createElement('div');
            item.className = 'suggestion-item';
            item.textContent = g.name;
            item.addEventListener('mouseenter', () => {
                this.state.activeSuggestionIndex = i;
                Array.from(this.ui.gameSuggestionsList.children).forEach((el, idx) => el.classList.toggle('active', idx === i));
            });
            item.addEventListener('mousedown', (e) => {
                e.preventDefault();
                this.addGame(g.name);
                this.ui.gameInput.value = '';
                setTimeout(() => { this.ui.gameSuggestionsList.style.display = 'none'; }, 200);
            });
            this.ui.gameSuggestionsList.appendChild(item);
        });
        
        this.ui.gameSuggestionsList.style.display = 'block';
        this.state.activeSuggestionIndex = -1;
    }

    handleGameInputKeyDown(e) {
        const listHidden = !this.ui.gameSuggestionsList || this.ui.gameSuggestionsList.style.display === 'none';
        
        if (e.key === 'Enter') {
            e.preventDefault();
            if (!listHidden && this.state.activeSuggestionIndex >= 0 && this.state.suggestionData[this.state.activeSuggestionIndex]) {
                this.addGame(this.state.suggestionData[this.state.activeSuggestionIndex].name);
            } else if (!listHidden && this.state.suggestionData.length) {
                this.addGame(this.state.suggestionData[0].name);
            } else {
                this.addGame(this.ui.gameInput.value);
            }
            this.ui.gameInput.value = '';
            if (this.ui.gameSuggestionsList) this.ui.gameSuggestionsList.style.display = 'none';
        } else if (e.key === 'ArrowDown' && !listHidden) {
            e.preventDefault();
            this.state.activeSuggestionIndex = (this.state.activeSuggestionIndex + 1) % this.state.suggestionData.length;
            this.syncSuggestionHighlight();
        } else if (e.key === 'ArrowUp' && !listHidden) {
            e.preventDefault();
            this.state.activeSuggestionIndex = (this.state.activeSuggestionIndex - 1 + this.state.suggestionData.length) % this.state.suggestionData.length;
            this.syncSuggestionHighlight();
        } else if (e.key === 'Escape') {
            if (this.ui.gameSuggestionsList) this.ui.gameSuggestionsList.style.display = 'none';
        }
    }

    syncSuggestionHighlight() {
        Array.from(this.ui.gameSuggestionsList.children).forEach((el, idx) => {
            if (idx === this.state.activeSuggestionIndex) {
                el.classList.add('active');
                el.scrollIntoView({ block: 'nearest' });
            } else {
                el.classList.remove('active');
            }
        });
    }

    populateYearDropdown() {
        const curr = new Date().getFullYear();
        this.ui.dobYear.innerHTML = '<option value="">Year</option>';
        for (let i = curr - 13; i >= curr - 80; i--) {
            this.ui.dobYear.insertAdjacentHTML('beforeend', `<option value="${i}">${i}</option>`);
        }
    }

    populateDayDropdown() {
        const m = parseInt(this.ui.dobMonth.value);
        const y = parseInt(this.ui.dobYear.value);
        const currentDay = this.ui.dobDay.value;
        this.ui.dobDay.innerHTML = '<option value="">Date</option>';
        if (m && y) {
            const days = new Date(y, m, 0).getDate();
            for (let i = 1; i <= days; i++) {
                this.ui.dobDay.insertAdjacentHTML('beforeend', `<option value="${i}">${i}</option>`);
            }
            if (currentDay) this.ui.dobDay.value = currentDay;
        }
    }

    updateHiddenDate() {
        const d = this.ui.dobDay.value, m = this.ui.dobMonth.value, y = this.ui.dobYear.value;
        if (d && m && y) {
            this.fields.date_of_birth.value = `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
        } else {
            this.fields.date_of_birth.value = '';
        }
    }

    handleAvatarUpload(e) {
        const file = e.target.files[0];
        if (!file) return;
        if (!file.type.startsWith('image/')) { window.toastManager.error('Invalid File', 'Please select an image file.'); return; }
        if (file.size > 5 * 1024 * 1024) { window.toastManager.error('File Too Large', 'File size must be < 5MB.'); return; }
        
        const r = new FileReader();
        r.onload = (ev) => {
            this.ui.avatarPreview.src = ev.target.result;
            this.ui.avatarPreview.style.display = 'block';
            this.ui.avatarPlaceholder.style.display = 'none';
        };
        r.readAsDataURL(file);
    }

    async handleSubmit(e) {
        e.preventDefault();
        let ok = true;
        
        ok = (await this.checkUsernameAvailability()) && ok;
        
        const bio = (this.fields.bio.value || '').trim();
        if (bio.length < 5 || bio.length > 30) {
            this.validateField('bio', false); ok = false;
        } else { this.validateField('bio', true); }
        
        if (this.state.selectedPlatforms.length === 0) { this.validateField('platforms', false); ok = false; }
        if (this.state.selectedGames.length === 0) { this.validateField('games', false); ok = false; }
        
        const loc = (this.fields.location.value || '').trim();
        if (!loc) { this.validateField('location', false); ok = false; } else { this.validateField('location', true); }
        
        if (!this.fields.date_of_birth.value) {
            window.toastManager.error('Incomplete Date', 'Please select a complete date of birth.');
            if (!this.ui.dobDay.value) this.ui.dobDay.classList.add('error');
            if (!this.ui.dobMonth.value) this.ui.dobMonth.classList.add('error');
            if (!this.ui.dobYear.value) this.ui.dobYear.classList.add('error');
            ok = false;
        }
        
        if (!ok) {
            window.toastManager.error('Form Errors', 'Please correct form errors.');
            return;
        }

        try {
            window.toastManager.info('Processing', 'Saving profile details...');
            const formData = new FormData(this.form);
            const url = this.form.dataset.url || '/accounts/gamer-profile-completion/';
            
            const file = formData.get('profile_picture');
            let response, data;
            
            if (file && file.size > 0) {
                response = await fetch(url, { method: 'POST', body: formData, headers: { 'X-Requested-With': 'XMLHttpRequest' } });
            } else {
                const jsonPayload = {};
                formData.forEach((v, k) => {
                    try {
                        // Added strict type checking to resolve the FormData string IDE warning
                        jsonPayload[k] = ['platforms', 'games'].includes(k) && typeof v === 'string' ? JSON.parse(v) : v;
                    }
                    catch { jsonPayload[k] = v; }
                });
                const csrf = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
                response = await fetch(url, {
                    method: 'POST',
                    body: JSON.stringify(jsonPayload),
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf, 'X-Requested-With': 'XMLHttpRequest' }
                });
            }
            
            data = await response.json();
            
            if (response.ok && data.success) {
                localStorage.setItem('profileCompleted', 'true');
                window.toastManager.success('Success', 'Profile completed successfully!');
                if (this.modal) {
                    this.modal.classList.remove('show', 'mandatory');
                    this.modal.style.display = 'none';
                }
                setTimeout(() => window.location.reload(), 800);
            } else {
                window.toastManager.error('Update Failed', data.message || 'Error updating profile.');
            }
        } catch (err) {
            window.toastManager.error('Network Error', 'Network error. Please try again.');
        }
    }
}

document.addEventListener('DOMContentLoaded', () => new ProfileCompletionManager());