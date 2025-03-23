import gi
import os
import subprocess
gi.require_version('Gtk', '3.0')
gi.require_version('Vte', '2.91')
from gi.repository import Gtk, Gdk, Vte, GLib
import modules.config as config

class TerminalTab(Gtk.Box):
    def __init__(self, parent_window, layout="single"):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL)
        self.parent_window = parent_window
        self.terminals = []
        
        # Initialize hint-related variables for each terminal
        self.hint_timeouts = {}
        self.current_commands = {}
        self.current_hints = {}
        
        if layout == "single":
            self.create_single_terminal()
        elif layout == "horizontal":
            self.create_horizontal_split()
        elif layout == "vertical":
            self.create_vertical_split()
        elif layout == "quad":
            self.create_quad_split()
        elif layout == "custom":
            self.show_custom_layout_dialog()
    def create_terminal(self):
        """Create a new terminal instance"""
        terminal = Vte.Terminal()
        terminal.connect("child-exited", self.on_terminal_exit)
        terminal.connect("key-press-event", lambda w, e: self.on_key_press(w, e))
        
        # Initialize hint state for this terminal
        self.hint_timeouts[terminal] = None
        self.current_commands[terminal] = ""
        self.current_hints[terminal] = ""
        
        terminal.set_scrollback_lines(self.parent_window.config.get('scrollback_lines', 10000))
        terminal.set_font_scale(self.parent_window.config.get('font_scale', 1.0))
        terminal.set_cursor_shape(self.get_cursor_shape(
            self.parent_window.config.get('cursor_shape', 'block')
        ))
        
        self.update_colors_for_terminal(terminal)
        self.start_shell(terminal)
        self.terminals.append(terminal)
        return terminal

    def create_single_terminal(self):
        """Create a single terminal layout"""
        terminal = self.create_terminal()
        self.pack_start(terminal, True, True, 0)
        self.terminal = terminal  # Keep reference for compatibility

    def create_horizontal_split(self):
        """Create two terminals side by side"""
        # Remove existing terminal
        if len(self.get_children()) > 0:
            old_terminal = self.get_children()[0]
            self.remove(old_terminal)
            
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.style_paned(paned)
        term1 = old_terminal if old_terminal else self.create_terminal()
        term2 = self.create_terminal()
        paned.pack1(term1, True, True)
        paned.pack2(term2, True, True)
        self.pack_start(paned, True, True, 0)
        self.terminal = term1  # Keep reference for compatibility
        term2.grab_focus()  # Focus the new terminal
        self.show_all()

    def create_vertical_split(self):
        """Create two terminals stacked vertically"""
        # Remove existing terminal
        if len(self.get_children()) > 0:
            old_terminal = self.get_children()[0]
            self.remove(old_terminal)
            
        paned = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
        self.style_paned(paned)
        term1 = old_terminal if old_terminal else self.create_terminal()
        term2 = self.create_terminal()
        paned.pack1(term1, True, True)
        paned.pack2(term2, True, True)
        self.pack_start(paned, True, True, 0)
        self.terminal = term1  # Keep reference for compatibility
        term2.grab_focus()  # Focus the new terminal
        self.show_all()

    def create_quad_split(self):
        """Create four terminals in a grid layout"""
        vpaned = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
        self.style_paned(vpaned)
        hpaned1 = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.style_paned(hpaned1)
        hpaned2 = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.style_paned(hpaned2)
        
        term1 = self.create_terminal()
        term2 = self.create_terminal()
        term3 = self.create_terminal()
        term4 = self.create_terminal()
        
        hpaned1.pack1(term1, True, True)
        hpaned1.pack2(term2, True, True)
        hpaned2.pack1(term3, True, True)
        hpaned2.pack2(term4, True, True)
        
        vpaned.pack1(hpaned1, True, True)
        vpaned.pack2(hpaned2, True, True)
        
        self.pack_start(vpaned, True, True, 0)
        self.terminal = term1  # Keep reference for compatibility
        term4.grab_focus()  # Focus the last terminal

    def show_custom_layout_dialog(self):
        """Show dialog for custom layout (with limits)"""
        dialog = Gtk.Dialog(
            title="Custom Layout",
            parent=self.parent_window,
            flags=0
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OK, Gtk.ResponseType.OK
        )

        box = dialog.get_content_area()
        box.set_spacing(6)

        # Add spinbuttons for rows and columns (limit to reasonable values)
        row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        row_box.pack_start(Gtk.Label(label="Rows:"), False, False, 0)
        row_spin = Gtk.SpinButton.new_with_range(1, 4, 1)
        row_box.pack_start(row_spin, True, True, 0)
        box.pack_start(row_box, True, True, 0)

        col_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        col_box.pack_start(Gtk.Label(label="Columns:"), False, False, 0)
        col_spin = Gtk.SpinButton.new_with_range(1, 4, 1)
        col_box.pack_start(col_spin, True, True, 0)
        box.pack_start(col_box, True, True, 0)

        box.show_all()
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            rows = int(row_spin.get_value())
            cols = int(col_spin.get_value())
            self.create_custom_layout(rows, cols)

        dialog.destroy()

    def create_custom_layout(self, rows, cols):
        """Create a custom grid layout of terminals"""
        if rows == 1 and cols == 1:
            self.create_single_terminal()
            return

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        for i in range(rows):
            hpaned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
            self.style_paned(hpaned)
            if i == 0:
                current_paned = hpaned
            else:
                vpaned = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
                self.style_paned(vpaned)
                vpaned.pack1(current_paned, True, True)
                vpaned.pack2(hpaned, True, True)
                current_paned = vpaned

            for j in range(cols):
                terminal = self.create_terminal()
                if j == 0:
                    hpaned.pack1(terminal, True, True)
                else:
                    hpaned.pack2(terminal, True, True)

        self.pack_start(current_paned, True, True, 0)
        self.terminal = self.terminals[0]  # Keep reference for compatibility
        self.terminals[-1].grab_focus()  # Focus the last terminal created

    def style_paned(self, paned):
        """Apply styling to make the paned divider more visible"""
        css = b"""
        paned separator { 
            background-color: rgba(200, 200, 200, 0.5);
            min-width: 3px;
            min-height: 3px;
        }
        """
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(css)
        paned.get_style_context().add_provider(
            css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
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
        for terminal in self.terminals:
            terminal.set_cursor_shape(self.get_cursor_shape(shape_name))

    def update_colors(self, bg_color, fg_color, opacity):
        """Update colors for all terminals"""
        for terminal in self.terminals:
            bg = config.parse_color(bg_color, opacity)
            fg = config.parse_color(fg_color)
            terminal.set_colors(fg, bg, [])

    def update_colors_for_terminal(self, terminal):
        """Update colors for a specific terminal"""
        bg = config.parse_color(
            self.parent_window.config.get('background_color', '#000000'),
            self.parent_window.config.get('background_opacity', 0.9)
        )
        fg = config.parse_color(
            self.parent_window.config.get('foreground_color', '#FFFFFF')
        )
        terminal.set_colors(fg, bg, [])

    def start_shell(self, terminal):
        """Start shell in the given terminal"""
        terminal.spawn_async(
            Vte.PtyFlags.DEFAULT,
            os.environ['HOME'],
            ["/bin/bash"],
            [],
            GLib.SpawnFlags.DEFAULT,
            None,
            None,
            -1,
            None,
            None
        )

    def on_terminal_exit(self, terminal, status):
        """Handle terminal exit - close tab or window appropriately"""
        # Remove the exited terminal from our list
        if terminal in self.terminals:
            self.terminals.remove(terminal)
            
        # Get the parent container of the terminal
        parent = terminal.get_parent()
        if not parent:
            return
            
        # If parent is a Paned widget, handle the split view case
        if isinstance(parent, Gtk.Paned):
            other_terminal = None
            # Find the other terminal that's still alive
            if parent.get_child1() == terminal:
                other_terminal = parent.get_child2()
            else:
                other_terminal = parent.get_child1()
                
            if other_terminal:
                # Get the grandparent (should be the tab box)
                grandparent = parent.get_parent()
                if grandparent:
                    # First remove both terminals from the paned
                    parent.remove(terminal)
                    parent.remove(other_terminal)
                    # Remove the paned from the tab
                    grandparent.remove(parent)
                    # Add the remaining terminal directly to the tab
                    grandparent.pack_start(other_terminal, True, True, 0)
                    if terminal == self.terminal:
                        self.terminal = other_terminal
                    grandparent.show_all()
                    return
        else:
            # Remove the terminal from its parent
            parent.remove(terminal)
            
        # If we still have terminals, try to show the next one
        if self.terminals:
            new_terminal = self.terminals[0]
            if new_terminal.get_parent() is None:  # Only pack if it doesn't have a parent
                self.pack_start(new_terminal, True, True, 0)
                self.terminal = new_terminal
                self.show_all()
            return
            
        # If no terminals left, handle tab/window closure
        notebook = self.get_parent()
        if not notebook:
            return
            
        page_num = notebook.page_num(self)
        if page_num == -1:
            return
            
        # If this is the last tab, destroy the window
        if notebook.get_n_pages() <= 1:
            self.parent_window.destroy()
        else:
            # Otherwise just remove this tab
            notebook.remove_page(page_num)

    def on_key_press(self, terminal, event):
        """Handle key events for command hints"""
        keyval = event.keyval
        if keyval == Gdk.KEY_Tab:
            if self.hint_timeouts.get(terminal):
                GLib.source_remove(self.hint_timeouts[terminal])
                self.hint_timeouts[terminal] = None
            self.current_hints[terminal] = ""
            return False
        elif keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            self.clear_hint(terminal)
            self.current_commands[terminal] = ""
        else:
            if keyval in range(32, 127):
                self.current_commands[terminal] = self.current_commands.get(terminal, "") + chr(keyval)
                self.schedule_hint_check(terminal)
            elif keyval == Gdk.KEY_BackSpace:
                if self.current_commands.get(terminal):
                    self.current_commands[terminal] = self.current_commands[terminal][:-1]
                    if self.current_commands[terminal]:
                        self.schedule_hint_check(terminal)
                    else:
                        self.clear_hint(terminal)
        return False

    def schedule_hint_check(self, terminal):
        """Schedule a new hint check with proper cleanup"""
        if self.hint_timeouts.get(terminal):
            GLib.source_remove(self.hint_timeouts[terminal])
        self.hint_timeouts[terminal] = GLib.timeout_add(1000, lambda: self.check_command_completion(terminal))

    def clear_hint(self, terminal):
        """Safely clear current hint"""
        if self.hint_timeouts.get(terminal):
            GLib.source_remove(self.hint_timeouts[terminal])
            self.hint_timeouts[terminal] = None
        if self.current_hints.get(terminal):
            terminal.feed(f"\033[{len(self.current_hints[terminal])}D\033[K".encode())
            self.current_hints[terminal] = ""

    def display_hint(self, terminal, hint_text):
        """Display hint directly in terminal"""
        if hint_text:
            sequence = f"\033[2;37m{hint_text}\033[0m"
            terminal.feed(sequence.encode())
            terminal.feed(f"\033[{len(hint_text)}D".encode())
            self.current_hints[terminal] = hint_text

    def check_command_completion(self, terminal):
        """Check for command completion"""
        try:
            current_command = self.current_commands.get(terminal, "")
            cmd = ["bash", "-c", f"compgen -c '{current_command}' | head -n 1"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            suggestion = result.stdout.strip()

            if suggestion and suggestion.startswith(current_command):
                completion = suggestion[len(current_command):]
                if completion:
                    self.display_hint(terminal, completion)

        except Exception as e:
            print(f"Error checking completion: {e}")
            self.clear_hint(terminal)

        self.hint_timeouts[terminal] = None
        return False
