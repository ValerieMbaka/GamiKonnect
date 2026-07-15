class AdminDashboardController {
    constructor() {
        this.chartData = this.getChartData();
        this.initThemeSettings();
        this.initCharts();
    }

    getChartData() {
        const chartDataElement = document.getElementById('dashboard-chart-data');
        if (!chartDataElement) {
            return { activity_labels: [], activity_data: [], revenue_data: [] };
        }

        try {
            return JSON.parse(chartDataElement.textContent || '{}');
        } catch (error) {
            console.error('Failed to parse dashboard chart data:', error);
            return { activity_labels: [], activity_data: [], revenue_data: [] };
        }
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
                labels: this.chartData.activity_labels || [],
                datasets: [{
                    label: 'Active Users',
                    data: this.chartData.activity_data || [],
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
                    data: this.chartData.revenue_data || [],
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

    renderTrafficSourcesChart() {
        const canvas = document.getElementById('trafficSourcesChart');
        if (!canvas) return;

        new Chart(canvas.getContext('2d'), {
            type: 'bar',
            data: {
                labels: this.chartData.rev_labels || [],
                datasets: [
                    {
                        label: 'Competitions',
                        data: this.chartData.rev_competitions || [],
                        backgroundColor: this.colors.primary,
                        borderRadius: 4
                    },
                    {
                        label: 'Ads',
                        data: this.chartData.rev_ads || [],
                        backgroundColor: this.colors.success,
                        borderRadius: 4
                    },
                    {
                        label: 'Subscriptions',
                        data: this.chartData.rev_subscriptions || [],
                        backgroundColor: this.colors.purple,
                        borderRadius: 4
                    },
                    {
                        label: 'Arena Fees',
                        data: this.chartData.rev_arena_fees || [],
                        backgroundColor: this.colors.warning,
                        borderRadius: 4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom', labels: { boxWidth: 12, usePointStyle: true } },
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