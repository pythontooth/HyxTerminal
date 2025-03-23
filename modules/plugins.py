import gi
import os
import json
import importlib
import inspect
from typing import Dict, List, Optional, Any
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

class Plugin:
    """Base class for all plugins"""
    def __init__(self):
        self.name = "Base Plugin"
        self.description = "Base plugin class"
        self.version = "1.0"
        self.author = "HyxTerminal Team"
        self.enabled = False
        self.settings = {}
        self.dependencies = []
        self.categories = []
        self.tags = []
        
    def on_enable(self, parent_window):
        """Called when the plugin is enabled"""
        pass
        
    def on_disable(self, parent_window):
        """Called when the plugin is disabled"""
        pass
        
    def on_settings_changed(self, settings):
        """Called when plugin settings are changed"""
        self.settings.update(settings)
        
    def get_settings_widget(self):
        """Return a widget for plugin settings"""
        return None

class PluginManager:
    """Manages plugin loading, unloading, and state"""
    def __init__(self, parent_window):
        self.parent_window = parent_window
        self.plugins: Dict[str, Plugin] = {}
        self.loaded_plugins: Dict[str, Plugin] = {}
        self.plugin_dir = os.path.join(os.path.dirname(__file__), "plugins")
        self.settings_file = os.path.join(os.path.dirname(__file__), "plugin_settings.json")
        self.load_settings()
        
    def load_settings(self):
        """Load plugin settings from file"""
        if os.path.exists(self.settings_file):
            with open(self.settings_file, 'r') as f:
                self.settings = json.load(f)
        else:
            self.settings = {}
            
    def save_settings(self):
        """Save plugin settings to file"""
        settings_data = {}
        for name, plugin in self.plugins.items():
            settings_data[name] = {
                'enabled': plugin.enabled,
                'settings': plugin.settings
            }
        with open(self.settings_file, 'w') as f:
            json.dump(settings_data, f, indent=4)
            
    def load_plugins(self):
        """Load all available plugins"""
        if not os.path.exists(self.plugin_dir):
            os.makedirs(self.plugin_dir)
            
        for filename in os.listdir(self.plugin_dir):
            if filename.endswith('.py') and not filename.startswith('__'):
                try:
                    module_name = f"modules.plugins.{filename[:-3]}"
                    spec = importlib.util.spec_from_file_location(
                        module_name,
                        os.path.join(self.plugin_dir, filename)
                    )
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Find plugin classes in the module
                    for name, obj in inspect.getmembers(module):
                        if (inspect.isclass(obj) and 
                            issubclass(obj, Plugin) and 
                            obj != Plugin):
                            plugin = obj()
                            self.plugins[plugin.name] = plugin
                            
                            # Restore plugin state from settings
                            if plugin.name in self.settings:
                                plugin.enabled = self.settings[plugin.name].get('enabled', False)
                                plugin.settings = self.settings[plugin.name].get('settings', {})
                                
                            if plugin.enabled:
                                self.enable_plugin(plugin.name)
                except Exception as e:
                    print(f"Error loading plugin {filename}: {e}")
                    
    def enable_plugin(self, plugin_name: str) -> bool:
        """Enable a plugin and its dependencies"""
        if plugin_name not in self.plugins:
            return False
            
        plugin = self.plugins[plugin_name]
        
        # Check dependencies
        for dep in plugin.dependencies:
            if dep not in self.loaded_plugins:
                if not self.enable_plugin(dep):
                    return False
                    
        plugin.enabled = True
        plugin.on_enable(self.parent_window)
        self.loaded_plugins[plugin_name] = plugin
        self.save_settings()
        return True
        
    def disable_plugin(self, plugin_name: str) -> bool:
        """Disable a plugin"""
        if plugin_name not in self.loaded_plugins:
            return False
            
        plugin = self.loaded_plugins[plugin_name]
        plugin.enabled = False
        plugin.on_disable(self.parent_window)
        del self.loaded_plugins[plugin_name]
        self.save_settings()
        return True
        
    def get_plugin(self, plugin_name: str) -> Optional[Plugin]:
        """Get a plugin by name"""
        return self.plugins.get(plugin_name)
        
    def get_enabled_plugins(self) -> List[Plugin]:
        """Get list of enabled plugins"""
        return list(self.loaded_plugins.values())
        
    def get_available_plugins(self) -> List[Plugin]:
        """Get list of all available plugins"""
        return list(self.plugins.values())
        
    def update_plugin_settings(self, plugin_name: str, settings: Dict[str, Any]):
        """Update settings for a plugin"""
        if plugin_name in self.plugins:
            plugin = self.plugins[plugin_name]
            plugin.on_settings_changed(settings)
            self.save_settings()
            return True
        return False

class Plugins:
    """Static class for plugin-related UI operations"""
    _manager = None
    
    @classmethod
    def initialize(cls, parent_window):
        """Initialize the plugin manager"""
        cls._manager = PluginManager(parent_window)
        cls._manager.load_plugins()
        
    @classmethod
    def show_plugin_browser(cls, parent_window):
        """Show plugin browser dialog with available plugins"""
        if not cls._manager:
            cls.initialize(parent_window)
            
        dialog = Gtk.Dialog(
            title="Plugin Browser",
            parent=parent_window,
            flags=0
        )
        dialog.add_buttons(
            Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE
        )
        dialog.set_default_size(800, 600)
        
        # Create main container
        main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        main_box.set_margin_start(12)
        main_box.set_margin_end(12)
        main_box.set_margin_top(12)
        main_box.set_margin_bottom(12)
        dialog.get_content_area().pack_start(main_box, True, True, 0)
        
        # Left panel - Plugin list
        left_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        left_panel.set_size_request(520, -1)  # Fixed width for left panel
        
        # Search box with icon
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        search_icon = Gtk.Image.new_from_icon_name("system-search", Gtk.IconSize.SMALL_TOOLBAR)
        search_entry = Gtk.SearchEntry()
        search_entry.set_placeholder_text("Search plugins...")
        search_box.pack_start(search_icon, False, False, 0)
        search_box.pack_start(search_entry, True, True, 0)
        left_panel.pack_start(search_box, False, False, 0)
        
        # Category filter
        filter_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        filter_label = Gtk.Label(label="Filter by:")
        filter_combo = Gtk.ComboBoxText()
        filter_combo.append_text("All Categories")
        categories = set()
        for plugin in cls._manager.get_available_plugins():
            categories.update(plugin.categories)
        for category in sorted(categories):
            filter_combo.append_text(category)
        filter_combo.set_active(0)
        filter_box.pack_start(filter_label, False, False, 0)
        filter_box.pack_start(filter_combo, True, True, 0)
        left_panel.pack_start(filter_box, False, False, 0)
        
        # Plugin list
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        
        # Create list store
        store = Gtk.ListStore(str, str, bool, str, str, str, str, str)  # Added status column
        treeview = Gtk.TreeView(model=store)
        treeview.set_headers_visible(True)
        
        # Add columns
        # Status column (enabled/disabled)
        renderer_toggle = Gtk.CellRendererToggle()
        renderer_toggle.connect("toggled", lambda cell, path: cls.on_plugin_toggled(cell, path, store))
        column_status = Gtk.TreeViewColumn("Status", renderer_toggle, active=2)
        column_status.set_min_width(60)
        column_status.set_fixed_width(60)
        column_status.set_resizable(True)
        treeview.append_column(column_status)
        
        # Name column
        renderer_text = Gtk.CellRendererText()
        column_name = Gtk.TreeViewColumn("Plugin", renderer_text, text=0)
        column_name.set_min_width(150)
        column_name.set_fixed_width(150)
        column_name.set_resizable(True)
        treeview.append_column(column_name)
        
        # Version column
        renderer_text = Gtk.CellRendererText()
        column_version = Gtk.TreeViewColumn("Version", renderer_text, text=3)
        column_version.set_min_width(80)
        column_version.set_fixed_width(80)
        column_version.set_resizable(True)
        treeview.append_column(column_version)
        
        # Categories column
        renderer_text = Gtk.CellRendererText()
        column_categories = Gtk.TreeViewColumn("Categories", renderer_text, text=5)
        column_categories.set_min_width(150)
        column_categories.set_fixed_width(150)
        column_categories.set_resizable(True)
        treeview.append_column(column_categories)
        
        # Status text column
        renderer_text = Gtk.CellRendererText()
        column_status_text = Gtk.TreeViewColumn("", renderer_text, text=7)
        column_status_text.set_min_width(80)
        column_status_text.set_fixed_width(80)
        column_status_text.set_resizable(True)
        treeview.append_column(column_status_text)
        
        scrolled.add(treeview)
        left_panel.pack_start(scrolled, True, True, 0)
        
        # Right panel - Details
        right_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        right_panel.set_size_request(240, -1)  # Fixed width for right panel
        
        # Plugin details frame
        details_frame = Gtk.Frame(label="Plugin Details")
        details_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        details_box.set_margin_start(12)
        details_box.set_margin_end(12)
        details_box.set_margin_top(12)
        details_box.set_margin_bottom(12)
        
        # Plugin icon and name
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        plugin_icon = Gtk.Image.new_from_icon_name("application-x-addon", Gtk.IconSize.DIALOG)
        header_box.pack_start(plugin_icon, False, False, 0)
        
        name_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        name_label = Gtk.Label()
        name_label.set_markup("<span size='x-large'><b>Select a plugin</b></span>")
        version_label = Gtk.Label()
        version_label.set_markup("<span size='small' color='gray'>Version: -</span>")
        name_box.pack_start(name_label, False, False, 0)
        name_box.pack_start(version_label, False, False, 0)
        header_box.pack_start(name_box, True, True, 0)
        details_box.pack_start(header_box, False, False, 0)
        
        # Description
        desc_label = Gtk.Label()
        desc_label.set_line_wrap(True)
        desc_label.set_xalign(0)
        desc_label.set_markup("<i>Select a plugin to view its description</i>")
        details_box.pack_start(desc_label, False, False, 0)
        
        # Author
        author_label = Gtk.Label()
        author_label.set_markup("<span size='small'><b>Author:</b> -</span>")
        details_box.pack_start(author_label, False, False, 0)
        
        # Tags
        tags_label = Gtk.Label()
        tags_label.set_markup("<span size='small'><b>Tags:</b> -</span>")
        details_box.pack_start(tags_label, False, False, 0)
        
        # Settings button
        settings_button = Gtk.Button(label="Configure Plugin")
        settings_button.set_sensitive(False)
        settings_button.connect("clicked", lambda w: cls.show_plugin_settings(parent_window, treeview))
        details_box.pack_start(settings_button, False, False, 0)
        
        details_frame.add(details_box)
        right_panel.pack_start(details_frame, True, True, 0)
        
        # Add panels to main container
        main_box.pack_start(left_panel, True, True, 0)
        main_box.pack_start(right_panel, True, True, 0)
        
        # Add plugins to store
        for plugin in cls._manager.get_available_plugins():
            status_text = "Enabled" if plugin.enabled else "Disabled"
            store.append([
                plugin.name,
                plugin.description,
                plugin.enabled,
                plugin.version,
                plugin.author,
                ", ".join(plugin.categories),
                ", ".join(plugin.tags),
                status_text
            ])
        
        # Handle selection changes
        selection = treeview.get_selection()
        selection.connect("changed", lambda sel: cls.on_plugin_selection_changed(
            sel, store, name_label, version_label, desc_label, author_label, tags_label, settings_button
        ))
        
        # Handle search and filtering
        def filter_plugins(entry):
            search_text = entry.get_text().lower()
            category = filter_combo.get_active_text()
            store.clear()
            
            for plugin in cls._manager.get_available_plugins():
                if category != "All Categories" and category not in plugin.categories:
                    continue
                    
                if (search_text in plugin.name.lower() or
                    search_text in plugin.description.lower() or
                    search_text in " ".join(plugin.categories).lower() or
                    search_text in " ".join(plugin.tags).lower()):
                    status_text = "Enabled" if plugin.enabled else "Disabled"
                    store.append([
                        plugin.name,
                        plugin.description,
                        plugin.enabled,
                        plugin.version,
                        plugin.author,
                        ", ".join(plugin.categories),
                        ", ".join(plugin.tags),
                        status_text
                    ])
        
        search_entry.connect("search-changed", filter_plugins)
        filter_combo.connect("changed", lambda w: filter_plugins(search_entry))
        
        dialog.show_all()
        dialog.run()
        dialog.destroy()
    
    @classmethod
    def on_plugin_toggled(cls, cell, path, store):
        """Toggle plugin enabled state"""
        store[path][2] = not store[path][2]
        plugin_name = store[path][0]
        enabled = store[path][2]
        
        if enabled:
            cls._manager.enable_plugin(plugin_name)
        else:
            cls._manager.disable_plugin(plugin_name)
    
    @classmethod
    def on_plugin_selection_changed(cls, selection, store, name_label, version_label, 
                                  desc_label, author_label, tags_label, settings_button):
        """Update plugin details when selection changes"""
        model, treeiter = selection.get_selected()
        if treeiter is not None:
            name = model[treeiter][0]
            desc = model[treeiter][1]
            version = model[treeiter][3]
            author = model[treeiter][4]
            categories = model[treeiter][5]
            tags = model[treeiter][6]
            
            name_label.set_markup(f"<span size='x-large'><b>{name}</b></span>")
            version_label.set_markup(f"<span size='small' color='gray'>Version: {version}</span>")
            desc_label.set_text(desc)
            author_label.set_markup(f"<span size='small'><b>Author:</b> {author}</span>")
            tags_label.set_markup(f"<span size='small'><b>Tags:</b> {tags}</span>")
            settings_button.set_sensitive(True)
        else:
            name_label.set_markup("<span size='x-large'><b>Select a plugin</b></span>")
            version_label.set_markup("<span size='small' color='gray'>Version: -</span>")
            desc_label.set_text("Select a plugin to view its description")
            author_label.set_markup("<span size='small'><b>Author:</b> -</span>")
            tags_label.set_markup("<span size='small'><b>Tags:</b> -</span>")
            settings_button.set_sensitive(False)
    
    @classmethod
    def show_plugin_settings(cls, parent_window, treeview):
        """Show settings dialog for the selected plugin"""
        model, treeiter = treeview.get_selection().get_selected()
        if treeiter is None:
            return
            
        plugin_name = model[treeiter][0]
        plugin = cls._manager.get_plugin(plugin_name)
        if not plugin:
            return
            
        dialog = Gtk.Dialog(
            title=f"Settings - {plugin_name}",
            parent=parent_window,
            flags=0
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE, Gtk.ResponseType.ACCEPT
        )
        dialog.set_default_size(400, 300)
        
        # Get settings widget from plugin
        settings_widget = plugin.get_settings_widget()
        if settings_widget:
            dialog.get_content_area().pack_start(settings_widget, True, True, 0)
        else:
            label = Gtk.Label(label="This plugin has no settings.")
            label.set_margin_start(10)
            label.set_margin_end(10)
            label.set_margin_top(10)
            label.set_margin_bottom(10)
            dialog.get_content_area().pack_start(label, True, True, 0)
            
        dialog.show_all()
        response = dialog.run()
        
        if response == Gtk.ResponseType.ACCEPT:
            # Save settings
            cls._manager.update_plugin_settings(plugin_name, plugin.settings)
            
        dialog.destroy() 