import gi
import os
import subprocess
gi.require_version('Gtk', '3.0')
gi.require_version('Vte', '2.91')
from gi.repository import Gtk, Gdk, Vte, GLib
import modules.config as config

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
        
        # Command hint support
        self.hint_timeout = None
        self.current_command = ""
        self.current_hint = ""
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
        bg = config.parse_color(bg_color, opacity)
        fg = config.parse_color(fg_color)
        self.terminal.set_colors(fg, bg, [])

    def on_terminal_exit(self, terminal, status):
        notebook = self.get_parent()
        if notebook and notebook.get_n_pages() > 1:
            notebook.remove_page(notebook.page_num(self))
        else:
            self.parent_window.destroy()

    def on_key_press(self, widget, event):
        """Handle key events for command hints"""
        keyval = event.keyval
        if keyval == Gdk.KEY_Tab:
            # Instead of clearing hint with terminal.feed, simply reset the hint state
            if self.hint_timeout:
                GLib.source_remove(self.hint_timeout)
                self.hint_timeout = None
            self.current_hint = ""
            return False  # Let bash handle Tab completion
        elif keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            self.clear_hint()
            self.current_command = ""
        else:
            # Update current command and schedule hint check
            if keyval in range(32, 127):  # Printable characters
                self.current_command += chr(keyval)
                self.schedule_hint_check()
            elif keyval == Gdk.KEY_BackSpace and self.current_command:
                self.current_command = self.current_command[:-1]
                if self.current_command:
                    self.schedule_hint_check()
                else:
                    self.clear_hint()
        return False

    def schedule_hint_check(self):
        """Schedule a new hint check with proper cleanup"""
        if self.hint_timeout:
            GLib.source_remove(self.hint_timeout)
        self.hint_timeout = GLib.timeout_add(1000, self.check_command_completion)

    def clear_hint(self):
        """Safely clear current hint"""
        if self.hint_timeout:
            GLib.source_remove(self.hint_timeout)
            self.hint_timeout = None
        if self.current_hint:
            self.terminal.feed(f"\033[{len(self.current_hint)}D\033[K".encode())
            self.current_hint = ""

    def display_hint(self, hint_text):
        """Display hint directly in terminal"""
        if hint_text:
            sequence = f"\033[2;37m{hint_text}\033[0m"
            self.terminal.feed(sequence.encode())
            self.terminal.feed(f"\033[{len(hint_text)}D".encode())
            self.current_hint = hint_text

    def check_command_completion(self):
        """Check for command completion"""
        try:
            cmd = ["bash", "-c", f"compgen -c '{self.current_command}' | head -n 1"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            suggestion = result.stdout.strip()

            if suggestion and suggestion.startswith(self.current_command):
                completion = suggestion[len(self.current_command):]
                if completion:
                    self.display_hint(completion)

        except Exception as e:
            print(f"Error checking completion: {e}")
            self.clear_hint()

        self.hint_timeout = None
        return False
