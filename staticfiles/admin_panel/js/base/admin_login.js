class AdminLoginController {
    constructor() {
        this.cacheDOM();
        this.bindEvents();
    }

    // Cache all necessary DOM elements once upon initialization to prevent repeated DOM queries during execution.
    
    cacheDOM() {
        this.form = document.getElementById('adminLoginForm');
        this.passwordInput = document.getElementById('password');
        this.toggleBtn = document.getElementById('togglePasswordBtn');
        this.toggleIcon = this.toggleBtn ? this.toggleBtn.querySelector('i') : null;
        
        this.submitBtn = document.getElementById('loginSubmitBtn');
        this.submitBtnText = this.submitBtn ? this.submitBtn.querySelector('.btn-text') : null;
        this.submitBtnIcon = this.submitBtn ? this.submitBtn.querySelector('.btn-icon-right') : null;
    }

    // Attach all event listeners to the cached DOM elements.
    bindEvents() {
        if (this.toggleBtn && this.passwordInput) {
            this.toggleBtn.addEventListener('click', () => this.togglePasswordVisibility());
        }

        if (this.form) {
            this.form.addEventListener('submit', (e) => this.handleSubmission(e));
        }
    }
    
    togglePasswordVisibility() {
        const isPassword = this.passwordInput.type === 'password';
        
        // Toggle input type
        this.passwordInput.type = isPassword ? 'text' : 'password';
        
        // Toggle icon visually
        if (this.toggleIcon) {
            this.toggleIcon.className = isPassword ? 'fas fa-eye-slash' : 'fas fa-eye';
        }
    }

    /**
     * Handles the UI state during form submission.
     * Allow the native standard POST request to proceed to Django,
     * but lock the UI to prevent duplicate submissions.
     */
    handleSubmission(e) {
        // Ensure the browser's native HTML5 validation passes first
        if (!this.form.checkValidity()) {
            return;
        }

        // Disable the button to prevent multiple clicks
        this.submitBtn.disabled = true;

        // Update the button text to provide immediate feedback
        if (this.submitBtnText) {
            this.submitBtnText.textContent = 'Authenticating...';
        }

        // Swap the right arrow icon for a spinning loading circle
        if (this.submitBtnIcon) {
            this.submitBtnIcon.className = 'fas fa-circle-notch fa-spin btn-icon-right';
        }

        // Do NOT call e.preventDefault() here since the form should natively submit to the backend.
    }
}

// Initialize the controller only after the DOM is fully constructed
document.addEventListener('DOMContentLoaded', () => {
    new AdminLoginController();
});