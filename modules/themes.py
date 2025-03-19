import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from modules import config

class Themes:
    # Predefined themes (background_color, foreground_color, name)
    THEME_LIST = [
        ("HyxTerminal", "#282A36", "#FFFFFF"),  # Default HyxTerminal brand theme
        ("Default Dark", "#000000", "#FFFFFF"),
        ("Solarized Dark", "#002b36", "#839496"),
        ("Solarized Light", "#fdf6e3", "#657b83"),
        ("Monokai", "#272822", "#f8f8f2"),
        ("Dracula", "#282a36", "#f8f8f2"),
        ("Nord", "#2e3440", "#d8dee9")
    ]
    
    @staticmethod
    def create_theme_menu(parent_window):
        """Create and return a submenu with theme options"""
        theme_submenu = Gtk.Menu()
        
        for name, bg, fg in Themes.THEME_LIST:
            item = Gtk.MenuItem.new_with_label(name)
            item.connect("activate", lambda w, b, f, n: Themes.apply_theme(parent_window, b, f, n), bg, fg, name)
            theme_submenu.append(item)
            
        return theme_submenu
    
    @staticmethod
    def apply_theme(parent_window, bg, fg, name):
        """Apply a theme to the terminal"""
        # Update configuration
        parent_window.config.update({
            'background_color': bg,
            'foreground_color': fg,
            'font_scale': 1.0  # Reset font scale for consistency
        })

        # Apply changes to all terminal tabs
        opacity = parent_window.config.get('background_opacity', 0.9)
        for i in range(parent_window.notebook.get_n_pages()):
            tab = parent_window.notebook.get_nth_page(i)
            tab.update_colors(bg, fg, opacity)
            tab.terminal.set_font_scale(1.0)
            
        # Update menubar style
        menubar = parent_window.vbox.get_children()[0]
        menubar_style = menubar.get_style_context()
        menubar_css = Gtk.CssProvider()
        css = f"""
        menubar {{
            background-color: {bg};
            color: {fg};
        }}
        """
        menubar_css.load_from_data(css.encode())
        menubar_style.add_provider(menubar_css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        # Save configuration
        config.save_config(parent_window.config) 