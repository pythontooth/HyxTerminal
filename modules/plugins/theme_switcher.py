import gi
import time
from datetime import datetime
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
from modules.plugins import Plugin
from modules.themes import Themes

class ThemeSwitcherPlugin(Plugin):
    def __init__(self):
        super().__init__()
        self.name = "Theme Switcher"
        self.description = "Automatically switch themes based on time of day"
        self.version = "1.0"
        self.author = "HyxTerminal Team"
        self.categories = ["Appearance", "Automation"]
        self.tags = ["themes", "dark-mode", "light-mode"]
        self.settings = {
            "auto_switch": True,
            "day_theme": "Solarized Light",
            "night_theme": "Solarized Dark",
            "day_start_hour": 7,
            "night_start_hour": 19
        }
        self.timeout_id = None
        
    def on_enable(self, parent_window):
        """Enable theme switcher"""
        self.parent_window = parent_window
        if self.settings["auto_switch"]:
            self.start_theme_checker()
            
    def on_disable(self, parent_window):
        """Disable theme switcher"""
        if self.timeout_id:
            GLib.source_remove(self.timeout_id)
            self.timeout_id = None
            
    def start_theme_checker(self):
        """Start periodic theme checking"""
        self.check_and_update_theme()
        # Check every minute
        self.timeout_id = GLib.timeout_add(60000, self.check_and_update_theme)
        
    def check_and_update_theme(self):
        """Check current time and update theme if needed"""
        current_hour = datetime.now().hour
        
        if current_hour >= self.settings["day_start_hour"] and current_hour < self.settings["night_start_hour"]:
            # Day time
            self.apply_theme(self.settings["day_theme"])
        else:
            # Night time
            self.apply_theme(self.settings["night_theme"])
            
        return True
        
    def apply_theme(self, theme_name):
        """Apply the specified theme"""
        for name, bg, fg in Themes.THEME_LIST:
            if name == theme_name:
                Themes.apply_theme(self.parent_window, bg, fg, name)
                break
                
    def get_settings_widget(self):
        """Create settings widget for the plugin"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_start(10)
        box.set_margin_end(10)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        
        # Auto-switch setting
        auto_switch = Gtk.CheckButton(label="Automatically switch themes")
        auto_switch.set_active(self.settings["auto_switch"])
        box.pack_start(auto_switch, False, False, 0)
        
        # Day theme setting
        day_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        day_label = Gtk.Label(label="Day theme:")
        day_combo = Gtk.ComboBoxText()
        for name, _, _ in Themes.THEME_LIST:
            day_combo.append_text(name)
        day_combo.set_active([name for name, _, _ in Themes.THEME_LIST].index(self.settings["day_theme"]))
        day_box.pack_start(day_label, False, False, 0)
        day_box.pack_start(day_combo, True, True, 0)
        box.pack_start(day_box, False, False, 0)
        
        # Night theme setting
        night_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        night_label = Gtk.Label(label="Night theme:")
        night_combo = Gtk.ComboBoxText()
        for name, _, _ in Themes.THEME_LIST:
            night_combo.append_text(name)
        night_combo.set_active([name for name, _, _ in Themes.THEME_LIST].index(self.settings["night_theme"]))
        night_box.pack_start(night_label, False, False, 0)
        night_box.pack_start(night_combo, True, True, 0)
        box.pack_start(night_box, False, False, 0)
        
        # Time settings
        time_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        
        day_time = Gtk.SpinButton.new_with_range(0, 23, 1)
        day_time.set_value(self.settings["day_start_hour"])
        day_label2 = Gtk.Label(label="Day starts at:")
        
        night_time = Gtk.SpinButton.new_with_range(0, 23, 1)
        night_time.set_value(self.settings["night_start_hour"])
        night_label2 = Gtk.Label(label="Night starts at:")
        
        time_box.pack_start(day_label2, False, False, 0)
        time_box.pack_start(day_time, False, False, 0)
        time_box.pack_start(night_label2, False, False, 0)
        time_box.pack_start(night_time, False, False, 0)
        box.pack_start(time_box, False, False, 0)
        
        # Connect signals
        def on_auto_switch_changed(button):
            self.settings["auto_switch"] = button.get_active()
            if self.settings["auto_switch"]:
                self.start_theme_checker()
            else:
                self.on_disable(self.parent_window)
                
        def on_day_theme_changed(combo):
            self.settings["day_theme"] = combo.get_active_text()
            if datetime.now().hour >= self.settings["day_start_hour"] and datetime.now().hour < self.settings["night_start_hour"]:
                self.apply_theme(self.settings["day_theme"])
                
        def on_night_theme_changed(combo):
            self.settings["night_theme"] = combo.get_active_text()
            if datetime.now().hour < self.settings["day_start_hour"] or datetime.now().hour >= self.settings["night_start_hour"]:
                self.apply_theme(self.settings["night_theme"])
                
        def on_day_time_changed(spinner):
            self.settings["day_start_hour"] = spinner.get_value_as_int()
            self.check_and_update_theme()
            
        def on_night_time_changed(spinner):
            self.settings["night_start_hour"] = spinner.get_value_as_int()
            self.check_and_update_theme()
            
        auto_switch.connect("toggled", on_auto_switch_changed)
        day_combo.connect("changed", on_day_theme_changed)
        night_combo.connect("changed", on_night_theme_changed)
        day_time.connect("value-changed", on_day_time_changed)
        night_time.connect("value-changed", on_night_time_changed)
        
        return box 