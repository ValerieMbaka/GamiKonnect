document.addEventListener('DOMContentLoaded', () => {
    const sidebar = document.getElementById('shopOwnerSidebar');
    const sidebarToggle = document.getElementById('sidebarToggle');
    const profileDropdown = document.querySelector('.profile-dropdown');
    const themeToggle = document.getElementById('themeToggle');
    const body = document.body;

    /* ---------- Theme Handling ---------- */
    const storedTheme = localStorage.getItem('gk-dashboard-theme');
    if (storedTheme) {
        document.documentElement.setAttribute('data-theme', storedTheme);
        body.dataset.dashboardTheme = storedTheme;
        toggleThemeIcons(storedTheme);
    }

    function toggleThemeIcons(theme) {
        const sun = themeToggle?.querySelector('.fa-sun');
        const moon = themeToggle?.querySelector('.fa-moon');
        if (!sun || !moon) return;
        if (theme === 'dark') {
            sun.style.opacity = '0.3';
            moon.style.opacity = '1';
        } else {
            sun.style.opacity = '1';
            moon.style.opacity = '0.3';
        }
    }

    themeToggle?.addEventListener('click', () => {
        const currentTheme = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', currentTheme);
        localStorage.setItem('gk-dashboard-theme', currentTheme);
        body.dataset.dashboardTheme = currentTheme;
        toggleThemeIcons(currentTheme);
    });

    /* ---------- Sidebar Toggle ---------- */
    sidebarToggle?.addEventListener('click', () => {
        if (!sidebar) return;
        if (window.innerWidth <= 992) {
            sidebar.classList.toggle('open');
        } else {
            sidebar.classList.toggle('collapsed');
        }
    });

    window.addEventListener('resize', () => {
        if (window.innerWidth > 992) {
            sidebar?.classList.remove('open');
        }
    });

    document.addEventListener('click', (event) => {
        if (
            window.innerWidth <= 992 &&
            sidebar?.classList.contains('open') &&
            !sidebar.contains(event.target) &&
            !sidebarToggle?.contains(event.target)
        ) {
            sidebar.classList.remove('open');
        }
    });

    /* ---------- Profile Dropdown ---------- */
    const dropdownTrigger = profileDropdown?.querySelector('.profile-trigger');
    dropdownTrigger?.addEventListener('click', () => {
        profileDropdown.classList.toggle('open');
        const expanded = profileDropdown.classList.contains('open');
        dropdownTrigger.setAttribute('aria-expanded', expanded);
    });

    document.addEventListener('click', (event) => {
        if (profileDropdown && !profileDropdown.contains(event.target)) {
            profileDropdown.classList.remove('open');
            if (dropdownTrigger) {
                dropdownTrigger.setAttribute('aria-expanded', 'false');
            }
        }
    });

    /* ---------- Sidebar Active Link Helper ---------- */
    const currentPath = window.location.pathname;
    document.querySelectorAll('.sidebar-link').forEach(link => {
        try {
            const href = link.getAttribute('href');
            if (href && currentPath === new URL(href, window.location.origin).pathname) {
                link.classList.add('active');
            }
        } catch (error) {
            // eslint-disable-next-line no-console
            console.debug('Sidebar link normalisation failed', error);
        }
    });
});

window.showDashboardToast = function showDashboardToast(message, type = 'info') {
    if (window.toastManager) {
        window.toastManager.show({
            type,
            title: type.charAt(0).toUpperCase() + type.slice(1),
            message,
        });
        return;
    }
    alert(message);
};