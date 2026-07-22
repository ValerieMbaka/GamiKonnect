/* ==========================================================================
   Leaderboard (Global & Per-Game) — leaderboard_global.html / leaderboard_game.html
   Progressive enhancement only: the page is fully functional via plain links
   and server-rendered pagination without this file.
   ========================================================================== */

document.addEventListener('DOMContentLoaded', function () {
    var table = document.querySelector('.lb-table');
    if (!table) return;

    var rows = table.querySelectorAll('.lb-row');

    // Staggered entrance animation for the ranked rows.
    rows.forEach(function (row, index) {
        row.style.opacity = '0';
        row.style.transform = 'translateY(8px)';
        row.style.transition = 'opacity 0.3s ease-out, transform 0.3s ease-out';
        window.setTimeout(function () {
            row.style.opacity = '1';
            row.style.transform = 'translateY(0)';
        }, Math.min(index, 15) * 35);
    });

    // If the current gamer's row isn't already visible near the top of the
    // viewport (e.g. they're ranked further down the page), gently scroll
    // it into view once the entrance animation has settled.
    var selfRow = table.querySelector('.lb-row--self');
    if (selfRow) {
        window.setTimeout(function () {
            var rect = selfRow.getBoundingClientRect();
            var isInView = rect.top >= 0 && rect.bottom <= window.innerHeight;
            if (!isInView) {
                selfRow.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        }, 500);
    }
});
