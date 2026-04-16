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
    }

    init() {
        // Apply custom classes to Django's text inputs
        this.djangoInputs.forEach(el => {
            el.classList.add('form-control');
        });

        // Initialize Hex Displays
        this.colorPickers.forEach(picker => {
            const hexDisplay = picker.nextElementSibling;
            if (hexDisplay) {
                hexDisplay.textContent = picker.value.toUpperCase();
            }
        });
    }

    bindEvents() {
        // Intercept file selection for live preview
        if (this.fileInput) {
            this.fileInput.addEventListener('change', (e) => this.handleLogoPreview(e));
        }

        // Live Hex updates
        this.colorPickers.forEach(picker => {
            picker.addEventListener('input', (e) => {
                const hexDisplay = e.target.nextElementSibling;
                if (hexDisplay) {
                    hexDisplay.textContent = e.target.value.toUpperCase();
                }
            });
        });

        // Loading state on save
        if (this.form && this.saveBtn) {
            this.form.addEventListener('submit', () => this.handleSubmission());
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