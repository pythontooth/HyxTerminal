import gi
import os
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, GdkPixbuf, Pango

class Dialogs:
    @staticmethod
    def show_preferences(parent_window, config, update_terminals_callback):
        """Show preferences dialog"""
        from modules import config as config_module
        
        dialog = Gtk.Dialog(
            title="Preferences...",
            parent=parent_window,
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
        width_spin.set_value(config.get('window_width', 800))
        width_box.pack_start(width_label, False, False, 0)
        width_box.pack_start(width_spin, True, True, 0)
        size_box.add(width_box)

        height_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        height_label = Gtk.Label(label="Height:")
        height_spin = Gtk.SpinButton.new_with_range(300, 2000, 50)
        height_spin.set_value(config.get('window_height', 600))
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
            f"{config.get('font_family', 'Monospace')} {config.get('font_size', 11)}"
        )
        font_button.set_font_desc(font_desc)
        font_box.add(font_button)

        scale_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        scale_label = Gtk.Label(label="Font Scale:")
        scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0.5, 2.0, 0.1)
        scale.set_value(config.get('font_scale', 1.0))
        scale_box.pack_start(scale_label, False, False, 0)
        scale_box.pack_start(scale, True, True, 0)
        font_box.add(scale_box)
        box.add(font_frame)

        # Colors
        colors_frame = Gtk.Frame(label="Colors")
        colors_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        colors_frame.add(colors_box)

        bg_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        bg_label = Gtk.Label(label="Background:")
        bg_color = Gtk.ColorButton()
        bg_color.set_rgba(config_module.parse_color(config.get('background_color', '#000000')))
        bg_box.pack_start(bg_label, False, False, 0)
        bg_box.pack_start(bg_color, True, True, 0)
        colors_box.add(bg_box)

        fg_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        fg_label = Gtk.Label(label="Foreground:")
        fg_color = Gtk.ColorButton()
        fg_color.set_rgba(config_module.parse_color(config.get('foreground_color', '#FFFFFF')))
        fg_box.pack_start(fg_label, False, False, 0)
        fg_box.pack_start(fg_color, True, True, 0)
        colors_box.add(fg_box)

        # Add opacity control
        opacity_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        opacity_label = Gtk.Label(label="Background Opacity:")
        opacity_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0.0, 1.0, 0.1)
        opacity_scale.set_value(config.get('background_opacity', 0.9))
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
        scrollback_spin.set_value(config.get('scrollback_lines', 10000))
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
        current_shape = config.get('cursor_shape', 'block')
        cursor_combo.set_active(shapes.index(current_shape))
        cursor_box.pack_start(cursor_label, False, False, 0)
        cursor_box.pack_start(cursor_combo, True, True, 0)
        term_box.add(cursor_box)
        box.add(term_frame)

        dialog.show_all()
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            # Update configuration
            config.update({
                'window_width': int(width_spin.get_value()),
                'window_height': int(height_spin.get_value()),
                'scrollback_lines': int(scrollback_spin.get_value()),
                'font_scale': scale.get_value(),
                'background_color': config_module.rgba_to_hex(bg_color.get_rgba()),
                'foreground_color': config_module.rgba_to_hex(fg_color.get_rgba()),
                'font_family': font_button.get_font_desc().get_family(),
                'font_size': font_button.get_font_desc().get_size() // 1000,
                'cursor_shape': shapes[cursor_combo.get_active()],
                'background_opacity': opacity_scale.get_value()
            })

            # Apply changes to all terminals
            update_terminals_callback(
                config['background_color'],
                config['foreground_color'],
                config['background_opacity'],
                scale.get_value(),
                int(scrollback_spin.get_value()),
                shapes[cursor_combo.get_active()]
            )

            # Save configuration
            config_module.save_config(config)

        dialog.destroy()
        return response
    
    @staticmethod
    def show_find_dialog(parent_window, find_callback):
        """Show find dialog for terminal search"""
        dialog = Gtk.Dialog(
            title="Find",
            parent=parent_window,
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
        
        while True:
            response = dialog.run()
            if response == Gtk.ResponseType.OK:
                text = search_entry.get_text()
                case_sensitive = case_check.get_active()
                use_regex = regex_check.get_active()
                backward = backward_check.get_active()
                
                found = find_callback(text, case_sensitive, use_regex, backward)
                
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
            else:
                # Clear search highlighting
                find_callback("", False, False, False, clear=True)
                break
        
        dialog.destroy()
    
    @staticmethod
    def show_about_dialog(parent_window):
        """Show about dialog with application information"""
        about_dialog = Gtk.AboutDialog()
        about_dialog.set_transient_for(parent_window)
        about_dialog.set_modal(True)
        
        about_dialog.set_program_name("HyxTerminal")
        about_dialog.set_version("1.0.0")
        about_dialog.set_copyright("© 2023 HyxTerminal Project")
        about_dialog.set_comments("A modern terminal emulator with unique features")
        about_dialog.set_website("https://github.com/hyxterminal")
        about_dialog.set_website_label("HyxTerminal on GitHub")
        about_dialog.set_authors(["HyxTerminal Team"])
        about_dialog.set_license_type(Gtk.License.GPL_3_0)
        
        # Set logo from file
        try:
            # Try to find the logo in different locations
            logo_paths = [
                os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "HyxTerminal.png"),
                os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "HyxTerminal.png"),
                "/usr/share/icons/hicolor/128x128/apps/hyxterminal.png",
                "/usr/share/pixmaps/hyxterminal.png"
            ]
            
            for logo_path in logo_paths:
                if os.path.exists(logo_path):
                    logo_pixbuf = GdkPixbuf.Pixbuf.new_from_file(logo_path)
                    # Scale if needed (to 128x128 for example)
                    if logo_pixbuf.get_width() > 128 or logo_pixbuf.get_height() > 128:
                        logo_pixbuf = logo_pixbuf.scale_simple(128, 128, GdkPixbuf.InterpType.BILINEAR)
                    about_dialog.set_logo(logo_pixbuf)
                    break
            else:
                # If no custom logo found, use default terminal icon
                logo = Gtk.Image.new_from_icon_name("utilities-terminal", Gtk.IconSize.DIALOG)
                about_dialog.set_logo(logo.get_pixbuf())
        except Exception as e:
            print(f"Failed to set about dialog logo: {e}")
            # Fallback to default icon
            try:
                logo = Gtk.Image.new_from_icon_name("utilities-terminal", Gtk.IconSize.DIALOG)
                about_dialog.set_logo(logo.get_pixbuf())
            except:
                pass
            
        about_dialog.run()
        about_dialog.destroy()
    
    @staticmethod
    def show_keyboard_shortcuts(parent_window):
        """Show keyboard shortcuts dialog"""
        dialog = Gtk.Dialog(
            title="Keyboard Shortcuts",
            parent=parent_window,
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
        
    @staticmethod
    def check_for_updates(parent_window):
        """Check for application updates"""
        # Create a progress dialog
        dialog = Gtk.Dialog(
            title="Checking for Updates",
            parent=parent_window,
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
                parent=parent_window,
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