/**
 * gamer_competition_result.js
 * Minimal JS for the result detail page.
 * The page is primarily static — animations and highlight effects only.
 */

document.addEventListener('DOMContentLoaded', () => {

    // Stagger-animate leaderboard rows on load
    const rows = document.querySelectorAll('.result-leaderboard-row');
    rows.forEach((row, i) => {
        row.style.opacity = '0';
        row.style.transform = 'translateX(-10px)';
        row.style.transition = `opacity 0.3s ease ${i * 0.04}s, transform 0.3s ease ${i * 0.04}s`;

        // Trigger animation after a brief delay
        requestAnimationFrame(() => {
            setTimeout(() => {
                row.style.opacity = '1';
                row.style.transform = 'translateX(0)';
            }, 50);
        });
    });

    // Scroll the gamer's own row into view if not visible
    const selfRow = document.querySelector('.result-leaderboard-row--self');
    if (selfRow) {
        setTimeout(() => {
            selfRow.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }, 500);
    }

});