#!/usr/bin/env python3

import gi
import os
import json
from pathlib import Path
gi.require_version('Gtk', '3.0')
gi.require_version('Vte', '2.91')
from gi.repository import Gtk, Gdk, Vte, GLib, Pango

class HyxTerminal(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="HyxTerminal")
        
        # Load config
        self.config = self.load_config()
        self.set_default_size(
            self.config.get('window_width', 800),
            self.config.get('window_height', 600)
        )

        # Create main vertical box
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(vbox)

        # Create menubar
        menubar = Gtk.MenuBar()
        vbox.pack_start(menubar, False, False, 0)

        # File menu
        file_menu = Gtk.MenuItem.new_with_label("File")
        file_submenu = Gtk.Menu()
        file_menu.set_submenu(file_submenu)

        new_window = Gtk.MenuItem.new_with_label("New Window")
        new_window.connect("activate", self.new_window)
        file_submenu.append(new_window)

        quit_item = Gtk.MenuItem.new_with_label("Quit")
        quit_item.connect("activate", Gtk.main_quit)
        file_submenu.append(quit_item)
        menubar.append(file_menu)

        # Edit menu
        edit_menu = Gtk.MenuItem.new_with_label("Edit")
        edit_submenu = Gtk.Menu()
        edit_menu.set_submenu(edit_submenu)

        preferences = Gtk.MenuItem.new_with_label("Preferences")
        preferences.connect("activate", self.show_preferences)
        edit_submenu.append(preferences)
        menubar.append(edit_menu)

        # Create terminal
        self.terminal = Vte.Terminal()
        self.terminal.set_scrollback_lines(self.config.get('scrollback_lines', 10000))
        self.terminal.set_font_scale(self.config.get('font_scale', 1.0))
        
        # Set colors from config
        bg_color = self.parse_color(self.config.get('background_color', '#000000'))
        fg_color = self.parse_color(self.config.get('foreground_color', '#FFFFFF'))
        self.terminal.set_color_background(bg_color)
        self.terminal.set_color_foreground(fg_color)

        # Add terminal to window
        vbox.pack_start(self.terminal, True, True, 0)

        # Start shell
        self.terminal.spawn_sync(
            Vte.PtyFlags.DEFAULT,
            os.environ['HOME'],
            ["/bin/bash"],
            [],
            GLib.SpawnFlags.DO_NOT_REAP_CHILD,
            None,
            None,
        )

        # Key bindings
        self.connect("key-press-event", self.on_key_press)

    def load_config(self):
        config_path = Path.home() / '.config' / 'hyxterminal' / 'config.json'
        default_config = {
            'window_width': 800,
            'window_height': 600,
            'scrollback_lines': 10000,
            'font_scale': 1.0,
            'background_color': '#000000',
            'foreground_color': '#FFFFFF'
        }
        
        if config_path.exists():
            try:
                with open(config_path) as f:
                    return {**default_config, **json.load(f)}
            except Exception:
                return default_config
        return default_config

    def parse_color(self, color_str):
        if color_str.startswith('#'):
            r = int(color_str[1:3], 16) / 255.0
            g = int(color_str[3:5], 16) / 255.0
            b = int(color_str[5:7], 16) / 255.0
            return Gdk.RGBA(r, g, b, 1)
        return Gdk.RGBA(0, 0, 0, 1)

    def show_preferences(self, widget):
        dialog = Gtk.Dialog(
            title="Preferences",
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
        scale.set_value(self.terminal.get_font_scale())
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
        bg_color = Gtk.ColorButton.new_with_rgba(
            self.parse_color(self.config.get('background_color', '#000000'))
        )
        bg_box.pack_start(bg_label, False, False, 0)
        bg_box.pack_start(bg_color, True, True, 0)
        colors_box.add(bg_box)

        fg_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        fg_label = Gtk.Label(label="Foreground:")
        fg_color = Gtk.ColorButton.new_with_rgba(
            self.parse_color(self.config.get('foreground_color', '#FFFFFF'))
        )
        fg_box.pack_start(fg_label, False, False, 0)
        fg_box.pack_start(fg_color, True, True, 0)
        colors_box.add(fg_box)
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
        for shape in ['block', 'ibeam', 'underline']:
            cursor_combo.append_text(shape)
        cursor_combo.set_active(0)  # Set to current value
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
                'background_color': self.rgba_to_hex(bg_color.get_rgba()),
                'foreground_color': self.rgba_to_hex(fg_color.get_rgba()),
                'font_family': font_button.get_font_desc().get_family(),
                'font_size': font_button.get_font_desc().get_size() // 1000,
                'cursor_shape': cursor_combo.get_active_text()
            })

            # Apply changes
            self.terminal.set_font_scale(scale.get_value())
            self.terminal.set_color_background(bg_color.get_rgba())
            self.terminal.set_color_foreground(fg_color.get_rgba())
            self.terminal.set_scrollback_lines(int(scrollback_spin.get_value()))
            self.resize(int(width_spin.get_value()), int(height_spin.get_value()))
            
            # Save configuration
            self.save_config()

        dialog.destroy()

    def rgba_to_hex(self, rgba):
        return '#{:02x}{:02x}{:02x}'.format(
            int(rgba.red * 255),
            int(rgba.green * 255),
            int(rgba.blue * 255)
        )

    def save_config(self):
        config_path = Path.home() / '.config' / 'hyxterminal' / 'config.json'
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(self.config, f, indent=4)

    def new_window(self, widget):
        window = HyxTerminal()
        window.show_all()

    def on_terminal_exit(self, widget, status):
        Gtk.main_quit()

    def on_key_press(self, widget, event):
        modifiers = event.state & Gtk.accelerator_get_default_mod_mask()
        
        # Ctrl+Shift+C - Copy
        if modifiers == (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK) and event.keyval == Gdk.KEY_C:
            self.terminal.copy_clipboard()
            return True
            
        # Ctrl+Shift+V - Paste
        if modifiers == (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK) and event.keyval == Gdk.KEY_V:
            self.terminal.paste_clipboard()
            return True

        return False

if __name__ == "__main__":
    win = HyxTerminal()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
