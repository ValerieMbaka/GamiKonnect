class LoginManager extends BaseAuthManager {
    constructor() {
        super();
        this.cacheDOM();
        this.bindEvents();
    }

    cacheDOM() {
        this.loginForm = document.getElementById('loginForm');
        this.resendForm = document.getElementById('resendForm');
        this.emailInput = document.getElementById('email');
        this.passwordInput = document.getElementById('password');
        this.submitBtn = document.getElementById('loginSubmitBtn');
        this.resendBtn = document.getElementById('resendVerificationBtn');
        this.resendSection = document.getElementById('resendVerificationSection');
        this.resendEmailInput = document.getElementById('resendEmail');
        this.uidInput = document.getElementById('firebase_uid');
        this.tokenInput = document.getElementById('id_token');
    }

    bindEvents() {
        if (this.loginForm) this.loginForm.addEventListener('submit', (e) => this.handleLogin(e));
        if (this.resendForm) this.resendForm.addEventListener('submit', (e) => this.handleResend(e));
    }

    async handleLogin(e) {
        e.preventDefault();
        this.toggleButtonState(this.submitBtn, true, 'Signing In...');
        
        try {
            const userCredential = await window.firebaseAuthSignIn(this.emailInput.value, this.passwordInput.value);
            const idToken = await userCredential.user.getIdToken(true);
            
            if (this.uidInput) this.uidInput.value = userCredential.user.uid;
            if (this.tokenInput) this.tokenInput.value = idToken;
            
            const data = await this.sendFormRequest(this.loginForm);
            
            if (data.success) {
                window.toastManager.success('Success', data.message || 'Login successful');
                const nextUrl = (data.next && typeof data.next === 'string' && data.next.length) ? data.next : null;
                const fallbackUrl = data.role === 'gamer'
                    ? this.loginForm.dataset.gamerDashboardUrl
                    : this.loginForm.dataset.shopOwnerDashboardUrl;
                    
                setTimeout(() => { window.location.href = nextUrl || fallbackUrl; }, 800);
            } else {
                this.handleLoginFailure(data, this.emailInput.value);
            }
        } catch(err) {
            window.toastManager.error('Login Failed', err.message || 'Unknown error');
            this.toggleButtonState(this.submitBtn, false, 'Sign In');
        }
    }

    handleLoginFailure(data, email) {
        if ((data.message || '').toLowerCase().includes('verify your account')) {
            if (this.resendSection) this.resendSection.style.display = 'block';
            if (this.resendEmailInput) this.resendEmailInput.value = email;
        }
        window.toastManager.warning('Login blocked', data.message || 'Please try again.');
        this.toggleButtonState(this.submitBtn, false, 'Sign In');
    }

    async handleResend(e) {
        e.preventDefault();
        this.toggleButtonState(this.resendBtn, true, 'Sending...');
        
        try {
            const data = await this.sendFormRequest(this.resendForm);
            
            if (data.success) {
                window.toastManager.success('Email Sent', data.message || 'Verification email sent.');
            } else {
                window.toastManager.error('Failed', data.message || 'Failed to send verification email.');
            }
        } catch(err) {
            window.toastManager.error('Failed', err.message || 'Could not resend email');
        } finally {
            this.toggleButtonState(this.resendBtn, false, 'Resend Verification Email');
        }
    }
}

document.addEventListener('DOMContentLoaded', () => new LoginManager());