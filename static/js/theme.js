// Theme toggle functionality
document.addEventListener('DOMContentLoaded', function() {
    const themeToggle = document.getElementById('themeToggle');
    const currentTheme = localStorage.getItem('theme') || 'dark';
    
    // Set initial theme
    document.documentElement.setAttribute('data-theme', currentTheme);
    updateThemeIcon(currentTheme);
    updateMetaTheme(currentTheme);
    
    if (themeToggle) {
        themeToggle.addEventListener('click', function() {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            updateThemeIcon(newTheme);
            updateMetaTheme(newTheme);
        });
    }
    
    function updateThemeIcon(theme) {
        if (themeToggle) {
            if (theme === 'dark') {
                themeToggle.innerHTML = '<i class="fas fa-moon"></i>';
                themeToggle.title = 'Modo Escuro';
                themeToggle.setAttribute('aria-label', 'Mudar para modo claro');
            } else {
                themeToggle.innerHTML = '<i class="fas fa-sun"></i>';
                themeToggle.title = 'Modo Claro';
                themeToggle.setAttribute('aria-label', 'Mudar para modo escuro');
            }
        }
    }
    
    function updateMetaTheme(theme) {
        // Update meta theme-color for mobile browsers
        const metaThemeColor = document.querySelector('meta[name="theme-color"]');
        if (metaThemeColor) {
            metaThemeColor.setAttribute('content', theme === 'dark' ? '#0f172a' : '#ffffff');
        }
    }
    
    // Add loading animation removal
    window.addEventListener('load', function() {
        document.body.classList.add('loaded');
    });
});