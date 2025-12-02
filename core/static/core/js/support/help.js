document.addEventListener('DOMContentLoaded', function() {
    initializeHelpCenter();
});

function initializeHelpCenter() {
    initializeSidebarNavigation();
    initializeHelpSearch();
    initializeResourceCards();
    initializeScrollSpy();
}

function initializeSidebarNavigation() {
    const navLinks = document.querySelectorAll('.help-sidebar .nav-link');
    
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            navLinks.forEach(l => l.classList.remove('active'));
            this.classList.add('active');
            
            const targetId = this.getAttribute('href');
            smoothScrollTo(targetId, 100);
        });
    });
}

function initializeHelpSearch() {
    const searchInput = document.querySelector('.help-search-input');
    
    if (searchInput) {
        searchInput.addEventListener('input', debounce(function(e) {
            const searchTerm = e.target.value.toLowerCase().trim();
            searchHelpContent(searchTerm);
        }, 300));
    }
}

function searchHelpContent(searchTerm) {
    const sections = document.querySelectorAll('.help-section');
    const resources = document.querySelectorAll('.help-resource-card');
    let foundResults = false;
    
    sections.forEach(section => {
        const sectionText = section.textContent.toLowerCase();
        const shouldShow = searchTerm === '' || sectionText.includes(searchTerm);
        
        if (shouldShow) {
            section.style.display = 'block';
            foundResults = true;
            
            if (searchTerm) {
                highlightText(section, searchTerm);
            }
        } else {
            section.style.display = 'none';
        }
    });
    
    resources.forEach(resource => {
        const resourceText = resource.textContent.toLowerCase();
        const shouldShow = searchTerm === '' || resourceText.includes(searchTerm);
        
        if (shouldShow) {
            resource.style.display = 'block';
            foundResults = true;
        } else {
            resource.style.display = 'none';
        }
    });
    
    toggleNoResultsMessage(!foundResults && searchTerm !== '');
}

function highlightText(element, searchTerm) {
    const existingHighlights = element.querySelectorAll('.search-highlight');
    existingHighlights.forEach(highlight => {
        const parent = highlight.parentNode;
        parent.replaceChild(document.createTextNode(highlight.textContent), highlight);
        parent.normalize();
    });
    
    if (searchTerm.length > 2) {
        const walker = document.createTreeWalker(
            element,
            NodeFilter.SHOW_TEXT,
            null,
            false
        );
        
        let node;
        while (node = walker.nextNode()) {
            const text = node.nodeValue;
            const regex = new RegExp(`(${searchTerm})`, 'gi');
            const newText = text.replace(regex, '<mark class="search-highlight">$1</mark>');
            
            if (newText !== text) {
                const newElement = document.createElement('span');
                newElement.innerHTML = newText;
                node.parentNode.replaceChild(newElement, node);
            }
        }
    }
}

function toggleNoResultsMessage(show) {
    let noResultsMessage = document.getElementById('noResultsMessage');
    
    if (show && !noResultsMessage) {
        noResultsMessage = document.createElement('div');
        noResultsMessage.id = 'noResultsMessage';
        noResultsMessage.className = 'alert alert-warning text-center mt-4';
        noResultsMessage.innerHTML = `
            <i class="fas fa-search me-2"></i>
            No results found. Try different keywords or
            <a href="/contact-us/" class="alert-link">contact support</a>.
        `;
        
        document.querySelector('.col-lg-9').appendChild(noResultsMessage);
    } else if (!show && noResultsMessage) {
        noResultsMessage.remove();
    }
}

function initializeResourceCards() {
    const resourceCards = document.querySelectorAll('.help-resource-card');
    
    resourceCards.forEach(card => {
        card.addEventListener('click', function() {
            const resourceType = this.getAttribute('data-resource-type');
            trackResourceView(resourceType, this.querySelector('.card-title').textContent);
        });
    });
}

function trackResourceView(resourceType, title) {
    console.log(`Resource viewed: ${resourceType} - ${title}`);
}

function initializeScrollSpy() {
    const sections = document.querySelectorAll('.help-section');
    const navLinks = document.querySelectorAll('.help-sidebar .nav-link');
    
    window.addEventListener('scroll', debounce(function() {
        let current = '';
        
        sections.forEach(section => {
            const sectionTop = section.offsetTop;
            if (window.pageYOffset >= sectionTop - 150) {
                current = section.getAttribute('id');
            }
        });
        
        navLinks.forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('href') === `#${current}`) {
                link.classList.add('active');
            }
        });
    }, 100));
}

function jumpToContact() {
    smoothScrollTo('#contact-section', 100);
}

function printHelpArticle() {
    window.print();
}