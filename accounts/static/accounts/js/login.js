class LoginManager {
    constructor() {
        this.loginForm = document.getElementById('loginForm');
        this.resendForm = document.getElementById('resendForm');
        
        if (this.loginForm || this.resendForm) {
            this.init();
        }
    }

    init() {
        if (this.loginForm) {
            this.loginForm.addEventListener('submit', (e) => this.handleLogin(e));
        }
        
        if (this.resendForm) {
            this.resendForm.addEventListener('submit', (e) => this.handleResend(e));
        }
    }

    async handleLogin(e) {
        e.preventDefault();
        
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        const submitBtn = document.getElementById('loginSubmitBtn');
        
        submitBtn.disabled = true;
        submitBtn.textContent = 'Signing In...';
        
        try {
            const userCredential = await window.firebaseAuthSignIn(email, password);
            const user = userCredential.user;
            const idToken = await user.getIdToken(true);
            
            document.getElementById('firebase_uid').value = user.uid;
            document.getElementById('id_token').value = idToken;
            
            const formData = new FormData(this.loginForm);
            const resp = await fetch(this.loginForm.action, {
                method: 'POST',
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
                body: formData
            });
            
            const data = await resp.json();
            
            if (data.success) {
                window.toastManager.success('Success', data.message || 'Login successful');
                
                const nextUrl = (data.next && typeof data.next === 'string' && data.next.length) ? data.next : null;
                const fallbackUrl = data.role === 'gamer' 
                    ? this.loginForm.dataset.gamerDashboardUrl 
                    : this.loginForm.dataset.shopOwnerDashboardUrl;
                    
                setTimeout(() => { window.location.href = nextUrl || fallbackUrl; }, 800);
            } else {
                this.handleLoginFailure(data, email);
                submitBtn.disabled = false;
                submitBtn.textContent = 'Sign In';
            }
        } catch(err) {
            window.toastManager.error('Login Failed', err.message || 'Unknown error');
            submitBtn.disabled = false;
            submitBtn.textContent = 'Sign In';
        }
    }

    handleLoginFailure(data, email) {
        if ((data.message || '').toLowerCase().includes('verify your account')) {
            const resendSection = document.getElementById('resendVerificationSection');
            if (resendSection) resendSection.style.display = 'block';
            
            const resendEmail = document.getElementById('resendEmail');
            if (resendEmail) resendEmail.value = email;
        }
        window.toastManager.warning('Login blocked', data.message || 'Please try again.');
    }

    async handleResend(e) {
        e.preventDefault();
        
        const btn = document.getElementById('resendVerificationBtn');
        btn.disabled = true; 
        btn.textContent = 'Sending...';
        
        try {
            const formData = new FormData(this.resendForm);
            const resp = await fetch(this.resendForm.action, {
                method: 'POST',
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
                body: formData
            });
            const data = await resp.json();
            
            if (data.success) {
                window.toastManager.success('Email Sent', data.message || 'Verification email sent.');
            } else {
                window.toastManager.error('Failed', data.message || 'Failed to send verification email.');
            }
        } catch(err) {
            window.toastManager.error('Failed', err.message || 'Could not resend email');
        } finally {
            btn.disabled = false; 
            btn.textContent = 'Resend Verification Email';
        }
    }
}

// Initialize the class when the DOM is fully loaded
document.addEventListener('DOMContentLoaded', () => new LoginManager());