import re

def fix_index_html():
    with open('templates/index.html', 'r') as f:
        content = f.read()
    
    # Fix navbar with stats link and remove duplicate theme switcher
    pattern = r'<ul class="navbar-nav ms-auto">.*?</li>\s*</ul>'
    replacement = '''<ul class="navbar-nav ms-auto">
                    <li class="nav-item">
                        <a class="nav-link active" href="/"><i class="fas fa-home me-1"></i> Strona główna</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/info"><i class="fas fa-book me-1"></i> Dokumentacja</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/logs"><i class="fas fa-clipboard-list me-1"></i> Logi</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/history"><i class="fas fa-history me-1"></i> Historia</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/stats"><i class="fas fa-chart-bar me-1"></i> Statystyki</a>
                    </li>
                    <li class="nav-item ms-2" id="themeSwitcher"></li>
                </ul>'''
    
    updated_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    with open('templates/index.html', 'w') as f:
        f.write(updated_content)
    
    return "Fixed index.html"

def update_all_navbars():
    # Get the list of all template files except stats.html which is already fixed
    import os
    templates = [f for f in os.listdir('templates') if f.endswith('.html') and f != 'stats.html']
    
    results = []
    for template in templates:
        results.append(update_navbar(template))
    
    return results

def update_navbar(template_name):
    with open(f'templates/{template_name}', 'r') as f:
        content = f.read()
    
    # Check if stats link is already present
    if '/stats' in content:
        return f"{template_name} already has stats link"
    
    # Find the history link and add stats link after it
    history_pattern = r'<a class="nav-link.*?href="/history">.*?</a>\s*</li>'
    history_match = re.search(history_pattern, content, re.DOTALL)
    
    if history_match:
        history_link = history_match.group(0)
        stats_link = '''
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/stats"><i class="fas fa-chart-bar me-1"></i> Statystyki</a>'''
        
        updated_content = content.replace(history_link, history_link + stats_link)
        
        with open(f'templates/{template_name}', 'w') as f:
            f.write(updated_content)
        
        return f"Updated {template_name} with stats link"
    else:
        return f"Could not find history link in {template_name}"

if __name__ == "__main__":
    print(fix_index_html())
    print(update_all_navbars())
