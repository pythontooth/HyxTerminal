#!/usr/bin/env python3

import gi
import re
gi.require_version('Gtk', '3.0')
gi.require_version('Vte', '2.91')
from gi.repository import Gtk, Gdk, Pango, Vte, GLib

from modules.terminal_tab import TerminalTab
from modules.tab_label import TabLabel
import modules.config as config

class HyxTerminal(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="HyxTerminal")
        
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
        theme_submenu = Gtk.Menu()
        theme_item.set_submenu(theme_submenu)

        themes = [
            ("Default Dark", "#000000", "#FFFFFF"),
            ("Solarized Dark", "#002b36", "#839496"),
            ("Solarized Light", "#fdf6e3", "#657b83"),
            ("Monokai", "#272822", "#f8f8f2"),
            ("Dracula", "#282a36", "#f8f8f2"),
            ("Nord", "#2e3440", "#d8dee9")
        ]

        for name, bg, fg in themes:
            item = Gtk.MenuItem.new_with_label(name)
            item.connect("activate", lambda w, b, f, n: self.apply_theme(b, f, n), bg, fg, name)
            theme_submenu.append(item)

        view_submenu.append(theme_item)
        menubar.append(view_menu)

        # Plugins menu
        plugins_menu = Gtk.MenuItem.new_with_label("Plugins")
        plugins_submenu = Gtk.Menu()
        plugins_menu.set_submenu(plugins_submenu)

        # Plugin browser
        manage_plugins = Gtk.MenuItem.new_with_label("Plugin Browser...")
        manage_plugins.connect("activate", self.show_plugin_browser)
        plugins_submenu.append(manage_plugins)

        plugins_submenu.append(Gtk.SeparatorMenuItem())

        # Sample plugins
        command_palette = Gtk.MenuItem.new_with_label("Command Palette" + " " * 7 + "Ctrl+Shift+P")
        command_palette.connect("activate", self.show_command_palette)
        plugins_submenu.append(command_palette)

        smart_completion = Gtk.CheckMenuItem.new_with_label("Smart Command Completion")
        smart_completion.set_active(True)
        smart_completion.connect("toggled", self.toggle_smart_completion)
        plugins_submenu.append(smart_completion)

        # More plugin options
        clipboard_manager = Gtk.MenuItem.new_with_label("Clipboard Manager")
        clipboard_manager.connect("activate", self.show_clipboard_manager)
        plugins_submenu.append(clipboard_manager)

        plugins_submenu.append(Gtk.SeparatorMenuItem())

        # Plugin settings
        plugin_settings = Gtk.MenuItem.new_with_label("Plugin Settings...")
        plugin_settings.connect("activate", self.show_plugin_settings)
        plugins_submenu.append(plugin_settings)

        menubar.append(plugins_menu)

        # Help menu
        help_menu = Gtk.MenuItem.new_with_label("Help")
        help_submenu = Gtk.Menu()
        help_menu.set_submenu(help_submenu)

        # Help items
        documentation = Gtk.MenuItem.new_with_label("Documentation" + " " * 10 + "F1")
        documentation.connect("activate", self.show_documentation)
        help_submenu.append(documentation)

        keyboard_shortcuts = Gtk.MenuItem.new_with_label("Keyboard Shortcuts...")
        keyboard_shortcuts.connect("activate", self.show_keyboard_shortcuts)
        help_submenu.append(keyboard_shortcuts)

        help_submenu.append(Gtk.SeparatorMenuItem())

        # Check for updates
        check_updates = Gtk.MenuItem.new_with_label("Check for Updates...")
        check_updates.connect("activate", self.check_for_updates)
        help_submenu.append(check_updates)

        help_submenu.append(Gtk.SeparatorMenuItem())

        # About dialog
        about_item = Gtk.MenuItem.new_with_label("About HyxTerminal")
        about_item.connect("activate", self.show_about_dialog)
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
            return self.notebook.get_nth_page(current_page).terminal
        return None

    def show_preferences(self, widget):
        dialog = Gtk.Dialog(
            title="Preferences...",
            parent=self,
            flags=0
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OK, Gtk.ResponseType.OK
        )

        box = dialog.get_content_area()
        box.set_spacing(10)
        box.set_margin_start(10)
        box.set_margin_end(10)
        box.set_margin_top(10)
        box.set_margin_bottom(10)

        # Window Size
        size_frame = Gtk.Frame(label="Window Size")
        size_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        size_frame.add(size_box)

        width_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        width_label = Gtk.Label(label="Width:")
        width_spin = Gtk.SpinButton.new_with_range(400, 3000, 50)
        width_spin.set_value(self.config.get('window_width', 800))
        width_box.pack_start(width_label, False, False, 0)
        width_box.pack_start(width_spin, True, True, 0)
        size_box.add(width_box)

        height_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        height_label = Gtk.Label(label="Height:")
        height_spin = Gtk.SpinButton.new_with_range(300, 2000, 50)
        height_spin.set_value(self.config.get('window_height', 600))
        height_box.pack_start(height_label, False, False, 0)
        height_box.pack_start(height_spin, True, True, 0)
        size_box.add(height_box)
        box.add(size_frame)

        # Font Settings
        font_frame = Gtk.Frame(label="Font Settings")
        font_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        font_frame.add(font_box)

        font_button = Gtk.FontButton()
        font_desc = Pango.FontDescription.from_string(
            f"{self.config.get('font_family', 'Monospace')} {self.config.get('font_size', 11)}"
        )
        font_button.set_font_desc(font_desc)
        font_box.add(font_button)

        scale_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        scale_label = Gtk.Label(label="Font Scale:")
        scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0.5, 2.0, 0.1)
        current_terminal = self.get_current_terminal()
        if current_terminal:
            scale.set_value(current_terminal.get_font_scale())
        else:
            scale.set_value(self.config.get('font_scale', 1.0))
        scale_box.pack_start(scale_label, False, False, 0)
        scale_box.pack_start(scale, True, True, 0)
        font_box.add(scale_box)

        # Colors
        colors_frame = Gtk.Frame(label="Colors")
        colors_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        colors_frame.add(colors_box)

        bg_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        bg_label = Gtk.Label(label="Background:")
        bg_color = Gtk.ColorButton()
        bg_color.set_rgba(config.parse_color(self.config.get('background_color', '#000000')))
        bg_box.pack_start(bg_label, False, False, 0)
        bg_box.pack_start(bg_color, True, True, 0)
        colors_box.add(bg_box)

        fg_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        fg_label = Gtk.Label(label="Foreground:")
        fg_color = Gtk.ColorButton()
        fg_color.set_rgba(config.parse_color(self.config.get('foreground_color', '#FFFFFF')))
        fg_box.pack_start(fg_label, False, False, 0)
        fg_box.pack_start(fg_color, True, True, 0)
        colors_box.add(fg_box)

        # Add opacity control
        opacity_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        opacity_label = Gtk.Label(label="Background Opacity:")
        opacity_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0.0, 1.0, 0.1)
        opacity_scale.set_value(self.config.get('background_opacity', 0.9))
        opacity_box.pack_start(opacity_label, False, False, 0)
        opacity_box.pack_start(opacity_scale, True, True, 0)
        colors_box.add(opacity_box)
        box.add(colors_frame)

        # Terminal Settings
        term_frame = Gtk.Frame(label="Terminal Settings")
        term_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        term_frame.add(term_box)

        scrollback_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        scrollback_label = Gtk.Label(label="Scrollback Lines:")
        scrollback_spin = Gtk.SpinButton.new_with_range(100, 100000, 1000)
        scrollback_spin.set_value(self.config.get('scrollback_lines', 10000))
        scrollback_box.pack_start(scrollback_label, False, False, 0)
        scrollback_box.pack_start(scrollback_spin, True, True, 0)
        term_box.add(scrollback_box)

        cursor_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        cursor_label = Gtk.Label(label="Cursor Shape:")
        cursor_combo = Gtk.ComboBoxText()
        shapes = ['block', 'ibeam', 'underline']
        for shape in shapes:
            cursor_combo.append_text(shape)
        # Set active based on current config
        current_shape = self.config.get('cursor_shape', 'block')
        cursor_combo.set_active(shapes.index(current_shape))
        cursor_box.pack_start(cursor_label, False, False, 0)
        cursor_box.pack_start(cursor_combo, True, True, 0)
        term_box.add(cursor_box)
        box.add(term_frame)

        dialog.show_all()
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            # Update configuration
            self.config.update({
                'window_width': int(width_spin.get_value()),
                'window_height': int(height_spin.get_value()),
                'scrollback_lines': int(scrollback_spin.get_value()),
                'font_scale': scale.get_value(),
                'background_color': config.rgba_to_hex(bg_color.get_rgba()),
                'foreground_color': config.rgba_to_hex(fg_color.get_rgba()),
                'font_family': font_button.get_font_desc().get_family(),
                'font_size': font_button.get_font_desc().get_size() // 1000,
                'cursor_shape': shapes[cursor_combo.get_active()],
                'background_opacity': opacity_scale.get_value()
            })

            # Apply changes to all terminals
            bg_color = self.config['background_color']
            fg_color = self.config['foreground_color']
            opacity = self.config['background_opacity']
            
            for i in range(self.notebook.get_n_pages()):
                tab = self.notebook.get_nth_page(i)
                tab.update_colors(bg_color, fg_color, opacity)
                tab.terminal.set_font_scale(scale.get_value())
                tab.terminal.set_scrollback_lines(int(scrollback_spin.get_value()))
                tab.update_cursor(shapes[cursor_combo.get_active()])

            self.resize(int(width_spin.get_value()), int(height_spin.get_value()))
            
            # Update menubar style when colors change
            menubar = self.get_children()[0].get_children()[0]  # Get menubar from vbox
            menubar_style = menubar.get_style_context()
            menubar_css = Gtk.CssProvider()
            css = f"""
            menubar {{
                background-color: {self.config['background_color']};
                color: {self.config['foreground_color']};
            }}
            """
            menubar_css.load_from_data(css.encode())
            menubar_style.add_provider(menubar_css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

            # Save configuration
            config.save_config(self.config)

        dialog.destroy()

    def new_window(self, widget):
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
        modifiers = event.state & Gtk.accelerator_get_default_mod_mask()
        
        # F10, F11, and F1 keys
        if event.keyval == Gdk.KEY_F11:
            self.toggle_fullscreen(None)
            return True
        elif event.keyval == Gdk.KEY_F10:
            self.toggle_menubar(None)
            return True
        elif event.keyval == Gdk.KEY_F1:
            self.show_documentation(None)
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
                self.show_command_palette(None)
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

    # Add new methods for edit menu actions
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
        dialog = Gtk.Dialog(
            title="Find",
            parent=self,
            flags=0
        )
        dialog.add_buttons(
            Gtk.STOCK_FIND, Gtk.ResponseType.OK,
            Gtk.STOCK_CLOSE, Gtk.ResponseType.CANCEL
        )
        
        box = dialog.get_content_area()
        box.set_spacing(6)
        box.set_margin_start(10)
        box.set_margin_end(10)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        
        # Search entry
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        search_label = Gtk.Label(label="Search:")
        search_entry = Gtk.Entry()
        search_box.pack_start(search_label, False, False, 0)
        search_box.pack_start(search_entry, True, True, 0)
        box.add(search_box)
        
        # Case sensitive checkbox
        case_check = Gtk.CheckButton(label="Case sensitive")
        box.add(case_check)
        
        # Regex checkbox
        regex_check = Gtk.CheckButton(label="Regular expression")
        box.add(regex_check)

        # Search direction
        direction_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        direction_label = Gtk.Label(label="Search direction:")
        backward_check = Gtk.CheckButton(label="Search backward")
        direction_box.pack_start(direction_label, False, False, 0)
        direction_box.pack_start(backward_check, False, False, 0)
        box.add(direction_box)
        
        box.show_all()
        
        def do_search():
            terminal = self.get_current_terminal()
            if terminal and search_entry.get_text():
                # Clear previous search
                terminal.search_set_regex(None, 0)
                
                # Set up search flags
                flags = 0
                if regex_check.get_active():
                    flags |= 1 << 0  # PCRE2_MULTILINE
                if not case_check.get_active():
                    flags |= 1 << 1  # PCRE2_CASELESS
                
                # Set up search pattern
                terminal.search_set_regex(search_entry.get_text(), flags)
                
                # Perform search
                found = terminal.search_find_next() if not backward_check.get_active() else terminal.search_find_previous()
                
                if not found:
                    # If not found, show a message
                    msg_dialog = Gtk.MessageDialog(
                        parent=dialog,
                        flags=0,
                        message_type=Gtk.MessageType.INFO,
                        buttons=Gtk.ButtonsType.OK,
                        text="Text not found"
                    )
                    msg_dialog.run()
                    msg_dialog.destroy()
        
        while True:
            response = dialog.run()
            if response == Gtk.ResponseType.OK:
                do_search()
            else:
                # Clear search highlighting when closing dialog
                terminal = self.get_current_terminal()
                if terminal:
                    terminal.search_set_regex(None, 0)
                break
        
        dialog.destroy()

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

    def apply_theme(self, bg, fg, name):
        self.config.update({
            'background_color': bg,
            'foreground_color': fg,
            'font_family': 'Monospace',
            'font_size': 11,
            'font_scale': 1.0
        })

        # Apply changes to all terminals
        for i in range(self.notebook.get_n_pages()):
            tab = self.notebook.get_nth_page(i)
            tab.update_colors(bg, fg, 0.9)
            tab.terminal.set_font_scale(1.0)

        # Save configuration
        config.save_config(self.config)

    def show_plugin_browser(self, widget):
        """Show plugin browser dialog with available plugins"""
        dialog = Gtk.Dialog(
            title="Plugin Browser",
            parent=self,
            flags=0
        )
        dialog.add_buttons(
            Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE
        )
        dialog.set_default_size(500, 400)
        
        box = dialog.get_content_area()
        box.set_spacing(6)
        box.set_margin_start(10)
        box.set_margin_end(10)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        
        # Create list store for plugins
        # Columns: Name, Description, Enabled, Version, Author
        store = Gtk.ListStore(str, str, bool, str, str)
        
        # Sample plugins
        plugins = [
            ("Smart Completion", "Provides intelligent command completion", True, "1.0", "HyxTerminal Team"),
            ("Clipboard Manager", "Enhanced clipboard with history", False, "0.9", "HyxTerminal Team"),
            ("Theme Switcher", "Automatic theme switching based on time", False, "1.2", "HyxTerminal Team"),
            ("Advanced Search", "Regex-based terminal search", False, "0.8", "HyxTerminal Team"),
            ("Git Integration", "Git branch and status in terminal", False, "1.1", "HyxTerminal Team")
        ]
        
        for name, desc, enabled, version, author in plugins:
            store.append([name, desc, enabled, version, author])
        
        # Create tree view
        treeview = Gtk.TreeView(model=store)
        
        # Add columns
        renderer_toggle = Gtk.CellRendererToggle()
        renderer_toggle.connect("toggled", self.on_plugin_toggled, store)
        column_toggle = Gtk.TreeViewColumn("Enabled", renderer_toggle, active=2)
        treeview.append_column(column_toggle)
        
        renderer_text = Gtk.CellRendererText()
        column_name = Gtk.TreeViewColumn("Plugin", renderer_text, text=0)
        treeview.append_column(column_name)
        
        renderer_text = Gtk.CellRendererText()
        column_desc = Gtk.TreeViewColumn("Description", renderer_text, text=1)
        treeview.append_column(column_desc)
        
        renderer_text = Gtk.CellRendererText()
        column_version = Gtk.TreeViewColumn("Version", renderer_text, text=3)
        treeview.append_column(column_version)
        
        # Add tree view to a scrolled window
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.add(treeview)
        box.pack_start(scrolled, True, True, 0)
        
        # Add plugin details section
        frame = Gtk.Frame(label="Plugin Details")
        details_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        details_box.set_margin_start(10)
        details_box.set_margin_end(10)
        details_box.set_margin_top(10)
        details_box.set_margin_bottom(10)
        
        self.plugin_details_label = Gtk.Label()
        self.plugin_details_label.set_markup("<i>Select a plugin to view details</i>")
        self.plugin_details_label.set_line_wrap(True)
        self.plugin_details_label.set_xalign(0)
        details_box.pack_start(self.plugin_details_label, False, False, 0)
        
        frame.add(details_box)
        box.pack_start(frame, False, False, 0)
        
        # Update details when selection changes
        selection = treeview.get_selection()
        selection.connect("changed", self.on_plugin_selection_changed, store)
        
        dialog.show_all()
        dialog.run()
        dialog.destroy()
    
    def on_plugin_toggled(self, cell, path, store):
        """Toggle plugin enabled state"""
        store[path][2] = not store[path][2]
        plugin_name = store[path][0]
        enabled = store[path][2]
        
        # If this is the smart completion plugin, update the terminal tabs
        if plugin_name == "Smart Completion":
            for i in range(self.notebook.get_n_pages()):
                tab = self.notebook.get_nth_page(i)
                for terminal in tab.terminals:
                    # Enable or disable command completion
                    if hasattr(tab, 'hint_timeouts'):
                        if not enabled and tab.hint_timeouts.get(terminal):
                            tab.clear_hint(terminal)
    
    def on_plugin_selection_changed(self, selection, store):
        """Update plugin details when selection changes"""
        model, treeiter = selection.get_selected()
        if treeiter is not None:
            name = model[treeiter][0]
            desc = model[treeiter][1]
            version = model[treeiter][3]
            author = model[treeiter][4]
            
            details = f"<b>{name}</b> (v{version})\n\n{desc}\n\nAuthor: {author}"
            self.plugin_details_label.set_markup(details)
    
    def toggle_smart_completion(self, widget):
        """Toggle smart command completion in all terminals"""
        enabled = widget.get_active()
        
        # Update all terminal tabs
        for i in range(self.notebook.get_n_pages()):
            tab = self.notebook.get_nth_page(i)
            for terminal in tab.terminals:
                # Clear current hints if disabling
                if not enabled and hasattr(tab, 'hint_timeouts'):
                    if tab.hint_timeouts.get(terminal):
                        tab.clear_hint(terminal)
    
    def show_clipboard_manager(self, widget):
        """Show clipboard manager with history"""
        dialog = Gtk.Dialog(
            title="Clipboard Manager",
            parent=self,
            flags=0
        )
        dialog.add_buttons(
            Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE,
            "Clear History", Gtk.ResponseType.REJECT
        )
        dialog.set_default_size(400, 300)
        
        box = dialog.get_content_area()
        box.set_spacing(6)
        box.set_margin_start(10)
        box.set_margin_end(10)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        
        # Sample clipboard history
        clipboard_items = [
            "ls -la",
            "cd /home/user/projects",
            "git status",
            "docker ps",
            "python3 script.py --verbose",
            "grep -r 'pattern' .",
            "echo $PATH"
        ]
        
        # Create list store
        store = Gtk.ListStore(str)
        for item in clipboard_items:
            store.append([item])
        
        # Create tree view
        treeview = Gtk.TreeView(model=store)
        treeview.set_headers_visible(False)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Content", renderer, text=0)
        treeview.append_column(column)
        
        # Add tree view to scrolled window
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.add(treeview)
        box.pack_start(scrolled, True, True, 0)
        
        # Add "Paste" button
        paste_button = Gtk.Button(label="Paste Selected")
        paste_button.set_sensitive(False)
        box.pack_start(paste_button, False, False, 0)
        
        # Handle selection changes
        selection = treeview.get_selection()
        selection.connect("changed", lambda s: paste_button.set_sensitive(True))
        
        # Handle paste button click
        def on_paste_clicked(button):
            model, treeiter = selection.get_selected()
            if treeiter:
                text = model[treeiter][0]
                terminal = self.get_current_terminal()
                if terminal:
                    terminal.feed_child((text + "\n").encode())
                dialog.destroy()
        
        paste_button.connect("clicked", on_paste_clicked)
        
        # Handle double-click on item
        def on_row_activated(view, path, column):
            treeiter = store.get_iter(path)
            text = store[treeiter][0]
            terminal = self.get_current_terminal()
            if terminal:
                terminal.feed_child((text + "\n").encode())
            dialog.destroy()
        
        treeview.connect("row-activated", on_row_activated)
        
        dialog.show_all()
        response = dialog.run()
        
        if response == Gtk.ResponseType.REJECT:
            # Clear history
            store.clear()
        
        dialog.destroy()
    
    def show_plugin_settings(self, widget):
        """Show settings for installed plugins"""
        dialog = Gtk.Dialog(
            title="Plugin Settings",
            parent=self,
            flags=0
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_APPLY, Gtk.ResponseType.APPLY,
            Gtk.STOCK_OK, Gtk.ResponseType.OK
        )
        dialog.set_default_size(500, 400)
        
        box = dialog.get_content_area()
        box.set_spacing(6)
        box.set_margin_start(10)
        box.set_margin_end(10)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        
        # Create notebook for plugin settings
        notebook = Gtk.Notebook()
        box.pack_start(notebook, True, True, 0)
        
        # Smart Completion settings page
        sc_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        sc_page.set_margin_start(10)
        sc_page.set_margin_end(10)
        sc_page.set_margin_top(10)
        sc_page.set_margin_bottom(10)
        
        delay_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        delay_label = Gtk.Label(label="Completion delay (ms):")
        delay_spinner = Gtk.SpinButton.new_with_range(100, 5000, 100)
        delay_spinner.set_value(1000)  # Default delay is 1000ms
        delay_box.pack_start(delay_label, False, False, 0)
        delay_box.pack_start(delay_spinner, True, True, 0)
        sc_page.pack_start(delay_box, False, False, 0)
        
        case_check = Gtk.CheckButton(label="Case sensitive completion")
        sc_page.pack_start(case_check, False, False, 0)
        
        style_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        style_label = Gtk.Label(label="Hint style:")
        style_combo = Gtk.ComboBoxText()
        for style in ["Subtle", "Bold", "Italic", "Colored"]:
            style_combo.append_text(style)
        style_combo.set_active(0)
        style_box.pack_start(style_label, False, False, 0)
        style_box.pack_start(style_combo, True, True, 0)
        sc_page.pack_start(style_box, False, False, 0)
        
        notebook.append_page(sc_page, Gtk.Label(label="Smart Completion"))
        
        # Theme Switcher settings page
        ts_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        ts_page.set_margin_start(10)
        ts_page.set_margin_end(10)
        ts_page.set_margin_top(10)
        ts_page.set_margin_bottom(10)
        
        auto_switch = Gtk.CheckButton(label="Automatically switch themes")
        ts_page.pack_start(auto_switch, False, False, 0)
        
        day_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        day_label = Gtk.Label(label="Day theme:")
        day_combo = Gtk.ComboBoxText()
        for theme in ["Default Light", "Solarized Light", "GitHub Light"]:
            day_combo.append_text(theme)
        day_combo.set_active(1)
        day_box.pack_start(day_label, False, False, 0)
        day_box.pack_start(day_combo, True, True, 0)
        ts_page.pack_start(day_box, False, False, 0)
        
        night_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        night_label = Gtk.Label(label="Night theme:")
        night_combo = Gtk.ComboBoxText()
        for theme in ["Default Dark", "Solarized Dark", "Dracula", "Nord"]:
            night_combo.append_text(theme)
        night_combo.set_active(0)
        night_box.pack_start(night_label, False, False, 0)
        night_box.pack_start(night_combo, True, True, 0)
        ts_page.pack_start(night_box, False, False, 0)
        
        time_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        time_label = Gtk.Label(label="Switch at:")
        
        day_time = Gtk.SpinButton.new_with_range(0, 23, 1)
        day_time.set_value(7)  # 7:00 AM
        day_label2 = Gtk.Label(label="Day starts at:")
        
        night_time = Gtk.SpinButton.new_with_range(0, 23, 1)
        night_time.set_value(19)  # 7:00 PM
        night_label2 = Gtk.Label(label="Night starts at:")
        
        time_box.pack_start(day_label2, False, False, 0)
        time_box.pack_start(day_time, False, False, 0)
        time_box.pack_start(night_label2, False, False, 0)
        time_box.pack_start(night_time, False, False, 0)
        ts_page.pack_start(time_box, False, False, 0)
        
        notebook.append_page(ts_page, Gtk.Label(label="Theme Switcher"))
        
        dialog.show_all()
        response = dialog.run()
        
        if response in [Gtk.ResponseType.OK, Gtk.ResponseType.APPLY]:
            # Save settings (simulated)
            pass
            
        dialog.destroy()
    
    def check_for_updates(self, widget):
        """Check for application updates"""
        # Create a progress dialog
        dialog = Gtk.Dialog(
            title="Checking for Updates",
            parent=self,
            flags=0
        )
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        dialog.set_default_size(300, 100)
        
        box = dialog.get_content_area()
        box.set_spacing(6)
        box.set_margin_start(10)
        box.set_margin_end(10)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        
        # Add status label
        status_label = Gtk.Label(label="Checking for available updates...")
        box.pack_start(status_label, False, False, 0)
        
        # Add progress bar
        progress = Gtk.ProgressBar()
        box.pack_start(progress, False, False, 0)
        
        dialog.show_all()
        
        # Simulate update check with progress updates
        def update_progress():
            progress.pulse()
            return True
            
        def finish_check():
            dialog.destroy()
            
            # Show result dialog
            result_dialog = Gtk.MessageDialog(
                parent=self,
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text="Update Check Complete"
            )
            result_dialog.format_secondary_text(
                "HyxTerminal is up to date (version 1.0.0)"
            )
            result_dialog.run()
            result_dialog.destroy()
            
            return False
        
        # Start progress updates
        GLib.timeout_add(100, update_progress)
        
        # Schedule completion after 2 seconds
        GLib.timeout_add(2000, finish_check)
        
        dialog.run()
        dialog.destroy()

    def show_documentation(self, widget):
        """Show HyxTerminal documentation"""
        dialog = Gtk.Dialog(
            title="HyxTerminal Documentation",
            parent=self,
            flags=0
        )
        dialog.add_buttons(Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE)
        dialog.set_default_size(600, 500)
        
        box = dialog.get_content_area()
        box.set_spacing(6)
        box.set_margin_start(10)
        box.set_margin_end(10)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        
        # Use a notebook to organize documentation sections
        notebook = Gtk.Notebook()
        box.pack_start(notebook, True, True, 0)
        
        # Overview tab
        overview_scroll = Gtk.ScrolledWindow()
        overview_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        
        overview_view = Gtk.TextView()
        overview_view.set_wrap_mode(Gtk.WrapMode.WORD)
        overview_view.set_editable(False)
        overview_view.set_cursor_visible(False)
        overview_buffer = overview_view.get_buffer()
        overview_buffer.set_text(
            "HyxTerminal - Modern Terminal Emulator\n\n"
            "HyxTerminal is a feature-rich terminal emulator designed to enhance productivity with "
            "unique features not commonly found in other terminal emulators.\n\n"
            "Key Features:\n"
            "• Multiple terminal layouts (single, horizontal split, vertical split, quad)\n"
            "• Smart command completion with hints displayed directly in the terminal\n"
            "• Customizable themes and appearance\n"
            "• Tabbed interface with renaming support (double-click tab to rename)\n"
            "• Plugin support for extended functionality\n\n"
            "This documentation provides an overview of the application's capabilities and "
            "instructions for customization."
        )
        
        overview_scroll.add(overview_view)
        notebook.append_page(overview_scroll, Gtk.Label(label="Overview"))
        
        # Features tab
        features_scroll = Gtk.ScrolledWindow()
        features_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        
        features_view = Gtk.TextView()
        features_view.set_wrap_mode(Gtk.WrapMode.WORD)
        features_view.set_editable(False)
        features_view.set_cursor_visible(False)
        features_buffer = features_view.get_buffer()
        features_buffer.set_text(
            "Terminal Layouts\n\n"
            "HyxTerminal supports multiple terminal layouts in each tab:\n"
            "• Single terminal (default)\n"
            "• Horizontal split (two terminals side by side)\n"
            "• Vertical split (two terminals stacked)\n"
            "• Quad split (four terminals in a grid)\n"
            "• Custom layouts (with row and column configuration)\n\n"
            
            "Smart Command Completion\n\n"
            "As you type commands in the terminal, HyxTerminal displays completion suggestions "
            "directly in the terminal with a subtle hint. Press Tab to accept the suggestion.\n\n"
            
            "Themes and Customization\n\n"
            "HyxTerminal offers several built-in themes and allows for customizing colors, font, "
            "opacity, and other visual elements through the Preferences dialog.\n\n"
            
            "Plugins\n\n"
            "Extend functionality with plugins accessible from the Plugins menu."
        )
        
        features_scroll.add(features_view)
        notebook.append_page(features_scroll, Gtk.Label(label="Features"))
        
        # Usage tab
        usage_scroll = Gtk.ScrolledWindow()
        usage_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        
        usage_view = Gtk.TextView()
        usage_view.set_wrap_mode(Gtk.WrapMode.WORD)
        usage_view.set_editable(False)
        usage_view.set_cursor_visible(False)
        usage_buffer = usage_view.get_buffer()
        usage_buffer.set_text(
            "Basic Usage\n\n"
            "• Create new tabs with File > New Tab or Ctrl+Shift+T\n"
            "• Close tabs with File > Close Tab or Ctrl+Shift+W\n"
            "• Switch between tabs with Ctrl+PgUp and Ctrl+PgDown\n"
            "• Rename a tab by double-clicking its label\n"
            "• Access the command palette with Ctrl+Shift+P\n\n"
            
            "Terminal Operations\n\n"
            "• Copy selected text with Ctrl+Shift+C\n"
            "• Paste clipboard content with Ctrl+Shift+V\n"
            "• Clear the terminal with Ctrl+Shift+X\n"
            "• Split the terminal horizontally or vertically from the Actions menu\n"
            "• Search in terminal output with Ctrl+Shift+F\n\n"
            
            "Appearance\n\n"
            "• Toggle fullscreen mode with F11\n"
            "• Toggle menubar visibility with F10\n"
            "• Adjust zoom with Ctrl++, Ctrl+-, and Ctrl+0\n"
            "• Change terminal colors and fonts in Preferences"
        )
        
        usage_scroll.add(usage_view)
        notebook.append_page(usage_scroll, Gtk.Label(label="Usage"))
        
        dialog.show_all()
        dialog.run()
        dialog.destroy()

    def show_keyboard_shortcuts(self, widget):
        """Show keyboard shortcuts dialog"""
        dialog = Gtk.Dialog(
            title="Keyboard Shortcuts",
            parent=self,
            flags=0
        )
        dialog.add_buttons(Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE)
        dialog.set_default_size(500, 400)
        
        box = dialog.get_content_area()
        box.set_spacing(6)
        box.set_margin_start(10)
        box.set_margin_end(10)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        
        # Create a notebook for organizing shortcuts
        notebook = Gtk.Notebook()
        box.pack_start(notebook, True, True, 0)
        
        # Define shortcut categories and their entries
        categories = {
            "General": [
                ("Ctrl+Shift+T", "New Tab"),
                ("Ctrl+Shift+W", "Close Tab"),
                ("Ctrl+PgUp", "Next Tab"),
                ("Ctrl+PgDown", "Previous Tab"),
                ("F10", "Toggle Menubar"),
                ("F11", "Toggle Fullscreen"),
                ("Ctrl+Q", "Quit Application")
            ],
            "Terminal": [
                ("Ctrl+Shift+C", "Copy Selection"),
                ("Ctrl+Shift+V", "Paste Clipboard"),
                ("Shift+Insert", "Paste Selection"),
                ("Ctrl+Shift+X", "Clear Terminal"),
                ("Ctrl++", "Zoom In"),
                ("Ctrl+-", "Zoom Out"),
                ("Ctrl+0", "Reset Zoom")
            ],
            "Plugins": [
                ("Ctrl+Shift+P", "Command Palette"),
                ("Ctrl+Shift+F", "Find in Terminal"),
                ("F1", "Show Documentation")
            ]
        }
        
        # Create a tab for each category
        for category, shortcuts in categories.items():
            grid = Gtk.Grid()
            grid.set_column_spacing(20)
            grid.set_row_spacing(6)
            grid.set_margin_start(12)
            grid.set_margin_end(12)
            grid.set_margin_top(12)
            grid.set_margin_bottom(12)
            
            # Add shortcuts to grid
            for i, (key, action) in enumerate(shortcuts):
                key_label = Gtk.Label()
                key_label.set_markup(f"<b>{key}</b>")
                key_label.set_halign(Gtk.Align.START)
                
                action_label = Gtk.Label(label=action)
                action_label.set_halign(Gtk.Align.START)
                
                grid.attach(key_label, 0, i, 1, 1)
                grid.attach(action_label, 1, i, 1, 1)
            
            # Add grid to notebook
            label = Gtk.Label(label=category)
            notebook.append_page(grid, label)
        
        dialog.show_all()
        dialog.run()
        dialog.destroy()

    def show_about_dialog(self, widget):
        """Show about dialog with application information"""
        about_dialog = Gtk.AboutDialog()
        about_dialog.set_transient_for(self)
        about_dialog.set_modal(True)
        
        about_dialog.set_program_name("HyxTerminal")
        about_dialog.set_version("1.0.0")
        about_dialog.set_copyright("© 2023 HyxTerminal Project")
        about_dialog.set_comments("A modern terminal emulator with unique features")
        about_dialog.set_website("https://github.com/hyxterminal")
        about_dialog.set_website_label("HyxTerminal on GitHub")
        about_dialog.set_authors(["HyxTerminal Team"])
        about_dialog.set_license_type(Gtk.License.GPL_3_0)
        
        # Set logo if available
        try:
            logo = Gtk.Image.new_from_icon_name("utilities-terminal", Gtk.IconSize.DIALOG)
            about_dialog.set_logo(logo.get_pixbuf())
        except:
            pass
            
        about_dialog.run()
        about_dialog.destroy()

    def show_command_palette(self, widget):
        """Show command palette with searchable commands"""
        dialog = Gtk.Dialog(
            title="Command Palette",
            parent=self,
            flags=0
        )
        dialog.set_default_size(400, 300)
        
        box = dialog.get_content_area()
        box.set_spacing(6)
        box.set_margin_start(10)
        box.set_margin_end(10)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        
        # Create search entry
        search_entry = Gtk.SearchEntry()
        search_entry.set_placeholder_text("Type to search commands...")
        box.pack_start(search_entry, False, False, 0)
        
        # Create a scrolled window for the list
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        box.pack_start(scrolled, True, True, 0)
        
        # Create a list store for commands
        # Columns: Category, Command, Icon
        store = Gtk.ListStore(str, str, str)
        
        # Add commands to the list store
        commands = [
            ("Tabs", "New Tab", "tab-new"),
            ("Tabs", "Close Tab", "window-close"),
            ("Terminal", "Split Horizontally", "object-flip-horizontal"),
            ("Terminal", "Split Vertically", "object-flip-vertical"),
            ("Terminal", "Copy Selection", "edit-copy"),
            ("Terminal", "Paste Clipboard", "edit-paste"),
            ("Terminal", "Clear Terminal", "edit-clear-all"),
            ("View", "Toggle Fullscreen", "view-fullscreen"),
            ("View", "Toggle Menubar", "show-menu"),
            ("View", "Zoom In", "zoom-in"),
            ("View", "Zoom Out", "zoom-out"),
            ("View", "Reset Zoom", "zoom-original")
        ]
        
        for category, cmd, icon in commands:
            store.append([category, cmd, icon])
        
        # Create a tree view
        treeview = Gtk.TreeView(model=store)
        treeview.set_headers_visible(False)
        scrolled.add(treeview)
        
        # Add columns
        icon_renderer = Gtk.CellRendererPixbuf()
        icon_column = Gtk.TreeViewColumn("", icon_renderer, icon_name=2)
        treeview.append_column(icon_column)
        
        text_renderer = Gtk.CellRendererText()
        text_column = Gtk.TreeViewColumn("Command", text_renderer, text=1)
        treeview.append_column(text_column)
        
        # Handle selection
        selection = treeview.get_selection()
        
        # Function to execute when a command is selected
        def on_command_activated(treeview, path, column):
            model = treeview.get_model()
            iter = model.get_iter(path)
            category = model.get_value(iter, 0)
            command = model.get_value(iter, 1)
            
            # Execute the selected command
            if command == "New Tab":
                self.new_tab()
            elif command == "Close Tab":
                self.close_current_tab(None)
            elif command == "Split Horizontally":
                self.split_horizontal(None)
            elif command == "Split Vertically":
                self.split_vertical(None)
            elif command == "Copy Selection":
                self.copy_selection(None)
            elif command == "Paste Clipboard":
                self.paste_clipboard(None)
            elif command == "Clear Terminal":
                self.clear_active_terminal(None)
            elif command == "Toggle Fullscreen":
                self.toggle_fullscreen(None)
            elif command == "Toggle Menubar":
                self.toggle_menubar(None)
            elif command == "Zoom In":
                self.zoom_in(None)
            elif command == "Zoom Out":
                self.zoom_out(None)
            elif command == "Reset Zoom":
                self.zoom_reset(None)
                
            dialog.destroy()
        
        treeview.connect("row-activated", on_command_activated)
        
        # Handle search
        def filter_commands(entry):
            search_text = entry.get_text().lower()
            store.clear()
            
            for category, cmd, icon in commands:
                if search_text in cmd.lower() or search_text in category.lower():
                    store.append([category, cmd, icon])
        
        search_entry.connect("search-changed", filter_commands)
        
        dialog.show_all()
        search_entry.grab_focus()
        dialog.run()
        dialog.destroy()

if __name__ == "__main__":
    win = HyxTerminal()
    win.connect("delete-event", Gtk.main_quit)
    win.show_all()
    try:
        Gtk.main()
    except KeyboardInterrupt:
        win.destroy()
