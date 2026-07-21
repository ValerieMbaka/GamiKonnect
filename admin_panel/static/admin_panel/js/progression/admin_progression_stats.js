/* ==========================================================================
   admin_progression_stats.js
   Player Progression stats modal handler. One "Adjust Stats" modal is
   shared across every row in the table — each row's trigger button
   just points the form at that gamer before opening it. This keeps
   the table itself down to a single compact button per row instead
   of a full inline form, which is what was forcing the table wider
   than the viewport.
   Depends on progression_common.js.
   ========================================================================== */

function openStatsAdjustModal(gamerId, gamerName) {
    const form = document.getElementById('statsAdjustForm');
    if (form) {
        const template = form.dataset.urlTemplate;
        // The URL template is rendered with a placeholder UUID
        // (e.g. /admin/progression/stats/00000000-0000-0000-0000-000000000000/action/);
        // swap it for the real gamer stats id.
        form.action = template.replace('00000000-0000-0000-0000-000000000000', gamerId);
    }
    pgSetText('statsAdjustGamerName', gamerName);
    pgOpenModal('statsAdjustModal');
}