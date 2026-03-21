class AdminDashboardManager {
    constructor() {
        this.growthChartCanvas = document.getElementById('userGrowthChart');
        this.revenueChartCanvas = document.getElementById('revenueChart');
        
        this.init();
    }

    init() {
        if (typeof Chart !== 'undefined') {
            if (this.growthChartCanvas) this.initGrowthChart();
            if (this.revenueChartCanvas) this.initRevenueChart();
        }
    }

    initGrowthChart() {
        const ctx = this.growthChartCanvas.getContext('2d');
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                datasets: [
                    {
                        label: 'Gamers',
                        data: [120, 190, 300, 450, 600, 850],
                        backgroundColor: '#3b82f6',
                        borderRadius: 4
                    },
                    {
                        label: 'Shops',
                        data: [5, 12, 18, 24, 35, 42],
                        backgroundColor: '#10b981',
                        borderRadius: 4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: { y: { beginAtZero: true, grid: { borderDash: [2, 4] } }, x: { grid: { display: false } } },
                plugins: { legend: { position: 'top' } }
            }
        });
    }

    initRevenueChart() {
        const ctx = this.revenueChartCanvas.getContext('2d');
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
                datasets: [{
                    label: 'Platform Revenue (Kshs)',
                    data: [15000, 22000, 18000, 29000],
                    borderColor: '#8b5cf6',
                    backgroundColor: 'rgba(139, 92, 246, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: { y: { beginAtZero: true } }
            }
        });
    }
}

document.addEventListener('DOMContentLoaded', () => new AdminDashboardManager());