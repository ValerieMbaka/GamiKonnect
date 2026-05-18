/**
 * leaderboard.js
 * Minimal JS for leaderboard pages — auto-scrolls to the current
 * gamer's row on page load if it's in the visible table.
 */
document.addEventListener('DOMContentLoaded', () => {
    const selfRow = document.querySelector('.lb-row--self');
    if (selfRow) {
        setTimeout(() => {
            selfRow.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }, 400);
    }
});


/**
 * progression.js
 * Animates the XP progress bar on page load.
 */
document.addEventListener('DOMContentLoaded', () => {
    const fill = document.querySelector('.prog-xp-fill');
    if (fill) {
        const target = fill.style.width;
        fill.style.width = '0%';
        setTimeout(() => {
            fill.style.width = target;
        }, 200);
    }
});