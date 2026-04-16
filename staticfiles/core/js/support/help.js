class HelpCenterManager {
    constructor() {
        this.init();
    }

    init() {
        this.initializeSidebarNavigation();
        this.initializeHelpSearch();
        this.initializeResourceCards();
        this.initializeScrollSpy();

        window.jumpToContact = () => LegalUtils.smoothScrollTo('#contact-section', 100);
        window.printHelpArticle = () => window.print();
    }

    initializeSidebarNavigation() {
        const navLinks = document.querySelectorAll('.help-sidebar .nav-link');
        navLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                navLinks.forEach(l => l.classList.remove('active'));
                e.currentTarget.classList.add('active');
                
                const targetId = e.currentTarget.getAttribute('href');
                LegalUtils.smoothScrollTo(targetId, 100);
            });
        });
    }

    initializeHelpSearch() {
        const searchInput = document.querySelector('.help-search-input');
        if (searchInput) {
            searchInput.addEventListener('input', LegalUtils.debounce((e) => {
                this.searchHelpContent(e.target.value.toLowerCase().trim());
            }, 300));
        }
    }

    searchHelpContent(searchTerm) {
        let foundResults = false;

        document.querySelectorAll('.help-section').forEach(section => {
            const sectionText = section.textContent.toLowerCase();
            if (searchTerm === '' || sectionText.includes(searchTerm)) {
                section.style.display = 'block';
                foundResults = true;
                if (searchTerm) this.highlightText(section, searchTerm);
            } else {
                section.style.display = 'none';
            }
        });

        document.querySelectorAll('.help-resource-card').forEach(resource => {
            const resourceText = resource.textContent.toLowerCase();
            if (searchTerm === '' || resourceText.includes(searchTerm)) {
                resource.style.display = 'block';
                foundResults = true;
            } else {
                resource.style.display = 'none';
            }
        });

        this.toggleNoResultsMessage(!foundResults && searchTerm !== '');
    }

    highlightText(element, searchTerm) {
        element.querySelectorAll('.search-highlight').forEach(highlight => {
            const parent = highlight.parentNode;
            parent.replaceChild(document.createTextNode(highlight.textContent), highlight);
            parent.normalize();
        });

        if (searchTerm.length > 2) {
            const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT, null, false);
            let node;
            const nodesToReplace = [];
            
            while (node = walker.nextNode()) {
                const text = node.nodeValue;
                const regex = new RegExp(`(${searchTerm})`, 'gi');
                if (regex.test(text)) {
                    nodesToReplace.push({ node, text });
                }
            }

            nodesToReplace.forEach(({ node, text }) => {
                const regex = new RegExp(`(${searchTerm})`, 'gi');
                const newText = text.replace(regex, '<mark class="search-highlight">$1</mark>');
                const newElement = document.createElement('span');
                newElement.innerHTML = newText;
                node.parentNode.replaceChild(newElement, node);
            });
        }
    }

    toggleNoResultsMessage(show) {
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
            const container = document.querySelector('.col-lg-9');
            if(container) container.appendChild(noResultsMessage);
        } else if (!show && noResultsMessage) {
            noResultsMessage.remove();
        }
    }

    initializeResourceCards() {
        document.querySelectorAll('.help-resource-card').forEach(card => {
            card.addEventListener('click', (e) => {
                const resourceType = e.currentTarget.getAttribute('data-resource-type');
                const title = e.currentTarget.querySelector('.card-title')?.textContent;
                this.trackResourceView(resourceType, title);
            });
        });
    }

    trackResourceView(resourceType, title) {
        console.log(`Resource viewed: ${resourceType} - ${title}`);
    }

    initializeScrollSpy() {
        const sections = document.querySelectorAll('.help-section');
        const navLinks = document.querySelectorAll('.help-sidebar .nav-link');

        window.addEventListener('scroll', LegalUtils.debounce(() => {
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
}

document.addEventListener('DOMContentLoaded', () => new HelpCenterManager());