// Update stats every 10 seconds
function updateStats() {
    fetch('/api/stats')
        .then(response => response.json())
        .then(data => {
            // Update CPU
            document.querySelector('.progress-bar[aria-valuenow]').style.width = data.cpu + '%';
            document.querySelector('.progress-bar[aria-valuenow]').textContent = data.cpu + '%';
            document.querySelector('.progress-bar[aria-valuenow]').className = 
                'progress-bar bg-' + (data.cpu > 80 ? 'danger' : data.cpu > 50 ? 'warning' : 'success');
            
            // Update memory
            document.querySelectorAll('.progress-bar')[1].style.width = data.memory + '%';
            document.querySelectorAll('.progress-bar')[1].textContent = data.memory + '%';
            document.querySelectorAll('.progress-bar')[1].className = 
                'progress-bar bg-' + (data.memory > 80 ? 'danger' : data.memory > 50 ? 'warning' : 'success');
            
            // Update bot status
            const botStatus = document.querySelector('.badge.bg-success, .badge.bg-danger');
            botStatus.className = 'badge bg-' + (data.bot_running ? 'success' : 'danger');
            botStatus.textContent = data.bot_running ? 'Running' : 'Stopped';
        });
}

// Update network stats every 30 seconds
function updateNetworkStats() {
    fetch('/api/network')
        .then(response => response.json())
        .then(data => {
            document.querySelectorAll('h2')[0].textContent = data.download + ' Mbps';
            document.querySelectorAll('h2')[1].textContent = data.upload + ' Mbps';
            document.querySelectorAll('h2')[2].textContent = data.ping + ' ms';
        });
}

// Initialize charts
function initCharts() {
    // CPU Usage Chart
    const cpuCtx = document.getElementById('cpuChart').getContext('2d');
    const cpuChart = new Chart(cpuCtx, {
        type: 'line',
        data: {
            labels: Array.from({length: 20}, (_, i) => i + 1),
            datasets: [{
                label: 'CPU Usage %',
                data: Array(20).fill(0),
                borderColor: '#4e73df',
                backgroundColor: 'rgba(78, 115, 223, 0.05)',
                pointRadius: 3,
                pointBackgroundColor: '#4e73df',
                pointBorderColor: '#4e73df',
                pointHoverRadius: 3,
                pointHoverBackgroundColor: '#4e73df',
                pointHoverBorderColor: '#4e73df',
                pointHitRadius: 10,
                pointBorderWidth: 2,
                fill: true
            }]
        },
        options: {
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                        callback: function(value) {
                            return value + '%';
                        }
                    }
                }
            }
        }
    });

    // Update charts with real data
    setInterval(() => {
        fetch('/api/stats')
            .then(response => response.json())
            .then(data => {
                // Shift and add new CPU data
                cpuChart.data.datasets[0].data.shift();
                cpuChart.data.datasets[0].data.push(data.cpu);
                cpuChart.update();
            });
    }, 5000);
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Update stats immediately
    updateStats();
    updateNetworkStats();
    
    // Set up periodic updates
    setInterval(updateStats, 10000);
    setInterval(updateNetworkStats, 30000);
    
    // Initialize charts if on dashboard
    if (document.getElementById('cpuChart')) {
        initCharts();
    }
    
    // Enable tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});