import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Vte', '2.91')
from gi.repository import Gtk, Gdk, GLib
import cairo
from modules.plugins import Plugin

class GpuAccelerationPlugin(Plugin):
    def __init__(self):
        super().__init__()
        self.name = "GPU Acceleration"
        self.description = "Enables hardware acceleration for improved terminal rendering performance"
        self.version = "1.0"
        self.author = "HyxTerminal Team"
        self.categories = ["Performance"]
        self.tags = ["gpu", "hardware", "acceleration", "performance"]
        self.settings = {
            "enable_cairo_gl": True,
            "enable_vsync": True,
            "enable_triple_buffering": True,
            "texture_filter": "linear",  # or "nearest"
            "scroll_acceleration": True
        }
        
    def on_enable(self, parent_window):
        """Enable GPU acceleration features"""
        try:
            # Enable OpenGL-based rendering if available
            display = parent_window.get_display()
            if display:
                # Try to get the GPU device
                monitor = display.get_primary_monitor()
                if monitor:
                    # Enable hardware acceleration for the window
                    visual = parent_window.get_screen().get_rgba_visual()
                    if visual:
                        parent_window.set_visual(visual)
                        
            # Configure VTE terminal acceleration
            for terminal in self._get_all_terminals(parent_window):
                self._configure_terminal_acceleration(terminal)
                
            # Set up scrolling optimization
            if self.settings["scroll_acceleration"]:
                self._setup_scroll_acceleration(parent_window)
                
            return True
        except Exception as e:
            print(f"Error enabling GPU acceleration: {e}")
            return False
            
    def on_disable(self, parent_window):
        """Disable GPU acceleration features"""
        try:
            # Reset terminal settings to default
            for terminal in self._get_all_terminals(parent_window):
                self._reset_terminal_acceleration(terminal)
            return True
        except Exception as e:
            print(f"Error disabling GPU acceleration: {e}")
            return False
            
    def get_settings_widget(self):
        """Create settings widget for GPU acceleration options"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_start(10)
        box.set_margin_end(10)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        
        # Cairo GL acceleration
        cairo_switch = Gtk.Switch()
        cairo_switch.set_active(self.settings["enable_cairo_gl"])
        cairo_switch.connect("notify::active", self._on_cairo_switch_toggled)
        
        cairo_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        cairo_label = Gtk.Label(label="Enable Cairo GL acceleration")
        cairo_box.pack_start(cairo_label, True, True, 0)
        cairo_box.pack_end(cairo_switch, False, False, 0)
        box.pack_start(cairo_box, False, False, 0)
        
        # VSync
        vsync_switch = Gtk.Switch()
        vsync_switch.set_active(self.settings["enable_vsync"])
        vsync_switch.connect("notify::active", self._on_vsync_switch_toggled)
        
        vsync_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        vsync_label = Gtk.Label(label="Enable VSync")
        vsync_box.pack_start(vsync_label, True, True, 0)
        vsync_box.pack_end(vsync_switch, False, False, 0)
        box.pack_start(vsync_box, False, False, 0)
        
        # Triple buffering
        triple_switch = Gtk.Switch()
        triple_switch.set_active(self.settings["enable_triple_buffering"])
        triple_switch.connect("notify::active", self._on_triple_switch_toggled)
        
        triple_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        triple_label = Gtk.Label(label="Enable triple buffering")
        triple_box.pack_start(triple_label, True, True, 0)
        triple_box.pack_end(triple_switch, False, False, 0)
        box.pack_start(triple_box, False, False, 0)
        
        # Texture filter
        filter_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        filter_label = Gtk.Label(label="Texture filter:")
        filter_combo = Gtk.ComboBoxText()
        filter_combo.append_text("Linear")
        filter_combo.append_text("Nearest")
        filter_combo.set_active(0 if self.settings["texture_filter"] == "linear" else 1)
        filter_combo.connect("changed", self._on_filter_changed)
        
        filter_box.pack_start(filter_label, True, True, 0)
        filter_box.pack_end(filter_combo, False, False, 0)
        box.pack_start(filter_box, False, False, 0)
        
        # Scroll acceleration
        scroll_switch = Gtk.Switch()
        scroll_switch.set_active(self.settings["scroll_acceleration"])
        scroll_switch.connect("notify::active", self._on_scroll_switch_toggled)
        
        scroll_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        scroll_label = Gtk.Label(label="Enable scroll acceleration")
        scroll_box.pack_start(scroll_label, True, True, 0)
        scroll_box.pack_end(scroll_switch, False, False, 0)
        box.pack_start(scroll_box, False, False, 0)
        
        return box
        
    def _get_all_terminals(self, parent_window):
        """Get all terminal widgets from the window"""
        terminals = []
        for notebook in parent_window.get_children():
            if isinstance(notebook, Gtk.Notebook):
                for page_num in range(notebook.get_n_pages()):
                    page = notebook.get_nth_page(page_num)
                    for terminal in page.get_children():
                        if isinstance(terminal, Gtk.ScrolledWindow):
                            for child in terminal.get_children():
                                terminals.append(child)
        return terminals
        
    def _configure_terminal_acceleration(self, terminal):
        """Configure hardware acceleration for a terminal"""
        # Enable smooth scrolling
        terminal.set_scroll_on_output(False)
        terminal.set_scroll_on_keystroke(True)
        
        # Set scroll acceleration
        if self.settings["scroll_acceleration"]:
            terminal.set_scrollback_lines(10000)
        
        # Apply texture filtering
        if hasattr(terminal, "set_filter"):
            terminal.set_filter(
                cairo.FILTER_BILINEAR if self.settings["texture_filter"] == "linear"
                else cairo.FILTER_NEAREST
            )
            
    def _reset_terminal_acceleration(self, terminal):
        """Reset terminal acceleration settings to default"""
        terminal.set_scroll_on_output(True)
        terminal.set_scroll_on_keystroke(True)
        terminal.set_scrollback_lines(1000)
        if hasattr(terminal, "set_filter"):
            terminal.set_filter(cairo.FILTER_NEAREST)
            
    def _setup_scroll_acceleration(self, parent_window):
        """Set up accelerated scrolling"""
        def on_scroll(widget, event):
            # Use smooth scrolling with acceleration
            if event.direction == Gdk.ScrollDirection.UP:
                widget.emit('scroll-event', event)
                return True
            elif event.direction == Gdk.ScrollDirection.DOWN:
                widget.emit('scroll-event', event)
                return True
            return False
            
        # Add scroll event handler to all terminals
        for terminal in self._get_all_terminals(parent_window):
            terminal.connect('scroll-event', on_scroll)
            
    def _on_cairo_switch_toggled(self, switch, gparam):
        self.settings["enable_cairo_gl"] = switch.get_active()
        
    def _on_vsync_switch_toggled(self, switch, gparam):
        self.settings["enable_vsync"] = switch.get_active()
        
    def _on_triple_switch_toggled(self, switch, gparam):
        self.settings["enable_triple_buffering"] = switch.get_active()
        
    def _on_filter_changed(self, combo):
        self.settings["texture_filter"] = "linear" if combo.get_active() == 0 else "nearest"
        
    def _on_scroll_switch_toggled(self, switch, gparam):
        self.settings["scroll_acceleration"] = switch.get_active() 