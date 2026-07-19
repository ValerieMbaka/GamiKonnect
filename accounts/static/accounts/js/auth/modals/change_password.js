class ChangePasswordManager {
    constructor() {
        this.modal = document.getElementById('changePasswordModal');
        this.form = document.getElementById('changePasswordForm');
        this.openBtns = document.querySelectorAll('.trigger-change-password');
        this.closeBtn = document.getElementById('closePasswordModalBtn');
        this.closeIcon = document.getElementById('closePasswordModalIcon');

        if (this.modal) {
            this.initEvents();
            this.initPasswordToggles();
        }
    }

    initEvents() {
        this.openBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                if (this.form) this.form.reset(); // Clear old inputs when opening
                this.modal.classList.add('show');
            });
        });

        if (this.closeBtn) this.closeBtn.addEventListener('click', () => this.modal.classList.remove('show'));
        if (this.closeIcon) this.closeIcon.addEventListener('click', () => this.modal.classList.remove('show'));
        
        window.addEventListener('click', (e) => {
            if (e.target === this.modal) this.modal.classList.remove('show');
        });

        if (this.form) {
            this.form.addEventListener('submit', async (e) => {
                e.preventDefault();
                
                const currentPassword = document.getElementById('current_password').value;
                const newPassword = document.getElementById('new_password').value;
                const confirmPassword = document.getElementById('confirm_new_password').value;
                const firebaseUid = document.getElementById('change_password_firebase_uid').value;

                if (newPassword !== confirmPassword) {
                    window.toastManager?.error('Validation Error', 'New passwords do not match.');
                    return;
                }

                const submitBtn = this.form.querySelector('button[type="submit"]');
                const originalHtml = submitBtn.innerHTML;
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> Updating...';

                try {
                    // Send to Django backend
                    const response = await fetch('/accounts/change-password/', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                        },
                        body: JSON.stringify({
                            firebase_uid: firebaseUid,
                            new_password: newPassword
                        })
                    });

                    const data = await response.json();

                    if (data.success) {
                        window.toastManager?.success('Success', 'Password updated successfully.');
                        this.form.reset();
                        setTimeout(() => this.modal.classList.remove('show'), 1500);
                    } else {
                        window.toastManager?.error('Update Failed', data.message || 'Failed to change password.');
                    }
                } catch (error) {
                    console.error('Password change error:', error);
                    window.toastManager?.error('Network Error', 'An unexpected error occurred. Please try again.');
                } finally {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalHtml;
                }
            });
        }
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
}

document.addEventListener('DOMContentLoaded', () => new ChangePasswordManager());