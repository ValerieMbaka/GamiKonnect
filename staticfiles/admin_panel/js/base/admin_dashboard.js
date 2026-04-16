class AdminDashboardController {
    constructor() {
        this.initThemeSettings();
        this.initCharts();
    }

    initThemeSettings() {
        this.isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        this.textColor = this.isDark ? '#CBD5E1' : '#64748B';
        this.gridColor = this.isDark ? '#334155' : '#E2E8F0';

        Chart.defaults.color = this.textColor;
        Chart.defaults.font.family = "'Poppins', sans-serif";
        
        this.colors = {
            primary: '#35A8F0',
            success: '#10B981',
            warning: '#F59E0B',
            purple: '#8B5CF6',
            danger: '#EF4444'
        };
    }

    initCharts() {
        this.renderSiteActivityChart();
        this.renderPlatformDistributionChart();
        this.renderRevenueChart();
        this.renderTrafficSourcesChart(); // New Chart
    }

    renderSiteActivityChart() {
        const canvas = document.getElementById('siteActivityChart');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        
        let gradientFill = ctx.createLinearGradient(0, 0, 0, canvas.parentElement.clientHeight);
        gradientFill.addColorStop(0, this.isDark ? 'rgba(53, 168, 240, 0.4)' : 'rgba(53, 168, 240, 0.25)');
        gradientFill.addColorStop(1, 'rgba(53, 168, 240, 0)');

        new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                datasets: [{
                    label: 'Active Users',
                    data: [1520, 1840, 1620, 2100, 2450, 3100, 2800],
                    borderColor: this.colors.primary,
                    backgroundColor: gradientFill,
                    borderWidth: 3,
                    tension: 0.4,
                    fill: true,
                    pointBackgroundColor: this.isDark ? '#1E293B' : '#FFFFFF',
                    pointBorderColor: this.colors.primary,
                    pointBorderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: this.getTooltipConfig()
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: this.gridColor, drawBorder: false, borderDash: [5, 5] },
                        border: { display: false }
                    },
                    x: {
                        grid: { display: false },
                        border: { display: false }
                    }
                }
            }
        });
    }

    renderPlatformDistributionChart() {
        const canvas = document.getElementById('platformDistributionChart');
        if (!canvas) return;

        new Chart(canvas.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: ['PC', 'PlayStation', 'Xbox', 'Mobile'],
                datasets: [{
                    data: [45, 25, 20, 10],
                    backgroundColor: [this.colors.primary, this.colors.purple, this.colors.success, this.colors.warning],
                    borderWidth: 0,
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '80%',
                plugins: {
                    legend: { position: 'bottom', labels: { padding: 20, usePointStyle: true, pointStyle: 'circle' } },
                    tooltip: this.getTooltipConfig()
                }
            }
        });
    }

    renderRevenueChart() {
        const canvas = document.getElementById('revenueChart');
        if (!canvas) return;

        new Chart(canvas.getContext('2d'), {
            type: 'bar',
            data: {
                labels: ['Shop Fees', 'Tournaments', 'Subscriptions', 'Ads'],
                datasets: [{
                    label: 'Revenue ($)',
                    data: [5400, 3200, 2850, 1000],
                    backgroundColor: this.colors.primary,
                    borderRadius: 6,
                    barPercentage: 0.5
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: this.getTooltipConfig()
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: this.gridColor, drawBorder: false },
                        border: { display: false }
                    },
                    x: {
                        grid: { display: false },
                        border: { display: false }
                    }
                }
            }
        });
    }

    getTooltipConfig() {
        return {
            backgroundColor: this.isDark ? '#0F172A' : '#1E293B',
            titleColor: '#FFFFFF',
            bodyColor: '#CBD5E1',
            padding: 12,
            cornerRadius: 8,
            displayColors: true,
            boxPadding: 4
        };
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new AdminDashboardController();
});