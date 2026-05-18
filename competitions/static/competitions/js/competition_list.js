/**
 * CompetitionList
 * Handles gamer-facing competition list interactions:
 * - Registration modal open/confirm/close
 * - AJAX registration submission
 * - Dynamic card UI updates
 * 
 * Usage: new CompetitionList()
 * Dependencies: showToast() global function
 */

class CompetitionList {
    constructor() {
        this.activeCompetitionId = null;
        this.activeCompetitionName = null;
        this.init();
    }

    init() {
        this.bindEvents();
    }

    bindEvents() {
        // Note: The register buttons use inline onclick handlers in the template
        // which call this.openRegisterModal(button)
        // No additional event binding needed here
    }

    openRegisterModal(btn) {
        this.activeCompetitionId = btn.dataset.competitionId;
        this.activeCompetitionName = btn.dataset.competitionName;

        // Load the full registration modal with payment form from the server
        this.loadRegistrationModal(this.activeCompetitionId);
    }

    async loadRegistrationModal(competitionId) {
        try {
            const response = await fetch(`/competitions/${competitionId}/register/`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            // Get the HTML response
            const html = await response.text();
            
            // Get or create the modal backdrop
            let modalBackdrop = document.getElementById('modalBackdrop');
            if (!modalBackdrop) {
                modalBackdrop = document.createElement('div');
                modalBackdrop.id = 'modalBackdrop';
                modalBackdrop.className = 'modal-backdrop';
                document.body.appendChild(modalBackdrop);
            }
            
            // Get or create the registration modal container
            let registrationModal = document.getElementById('registrationModal');
            if (!registrationModal) {
                registrationModal = document.createElement('div');
                registrationModal.id = 'registrationModal';
                registrationModal.className = 'modal-container registration-modal';
                document.body.appendChild(registrationModal);
            } else {
                // Update class if it exists
                registrationModal.className = 'modal-container registration-modal';
            }
            
            // Set the modal content
            registrationModal.innerHTML = html;
            
            // Show the modal
            modalBackdrop.classList.remove('hidden');
            registrationModal.classList.remove('hidden');
            document.body.classList.add('modal-open');
            
            // Initialize or reinitialize the CompetitionRegistration class for the modal
            // Recreate the instance to bind to newly loaded DOM elements
            if (window.competitionRegistration) {
                window.competitionRegistration = null;
            }
            window.competitionRegistration = new CompetitionRegistration();
            
        } catch (error) {
            console.error('Error loading registration form:', error);
            if (typeof showToast !== 'undefined') {
                showToast('error', 'Failed to load registration form. Please try again.');
            } else {
                alert('Failed to load registration form. Please try again.');
            }
        }
    }

    closeRegistrationModal() {
        const modalBackdrop = document.getElementById('modalBackdrop');
        const registrationModal = document.getElementById('registrationModal');
        
        if (modalBackdrop) modalBackdrop.classList.add('hidden');
        if (registrationModal) registrationModal.classList.add('hidden');
        document.body.classList.remove('modal-open');
        
        this.activeCompetitionId = null;
        this.activeCompetitionName = null;
    }

    // Legacy method for backward compatibility
    closeRegisterModal() {
        this.closeRegistrationModal();
    }

    static initialize() {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                window.competitionList = new CompetitionList();
            });
        } else {
            window.competitionList = new CompetitionList();
        }
    }
}

// Auto-initialize on page load
CompetitionList.initialize();