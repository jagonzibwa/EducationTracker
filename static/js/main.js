// Education Tracker - Main JavaScript

// Auto-dismiss flash messages after 5 seconds
document.addEventListener('DOMContentLoaded', function() {
    const alerts = document.querySelectorAll('[class*="bg-green-100"], [class*="bg-red-100"], [class*="bg-blue-100"]');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            alert.style.transition = 'opacity 0.5s';
            alert.style.opacity = '0';
            setTimeout(function() {
                alert.remove();
            }, 500);
        }, 5000);
    });
});
