/**
 * admin_competition_detail.js
 * Handles all admin actions on the competition detail page:
 * - Approve modal (with prize form + dynamic prize type fields)
 * - Reject modal
 * - Confirm check-ins
 * - Verify & publish results
 */

const adminComp = (() => {

    const cfg = ADMIN_COMP_CONFIG;

    // ------------------------------------------------------------------
    // Approve Modal
    // ------------------------------------------------------------------

    function openApproveModal() {
        document.getElementById('approveModal').classList.add('show');
        document.body.style.overflow = 'hidden';
    }

    function closeApproveModal() {
        document.getElementById('approveModal').classList.remove('show');
        document.body.style.overflow = '';
        clearErrors('approveForm');
        resetApproveBtn();
    }

    function resetApproveBtn() {
        const btn = document.getElementById('approveSubmitBtn');
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-check"></i> Approve & Go Live';
        }
    }

    // Show/hide prize fields based on selected prize type
    function onPrizeTypeChange(select) {
        const type = select.value;
        document.getElementById('pointsFields').style.display = type === 'points' ? 'block' : 'none';
        document.getElementById('moneyFields').style.display  = type === 'money'  ? 'block' : 'none';
        document.getElementById('giftFields').style.display   = type === 'gift'   ? 'block' : 'none';
    }

    async function submitApprove() {
        const form = document.getElementById('approveForm');
        const btn = document.getElementById('approveSubmitBtn');

        clearErrors('approveForm');

        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Approving...';

        try {
            const formData = new FormData(form);

            const response = await fetch(cfg.approveUrl, {
                method: 'POST',
                body: formData,
                headers: { 'X-CSRFToken': cfg.csrfToken },
            });

            const data = await response.json();

            if (data.success) {
                closeApproveModal();
                showToast('success', data.message || 'Competition approved and is now in registration!');
                setTimeout(() => window.location.reload(), 2000);
            } else {
                if (data.errors) displayErrors(data.errors, 'ap-err-');
                showToast('error', data.message || 'Please fix the errors below.');
                resetApproveBtn();
            }
        } catch (err) {
            console.error('Approve error:', err);
            showToast('error', 'Something went wrong. Please try again.');
            resetApproveBtn();
        }
    }

    // ------------------------------------------------------------------
    // Reject Modal
    // ------------------------------------------------------------------

    function openRejectModal() {
        document.getElementById('rejectModal').classList.add('show');
        document.body.style.overflow = 'hidden';
    }

    function closeRejectModal() {
        document.getElementById('rejectModal').classList.remove('show');
        document.body.style.overflow = '';
        clearErrors('rejectForm');
        resetRejectBtn();
    }

    function resetRejectBtn() {
        const btn = document.getElementById('rejectSubmitBtn');
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-times"></i> Reject Competition';
        }
    }

    async function submitReject() {
        const form = document.getElementById('rejectForm');
        const btn = document.getElementById('rejectSubmitBtn');
        const reason = document.getElementById('rejectionReason')?.value.trim();

        clearErrors('rejectForm');

        if (!reason) {
            document.getElementById('rej-err-rejection_reason').textContent = 'A rejection reason is required.';
            return;
        }

        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Rejecting...';

        try {
            const formData = new FormData(form);

            const response = await fetch(cfg.rejectUrl, {
                method: 'POST',
                body: formData,
                headers: { 'X-CSRFToken': cfg.csrfToken },
            });

            const data = await response.json();

            if (data.success) {
                closeRejectModal();
                showToast('success', data.message || 'Competition rejected. Arena owner has been notified.');
                setTimeout(() => window.location.reload(), 2000);
            } else {
                if (data.errors) displayErrors(data.errors, 'rej-err-');
                showToast('error', data.message || 'Rejection failed. Please try again.');
                resetRejectBtn();
            }
        } catch (err) {
            console.error('Reject error:', err);
            showToast('error', 'Something went wrong. Please try again.');
            resetRejectBtn();
        }
    }

    // ------------------------------------------------------------------
    // Confirm Check-ins
    // ------------------------------------------------------------------

    async function confirmCheckins() {
        if (!confirm('Confirm the check-in list? The arena owner will be notified to submit results.')) return;

        try {
            const formData = new FormData();
            formData.append('csrfmiddlewaretoken', cfg.csrfToken);

            const response = await fetch(cfg.confirmCheckinsUrl, {
                method: 'POST',
                body: formData,
            });

            const data = await response.json();

            if (data.success) {
                showToast('success', data.message || 'Check-ins confirmed. Arena owner notified.');
                setTimeout(() => window.location.reload(), 2000);
            } else {
                showToast('error', data.message || 'Failed to confirm check-ins.');
            }
        } catch (err) {
            console.error('Confirm checkins error:', err);
            showToast('error', 'Something went wrong. Please try again.');
        }
    }

    // ------------------------------------------------------------------
    // Verify Results
    // ------------------------------------------------------------------

    async function verifyResults() {
        if (!confirm('Verify and publish these results? Gamers will be notified immediately.')) return;

        try {
            const formData = new FormData();
            formData.append('csrfmiddlewaretoken', cfg.csrfToken);

            const response = await fetch(cfg.verifyResultsUrl, {
                method: 'POST',
                body: formData,
            });

            const data = await response.json();

            if (data.success) {
                showToast('success', data.message || 'Results verified and published!');
                setTimeout(() => window.location.reload(), 2000);
            } else {
                showToast('error', data.message || 'Verification failed.');
            }
        } catch (err) {
            console.error('Verify results error:', err);
            showToast('error', 'Something went wrong. Please try again.');
        }
    }

    // ------------------------------------------------------------------
    // Error Helpers
    // ------------------------------------------------------------------

    function displayErrors(errors, prefix) {
        Object.keys(errors).forEach(field => {
            const el = document.getElementById(`${prefix}${field}`);
            if (el) {
                const msg = errors[field];
                el.textContent = Array.isArray(msg) ? msg[0] : msg;
            }
        });
    }

    function clearErrors(formId) {
        const form = document.getElementById(formId);
        if (!form) return;
        form.querySelectorAll('.error-msg').forEach(el => el.textContent = '');
    }

    // ------------------------------------------------------------------
    // Close Modals on Overlay Click
    // ------------------------------------------------------------------

    function init() {
        ['approveModal', 'rejectModal'].forEach(id => {
            const overlay = document.getElementById(id);
            if (overlay) {
                overlay.addEventListener('click', (e) => {
                    if (e.target === overlay) {
                        if (id === 'approveModal') closeApproveModal();
                        else closeRejectModal();
                    }
                });
            }
        });
    }

    document.addEventListener('DOMContentLoaded', init);

    // Public API
    return {
        openApproveModal,
        closeApproveModal,
        submitApprove,
        onPrizeTypeChange,
        openRejectModal,
        closeRejectModal,
        submitReject,
        confirmCheckins,
        verifyResults,
    };

})();