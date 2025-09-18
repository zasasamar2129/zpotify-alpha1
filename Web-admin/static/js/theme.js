document.addEventListener('DOMContentLoaded', function() {
    const themeToggle = document.getElementById('theme-toggle');
    if (!themeToggle) return;
    
    const sunIcon = themeToggle.querySelector('.bi-sun-fill');
    const moonIcon = themeToggle.querySelector('.bi-moon-fill');
    
    // Initialize theme
    function initTheme() {
        const currentTheme = localStorage.getItem('theme') || 'light';
        if (currentTheme === 'dark') {
            document.body.classList.add('dark-mode');
            if (sunIcon) sunIcon.classList.remove('d-none');
            if (moonIcon) moonIcon.classList.add('d-none');
        } else {
            document.body.classList.remove('dark-mode');
            if (sunIcon) sunIcon.classList.add('d-none');
            if (moonIcon) moonIcon.classList.remove('d-none');
        }
    }
    
    // Toggle theme
    function toggleTheme() {
        if (document.body.classList.contains('dark-mode')) {
            document.body.classList.remove('dark-mode');
            localStorage.setItem('theme', 'light');
            if (sunIcon) sunIcon.classList.add('d-none');
            if (moonIcon) moonIcon.classList.remove('d-none');
        } else {
            document.body.classList.add('dark-mode');
            localStorage.setItem('theme', 'dark');
            if (sunIcon) sunIcon.classList.remove('d-none');
            if (moonIcon) moonIcon.classList.add('d-none');
        }
    }
    
    // Initialize
    initTheme();
    
    // Add event listener
    themeToggle.addEventListener('click', toggleTheme);
});

document.getElementById('theme-toggle').addEventListener('click', function() {
    // Add temporary class during transition
    document.body.classList.add('theme-transition');
    
    // Toggle dark mode
    document.body.classList.toggle('dark-mode');
    
    // Remove transition class after animation completes
    setTimeout(function() {
        document.body.classList.remove('theme-transition');
    }, 500); // Match this duration to your CSS transition time
});