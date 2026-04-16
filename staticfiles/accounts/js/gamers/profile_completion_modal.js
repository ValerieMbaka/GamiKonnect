class ProfileCompletionModal {
    constructor() {
        this.modal = document.getElementById('profileCompletionModal');
        if (this.modal) {
            this.init();
        }
    }

    init() {
        const isCompleted = localStorage.getItem('profileCompleted') === 'true';
        
        if (isCompleted) {
            this.hideModal();
        } else if (this.modal.classList.contains('show')) {
            this.modal.classList.add('mandatory');
        }
        
        this.bindEvents();
    }

    hideModal() {
        this.modal.classList.remove('show', 'mandatory');
        this.modal.style.display = 'none';
    }

    bindEvents() {
        this.modal.addEventListener('click', (e) => {
            if (e.target === this.modal && this.modal.classList.contains('mandatory')) {
                e.stopPropagation();
            }
        });
        
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.modal.classList.contains('mandatory')) {
                e.preventDefault();
            }
        });
    }

    static clearProfileCompletion() {
        localStorage.removeItem('profileCompleted');
        localStorage.removeItem('updatedProfile');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new ProfileCompletionModal();
    window.clearProfileCompletion = ProfileCompletionModal.clearProfileCompletion;
});