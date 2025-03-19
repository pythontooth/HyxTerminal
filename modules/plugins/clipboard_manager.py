import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk
from modules.plugins import Plugin

class ClipboardManagerPlugin(Plugin):
    def __init__(self):
        super().__init__()
        self.name = "Clipboard Manager"
        self.description = "Enhanced clipboard with history and search functionality"
        self.version = "1.0"
        self.author = "HyxTerminal Team"
        self.categories = ["Terminal", "Productivity"]
        self.tags = ["clipboard", "history", "search"]
        self.settings = {
            "max_history": 100,
            "auto_paste": False,
            "show_timestamps": True
        }
        self.history = []
        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        self.clipboard.connect("owner-change", self.on_clipboard_change)
        
    def on_enable(self, parent_window):
        """Enable clipboard manager"""
        self.parent_window = parent_window
        
    def on_disable(self, parent_window):
        """Disable clipboard manager"""
        self.clipboard.disconnect_by_func(self.on_clipboard_change)
        
    def on_clipboard_change(self, clipboard, event):
        """Handle clipboard changes"""
        if clipboard.wait_is_text_available():
            text = clipboard.wait_for_text()
            if text and text not in self.history:
                self.history.insert(0, text)
                if len(self.history) > self.settings["max_history"]:
                    self.history.pop()
                    
    def get_settings_widget(self):
        """Create settings widget for the plugin"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_start(10)
        box.set_margin_end(10)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        
        # Max history setting
        history_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        history_label = Gtk.Label(label="Maximum history items:")
        history_spinner = Gtk.SpinButton.new_with_range(10, 1000, 10)
        history_spinner.set_value(self.settings["max_history"])
        history_box.pack_start(history_label, False, False, 0)
        history_box.pack_start(history_spinner, True, True, 0)
        box.pack_start(history_box, False, False, 0)
        
        # Auto-paste setting
        auto_paste = Gtk.CheckButton(label="Auto-paste on selection")
        auto_paste.set_active(self.settings["auto_paste"])
        box.pack_start(auto_paste, False, False, 0)
        
        # Timestamps setting
        timestamps = Gtk.CheckButton(label="Show timestamps in history")
        timestamps.set_active(self.settings["show_timestamps"])
        box.pack_start(timestamps, False, False, 0)
        
        # Connect signals
        def on_history_changed(spinner):
            self.settings["max_history"] = spinner.get_value_as_int()
            # Trim history if needed
            while len(self.history) > self.settings["max_history"]:
                self.history.pop()
                
        def on_auto_paste_changed(button):
            self.settings["auto_paste"] = button.get_active()
            
        def on_timestamps_changed(button):
            self.settings["show_timestamps"] = button.get_active()
            
        history_spinner.connect("value-changed", on_history_changed)
        auto_paste.connect("toggled", on_auto_paste_changed)
        timestamps.connect("toggled", on_timestamps_changed)
        
        return box
        
    def show_clipboard_dialog(self):
        """Show clipboard manager dialog"""
        dialog = Gtk.Dialog(
            title="Clipboard Manager",
            parent=self.parent_window,
            flags=0
        )
        dialog.add_buttons(
            Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE,
            "Clear History", Gtk.ResponseType.REJECT
        )
        dialog.set_default_size(400, 300)
        
        box = dialog.get_content_area()
        box.set_spacing(6)
        box.set_margin_start(10)
        box.set_margin_end(10)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        
        # Create search entry
        search_entry = Gtk.SearchEntry()
        search_entry.set_placeholder_text("Search clipboard history...")
        box.pack_start(search_entry, False, False, 0)
        
        # Create list store
        store = Gtk.ListStore(str)
        for item in self.history:
            store.append([item])
            
        # Create tree view
        treeview = Gtk.TreeView(model=store)
        treeview.set_headers_visible(False)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Content", renderer, text=0)
        treeview.append_column(column)
        
        # Add tree view to scrolled window
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.add(treeview)
        box.pack_start(scrolled, True, True, 0)
        
        # Add "Paste" button
        paste_button = Gtk.Button(label="Paste Selected")
        paste_button.set_sensitive(False)
        box.pack_start(paste_button, False, False, 0)
        
        # Handle selection changes
        selection = treeview.get_selection()
        selection.connect("changed", lambda s: paste_button.set_sensitive(True))
        
        # Handle paste button click
        def on_paste_clicked(button):
            model, treeiter = selection.get_selected()
            if treeiter:
                text = model[treeiter][0]
                terminal = self.parent_window.get_current_terminal()
                if terminal:
                    terminal.feed_child((text + "\n").encode())
                dialog.destroy()
                
        paste_button.connect("clicked", on_paste_clicked)
        
        # Handle double-click on item
        def on_row_activated(view, path, column):
            treeiter = store.get_iter(path)
            text = store[treeiter][0]
            terminal = self.parent_window.get_current_terminal()
            if terminal:
                terminal.feed_child((text + "\n").encode())
            dialog.destroy()
            
        treeview.connect("row-activated", on_row_activated)
        
        # Handle search
        def filter_items(entry):
            search_text = entry.get_text().lower()
            store.clear()
            
            for item in self.history:
                if search_text in item.lower():
                    store.append([item])
                    
        search_entry.connect("search-changed", filter_items)
        
        dialog.show_all()
        response = dialog.run()
        
        if response == Gtk.ResponseType.REJECT:
            # Clear history
            self.history.clear()
            
        dialog.destroy() 