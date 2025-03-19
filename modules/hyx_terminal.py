import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
from modules.plugin_manager import PluginManager

def __init__(self):
    super().__init__(title="HyxTerminal")
    
    # Initialize plugin manager
    self.plugin_manager = PluginManager()
    
    # Set window properties
    self.set_default_size(800, 600)
    self.set_position(Gtk.WindowPosition.CENTER) 