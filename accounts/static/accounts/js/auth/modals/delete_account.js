class DeleteAccountManager {
    constructor() {
        this.modal = document.getElementById('deleteAccountModal');
        this.form = document.getElementById('deleteAccountForm');
        this.openBtns = document.querySelectorAll('.trigger-delete-account');
        this.closeBtn = document.getElementById('closeDeleteModalBtn');
        this.closeIcon = document.getElementById('closeDeleteModalIcon');

        if (this.modal) {
            this.initEvents();
            this.initPasswordToggles();
            this.initSubmitFlow();
        }
    }

    initEvents() {
        this.openBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                if (this.form) this.form.reset();
                this.modal.classList.add('show');
            });
        });

        if (this.closeBtn) this.closeBtn.addEventListener('click', () => this.modal.classList.remove('show'));
        if (this.closeIcon) this.closeIcon.addEventListener('click', () => this.modal.classList.remove('show'));

        window.addEventListener('click', (e) => {
            if (e.target === this.modal) this.modal.classList.remove('show');
        });
    }

    initPasswordToggles() {
        const toggleBtns = this.modal.querySelectorAll('.modular-toggle-password');
        toggleBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const targetId = e.currentTarget.dataset.target;
                const input = document.getElementById(targetId);
                if (input) {
                    const type = input.getAttribute('type') === 'password' ? 'text' : 'password';
                    input.setAttribute('type', type);
                    const icon = e.currentTarget.querySelector('i');
                    icon.className = type === 'password' ? 'fas fa-eye' : 'fas fa-eye-slash';
                }
            });
        });
    }

    initSubmitFlow() {
        if (this.form) {
            this.form.addEventListener('submit', async (e) => {
                e.preventDefault();

                const firebaseUidInput = document.getElementById('delete_firebase_uid');
                const passwordInput = document.getElementById('delete_confirm_password');
                const emailInput = document.getElementById('delete_user_email');
                
                const password = passwordInput ? passwordInput.value : '';
                const firebaseUid = firebaseUidInput ? firebaseUidInput.value : '';
                const emailText = emailInput ? emailInput.value : '';

                if (!password) {
                    window.toastManager?.error('Validation Error', 'Please enter your password to confirm.');
                    return;
                }

                const submitBtn = this.form.querySelector('button[type="submit"]');
                const originalHtml = submitBtn.innerHTML;
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> Erasing...';

                try {
                    // Safely try to re-authenticate with Firebase using the global hidden email
                    if (typeof window.firebaseAuthSignIn === 'function' && emailText) {
                        await window.firebaseAuthSignIn(emailText.trim(), password);
                    }

                    const response = await fetch('/accounts/delete-account/', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                        },
                        body: JSON.stringify({ password, firebase_uid: firebaseUid })
                    });

                    const data = await response.json();

                    if (data.success) {
                        window.toastManager?.success('Account Deleted', 'Your account has been permanently deleted.');
                        setTimeout(() => {
                            window.location.href = data.redirect_url || '/accounts/login/';
                        }, 2000);
                    } else {
                        window.toastManager?.error('Deletion Failed', data.message || 'Failed to delete account.');
                        this.resetButton(submitBtn, originalHtml);
                    }
                } catch (err) {
                    console.error('Error deleting account:', err);
                    window.toastManager?.error('Network Error', 'Authentication failed or network error.');
                    this.resetButton(submitBtn, originalHtml);
                }
            });
        }
    }

    resetButton(btn, html) {
        btn.disabled = false;
        btn.innerHTML = html;
    }
}

document.addEventListener('DOMContentLoaded', () => new DeleteAccountManager());