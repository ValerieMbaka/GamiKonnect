class GamerGamesManager {
    constructor() {
        this.cacheDOM();
        if (this.gamesGrid || this.emptyState) {
            this.init();
        }
    }

    cacheDOM() {
        this.searchInput = document.getElementById('gamesSearch');
        this.platformFilter = document.getElementById('platformFilter');
        this.genreFilter = document.getElementById('genreFilter');
        this.gamesGrid = document.getElementById('gamesGrid');
        this.emptyState = document.getElementById('gamesEmptyState');
        this.clearFiltersBtn = document.getElementById('clearFiltersBtn');
        this.refreshBtn = document.getElementById('refreshGamesBtn');
        
        if (this.gamesGrid) {
            this.cards = Array.from(this.gamesGrid.querySelectorAll('.library-game-card'));
        } else {
            this.cards = [];
        }
    }

    init() {
        this.bindEvents();
        this.initializeGameImages();
    }

    bindEvents() {
        if (this.searchInput) {
            this.searchInput.addEventListener('input', () => {
                window.clearTimeout(this.searchDebounce);
                this.searchDebounce = setTimeout(() => this.applyFilters(), 200);
            });
        }

        if (this.platformFilter) this.platformFilter.addEventListener('change', () => this.applyFilters());
        if (this.genreFilter) this.genreFilter.addEventListener('change', () => this.applyFilters());

        if (this.clearFiltersBtn) {
            this.clearFiltersBtn.addEventListener('click', () => {
                if (this.searchInput) this.searchInput.value = '';
                if (this.platformFilter) this.platformFilter.value = 'all';
                if (this.genreFilter) this.genreFilter.value = 'all';
                this.applyFilters();
            });
        }

        if (this.refreshBtn) {
            this.refreshBtn.addEventListener('click', () => {
                this.applyFilters();
                window.scrollTo({ top: 0, behavior: 'smooth' });
                if(window.toastManager) window.toastManager.info('Refreshed', 'Library view updated.');
            });
        }
    }

    applyFilters() {
        const query = (this.searchInput?.value || '').toLowerCase().trim();
        let visibleCount = 0;

        this.cards.forEach(card => {
            const name = (card.dataset.name || '').toLowerCase();
            const matchesSearch = !query || name.includes(query);
            
            const shouldShow = matchesSearch; 
            
            card.style.display = shouldShow ? 'flex' : 'none';
            if (shouldShow) visibleCount++;
        });

        if (this.emptyState) {
            if (visibleCount === 0 && this.cards.length > 0) {
                this.emptyState.classList.remove('d-none');
            } else {
                this.emptyState.classList.add('d-none');
            }
        }
    }

    initializeGameImages() {
        const images = document.querySelectorAll('.game-banner-img');
        images.forEach(img => {
            const gameName = img.getAttribute('data-game');
            if (gameName) {
                img.src = this.getGameImage(gameName);
            }
        });
    }

    getGameImage(gameName) {
        const gameNameLower = gameName.toLowerCase();
        if (gameNameLower.includes('valorant') || gameNameLower.includes('csgo') || gameNameLower.includes('counter-strike')) return '/static/core/images/cod.jpeg';
        if (gameNameLower.includes('cod') || gameNameLower.includes('warzone')) return '/static/core/images/codwarzone.jpeg';
        if (gameNameLower.includes('fifa') || gameNameLower.includes('soccer')) return '/static/core/images/fc.jpeg';
        if (gameNameLower.includes('tekken') || gameNameLower.includes('fighting')) return '/static/core/images/tekken.jpeg';
        return '/static/core/images/gamepad.jpeg';
    }
}

document.addEventListener('DOMContentLoaded', () => new GamerGamesManager());