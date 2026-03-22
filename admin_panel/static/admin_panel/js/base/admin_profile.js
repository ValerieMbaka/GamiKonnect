class AdminProfileController {
    constructor() {
        this.bindEvents();
    }

    bindEvents() {
        // Image Preview Logic
        const fileInput = document.getElementById('id_avatar');
        if (fileInput) {
            fileInput.addEventListener('change', (e) => this.handleImagePreview(e));
        }

        // Form Submissions
        const editForm = document.getElementById('editProfileForm');
        const passForm = document.getElementById('changePasswordForm');
        
        if(editForm) editForm.addEventListener('submit', (e) => this.submitForm(e, 'editProfileModal'));
        if(passForm) passForm.addEventListener('submit', (e) => this.submitForm(e, 'changePasswordModal'));
        
        // Close modal on outside click
        document.querySelectorAll('.admin-modal-overlay').forEach(overlay => {
            overlay.addEventListener('click', (e) => {
                if (e.target === overlay) this.closeModal(overlay.id);
            });
        });
    }

    openModal(modalId) {
        this.clearErrors(modalId);
        document.getElementById(modalId).classList.add('active');
        document.body.style.overflow = 'hidden'; // Prevent background scrolling
    }

    closeModal(modalId) {
        document.getElementById(modalId).classList.remove('active');
        document.body.style.overflow = '';
        
        // Reset the password form on close for security
        if (modalId === 'changePasswordModal') {
            document.getElementById('changePasswordForm').reset();
        }
    }

    handleImagePreview(e) {
        const file = e.target.files[0];
        if (file && file.type.startsWith('image/')) {
            const reader = new FileReader();
            reader.onload = (event) => {
                document.getElementById('avatarPreview').src = event.target.result;
            };
            reader.readAsDataURL(file);
        }
    }

    clearErrors(modalId) {
        const modal = document.getElementById(modalId);
        modal.querySelectorAll('.error-msg').forEach(el => el.textContent = '');
    }

    async submitForm(e, modalId) {
        e.preventDefault();
        const form = e.target;
        const btn = form.querySelector('button[type="submit"]');
        const originalBtnText = btn.innerHTML;
        
        // Set loading state
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
        this.clearErrors(modalId);

        try {
            const response = await fetch(form.action, {
                method: 'POST',
                body: new FormData(form),
                headers: {
                    'X-Requested-With': 'XMLHttpRequest' // Tells Django this is an AJAX request
                }
            });

            const data = await response.json();

            if (response.ok && data.success) {
                // Close Modal
                this.closeModal(modalId);
                
                // Update UI instantly if it was the profile form
                if (modalId === 'editProfileModal' && data.data) {
                    this.updateProfileUI(data.data);
                }
                
                // Fallback to reload if global toast isn't available
                window.location.reload();
                
            } else {
                // Display Validation Errors below inputs
                if (data.errors) {
                    for (const [field, messages] of Object.entries(data.errors)) {
                        const errorDiv = document.getElementById(`error-${field}`);
                        if (errorDiv) {
                            errorDiv.textContent = messages[0]; // Show first error
                        }
                    }
                }
            }
        } catch (error) {
            console.error('Error submitting form:', error);
            alert('A network error occurred. Please try again.');
        } finally {
            // Restore button state
            btn.disabled = false;
            btn.innerHTML = originalBtnText;
        }
    }

    updateProfileUI(data) {
        document.getElementById('displayFullName').textContent = `${data.first_name} ${data.last_name}`;
        document.getElementById('displayEmail').textContent = data.email;
        
        if (data.job_title) {
            document.getElementById('displayJobTitle').textContent = data.job_title;
        }
        if (data.timezone) {
            document.getElementById('displayTimezone').textContent = data.timezone;
        }
        if (data.avatar_url) {
            document.getElementById('displayAvatar').src = data.avatar_url;
            document.querySelectorAll('.admin-avatar').forEach(img => img.src = data.avatar_url);
        }
    }
}

// Instantiate globally so inline onclick handlers in HTML can reach it
const adminProfile = new AdminProfileController();