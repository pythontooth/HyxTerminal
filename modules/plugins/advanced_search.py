import gi
import re
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk
from modules.plugins import Plugin

class AdvancedSearchPlugin(Plugin):
    def __init__(self):
        super().__init__()
        self.name = "Advanced Search"
        self.description = "Regex-based terminal search with highlighting and navigation"
        self.version = "1.0"
        self.author = "HyxTerminal Team"
        self.categories = ["Terminal", "Search"]
        self.tags = ["search", "regex", "highlight"]
        self.settings = {
            "case_sensitive": False,
            "whole_word": False,
            "highlight_color": "#FFD700",
            "max_results": 100
        }
        self.current_search = None
        self.search_results = []
        self.current_result = -1
        
    def on_enable(self, parent_window):
        """Enable advanced search"""
        self.parent_window = parent_window
        
    def on_disable(self, parent_window):
        """Disable advanced search"""
        self.clear_search()
        
    def get_settings_widget(self):
        """Create settings widget for the plugin"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_start(10)
        box.set_margin_end(10)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        
        # Case sensitivity setting
        case_check = Gtk.CheckButton(label="Case sensitive search")
        case_check.set_active(self.settings["case_sensitive"])
        box.pack_start(case_check, False, False, 0)
        
        # Whole word setting
        whole_word = Gtk.CheckButton(label="Match whole words only")
        whole_word.set_active(self.settings["whole_word"])
        box.pack_start(whole_word, False, False, 0)
        
        # Highlight color setting
        color_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        color_label = Gtk.Label(label="Highlight color:")
        color_button = Gtk.ColorButton()
        color_button.set_rgba(Gdk.RGBA())
        color_button.set_use_alpha(False)
        color_box.pack_start(color_label, False, False, 0)
        color_box.pack_start(color_button, True, True, 0)
        box.pack_start(color_box, False, False, 0)
        
        # Max results setting
        results_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        results_label = Gtk.Label(label="Maximum results:")
        results_spinner = Gtk.SpinButton.new_with_range(10, 1000, 10)
        results_spinner.set_value(self.settings["max_results"])
        results_box.pack_start(results_label, False, False, 0)
        results_box.pack_start(results_spinner, True, True, 0)
        box.pack_start(results_box, False, False, 0)
        
        # Connect signals
        def on_case_changed(button):
            self.settings["case_sensitive"] = button.get_active()
            if self.current_search:
                self.perform_search(self.current_search)
                
        def on_whole_word_changed(button):
            self.settings["whole_word"] = button.get_active()
            if self.current_search:
                self.perform_search(self.current_search)
                
        def on_color_changed(button):
            color = button.get_rgba()
            self.settings["highlight_color"] = f"#{int(color.red*255):02x}{int(color.green*255):02x}{int(color.blue*255):02x}"
            if self.current_search:
                self.perform_search(self.current_search)
                
        def on_results_changed(spinner):
            self.settings["max_results"] = spinner.get_value_as_int()
            if self.current_search:
                self.perform_search(self.current_search)
                
        case_check.connect("toggled", on_case_changed)
        whole_word.connect("toggled", on_whole_word_changed)
        color_button.connect("color-set", on_color_changed)
        results_spinner.connect("value-changed", on_results_changed)
        
        return box
        
    def show_search_dialog(self):
        """Show advanced search dialog"""
        dialog = Gtk.Dialog(
            title="Advanced Search",
            parent=self.parent_window,
            flags=0
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_FIND, Gtk.ResponseType.ACCEPT
        )
        dialog.set_default_size(400, 300)
        
        box = dialog.get_content_area()
        box.set_spacing(6)
        box.set_margin_start(10)
        box.set_margin_end(10)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        
        # Search entry
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        search_label = Gtk.Label(label="Search:")
        search_entry = Gtk.SearchEntry()
        search_entry.set_placeholder_text("Enter search pattern...")
        search_box.pack_start(search_label, False, False, 0)
        search_box.pack_start(search_entry, True, True, 0)
        box.pack_start(search_box, False, False, 0)
        
        # Results list
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        
        # Create list store
        store = Gtk.ListStore(str, str)  # Line number, Content
        treeview = Gtk.TreeView(model=store)
        treeview.set_headers_visible(False)
        
        # Add columns
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Content", renderer, text=1)
        treeview.append_column(column)
        
        scrolled.add(treeview)
        box.pack_start(scrolled, True, True, 0)
        
        # Navigation buttons
        nav_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        
        prev_button = Gtk.Button(label="Previous")
        prev_button.set_sensitive(False)
        
        next_button = Gtk.Button(label="Next")
        next_button.set_sensitive(False)
        
        nav_box.pack_start(prev_button, False, False, 0)
        nav_box.pack_start(next_button, False, False, 0)
        box.pack_start(nav_box, False, False, 0)
        
        # Handle search
        def on_search_changed(entry):
            pattern = entry.get_text()
            if pattern:
                self.perform_search(pattern)
            else:
                self.clear_search()
                
        def on_result_selected(view, path, column):
            model = view.get_model()
            iter = model.get_iter(path)
            line_num = int(model.get_value(iter, 0))
            self.jump_to_line(line_num)
            
        def on_prev_clicked(button):
            if self.current_result > 0:
                self.current_result -= 1
                self.jump_to_line(self.search_results[self.current_result])
                
        def on_next_clicked(button):
            if self.current_result < len(self.search_results) - 1:
                self.current_result += 1
                self.jump_to_line(self.search_results[self.current_result])
                
        search_entry.connect("search-changed", on_search_changed)
        treeview.connect("row-activated", on_result_selected)
        prev_button.connect("clicked", on_prev_clicked)
        next_button.connect("clicked", on_next_clicked)
        
        dialog.show_all()
        response = dialog.run()
        
        if response == Gtk.ResponseType.ACCEPT:
            # Keep the search active
            self.current_search = search_entry.get_text()
        else:
            # Clear the search
            self.clear_search()
            
        dialog.destroy()
        
    def perform_search(self, pattern):
        """Perform the search with the given pattern"""
        self.clear_search()
        self.current_search = pattern
        
        # Build regex pattern
        flags = 0 if self.settings["case_sensitive"] else re.IGNORECASE
        if self.settings["whole_word"]:
            pattern = r"\b" + re.escape(pattern) + r"\b"
            
        try:
            regex = re.compile(pattern, flags)
        except re.error:
            return
            
        # Get current terminal
        terminal = self.parent_window.get_current_terminal()
        if not terminal:
            return
            
        # Get terminal content
        content = terminal.get_text()
        lines = content.split("\n")
        
        # Find matches
        for i, line in enumerate(lines):
            if len(self.search_results) >= self.settings["max_results"]:
                break
                
            if regex.search(line):
                self.search_results.append(i)
                
        # Update UI
        self.current_result = 0 if self.search_results else -1
        if self.current_result >= 0:
            self.jump_to_line(self.search_results[self.current_result])
            
    def clear_search(self):
        """Clear the current search"""
        self.current_search = None
        self.search_results = []
        self.current_result = -1
        
    def jump_to_line(self, line_num):
        """Jump to the specified line in the terminal"""
        terminal = self.parent_window.get_current_terminal()
        if not terminal:
            return
            
        # Scroll to line
        terminal.scroll_to_line(line_num)
        
        # Highlight the line
        # Note: This is a simplified version. In a real implementation,
        # you would need to handle the actual highlighting of text
        # based on the terminal's capabilities 