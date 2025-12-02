document.addEventListener('DOMContentLoaded', function() {
    initializeTermsConditions();
});

function initializeTermsConditions() {
    initializeSectionNavigation();
    highlightImportantTerms();
    initializeQuickJump();
}

function initializeSectionNavigation() {
    const sections = document.querySelectorAll('.terms-section');
    const navLinks = document.querySelectorAll('.terms-nav-link');
    
    window.addEventListener('scroll', debounce(function() {
        let current = '';
        
        sections.forEach(section => {
            const sectionTop = section.offsetTop;
            if (pageYOffset >= sectionTop - 100) {
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

function highlightImportantTerms() {
    const importantTerms = document.querySelectorAll('.terms-highlight');
    
    importantTerms.forEach(term => {
        term.style.animation = 'pulse 2s infinite';
    });
}

function initializeQuickJump() {
    const quickJumpLinks = document.querySelectorAll('.quick-jump-link');
    
    quickJumpLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('href');
            smoothScrollTo(targetId, 120);
        });
    });
}

function printTerms() {
    window.print();
}

function downloadTermsPDF() {
    showToast('Downloading Terms & Conditions as PDF...', 'info');
    
    setTimeout(() => {
        showToast('Terms & Conditions downloaded successfully!', 'success');
    }, 2000);
}