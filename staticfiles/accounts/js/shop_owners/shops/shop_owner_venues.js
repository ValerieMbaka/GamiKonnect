class VenueManager {
    constructor() {
        // Cache DOM elements
        this.searchInput = document.getElementById('venueSearch');
        this.filterBtns = document.querySelectorAll('.btn-filter');
        this.venueCols = document.querySelectorAll('.venue-card-col');
        this.noResultsMsg = document.getElementById('noSearchResults');
        
        // Initialize State
        this.currentFilter = 'all';
        this.currentSearch = '';

        // Only initialize if there are venues on the page
        if (this.venueCols.length > 0) {
            this.initEvents();
        }
    }

    // Bind all necessary event listeners
    initEvents() {
        // Bind search input
        if (this.searchInput) {
            this.searchInput.addEventListener('input', (e) => this.handleSearch(e));
        }

        // Bind filter buttons
        this.filterBtns.forEach(btn => {
            btn.addEventListener('click', (e) => this.handleFilterClick(e));
        });
    }

    // Handle search input changes
    handleSearch(e) {
        this.currentSearch = e.target.value.toLowerCase().trim();
        this.applyFilters();
    }

    // Handle filter button clicks
    handleFilterClick(e) {
        const clickedBtn = e.currentTarget;

        // Manage active class visual state
        this.filterBtns.forEach(b => b.classList.remove('active'));
        clickedBtn.classList.add('active');
        
        // Update state and apply
        this.currentFilter = clickedBtn.dataset.filter;
        this.applyFilters();
    }

    // Animation
    showElement(element) {
        element.classList.remove('d-none');
        element.style.animation = 'none';
        void element.offsetHeight;
        element.style.animation = 'fadeInUp 0.4s ease-out forwards';
    }

    // Hide element
    hideElement(element) {
        element.classList.add('d-none');
    }

    // Filtering
    applyFilters() {
        let visibleCount = 0;

        this.venueCols.forEach(col => {
            const status = col.dataset.status;
            const name = col.dataset.name;
            const location = col.dataset.location;
            
            // Evaluate conditions
            const matchesFilter = this.currentFilter === 'all' || status === this.currentFilter;
            const matchesSearch = this.currentSearch === '' ||
                                  name.includes(this.currentSearch) ||
                                  location.includes(this.currentSearch);

            // Apply visibility
            if (matchesFilter && matchesSearch) {
                this.showElement(col);
                visibleCount++;
            } else {
                this.hideElement(col);
            }
        });

        // Handle empty state messaging
        if (this.noResultsMsg) {
            if (visibleCount === 0) {
                this.noResultsMsg.classList.remove('d-none');
            } else {
                this.noResultsMsg.classList.add('d-none');
            }
        }
    }
}

// Instantiate the class when the DOM is fully loaded
document.addEventListener('DOMContentLoaded', () => {
    new VenueManager();
});