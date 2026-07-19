class ScrollToTop {
    constructor() {
        this.backToTop = document.getElementById('backToTop');
        if (this.backToTop) this.init();
    }

    init() {
        window.addEventListener('scroll', () => this.toggleButton());
        this.backToTop.addEventListener('click', (e) => this.scrollToTop(e));
    }

    toggleButton() {
        if (window.pageYOffset > 300) {
            this.backToTop.classList.add('active');
        } else {
            this.backToTop.classList.remove('active');
        }
    }

    scrollToTop(e) {
        e.preventDefault();
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
}

class SmoothScroller {
    constructor() {
        this.links = document.querySelectorAll('a[href^="#"]');
        if (this.links.length) this.init();
    }

    init() {
        this.links.forEach(link => {
            link.addEventListener('click', (e) => this.handleClick(e, link));
        });
    }

    handleClick(e, link) {
        const targetId = link.getAttribute('href');
        if (targetId === '#') return;
        
        const targetElement = document.querySelector(targetId);
        if (targetElement) {
            e.preventDefault();
            window.scrollTo({
                top: targetElement.offsetTop - 80,
                behavior: 'smooth'
            });
        }
    }
}

class SiteStyleManager {
    constructor() {
        this.body = document.body;
        if (this.body) this.applySiteStyles();
    }

    applySiteStyles() {
        const mappings = [
            ['siteFont', '--site-font', (value) => `${value}, sans-serif`],
            ['siteColor', '--site-color'],
            ['siteFontSize', '--site-font-size'],
            ['siteBg', '--site-bg'],
            ['siteLink', '--site-link'],
            ['siteBtnBg', '--site-btn-bg'],
            ['siteBtnText', '--site-btn-text'],
            ['sitePrimary', '--site-primary'],
            ['siteSecondary', '--site-secondary']
        ];

        mappings.forEach(([datasetKey, cssVar, formatter]) => {
            const value = this.body.dataset[datasetKey];
            if (!value) return;
            const finalValue = formatter ? formatter(value) : value;
            this.body.style.setProperty(cssVar, finalValue);
        });
    }
}

class ThemeManager {
    constructor() {
        this.themeToggle = document.getElementById('themeToggle');
        this.lightIcon = document.getElementById('lightIcon');
        this.darkIcon = document.getElementById('darkIcon');
        this.html = document.documentElement;
        
        if (this.themeToggle) this.init();
    }

    init() {
        const savedTheme = localStorage.getItem('theme') || 'light';
        this.setTheme(savedTheme);
        this.themeToggle.addEventListener('click', () => this.toggleTheme());
    }

    setTheme(theme) {
        this.html.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
        this.updateIcons(theme);
    }

    toggleTheme() {
        const currentTheme = this.html.getAttribute('data-theme') || 'light';
        this.setTheme(currentTheme === 'dark' ? 'light' : 'dark');
    }

    updateIcons(theme) {
        if (!this.lightIcon || !this.darkIcon) return;
        const isDark = theme === 'dark';
        this.lightIcon.classList.toggle('d-none', isDark);
        this.darkIcon.classList.toggle('d-none', !isDark);
    }
}

class TooltipManager {
    constructor() {
        this.tooltips = [];
        this.init();
    }

    init() {
        if (typeof bootstrap === 'undefined') return;

        // Select both modern BS5 attributes, legacy BS4 attributes, and general title tooltips
        const tooltipElements = document.querySelectorAll('[data-bs-toggle="tooltip"], [data-toggle="tooltip"]');
        
        this.tooltips = Array.from(tooltipElements).map(el => {
            // Auto-upgrade legacy data-toggle attributes to data-bs-toggle so Bootstrap 5 recognizes them
            if (el.hasAttribute('data-toggle') && !el.hasAttribute('data-bs-toggle')) {
                el.setAttribute('data-bs-toggle', 'tooltip');
            }
            
            return new bootstrap.Tooltip(el, {
                trigger: 'hover',     // Ensures tooltips disappear after clicking
                boundary: 'window',   // Prevents tooltips from getting clipped inside a scrolling sidebar
                animation: true
            });
        });
    }

    hideAll() {
        this.tooltips.forEach(tooltip => tooltip.hide());
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.appComponents = {
        siteStyleManager: new SiteStyleManager(),
        scrollToTop: new ScrollToTop(),
        smoothScroller: new SmoothScroller(),
        themeManager: new ThemeManager(),
        tooltipManager: new TooltipManager() // Added here
    };
});