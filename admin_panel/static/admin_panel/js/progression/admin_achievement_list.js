/* ==========================================================================
   admin_achievement_list.js
   Achievement create/edit modal handlers. Depends on progression_common.js.
   ========================================================================== */

function resetAchievementForm() {
    pgSetValue('achievement_id', '');
    pgSetValue('achievement_name', '');
    pgSetValue('achievement_desc', '');

    const categoryEl = document.getElementById('achievement_category');
    if (categoryEl) categoryEl.selectedIndex = 0;

    pgSetValue('achievement_key', '');
    pgSetValue('achievement_target', '1');
    pgSetValue('achievement_xp', '0');
    pgSetChecked('achievement_active', true);
    pgSetChecked('achievement_hidden', false);
    pgSetText('achievementModalLabel', 'Add Achievement');
}

function editAchievement(id, name, desc, category, key, target, xp, isActive, isHidden) {
    pgSetValue('achievement_id', id);
    pgSetValue('achievement_name', name);
    pgSetValue('achievement_desc', desc);
    pgSetValue('achievement_category', category);
    pgSetValue('achievement_key', key);
    pgSetValue('achievement_target', target);
    pgSetValue('achievement_xp', xp);
    pgSetChecked('achievement_active', isActive);
    pgSetChecked('achievement_hidden', isHidden);
    pgSetText('achievementModalLabel', 'Edit Achievement');
    pgOpenModal('achievementModal');
}