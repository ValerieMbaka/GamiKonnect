/**
 * CompetitionDetail
 * Modern ES6 class replacement for the old IIFE-based competitionDetail.
 * Preserves the same public methods but exposes an instance on `window.competitionDetail`.
 */

class CompetitionDetail {
    constructor(config = window.COMP_DETAIL_CONFIG || {}) {
        this.config = config;

        this.modal = document.getElementById('detailRegisterModal');
        this.confirmBtn = document.getElementById('detailConfirmBtn');
        this.codeInput = document.getElementById('verifyCodeInput');
        this.feedback = document.getElementById('verifyFeedback');
        this.verifyBtn = document.querySelector('.comp-verify-btn');

        this.bindEvents();
    }

    bindEvents() {
        if (this.modal) {
            this.modal.addEventListener('click', (e) => {
                if (e.target === this.modal) this.closeRegisterModal();
            });
        }

        if (this.confirmBtn) {
            this.confirmBtn.addEventListener('click', () => this.confirmRegister());
        }

        if (this.codeInput) {
            this.codeInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    this.verifyGamer();
                }
            });
        }

        // Optional: bind any register buttons that use a class
        document.querySelectorAll('.detail-register-btn').forEach(btn => {
            btn.addEventListener('click', () => this.register());
        });
    }

    // Gamer — Registration
    register() {
        if (!this.modal) return;
        this.modal.classList.add('show');
        document.body.style.overflow = 'hidden';
    }

    closeRegisterModal() {
        if (!this.modal) return;
        this.modal.classList.remove('show');
        document.body.style.overflow = '';
        this.resetConfirmBtn();
    }

    resetConfirmBtn() {
        if (!this.confirmBtn) return;
        this.confirmBtn.disabled = false;
        this.confirmBtn.innerHTML = '<i class="fas fa-check"></i> Confirm Registration';
    }

    async confirmRegister() {
        if (!this.config?.registerUrl) return;

        if (this.confirmBtn) {
            this.confirmBtn.disabled = true;
            this.confirmBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Registering...';
        }

        try {
            const formData = new FormData();
            formData.append('csrfmiddlewaretoken', this.config.csrfToken);

            const resp = await fetch(this.config.registerUrl, { method: 'POST', body: formData });
            const data = await resp.json();

            if (data.success) {
                this.closeRegisterModal();
                showToast('success', data.message || 'Registration successful! Check your email for your unique code.');
                setTimeout(() => window.location.reload(), 2000);
            } else {
                this.closeRegisterModal();
                showToast('error', data.message || 'Registration failed. Please try again.');
                this.resetConfirmBtn();
            }
        } catch (err) {
            console.error('Registration error:', err);
            this.closeRegisterModal();
            showToast('error', 'Something went wrong. Please try again.');
            this.resetConfirmBtn();
        }
    }

    // Gamer — Copy Unique Code
    copyCode() {
        const codeEl = document.getElementById('uniqueCode');
        if (!codeEl) return;

        const code = codeEl.textContent.trim();
        navigator.clipboard.writeText(code).then(() => showToast('success', 'Registration code copied to clipboard!')).catch(() => {
            const textarea = document.createElement('textarea');
            textarea.value = code;
            textarea.style.position = 'fixed';
            textarea.style.opacity = '0';
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand('copy');
            document.body.removeChild(textarea);
            showToast('success', 'Code copied!');
        });
    }

    // Shop Owner — Verify Gamer
    async verifyGamer() {
        const code = this.codeInput?.value.trim() || '';
        if (!code) {
            this.showFeedback('error', 'Please enter a registration code.');
            return;
        }

        if (this.verifyBtn) {
            this.verifyBtn.disabled = true;
            this.verifyBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Verifying...';
        }

        try {
            const formData = new FormData();
            formData.append('csrfmiddlewaretoken', this.config.csrfToken);
            formData.append('unique_code', code);

            const resp = await fetch(this.config.verifyUrl, { method: 'POST', body: formData });
            const data = await resp.json();

            if (data.success) {
                this.showFeedback('success', `✓ ${data.message}`);
                if (this.codeInput) this.codeInput.value = '';
                if (data.gamer) this.addToVerifiedList(data);
                showToast('success', data.message);
            } else {
                this.showFeedback('error', data.message || 'Verification failed.');
                showToast('error', data.message || 'Verification failed.');
            }
        } catch (err) {
            console.error('Verification error:', err);
            this.showFeedback('error', 'Something went wrong. Please try again.');
        } finally {
            if (this.verifyBtn) {
                this.verifyBtn.disabled = false;
                this.verifyBtn.innerHTML = '<i class="fas fa-check-circle"></i> Verify';
            }
        }
    }

    showFeedback(type, message) {
        if (!this.feedback) return;
        this.feedback.className = `comp-verify-feedback ${type}`;
        this.feedback.textContent = message;
        this.feedback.style.display = 'block';
        setTimeout(() => { if (this.feedback) this.feedback.style.display = 'none'; }, 5000);
    }

    addToVerifiedList(data) {
        const list = document.getElementById('verifiedList');
        if (!list) return;
        const placeholder = list.querySelector('.comp-no-verified');
        if (placeholder) placeholder.remove();

        // Update the registration row if it exists
        const regRow = document.getElementById(`regRow-${data.registration_id}`);
        if (regRow) {
            regRow.classList.add('checked-in');
            const statusBadge = regRow.querySelector('.reg-status-badge');
            if (statusBadge) {
                statusBadge.className = 'reg-status-badge checked-in';
                statusBadge.innerHTML = '<i class="fas fa-check-circle"></i> Checked In';
            }
        }

        const gamer = data.gamer;
        const item = document.createElement('div');
        item.className = 'comp-verified-item anim-pop-in';
        item.id = `verified-${data.registration_id}`;
        item.innerHTML = `
            <div class="verified-gamer-info">
                ${gamer.profile_picture ? `<img src="${gamer.profile_picture}" class="verified-avatar">` : '<i class="fas fa-user-circle fs-4 text-muted"></i>'}
                <div class="ms-2">
                    <span class="fw-bold d-block">${gamer.name}</span>
                    <span class="text-muted small">@${gamer.username || 'gamer'}</span>
                </div>
            </div>
            <span class="verified-time"><i class="fas fa-check-circle text-success me-1"></i> ${gamer.checked_in_at || ''}</span>
        `;
        list.prepend(item);
    }

    // Shop Owner — Submit Check-ins
    async submitCheckins() {
        if (!confirm('Submit the check-in list to the admin for review? Make sure all gamers have been verified before proceeding.')) return;

        try {
            const formData = new FormData();
            formData.append('csrfmiddlewaretoken', this.config.csrfToken);

            const resp = await fetch(this.config.submitCheckinsUrl, { method: 'POST', body: formData });
            const data = await resp.json();

            if (data.success) {
                showToast('success', data.message || 'Check-in list submitted successfully!');
                setTimeout(() => window.location.reload(), 2000);
            } else {
                showToast('error', data.message || 'Submission failed. Please try again.');
            }
        } catch (err) {
            console.error('Check-in submission error:', err);
            showToast('error', 'Something went wrong. Please try again.');
        }
    }

    // Shop Owner — Submit Results
    async submitResults() {
        const entries = document.querySelectorAll('.comp-result-entry');
        const results = [];
        let hasError = false;

        entries.forEach(entry => {
            const gamerId = entry.dataset.gamerId;
            const rankInput = entry.querySelector('.result-rank-input');
            const noShowCheck = entry.querySelector('.result-noshow-check');

            const isNoShow = noShowCheck?.checked || false;
            const rank = rankInput ? parseInt(rankInput.value) : null;

            if (!isNoShow && (!rank || rank < 1)) {
                showToast('error', 'Please assign a rank to all participating gamers.');
                hasError = true;
                return;
            }

            results.push({ gamer_id: gamerId, rank: isNoShow ? null : rank, is_no_show: isNoShow });
        });

        if (hasError) return;

        const ranks = results.filter(r => !r.is_no_show).map(r => r.rank);
        const uniqueRanks = new Set(ranks);
        if (ranks.length !== uniqueRanks.size) { showToast('error', 'Duplicate ranks detected. Each gamer must have a unique rank.'); return; }

        if (!confirm('Submit these results? Once submitted, points will be allocated automatically for points-based competitions.')) return;

        const submitBtn = document.querySelector('.comp-results-submit-row .comp-action-btn');
        if (submitBtn) { submitBtn.disabled = true; submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Submitting...'; }

        try {
            const formData = new FormData();
            formData.append('csrfmiddlewaretoken', this.config.csrfToken);
            formData.append('results', JSON.stringify(results));

            const resp = await fetch(this.config.submitResultsUrl, { method: 'POST', body: formData });
            const data = await resp.json();

            if (data.success) {
                showToast('success', data.message || 'Results submitted successfully!');
                setTimeout(() => window.location.reload(), 2500);
            } else {
                showToast('error', data.message || 'Submission failed. Please try again.');
                if (submitBtn) { submitBtn.disabled = false; submitBtn.innerHTML = '<i class="fas fa-paper-plane"></i> Submit Results'; }
            }
        } catch (err) {
            console.error('Results submission error:', err);
            showToast('error', 'Something went wrong. Please try again.');
            if (submitBtn) { submitBtn.disabled = false; submitBtn.innerHTML = '<i class="fas fa-paper-plane"></i> Submit Results'; }
        }
    }

    // No-show Toggle
    toggleNoShow(checkbox) {
        const gamerId = checkbox.dataset.gamerId;
        const rankInput = document.querySelector(`.result-rank-input[data-gamer-id="${gamerId}"]`);
        if (rankInput) { rankInput.disabled = checkbox.checked; if (checkbox.checked) rankInput.value = ''; }
    }

    static initialize(config) {
        const init = () => {
            const inst = new CompetitionDetail(config);
            window.competitionDetail = inst;
            // Expose for compatibility with older inline onclick handlers
            window.verifyGamer = () => inst.verifyGamer();
            window.submitCheckins = () => inst.submitCheckins();
            window.submitResults = () => inst.submitResults();
            window.register = () => inst.register();
            window.closeRegisterModal = () => inst.closeRegisterModal();
            window.copyCode = () => inst.copyCode();
        };

        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', init);
        } else {
            init();
        }
    }
}

// Auto-initialize and expose instance for backward compatibility
CompetitionDetail.initialize(window.COMP_DETAIL_CONFIG);
