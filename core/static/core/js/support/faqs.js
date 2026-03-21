class FAQManager {
    constructor() {
        this.init();
    }

    init() {
        this.initializeFAQSearch();
        this.initializeCategoryFilter();
        this.initializeAccordionEnhancements();
        this.initializeQuickStats();
        window.resetFAQFilters = () => this.resetFilters();
    }

    initializeFAQSearch() {
        const searchInput = document.getElementById('faqSearch');
        if (searchInput) {
            searchInput.addEventListener('input', LegalUtils.debounce((e) => {
                this.filterFAQs(e.target.value.toLowerCase().trim());
            }, 300));
        }
    }

    filterFAQs(searchTerm) {
        const faqItems = document.querySelectorAll('.accordion-item');
        let visibleCount = 0;

        faqItems.forEach(item => {
            const text = item.textContent.toLowerCase();
            const shouldShow = searchTerm === '' || text.includes(searchTerm);

            if (shouldShow) {
                item.classList.remove('faq-hidden');
                visibleCount++;

                if (searchTerm.length > 2) {
                    const collapse = item.querySelector('.accordion-collapse');
                    const button = item.querySelector('.accordion-button');

                    if (collapse && collapse.classList.contains('collapse') && button) {
                        if (typeof bootstrap !== 'undefined') {
                            new bootstrap.Collapse(collapse, { show: true });
                        } else {
                            collapse.classList.add('show');
                            button.classList.remove('collapsed');
                        }
                    }
                }
            } else {
                item.classList.add('faq-hidden');
            }
        });

        this.updateSearchResultsCount(visibleCount, faqItems.length);
    }

    updateSearchResultsCount(visible, total) {
        let resultsCounter = document.getElementById('faqResultsCounter');
        
        if (!resultsCounter) {
            resultsCounter = document.createElement('div');
            resultsCounter.id = 'faqResultsCounter';
            resultsCounter.className = 'text-center text-muted mt-3';
            document.querySelector('.faq-search-container').appendChild(resultsCounter);
        }

        if (visible === total) {
            resultsCounter.textContent = `Showing all ${total} FAQs`;
            resultsCounter.classList.remove('text-primary', 'fw-bold');
        } else {
            resultsCounter.textContent = `Showing ${visible} of ${total} FAQs`;
            resultsCounter.classList.add('text-primary', 'fw-bold');
        }
    }

    initializeCategoryFilter() {
        document.querySelectorAll('.faq-category-card').forEach(card => {
            card.addEventListener('click', (e) => {
                const category = e.currentTarget.getAttribute('data-category');
                this.filterByCategory(category, e.currentTarget);
            });
        });
    }

    filterByCategory(category, clickedCard) {
        document.querySelectorAll('.accordion-item').forEach(item => {
            const itemCategory = item.getAttribute('data-category');
            if (category === 'all' || itemCategory === category) {
                item.classList.remove('faq-hidden');
            } else {
                item.classList.add('faq-hidden');
            }
        });

        document.querySelectorAll('.faq-category-card').forEach(card => card.classList.remove('active'));
        if (clickedCard) clickedCard.classList.add('active');
    }

    initializeAccordionEnhancements() {
        document.querySelectorAll('.accordion-button').forEach(button => {
            button.addEventListener('click', (e) => {
                const faqId = e.currentTarget.closest('.accordion-item').getAttribute('data-faq-id');
                this.trackFAQOpen(faqId, e.currentTarget.textContent.trim());
            });
        });
    }

    trackFAQOpen(faqId, question) {
        console.log(`FAQ opened: ${faqId} - ${question}`);
    }

    initializeQuickStats() {
        document.querySelectorAll('.popular-faq-badge').forEach(badge => {
            const views = Math.floor(Math.random() * 1000) + 100;
            badge.textContent = `${views} views`;
        });
    }

    resetFilters() {
        const searchInput = document.getElementById('faqSearch');
        if (searchInput) searchInput.value = '';

        this.filterFAQs('');
        this.filterByCategory('all', null);
    }
}

document.addEventListener('DOMContentLoaded', () => new FAQManager());