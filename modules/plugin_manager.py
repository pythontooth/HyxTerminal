import json
import os
from pathlib import Path

class PluginManager:
    def __init__(self):
        self.settings_file = Path.home() / '.hyxterminal' / 'plugin_settings.json'
        self.settings = self._load_settings()
        
    def _load_settings(self):
        """Load plugin settings from file"""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"Error loading plugin settings: {e}")
            return {}
            
    def _save_settings(self):
        """Save plugin settings to file"""
        try:
            # Create directory if it doesn't exist
            self.settings_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            print(f"Error saving plugin settings: {e}")
            
    def get_plugin_settings(self, plugin_name):
        """Get settings for a specific plugin"""
        if plugin_name in self.settings:
            return self.settings[plugin_name].get('settings', {})
        return {}
        
    def update_plugin_settings(self, plugin_name, settings):
        """Update settings for a specific plugin"""
        if plugin_name not in self.settings:
            self.settings[plugin_name] = {'enabled': False, 'settings': {}}
            
        # Update only the settings part, preserve enabled state
        self.settings[plugin_name]['settings'] = settings
        self._save_settings()
        
    def get_plugin_enabled(self, plugin_name):
        """Get enabled state for a specific plugin"""
        if plugin_name in self.settings:
            return self.settings[plugin_name].get('enabled', False)
        return False
        
    def set_plugin_enabled(self, plugin_name, enabled):
        """Set enabled state for a specific plugin"""
        if plugin_name not in self.settings:
            self.settings[plugin_name] = {'enabled': False, 'settings': {}}
            
        self.settings[plugin_name]['enabled'] = enabled
        self._save_settings() 