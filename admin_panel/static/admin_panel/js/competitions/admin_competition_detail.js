/**
 * admin_competition_detail.js
 * Handles all admin actions on the competition detail page:
 * - Approve modal (with prize form + dynamic prize type fields)
 * - Reject modal
 * - Suspend modal
 * - Edit Prizes modal
 * - Edit Results modal
 * - Confirm check-ins / Verify & publish results
 *
 * All config (URLs, slug, status) comes from data-* attributes on the
 * #competitionDetailApp container, and result rows come from the
 * #resultsData JSON script tag — nothing here depends on inline
 * <script> blocks in the template.
 */

const adminComp = (() => {

    let cfg = {};
    let resultsData = [];

    function readConfig() {
        const app = document.getElementById('competitionDetailApp');
        if (!app) return;
        cfg = {
            slug: app.dataset.slug,
            status: app.dataset.status,
            approveUrl: app.dataset.approveUrl,
            rejectUrl: app.dataset.rejectUrl,
            suspendUrl: app.dataset.suspendUrl,
            editPrizesUrl: app.dataset.editPrizesUrl,
            editResultsUrl: app.dataset.editResultsUrl,
            confirmCheckinsUrl: app.dataset.confirmCheckinsUrl,
            verifyResultsUrl: app.dataset.verifyResultsUrl,
        };

        const dataEl = document.getElementById('resultsData');
        if (dataEl) {
            try {
                resultsData = JSON.parse(dataEl.textContent);
            } catch (e) {
                console.error('Failed to parse results data', e);
                resultsData = [];
            }
        }
    }

    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
    }

    function csrfToken() {
        return getCookie('csrftoken') || '';
    }

    // ------------------------------------------------------------------
    // Generic Modal Helpers
    // ------------------------------------------------------------------

    function openModal(id) {
        const overlay = document.getElementById(id);
        if (!overlay) return;
        overlay.classList.add('show');
        document.body.style.overflow = 'hidden';

        if (id === 'approveModal') {
            const select = document.getElementById('approvePrizeType');
            if (select) updatePrizeFieldVisibility(select.value);
        }
        if (id === 'editPrizesModal') {
            const select = document.getElementById('editPrizeType');
            if (select) updateEditPrizeFieldVisibility(select.value);
        }
    }

    function closeModal(id) {
        const overlay = document.getElementById(id);
        if (!overlay) return;
        overlay.classList.remove('show');
        document.body.style.overflow = '';

        const form = overlay.querySelector('form');
        if (form) clearErrors(form);
        resetSubmitButton(id);
    }

    function resetSubmitButton(id) {
        const defaults = {
            approveModal: { id: 'approveSubmitBtn', html: '<i class="fas fa-check"></i> Approve & Go Live' },
            rejectModal: { id: 'rejectSubmitBtn', html: '<i class="fas fa-times"></i> Reject Competition' },
            suspendModal: { id: 'suspendSubmitBtn', html: '<i class="fas fa-ban"></i> Suspend & Refund' },
            editPrizesModal: { id: 'editPrizesSubmitBtn', html: '<i class="fas fa-save"></i> Save Changes' },
            editResultsModal: { id: 'editResultsSubmitBtn', html: '<i class="fas fa-save"></i> Save & Notify Gamers' },
        };
        const entry = defaults[id];
        if (!entry) return;
        const btn = document.getElementById(entry.id);
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = entry.html;
        }
    }

    function displayErrors(errors, prefix) {
        Object.keys(errors).forEach(field => {
            const el = document.getElementById(`${prefix}${field}`);
            if (el) {
                const msg = errors[field];
                el.textContent = Array.isArray(msg) ? msg[0] : msg;
            }
        });
    }

    function clearErrors(form) {
        form.querySelectorAll('.error-msg').forEach(el => el.textContent = '');
    }

    // ------------------------------------------------------------------
    // Approve
    // ------------------------------------------------------------------

    function updatePrizeFieldVisibility(type) {
        document.getElementById('pointsFields').style.display = type === 'points' ? 'block' : 'none';
        document.getElementById('moneyFields').style.display  = type === 'money'  ? 'block' : 'none';
        document.getElementById('giftFields').style.display   = type === 'gift'   ? 'block' : 'none';
    }

    async function submitApprove() {
        const form = document.getElementById('approveForm');
        const btn = document.getElementById('approveSubmitBtn');

        clearErrors(form);
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Approving...';

        try {
            const response = await fetch(cfg.approveUrl, {
                method: 'POST',
                body: new FormData(form),
                headers: { 'X-CSRFToken': csrfToken() },
            });
            const data = await response.json();

            if (data.success) {
                closeModal('approveModal');
                showToast('success', data.message || 'Competition approved and is now in registration!');
                setTimeout(() => window.location.reload(), 2000);
            } else {
                if (data.errors) displayErrors(data.errors, 'ap-err-');
                showToast('error', data.message || 'Please fix the errors below.');
                resetSubmitButton('approveModal');
            }
        } catch (err) {
            console.error('Approve error:', err);
            showToast('error', 'Something went wrong. Please try again.');
            resetSubmitButton('approveModal');
        }
    }

    // ------------------------------------------------------------------
    // Reject
    // ------------------------------------------------------------------

    async function submitReject() {
        const form = document.getElementById('rejectForm');
        const btn = document.getElementById('rejectSubmitBtn');
        const reason = document.getElementById('rejectionReason')?.value.trim();

        clearErrors(form);

        if (!reason) {
            document.getElementById('rej-err-rejection_reason').textContent = 'A rejection reason is required.';
            return;
        }

        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Rejecting...';

        try {
            const response = await fetch(cfg.rejectUrl, {
                method: 'POST',
                body: new FormData(form),
                headers: { 'X-CSRFToken': csrfToken() },
            });
            const data = await response.json();

            if (data.success) {
                closeModal('rejectModal');
                showToast('success', data.message || 'Competition rejected. Arena owner has been notified.');
                setTimeout(() => window.location.reload(), 2000);
            } else {
                if (data.errors) displayErrors(data.errors, 'rej-err-');
                showToast('error', data.message || 'Rejection failed. Please try again.');
                resetSubmitButton('rejectModal');
            }
        } catch (err) {
            console.error('Reject error:', err);
            showToast('error', 'Something went wrong. Please try again.');
            resetSubmitButton('rejectModal');
        }
    }

    // ------------------------------------------------------------------
    // Suspend
    // ------------------------------------------------------------------

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
                    'X-CSRFToken': csrfToken(),
                },
                body: JSON.stringify({ suspension_reason: reason }),
            });
            const data = await response.json();

            if (data.success) {
                closeModal('suspendModal');
                showToast('success', data.message || 'Competition suspended.');
                setTimeout(() => window.location.reload(), 2000);
            } else {
                showToast('error', data.message || 'Suspension failed.');
                resetSubmitButton('suspendModal');
            }
        } catch (err) {
            console.error('Suspend error:', err);
            showToast('error', 'Something went wrong.');
            resetSubmitButton('suspendModal');
        }
    }

    // ------------------------------------------------------------------
    // Edit Prizes
    // ------------------------------------------------------------------

    function updateEditPrizeFieldVisibility(type) {
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
                headers: { 'X-CSRFToken': csrfToken() },
            });
            const data = await response.json();

            if (data.success) {
                closeModal('editPrizesModal');
                showToast('success', data.message || 'Prize details updated.');
                setTimeout(() => window.location.reload(), 2000);
            } else {
                showToast('error', data.message || 'Failed to save prize details.');
                resetSubmitButton('editPrizesModal');
            }
        } catch (err) {
            console.error('Edit prizes error:', err);
            showToast('error', 'Something went wrong.');
            resetSubmitButton('editPrizesModal');
        }
    }

    // ------------------------------------------------------------------
    // Edit Results — populates the pre-built modal, never builds one at
    // runtime, so nothing appears until this explicitly shows it.
    // ------------------------------------------------------------------

    function openEditResultsModal() {
        if (!resultsData || !resultsData.length) {
            showToast('error', 'No results available to edit.');
            return;
        }

        const tbody = document.getElementById('editResultsTableBody');
        tbody.innerHTML = resultsData.map((row, idx) => `
            <tr>
                <td>${row.username}</td>
                <td><input type="number" min="1" class="form-control edit-rank" data-idx="${idx}" value="${row.rank ?? ''}"></td>
                <td><input type="checkbox" class="edit-noshow" data-idx="${idx}" ${row.is_no_show ? 'checked' : ''}></td>
            </tr>
        `).join('');

        openModal('editResultsModal');
    }

    async function submitEditResults() {
        const btn = document.getElementById('editResultsSubmitBtn');
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';

        const results = resultsData.map((row, idx) => ({
            gamer_id: row.gamer_id,
            rank: parseInt(document.querySelector(`.edit-rank[data-idx="${idx}"]`).value, 10) || null,
            is_no_show: document.querySelector(`.edit-noshow[data-idx="${idx}"]`).checked,
        }));

        try {
            const response = await fetch(cfg.editResultsUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken(),
                },
                body: JSON.stringify({ results }),
            });
            const data = await response.json();

            if (data.success) {
                closeModal('editResultsModal');
                showToast('success', data.message || 'Results updated.');
                setTimeout(() => window.location.reload(), 2000);
            } else {
                showToast('error', data.message || 'Failed to update results.');
                resetSubmitButton('editResultsModal');
            }
        } catch (err) {
            console.error('Edit results error:', err);
            showToast('error', 'Something went wrong.');
            resetSubmitButton('editResultsModal');
        }
    }

    // ------------------------------------------------------------------
    // Confirm Check-ins / Verify Results (confirm-dialog actions, no modal)
    // ------------------------------------------------------------------

    async function confirmCheckins() {
        if (!confirm('Confirm the check-in list? The arena owner will be notified to submit results.')) return;

        try {
            const formData = new FormData();
            formData.append('csrfmiddlewaretoken', csrfToken());

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

    async function verifyResults() {
        if (!confirm('Verify and publish these results? Gamers will be notified immediately.')) return;

        try {
            const formData = new FormData();
            formData.append('csrfmiddlewaretoken', csrfToken());

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
    // Wiring — one delegated listener for every [data-action] element,
    // plus overlay-click-to-close and prize-type select changes.
    // ------------------------------------------------------------------

    const actions = {
        'open-modal': (el) => openModal(el.dataset.modal),
        'close-modal': (el) => closeModal(el.dataset.modal),
        'open-edit-results': () => openEditResultsModal(),
        'submit-approve': () => submitApprove(),
        'submit-reject': () => submitReject(),
        'submit-suspend': () => submitSuspend(),
        'submit-edit-prizes': () => submitEditPrizes(),
        'submit-edit-results': () => submitEditResults(),
        'confirm-checkins': () => confirmCheckins(),
        'verify-results': () => verifyResults(),
    };

    function bindEvents() {
        document.addEventListener('click', (e) => {
            const trigger = e.target.closest('[data-action]');
            if (!trigger) return;
            const handler = actions[trigger.dataset.action];
            if (handler) {
                e.preventDefault();
                handler(trigger);
            }
        });

        document.addEventListener('change', (e) => {
            if (e.target.id === 'approvePrizeType') updatePrizeFieldVisibility(e.target.value);
            if (e.target.id === 'editPrizeType') updateEditPrizeFieldVisibility(e.target.value);
        });

        // Close modal when clicking the dimmed overlay itself
        document.querySelectorAll('.admin-modal-overlay').forEach((overlay) => {
            overlay.addEventListener('click', (e) => {
                if (e.target === overlay) closeModal(overlay.id);
            });
        });

        // Auto-open a modal when arriving from the list page's quick actions
        try {
            const params = new URLSearchParams(window.location.search);
            const action = params.get('action');
            if (action === 'approve') openModal('approveModal');
            if (action === 'reject') openModal('rejectModal');
        } catch (e) {
            console.warn('Auto-open action parse failed', e);
        }
    }

    function init() {
        readConfig();
        bindEvents();
    }

    document.addEventListener('DOMContentLoaded', init);

    // Public API (kept for any external callers / debugging)
    return {
        openModal,
        closeModal,
        submitApprove,
        submitReject,
        submitSuspend,
        submitEditPrizes,
        openEditResultsModal,
        submitEditResults,
        confirmCheckins,
        verifyResults,
    };

})();