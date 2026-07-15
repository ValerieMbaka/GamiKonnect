/**
 * admin_competition_wizard.js
 * Drives the 4-step wizard on the admin "Create Competition" page.
 * Server-side Django form fields are grouped into steps; this script only
 * handles step navigation, client-side per-step validation, conditional
 * field visibility (virtual/physical, prize type), and the review summary.
 */

class AdminCompetitionWizard {
    constructor() {
        this.form = document.getElementById('adminCreateCompForm');
        if (!this.form) return;

        this.currentStep = 1;
        this.totalSteps = 4;

        this.steps = Array.from(this.form.querySelectorAll('.wizard-step'));
        this.indicators = Array.from(document.querySelectorAll('.step-indicator'));

        this.btnPrev = document.getElementById('btnPrev');
        this.btnNext = document.getElementById('btnNext');
        this.btnSubmit = document.getElementById('btnSubmit');

        this.typePhysical = document.getElementById('typePhysical');
        this.typeVirtual = document.getElementById('typeVirtual');
        this.shopField = document.getElementById('shopField');
        this.shopSelect = this.form.querySelector('[name="shop"]');
        this.gameSelect = this.form.querySelector('[name="game"]');
        this.platformSelect = this.form.querySelector('[name="platform"]');
        this.virtualLinkField = document.getElementById('virtualLinkField');
        this.virtualGuidelinesField = document.getElementById('virtualGuidelinesField');

        this.prizeTypeSelect = this.form.querySelector('[name="prize_type"]');
        this.prizePanels = {
            points: document.getElementById('prize-points'),
            money: document.getElementById('prize-money'),
            gift: document.getElementById('prize-gift'),
        };
        this.prizeHint = document.getElementById('prizeHint');

        this.summaryContainer = document.getElementById('summaryContainer');

        this.bindEvents();
        this.toggleCompType();
        this.updatePrizeFields();
        this.updateWizardUI();
    }

    bindEvents() {
        this.btnNext?.addEventListener('click', () => this.nextStep());
        this.btnPrev?.addEventListener('click', () => this.prevStep());

        this.typePhysical?.addEventListener('change', () => this.toggleCompType());
        this.typeVirtual?.addEventListener('change', () => this.toggleCompType());
        this.shopSelect?.addEventListener('change', () => this.loadShopResources());

        this.prizeTypeSelect?.addEventListener('change', () => this.updatePrizeFields());

        this.indicators.forEach((indicator) => {
            indicator.addEventListener('click', () => {
                const step = parseInt(indicator.dataset.step, 10);
                if (step < this.currentStep) this.goToStep(step);
            });
        });
    }

    toggleCompType() {
        const isVirtual = this.typeVirtual?.checked;
        const shopSelect = this.shopField?.querySelector('select');
        const linkInput = this.virtualLinkField?.querySelector('input');
        const guidelinesInput = this.virtualGuidelinesField?.querySelector('textarea');

        if (isVirtual) {
            if (this.shopField) this.shopField.style.display = 'none';
            if (this.virtualLinkField) this.virtualLinkField.style.display = 'block';
            if (this.virtualGuidelinesField) this.virtualGuidelinesField.style.display = 'block';
            shopSelect?.removeAttribute('required');
            linkInput?.setAttribute('required', 'required');
            guidelinesInput?.setAttribute('required', 'required');
        } else {
            if (this.shopField) this.shopField.style.display = 'block';
            if (this.virtualLinkField) this.virtualLinkField.style.display = 'none';
            if (this.virtualGuidelinesField) this.virtualGuidelinesField.style.display = 'none';
            shopSelect?.setAttribute('required', 'required');
            linkInput?.removeAttribute('required');
            guidelinesInput?.removeAttribute('required');
        }
    }

    updatePrizeFields() {
        const value = this.prizeTypeSelect?.value;
        Object.entries(this.prizePanels).forEach(([key, panel]) => {
            if (!panel) return;
            panel.style.display = key === value ? 'block' : 'none';
        });
        if (this.prizeHint) this.prizeHint.style.display = value ? 'none' : 'block';
    }

    async loadShopResources() {
        const shopId = this.shopSelect?.value;
        const url = this.form.dataset.resourcesUrl;
        
        if (!shopId || !url) {
            // Reset selects if no shop chosen
            this.updateSelectOptions(this.gameSelect, []);
            this.updateSelectOptions(this.platformSelect, []);
            return;
        }

        try {
            const response = await fetch(`${url}?shop_id=${shopId}`);
            if (!response.ok) throw new Error('Failed to fetch resources');
            
            const data = await response.json();
            
            this.updateSelectOptions(this.gameSelect, data.games);
            this.updateSelectOptions(this.platformSelect, data.platforms);
        } catch (error) {
            console.error('Error loading shop resources:', error);
        }
    }

    updateSelectOptions(select, items) {
        if (!select) return;
        
        // Keep the first option (placeholder)
        const firstOption = select.options[0];
        select.innerHTML = '';
        if (firstOption) select.appendChild(firstOption);
        
        items.forEach(item => {
            const option = document.createElement('option');
            option.value = item.id;
            option.textContent = item.name;
            select.appendChild(option);
        });
    }

    // --- Navigation ---

    currentStepEl() {
        return this.steps.find((s) => parseInt(s.dataset.step, 10) === this.currentStep);
    }

    validateCurrentStep() {
        const stepEl = this.currentStepEl();
        if (!stepEl) return true;

        let valid = true;
        const fields = stepEl.querySelectorAll('input, select, textarea');
        fields.forEach((field) => {
            if (field.offsetParent === null) return; // skip hidden fields
            if (!field.checkValidity()) {
                valid = false;
                field.reportValidity();
            }
        });
        return valid;
    }

    nextStep() {
        if (!this.validateCurrentStep()) return;
        if (this.currentStep < this.totalSteps) {
            if (this.currentStep === this.totalSteps - 1) this.buildSummary();
            this.currentStep += 1;
            this.updateWizardUI();
        }
    }

    prevStep() {
        if (this.currentStep > 1) {
            this.currentStep -= 1;
            this.updateWizardUI();
        }
    }

    goToStep(step) {
        this.currentStep = step;
        this.updateWizardUI();
    }

    updateWizardUI() {
        this.steps.forEach((step) => {
            step.classList.toggle('active', parseInt(step.dataset.step, 10) === this.currentStep);
        });

        this.indicators.forEach((indicator) => {
            const step = parseInt(indicator.dataset.step, 10);
            indicator.classList.toggle('active', step === this.currentStep);
            indicator.classList.toggle('completed', step < this.currentStep);
        });

        this.btnPrev?.classList.toggle('wizard-btn-hidden', this.currentStep === 1);
        this.btnNext?.classList.toggle('wizard-btn-hidden', this.currentStep === this.totalSteps);
        this.btnSubmit?.classList.toggle('wizard-btn-hidden', this.currentStep !== this.totalSteps);

        window.scrollTo({ top: this.form.offsetTop - 100, behavior: 'smooth' });
    }

    // --- Review Summary ---

    fieldValue(name) {
        const field = this.form.querySelector(`[name="${name}"]`);
        if (!field) return '';
        if (field.tagName === 'SELECT') {
            return field.options[field.selectedIndex]?.text?.trim() || '—';
        }
        if (field.type === 'checkbox') {
            return field.checked ? 'Yes' : 'No';
        }
        return field.value?.trim() || '—';
    }

    buildSummary() {
        if (!this.summaryContainer) return;

        const isVirtual = this.typeVirtual?.checked;
        const prizeType = this.prizeTypeSelect?.value;

        let prizeSummary = '';
        if (prizeType === 'points') {
            prizeSummary = `1st: ${this.fieldValue('points_1st')} pts · 2nd: ${this.fieldValue('points_2nd')} pts · 3rd: ${this.fieldValue('points_3rd')} pts`;
        } else if (prizeType === 'money') {
            prizeSummary = `Pool: KES ${this.fieldValue('prize_money_total')}`;
        } else if (prizeType === 'gift') {
            prizeSummary = this.fieldValue('prize_gift_description');
        } else {
            prizeSummary = 'Not configured';
        }

        this.summaryContainer.innerHTML = `
            <div class="summary-grid">
                <div class="summary-item"><span class="summary-label">Name</span><span class="summary-value">${this.fieldValue('name')}</span></div>
                <div class="summary-item"><span class="summary-label">Type</span><span class="summary-value">${isVirtual ? 'Virtual (Online)' : 'Physical (In-Shop)'}</span></div>
                <div class="summary-item"><span class="summary-label">${isVirtual ? 'Link' : 'Shop'}</span><span class="summary-value">${isVirtual ? this.fieldValue('platform_or_shop_link') : this.fieldValue('shop')}</span></div>
                <div class="summary-item"><span class="summary-label">Game</span><span class="summary-value">${this.fieldValue('game')}</span></div>
                <div class="summary-item"><span class="summary-label">Platform</span><span class="summary-value">${this.fieldValue('platform')}</span></div>
                <div class="summary-item"><span class="summary-label">Start Time</span><span class="summary-value">${this.fieldValue('scheduled_time')}</span></div>
                <div class="summary-item"><span class="summary-label">Registration Closes</span><span class="summary-value">${this.fieldValue('registration_closes_at')}</span></div>
                <div class="summary-item"><span class="summary-label">Capacity</span><span class="summary-value">${this.fieldValue('max_participants')}</span></div>
                <div class="summary-item"><span class="summary-label">Entry Fee</span><span class="summary-value">${this.fieldValue('entry_fee') || 'Free'}</span></div>
                <div class="summary-item summary-item--full"><span class="summary-label">Prize</span><span class="summary-value">${prizeSummary}</span></div>
            </div>
        `;
    }
}

document.addEventListener('DOMContentLoaded', () => new AdminCompetitionWizard());