// Shop Owner delete account behavior

function showShopOwnerDeleteModal() {
    const modal = document.getElementById('shopOwnerDeleteAccountModal');
    if (modal) {
        modal.classList.add('show');
    }
}

function hideShopOwnerDeleteModal() {
    const modal = document.getElementById('shopOwnerDeleteAccountModal');
    if (modal) {
        modal.classList.remove('show');
    }
}

// Close modal when clicking on backdrop
window.addEventListener('click', function (e) {
    const modal = document.getElementById('shopOwnerDeleteAccountModal');
    if (modal && e.target === modal) {
        hideShopOwnerDeleteModal();
    }
});

// Simple toast helper (reuse global if present)
function shopOwnerShowToast(message, type = 'info') {
    if (window.toastManager) {
        window.toastManager.show({ type, title: type === 'error' ? 'Error' : 'Notice', message });
        return;
    }
    if (window.showToast) {
        window.showToast(message, type);
        return;
    }
    alert(message);
}

// Handle delete form submission

document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('shopOwnerDeleteAccountForm');
    if (!form) return;

    form.addEventListener('submit', async function (e) {
        e.preventDefault();

        const passwordInput = document.getElementById('shop_owner_delete_password');
        const firebaseUidInput = document.getElementById('shop_owner_delete_firebase_uid');
        const password = passwordInput ? passwordInput.value : '';
        const firebaseUid = firebaseUidInput ? firebaseUidInput.value : '';

        if (!password) {
            shopOwnerShowToast('Please enter your password to confirm account deletion.', 'error');
            return;
        }

        const submitBtn = form.querySelector('button[type="submit"]');
        const originalHtml = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Deleting Account...';

        try {
            shopOwnerShowToast('Deleting account...', 'info');

            const firebaseModule = await import('/static/core/js/firebase-init.js');
            const { auth, signInWithEmailAndPassword } = firebaseModule;

            const emailElement = document.querySelector('.settings-card input[type="email"]');
            const email = emailElement ? emailElement.value.trim() : '';

            if (!email) {
                shopOwnerShowToast('Unable to get email address', 'error');
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalHtml;
                return;
            }

            try {
                await signInWithEmailAndPassword(auth, email, password);
            } catch (firebaseError) {
                if (firebaseError.code === 'auth/wrong-password' || firebaseError.code === 'auth/invalid-credential') {
                    shopOwnerShowToast('Password is incorrect', 'error');
                } else {
                    shopOwnerShowToast('Failed to verify password', 'error');
                }
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalHtml;
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
                shopOwnerShowToast('Account permanently deleted', 'success');
                setTimeout(() => {
                    window.location.href = data.redirect_url || '/accounts/login/';
                }, 2000);
            } else {
                shopOwnerShowToast(data.message || 'Failed to delete account', 'error');
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalHtml;
            }
        } catch (err) {
            console.error('Error deleting shop owner account:', err);
            shopOwnerShowToast('Network error. Please try again.', 'error');
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalHtml;
        }
    });
});
