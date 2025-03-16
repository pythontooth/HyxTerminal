#!/usr/bin/env python3

import gi
import os
import json
from pathlib import Path
import subprocess
gi.require_version('Gtk', '3.0')
gi.require_version('Vte', '2.91')
from gi.repository import Gtk, Gdk, Vte, GLib, Pango, GdkPixbuf

class TerminalTab(Gtk.Box):
    def __init__(self, parent_window):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL)
        self.parent_window = parent_window
        
        # Create terminal
        self.terminal = Vte.Terminal()
        self.terminal.connect("child-exited", self.on_terminal_exit)
        self.terminal.set_scrollback_lines(parent_window.config.get('scrollback_lines', 10000))
        self.terminal.set_font_scale(parent_window.config.get('font_scale', 1.0))
        self.terminal.set_cursor_shape(self.get_cursor_shape(
            parent_window.config.get('cursor_shape', 'block')
        ))
        
        self.pack_start(self.terminal, True, True, 0)
        
        # Set up initial colors
        self.update_colors(
            parent_window.config.get('background_color', '#000000'),
            parent_window.config.get('foreground_color', '#FFFFFF'),
            parent_window.config.get('background_opacity', 0.9)
        )
        
        # Simple hint support
        self.hint_text = ""
        self.hint_timeout = None
        self.terminal.connect('contents-changed', self.on_contents_changed)
        self.terminal.connect('key-press-event', self.on_key_press)
        
        # Start shell with proper flags
        self.terminal.spawn_async(
            Vte.PtyFlags.DEFAULT,
            os.environ['HOME'],
            ["/bin/bash"],
            [],
            GLib.SpawnFlags.DEFAULT,  # Changed from DO_NOT_REAP_CHILD
            None,
            None,
            -1,
            None,
            None
        )

    def get_cursor_shape(self, shape_name):
        """Convert cursor shape name to VTE constant"""
        shapes = {
            'block': Vte.CursorShape.BLOCK,
            'ibeam': Vte.CursorShape.IBEAM,
            'underline': Vte.CursorShape.UNDERLINE
        }
        return shapes.get(shape_name, Vte.CursorShape.BLOCK)

    def update_cursor(self, shape_name):
        """Update terminal cursor shape"""
        self.terminal.set_cursor_shape(self.get_cursor_shape(shape_name))

    def update_colors(self, bg_color, fg_color, opacity):
        """Update terminal colors and opacity"""
        bg = self.parent_window.parse_color(bg_color, opacity)
        fg = self.parent_window.parse_color(fg_color)
        self.terminal.set_colors(fg, bg, [])

    def on_terminal_resize(self, widget, allocation):
        """Handle terminal resize"""
        pass

    def on_terminal_exit(self, terminal, status):
        notebook = self.get_parent()
        if notebook and notebook.get_n_pages() > 1:
            notebook.remove_page(notebook.page_num(self))
        else:
            self.parent_window.destroy()

    def on_key_press(self, widget, event):
        """Handle key events for visual hints"""
        keyval = event.keyval
        if keyval in (Gdk.KEY_Tab, Gdk.KEY_Return, Gdk.KEY_space):
            self.clear_hint()
            return False
        return False

    def on_contents_changed(self, terminal):
        """Schedule hint check when content changes"""
        if self.hint_timeout:
            GLib.source_remove(self.hint_timeout)
        self.hint_timeout = GLib.timeout_add(500, self.check_hint)

    def clear_hint(self):
        """Clear any visible hint"""
        if self.hint_text:
            self.terminal.feed(f"\033[{len(self.hint_text)}D\033[K".encode())
            self.hint_text = ""
        if self.hint_timeout:
            GLib.source_remove(self.hint_timeout)
            self.hint_timeout = None

    def check_hint(self):
        """Show completion hint for current text"""
        try:
            # Get current command using newer VTE method
            col = self.terminal.get_cursor_position()[1]
            row = self.terminal.get_cursor_position()[0]
            text = self.terminal.get_text(lambda *a: False, None)[0]  # Get text without attributes
            
            # Get current line
            lines = text.splitlines()
            if not lines or row >= len(lines):
                return False
            
            current_line = lines[row]
            if not current_line or col > len(current_line):
                return False

            # Get current word
            words = current_line[:col].split()
            if not words:
                return False
            current_word = words[-1]

            if current_word:
                # Get completion suggestion
                cmd = ["bash", "-c", f"compgen -c '{current_word}' | head -n 1"]
                result = subprocess.run(cmd, capture_output=True, text=True)
                suggestion = result.stdout.strip()

                # Show hint if valid
                if suggestion and suggestion.startswith(current_word) and suggestion != current_word:
                    hint = suggestion[len(current_word):]
                    self.clear_hint()
                    self.hint_text = hint
                    self.terminal.feed(f"\033[2;37m{hint}\033[0m".encode())
                    self.terminal.feed(f"\033[{len(hint)}D".encode())
        except Exception as e:
            print(f"Hint error: {e}")
            self.clear_hint()

        self.hint_timeout = None
        return False

class TabLabel(Gtk.Box):
    def __init__(self, title, tab, notebook):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.notebook = notebook
        self.tab = tab
        self.is_editing = False
        
        # Create label container (for easier widget swapping)
        self.label_container = Gtk.Box()
        
        # Create label
        self.label = Gtk.Label(label=title)
        self.label_container.add(self.label)
        
        # Create close button
        close_button = Gtk.Button()
        close_button.set_relief(Gtk.ReliefStyle.NONE)
        close_button.set_focus_on_click(False)
        close_button.add(Gtk.Image.new_from_icon_name("window-close", Gtk.IconSize.MENU))
        close_button.connect('clicked', self.on_close_clicked)
        
        # Add double-click detection to the label container
        event_box = Gtk.EventBox()
        event_box.add(self.label_container)
        event_box.connect('button-press-event', self.on_tab_clicked)
        event_box.set_above_child(False)
        
        # Pack widgets
        self.pack_start(event_box, True, True, 0)
        self.pack_start(close_button, False, False, 0)
        self.show_all()

    def on_close_clicked(self, button):
        if not self.is_editing:  # Prevent closing while editing
            page_num = self.notebook.page_num(self.tab)
            if page_num != -1:
                self.notebook.remove_page(page_num)

    def on_tab_clicked(self, widget, event):
        if event.type == Gdk.EventType._2BUTTON_PRESS and not self.is_editing:
            self.start_editing()
            return True
        return False

    def start_editing(self):
        self.is_editing = True
        # Create entry widget
        entry = Gtk.Entry()
        entry.set_text(self.label.get_text())
        entry.connect('activate', self.finish_editing)
        entry.connect('focus-out-event', self.finish_editing)
        entry.connect('key-press-event', self.on_entry_key_press)
        
        # Safely swap widgets
        self.label.hide()
        self.label_container.add(entry)
        entry.show()
        entry.grab_focus()

    def finish_editing(self, widget, event=None):
        if not self.is_editing:
            return False
            
        try:
            new_text = widget.get_text().strip()
            if new_text:
                self.label.set_text(new_text)
            
            # Safely restore label
            widget.hide()
            self.label_container.remove(widget)
            self.label.show()
            
        except Exception as e:
            print(f"Error while finishing edit: {e}")
        
        finally:
            self.is_editing = False
            
        return False

    def on_entry_key_press(self, widget, event):
        # Handle Escape key to cancel editing
        if event.keyval == Gdk.KEY_Escape:
            self.is_editing = False
            widget.hide()
            self.label_container.remove(widget)
            self.label.show()
            return True
        return False

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
        self.config = self.load_config()
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

        new_tab = Gtk.MenuItem.new_with_label("New Tab")
        new_tab.connect("activate", self.new_tab)
        file_submenu.append(new_tab)

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

    def load_config(self):
        config_path = Path.home() / '.config' / 'hyxterminal' / 'config.json'
        default_config = {
            'window_width': 800,
            'window_height': 600,
            'scrollback_lines': 10000,
            'font_scale': 1.0,
            'background_color': '#000000',
            'foreground_color': '#FFFFFF',
            'background_opacity': 0.9,
            'font_family': 'Monospace',
            'font_size': 11,
            'cursor_shape': 'block',
            'cursor_blink_mode': 'system'
        }
        
        if config_path.exists():
            try:
                with open(config_path) as f:
                    return {**default_config, **json.load(f)}
            except Exception:
                return default_config
        return default_config

    def parse_color(self, color_str, opacity=1.0):
        """Parse hex color string to Gdk.RGBA with optional opacity"""
        if color_str.startswith('#'):
            r = int(color_str[1:3], 16) / 255.0
            g = int(color_str[3:5], 16) / 255.0
            b = int(color_str[5:7], 16) / 255.0
            color = Gdk.RGBA()
            color.red = r
            color.green = g
            color.blue = b
            color.alpha = opacity
            return color
        return None

    def get_current_terminal(self):
        """Get the terminal from the current tab"""
        current_page = self.notebook.get_current_page()
        if current_page != -1:
            return self.notebook.get_nth_page(current_page).terminal
        return None

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
        bg_color.set_rgba(self.parse_color(self.config.get('background_color', '#000000')))
        bg_box.pack_start(bg_label, False, False, 0)
        bg_box.pack_start(bg_color, True, True, 0)
        colors_box.add(bg_box)

        fg_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        fg_label = Gtk.Label(label="Foreground:")
        fg_color = Gtk.ColorButton()
        fg_color.set_rgba(self.parse_color(self.config.get('foreground_color', '#FFFFFF')))
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
                'background_color': self.rgba_to_hex(bg_color.get_rgba()),
                'foreground_color': self.rgba_to_hex(fg_color.get_rgba()),
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

    def new_tab(self, widget=None):
        """Add a new terminal tab"""
        tab = TerminalTab(self)
        label = TabLabel(f"Terminal {self.notebook.get_n_pages() + 1}", tab, self.notebook)
        self.notebook.append_page(tab, label)
        self.notebook.set_tab_reorderable(tab, True)  # Allow tab reordering
        self.notebook.set_current_page(-1)
        tab.show_all()

    def on_tab_added(self, notebook, child, page_num):
        """Show tabs bar when there's more than one tab"""
        self.notebook.set_show_tabs(notebook.get_n_pages() > 1)

    def on_tab_removed(self, notebook, child, page_num):
        """Hide tabs bar when only one tab remains"""
        self.notebook.set_show_tabs(notebook.get_n_pages() > 1)

    def on_terminal_exit(self, terminal, status):
        """Handle terminal exit properly"""
        if self.get_property('is-active'):
            self.destroy()
        else:
            Gtk.main_quit()

    def on_key_press(self, widget, event):
        modifiers = event.state & Gtk.accelerator_get_default_mod_mask()
        
        # Ctrl+Shift+T - New Tab
        if modifiers == (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK) and event.keyval == Gdk.KEY_T:
            self.new_tab()
            return True
            
        # Get current terminal
        current_page = self.notebook.get_current_page()
        if current_page != -1:
            current_terminal = self.notebook.get_nth_page(current_page).terminal
            
            # Ctrl+Shift+C - Copy
            if modifiers == (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK) and event.keyval == Gdk.KEY_C:
                current_terminal.copy_clipboard()
                return True
                
            # Ctrl+Shift+V - Paste
            if modifiers == (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK) and event.keyval == Gdk.KEY_V:
                current_terminal.paste_clipboard()
                return True

        return False

if __name__ == "__main__":
    win = HyxTerminal()
    win.connect("delete-event", Gtk.main_quit)
    win.show_all()
    try:
        Gtk.main()
    except KeyboardInterrupt:
        win.destroy()
