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
    // Suspend Modal
    // ------------------------------------------------------------------

    function openSuspendModal() {
        document.getElementById('suspendModal').classList.add('show');
        document.body.style.overflow = 'hidden';
    }

    function closeSuspendModal() {
        document.getElementById('suspendModal').classList.remove('show');
        document.body.style.overflow = '';
    }

    async function submitSuspend() {
        const reason = document.getElementById('suspensionReason')?.value.trim();
        if (!reason) {
            document.getElementById('sus-err-suspension_reason').textContent = 'A suspension reason is required.';
            return;
        }

        const btn = document.getElementById('suspendSubmitBtn');
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Suspending...';

        try {
            const response = await fetch(cfg.suspendUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': cfg.csrfToken,
                },
                body: JSON.stringify({ suspension_reason: reason }),
            });
            const data = await response.json();

            if (data.success) {
                closeSuspendModal();
                showToast('success', data.message);
                setTimeout(() => window.location.reload(), 2000);
            } else {
                showToast('error', data.message || 'Suspension failed.');
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-ban"></i> Suspend & Refund';
            }
        } catch (err) {
            console.error('Suspend error:', err);
            showToast('error', 'Something went wrong.');
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-ban"></i> Suspend & Refund';
        }
    }

    // ------------------------------------------------------------------
    // Edit Prizes Modal
    // ------------------------------------------------------------------

    function openEditPrizesModal() {
        document.getElementById('editPrizesModal').classList.add('show');
        document.body.style.overflow = 'hidden';
        const prizeSelect = document.getElementById('editPrizeType');
        if (prizeSelect) onEditPrizeTypeChange(prizeSelect);
    }

    function closeEditPrizesModal() {
        document.getElementById('editPrizesModal').classList.remove('show');
        document.body.style.overflow = '';
    }

    function onEditPrizeTypeChange(select) {
        const type = select.value;
        document.getElementById('editPointsFields').style.display = 'block';
        document.getElementById('editMoneyFields').style.display = type === 'money' ? 'block' : 'none';
        document.getElementById('editGiftFields').style.display = type === 'gift' ? 'block' : 'none';
    }

    async function submitEditPrizes() {
        const form = document.getElementById('editPrizesForm');
        const btn = document.getElementById('editPrizesSubmitBtn');
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';

        try {
            const response = await fetch(cfg.editPrizesUrl, {
                method: 'POST',
                body: new FormData(form),
                headers: { 'X-CSRFToken': cfg.csrfToken },
            });
            const data = await response.json();

            if (data.success) {
                closeEditPrizesModal();
                showToast('success', data.message);
                setTimeout(() => window.location.reload(), 2000);
            } else {
                showToast('error', data.message || 'Failed to save prize details.');
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-save"></i> Save Changes';
            }
        } catch (err) {
            console.error('Edit prizes error:', err);
            showToast('error', 'Something went wrong.');
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-save"></i> Save Changes';
        }
    }

    // ------------------------------------------------------------------
    // Edit Results
    // ------------------------------------------------------------------

    function openEditResultsModal() {
        if (!cfg.resultsData || !cfg.resultsData.length) {
            showToast('error', 'No results available to edit.');
            return;
        }

        let html = '<table class="modern-table"><thead><tr><th>Gamer</th><th>Rank</th><th>No-show</th></tr></thead><tbody>';
        cfg.resultsData.forEach((row, idx) => {
            html += `<tr>
                <td>${row.username}</td>
                <td><input type="number" min="1" class="form-control edit-rank" data-idx="${idx}" value="${row.rank || ''}"></td>
                <td><input type="checkbox" class="edit-noshow" data-idx="${idx}" ${row.is_no_show ? 'checked' : ''}></td>
            </tr>`;
        });
        html += '</tbody></table>';

        const container = document.createElement('div');
        container.innerHTML = html;
        const confirmed = confirm('Edit results in the prompt that follows. Click OK to open the editor.');

        if (!confirmed) return;

        const modal = document.createElement('div');
        modal.className = 'admin-modal-overlay show';
        modal.innerHTML = `
            <div class="admin-modal" style="max-width:640px;">
                <div class="modal-header"><h3>Edit Results</h3></div>
                <div class="modal-body">${container.innerHTML}</div>
                <div class="modal-footer mt-4">
                    <button class="btn-admin-secondary" id="cancelEditResults">Cancel</button>
                    <button class="btn-admin-primary" id="saveEditResults">Save & Notify Gamers</button>
                </div>
            </div>`;
        document.body.appendChild(modal);

        modal.querySelector('#cancelEditResults').onclick = () => modal.remove();
        modal.querySelector('#saveEditResults').onclick = async () => {
            const results = cfg.resultsData.map((row, idx) => ({
                gamer_id: row.gamer_id,
                rank: parseInt(modal.querySelector(`.edit-rank[data-idx="${idx}"]`).value, 10) || null,
                is_no_show: modal.querySelector(`.edit-noshow[data-idx="${idx}"]`).checked,
            }));

            try {
                const response = await fetch(cfg.editResultsUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': cfg.csrfToken,
                    },
                    body: JSON.stringify({ results }),
                });
                const data = await response.json();
                if (data.success) {
                    modal.remove();
                    showToast('success', data.message);
                    setTimeout(() => window.location.reload(), 2000);
                } else {
                    showToast('error', data.message || 'Failed to update results.');
                }
            } catch (err) {
                showToast('error', 'Something went wrong.');
            }
        };
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
        ['approveModal', 'rejectModal', 'suspendModal', 'editPrizesModal'].forEach(id => {
            const overlay = document.getElementById(id);
            if (overlay) {
                overlay.addEventListener('click', (e) => {
                    if (e.target === overlay) {
                        if (id === 'approveModal') closeApproveModal();
                        else if (id === 'rejectModal') closeRejectModal();
                        else if (id === 'suspendModal') closeSuspendModal();
                        else if (id === 'editPrizesModal') closeEditPrizesModal();
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
        openSuspendModal,
        closeSuspendModal,
        submitSuspend,
        openEditPrizesModal,
        closeEditPrizesModal,
        onEditPrizeTypeChange,
        submitEditPrizes,
        openEditResultsModal,
        confirmCheckins,
        verifyResults,
    };

})();