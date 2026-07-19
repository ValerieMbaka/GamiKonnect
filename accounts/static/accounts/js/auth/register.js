class RegistrationManager extends BaseAuthManager {
    constructor() {
        super();
        this.cacheDOM();
        if (this.form || this.passwordInput) {
            this.init();
        }
    }

    cacheDOM() {
        this.form = document.getElementById('registerForm');
        this.passwordInput = document.getElementById('password');
        this.confirmInput = document.getElementById('confirm_password');
        this.requirementsPopup = document.getElementById('passwordRequirements');
        this.strengthBar = document.getElementById('strengthBar');
        this.matchFeedback = document.getElementById('password-match');
        this.submitBtn = document.getElementById('registerSubmitBtn');
        this.uidInput = document.getElementById('firebase_uid');
        this.emailInput = document.getElementById('email');
    }

    init() {
        this.bindPasswordEvents();
        this.bindFormEvents();
    }

    bindPasswordEvents() {
        if (this.passwordInput) {
            this.passwordInput.addEventListener('focus', () => this.toggleRequirements(true));
            this.passwordInput.addEventListener('input', (e) => this.handlePasswordInput(e.target.value));
            
            this.passwordInput.addEventListener('blur', () => {
                setTimeout(() => {
                    if (document.activeElement !== this.confirmInput) {
                        this.toggleRequirements(false);
                    }
                }, 100);
            });

            document.addEventListener('click', (e) => {
                if (this.requirementsPopup &&
                    !this.passwordInput.contains(e.target) &&
                    !this.requirementsPopup.contains(e.target)) {
                    this.toggleRequirements(false);
                }
            });
        }
        
        if (this.confirmInput) {
            this.confirmInput.addEventListener('input', () => this.checkMatch());
            this.confirmInput.addEventListener('focus', () => {
                if (this.passwordInput.value.length > 0) {
                    this.toggleRequirements(true);
                }
            });
        }
        
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') this.toggleRequirements(false);
        });
    }

    bindFormEvents() {
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
            this.toggleRequirements(true);
        }
    }

    updateRequirementsUI(requirements) {
        Object.entries(requirements).forEach(([key, isValid]) => {
            const element = document.getElementById(`req-${key}`);
            if (element) {
                const icon = element.querySelector('.req-icon');
                element.className = isValid ? 'req-valid' : 'req-invalid';
                icon.textContent = isValid ? '✓' : '○';
            }
        });
    }

    updateStrengthUI(password, requirements) {
        if (!this.strengthBar) return;
        
        const metCount = Object.values(requirements).filter(Boolean).length;
        const totalCount = Object.keys(requirements).length;
        const strength = metCount / totalCount;
        
        this.strengthBar.style.setProperty('--strength-width', password.length === 0 ? '0%' : `${strength * 100}%`);
        
        this.strengthBar.className = 'strength-bar';
        if (password.length > 0) {
            if (strength < 0.6) this.strengthBar.classList.add('strength-weak');
            else if (strength < 0.8) this.strengthBar.classList.add('strength-medium');
            else this.strengthBar.classList.add('strength-strong');
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

    toggleRequirements(show) {
        if (!this.requirementsPopup) return;
        if (show) {
            this.requirementsPopup.classList.add('show');
        } else {
            this.requirementsPopup.classList.remove('show');
        }
    }

    async handleRegistration(e) {
        e.preventDefault();
        
        this.toggleButtonState(this.submitBtn, true, 'Creating Account...');
        window.toastManager.info('Creating Account', 'Please wait while we set things up...');

        try {
            const cred = await window.firebaseAuthCreateUser(this.emailInput.value, this.passwordInput.value);
            this.uidInput.value = cred.user.uid;
            
            const data = await this.sendFormRequest(this.form);
            
            if (data.success) {
                window.toastManager.success('Registration Successful', 'Account created. We\'ve sent a verification email. Please verify to proceed.');
                setTimeout(() => { window.location.href = this.form.dataset.loginUrl; }, 1200);
            } else {
                window.toastManager.error('Registration Failed', data.message || 'Please try again.');
                this.toggleButtonState(this.submitBtn, false, 'Sign Up');
            }
        } catch(err) {
            window.toastManager.error('Registration Failed', err.message || 'Unknown error');
            this.toggleButtonState(this.submitBtn, false, 'Sign Up');
        }
    }
}

document.addEventListener('DOMContentLoaded', () => new RegistrationManager());