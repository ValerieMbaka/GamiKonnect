document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('loginForm');
    if (!loginForm) return;
    
    loginForm.addEventListener('submit', async function(e){
        e.preventDefault();
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        const submitBtn = document.getElementById('loginSubmitBtn');
        submitBtn.disabled = true;
        submitBtn.textContent = 'Signing In...';
        try {
            const userCredential = await window.firebaseAuthSignIn(email, password);
            const user = userCredential.user;
            // Force a fresh ID token to avoid clock skew issues
            const idToken = await user.getIdToken(true);
            document.getElementById('firebase_uid').value = user.uid;
            document.getElementById('id_token').value = idToken;
            
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
                    window.toastManager.show({ type: 'success', title: 'Success', message: data.message || 'Login successful' });
                } else if (window.showToast) {
                    window.showToast(data.message || 'Login successful', 'success');
                } else {
                    alert(data.message || 'Login successful');
                }
                // Server-provided next redirect, fallback to role-based default dashboards
                const nextUrl = (data.next && typeof data.next === 'string' && data.next.length) ? data.next : null;
                const fallbackUrl = data.role === 'gamer' ? loginForm.dataset.gamerDashboardUrl : loginForm.dataset.shopOwnerDashboardUrl;
                const redirectUrl = nextUrl || fallbackUrl;
                setTimeout(() => { window.location.href = redirectUrl; }, 800);
            } else {
                // If email not verified, show resend section and set email value
                if ((data.message || '').toLowerCase().includes('verify your account')) {
                    const resendSection = document.getElementById('resendVerificationSection');
                    if (resendSection) {
                        resendSection.style.display = 'block';
                        const resendEmail = document.getElementById('resendEmail');
                        if (resendEmail) resendEmail.value = email;
                    }
                }
                if (window.toastManager) {
                    window.toastManager.show({ type: 'warning', title: 'Login blocked', message: data.message || 'Please try again.' });
                } else if (window.showToast) {
                    window.showToast(data.message || 'Login failed. Please try again.', 'warning');
                } else {
                    alert(data.message || 'Login failed. Please try again.');
                }
                submitBtn.disabled = false;
                submitBtn.textContent = 'Sign In';
            }
        } catch(err){
            if (window.toastManager) {
                window.toastManager.show({ type: 'error', title: 'Login Failed', message: err.message || 'Unknown error' });
            } else if (window.showToast) {
                window.showToast(err.message || 'Login failed.', 'error');
            } else {
                alert(err.message || 'Login failed.');
            }
            submitBtn.disabled = false;
            submitBtn.textContent = 'Sign In';
        }
    });
    
    // Resend verification via AJAX
    const resendForm = document.getElementById('resendForm');
    if (resendForm) {
        resendForm.addEventListener('submit', async function(e){
            e.preventDefault();
            const btn = document.getElementById('resendVerificationBtn');
            if (!btn) return;
            btn.disabled = true; btn.textContent = 'Sending...';
            try {
                const formData = new FormData(resendForm);
                const resp = await fetch(resendForm.action, {
                    method: 'POST',
                    headers: { 'X-Requested-With': 'XMLHttpRequest' },
                    body: formData
                });
                const data = await resp.json();
                if (window.toastManager) {
                    window.toastManager.show({ type: data.success ? 'success' : 'error', title: data.success ? 'Email Sent' : 'Failed', message: data.message || '' });
                } else if (window.showToast) {
                    window.showToast(data.message || (data.success ? 'Verification email sent.' : 'Failed to send verification email.'), data.success ? 'success' : 'error');
                } else {
                    alert(data.message || (data.success ? 'Verification email sent.' : 'Failed to send verification email.'));
                }
            } catch(err) {
                if (window.toastManager) {
                    window.toastManager.show({ type: 'error', title: 'Failed', message: err.message || 'Could not resend email' });
                } else if (window.showToast) {
                    window.showToast(err.message || 'Could not resend email', 'error');
                } else {
                    alert(err.message || 'Could not resend email');
                }
            } finally {
                btn.disabled = false; btn.textContent = 'Resend Verification Email';
            }
        });
    }
});

