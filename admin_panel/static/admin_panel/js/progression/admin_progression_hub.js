/* ==========================================================================
   admin_progression_hub.js
   Drives the contextual Seed / Add action group in the Progression Hub
   header. Both controls track whichever tab (Levels / Achievements /
   Player Progression) is currently active:
     - Add button: label + modal target + reset handler swap between
       "Add New Level" and "Add Achievement", and hide entirely on the
       Player Progression tab (nothing to add there).
     - Seed split button: the main face runs the seed command that
       matches the active tab ("all" on Player Progression); the caret
       dropdown always exposes all three options regardless of tab.
   Depends on progression_common.js, admin_level_list.js, and
   admin_achievement_list.js (for resetLevelForm / resetAchievementForm).
   ========================================================================== */

const HUB_TAB_CONFIG = {
    'levels-tab': {
        seedAction: 'levels',
        seedLabel: 'Run seed_levels',
        addLabel: 'Add New Level',
        addModal: 'levelModal',
        addReset: 'resetLevelForm',
    },
    'achievements-tab': {
        seedAction: 'achievements',
        seedLabel: 'Run seed_achievements',
        addLabel: 'Add Achievement',
        addModal: 'achievementModal',
        addReset: 'resetAchievementForm',
    },
    'stats-tab': {
        seedAction: 'all',
        seedLabel: 'Run All Seeds',
        addLabel: null,
        addModal: null,
        addReset: null,
    },
};

function submitHubSeed(action) {
    const input = document.getElementById('hubSeedActionInput');
    const form = document.getElementById('hubSeedForm');
    if (!input || !form) return;
    input.value = action;
    form.submit();
}

function applyHubTabContext(tabId) {
    const config = HUB_TAB_CONFIG[tabId];
    if (!config) return;

    const seedInput = document.getElementById('hubSeedActionInput');
    const seedMainBtn = document.getElementById('hubSeedMainBtn');
    if (seedInput) seedInput.value = config.seedAction;
    if (seedMainBtn) {
        seedMainBtn.innerHTML = `<i class="fas fa-seedling"></i> ${config.seedLabel}`;
    }

    const addBtn = document.getElementById('hubAddBtn');
    const addBtnLabel = document.getElementById('hubAddBtnLabel');
    if (!addBtn) return;

    if (!config.addLabel) {
        addBtn.classList.add('is-hidden');
        return;
    }

    addBtn.classList.remove('is-hidden');
    if (addBtnLabel) addBtnLabel.textContent = config.addLabel;
    addBtn.setAttribute('data-bs-target', `#${config.addModal}`);
    addBtn.setAttribute('onclick', `${config.addReset}()`);
}

document.addEventListener('DOMContentLoaded', function () {
    const tabButtons = document.querySelectorAll('#progressionTabs button[data-bs-toggle="tab"]');
    tabButtons.forEach(function (btn) {
        btn.addEventListener('shown.bs.tab', function (evt) {
            applyHubTabContext(evt.target.id);
        });
    });

    const activeTab = document.querySelector('#progressionTabs button.nav-link.active');
    applyHubTabContext(activeTab ? activeTab.id : 'levels-tab');
});