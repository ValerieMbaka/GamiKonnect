class AdminSettingsManager {
    constructor() {
        this.form = document.getElementById('siteSettingsForm');
        this.previewWindow = document.getElementById('livePreviewWindow');
        this.fontSelect = document.getElementById('fontFamily');
        
        // Color inputs maps: { cssVar: { color: elem, hex: elem } }
        this.colorInputs = {
            '--preview-primary': {
                color: document.getElementById('primaryColor'),
                hex: document.getElementById('primaryHex')
            },
            '--preview-bg': {
                color: document.getElementById('bgColor'),
                hex: document.getElementById('bgHex')
            },
            '--preview-text': {
                color: document.getElementById('textColor'),
                hex: document.getElementById('textHex')
            },
            '--preview-link': {
                color: document.getElementById('linkColor'),
                hex: document.getElementById('linkHex')
            },
            '--preview-btn-bg': {
                color: document.getElementById('btnBgColor'),
                hex: document.getElementById('btnBgHex')
            },
            '--preview-btn-text': {
                color: document.getElementById('btnTextColor'),
                hex: document.getElementById('btnTextHex')
            }
        };

        this.init();
    }

    init() {
        this.bindColorPickers();
        this.bindTypography();
        this.bindFormSubmit();
        
        // Initialize preview with current values
        this.updateAllPreviews();
    }

    bindColorPickers() {
        Object.entries(this.colorInputs).forEach(([cssVar, inputs]) => {
            if (!inputs.color || !inputs.hex) return;

            // When color picker changes
            inputs.color.addEventListener('input', (e) => {
                const val = e.target.value;
                inputs.hex.value = val.toUpperCase();
                this.updatePreviewVar(cssVar, val);
            });

            // When hex text input changes
            inputs.hex.addEventListener('input', (e) => {
                let val = e.target.value;
                if (!val.startsWith('#')) val = '#' + val;
                
                // Only update if it's a valid hex
                if (/^#[0-9A-F]{6}$/i.test(val) || /^#[0-9A-F]{3}$/i.test(val)) {
                    inputs.color.value = val;
                    this.updatePreviewVar(cssVar, val);
                }
            });
        });
    }

    bindTypography() {
        if (this.fontSelect) {
            this.fontSelect.addEventListener('change', (e) => {
                this.updatePreviewVar('--preview-font', e.target.value);
            });
        }
    }

    updatePreviewVar(cssVar, value) {
        if (this.previewWindow) {
            this.previewWindow.style.setProperty(cssVar, value);
        }
    }

    updateAllPreviews() {
        Object.entries(this.colorInputs).forEach(([cssVar, inputs]) => {
            if (inputs.color) {
                this.updatePreviewVar(cssVar, inputs.color.value);
            }
        });
        if (this.fontSelect) {
            this.updatePreviewVar('--preview-font', this.fontSelect.value);
        }
    }

    bindFormSubmit() {
        if (!this.form) return;

        this.form.addEventListener('submit', (e) => {
            e.preventDefault();
            const submitBtn = this.form.querySelector('button[type="submit"]');
            const originalHtml = submitBtn.innerHTML;
            
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> Saving...';
            submitBtn.disabled = true;

            // Simulate API Call for saving global settings
            setTimeout(() => {
                window.toastManager.success('Settings Saved', 'Global site style has been updated successfully.');
                submitBtn.innerHTML = originalHtml;
                submitBtn.disabled = false;
            }, 1200);
        });
    }
}

document.addEventListener('DOMContentLoaded', () => new AdminSettingsManager());