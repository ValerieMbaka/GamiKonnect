class RegistrationManager {
    constructor() {
        this.form = document.getElementById('registerForm');
        this.passwordInput = document.getElementById('password');
        this.confirmInput = document.getElementById('confirm_password');
        this.requirementsPopup = document.getElementById('passwordRequirements');
        this.strengthBar = document.querySelector('.strength-bar');
        this.matchFeedback = document.getElementById('password-match');

        if (this.form || this.passwordInput) {
            this.init();
        }
    }

    init() {
        this.setupPasswordListeners();
        this.setupFormListener();
    }

    setupPasswordListeners() {
        if (this.passwordInput) {
            this.passwordInput.addEventListener('focus', () => this.showRequirements());
            this.passwordInput.addEventListener('input', (e) => this.handlePasswordInput(e.target.value));
            
            this.passwordInput.addEventListener('blur', () => {
                setTimeout(() => {
                    if (document.activeElement !== this.confirmInput) {
                        this.hideRequirements();
                    }
                }, 100);
            });

            document.addEventListener('click', (e) => {
                if (this.requirementsPopup && 
                    !this.passwordInput.contains(e.target) && 
                    !this.requirementsPopup.contains(e.target)) {
                    this.hideRequirements();
                }
            });
        }
        
        if (this.confirmInput) {
            this.confirmInput.addEventListener('input', () => this.checkMatch());
            this.confirmInput.addEventListener('focus', () => {
                if (this.passwordInput.value.length > 0) {
                    this.showRequirements();
                }
            });
        }
           
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') this.hideRequirements();
        });
    }

    setupFormListener() {
        if (this.form) {
            this.form.addEventListener('submit', (e) => this.handleRegistration(e));
        }
    }

    validatePassword(password) {
        return {
            length: password.length >= 8,
            uppercase: /[A-Z]/.test(password),
            lowercase: /[a-z]/.test(password),
            number: /[0-9]/.test(password),
            special: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)
        };
    }

    handlePasswordInput(value) {
        const requirements = this.validatePassword(value);
        this.updateRequirementsUI(requirements);
        this.updateStrengthUI(value, requirements);
        this.checkMatch();
        
        if (value.length > 0) {
            this.showRequirements();
        }
    }

    updateRequirementsUI(requirements) {
        Object.keys(requirements).forEach(key => {
            const element = document.getElementById(`req-${key}`);
            if (element) {
                const icon = element.querySelector('.req-icon');
                if (requirements[key]) {
                    element.className = 'req-valid';
                    icon.textContent = '✓';
                } else {
                    element.className = 'req-invalid';
                    icon.textContent = '○';
                }
            }
        });
    }

    updateStrengthUI(password, requirements) {
        if (!this.strengthBar) return;
        
        const metCount = Object.values(requirements).filter(Boolean).length;
        const totalCount = Object.keys(requirements).length;
        const strength = metCount / totalCount;
        
        this.strengthBar.className = 'strength-bar';
        
        if (password.length === 0) {
            this.strengthBar.style.width = '0%';
        } else if (strength < 0.6) {
            this.strengthBar.className += ' strength-weak';
            this.strengthBar.style.width = `${strength * 100}%`;
        } else if (strength < 0.8) {
            this.strengthBar.className += ' strength-medium';
            this.strengthBar.style.width = `${strength * 100}%`;
        } else {
            this.strengthBar.className += ' strength-strong';
            this.strengthBar.style.width = `${strength * 100}%`;
        }
    }

    checkMatch() {
        if (!this.matchFeedback || !this.confirmInput || !this.passwordInput) return;
        
        const password = this.passwordInput.value;
        const confirmPassword = this.confirmInput.value;
        
        if (confirmPassword.length === 0) {
            this.matchFeedback.textContent = '';
            this.matchFeedback.className = 'password-feedback';
        } else if (password === confirmPassword) {
            this.matchFeedback.textContent = 'Passwords match';
            this.matchFeedback.className = 'password-feedback password-match';
        } else {
            this.matchFeedback.textContent = 'Passwords do not match';
            this.matchFeedback.className = 'password-feedback password-mismatch';
        }
    }

    showRequirements() {
        if (this.requirementsPopup) this.requirementsPopup.classList.add('show');
    }

    hideRequirements() {
        if (this.requirementsPopup) this.requirementsPopup.classList.remove('show');
    }

    async handleRegistration(e) {
        e.preventDefault();
        
        const btn = document.getElementById('registerSubmitBtn');
        btn.disabled = true; 
        btn.textContent = 'Creating Account...';

        window.toastManager.info('Creating Account', 'Please wait while we set things up...');

        const email = document.getElementById('email').value;
        const password = this.passwordInput.value;
        
        try {
            const cred = await window.firebaseAuthCreateUser(email, password);
            document.getElementById('firebase_uid').value = cred.user.uid;
            
            const formData = new FormData(this.form);
            const resp = await fetch(this.form.action, {
                method: 'POST',
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
                body: formData
            });
            const data = await resp.json();
            
            if (data.success) {
                window.toastManager.success('Registration Successful', 'Account created. We\'ve sent a verification email. Please verify to proceed.');
                setTimeout(() => { window.location.href = this.form.dataset.loginUrl; }, 1200);
            } else {
                window.toastManager.error('Registration Failed', data.message || 'Please try again.');
                btn.disabled = false; 
                btn.textContent = 'Sign Up';
            }
        } catch(err) {
            window.toastManager.error('Registration Failed', err.message || 'Unknown error');
            btn.disabled = false; 
            btn.textContent = 'Sign Up';
        }
    }
}

// Initialize the class when the DOM is fully loaded
document.addEventListener('DOMContentLoaded', () => new RegistrationManager());