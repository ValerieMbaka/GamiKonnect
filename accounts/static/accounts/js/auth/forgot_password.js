class ForgotPasswordManager extends BaseAuthManager {
    constructor() {
        super();
        this.cacheDOM();
        this.bindEvents();
    }

    cacheDOM() {
        this.form = document.getElementById('forgotPasswordForm');
        this.emailInput = document.getElementById('email');
        this.submitBtn = document.getElementById('resetSubmitBtn');
    }

    bindEvents() {
        if (this.form) {
            this.form.addEventListener('submit', (e) => this.handleSubmit(e));
        }
    }

    async handleSubmit(e) {
        e.preventDefault();
        const email = this.emailInput.value.trim();
        if (!email) return;

        this.toggleButtonState(this.submitBtn, true, 'Sending...');

        try {
            // Check if email exists in our system first (optional but better UX)
            // For now, we'll rely on Firebase's password reset email.
            // If the user doesn't exist, Firebase might not send the email or might not throw error depending on config.
            
            await window.firebaseSendPasswordResetEmail(email);
            
            window.toastManager.success(
                'Email Sent', 
                'If an account exists for this email, you will receive a password reset link shortly.'
            );
            
            this.form.reset();
        } catch (error) {
            console.error('Password reset error:', error);
            let message = 'Could not send password reset email. Please try again.';
            if (error.code === 'auth/user-not-found') {
                message = 'No account found with this email address.';
            }
            window.toastManager.error('Error', message);
        } finally {
            this.toggleButtonState(this.submitBtn, false, 'Send Reset Link');
        }
    }
}

document.addEventListener('DOMContentLoaded', () => new ForgotPasswordManager());
