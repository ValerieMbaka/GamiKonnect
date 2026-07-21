/**
 * CompetitionCommon
 * Shared utilities used by both the browse-competitions page and the
 * my-competitions page:
 *   - copyToClipboard(text, successMessage)
 *   - global Escape-key / backdrop-click dismissal for `.modal-backdrop`
 *
 * Load this before competition_list.js / gamer_competitions.js.
 */

const CompetitionCommon = (() => {

    // ------------------------------------------------------------------
    // Clipboard
    // ------------------------------------------------------------------

    function copyToClipboard(text, successMessage = 'Copied to clipboard!') {
        if (!text) return;

        const notify = () => {
            if (typeof showToast !== 'undefined') {
                showToast('success', successMessage);
            }
        };

        if (navigator.clipboard && window.isSecureContext) {
            navigator.clipboard.writeText(text).then(notify).catch(() => fallbackCopy(text, notify));
        } else {
            fallbackCopy(text, notify);
        }
    }

    function fallbackCopy(text, onSuccess) {
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        try {
            document.execCommand('copy');
            onSuccess();
        } finally {
            document.body.removeChild(textarea);
        }
    }

    // ------------------------------------------------------------------
    // Modal dismissal (Escape key + backdrop click)
    // Any open modal should be wrapped by #modalBackdrop, matching the
    // pattern already used for the registration modal.
    // ------------------------------------------------------------------

    function closeOpenModal() {
        const backdrop = document.getElementById('modalBackdrop');
        if (!backdrop || backdrop.classList.contains('hidden')) return;

        document.querySelectorAll('.modal-container').forEach(modal => {
            modal.classList.add('hidden');
        });
        backdrop.classList.add('hidden');
        document.body.classList.remove('modal-open');
    }

    function initModalDismissal() {
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') closeOpenModal();
        });

        document.addEventListener('click', (e) => {
            if (e.target && e.target.id === 'modalBackdrop') closeOpenModal();
        });
    }

    function init() {
        initModalDismissal();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    return {
        copyToClipboard,
        closeOpenModal,
    };

})();