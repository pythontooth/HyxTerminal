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
        menubar.append(view_menu)

        # Plugins menu
        plugins_menu = Gtk.MenuItem.new_with_label("Plugins")
        plugins_submenu = Gtk.Menu()
        plugins_menu.set_submenu(plugins_submenu)
        menubar.append(plugins_menu)

        # Help menu
        help_menu = Gtk.MenuItem.new_with_label("Help")
        help_submenu = Gtk.Menu()
        help_menu.set_submenu(help_submenu)
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

if __name__ == "__main__":
    win = HyxTerminal()
    win.connect("delete-event", Gtk.main_quit)
    win.show_all()
    try:
        Gtk.main()
    except KeyboardInterrupt:
        win.destroy()
