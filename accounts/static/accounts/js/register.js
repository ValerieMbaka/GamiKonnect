function validatePassword(password) {
    return {
        length: password.length >= 8,
        uppercase: /[A-Z]/.test(password),
        lowercase: /[a-z]/.test(password),
        number: /[0-9]/.test(password),
        special: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)
    };
}

function updatePasswordRequirements(requirements) {
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

function updatePasswordStrength(password) {
    const strengthBar = document.querySelector('.strength-bar');
    if (!strengthBar) return;
    const requirements = validatePassword(password);
    const metCount = Object.values(requirements).filter(Boolean).length;
    const totalCount = Object.keys(requirements).length;
    const strength = metCount / totalCount;
    strengthBar.className = 'strength-bar';
    if (password.length === 0) {
        strengthBar.style.width = '0%';
    } else if (strength < 0.6) {
        strengthBar.className += ' strength-weak';
        strengthBar.style.width = `${strength * 100}%`;
    } else if (strength < 0.8) {
        strengthBar.className += ' strength-medium';
        strengthBar.style.width = `${strength * 100}%`;
    } else {
        strengthBar.className += ' strength-strong';
        strengthBar.style.width = `${strength * 100}%`;
    }
}

function checkPasswordMatch() {
    const password = document.getElementById('password').value;
    const confirmPassword = document.getElementById('confirm_password').value;
    const matchFeedback = document.getElementById('password-match');
    if (!matchFeedback) return;
    if (confirmPassword.length === 0) {
        matchFeedback.textContent = '';
        matchFeedback.className = 'password-feedback';
    } else if (password === confirmPassword) {
        matchFeedback.textContent = 'Passwords match';
        matchFeedback.className = 'password-feedback password-match';
    } else {
        matchFeedback.textContent = 'Passwords do not match';
        matchFeedback.className = 'password-feedback password-mismatch';
    }
}

function showPasswordRequirements() {
    const popup = document.getElementById('passwordRequirements');
    if (popup) {
        popup.classList.add('show');
    }
}

function hidePasswordRequirements() {
    const popup = document.getElementById('passwordRequirements');
    if (popup) {
        popup.classList.remove('show');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const passwordInput = document.getElementById('password');
    const confirmInput = document.getElementById('confirm_password');
    
    if (passwordInput) {
        passwordInput.addEventListener('focus', showPasswordRequirements);
        document.addEventListener('click', function(e) {
            const popup = document.getElementById('passwordRequirements');
            if (popup && !passwordInput.contains(e.target) && !popup.contains(e.target)) {
                hidePasswordRequirements();
            }
        });

        passwordInput.addEventListener('input', function() {
            const requirements = validatePassword(this.value);
            updatePasswordRequirements(requirements);
            updatePasswordStrength(this.value);
            checkPasswordMatch();
            if (this.value.length > 0) {
                showPasswordRequirements();
            }
        });

        passwordInput.addEventListener('blur', function() {
            setTimeout(() => {
                if (document.activeElement !== confirmInput) {
                    hidePasswordRequirements();
                }
                }, 100);
        });
    }
    
    if (confirmInput) {
        confirmInput.addEventListener('input', checkPasswordMatch);
        confirmInput.addEventListener('focus', function() {
            if (passwordInput.value.length > 0) {
                showPasswordRequirements();
            }
        });
    }
	   
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            hidePasswordRequirements();
        }
    });
	   
    const registerForm = document.getElementById('registerForm');
    if (!registerForm) return;
	   
    // Firebase create user then submit to backend via AJAX to handle JSON + toasts
    registerForm.addEventListener('submit', async function(e){
        e.preventDefault();
        const btn = document.getElementById('registerSubmitBtn');
        btn.disabled = true; btn.textContent = 'Creating Account...';

        if (window.toastManager) {
            window.toastManager.show({
                type: 'info',
                title: 'Creating Account',
                message: 'Please wait while we set things up...'
            });
        }

        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        try {
            const cred = await window.firebaseAuthCreateUser(email, password);
            document.getElementById('firebase_uid').value = cred.user.uid;
            
            const formEl = e.target;
            const formData = new FormData(formEl);
            const resp = await fetch(formEl.action, {
                method: 'POST',
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
                body: formData
            });
            const data = await resp.json();
            if (data.success) {
                if (window.toastManager) {
                    window.toastManager.show({
                        type: 'success',
                        title: 'Registration Successful',
                        message: 'Account created. We\'ve sent a verification email. Please verify to proceed.'
                    });
                } else if (window.showToast) {
                    window.showToast('Account created. Please check your email for verification.', 'success');
                } else {
                    alert('Account created. Please check your email for verification.');
                }
                setTimeout(() => { window.location.href = registerForm.dataset.loginUrl; }, 1200);
            } else {
                if (window.toastManager) {
                    window.toastManager.show({ type: 'error', title: 'Registration Failed', message: data.message || 'Please try again.' });
                } else if (window.showToast) {
                    window.showToast('Registration failed: ' + (data.message || 'Unknown error'), 'error');
                } else {
                    alert('Registration failed: ' + (data.message || 'Unknown error'));
                }
                btn.disabled = false; btn.textContent = 'Sign Up';
            }
        } catch(err){
            if (window.toastManager) {
                window.toastManager.show({ type: 'error', title: 'Registration Failed', message: err.message || 'Unknown error' });
            } else if (window.showToast) {
                window.showToast('Registration failed: ' + (err.message || 'Unknown error'), 'error');
            } else {
                alert('Registration failed: ' + (err.message || 'Unknown error'));
            }
            btn.disabled = false; btn.textContent = 'Sign Up';
        }
    });
});

