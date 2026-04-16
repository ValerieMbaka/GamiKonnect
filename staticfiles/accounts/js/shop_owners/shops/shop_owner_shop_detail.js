class GameLibraryManager {
    constructor() {
        this.searchInput = document.getElementById('gameSearch');
        this.tableRows = Array.from(document.querySelectorAll('.game-row'));
        this.noResultsRow = document.getElementById('noSearchResultsRow');
        this.paginationInfo = document.getElementById('paginationInfo');
        this.prevBtn = document.getElementById('prevPageBtn');
        this.nextBtn = document.getElementById('nextPageBtn');

        this.itemsPerPage = 8;
        this.currentPage = 1;
        this.filteredRows = [...this.tableRows];

        if (this.tableRows.length > 0) {
            this.initEvents();
            this.renderPage();
        }
    }

    initEvents() {
        if (this.searchInput) {
            this.searchInput.addEventListener('input', (e) => this.handleSearch(e));
        }

        if (this.prevBtn && this.nextBtn) {
            this.prevBtn.addEventListener('click', () => this.changePage(-1));
            this.nextBtn.addEventListener('click', () => this.changePage(1));
        }
    }

    handleSearch(e) {
        const searchTerm = e.target.value.toLowerCase().trim();

        this.filteredRows = this.tableRows.filter(row => {
            const gameName = row.dataset.name || '';
            return gameName.includes(searchTerm);
        });

        this.currentPage = 1;
        this.renderPage();
    }

    changePage(direction) {
        const totalPages = Math.ceil(this.filteredRows.length / this.itemsPerPage);
        
        this.currentPage += direction;
        
        if (this.currentPage < 1) this.currentPage = 1;
        if (this.currentPage > totalPages) this.currentPage = totalPages;

        this.renderPage();
    }

    renderPage() {
        const totalItems = this.filteredRows.length;
        const totalPages = Math.ceil(totalItems / this.itemsPerPage);
        
        if (totalItems === 0) {
            this.tableRows.forEach(row => row.classList.add('d-none'));
            if (this.noResultsRow) this.noResultsRow.classList.remove('d-none');
            this.updatePaginationUI(0, 0, 0, 0);
            return;
        }

        if (this.noResultsRow) this.noResultsRow.classList.add('d-none');

        const startIndex = (this.currentPage - 1) * this.itemsPerPage;
        const endIndex = Math.min(startIndex + this.itemsPerPage, totalItems);

        this.tableRows.forEach(row => row.classList.add('d-none'));

        const rowsToShow = this.filteredRows.slice(startIndex, endIndex);
        rowsToShow.forEach(row => {
            row.classList.remove('d-none');
            row.style.animation = 'none';
            void row.offsetHeight;
            row.style.animation = 'fadeInUp 0.3s ease-out forwards';
        });

        this.updatePaginationUI(startIndex + 1, endIndex, totalItems, totalPages);
    }

    updatePaginationUI(start, end, total, totalPages) {
        if (!this.paginationInfo || !this.prevBtn || !this.nextBtn) return;

        if (total === 0) {
            this.paginationInfo.textContent = "No games found";
        } else {
            this.paginationInfo.textContent = `Showing ${start} to ${end} of ${total} games`;
        }

        if (this.currentPage <= 1 || total === 0) {
            this.prevBtn.setAttribute('disabled', 'true');
            this.prevBtn.classList.add('opacity-50');
        } else {
            this.prevBtn.removeAttribute('disabled');
            this.prevBtn.classList.remove('opacity-50');
        }

        if (this.currentPage >= totalPages || total === 0) {
            this.nextBtn.setAttribute('disabled', 'true');
            this.nextBtn.classList.add('opacity-50');
        } else {
            this.nextBtn.removeAttribute('disabled');
            this.nextBtn.classList.remove('opacity-50');
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new GameLibraryManager();
});