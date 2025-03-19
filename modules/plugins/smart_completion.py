import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from modules.plugins import Plugin

class SmartCompletionPlugin(Plugin):
    def __init__(self):
        super().__init__()
        self.name = "Smart Completion"
        self.description = "Provides intelligent command completion with hints displayed directly in the terminal"
        self.version = "1.0"
        self.author = "HyxTerminal Team"
        self.categories = ["Terminal", "Productivity"]
        self.tags = ["completion", "hints", "commands"]
        self.settings = {
            "delay_ms": 1000,
            "case_sensitive": False,
            "hint_style": "subtle"
        }
        
    def on_enable(self, parent_window):
        """Enable smart completion for all terminals"""
        if hasattr(parent_window, 'notebook'):
            for i in range(parent_window.notebook.get_n_pages()):
                tab = parent_window.notebook.get_nth_page(i)
                for terminal in tab.terminals:
                    # Enable command completion
                    if hasattr(tab, 'hint_timeouts'):
                        tab.hint_timeouts[terminal] = None
                        tab.current_commands[terminal] = ""
                        tab.current_hints[terminal] = ""
                        
    def on_disable(self, parent_window):
        """Disable smart completion for all terminals"""
        if hasattr(parent_window, 'notebook'):
            for i in range(parent_window.notebook.get_n_pages()):
                tab = parent_window.notebook.get_nth_page(i)
                for terminal in tab.terminals:
                    # Clear current hints
                    if hasattr(tab, 'hint_timeouts'):
                        if tab.hint_timeouts.get(terminal):
                            tab.clear_hint(terminal)
                            
    def get_settings_widget(self):
        """Create settings widget for the plugin"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_start(10)
        box.set_margin_end(10)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        
        # Delay setting
        delay_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        delay_label = Gtk.Label(label="Completion delay (ms):")
        delay_spinner = Gtk.SpinButton.new_with_range(100, 5000, 100)
        delay_spinner.set_value(self.settings["delay_ms"])
        delay_box.pack_start(delay_label, False, False, 0)
        delay_box.pack_start(delay_spinner, True, True, 0)
        box.pack_start(delay_box, False, False, 0)
        
        # Case sensitivity setting
        case_check = Gtk.CheckButton(label="Case sensitive completion")
        case_check.set_active(self.settings["case_sensitive"])
        box.pack_start(case_check, False, False, 0)
        
        # Hint style setting
        style_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        style_label = Gtk.Label(label="Hint style:")
        style_combo = Gtk.ComboBoxText()
        for style in ["Subtle", "Bold", "Italic", "Colored"]:
            style_combo.append_text(style)
        style_combo.set_active(["subtle", "bold", "italic", "colored"].index(self.settings["hint_style"]))
        style_box.pack_start(style_label, False, False, 0)
        style_box.pack_start(style_combo, True, True, 0)
        box.pack_start(style_box, False, False, 0)
        
        # Connect signals
        def on_delay_changed(spinner):
            self.settings["delay_ms"] = spinner.get_value_as_int()
            
        def on_case_changed(button):
            self.settings["case_sensitive"] = button.get_active()
            
        def on_style_changed(combo):
            styles = ["subtle", "bold", "italic", "colored"]
            self.settings["hint_style"] = styles[combo.get_active()]
            
        delay_spinner.connect("value-changed", on_delay_changed)
        case_check.connect("toggled", on_case_changed)
        style_combo.connect("changed", on_style_changed)
        
        return box 