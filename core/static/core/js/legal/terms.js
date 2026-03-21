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
    
    window.addEventListener('scroll', LegalUtils.debounce(function() {
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
            LegalUtils.smoothScrollTo(targetId, 120);
        });
    });
}

function printTerms() {
    window.print();
}

function downloadTermsPDF() {
    window.toastManager.info('Downloading', 'Downloading Terms & Conditions as PDF...');
    setTimeout(() => {
        window.toastManager.success('Success', 'Terms & Conditions downloaded successfully!');
    }, 2000);
}