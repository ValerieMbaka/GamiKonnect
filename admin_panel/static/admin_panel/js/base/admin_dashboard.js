document.addEventListener('DOMContentLoaded', () => {
    
    // Check if the current theme is dark to adjust text colors on the charts
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    const textColor = isDark ? '#CBD5E1' : '#64748B';
    const gridColor = isDark ? '#334155' : '#E2E8F0';

    // Set global Chart.js defaults
    Chart.defaults.color = textColor;
    Chart.defaults.font.family = "'Poppins', sans-serif";

    /* Registration Growth Chart */
    const ctxGrowth = document.getElementById('growthChart');
    if (ctxGrowth) {
        new Chart(ctxGrowth, {
            type: 'line',
            data: {
                labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                datasets: [{
                    label: 'New Users',
                    data: [65, 89, 72, 120, 155, 210, 190],
                    borderColor: '#35A8F0',
                    backgroundColor: 'rgba(53, 168, 240, 0.1)',
                    borderWidth: 3,
                    tension: 0.4,
                    fill: true,
                    pointBackgroundColor: '#FFFFFF',
                    pointBorderColor: '#35A8F0',
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
                    tooltip: {
                        backgroundColor: isDark ? '#1E293B' : '#FFFFFF',
                        titleColor: isDark ? '#F8FAFC' : '#1E293B',
                        bodyColor: isDark ? '#CBD5E1' : '#475569',
                        borderColor: isDark ? '#334155' : '#E2E8F0',
                        borderWidth: 1,
                        padding: 10,
                        displayColors: false,
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: gridColor, drawBorder: false },
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

    /* User Distribution Chart */
    const ctxDist = document.getElementById('distributionChart');
    if (ctxDist) {
        new Chart(ctxDist, {
            type: 'doughnut',
            data: {
                labels: ['PC Gamers', 'Console Gamers', 'Mobile Gamers'],
                datasets: [{
                    data: [55, 30, 15],
                    backgroundColor: [
                        '#35A8F0',
                        '#8B5CF6',
                        '#10B981'
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
                        position: 'bottom',
                        labels: { padding: 20, usePointStyle: true, pointStyle: 'circle' }
                    }
                }
            }
        });
    }
});