import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

class Plugins:
    @staticmethod
    def show_plugin_browser(parent_window):
        """Show plugin browser dialog with available plugins"""
        dialog = Gtk.Dialog(
            title="Plugin Browser",
            parent=parent_window,
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
        renderer_toggle.connect("toggled", lambda cell, path: Plugins.on_plugin_toggled(cell, path, store, parent_window))
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
        
        details_label = Gtk.Label()
        details_label.set_markup("<i>Select a plugin to view details</i>")
        details_label.set_line_wrap(True)
        details_label.set_xalign(0)
        details_box.pack_start(details_label, False, False, 0)
        
        frame.add(details_box)
        box.pack_start(frame, False, False, 0)
        
        # Update details when selection changes
        selection = treeview.get_selection()
        selection.connect("changed", lambda sel: Plugins.on_plugin_selection_changed(sel, store, details_label))
        
        dialog.show_all()
        dialog.run()
        dialog.destroy()
    
    @staticmethod
    def on_plugin_toggled(cell, path, store, parent_window):
        """Toggle plugin enabled state"""
        store[path][2] = not store[path][2]
        plugin_name = store[path][0]
        enabled = store[path][2]
        
        # If this is the smart completion plugin, update the terminal tabs
        if hasattr(parent_window, 'notebook') and plugin_name == "Smart Completion":
            for i in range(parent_window.notebook.get_n_pages()):
                tab = parent_window.notebook.get_nth_page(i)
                for terminal in tab.terminals:
                    # Enable or disable command completion
                    if hasattr(tab, 'hint_timeouts'):
                        if not enabled and tab.hint_timeouts.get(terminal):
                            tab.clear_hint(terminal)
    
    @staticmethod
    def on_plugin_selection_changed(selection, store, details_label):
        """Update plugin details when selection changes"""
        model, treeiter = selection.get_selected()
        if treeiter is not None:
            name = model[treeiter][0]
            desc = model[treeiter][1]
            version = model[treeiter][3]
            author = model[treeiter][4]
            
            details = f"<b>{name}</b> (v{version})\n\n{desc}\n\nAuthor: {author}"
            details_label.set_markup(details)
    
    @staticmethod
    def toggle_smart_completion(widget, parent_window):
        """Toggle smart command completion in all terminals"""
        enabled = widget.get_active()
        
        # Update all terminal tabs
        if hasattr(parent_window, 'notebook'):
            for i in range(parent_window.notebook.get_n_pages()):
                tab = parent_window.notebook.get_nth_page(i)
                for terminal in tab.terminals:
                    # Clear current hints if disabling
                    if not enabled and hasattr(tab, 'hint_timeouts'):
                        if tab.hint_timeouts.get(terminal):
                            tab.clear_hint(terminal)
    
    @staticmethod
    def show_clipboard_manager(parent_window):
        """Show clipboard manager with history"""
        dialog = Gtk.Dialog(
            title="Clipboard Manager",
            parent=parent_window,
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
                terminal = parent_window.get_current_terminal()
                if terminal:
                    terminal.feed_child((text + "\n").encode())
                dialog.destroy()
        
        paste_button.connect("clicked", on_paste_clicked)
        
        # Handle double-click on item
        def on_row_activated(view, path, column):
            treeiter = store.get_iter(path)
            text = store[treeiter][0]
            terminal = parent_window.get_current_terminal()
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
    
    @staticmethod
    def show_plugin_settings(parent_window):
        """Show settings for installed plugins"""
        dialog = Gtk.Dialog(
            title="Plugin Settings",
            parent=parent_window,
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
        
    @staticmethod
    def show_command_palette(parent_window):
        """Show command palette with searchable commands"""
        dialog = Gtk.Dialog(
            title="Command Palette",
            parent=parent_window,
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
                parent_window.new_tab()
            elif command == "Close Tab":
                parent_window.close_current_tab(None)
            elif command == "Split Horizontally":
                parent_window.split_horizontal(None)
            elif command == "Split Vertically":
                parent_window.split_vertical(None)
            elif command == "Copy Selection":
                parent_window.copy_selection(None)
            elif command == "Paste Clipboard":
                parent_window.paste_clipboard(None)
            elif command == "Clear Terminal":
                parent_window.clear_active_terminal(None)
            elif command == "Toggle Fullscreen":
                parent_window.toggle_fullscreen(None)
            elif command == "Toggle Menubar":
                parent_window.toggle_menubar(None)
            elif command == "Zoom In":
                parent_window.zoom_in(None)
            elif command == "Zoom Out":
                parent_window.zoom_out(None)
            elif command == "Reset Zoom":
                parent_window.zoom_reset(None)
                
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
        
    @staticmethod
    def show_documentation(parent_window):
        """Show HyxTerminal documentation"""
        dialog = Gtk.Dialog(
            title="HyxTerminal Documentation",
            parent=parent_window,
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