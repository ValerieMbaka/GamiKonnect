class AdminShopManager {
    constructor() {
        this.searchInput = document.getElementById('shopSearch');
        this.statusFilter = document.getElementById('statusFilter');
        this.tableRows = document.querySelectorAll('.shop-row');
        this.actionButtons = document.querySelectorAll('.btn-shop-action');
        
        this.init();
    }

    init() {
        this.bindFilters();
        this.bindActions();
    }

    bindFilters() {
        const applyFilters = () => {
            const searchTerm = (this.searchInput?.value || '').toLowerCase();
            const status = this.statusFilter?.value || 'all';

            this.tableRows.forEach(row => {
                const text = row.textContent.toLowerCase();
                const rowStatus = row.dataset.status;
                
                const matchesSearch = text.includes(searchTerm);
                const matchesStatus = status === 'all' || rowStatus === status;

                row.style.display = (matchesSearch && matchesStatus) ? 'table-row' : 'none';
            });
        };

        if (this.searchInput) {
            this.searchInput.addEventListener('input', () => {
                clearTimeout(this.debounceTimer);
                this.debounceTimer = setTimeout(applyFilters, 300);
            });
        }

        if (this.statusFilter) {
            this.statusFilter.addEventListener('change', applyFilters);
        }
    }

    bindActions() {
        this.actionButtons.forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.preventDefault();
                const action = btn.dataset.action;
                const shopId = btn.dataset.shopId;
                const row = document.getElementById(`shop-row-${shopId}`);

                if (action === 'approve') {
                    await this.handleApproval(shopId, row);
                } else if (action === 'reject') {
                    await this.handleRejection(shopId, row);
                }
            });
        });
    }

    async handleApproval(shopId, row) {
        if (!confirm('Are you sure you want to approve this shop and make it live?')) return;

        // Simulate API Call
        window.toastManager.info('Processing', 'Approving venue...');
        
        setTimeout(() => {
            window.toastManager.success('Approved', 'Shop is now live on the platform.');
            // Update UI dynamically
            if (row) {
                row.dataset.status = 'active';
                const statusCell = row.querySelector('.status-cell');
                statusCell.innerHTML = '<span class="badge-status active"><i class="fas fa-check-circle"></i> Active</span>';
                
                const actionsCell = row.querySelector('.action-buttons');
                actionsCell.innerHTML = `
                    <button class="btn btn-sm btn-outline-secondary rounded-pill px-3" title="View Details">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger rounded-pill px-3 btn-shop-action" data-action="reject" data-shop-id="${shopId}">
                        Revoke
                    </button>
                `;
                
                // Rebind new buttons
                this.actionButtons = document.querySelectorAll('.btn-shop-action');
                this.bindActions();
            }
        }, 1000);
    }

    async handleRejection(shopId, row) {
        const reason = prompt('Please provide a reason for rejecting this shop (sent to owner):');
        if (reason === null) return; // User cancelled

        window.toastManager.info('Processing', 'Rejecting venue...');
        
        setTimeout(() => {
            window.toastManager.warning('Rejected', 'Shop application has been rejected.');
            if (row) {
                row.dataset.status = 'rejected';
                const statusCell = row.querySelector('.status-cell');
                statusCell.innerHTML = '<span class="badge-status rejected"><i class="fas fa-times-circle"></i> Rejected</span>';
                
                // Remove approve/reject buttons, leave only view
                const actionsCell = row.querySelector('.action-buttons');
                actionsCell.innerHTML = `
                    <button class="btn btn-sm btn-outline-secondary rounded-pill px-3" title="View Details">
                        <i class="fas fa-eye"></i>
                    </button>
                `;
            }
        }, 1000);
    }
}

document.addEventListener('DOMContentLoaded', () => new AdminShopManager());