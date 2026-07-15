class AdminSettingsController {
    constructor() {
        this.cacheDOM();
        this.init();
        this.bindEvents();
    }

    cacheDOM() {
        this.form = document.getElementById('siteSettingsForm');
        this.fileInput = document.querySelector('.django-hidden-file-input input[type="file"]');
        this.logoPreview = document.getElementById('logoPreview');
        this.colorPickers = document.querySelectorAll('.color-input-wrapper input[type="color"]');
        this.saveButtons = document.querySelectorAll('#saveSettingsBtn, #saveThemeBtn');
        this.djangoInputs = document.querySelectorAll('input[type="text"], input[type="number"], select, textarea');
        this.previewEl = document.getElementById('themePreviewInner');

        this.pageTabButtons = document.querySelectorAll('.page-tab-btn');
        this.pageTabPanels = document.querySelectorAll('.page-tab-panel');

        this.modalBackdrop = document.getElementById('modalBackdrop');
        this.modalOpenTriggers = document.querySelectorAll('[data-modal-open]');
        this.modalCloseTriggers = document.querySelectorAll('[data-modal-close]');
        this.modalPanels = document.querySelectorAll('.modal-panel');
    }

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
        this.djangoInputs.forEach(el => el.classList.add('form-control'));

        this.colorPickers.forEach(picker => {
            const hexDisplay = picker.nextElementSibling;
            if (hexDisplay) hexDisplay.textContent = picker.value.toUpperCase();
            this.applyPreviewColor(picker);
        });

        this.initDeepLink();
    }

    bindEvents() {
        if (this.fileInput) {
            this.fileInput.addEventListener('change', (e) => this.handleLogoPreview(e));
        }

        this.colorPickers.forEach(picker => {
            picker.addEventListener('input', (e) => {
                const hexDisplay = e.target.nextElementSibling;
                if (hexDisplay) hexDisplay.textContent = e.target.value.toUpperCase();
                this.applyPreviewColor(e.target);
            });
        });

        if (this.form) {
            this.form.addEventListener('submit', () => this.handleSubmission());
        }

        // Page-level tabs (Site Brand / Site Content)
        this.pageTabButtons.forEach(btn => {
            btn.addEventListener('click', () => this.activatePageTab(btn.dataset.pageTab));
        });

        // Modal open triggers
        this.modalOpenTriggers.forEach(btn => {
            btn.addEventListener('click', () => this.openModal(btn.dataset.modalOpen));
        });

        // Modal close triggers (buttons inside modals)
        this.modalCloseTriggers.forEach(btn => {
            btn.addEventListener('click', () => this.closeAllModals());
        });

        if (this.modalBackdrop) {
            this.modalBackdrop.addEventListener('click', () => this.closeAllModals());
        }

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') this.closeAllModals();
        });
    }

    activatePageTab(key) {
        this.pageTabButtons.forEach(btn => btn.classList.toggle('active', btn.dataset.pageTab === key));
        this.pageTabPanels.forEach(panel => panel.classList.toggle('active', panel.dataset.pagePanel === key));
    }

    openModal(id) {
        const panel = document.getElementById(id);
        if (!panel) return;
        this.closeAllModals();
        panel.classList.add('active');
        if (this.modalBackdrop) this.modalBackdrop.classList.add('active');
    }

    closeAllModals() {
        this.modalPanels.forEach(panel => panel.classList.remove('active'));
        if (this.modalBackdrop) this.modalBackdrop.classList.remove('active');
    }

    initDeepLink() {
        // Existing "Edit" links from content lists use ?section=<key>&object_id=<id>.
        // If present, switch to the Site Content tab and open that content type's modal.
        const params = new URLSearchParams(window.location.search);
        const requestedSection = params.get('section');
        if (!requestedSection) return;

        const modalId = `modalContent-${requestedSection}`;
        if (!document.getElementById(modalId)) return;

        this.activatePageTab('content');
        this.openModal(modalId);
    }

    applyPreviewColor(picker) {
        if (!this.previewEl) return;
        const group = picker.closest('.color-picker-group');
        const target = group ? group.dataset.previewTarget : null;
        const cssVar = target ? AdminSettingsController.PREVIEW_VAR_MAP[target] : null;
        if (cssVar) this.previewEl.style.setProperty(cssVar, picker.value);
    }

    handleLogoPreview(e) {
        const file = e.target.files[0];
        if (file && file.type.startsWith('image/')) {
            const reader = new FileReader();
            reader.onload = (event) => {
                if (this.logoPreview) this.logoPreview.src = event.target.result;
            };
            reader.readAsDataURL(file);
        }
    }

    handleSubmission() {
        this.saveButtons.forEach(btn => {
            btn.style.pointerEvents = 'none';
            btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> Deploying Configuration...';
        });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new AdminSettingsController();
});