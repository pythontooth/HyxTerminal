import gi
import os
import cairo
import threading
import time
from PIL import Image, ImageEnhance
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
from modules.plugins import Plugin

class TerminalWallpaperPlugin(Plugin):
    def __init__(self):
        super().__init__()
        self.name = "Terminal Wallpaper"
        self.description = "Beautiful terminal backgrounds with smart transparency and brightness adjustments"
        self.version = "1.0"
        self.author = "HyxTerminal Team"
        self.categories = ["Appearance", "Terminal"]
        self.tags = ["wallpaper", "background", "transparency", "theme"]
        self.settings = {
            "enabled": True,
            "type": "image",  # image, gif, video
            "path": "",
            "brightness": 0.3,  # 0.0 to 1.0
            "blur": 0.0,  # 0.0 to 10.0
            "animation_speed": 1.0,  # 0.5 to 2.0
            "fit_mode": "cover",  # cover, contain, fill
            "auto_adjust": True,  # Automatically adjust brightness based on theme
            "opacity": 0.15  # 0.0 to 1.0
        }
        self.current_image = None
        self.current_frame = None
        self.animation_thread = None
        self.animation_running = False
        self.terminal_widgets = {}
        
    def on_enable(self, parent_window):
        """Enable terminal wallpaper"""
        self.parent_window = parent_window
        # Load settings first
        self.load_settings()
        # Then load wallpaper if path exists
        if self.settings.get("path"):
            self.load_wallpaper()
            self.start_animation()
        
    def on_disable(self, parent_window):
        """Disable terminal wallpaper"""
        self.stop_animation()
        self.clear_wallpaper()
        
    def get_settings_widget(self):
        """Create settings widget for the plugin"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        
        # File selection
        file_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        file_label = Gtk.Label(label="Wallpaper File:")
        file_button = Gtk.FileChooserButton(title="Select Wallpaper")
        file_button.set_action(Gtk.FileChooserAction.OPEN)
        file_button.set_current_folder(os.path.expanduser("~/Pictures"))
        
        # Set current file if exists
        if self.settings.get("path") and os.path.exists(self.settings["path"]):
            file_button.set_filename(self.settings["path"])
        
        # Set file filters
        filter_images = Gtk.FileFilter()
        filter_images.set_name("Images and Animations")
        filter_images.add_mime_type("image/*")
        filter_images.add_mime_type("video/mp4")
        file_button.add_filter(filter_images)
        
        file_box.pack_start(file_label, False, False, 0)
        file_box.pack_start(file_button, True, True, 0)
        box.pack_start(file_box, False, False, 0)
        
        # Type selection
        type_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        type_label = Gtk.Label(label="Type:")
        type_combo = Gtk.ComboBoxText()
        type_combo.append_text("Image")
        type_combo.append_text("GIF")
        type_combo.append_text("Video")
        type_combo.set_active(0)
        type_box.pack_start(type_label, False, False, 0)
        type_box.pack_start(type_combo, True, True, 0)
        box.pack_start(type_box, False, False, 0)
        
        # Brightness adjustment
        brightness_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        brightness_label = Gtk.Label(label="Brightness:")
        brightness_scale = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, 0, 100, 1
        )
        brightness_scale.set_value(self.settings["brightness"] * 100)
        brightness_box.pack_start(brightness_label, False, False, 0)
        brightness_box.pack_start(brightness_scale, True, True, 0)
        box.pack_start(brightness_box, False, False, 0)
        
        # Blur adjustment
        blur_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        blur_label = Gtk.Label(label="Blur:")
        blur_scale = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, 0, 100, 1
        )
        blur_scale.set_value(self.settings["blur"] * 10)
        blur_box.pack_start(blur_label, False, False, 0)
        blur_box.pack_start(blur_scale, True, True, 0)
        box.pack_start(blur_box, False, False, 0)
        
        # Opacity adjustment
        opacity_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        opacity_label = Gtk.Label(label="Opacity:")
        opacity_scale = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, 0, 100, 1
        )
        opacity_scale.set_value(self.settings["opacity"] * 100)
        opacity_box.pack_start(opacity_label, False, False, 0)
        opacity_box.pack_start(opacity_scale, True, True, 0)
        box.pack_start(opacity_box, False, False, 0)
        
        # Fit mode selection
        fit_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        fit_label = Gtk.Label(label="Fit Mode:")
        fit_combo = Gtk.ComboBoxText()
        fit_combo.append_text("Cover")
        fit_combo.append_text("Contain")
        fit_combo.append_text("Fill")
        fit_combo.set_active(["cover", "contain", "fill"].index(self.settings["fit_mode"]))
        fit_box.pack_start(fit_label, False, False, 0)
        fit_box.pack_start(fit_combo, True, True, 0)
        box.pack_start(fit_box, False, False, 0)
        
        # Auto-adjust toggle
        auto_adjust = Gtk.CheckButton(label="Auto-adjust brightness based on theme")
        auto_adjust.set_active(self.settings["auto_adjust"])
        box.pack_start(auto_adjust, False, False, 0)
        
        # Animation speed (for GIFs and videos)
        speed_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        speed_label = Gtk.Label(label="Animation Speed:")
        speed_scale = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, 50, 200, 1
        )
        speed_scale.set_value(self.settings["animation_speed"] * 100)
        speed_box.pack_start(speed_label, False, False, 0)
        speed_box.pack_start(speed_scale, True, True, 0)
        box.pack_start(speed_box, False, False, 0)
        
        # Connect signals
        def on_file_selected(button):
            filename = button.get_filename()
            if filename:
                self.settings["path"] = filename
                # Save settings immediately
                self.save_settings()
                # Reload wallpaper
                self.load_wallpaper()
                if self.settings["type"] == "gif":
                    self.restart_animation()
                
        def on_type_changed(combo):
            self.settings["type"] = combo.get_active_text().lower()
            self.save_settings()
            self.load_wallpaper()
            if self.settings["type"] == "gif":
                self.restart_animation()
            
        def on_brightness_changed(scale):
            self.settings["brightness"] = scale.get_value() / 100
            self.save_settings()
            self.update_wallpaper()
            
        def on_blur_changed(scale):
            self.settings["blur"] = scale.get_value() / 10
            self.save_settings()
            self.update_wallpaper()
            
        def on_opacity_changed(scale):
            self.settings["opacity"] = scale.get_value() / 100
            self.save_settings()
            self.update_wallpaper()
            
        def on_fit_changed(combo):
            self.settings["fit_mode"] = combo.get_active_text().lower()
            self.save_settings()
            self.update_wallpaper()
            
        def on_auto_adjust_changed(button):
            self.settings["auto_adjust"] = button.get_active()
            self.save_settings()
            self.update_wallpaper()
            
        def on_speed_changed(scale):
            self.settings["animation_speed"] = scale.get_value() / 100
            self.save_settings()
            self.restart_animation()
            
        file_button.connect("file-set", on_file_selected)
        type_combo.connect("changed", on_type_changed)
        brightness_scale.connect("value-changed", on_brightness_changed)
        blur_scale.connect("value-changed", on_blur_changed)
        opacity_scale.connect("value-changed", on_opacity_changed)
        fit_combo.connect("changed", on_fit_changed)
        auto_adjust.connect("toggled", on_auto_adjust_changed)
        speed_scale.connect("value-changed", on_speed_changed)
        
        return box
        
    def load_wallpaper(self):
        """Load the wallpaper file"""
        if not self.settings.get("path") or not os.path.exists(self.settings["path"]):
            print(f"Wallpaper path not set or file does not exist: {self.settings.get('path')}")
            return
            
        try:
            if self.settings["type"] == "gif":
                self.current_image = Image.open(self.settings["path"])
                self.current_frame = 0
            elif self.settings["type"] == "video":
                # TODO: Implement video support using GStreamer
                pass
            else:  # image
                self.current_image = Image.open(self.settings["path"])
                self.current_frame = None
                
            print(f"Successfully loaded wallpaper: {self.settings['path']}")
            self.update_wallpaper()
        except Exception as e:
            print(f"Error loading wallpaper: {e}")
            
    def update_wallpaper(self):
        """Update the wallpaper display"""
        if not self.current_image:
            print("No image loaded to update wallpaper")
            return
            
        # Get current terminal size
        terminal = self.parent_window.get_current_terminal()
        if not terminal:
            print("No terminal widget found")
            return
            
        width = terminal.get_allocated_width()
        height = terminal.get_allocated_height()
        
        if width <= 0 or height <= 0:
            print(f"Invalid terminal size: {width}x{height}")
            return
            
        # Resize image based on fit mode
        img_width, img_height = self.current_image.size
        if self.settings["fit_mode"] == "cover":
            ratio = max(width/img_width, height/img_height)
            new_size = (int(img_width * ratio), int(img_height * ratio))
        elif self.settings["fit_mode"] == "contain":
            ratio = min(width/img_width, height/img_height)
            new_size = (int(img_width * ratio), int(img_height * ratio))
        else:  # fill
            new_size = (width, height)
            
        resized = self.current_image.resize(new_size, Image.Resampling.LANCZOS)
        
        # Apply effects
        if self.settings["blur"] > 0:
            resized = resized.filter(Image.BLUR)
            
        # Adjust brightness
        if not self.settings["auto_adjust"]:
            enhancer = ImageEnhance.Brightness(resized)
            resized = enhancer.enhance(self.settings["brightness"])
            
        # Convert to RGBA and adjust opacity
        if resized.mode != 'RGBA':
            resized = resized.convert('RGBA')
            
        # Create a new image with adjusted opacity
        alpha = int(self.settings["opacity"] * 255)
        resized.putalpha(alpha)
        
        # Convert to bytes and create a copy to make it writable
        img_data = bytearray(resized.tobytes())
        
        # Convert to Cairo surface
        surface = cairo.ImageSurface.create_for_data(
            img_data,
            cairo.FORMAT_ARGB32,
            resized.width,
            resized.height
        )
        
        # Store the surface for the terminal
        self.terminal_widgets[terminal] = surface
        
        # Trigger redraw
        terminal.queue_draw()
        
    def start_animation(self):
        """Start the animation thread for GIFs"""
        if self.settings["type"] != "gif":
            return
            
        self.animation_running = True
        self.animation_thread = threading.Thread(target=self._animation_loop)
        self.animation_thread.daemon = True
        self.animation_thread.start()
        
    def stop_animation(self):
        """Stop the animation thread"""
        self.animation_running = False
        if self.animation_thread:
            self.animation_thread.join()
            
    def restart_animation(self):
        """Restart the animation with new speed"""
        self.stop_animation()
        self.start_animation()
        
    def _animation_loop(self):
        """Animation loop for GIFs"""
        while self.animation_running:
            try:
                self.current_image.seek(self.current_frame)
                self.current_frame = (self.current_frame + 1) % self.current_image.n_frames
                self.update_wallpaper()
                time.sleep(self.current_image.info['duration'] / 1000 / self.settings["animation_speed"])
            except Exception as e:
                print(f"Animation error: {e}")
                break
                
    def clear_wallpaper(self):
        """Clear the wallpaper"""
        self.terminal_widgets.clear()
        self.current_image = None
        self.current_frame = None
        
    def load_settings(self):
        """Load plugin settings from the plugin manager"""
        try:
            plugin_manager = self.parent_window.plugin_manager
            if plugin_manager:
                saved_settings = plugin_manager.get_plugin_settings(self.name)
                if saved_settings:
                    # Update only existing settings
                    for key, value in saved_settings.items():
                        if key in self.settings:
                            self.settings[key] = value
                    print(f"Loaded settings for {self.name}: {self.settings}")
        except Exception as e:
            print(f"Error loading settings for {self.name}: {e}")
            
    def save_settings(self):
        """Save plugin settings to the plugin manager"""
        try:
            plugin_manager = self.parent_window.plugin_manager
            if plugin_manager:
                plugin_manager.update_plugin_settings(self.name, self.settings)
                print(f"Saved settings for {self.name}: {self.settings}")
        except Exception as e:
            print(f"Error saving settings for {self.name}: {e}") 