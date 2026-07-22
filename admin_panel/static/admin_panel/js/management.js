/* ==========================================================================
   Shop / Arena Management
   NOTE: as of writing, this page renders hardcoded placeholder rows rather
   than real Shop records from the database (compare with the live, routed
   admin_panel:shop_list page at admin_panel/shops/admin_shop_list.html,
   which already pulls real data). The approve/reject wiring below points at
   the real backend endpoints (admin_panel:shop_approve / shop_reject) via
   each row's data-shop-id, so it will work as-is once this template is
   updated to loop over actual shop objects instead of static markup.
   ========================================================================== */

document.addEventListener('DOMContentLoaded', function () {
    var searchInput = document.getElementById('shopSearch');
    var statusFilter = document.getElementById('statusFilter');
    var rows = document.querySelectorAll('.shop-row');

    function applyFilters() {
        var query = (searchInput && searchInput.value || '').trim().toLowerCase();
        var status = (statusFilter && statusFilter.value) || 'all';

        rows.forEach(function (row) {
            var matchesStatus = status === 'all' || row.dataset.status === status;

            var text = '';
            row.querySelectorAll('.shop-name, .shop-location').forEach(function (el) {
                text += ' ' + el.textContent.toLowerCase();
            });
            var matchesQuery = query === '' || text.indexOf(query) !== -1;

            row.classList.toggle('is-hidden', !(matchesStatus && matchesQuery));
        });
    }

    if (searchInput) {
        searchInput.addEventListener('input', applyFilters);
    }
    if (statusFilter) {
        statusFilter.addEventListener('change', applyFilters);
    }

    // Approve / Reject — routes to the real admin_panel endpoints:
    //   /management/shops/<shop_id>/approve/
    //   /management/shops/<shop_id>/reject/
    document.querySelectorAll('.btn-shop-action').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var shopId = btn.dataset.shopId;
            var action = btn.dataset.action; // 'approve' | 'reject'
            if (!shopId || !action) return;

            var verb = action === 'approve' ? 'approve' : 'reject';
            if (!window.confirm('Are you sure you want to ' + verb + ' this shop?')) {
                return;
            }

            window.location.href = '/management/shops/' + encodeURIComponent(shopId) + '/' + action + '/';
        });
    });
});
