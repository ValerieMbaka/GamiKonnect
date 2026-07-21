/**
 * shop_owner_competitions.js
 * Handles the table filtering and Edit/Resubmit modal for rejected competitions.
 * Uses ES6 Class architecture and Unobtrusive JavaScript.
 */

class ShopOwnerCompetitionsManager {
    constructor() {
        this.loadDataIsland();
        this.activeEditId = null;

        // Filter Elements
        this.searchInput = document.getElementById('compSearchInput');
        this.statusFilter = document.getElementById('compStatusFilter');
        this.tableBody = document.getElementById('competitionsTableBody');

        // Modal Elements
        this.editModal = document.getElementById('editCompModal');
        this.editForm = document.getElementById('editCompForm');
        this.loadingState = document.getElementById('editCompLoading');
        this.rejectionNotice = document.getElementById('editRejectionNotice');
        
        // Form Inputs
        this.gameSelect = document.getElementById('editGame');
        this.platformSelect = document.getElementById('editPlatform');
        
        // Buttons
        this.closeBtns = [document.getElementById('closeEditModalBtn'), document.getElementById('cancelEditModalBtn')];
        this.submitBtn = document.getElementById('submitEditBtn');

        this.bindEvents();
    }

    loadDataIsland() {
        try {
            const dataElement = document.getElementById('compDashboardData');
            this.config = dataElement ? JSON.parse(dataElement.textContent) : {};
        } catch (error) {
            console.error('Failed to parse dashboard config:', error);
            this.config = { csrfToken: '', editUrlTemplate: '', allPlatforms: {} };
        }
    }

    bindEvents() {
        // Table Filtering
        this.searchInput?.addEventListener('input', () => this.filterTable());
        this.statusFilter?.addEventListener('change', () => this.filterTable());

        // Open Modal Buttons (Dynamically bound to handle paginated/filtered results)
        document.addEventListener('click', (e) => {
            const editBtn = e.target.closest('.btn-edit-comp');
            if (editBtn) {
                e.preventDefault();
                this.openEditModal(editBtn.dataset.id);
            }
        });

        // Close Modal
        this.closeBtns.forEach(btn => btn?.addEventListener('click', () => this.closeModal()));
        this.editModal?.addEventListener('click', (e) => {
            if (e.target === this.editModal) this.closeModal();
        });

        // Dynamic Form Logic inside Modal
        this.gameSelect?.addEventListener('change', (e) => this.handleGameChange(e.target.value));

        // Submit Form
        this.submitBtn?.addEventListener('click', () => this.submitEdit());
    }

    // --- Table Filtering ---

    filterTable() {
        const searchVal = this.searchInput?.value.toLowerCase().trim() || '';
        const statusVal = this.statusFilter?.value || '';
        
        if (!this.tableBody) return;
        const rows = this.tableBody.querySelectorAll('.comp-row');

        rows.forEach(row => {
            const name = row.dataset.name || '';
            const status = row.dataset.status || '';
            
            // Find the associated rejection row if it exists
            const rejectionRow = row.nextElementSibling;
            const isRejectionRowAssociated = rejectionRow && rejectionRow.classList.contains('rejection-row') && rejectionRow.dataset.parentName === name;

            const matchesSearch = !searchVal || name.includes(searchVal);
            const matchesStatus = !statusVal || status === statusVal;
            const isVisible = matchesSearch && matchesStatus;

            row.style.display = isVisible ? '' : 'none';
            if (isRejectionRowAssociated) {
                rejectionRow.style.display = isVisible ? '' : 'none';
            }
        });
    }

    // --- Modal Logic ---

    openEditModal(compId) {
        if (!compId || !this.config.editUrlTemplate) return;
        
        this.activeEditId = compId;
        this.editModal.classList.add('active');
        document.body.style.overflow = 'hidden'; // Prevent background scrolling
        
        // Reset View
        this.loadingState.classList.remove('d-none');
        this.editForm.classList.add('d-none');
        this.rejectionNotice.classList.add('d-none');
        
        this.fetchCompetitionData(compId);
    }

    closeModal() {
        this.editModal.classList.remove('active');
        document.body.style.overflow = '';
        this.activeEditId = null;
        this.editForm.reset();
    }

    async fetchCompetitionData(compId) {
        const url = this.config.editUrlTemplate.replace('{id}', compId);
        
        try {
            const response = await fetch(url);
            const data = await response.json();
            
            if (data.success) {
                this.populateForm(data.data);
                this.loadingState.classList.add('d-none');
                this.editForm.classList.remove('d-none');
            } else {
                if (typeof showToast === 'function') showToast('error', 'Failed to load competition details.');
                this.closeModal();
            }
        } catch (err) {
            console.error('Fetch error:', err);
            if (typeof showToast === 'function') showToast('error', 'Network error.');
            this.closeModal();
        }
    }

    populateForm(data) {
        document.getElementById('editName').value = data.name || '';
        document.getElementById('editDescription').value = data.description || '';
        
        // Set Game and manually trigger the platform update
        this.gameSelect.value = data.game || '';
        this.handleGameChange(data.game, data.platform);

        document.getElementById('editStart').value = data.scheduled_time || '';
        document.getElementById('editEnd').value = data.competition_end_time || '';
        document.getElementById('editMax').value = data.max_participants || '';
        document.getElementById('editFee').value = data.entry_fee || '';
        document.getElementById('editAge').checked = data.age_restricted || false;
        document.getElementById('editRules').value = data.rules || '';
        document.getElementById('editTimeline').value = data.timeline || '';

        if (data.rejection_reason) {
            this.rejectionNotice.innerHTML = `<strong>Admin Rejection Reason:</strong><br>${data.rejection_reason}`;
            this.rejectionNotice.classList.remove('d-none');
        }
    }

    handleGameChange(gameId, preselectedPlatformId = null) {
        this.platformSelect.innerHTML = '<option value="">Select Platform</option>';
        if (!gameId || !this.config.allPlatforms) return;

        const platforms = this.config.allPlatforms[gameId] || [];
        
        platforms.forEach(platform => {
            const option = document.createElement('option');
            option.value = platform.id;
            option.textContent = platform.name;
            if (preselectedPlatformId && String(platform.id) === String(preselectedPlatformId)) {
                option.selected = true;
            }
            this.platformSelect.appendChild(option);
        });
    }

    async submitEdit() {
        if (!this.activeEditId || !this.editForm.checkValidity()) {
            this.editForm.reportValidity();
            return;
        }

        const originalText = this.submitBtn.innerHTML;
        this.submitBtn.disabled = true;
        this.submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Submitting...';

        const url = this.config.editUrlTemplate.replace('{id}', this.activeEditId);
        const formData = new FormData(this.editForm);

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: { 'X-CSRFToken': this.config.csrfToken },
                body: formData
            });
            const data = await response.json();

            if (data.success) {
                if (typeof showToast === 'function') showToast('success', data.message);
                setTimeout(() => window.location.reload(), 1500);
            } else {
                if (typeof showToast === 'function') showToast('error', data.message || 'Validation failed. Check inputs.');
                this.submitBtn.disabled = false;
                this.submitBtn.innerHTML = originalText;
            }
        } catch (err) {
            console.error('Submit error:', err);
            if (typeof showToast === 'function') showToast('error', 'Network error while saving.');
            this.submitBtn.disabled = false;
            this.submitBtn.innerHTML = originalText;
        }
    }
}

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', () => {
    if (document.querySelector('.competitions-dashboard-wrapper')) {
        new ShopOwnerCompetitionsManager();
    }
});