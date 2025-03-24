#!/usr/bin/env python3

import gi
import re
import os
gi.require_version('Gtk', '3.0')
gi.require_version('Vte', '2.91')
from gi.repository import Gtk, Gdk, Pango, Vte, GLib, GObject

from modules.terminal_tab import TerminalTab
from modules.tab_label import TabLabel
from modules.dialogs import Dialogs
from modules.plugins import Plugins
from modules.themes import Themes
import modules.config as config
from modules.plugin_manager import PluginManager

class HyxTerminal(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="HyxTerminal")
        
        # Set application icon
        self.set_application_icon()
        
        # Enable transparency
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)
        
        # Set transparent background
        self.set_app_paintable(True)
        
        # Initialize fullscreen state
        self.is_fullscreen = False
        
        # Load config
        self.config = config.load_config()
        self.set_default_size(
            self.config.get('window_width', 800),
            self.config.get('window_height', 600)
        )

        # Initialize plugin manager
        self.plugin_manager = PluginManager()
        
        # Create main vertical box
        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(self.vbox)

        # Create menubar with solid background
        menubar = Gtk.MenuBar()
        menubar_style = menubar.get_style_context()
        menubar_css = Gtk.CssProvider()
        bg_color = self.config.get('background_color', '#000000')
        css = f"""
        menubar {{
            background-color: {bg_color};
            color: {self.config.get('foreground_color', '#FFFFFF')};
        }}
        """
        menubar_css.load_from_data(css.encode())
        menubar_style.add_provider(menubar_css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.vbox.pack_start(menubar, False, False, 0)

        # File menu
        file_menu = Gtk.MenuItem.new_with_label("File")
        file_submenu = Gtk.Menu()
        file_menu.set_submenu(file_submenu)

        # File menu items with accelerators
        new_tab = Gtk.MenuItem.new_with_label("New Tab" + " " * 13 + "Ctrl+Shift+T")
        new_tab.connect("activate", lambda w: self.new_tab())
        file_submenu.append(new_tab)

        preset_menu = Gtk.MenuItem.new_with_label("New Tab with Preset")
        preset_submenu = Gtk.Menu()
        preset_menu.set_submenu(preset_submenu)
        file_submenu.append(preset_menu)

        # Add preset options
        presets = [
            ("1 Terminal", "single"),
            ("2 Horizontal Terminals", "horizontal"),
            ("2 Vertical Terminals", "vertical"),
            ("4 Terminals", "quad"),
            ("Custom...", "custom")
        ]
        
        for label, layout in presets:
            item = Gtk.MenuItem.new_with_label(label)
            item.connect("activate", lambda w, l: self.new_tab(l), layout)
            preset_submenu.append(item)

        new_window = Gtk.MenuItem.new_with_label("New Window")
        new_window.connect("activate", self.new_window)
        file_submenu.append(new_window)

        file_submenu.append(Gtk.SeparatorMenuItem())

        close_tab = Gtk.MenuItem.new_with_label("Close Tab" + " " * 11 + "Ctrl+Shift+W")
        close_tab.connect("activate", self.close_current_tab)
        file_submenu.append(close_tab)

        file_submenu.append(Gtk.SeparatorMenuItem())

        preferences = Gtk.MenuItem.new_with_label("Preferences...")
        preferences.connect("activate", self.show_preferences)
        file_submenu.append(preferences)

        file_submenu.append(Gtk.SeparatorMenuItem())

        quit_item = Gtk.MenuItem.new_with_label("Quit" + " " * 18 + "Ctrl+Q")
        quit_item.connect("activate", Gtk.main_quit)
        file_submenu.append(quit_item)
        menubar.append(file_menu)

        # Edit menu
        edit_menu = Gtk.MenuItem.new_with_label("Edit")
        edit_submenu = Gtk.Menu()
        edit_menu.set_submenu(edit_submenu)

        copy_item = Gtk.MenuItem.new_with_label("Copy Selection" + " " * 6 + "Ctrl+Shift+C")
        copy_item.connect("activate", self.copy_selection)
        edit_submenu.append(copy_item)

        paste_item = Gtk.MenuItem.new_with_label("Paste Clipboard" + " " * 5 + "Ctrl+Shift+V")
        paste_item.connect("activate", self.paste_clipboard)
        edit_submenu.append(paste_item)

        paste_selection = Gtk.MenuItem.new_with_label("Paste Selection" + " " * 5 + "Shift+Insert")
        paste_selection.connect("activate", self.paste_selection)
        edit_submenu.append(paste_selection)

        edit_submenu.append(Gtk.SeparatorMenuItem())

        zoom_in = Gtk.MenuItem.new_with_label("Zoom In" + " " * 15 + "Ctrl++")
        zoom_in.connect("activate", self.zoom_in)
        edit_submenu.append(zoom_in)

        zoom_out = Gtk.MenuItem.new_with_label("Zoom Out" + " " * 12 + "Ctrl+-")
        zoom_out.connect("activate", self.zoom_out)
        edit_submenu.append(zoom_out)

        zoom_reset = Gtk.MenuItem.new_with_label("Zoom Reset" + " " * 9 + "Ctrl+0")
        zoom_reset.connect("activate", self.zoom_reset)
        edit_submenu.append(zoom_reset)

        menubar.append(edit_menu)

        # Actions menu
        actions_menu = Gtk.MenuItem.new_with_label("Actions")
        actions_submenu = Gtk.Menu()
        actions_menu.set_submenu(actions_submenu)

        # Clear Terminal
        clear_terminal = Gtk.MenuItem.new_with_label("Clear Active Terminal" + " " * 4 + "Ctrl+Shift+X")
        clear_terminal.connect("activate", self.clear_active_terminal)
        actions_submenu.append(clear_terminal)

        actions_submenu.append(Gtk.SeparatorMenuItem())

        # Tab navigation
        next_tab = Gtk.MenuItem.new_with_label("Next Tab" + " " * 16 + "Ctrl+PgUp")
        next_tab.connect("activate", self.next_tab)
        actions_submenu.append(next_tab)

        prev_tab = Gtk.MenuItem.new_with_label("Previous Tab" + " " * 12 + "Ctrl+PgDown")
        prev_tab.connect("activate", self.previous_tab)
        actions_submenu.append(prev_tab)

        # Go to terminal submenu
        goto_menu = Gtk.MenuItem.new_with_label("Go to")
        goto_submenu = Gtk.Menu()
        goto_menu.set_submenu(goto_submenu)
        actions_submenu.append(goto_menu)

        actions_submenu.append(Gtk.SeparatorMenuItem())

        # Split options
        split_h = Gtk.MenuItem.new_with_label("Split Terminal Horizontally")
        split_h.connect("activate", self.split_horizontal)
        actions_submenu.append(split_h)

        split_v = Gtk.MenuItem.new_with_label("Split Terminal Vertically")
        split_v.connect("activate", self.split_vertical)
        actions_submenu.append(split_v)

        actions_submenu.append(Gtk.SeparatorMenuItem())

        # Find
        find_item = Gtk.MenuItem.new_with_label("Find..." + " " * 16 + "Ctrl+Shift+F")
        find_item.connect("activate", self.show_find_dialog)
        actions_submenu.append(find_item)

        menubar.append(actions_menu)

        # View menu
        view_menu = Gtk.MenuItem.new_with_label("View")
        view_submenu = Gtk.Menu()
        view_menu.set_submenu(view_submenu)

        # Fullscreen toggle
        fullscreen_item = Gtk.MenuItem.new_with_label("Toggle Fullscreen" + " " * 8 + "F11")
        fullscreen_item.connect("activate", self.toggle_fullscreen)
        view_submenu.append(fullscreen_item)

        # Show/hide menubar
        menubar_item = Gtk.MenuItem.new_with_label("Toggle Menubar" + " " * 9 + "F10")
        menubar_item.connect("activate", self.toggle_menubar)
        view_submenu.append(menubar_item)

        view_submenu.append(Gtk.SeparatorMenuItem())

        # Theme submenu
        theme_item = Gtk.MenuItem.new_with_label("Terminal Theme")
        theme_submenu = Themes.create_theme_menu(self)
        theme_item.set_submenu(theme_submenu)
        
        view_submenu.append(theme_item)
        menubar.append(view_menu)

        # Plugins menu
        plugins_menu = Gtk.MenuItem.new_with_label("Plugins")
        plugins_submenu = Gtk.Menu()
        plugins_menu.set_submenu(plugins_submenu)

        # Plugin browser
        manage_plugins = Gtk.MenuItem.new_with_label("Plugin Browser...")
        manage_plugins.connect("activate", lambda w: Plugins.show_plugin_browser(self))
        plugins_submenu.append(manage_plugins)

        plugins_submenu.append(Gtk.SeparatorMenuItem())

        # Sample plugins
        command_palette = Gtk.MenuItem.new_with_label("Command Palette" + " " * 7 + "Ctrl+Shift+P")
        command_palette.connect("activate", lambda w: Plugins.show_command_palette(self))
        plugins_submenu.append(command_palette)

        smart_completion = Gtk.CheckMenuItem.new_with_label("Smart Command Completion")
        smart_completion.set_active(True)
        smart_completion.connect("toggled", lambda w: Plugins.toggle_smart_completion(w, self))
        plugins_submenu.append(smart_completion)

        # More plugin options
        clipboard_manager = Gtk.MenuItem.new_with_label("Clipboard Manager")
        clipboard_manager.connect("activate", lambda w: Plugins.show_clipboard_manager(self))
        plugins_submenu.append(clipboard_manager)

        plugins_submenu.append(Gtk.SeparatorMenuItem())

        # Plugin settings
        plugin_settings = Gtk.MenuItem.new_with_label("Plugin Settings...")
        plugin_settings.connect("activate", lambda w: Plugins.show_plugin_browser(self))
        plugins_submenu.append(plugin_settings)

        menubar.append(plugins_menu)

        # Help menu
        help_menu = Gtk.MenuItem.new_with_label("Help")
        help_submenu = Gtk.Menu()
        help_menu.set_submenu(help_submenu)

        # Help items
        documentation = Gtk.MenuItem.new_with_label("Documentation" + " " * 10 + "F1")
        documentation.connect("activate", lambda w: Plugins.show_documentation(self))
        help_submenu.append(documentation)

        keyboard_shortcuts = Gtk.MenuItem.new_with_label("Keyboard Shortcuts...")
        keyboard_shortcuts.connect("activate", lambda w: Dialogs.show_keyboard_shortcuts(self))
        help_submenu.append(keyboard_shortcuts)

        help_submenu.append(Gtk.SeparatorMenuItem())

        # Check for updates
        check_updates = Gtk.MenuItem.new_with_label("Check for Updates...")
        check_updates.connect("activate", lambda w: Dialogs.check_for_updates(self))
        help_submenu.append(check_updates)

        help_submenu.append(Gtk.SeparatorMenuItem())

        # About dialog
        about_item = Gtk.MenuItem.new_with_label("About HyxTerminal")
        about_item.connect("activate", lambda w: Dialogs.show_about_dialog(self))
        help_submenu.append(about_item)

        menubar.append(help_menu)

        # Create notebook for tabs
        self.notebook = Gtk.Notebook()
        self.notebook.set_show_tabs(False)  # Initially hide tabs
        self.notebook.connect("page-added", self.on_tab_added)
        self.notebook.connect("page-removed", self.on_tab_removed)
        
        # Style the notebook
        notebook_css = Gtk.CssProvider()
        notebook_css.load_from_data(f"""
        notebook {{
            background-color: {bg_color};
        }}
        notebook tab {{
            background-color: {bg_color};
            color: {self.config.get('foreground_color', '#FFFFFF')};
            padding: 4px;
        }}
        notebook tab:checked {{
            background-color: shade({bg_color}, 1.2);
        }}
        """.encode())
        self.notebook.get_style_context().add_provider(
            notebook_css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        
        self.vbox.pack_start(self.notebook, True, True, 0)
        
        # Create first tab
        self.new_tab()
        
        # Key bindings
        self.connect("key-press-event", self.on_key_press)

    def get_current_terminal(self):
        """Get the terminal from the current tab"""
        current_page = self.notebook.get_current_page()
        if current_page != -1:
            tab = self.notebook.get_nth_page(current_page)
            if hasattr(tab, 'terminals') and tab.terminals:
                return tab.terminal
        return None

    def show_preferences(self, widget):
        """Show preferences dialog using the Dialogs module"""
        def update_terminals(bg_color, fg_color, opacity, font_scale, scrollback_lines, cursor_shape):
            for i in range(self.notebook.get_n_pages()):
                tab = self.notebook.get_nth_page(i)
                tab.update_colors(bg_color, fg_color, opacity)
                for terminal in tab.terminals:
                    terminal.set_font_scale(font_scale)
                    terminal.set_scrollback_lines(scrollback_lines)
                    tab.update_cursor(cursor_shape)
            
            # Update window size
            self.resize(self.config['window_width'], self.config['window_height'])
            
            # Update menubar style when colors change
            menubar = self.vbox.get_children()[0]
            menubar_style = menubar.get_style_context()
            menubar_css = Gtk.CssProvider()
            css = f"""
            menubar {{
                background-color: {bg_color};
                color: {fg_color};
            }}
            """
            menubar_css.load_from_data(css.encode())
            menubar_style.add_provider(menubar_css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        Dialogs.show_preferences(self, self.config, update_terminals)

    def new_window(self, widget):
        """Create and show a new terminal window"""
        window = HyxTerminal()
        window.show_all()

    def new_tab(self, layout="single"):
        """Add a new terminal tab with specified layout"""
        tab = TerminalTab(self, layout)
        label = TabLabel(f"Terminal {self.notebook.get_n_pages() + 1}", tab, self.notebook)
        page_num = self.notebook.append_page(tab, label)
        self.notebook.set_tab_reorderable(tab, True)
        tab.show_all()
        # Switch to the new tab explicitly
        self.notebook.set_current_page(page_num)
        # Update the Go to menu
        self.update_goto_menu()

    def close_current_tab(self, widget):
        """Close the current tab"""
        current_page = self.notebook.get_current_page()
        if current_page != -1:
            self.notebook.remove_page(current_page)

    def on_tab_added(self, notebook, child, page_num):
        """Show tabs bar when there's more than one tab"""
        self.notebook.set_show_tabs(notebook.get_n_pages() > 1)

    def on_tab_removed(self, notebook, child, page_num):
        """Hide tabs bar when only one tab remains"""
        self.notebook.set_show_tabs(notebook.get_n_pages() > 1)

    def on_key_press(self, widget, event):
        """Handle keyboard shortcuts"""
        modifiers = event.state & Gtk.accelerator_get_default_mod_mask()
        keyval = event.keyval
        keyval_name = Gdk.keyval_name(keyval)
        
        # F10, F11, and F1 keys
        if event.keyval == Gdk.KEY_F11:
            self.toggle_fullscreen(None)
            return True
        elif event.keyval == Gdk.KEY_F10:
            self.toggle_menubar(None)
            return True
        elif event.keyval == Gdk.KEY_F1:
            Plugins.show_documentation(self)
            return True
        
        # Check for Ctrl+Space for AI Command Agent
        if modifiers == Gdk.ModifierType.CONTROL_MASK and keyval_name == "space":
            # Directly call the command palette (which uses our AI Command Agent)
            Plugins.show_command_palette(self)
            return True
        
        # Control pressed
        if modifiers == Gdk.ModifierType.CONTROL_MASK:
            if event.keyval in (Gdk.KEY_plus, Gdk.KEY_equal):
                self.zoom_in(None)
                return True
            elif event.keyval == Gdk.KEY_minus:
                self.zoom_out(None)
                return True
            elif event.keyval in (Gdk.KEY_0, Gdk.KEY_KP_0):
                self.zoom_reset(None)
                return True

        # Ctrl+Shift combinations
        if modifiers == (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK):
            if event.keyval == Gdk.KEY_T:
                self.new_tab()
                return True
            elif event.keyval == Gdk.KEY_W:
                self.close_current_tab(None)
                return True
            elif event.keyval == Gdk.KEY_C:
                self.copy_selection(None)
                return True
            elif event.keyval == Gdk.KEY_V:
                self.paste_clipboard(None)
                return True
            elif event.keyval == Gdk.KEY_X:
                self.clear_active_terminal(None)
                return True
            elif event.keyval == Gdk.KEY_F:
                self.show_find_dialog(None)
                return True
            elif event.keyval == Gdk.KEY_P:
                Plugins.show_command_palette(self)
                return True

        # Handle Ctrl+PgUp/PgDown
        if modifiers == Gdk.ModifierType.CONTROL_MASK:
            if event.keyval == Gdk.KEY_Page_Up:
                self.next_tab(None)
                return True
            elif event.keyval == Gdk.KEY_Page_Down:
                self.previous_tab(None)
                return True

        # Shift+Insert
        if modifiers == Gdk.ModifierType.SHIFT_MASK and event.keyval == Gdk.KEY_Insert:
            self.paste_selection(None)
            return True

        return False

    # Edit menu actions
    def copy_selection(self, widget):
        terminal = self.get_current_terminal()
        if terminal:
            terminal.copy_clipboard()

    def paste_clipboard(self, widget):
        terminal = self.get_current_terminal()
        if terminal:
            terminal.paste_clipboard()

    def paste_selection(self, widget):
        terminal = self.get_current_terminal()
        if terminal:
            terminal.paste_primary()

    def zoom_in(self, widget):
        terminal = self.get_current_terminal()
        if terminal:
            current_scale = terminal.get_font_scale()
            terminal.set_font_scale(current_scale + 0.1)

    def zoom_out(self, widget):
        terminal = self.get_current_terminal()
        if terminal:
            current_scale = terminal.get_font_scale()
            terminal.set_font_scale(max(0.1, current_scale - 0.1))

    def zoom_reset(self, widget):
        terminal = self.get_current_terminal()
        if terminal:
            terminal.set_font_scale(1.0)

    def clear_active_terminal(self, widget):
        terminal = self.get_current_terminal()
        if terminal:
            # Send the clear command instead of reset
            terminal.feed_child("clear\n".encode())

    def next_tab(self, widget):
        current = self.notebook.get_current_page()
        if current < self.notebook.get_n_pages() - 1:
            self.notebook.set_current_page(current + 1)
        else:
            self.notebook.set_current_page(0)

    def previous_tab(self, widget):
        current = self.notebook.get_current_page()
        if current > 0:
            self.notebook.set_current_page(current - 1)
        else:
            self.notebook.set_current_page(self.notebook.get_n_pages() - 1)

    def split_horizontal(self, widget):
        current_page = self.notebook.get_current_page()
        if current_page != -1:
            tab = self.notebook.get_nth_page(current_page)
            tab.create_horizontal_split()

    def split_vertical(self, widget):
        current_page = self.notebook.get_current_page()
        if current_page != -1:
            tab = self.notebook.get_nth_page(current_page)
            tab.create_vertical_split()

    def update_goto_menu(self):
        """Update the Go to submenu with current terminal tabs"""
        goto_menu = None
        actions_menu = None
        
        # Find the Actions menu and its Go to submenu
        menubar = self.vbox.get_children()[0]
        for menu_item in menubar.get_children():
            if menu_item.get_label() == "Actions":
                actions_menu = menu_item.get_submenu()
                break
        
        if actions_menu:
            for menu_item in actions_menu.get_children():
                if menu_item.get_label() == "Go to":
                    goto_menu = menu_item.get_submenu()
                    break

        if goto_menu:
            # Clear existing items
            goto_menu.foreach(lambda w: goto_menu.remove(w))
            
            # Add menu item for each tab
            for i in range(self.notebook.get_n_pages()):
                tab = self.notebook.get_nth_page(i)
                label = self.notebook.get_tab_label(tab).label.get_text()
                item = Gtk.MenuItem.new_with_label(f"{label}")
                item.connect("activate", lambda w, num: self.notebook.set_current_page(num), i)
                goto_menu.append(item)
            goto_menu.show_all()

    def show_find_dialog(self, widget):
        """Show find dialog using Dialogs module"""
        def do_find(text, case_sensitive, use_regex, backward, clear=False):
            terminal = self.get_current_terminal()
            if not terminal:
                return False
            
            if clear:
                # Clear search highlighting
                terminal.search_set_regex(None, 0)
                return True
            
            if not text:
                return False
            
            try:
                # Clear previous search
                terminal.search_set_regex(None, 0)
                
                # Prepare pattern
                pattern = text if use_regex else re.escape(text)
                
                try:
                    # Set up regex flags for VTE
                    # MULTILINE (8) is required by VTE for proper terminal search
                    # PCRE2_MULTILINE (1) is for regex multiline mode
                    flags = 8 | 1  # VTE multiline flag | PCRE2_MULTILINE
                    
                    if not case_sensitive:
                        flags |= 2  # PCRE2_CASELESS
                    
                    # Create regex for searching
                    regex = Vte.Regex.new_for_search(pattern, -1, flags)
                    
                    # Enable wrap-around search by default
                    terminal.search_set_wrap_around(True)
                    
                    # Set up search pattern with proper flags
                    terminal.search_set_regex(regex, flags)
                    
                    # Perform search
                    if backward:
                        found = terminal.search_find_previous()
                    else:
                        found = terminal.search_find_next()
                    
                    return found
                    
                except GLib.Error as e:
                    print(f"Invalid regex pattern: {e}")
                    return False
                
            except Exception as e:
                print(f"Search error: {e}")
                return False
        
        Dialogs.show_find_dialog(self, do_find)

    def toggle_fullscreen(self, widget):
        """Toggle fullscreen mode"""
        if self.is_fullscreen:
            self.unfullscreen()
            self.is_fullscreen = False
        else:
            self.fullscreen()
            self.is_fullscreen = True

    def toggle_menubar(self, widget):
        """Toggle menubar visibility"""
        menubar = self.vbox.get_children()[0]
        menubar.set_visible(not menubar.get_visible())
        # Save preference
        self.config['show_menubar'] = menubar.get_visible()
        config.save_config(self.config)

    def set_application_icon(self):
        """Set the application icon from the logo file"""
        try:
            # Try to find the icon in different locations
            icon_paths = [
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "HyxTerminal.png"),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "HyxTerminal.png"),
                "/usr/share/icons/hicolor/128x128/apps/hyxterminal.png",
                "/usr/share/pixmaps/hyxterminal.png"
            ]
            
            for icon_path in icon_paths:
                if os.path.exists(icon_path):
                    self.set_icon_from_file(icon_path)
                    return
                    
            # If we couldn't find the icon, use a fallback icon
            self.set_icon_name("utilities-terminal")
        except Exception as e:
            print(f"Failed to set application icon: {e}")
            # Fall back to a standard icon
            self.set_icon_name("utilities-terminal")

if __name__ == "__main__":
    win = HyxTerminal()
    win.connect("delete-event", Gtk.main_quit)
    win.show_all()
    try:
        Gtk.main()
    except KeyboardInterrupt:
        win.destroy()
