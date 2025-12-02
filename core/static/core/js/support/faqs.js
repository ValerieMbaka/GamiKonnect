document.addEventListener('DOMContentLoaded', function() {
    initializeFAQs();
});

function initializeFAQs() {
    initializeFAQSearch();
    initializeCategoryFilter();
    initializeAccordionEnhancements();
    initializeQuickStats();
}

function initializeFAQSearch() {
    const searchInput = document.getElementById('faqSearch');
    
    if (searchInput) {
        searchInput.addEventListener('input', debounce(function(e) {
            const searchTerm = e.target.value.toLowerCase().trim();
            filterFAQs(searchTerm);
        }, 300));
    }
}

function filterFAQs(searchTerm) {
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
    
    updateSearchResultsCount(visibleCount, faqItems.length);
}

function updateSearchResultsCount(visible, total) {
    let resultsCounter = document.getElementById('faqResultsCounter');
    
    if (!resultsCounter) {
        resultsCounter = document.createElement('div');
        resultsCounter.id = 'faqResultsCounter';
        resultsCounter.className = 'text-center text-muted mt-3';
        document.querySelector('.faq-search-container').appendChild(resultsCounter);
    }
    
    if (visible === total) {
        resultsCounter.textContent = `Showing all ${total} FAQs`;
    } else {
        resultsCounter.textContent = `Showing ${visible} of ${total} FAQs`;
        resultsCounter.classList.add('text-primary', 'fw-bold');
    }
}

function initializeCategoryFilter() {
    const categoryCards = document.querySelectorAll('.faq-category-card');
    
    categoryCards.forEach(card => {
        card.addEventListener('click', function() {
            const category = this.getAttribute('data-category');
            filterByCategory(category);
        });
    });
}

function filterByCategory(category) {
    const faqItems = document.querySelectorAll('.accordion-item');
    
    faqItems.forEach(item => {
        const itemCategory = item.getAttribute('data-category');
        const shouldShow = category === 'all' || itemCategory === category;
        
        if (shouldShow) {
            item.classList.remove('faq-hidden');
        } else {
            item.classList.add('faq-hidden');
        }
    });
    
    document.querySelectorAll('.faq-category-card').forEach(card => {
        card.classList.remove('active');
    });
    
    event.currentTarget.classList.add('active');
}

function initializeAccordionEnhancements() {
    const accordionButtons = document.querySelectorAll('.accordion-button');
    
    accordionButtons.forEach(button => {
        button.addEventListener('click', function() {
            const faqId = this.closest('.accordion-item').getAttribute('data-faq-id');
            trackFAQOpen(faqId, this.textContent.trim());
        });
    });
}

function trackFAQOpen(faqId, question) {
    console.log(`FAQ opened: ${faqId} - ${question}`);
}

function initializeQuickStats() {
    const popularItems = document.querySelectorAll('.popular-faq-badge');
    
    popularItems.forEach(badge => {
        const views = Math.floor(Math.random() * 1000) + 100;
        badge.textContent = `${views} views`;
    });
}

function resetFAQFilters() {
    const searchInput = document.getElementById('faqSearch');
    if (searchInput) searchInput.value = '';
    
    filterFAQs('');
    filterByCategory('all');
    
    document.querySelectorAll('.faq-category-card').forEach(card => {
        card.classList.remove('active');
    });
}