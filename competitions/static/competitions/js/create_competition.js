/**
 * create_competition.js
 * Handles the 3-Step Wizard for the competition creation standalone page.
 * Uses modern ES6 Class architecture and Unobtrusive JavaScript.
 */

class CompetitionWizard {
    constructor(createUrl) {
        this.createUrl = createUrl;
        this.currentStep = 1;
        this.totalSteps = 4;
        
        // Load data from the HTML5 Data Island
        this.loadDataIsland();

        // Cache DOM elements
        this.form = document.getElementById('createCompForm');
        this.shopSelect = document.getElementById('shopSelect');
        this.gameSelect = document.getElementById('gameSelect');
        this.platformSelect = document.getElementById('platformSelect');
        this.platformNote = document.getElementById('platformNote');
        
        this.scheduledTime = document.getElementById('scheduledTime');
        this.endTime = document.getElementById('endTime');
        this.durationDisplay = document.getElementById('durationDisplay');
        this.durationText = document.getElementById('durationText');
        
        this.ageToggle = document.getElementById('ageRestrictedToggle');
        this.ageToggleText = document.getElementById('ageToggleText');

        this.typePhysical = document.getElementById('typePhysical');
        this.typeVirtual = document.getElementById('typeVirtual');
        this.shopField = document.getElementById('shopField');
        this.virtualLinkField = document.getElementById('virtualLinkField');
        this.virtualGuidelinesField = document.getElementById('virtualGuidelinesField');
        this.summaryContainer = document.getElementById('summaryContainer');

        this.btnPrev = document.getElementById('btnPrev');
        this.btnNext = document.getElementById('btnNext');
        this.btnSubmit = document.getElementById('createCompSubmitBtn');

        // Initialize state and bind events
        this.init();
        this.bindEvents();
    }

// Replace the loadDataIsland() method in your create_competition.js with this:
loadDataIsland() {
        try {
            // Grab the native Django json_scripts by their IDs
            const gamesElement = document.getElementById('shopGamesData');
            const consolesElement = document.getElementById('shopConsolesData');

            this.serverData = {
                shopGames: gamesElement ? JSON.parse(gamesElement.textContent) : {},
                shopConsoles: consolesElement ? JSON.parse(consolesElement.textContent) : {}
            };
            
        } catch (error) {
            console.error('Failed to parse competition data islands:', error);
            this.serverData = { shopGames: {}, shopConsoles: {} };
        }
    }

    bindEvents() {
        // Wizard Navigation
        this.btnNext?.addEventListener('click', () => this.nextStep());
        this.btnPrev?.addEventListener('click', () => this.prevStep());
        
        // Prevent duplicate listener issues by cloning the submit button
        if (this.btnSubmit) {
            const newSubmitBtn = this.btnSubmit.cloneNode(true);
            this.btnSubmit.parentNode.replaceChild(newSubmitBtn, this.btnSubmit);
            this.btnSubmit = newSubmitBtn;
            this.btnSubmit.addEventListener('click', () => this.submit());
        }

        // Dynamic Form Logic
        this.shopSelect?.addEventListener('change', (e) => this.handleShopChange(e.target));
        this.gameSelect?.addEventListener('change', (e) => this.handleGameChange(e.target));
        
        this.scheduledTime?.addEventListener('change', () => this.validateSchedule());
        this.endTime?.addEventListener('change', () => this.validateSchedule());
        
        this.ageToggle?.addEventListener('change', (e) => this.handleAgeRestriction(e.target));

        this.typePhysical?.addEventListener('change', () => this.toggleCompType());
        this.typeVirtual?.addEventListener('change', () => this.toggleCompType());
    }

    toggleCompType() {
        const isVirtual = this.typeVirtual?.checked;
        if (isVirtual) {
            this.shopField.style.display = 'none';
            this.virtualLinkField.style.display = 'block';
            this.virtualGuidelinesField.style.display = 'block';
            this.shopSelect.removeAttribute('required');
            this.virtualLinkField.querySelector('input').setAttribute('required', 'required');
            this.virtualGuidelinesField.querySelector('textarea').setAttribute('required', 'required');
        } else {
            this.shopField.style.display = 'block';
            this.virtualLinkField.style.display = 'none';
            this.virtualGuidelinesField.style.display = 'none';
            this.shopSelect.setAttribute('required', 'required');
            this.virtualLinkField.querySelector('input').removeAttribute('required');
            this.virtualGuidelinesField.querySelector('textarea').removeAttribute('required');
        }
    }

    init() {
        this.updateWizardUI();

        // Set minimum datetime for start schedule to 'now'
        if (this.scheduledTime) {
            const now = new Date();
            now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
            this.scheduledTime.min = now.toISOString().slice(0, 16);
        }
    }

    // --- Wizard Navigation Logic ---

    updateWizardUI() {
        // Toggle Active Steps
        document.querySelectorAll('.wizard-step').forEach(step => {
            step.classList.toggle('active', parseInt(step.dataset.step) === this.currentStep);
        });

        // Toggle Progress Tracker Indicators
        document.querySelectorAll('.step-indicator').forEach(indicator => {
            const stepNum = parseInt(indicator.dataset.step);
            indicator.classList.remove('active', 'completed');
            
            if (stepNum === this.currentStep) {
                indicator.classList.add('active');
            } else if (stepNum < this.currentStep) {
                indicator.classList.add('completed');
            }
        });

        // Toggle Buttons
        this.btnPrev?.classList.toggle('wizard-btn-hidden', this.currentStep === 1);
        
        if (this.currentStep === this.totalSteps) {
            this.btnNext?.classList.add('wizard-btn-hidden');
            this.btnSubmit?.classList.remove('wizard-btn-hidden');
        } else {
            this.btnNext?.classList.remove('wizard-btn-hidden');
            this.btnSubmit?.classList.add('wizard-btn-hidden');
        }
    }

    nextStep() {
        if (!this.validateCurrentStep()) return;
        if (this.currentStep < this.totalSteps) {
            this.currentStep++;
            if (this.currentStep === 4) {
                this.updateSummary();
            }
            this.updateWizardUI();
        }
    }

    updateSummary() {
        const formData = new FormData(this.form);
        let summaryHtml = '<div class="row">';
        
        const fields = [
            { label: 'Name', name: 'name' },
            { label: 'Type', name: 'is_virtual', transform: (v) => v === 'true' ? 'Virtual' : 'Physical' },
            { label: 'Game', name: 'game', transform: () => this.gameSelect.options[this.gameSelect.selectedIndex].text },
            { label: 'Platform', name: 'platform', transform: () => this.platformSelect.options[this.platformSelect.selectedIndex].text },
            { label: 'Start Time', name: 'scheduled_time' },
            { label: 'End Time', name: 'competition_end_time' },
            { label: 'Capacity', name: 'max_participants' },
            { label: 'Entry Fee', name: 'entry_fee', transform: (v) => v ? `KES ${v}` : 'Free' },
        ];

        if (formData.get('is_virtual') === 'true') {
            fields.push({ label: 'Platform Link', name: 'platform_or_shop_link' });
        } else {
            fields.push({ label: 'Venue', name: 'shop', transform: () => this.shopSelect.options[this.shopSelect.selectedIndex].text });
        }

        fields.forEach(f => {
            const val = formData.get(f.name);
            const displayVal = f.transform ? f.transform(val) : val;
            summaryHtml += `
                <div class="col-md-6 mb-2">
                    <strong>${f.label}:</strong> <span>${displayVal || 'N/A'}</span>
                </div>
            `;
        });

        summaryHtml += '</div>';
        if (this.summaryContainer) this.summaryContainer.innerHTML = summaryHtml;
    }

    prevStep() {
        if (this.currentStep > 1) {
            this.currentStep--;
            this.updateWizardUI();
        }
    }

    validateCurrentStep() {
        let isValid = true;
        const currentStepEl = document.querySelector(`.wizard-step[data-step="${this.currentStep}"]`);
        const requiredInputs = currentStepEl.querySelectorAll('[required]');

        // Reset visual errors
        currentStepEl.querySelectorAll('.invalid-feedback').forEach(el => el.textContent = '');
        currentStepEl.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));

        // Check required fields
        requiredInputs.forEach(input => {
            // Special handling for checkboxes/switches if they were required
            if (input.type === 'checkbox') {
                if (!input.checked) {
                    input.classList.add('is-invalid');
                    isValid = false;
                }
            } else if (!input.value.trim()) {
                input.classList.add('is-invalid');
                const errEl = document.getElementById(`err-${input.name}`);
                if (errEl) errEl.textContent = 'This field is required.';
                isValid = false;
            }
        });

        // Step 2 specific schedule validation
        if (this.currentStep === 2) {
            const startStr = this.scheduledTime?.value;
            const endStr = this.endTime?.value;
            const now = new Date();
            
            if (startStr) {
                const startTime = new Date(startStr);
                const minStartTime = new Date(now.getTime() + (2 * 60 + 45) * 60 * 1000); // 2h 45m
                if (startTime < minStartTime) {
                    this.scheduledTime.classList.add('is-invalid');
                    document.getElementById('err-scheduled_time').textContent = `Start time must be at least 2h 45m from now (after ${minStartTime.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}).`;
                    isValid = false;
                }
            }
            if (startStr && endStr && new Date(endStr) <= new Date(startStr)) {
                this.endTime.classList.add('is-invalid');
                document.getElementById('err-competition_end_time').textContent = 'End time must be after start.';
                isValid = false;
            }
        }
        
        return isValid;
    }

    // --- Dynamic Form Handlers ---

    handleShopChange(selectElement) {
        const shopId = selectElement.value;
        this.gameSelect.innerHTML = '<option value="">Select a game...</option>';
        this.platformSelect.innerHTML = '<option value="">Select a game first...</option>';

        if (!shopId || !this.serverData) return;
        
        const shopGames = this.serverData.shopGames[shopId] || [];

        if (shopGames.length === 0) {
            this.gameSelect.innerHTML = '<option value="">No available games at this shop</option>';
            return;
        }

        shopGames.forEach(game => {
            const option = document.createElement('option');
            option.value = game.id;
            option.textContent = game.name;
            option.dataset.platforms = JSON.stringify(game.platforms);
            this.gameSelect.appendChild(option);
        });
    }

    handleGameChange(selectElement) {
        const gameId = selectElement.value;
        const shopId = this.shopSelect?.value;
        
        this.platformSelect.innerHTML = '<option value="">Select a platform...</option>';
        if (this.platformNote) this.platformNote.style.display = 'none';
        if (!gameId) return;

        const selectedOption = selectElement.options[selectElement.selectedIndex];
        let gamePlatforms = [];
        try {
            gamePlatforms = JSON.parse(selectedOption.dataset.platforms || '[]');
        } catch(e) {
            console.error("Failed to parse game platforms");
        }

        const shopConsoles = (shopId && this.serverData) ? (this.serverData.shopConsoles[shopId] || []) : [];
        
        // Intersect available game platforms with physical consoles in the shop
        const availablePlatforms = shopConsoles.length > 0
            ? gamePlatforms.filter(p => shopConsoles.includes(p.id))
            : gamePlatforms;

        if (availablePlatforms.length === 0) {
            this.platformSelect.innerHTML = '<option value="">No matching platforms at this shop</option>';
            if (this.platformNote) this.platformNote.style.display = 'block';
            return;
        }

        availablePlatforms.forEach(platform => {
            const option = document.createElement('option');
            option.value = platform.id;
            option.textContent = platform.name;
            this.platformSelect.appendChild(option);
        });
        
        if (this.platformNote) this.platformNote.style.display = 'block';
    }

    validateSchedule() {
        if (!this.scheduledTime?.value || !this.endTime?.value) return;

        const start = new Date(this.scheduledTime.value);
        const end = new Date(this.endTime.value);

        if (end > start) {
            const diffMs = end - start;
            const diffHrs = Math.floor(diffMs / (1000 * 60 * 60));
            const diffMins = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
            
            let durationStr = '';
            if (diffHrs > 0) durationStr += `${diffHrs}h `;
            if (diffMins > 0) durationStr += `${diffMins}m`;
            
            if (this.durationText) this.durationText.textContent = `Duration: ${durationStr.trim()}`;
            if (this.durationDisplay) this.durationDisplay.style.display = 'inline-block';
        } else {
            if (this.durationDisplay) this.durationDisplay.style.display = 'none';
        }
    }

    handleAgeRestriction(checkboxElement) {
        if (this.ageToggleText) {
            this.ageToggleText.textContent = checkboxElement.checked ? '18+ Required' : 'No Restriction';
        }
    }

    // --- Submission Handler ---

    async submit() {
        if (!this.validateCurrentStep()) return;

        const originalText = this.btnSubmit.innerHTML;
        this.btnSubmit.disabled = true;
        this.btnSubmit.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Submitting...';

        try {
            const formData = new FormData(this.form);
            
            // Ensure checkbox values are handled correctly for BooleanFields
            // If a checkbox is not checked, FormData doesn't include it.
            // Django's CheckboxInput expects 'on' or 'true' or presence for True, and absence for False.
            // However, when using JSON/AJAX, it's safer to explicitly set them if we want to be sure.
            // Since this is a standard form submit via fetch(formData), absence usually means False in Django for BooleanFields.
            
            const response = await fetch(this.createUrl, {
                method: 'POST',
                body: formData
            });
            const data = await response.json();

            if (data.success) {
                if (typeof showToast === 'function') showToast('success', data.message || 'Submitted successfully!');
                // REDIRECT back to the arena owner's competition dashboard
                setTimeout(() => window.location.href = '/competitions/manage/', 1500);
            } else {
                if (data.errors) {
                    Object.keys(data.errors).forEach(field => {
                        const errEl = document.getElementById(`err-${field}`);
                        if (errEl) errEl.textContent = Array.isArray(data.errors[field]) ? data.errors[field][0] : data.errors[field];
                    });
                }
                if (typeof showToast === 'function') showToast('error', data.message || 'Please fix the errors.');
                this.btnSubmit.disabled = false;
                this.btnSubmit.innerHTML = originalText;
            }
        } catch (err) {
            console.error('Submit error:', err);
            if (typeof showToast === 'function') showToast('error', 'Network error. Please try again.');
            this.btnSubmit.disabled = false;
            this.btnSubmit.innerHTML = originalText;
        }
    }
}

// --- AUTO INITIALIZATION FOR STANDALONE PAGE ---
document.addEventListener('DOMContentLoaded', () => {
    // Check if the form exists on the current page before firing
    if (document.getElementById('createCompForm')) {
        // Initialize the wizard.
        // Make sure the URL string matches the one configured in your urls.py for this action.
        new CompetitionWizard('/competitions/manage/create/');
    }
});