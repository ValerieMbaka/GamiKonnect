class AccountManager {
    constructor() {
        this.initTabs();
        this.initSwitches();
        this.initLocalModal();
    }

    /**
     * Handles switching between General and Security tabs
     */
    initTabs() {
        const tabBtns = document.querySelectorAll('.tab-btn');
        const tabPanes = document.querySelectorAll('.tab-pane');

        tabBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                tabBtns.forEach(b => b.classList.remove('active'));
                tabPanes.forEach(p => p.classList.add('d-none'));

                e.currentTarget.classList.add('active');

                const targetId = e.currentTarget.dataset.target;
                const targetPane = document.getElementById(targetId);
                if (targetPane) {
                    targetPane.classList.remove('d-none');
                    targetPane.style.animation = 'none';
                    void targetPane.offsetHeight; // Reflow
                    targetPane.style.animation = 'fadeInUp 0.3s ease-out forwards';
                }
            });
        });
    }

    /**
     * Handles UI toggles like MFA
     * Note: Dark mode is now handled globally by ThemeManager!
     */
    initSwitches() {
        const mfaToggle = document.getElementById('mfaToggle');
        if (mfaToggle) {
            mfaToggle.addEventListener('click', (e) => {
                e.currentTarget.classList.toggle('on');
            });
        }
    }

    /**
     * Handles the ONLY local modal on this page (Edit Profile)
     * Password and Deletion are handled by their own modular JS files.
     */
    initLocalModal() {
        const editModal = document.getElementById('editProfileModal');
        const openBtn = document.getElementById('openEditProfileBtn');
        const closeBtn = document.getElementById('closeEditModalBtn');
        const closeIcon = document.getElementById('closeEditModalIcon');

        if (editModal && openBtn) {
            openBtn.addEventListener('click', () => editModal.classList.add('show'));
            
            if (closeBtn) closeBtn.addEventListener('click', () => editModal.classList.remove('show'));
            if (closeIcon) closeIcon.addEventListener('click', () => editModal.classList.remove('show'));

            window.addEventListener('click', (e) => {
                if (e.target === editModal) editModal.classList.remove('show');
            });
        }
    }
}

document.addEventListener('DOMContentLoaded', () => new AccountManager());