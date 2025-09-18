// Bot control auto-refresh functionality
$(document).ready(function() {
    // Check bot status every 5 seconds
    const statusInterval = setInterval(checkBotStatus, 5000);
    
    function checkBotStatus() {
        $.ajax({
            url: '/api/bot_status',
            type: 'GET',
            success: function(data) {
                updateBotStatus(data.running);
            },
            error: function(xhr, status, error) {
                console.error("Error checking bot status:", error);
            }
        });
    }
    
    function updateBotStatus(running) {
        const statusBadge = $('#bot-status-badge');
        const statusText = running ? 'Running' : 'Stopped';
        const badgeClass = running ? 'bg-success' : 'bg-danger';
        
        statusBadge.removeClass('bg-success bg-danger').addClass(badgeClass).text(statusText);
    }
});