document.addEventListener('DOMContentLoaded', function() {
    // Wait for theme switcher container to be available
    const themeSwitcherContainer = document.getElementById('themeSwitcher');
    if (!themeSwitcherContainer) return;
    
    // Define themes
    const themes = [
        { 
            id: 'twilight',
            name: 'Zmierzch Fioletu', 
            desc: 'Domyślny motyw z subtelnymi odcieniami fioletu',
            vars: {
                '--primary-color': 'rgba(128, 100, 190, 0.8)',
                '--primary-hover': 'rgba(128, 100, 190, 0.9)',
                '--secondary-color': '#262636',
                '--accent-color': 'rgba(156, 128, 207, 0.7)',
                '--dark-bg': '#1e1e2d',
                '--card-bg': '#262636',
                '--border-color': 'rgba(70, 70, 90, 0.3)'
            }
        },
        {
            id: 'forest',
            name: 'Leśny Szmaragd', 
            desc: 'Uspokajające odcienie zieleni inspirowane lasem',
            vars: {
                '--primary-color': 'var(--forest-primary)',
                '--primary-hover': 'var(--forest-hover)',
                '--secondary-color': 'var(--forest-secondary)',
                '--accent-color': 'var(--forest-accent)',
                '--dark-bg': 'var(--forest-dark-bg)',
                '--card-bg': 'var(--forest-card-bg)',
                '--border-color': 'var(--forest-border)'
            }
        },
        {
            id: 'ocean',
            name: 'Oceaniczny Błękit', 
            desc: 'Głębokie odcienie niebieskiego inspirowane oceanem',
            vars: {
                '--primary-color': 'var(--ocean-primary)',
                '--primary-hover': 'var(--ocean-hover)',
                '--secondary-color': 'var(--ocean-secondary)',
                '--accent-color': 'var(--ocean-accent)',
                '--dark-bg': 'var(--ocean-dark-bg)',
                '--card-bg': 'var(--ocean-card-bg)',
                '--border-color': 'var(--ocean-border)'
            }
        },
        {
            id: 'amber',
            name: 'Bursztynowy Zachód', 
            desc: 'Ciepłe odcienie brązu i bursztynu jak zachód słońca',
            vars: {
                '--primary-color': 'var(--amber-primary)',
                '--primary-hover': 'var(--amber-hover)',
                '--secondary-color': 'var(--amber-secondary)',
                '--accent-color': 'var(--amber-accent)',
                '--dark-bg': 'var(--amber-dark-bg)',
                '--card-bg': 'var(--amber-card-bg)',
                '--border-color': 'var(--amber-border)'
            }
        },
        {
            id: 'rose',
            name: 'Szkarłatna Róża', 
            desc: 'Eleganckie odcienie czerwieni i burgunda',
            vars: {
                '--primary-color': 'var(--rose-primary)',
                '--primary-hover': 'var(--rose-hover)',
                '--secondary-color': 'var(--rose-secondary)',
                '--accent-color': 'var(--rose-accent)',
                '--dark-bg': 'var(--rose-dark-bg)',
                '--card-bg': 'var(--rose-card-bg)',
                '--border-color': 'var(--rose-border)'
            }
        },
        {
            id: 'lagoon',
            name: 'Turkusowa Laguna', 
            desc: 'Orzeźwiające odcienie turkusu i morskiej zieleni',
            vars: {
                '--primary-color': 'var(--lagoon-primary)',
                '--primary-hover': 'var(--lagoon-hover)',
                '--secondary-color': 'var(--lagoon-secondary)',
                '--accent-color': 'var(--lagoon-accent)',
                '--dark-bg': 'var(--lagoon-dark-bg)',
                '--card-bg': 'var(--lagoon-card-bg)',
                '--border-color': 'var(--lagoon-border)'
            }
        }
    ];
    
    // Create theme switcher UI
    let themeHtml = `
        <div class="dropdown mt-1">
            <button class="btn btn-sm dropdown-toggle theme-dropdown" type="button" id="themeDropdown" data-bs-toggle="dropdown" aria-expanded="false">
                <i class="fas fa-palette me-1"></i> Motyw
            </button>
            <ul class="dropdown-menu dropdown-menu-end" aria-labelledby="themeDropdown">
    `;
    
    // Add themes to dropdown
    themes.forEach(theme => {
        themeHtml += `
            <li>
                <button class="dropdown-item theme-item" data-theme="${theme.id}">
                    <span class="theme-color-dot" style="background: ${theme.vars['--primary-color']}"></span>
                    <div class="ms-2">
                        <div class="theme-name">${theme.name}</div>
                        <small class="theme-desc">${theme.desc}</small>
                    </div>
                </button>
            </li>
        `;
    });
    
    themeHtml += `</ul></div>`;
    themeSwitcherContainer.innerHTML = themeHtml;
    
    // Add some additional CSS for theme switcher UI
    const style = document.createElement('style');
    style.textContent = `
        .theme-dropdown {
            color: rgba(255,255,255,0.7);
            background-color: transparent;
            border: none;
            padding: 0.25rem 0.5rem;
            font-size: 0.85rem;
        }
        .theme-dropdown:hover {
            color: white;
            background-color: rgba(255,255,255,0.1);
        }
        .theme-item {
            display: flex;
            align-items: center;
            padding: 0.5rem 1rem;
        }
        .theme-color-dot {
            width: 16px;
            height: 16px;
            border-radius: 50%;
            display: inline-block;
        }
        .theme-name {
            font-size: 0.9rem;
            font-weight: 500;
        }
        .theme-desc {
            font-size: 0.75rem;
            opacity: 0.7;
        }
    `;
    document.head.appendChild(style);
    
    // Load saved theme preference from localStorage
    const savedTheme = localStorage.getItem('selectedTheme');
    if (savedTheme) {
        applyTheme(savedTheme);
    }
    
    // Add event listeners to theme switcher
    const themeButtons = document.querySelectorAll('.theme-item');
    themeButtons.forEach(button => {
        button.addEventListener('click', function() {
            const themeId = this.getAttribute('data-theme');
            applyTheme(themeId);
            
            // Save theme preference
            localStorage.setItem('selectedTheme', themeId);
        });
    });
    
    // Function to apply a theme
    function applyTheme(themeId) {
        const theme = themes.find(t => t.id === themeId);
        if (!theme) return;
        
        // Apply CSS variables
        const root = document.documentElement;
        Object.entries(theme.vars).forEach(([property, value]) => {
            root.style.setProperty(property, value);
        });
        
        // Update dropdown text (optional)
        const dropdown = document.getElementById('themeDropdown');
        dropdown.innerHTML = `<i class="fas fa-palette me-1"></i> ${theme.name}`;
    }
});
