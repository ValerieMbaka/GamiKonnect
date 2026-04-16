class MetricsChartManager {
    constructor() {
        this.earningsCanvas = document.getElementById('earningsChart');
        this.hardwareCanvas = document.getElementById('hardwareChart');
        
        if (typeof Chart !== 'undefined') {
            if (this.earningsCanvas) this.initEarningsChart();
            if (this.hardwareCanvas) this.initHardwareChart();
        }
    }

    initEarningsChart() {
        const ctx = this.earningsCanvas.getContext('2d');
        
        const gradient = ctx.createLinearGradient(0, 0, 0, 300);
        gradient.addColorStop(0, 'rgba(53, 168, 240, 0.3)');
        gradient.addColorStop(1, 'rgba(53, 168, 240, 0.0)');

        new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                datasets: [{
                    label: 'Revenue (Ksh)',
                    data: [1200, 1900, 1500, 2200, 3500, 4800, 4100],
                    borderColor: '#35a8f0',
                    backgroundColor: gradient,
                    borderWidth: 3,
                    pointBackgroundColor: '#ffffff',
                    pointBorderColor: '#35a8f0',
                    pointBorderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: 'rgba(15, 23, 42, 0.9)',
                        titleColor: '#fff',
                        bodyColor: '#e2e8f0',
                        padding: 12,
                        cornerRadius: 8,
                        displayColors: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { borderDash: [4, 4], color: 'rgba(0,0,0,0.05)' },
                        ticks: { font: { family: "'Inter', sans-serif" } }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { font: { family: "'Inter', sans-serif" } }
                    }
                },
                interaction: { mode: 'nearest', axis: 'x', intersect: false }
            }
        });
    }

    initHardwareChart() {
        const ctx = this.hardwareCanvas.getContext('2d');

        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['PlayStation 5', 'PlayStation 4', 'Xbox Series X', 'PC'],
                datasets: [{
                    data: [12, 25, 8, 15],
                    backgroundColor: [
                        '#35a8f0',
                        '#8b5cf6',
                        '#10b981',
                        '#f59e0b'
                    ],
                    borderWidth: 0,
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '75%',
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            font: { family: "'Inter', sans-serif", size: 12 },
                            usePointStyle: true,
                            padding: 20
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(15, 23, 42, 0.9)',
                        titleColor: '#fff',
                        bodyColor: '#e2e8f0',
                        padding: 12,
                        cornerRadius: 8
                    }
                }
            }
        });
    }
}

// Global Initialization
document.addEventListener('DOMContentLoaded', () => {
    const isLocked = document.querySelector('.blurred-locked');
    if (!isLocked) {
        window.shopOwnerApp = {
            metrics: new MetricsChartManager()
        };
    }
});