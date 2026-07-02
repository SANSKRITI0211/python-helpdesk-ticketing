// IT Helpdesk Ticketing System - Interactive Enhancements
document.addEventListener('DOMContentLoaded', () => {
    console.log('HelpDesk design system loaded.');

    // Theme switching logic
    const themeToggle = document.getElementById('theme-toggle');
    const themeIcon = document.getElementById('theme-icon');
    
    // Read current theme state and sync icon
    const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
    updateThemeIcon(currentTheme);
    
    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            const activeTheme = document.documentElement.getAttribute('data-theme') || 'dark';
            const newTheme = activeTheme === 'dark' ? 'light' : 'dark';
            
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            updateThemeIcon(newTheme);
        });
    }
    
    function updateThemeIcon(theme) {
        if (!themeIcon) return;
        if (theme === 'light') {
            themeIcon.className = 'fa-solid fa-sun';
            themeIcon.style.color = '#eab308'; // Amber/Yellow color for Sun
        } else {
            themeIcon.className = 'fa-solid fa-moon';
            themeIcon.style.color = ''; // Default style for Moon
        }
    }

    // Auto-dismiss Django message alerts after 5 seconds
    const alerts = document.querySelectorAll('.messages-container > div');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.transition = 'opacity 0.5s ease';
            alert.style.opacity = '0';
            setTimeout(() => {
                alert.remove();
            }, 500);
        }, 5000);
    });

    // Add confirmation warning to system actions
    const dangerButtons = document.querySelectorAll('.btn-danger');
    dangerButtons.forEach(button => {
        // If it's a form submit button inside a log-out, skip confirmation
        if (button.closest('form') && button.querySelector('.fa-right-from-bracket')) {
            return;
        }
        
        button.addEventListener('click', (e) => {
            if (!confirm('Are you sure you want to perform this action?')) {
                e.preventDefault();
            }
        });
    });
});
