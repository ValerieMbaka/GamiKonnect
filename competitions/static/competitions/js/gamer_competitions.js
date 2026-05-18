/**
 * gamer_competitions.js
 * Handles interactions on the My Competitions page:
 * - Tab switching between Upcoming and Past
 * - Unique code copy
 */

const myCompetitions = (() => {

    // ------------------------------------------------------------------
    // Tab Switching
    // ------------------------------------------------------------------

    function initTabs() {
        const tabs = document.querySelectorAll('.my-comp-tab');
        const contents = document.querySelectorAll('.my-comp-tab-content');

        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const targetTab = tab.dataset.tab;

                // Update tab active state
                tabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');

                // Update content visibility
                contents.forEach(content => {
                    content.classList.remove('active');
                    if (content.id === `tab-${targetTab}`) {
                        content.classList.add('active');
                    }
                });
            });
        });
    }

    // ------------------------------------------------------------------
    // Copy Unique Code
    // ------------------------------------------------------------------

    function copyCode(elementId) {
        const codeEl = document.getElementById(elementId);
        if (!codeEl) return;

        const code = codeEl.textContent.trim();

        navigator.clipboard.writeText(code).then(() => {
            showToast('success', 'Registration code copied to clipboard!');
        }).catch(() => {
            // Fallback
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

    // ------------------------------------------------------------------
    // Init
    // ------------------------------------------------------------------

    function init() {
        initTabs();
    }

    document.addEventListener('DOMContentLoaded', init);

    // Public API
    return {
        copyCode,
    };

})();