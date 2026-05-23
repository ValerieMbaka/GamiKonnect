class CompetitionRegistration {
    constructor() {
        this.isProcessing = false;
        this.init();
    }

    init() {
        this.bindEvents();
    }

    bindEvents() {
        // Join competition button click
        document.addEventListener('click', (e) => {
            if (e.target.closest('.join-competition-btn')) {
                const button = e.target.closest('.join-competition-btn');
                const competitionId = button.dataset.competitionId;
                this.openRegistrationModal(competitionId);
            }
        });

        // Modal close events
        document.addEventListener('click', (e) => {
            if (e.target.closest('[data-action="close-modal"]') ||
                e.target.closest('[data-action="cancel-registration"]')) {
                this.closeRegistrationModal();
            }

            // Confirmation modal actions
            if (e.target.closest('[data-action="close-confirmation"]') ||
                e.target.closest('[data-action="cancel-payment"]')) {
                this.hideConfirmation();
            }

            // Confirm payment action
            if (e.target.id === 'confirmPaymentBtn') {
                const btn = e.target;
                if (btn.disabled) return;
                btn.disabled = true;
                btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
                const competitionId = btn.dataset.competitionId;
                this.hideConfirmation();
                this.closeRegistrationModal();
                this.processPayment(null, competitionId);
            }
        });

        // Form submission
        document.addEventListener('submit', (e) => {
            if (e.target.id === 'registrationForm') {
                e.preventDefault();
                const form = e.target;
                const terms = form.querySelector('#agreeTerms');
                if (!terms || !terms.checked) {
                    const err = document.getElementById('termsError');
                    if (err) err.style.display = 'block';
                    Toast.warning('Terms Required', 'You must agree to the terms and conditions.');
                    return;
                }
                // show confirmation modal
                this.showConfirmation();
            }
        });
    }

    async openRegistrationModal(competitionId) {
        try {
            // Check if user is already registered
            const status = await this.checkRegistrationStatus(competitionId);
            if (status.already_registered) {
                Toast.info('Already Registered', 'You are already registered for this competition!');
                return;
            }

            if (status.pending_payment) {
                Toast.info('Payment Pending', 'You already started registration. Complete payment to finalize your entry.');
            }

            // Load registration form
            await this.loadRegistrationForm(competitionId);
            this.showModal();
        } catch (error) {
            console.error('Error opening registration modal:', error);
            Toast.error('Error', 'Failed to load registration form. Please try again.');
        }
    }

    async checkRegistrationStatus(competitionId) {
        try {
            const response = await fetch(`/competitions/api/check-registration/${competitionId}/`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            return {
                already_registered: Boolean(data.already_registered),
                pending_payment: Boolean(data.pending_payment),
                payment_status: data.payment_status || null,
            };
        } catch (error) {
            console.error('Error checking registration status:', error);
            return {
                already_registered: false,
                pending_payment: false,
                payment_status: null,
            };
        }
    }

    async loadRegistrationForm(competitionId) {
        try {
            const modal = document.getElementById('registrationModal');
            const response = await fetch(`/competitions/${competitionId}/register/`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const html = await response.text();
            modal.innerHTML = html;
            
            // Show the loading overlay
            const loadedLoadingModal = modal.querySelector('#loadingModal');
            if (loadedLoadingModal) {
                document.body.appendChild(loadedLoadingModal);
            }
        } catch (error) {
            console.error('Error loading registration form:', error);
            Toast.error('Error', 'Failed to load registration form. Please try again.');
        }
    }

    showModal() {
        const modalBackdrop = document.getElementById('modalBackdrop');
        const registrationModal = document.getElementById('registrationModal');
        
        if (modalBackdrop) modalBackdrop.classList.remove('hidden');
        if (registrationModal) registrationModal.classList.remove('hidden');
        document.body.classList.add('modal-open');
    }

    closeRegistrationModal() {
        const modalBackdrop = document.getElementById('modalBackdrop');
        const registrationModal = document.getElementById('registrationModal');
        
        if (modalBackdrop) modalBackdrop.classList.add('hidden');
        if (registrationModal) registrationModal.classList.add('hidden');
        document.body.classList.remove('modal-open');
    }

    showConfirmation() {
        const modal = document.getElementById('confirmationModal');
        const backdrop = document.getElementById('modalBackdrop');
        if (modal) modal.classList.remove('hidden');
        if (backdrop) backdrop.classList.remove('hidden');
    }

    hideConfirmation() {
        const modal = document.getElementById('confirmationModal');
        if (modal) modal.classList.add('hidden');
    }

    showLoading() {
        const loading = document.getElementById('loadingModal');
        if (loading) loading.classList.remove('hidden');
        document.body.classList.add('modal-open');
    }

    hideLoading() {
        const loading = document.getElementById('loadingModal');
        if (loading) loading.classList.add('hidden');
        document.body.classList.remove('modal-open');
    }

    async processPayment(form, competitionId) {
        if (this.isProcessing) return;
        this.isProcessing = true;
        
        try {
            this.showLoading();

            const formData = new FormData();
            formData.set('agreeTerms', 'true');
            
            // Use form data if provided
            if (form) {
                const phoneInput = form.querySelector('#phoneNumber');
                if (phoneInput) formData.set('phone_number', phoneInput.value);
            } else {
                // Get the phone number from the registration modal
                const phoneInput = document.querySelector('#phoneNumber');
                if (phoneInput) formData.set('phone_number', phoneInput.value);
            }

            const response = await fetch(`/competitions/${competitionId}/register/`, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();

            if (result.success) {
                this.handleRegistrationSuccess(result);
            } else {
                this.handleRegistrationError(result.message || 'Registration failed. Please try again.');
            }
        } catch (error) {
            console.error('Registration error:', error);
            this.handleRegistrationError('Network error. Please check your connection and try again.');
        } finally {
            this.isProcessing = false;
        }
    }

    getCSRFToken() {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
        if (csrfToken) return csrfToken.value;
        
        const csrfCookie = document.cookie.split('; ').find(row => row.startsWith('csrftoken='));
        if (csrfCookie) return csrfCookie.split('=')[1];
        
        return '';
    }

    handleRegistrationSuccess(result) {
        if (result.payment_required) {
            this.initializePaystackPayment(result);
            return;
        }

        this.hideLoading();
        this.closeRegistrationModal();
        
        // Update the specific competition card
        if (window.competitionsManager) {
            window.competitionsManager.updateCompetitionCardState(result.competition_id, true);
        }
        
        // Show success toast with unique code
        if (typeof Toast !== 'undefined') {
            Toast.success(
                'Registration Successful! 🎉',
                `Welcome to "${result.competition_title}"! Your unique access code is: ${result.access_code}`
            );
        } else {
            alert(`Registration successful!\n\nYour unique access code: ${result.access_code}`);
        }
        
        console.log('Registration successful for competition:', result.competition_id);
        
        // Redirect to competition detail page after a short delay
        if (result.competition_slug) {
            setTimeout(() => {
                window.location.href = `/competitions/${result.competition_slug}/`;
            }, 3000); // Wait 3 seconds so user can read the toast
        } else if (result.competition_id) {
            setTimeout(() => {
                window.location.href = `/competitions/${result.competition_id}/`;
            }, 3000);
        }
    }

    async initializePaystackPayment(result) {
        try {
            const response = await fetch('/payments/api/initiate/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken(),
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({
                    registration_id: result.registration?.id,
                    phone_number: document.querySelector('#phoneNumber')?.value || ''
                })
            });

            const data = await response.json();
            if (!response.ok || !data.success || !data.authorization_url) {
                throw new Error(data.error || 'Could not initialize Paystack payment.');
            }

            window.location.href = data.authorization_url;
        } catch (error) {
            console.error('Paystack initialization error:', error);
            this.handleRegistrationError(error.message || 'Unable to start payment. Please try again.');
        }
    }

    handleRegistrationError(errorMessage) {
        this.hideLoading();
        this.closeRegistrationModal();
        
        if (typeof Toast !== 'undefined') {
            Toast.error('Registration Failed', errorMessage);
        } else {
            alert('Registration failed: ' + errorMessage);
        }
    }
}

// Initialize competition registration
document.addEventListener('DOMContentLoaded', function() {
    console.log('Initializing CompetitionRegistration');
    window.competitionRegistration = new CompetitionRegistration();
    console.log('CompetitionRegistration initialized globally');
});

// Make available globally
window.CompetitionRegistration = CompetitionRegistration;