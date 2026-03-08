document.addEventListener('DOMContentLoaded', function() {
    // Get all navigation links
    const navLinks = document.querySelectorAll('.nav-link');
    
    // Get current page URL
    const currentPath = window.location.pathname;
    
    // Remove active class from all links first
    navLinks.forEach(link => {
        link.classList.remove('active');
    });
    
    // Find and activate the current page link
    navLinks.forEach(link => {
        const href = link.getAttribute('href');
        
        // Check if the link matches the current page
        if (href && href !== '#' && currentPath.includes(href)) {
            link.classList.add('active');
        }
        
        // Special case for dashboard (home page)
        if (currentPath === '/' && href && href.includes('dashboard')) {
            link.classList.add('active');
        }
        
        // Special case for settings page
        if (currentPath.includes('settings') && href && href.includes('settings')) {
            link.classList.add('active');
        }
    });
    
    // Add click event listeners for manual activation
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            if (href && href !== '#' && !href.startsWith('http')) {
                // Remove active class from all links
                navLinks.forEach(navLink => {
                    navLink.classList.remove('active');
                });
                
                // Add active class to clicked link
                this.classList.add('active');
            }
        });
    });
});
