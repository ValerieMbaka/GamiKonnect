/**
 * admin_competitions.js
 * Handles the admin competition list page:
 * - Search filter on Enter key
 */

document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.querySelector('.filter-group input[name="q"]');
    if (searchInput) {
        searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                searchInput.closest('form').submit();
            }
        });
    }
    // Inline approve/reject handlers
    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
    }

    function postJson(url, body) {
        return fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCookie('csrftoken') || ''
            },
            body: JSON.stringify(body || {})
        }).then(res => res.json());
    }

    document.querySelectorAll('a.ajax-approve').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const url = btn.dataset.approveUrl;
            const compId = btn.dataset.compId;
            btn.classList.add('loading');
            postJson(url, {}).then(data => {
                btn.classList.remove('loading');
                if (data && data.success) {
                    const row = document.getElementById(`comp-row-${compId}`);
                    if (row) {
                        const statusBadge = row.querySelector('.status-badge');
                        if (statusBadge) {
                            statusBadge.className = 'status-badge approved';
                            statusBadge.textContent = 'Live';
                        }
                        const actions = row.querySelector('.action-buttons');
                        if (actions) actions.innerHTML = `<a href="/admin_panel/competitions/${compId}/" class="btn-action view" data-tooltip="View & Manage"><i class="fas fa-arrow-right"></i></a>`;
                    }
                } else {
                    window.toastManager?.error('Approval Failed', (data && data.message) || 'Approval failed.');
                }
            }).catch(err => {
                btn.classList.remove('loading');
                console.error(err);
                window.toastManager?.error('Approval Failed', 'Approval failed.');
            });
        });
    });

    // Reject flow uses modal instead of prompt
    const rejectModal = document.getElementById('adminRejectModal');
    const rejectReasonInput = document.getElementById('rejectReason');
    const rejectCancel = document.getElementById('rejectCancel');
    const rejectSubmit = document.getElementById('rejectSubmit');
    let currentReject = { url: null, compId: null, btn: null };

    function showRejectModal(url, compId, btn) {
        currentReject.url = url;
        currentReject.compId = compId;
        currentReject.btn = btn;
        if (rejectReasonInput) rejectReasonInput.value = '';
        if (rejectModal) {
            rejectModal.style.display = 'block';
            rejectModal.classList.add('show');
        }
    }

    function hideRejectModal() {
        if (rejectModal) {
            rejectModal.style.display = 'none';
            rejectModal.classList.remove('show');
        }
        currentReject = { url: null, compId: null, btn: null };
    }

    // Wire modal controls
    document.querySelectorAll('a.ajax-reject').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const url = btn.dataset.rejectUrl;
            const compId = btn.dataset.compId;
            showRejectModal(url, compId, btn);
        });
    });

    if (rejectCancel) rejectCancel.addEventListener('click', hideRejectModal);
    const closeBtns = rejectModal?.querySelectorAll('.close-modal') || [];
    closeBtns.forEach(b => b.addEventListener('click', hideRejectModal));

    if (rejectSubmit) rejectSubmit.addEventListener('click', () => {
        const reason = rejectReasonInput?.value?.trim();
        if (!reason) {
            window.toastManager?.warning('Validation', 'Please enter a rejection reason.');
            return;
        }
        const btn = currentReject.btn;
        if (btn) btn.classList.add('loading');
        postJson(currentReject.url, { 'rejection_reason': reason }).then(data => {
            if (btn) btn.classList.remove('loading');
            if (data && data.success) {
                const compId = currentReject.compId;
                const row = document.getElementById(`comp-row-${compId}`);
                if (row) {
                    const statusBadge = row.querySelector('.status-badge');
                    if (statusBadge) {
                        statusBadge.className = 'status-badge rejected';
                        statusBadge.textContent = 'Rejected';
                    }
                    const actions = row.querySelector('.action-buttons');
                    if (actions) actions.innerHTML = `<a href="/admin_panel/competitions/${compId}/" class="btn-action view" data-tooltip="View & Manage"><i class="fas fa-arrow-right"></i></a>`;
                }
                hideRejectModal();
                window.toastManager?.success('Rejected', data.message || 'Competition rejected.');
            } else {
                window.toastManager?.error('Rejection Failed', (data && data.message) || 'Rejection failed.');
            }
        }).catch(err => {
            if (btn) btn.classList.remove('loading');
            console.error(err);
            window.toastManager?.error('Rejection Failed', 'Rejection failed.');
        });
    });
});