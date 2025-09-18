// Dashboard auto-refresh functionality
$(document).ready(function() {
    // Initial load
    updateDashboard();
    
    // Set interval for auto-refresh (every 5 seconds)
    const refreshInterval = setInterval(updateDashboard, 5000);
    
    // Manual refresh button
    $('#manual-refresh').click(function() {
    const $btn = $(this);
    const $icon = $btn.find('.bi-arrow-clockwise');
    
    // Disable button and add loading class
    $btn.prop('disabled', true).addClass('loading');
    $icon.addClass('spin');
    
    // Update dashboard
    updateDashboard();
    
    // Re-enable after update completes
    setTimeout(() => {
        $btn.prop('disabled', false).removeClass('loading');
        $icon.removeClass('spin');
    }, 1000);
});
    
    // Function to update dashboard data
    function updateDashboard() {
        $.ajax({
            url: '/api/dashboard_data',
            type: 'GET',
            success: function(data) {
                updateSystemStats(data.system_stats);
                updateNetworkStats(data.network_speed);
                updateBotStats(data.bot_stats);
                updateMaintenanceStatus(data.maintenance);
                updateBotStatus(data.bot_status);
            },
            error: function(xhr, status, error) {
                console.error("Error fetching dashboard data:", error);
                $('#dashboard-alerts').html(`
                    <div class="alert alert-danger alert-dismissible fade show" role="alert">
                        Error updating dashboard data: ${error}
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    </div>
                `);
            }
        });
    }
    
    // Update system stats
    function updateSystemStats(stats) {
        $('#cpu-usage').text(stats.cpu + '%');
        $('#cpu-usage-bar').css('width', stats.cpu + '%');
        
        $('#memory-usage').text(stats.memory + '%');
        $('#memory-usage-bar').css('width', stats.memory + '%');
        $('#memory-used').text(stats.memory_used + ' GB');
        $('#memory-total').text(stats.memory_total + ' GB');
        
        $('#disk-usage').text(stats.disk + '%');
        $('#disk-usage-bar').css('width', stats.disk + '%');
        $('#disk-used').text(stats.disk_used + ' GB');
        $('#disk-total').text(stats.disk_total + ' GB');
        
        $('#boot-time').text(stats.boot_time);
        $('#bot-pid').text(stats.bot_pid || 'N/A');
    }
    
    // Update network stats
    function updateNetworkStats(network) {
        $('#download-speed').text(network.download + ' Mbps');
        $('#upload-speed').text(network.upload + ' Mbps');
        $('#ping-time').text(network.ping + ' ms');
    }
    
    // Update bot stats
    function updateBotStats(stats) {
        $('#total-users').text(stats.total_users);
        $('#active-today').text(stats.active_today);
        $('#files-served').text(stats.files_served);
        $('#banned-users').text(stats.banned_users);
    }
    
    // Update maintenance status
    function updateMaintenanceStatus(status) {
        const badge = status ? 
            '<span class="badge bg-danger">Enabled</span>' : 
            '<span class="badge bg-success">Disabled</span>';
        $('#maintenance-status').html(badge);
        $('#maintenance-btn')
            .removeClass('btn-danger btn-success')
            .addClass(status ? 'btn-success' : 'btn-danger')
            .text(status ? 'Disable' : 'Enable');
    }
    
    // Update bot status
    function updateBotStatus(running) {
        const statusText = running ? 'Running' : 'Stopped';
        const badgeClass = running ? 'bg-success' : 'bg-danger';
        $('#bot-status').html(`<span class="badge ${badgeClass}">${statusText}</span>`);
    }
});