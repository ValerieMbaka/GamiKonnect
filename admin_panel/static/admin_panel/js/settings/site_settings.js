class AdminSettingsController {
    constructor() {
        this.cacheDOM();
        this.init();
        this.bindEvents();
    }

    cacheDOM() {
        this.form = document.getElementById('siteSettingsForm');
        // Target the actual file input hidden inside Django's rendered output
        this.fileInput = document.querySelector('.django-hidden-file-input input[type="file"]');
        this.logoPreview = document.getElementById('logoPreview');
        this.colorPickers = document.querySelectorAll('.color-input-wrapper input[type="color"]');
        this.saveBtn = document.getElementById('saveSettingsBtn');
        this.djangoInputs = document.querySelectorAll('input[type="text"], input[type="number"], select, textarea');
        this.previewEl = document.getElementById('themePreviewInner');
        this.tabButtons = document.querySelectorAll('.content-tab-btn');
        this.tabPanels = document.querySelectorAll('.content-tab-panel');
    }

    // Maps each color-picker-group's data-preview-target to the CSS custom
    // property read by site_settings.css on #themePreviewInner.
    static PREVIEW_VAR_MAP = {
        accent: '--preview-accent',
        secondary: '--preview-secondary',
        bg: '--preview-bg',
        text: '--preview-text',
        'btn-bg': '--preview-btn-bg',
        'btn-text': '--preview-btn-text',
        link: '--preview-link',
    };

    init() {
        // Apply custom classes to Django's text inputs
        this.djangoInputs.forEach(el => {
            el.classList.add('form-control');
        });

        // Initialize Hex Displays + seed the live preview with current values
        this.colorPickers.forEach(picker => {
            const hexDisplay = picker.nextElementSibling;
            if (hexDisplay) {
                hexDisplay.textContent = picker.value.toUpperCase();
            }
            this.applyPreviewColor(picker);
        });

        this.initTabs();
    }

    bindEvents() {
        // Intercept file selection for live preview
        if (this.fileInput) {
            this.fileInput.addEventListener('change', (e) => this.handleLogoPreview(e));
        }

        // Live Hex updates + live theme preview
        this.colorPickers.forEach(picker => {
            picker.addEventListener('input', (e) => {
                const hexDisplay = e.target.nextElementSibling;
                if (hexDisplay) {
                    hexDisplay.textContent = e.target.value.toUpperCase();
                }
                this.applyPreviewColor(e.target);
            });
        });

        // Loading state on save
        if (this.form && this.saveBtn) {
            this.form.addEventListener('submit', () => this.handleSubmission());
        }

        // Content Library tabs
        this.tabButtons.forEach(btn => {
            btn.addEventListener('click', () => this.activateTab(btn.dataset.tabKey));
        });
    }

    initTabs() {
        if (!this.tabButtons.length) return;

        // Deep-link support: ?section=<key> activates that tab (existing
        // "Edit" links from list items already use this query param).
        const params = new URLSearchParams(window.location.search);
        const requestedSection = params.get('section');

        if (requestedSection && [...this.tabButtons].some(b => b.dataset.tabKey === requestedSection)) {
            this.activateTab(requestedSection);
        }
    }

    activateTab(key) {
        this.tabButtons.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tabKey === key);
        });
        this.tabPanels.forEach(panel => {
            panel.classList.toggle('active', panel.dataset.tabKey === key);
        });
    }

    applyPreviewColor(picker) {
        if (!this.previewEl) return;

        const group = picker.closest('.color-picker-group');
        const target = group ? group.dataset.previewTarget : null;
        const cssVar = target ? AdminSettingsController.PREVIEW_VAR_MAP[target] : null;

        if (cssVar) {
            this.previewEl.style.setProperty(cssVar, picker.value);
        }
    }

    handleLogoPreview(e) {
        const file = e.target.files[0];
        
        if (file && file.type.startsWith('image/')) {
            const reader = new FileReader();
            
            reader.onload = (event) => {
                if (this.logoPreview) {
                    this.logoPreview.src = event.target.result;
                }
            };
            
            reader.readAsDataURL(file);
        }
    }

    handleSubmission() {
        if (this.saveBtn) {
            this.saveBtn.style.pointerEvents = 'none';
            this.saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> Deploying Configuration...';
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new AdminSettingsController();
});