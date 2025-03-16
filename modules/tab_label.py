import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

class TabLabel(Gtk.Box):
    def __init__(self, title, tab, notebook):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.notebook = notebook
        self.tab = tab
        self.is_editing = False
        
        # Create label container (for easier widget swapping)
        self.label_container = Gtk.Box()
        
        # Create label
        self.label = Gtk.Label(label=title)
        self.label_container.add(self.label)
        
        # Create close button
        close_button = Gtk.Button()
        close_button.set_relief(Gtk.ReliefStyle.NONE)
        close_button.set_focus_on_click(False)
        close_button.add(Gtk.Image.new_from_icon_name("window-close", Gtk.IconSize.MENU))
        close_button.connect('clicked', self.on_close_clicked)
        
        # Add double-click detection to the label container
        event_box = Gtk.EventBox()
        event_box.add(self.label_container)
        event_box.connect('button-press-event', self.on_tab_clicked)
        event_box.set_above_child(False)
        
        # Pack widgets
        self.pack_start(event_box, True, True, 0)
        self.pack_start(close_button, False, False, 0)
        self.show_all()

    def on_close_clicked(self, button):
        if not self.is_editing:  # Prevent closing while editing
            page_num = self.notebook.page_num(self.tab)
            if page_num != -1:
                self.notebook.remove_page(page_num)

    def on_tab_clicked(self, widget, event):
        if event.type == Gdk.EventType._2BUTTON_PRESS and not self.is_editing:
            self.start_editing()
            return True
        return False

    def start_editing(self):
        self.is_editing = True
        # Create entry widget
        entry = Gtk.Entry()
        entry.set_text(self.label.get_text())
        entry.connect('activate', self.finish_editing)
        entry.connect('focus-out-event', self.finish_editing)
        entry.connect('key-press-event', self.on_entry_key_press)
        
        # Safely swap widgets
        self.label.hide()
        self.label_container.add(entry)
        entry.show()
        entry.grab_focus()

    def finish_editing(self, widget, event=None):
        if not self.is_editing:
            return False
            
        try:
            new_text = widget.get_text().strip()
            if new_text:
                self.label.set_text(new_text)
            
            # Safely restore label
            widget.hide()
            self.label_container.remove(widget)
            self.label.show()
            
        except Exception as e:
            print(f"Error while finishing edit: {e}")
        
        finally:
            self.is_editing = False
            
        return False

    def on_entry_key_press(self, widget, event):
        # Handle Escape key to cancel editing
        if event.keyval == Gdk.KEY_Escape:
            self.is_editing = False
            widget.hide()
            self.label_container.remove(widget)
            self.label.show()
            return True
        return False
