// Reuse registration password rules for validation
function validatePassword(password) {
    return {
        length: password.length >= 8,
        uppercase: /[A-Z]/.test(password),
        lowercase: /[a-z]/.test(password),
        number: /[0-9]/.test(password),
        special: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)
    };
}

function isPasswordStrongEnough(password) {
    const req = validatePassword(password);
    // Require all registration rules for change password as well
    return req.length && req.uppercase && req.lowercase && req.number && req.special;
}

function updatePasswordRequirementsDisplay(requirements) {
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

function updatePasswordStrengthBar(password) {
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

// Password change functionality + account deletion
document.addEventListener('DOMContentLoaded', function() {
    // Password change form
    const changePasswordForm = document.getElementById('changePasswordForm');
    if (changePasswordForm) {
        const newPasswordInput = document.getElementById('new_password');
        const confirmPasswordInput = document.getElementById('confirm_password');

        if (newPasswordInput) {
            newPasswordInput.addEventListener('input', function() {
                const requirements = validatePassword(this.value);
                updatePasswordRequirementsDisplay(requirements);
                updatePasswordStrengthBar(this.value);
            });
        }

        changePasswordForm.addEventListener('submit', async function(e) {
            e.preventDefault();

            const currentPassword = document.getElementById('current_password').value;
            const newPassword = newPasswordInput ? newPasswordInput.value : '';
            const confirmPassword = confirmPasswordInput ? confirmPasswordInput.value : '';
            const firebaseUid = document.getElementById('firebase_uid').value;

            if (!currentPassword || !newPassword || !confirmPassword) {
                showToast('All password fields are required', 'error');
                return;
            }

            if (newPassword !== confirmPassword) {
                showToast('New passwords do not match', 'error');
                return;
            }

            if (!isPasswordStrongEnough(newPassword)) {
                showToast('New password does not meet the required strength rules', 'error');
                return;
            }

            try {
                showToast('Changing password...', 'info');

                const firebaseModule = await import('/static/core/js/firebase-init.js');
                const { auth, signInWithEmailAndPassword } = firebaseModule;

                const emailElement = document.querySelector('.profile-summary-email');
                const email = emailElement ? emailElement.textContent.trim() : '';

                if (!email) {
                    showToast('Unable to get email address', 'error');
                    return;
                }

                try {
                    await signInWithEmailAndPassword(auth, email, currentPassword);

                    const response = await fetch('/accounts/api/change-password/', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                        },
                        body: JSON.stringify({
                            current_password: currentPassword,
                            new_password: newPassword,
                            firebase_uid: firebaseUid
                        })
                    });

                    const data = await response.json();

                    if (data.success) {
                        showToast('Password changed successfully', 'success');
                        changePasswordForm.reset();
                    } else {
                        showToast(data.message || 'Failed to change password', 'error');
                    }
                } catch (firebaseError) {
                    console.error('Firebase error:', firebaseError);
                    if (firebaseError.code === 'auth/wrong-password' || firebaseError.code === 'auth/invalid-credential') {
                        showToast('Current password is incorrect', 'error');
                    } else {
                        showToast('Failed to verify current password', 'error');
                    }
                }
            } catch (error) {
                console.error('Error changing password:', error);
                showToast('Network error. Please try again.', 'error');
            }
        });
    }

    // Settings tabs
    const tabItems = document.querySelectorAll('.settings-nav-item');
    const tabContents = document.querySelectorAll('.settings-tab-content');
    
    tabItems.forEach(item => {
        item.addEventListener('click', function() {
            const tabName = this.getAttribute('data-tab');
            
            // Update active tab
            tabItems.forEach(tab => tab.classList.remove('active'));
            this.classList.add('active');
            
            // Show corresponding content
            tabContents.forEach(content => {
                content.classList.remove('active');
                if (content.id === tabName) {
                    content.classList.add('active');
                }
            });
        });
    });
    
    // Dark mode toggle
    const darkModeToggle = document.getElementById('settingsDarkModeToggle');
    if (darkModeToggle) {
        // Set initial state from localStorage
        const currentTheme = localStorage.getItem('theme') || 'light';
        darkModeToggle.checked = currentTheme === 'dark';
        
        darkModeToggle.addEventListener('change', function() {
            const theme = this.checked ? 'dark' : 'light';
            document.documentElement.setAttribute('data-theme', theme);
            localStorage.setItem('theme', theme);
        });
    }
});

// Password toggle functionality
window.togglePassword = function(inputId) {
    const input = document.getElementById(inputId);
    const icon = input.parentNode.querySelector('.password-toggle i');
    
    if (input.type === 'password') {
        input.type = 'text';
        icon.className = 'fas fa-eye-slash';
    } else {
        input.type = 'password';
        icon.className = 'fas fa-eye';
    }
};

// Modal functions
function showDeleteModal() {
    document.getElementById('deleteAccountModal').style.display = 'block';
}

function hideDeleteModal() {
    document.getElementById('deleteAccountModal').style.display = 'none';
}

// Close modal when clicking outside
window.addEventListener('click', function(e) {
    const modal = document.getElementById('deleteAccountModal');
    if (e.target === modal) {
        hideDeleteModal();
    }
});

// Toast notification function
function showToast(message, type = 'info') {
    // Use your existing toast function or create a simple one
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <div class="toast-content">
            <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
            <span>${message}</span>
        </div>
    `;
    
    document.body.appendChild(toast);
    
    // Show toast
    setTimeout(() => toast.classList.add('show'), 100);
    
    // Remove toast after 5 seconds
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}


document.addEventListener('DOMContentLoaded', function() {
    // Check for success message from URL parameters
    const urlParams = new URLSearchParams(window.location.search);
    const successMessage = urlParams.get('success');
    
    if (successMessage) {
        showSuccessMessage(decodeURIComponent(successMessage));
        // Remove the parameter from URL
        const newUrl = window.location.pathname;
        window.history.replaceState({}, document.title, newUrl);
    }
    
    // Check for updated profile data in localStorage
    const userProfileData = localStorage.getItem('userProfileData');
    const userStats = localStorage.getItem('userStats');
    
    if (userProfileData && userStats) {
        updateProfileDisplay(JSON.parse(userProfileData), JSON.parse(userStats));
        // Clear localStorage after updating
        localStorage.removeItem('userProfileData');
        localStorage.removeItem('userStats');
    }
    
    // Settings tab navigation
    const tabButtons = document.querySelectorAll('.settings-nav-item');
    const tabContents = document.querySelectorAll('.settings-tab-content');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', function() {
            const targetTab = this.getAttribute('data-tab');
            
            // Remove active class from all buttons and contents
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));
            
            // Add active class to clicked button and target content
            this.classList.add('active');
            document.getElementById(targetTab).classList.add('active');
        });
    });
    
    // Password toggle functionality
    const passwordToggles = document.querySelectorAll('.password-toggle');
    passwordToggles.forEach(toggle => {
        toggle.addEventListener('click', function() {
            const input = this.previousElementSibling;
            const icon = this.querySelector('i');
            
            if (input.type === 'password') {
                input.type = 'text';
                icon.classList.remove('fa-eye');
                icon.classList.add('fa-eye-slash');
            } else {
                input.type = 'password';
                icon.classList.remove('fa-eye-slash');
                icon.classList.add('fa-eye');
            }
        });
    });
    
    // Dark mode toggle
    const darkModeToggle = document.getElementById('settingsDarkModeToggle');
    if (darkModeToggle) {
        // Set initial state based on current theme
        const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
        const isDarkMode = currentTheme === 'dark';
        darkModeToggle.checked = isDarkMode;
        
        darkModeToggle.addEventListener('change', function() {
            if (this.checked) {
                document.documentElement.setAttribute('data-theme', 'dark');
                localStorage.setItem('theme', 'dark');
            } else {
                document.documentElement.setAttribute('data-theme', 'light');
                localStorage.setItem('theme', 'light');
            }
        });
    }
});

// Update Profile Display Function
function updateProfileDisplay(userData, userStats) {
    // Update profile summary info
    const displayName = document.querySelector('.profile-summary-info h2');
    if (displayName && userData.display_name) {
        displayName.textContent = userData.display_name;
    }
    
    // Update profile stats
    const gamesCount = document.querySelector('.stat-item:has(.fa-gamepad)');
    if (gamesCount && userStats.games_count !== undefined) {
        gamesCount.textContent = `${userStats.games_count} Games`;
    }
    
    const platformsCount = document.querySelector('.stat-item:has(.fa-desktop)');
    if (platformsCount && userStats.platforms_count !== undefined) {
        platformsCount.textContent = `${userStats.platforms_count} Platforms`;
    }
    
    // Update about section
    updateAboutSection(userData.about);
    
    // Update profile details
    updateDetailItem('Username', userData.custom_username);
    updateDetailItem('Location', userData.location);
    updateDetailItem('Bio', userData.bio);
    updateDetailItem('Games', userData.games ? userData.games.join(', ') : null);
    updateDetailItem('Platforms', userData.platforms ? userData.platforms.join(', ') : null);
    
    // Update avatar if changed
    if (userData.profile_picture_url) {
        const profilePictures = document.querySelectorAll('.profile-summary-avatar img');
        profilePictures.forEach(img => {
            img.src = userData.profile_picture_url;
        });
    }
}

// Helper function to update detail items
function updateDetailItem(label, value) {
    const detailItems = document.querySelectorAll('.detail-item');
    detailItems.forEach(item => {
        const detailLabel = item.querySelector('.detail-label');
        if (detailLabel && detailLabel.textContent === label) {
            const detailValue = item.querySelector('.detail-value');
            if (detailValue) {
                detailValue.textContent = value || 'Not set';
            }
        }
    });
}

// Update about section
function updateAboutSection(aboutText) {
    const aboutTextElement = document.querySelector('.about-text');
    if (aboutTextElement) {
        if (aboutText) {
            aboutTextElement.textContent = aboutText;
            aboutTextElement.classList.remove('about-placeholder');
        } else {
            aboutTextElement.textContent = 'No about information added yet.';
            aboutTextElement.classList.add('about-placeholder');
        }
    }
}

// Success Message Handler
function showSuccessMessage(message) {
    const successDiv = document.getElementById('successMessage');
    if (successDiv) {
        const messageText = successDiv.querySelector('.success-message-text');
        if (messageText) {
            messageText.textContent = message;
        }
        
        successDiv.classList.add('show');
        
        setTimeout(() => {
            successDiv.classList.remove('show');
        }, 3000);
    }
}

// Delete Account Modal Functions
function showDeleteModal() {
    const modal = document.getElementById('deleteAccountModal');
    if (modal) {
        modal.classList.add('show');
    }
}

function hideDeleteModal() {
    const modal = document.getElementById('deleteAccountModal');
    if (modal) {
        modal.classList.remove('show');
    }
}

// Close modal when clicking directly on the dark backdrop only
document.addEventListener('click', function(e) {
    const modal = document.getElementById('deleteAccountModal');
    if (!modal) return;

    // Only close when the actual backdrop element itself is clicked,
    // not when interacting with inputs or content inside the modal.
    if (e.target === modal) {
        hideDeleteModal();
    }
});

// Handle delete account form submission
document.addEventListener('DOMContentLoaded', function() {
    const deleteForm = document.getElementById('deleteAccountForm');
    if (deleteForm) {
        deleteForm.addEventListener('submit', async function(e) {
            e.preventDefault();

            const password = document.getElementById('delete_password').value;
            const firebaseUid = document.getElementById('delete_firebase_uid').value;

            if (!password) {
                showToast('Please enter your password to confirm account deletion.', 'error');
                return;
            }

            const modal = document.getElementById('deleteAccountModal');
            if (!modal) {
                showToast('Unable to open confirmation modal', 'error');
                return;
            }

            // At this point the surrounding UI should already be showing a modal.
            // We just proceed with deletion after password verification.

            const submitBtn = this.querySelector('button[type="submit"]');
            const originalText = submitBtn.innerHTML;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Deleting Account...';
            submitBtn.disabled = true;

            try {
                showToast('Deleting account...', 'info');

                const firebaseModule = await import('/static/core/js/firebase-init.js');
                const { auth, signInWithEmailAndPassword } = firebaseModule;
                const emailElement = document.querySelector('.profile-summary-email');
                const email = emailElement ? emailElement.textContent.trim() : '';

                if (!email) {
                    showToast('Unable to get email address', 'error');
                    submitBtn.innerHTML = originalText;
                    submitBtn.disabled = false;
                    return;
                }

                try {
                    await signInWithEmailAndPassword(auth, email, password);
                } catch (firebaseError) {
                    if (firebaseError.code === 'auth/wrong-password' || firebaseError.code === 'auth/invalid-credential') {
                        showToast('Password is incorrect', 'error');
                    } else {
                        showToast('Failed to verify password', 'error');
                    }
                    submitBtn.innerHTML = originalText;
                    submitBtn.disabled = false;
                    return;
                }

                const response = await fetch('/accounts/delete-account/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                    },
                    body: JSON.stringify({
                        password: password,
                        firebase_uid: firebaseUid
                    })
                });

                const data = await response.json();

                if (data.success) {
                    showToast('Account permanently deleted', 'success');
                    setTimeout(() => {
                        window.location.href = data.redirect_url || '/accounts/login/';
                    }, 2000);
                } else {
                    showToast(data.message || 'Failed to delete account', 'error');
                    submitBtn.innerHTML = originalText;
                    submitBtn.disabled = false;
                }
            } catch (error) {
                console.error('Error deleting account:', error);
                showToast('Network error. Please try again.', 'error');
                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
            }
        });
    }
    
    // Handle password change form
    const changePasswordForm = document.getElementById('changePasswordForm');
    if (changePasswordForm) {
        changePasswordForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const currentPassword = document.getElementById('current_password').value;
            const newPassword = document.getElementById('new_password').value;
            const confirmPassword = document.getElementById('confirm_password').value;
            const firebaseUid = document.getElementById('firebase_uid').value;
            
            if (!currentPassword || !newPassword || !confirmPassword) {
                showToast('All password fields are required', 'error');
                return;
            }
            
            if (newPassword !== confirmPassword) {
                showToast('New passwords do not match', 'error');
                return;
            }
            
            if (newPassword.length < 6) {
                showToast('Password must be at least 6 characters long', 'error');
                return;
            }
            
            try {
                showToast('Changing password...', 'info');
                
                // Import Firebase auth functions dynamically
                const firebaseModule = await import('/static/core/js/firebase-init.js');
                const { auth, signInWithEmailAndPassword } = firebaseModule;
                
                // Get email from page data
                const emailElement = document.querySelector('.profile-summary-email');
                const email = emailElement ? emailElement.textContent.trim() : '';
                
                if (!email) {
                    showToast('Unable to get email address', 'error');
                    return;
                }
                
                try {
                    // Verify current password with Firebase
                    await signInWithEmailAndPassword(auth, email, currentPassword);
                    
                    // If successful, change password via API
                    const response = await fetch('/accounts/api/change-password/', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                        },
                        body: JSON.stringify({
                            current_password: currentPassword,
                            new_password: newPassword,
                            firebase_uid: firebaseUid
                        })
                    });
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        showToast('Password changed successfully', 'success');
                        changePasswordForm.reset();
                    } else {
                        showToast(data.message || 'Failed to change password', 'error');
                    }
                } catch (firebaseError) {
                    console.error('Firebase error:', firebaseError);
                    if (firebaseError.code === 'auth/wrong-password' || firebaseError.code === 'auth/invalid-credential') {
                        showToast('Current password is incorrect', 'error');
                    } else {
                        showToast('Failed to verify current password', 'error');
                    }
                }
            } catch (error) {
                console.error('Error changing password:', error);
                showToast('Network error. Please try again.', 'error');
            }
        });
    }
});

// Password toggle function
function togglePassword(inputId) {
    const input = document.getElementById(inputId);
    const toggle = input.parentElement.querySelector('.password-toggle');
    const icon = toggle.querySelector('i');
    
    if (input.type === 'password') {
        input.type = 'text';
        icon.classList.remove('fa-eye');
        icon.classList.add('fa-eye-slash');
    } else {
        input.type = 'password';
        icon.classList.remove('fa-eye-slash');
        icon.classList.add('fa-eye');
    }
}


