class GamerSettingsManager {
    constructor() {
        this.cacheDOM();
        this.init();
    }

    cacheDOM() {
        this.tabs = document.querySelectorAll('.settings-nav-item');
        this.tabContents = document.querySelectorAll('.settings-tab-content');
    }

    init() {
        this.bindEvents();
    }

    bindEvents() {
        this.tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                this.tabs.forEach(t => t.classList.remove('active'));
                this.tabContents.forEach(c => c.classList.remove('active'));
                
                tab.classList.add('active');
                const targetId = tab.dataset.tab;
                const targetContent = document.getElementById(targetId);
                if (targetContent) targetContent.classList.add('active');
            });
        });
    }
}

document.addEventListener('DOMContentLoaded', () => new GamerSettingsManager());