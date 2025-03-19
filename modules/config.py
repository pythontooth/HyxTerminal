import json
from pathlib import Path
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gdk, Pango

def load_config():
    config_path = Path.home() / '.config' / 'hyxterminal' / 'config.json'
    default_config = {
        'window_width': 800,
        'window_height': 600,
        'scrollback_lines': 10000,
        'font_scale': 1.0,
        'background_color': '#282A36',  # HyxTerminal brand color
        'foreground_color': '#FFFFFF',
        'background_opacity': 0.95,
        'accent_color': '#14A89A',      # Teal accent color
        'font_family': 'Monospace',
        'font_size': 11,
        'cursor_shape': 'block',
        'cursor_blink_mode': 'system',
        'theme_name': 'HyxTerminal'     # Default theme name
    }
    
    if config_path.exists():
        try:
            with open(config_path) as f:
                return {**default_config, **json.load(f)}
        except Exception:
            return default_config
    return default_config

def save_config(config):
    config_path = Path.home() / '.config' / 'hyxterminal' / 'config.json'
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=4)

def parse_color(color_str, opacity=1.0):
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

def rgba_to_hex(rgba):
    return '#{:02x}{:02x}{:02x}'.format(
        int(rgba.red * 255),
        int(rgba.green * 255),
        int(rgba.blue * 255)
    )
