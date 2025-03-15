#!/usr/bin/env python3

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Vte', '2.91')
from gi.repository import Gtk, Gdk, Vte, GLib
import os

class HyxTerminal(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="HyxTerminal")
        self.set_default_size(800, 600)

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

        # Create terminal
        self.terminal = Vte.Terminal()
        self.terminal.set_scrollback_lines(1000)
        self.terminal.connect("child-exited", self.on_terminal_exit)
        
        # Terminal colors
        self.terminal.set_color_background(Gdk.RGBA(0, 0, 0, 1))
        self.terminal.set_color_foreground(Gdk.RGBA(1, 1, 1, 1))

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
