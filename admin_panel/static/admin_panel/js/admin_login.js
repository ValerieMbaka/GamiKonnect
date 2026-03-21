class AdminLoginManager {
    constructor() {
        this.loginForm = document.querySelector('.login-form');
        this.submitButton = document.querySelector('.btn-primary');
        if (this.loginForm) this.bindEvents();
    }

    bindEvents() {
        this.loginForm.addEventListener('submit', () => this.handleFormSubmit());
    }

    handleFormSubmit() {
        if (this.submitButton) {
            this.submitButton.disabled = true;
            this.submitButton.textContent = 'Authenticating...';
            this.submitButton.style.opacity = '0.7';
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new AdminLoginManager();
});