import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Vte', '2.91')
from gi.repository import Gtk, Vte, GLib
import os
import json
import paramiko
from pathlib import Path
from modules.plugins import Plugin

class SSHManagerPlugin(Plugin):
    def __init__(self):
        super().__init__()
        self.name = "SSH Manager"
        self.description = "Seamless SSH connection management with saved hosts and secure key handling"
        self.version = "1.0"
        self.author = "HyxTerminal Team"
        self.categories = ["Network", "Security"]
        self.tags = ["ssh", "remote", "connection", "security"]
        
        # Default settings
        self.settings = {
            "hosts": {},
            "default_port": 22,
            "timeout": 10,
            "keepalive": 60,
            "use_ssh_agent": True,
            "default_terminal_profile": "SSH Profile"
        }
        
        # Load SSH config and known hosts
        self.ssh_config = self._load_ssh_config()
        self.known_hosts = self._load_known_hosts()
        
    def on_enable(self, parent_window):
        """Enable SSH Manager features"""
        try:
            # Add SSH menu to the menubar
            self._add_ssh_menu(parent_window)
            return True
        except Exception as e:
            print(f"Error enabling SSH Manager: {e}")
            return False
            
    def on_disable(self, parent_window):
        """Disable SSH Manager features"""
        try:
            # Remove SSH menu from menubar
            self._remove_ssh_menu(parent_window)
            return True
        except Exception as e:
            print(f"Error disabling SSH Manager: {e}")
            return False
            
    def get_settings_widget(self):
        """Create settings widget for SSH Manager"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_start(10)
        box.set_margin_end(10)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        
        # SSH Agent integration
        agent_switch = Gtk.Switch()
        agent_switch.set_active(self.settings["use_ssh_agent"])
        agent_switch.connect("notify::active", self._on_agent_switch_toggled)
        
        agent_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        agent_label = Gtk.Label(label="Use SSH Agent")
        agent_box.pack_start(agent_label, True, True, 0)
        agent_box.pack_end(agent_switch, False, False, 0)
        box.pack_start(agent_box, False, False, 0)
        
        # Default port
        port_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        port_label = Gtk.Label(label="Default Port:")
        port_spin = Gtk.SpinButton.new_with_range(1, 65535, 1)
        port_spin.set_value(self.settings["default_port"])
        port_spin.connect("value-changed", self._on_port_changed)
        
        port_box.pack_start(port_label, True, True, 0)
        port_box.pack_end(port_spin, False, False, 0)
        box.pack_start(port_box, False, False, 0)
        
        # Connection timeout
        timeout_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        timeout_label = Gtk.Label(label="Connection Timeout (seconds):")
        timeout_spin = Gtk.SpinButton.new_with_range(1, 300, 1)
        timeout_spin.set_value(self.settings["timeout"])
        timeout_spin.connect("value-changed", self._on_timeout_changed)
        
        timeout_box.pack_start(timeout_label, True, True, 0)
        timeout_box.pack_end(timeout_spin, False, False, 0)
        box.pack_start(timeout_box, False, False, 0)
        
        # Keepalive interval
        keepalive_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        keepalive_label = Gtk.Label(label="Keepalive Interval (seconds):")
        keepalive_spin = Gtk.SpinButton.new_with_range(0, 3600, 10)
        keepalive_spin.set_value(self.settings["keepalive"])
        keepalive_spin.connect("value-changed", self._on_keepalive_changed)
        
        keepalive_box.pack_start(keepalive_label, True, True, 0)
        keepalive_box.pack_end(keepalive_spin, False, False, 0)
        box.pack_start(keepalive_box, False, False, 0)
        
        # Saved hosts management
        hosts_frame = Gtk.Frame(label="Saved Hosts")
        hosts_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        hosts_box.set_margin_start(10)
        hosts_box.set_margin_end(10)
        hosts_box.set_margin_top(10)
        hosts_box.set_margin_bottom(10)
        
        # Hosts list
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_min_content_height(200)
        
        self.hosts_store = Gtk.ListStore(str, str, int, str)  # Name, Host, Port, Username
        treeview = Gtk.TreeView(model=self.hosts_store)
        
        # Add columns
        renderer_text = Gtk.CellRendererText()
        column_name = Gtk.TreeViewColumn("Name", renderer_text, text=0)
        treeview.append_column(column_name)
        
        renderer_text = Gtk.CellRendererText()
        column_host = Gtk.TreeViewColumn("Host", renderer_text, text=1)
        treeview.append_column(column_host)
        
        renderer_text = Gtk.CellRendererText()
        column_port = Gtk.TreeViewColumn("Port", renderer_text, text=2)
        treeview.append_column(column_port)
        
        renderer_text = Gtk.CellRendererText()
        column_user = Gtk.TreeViewColumn("Username", renderer_text, text=3)
        treeview.append_column(column_user)
        
        scrolled.add(treeview)
        hosts_box.pack_start(scrolled, True, True, 0)
        
        # Buttons for host management
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        
        add_button = Gtk.Button(label="Add Host")
        add_button.connect("clicked", self._on_add_host_clicked)
        button_box.pack_start(add_button, True, True, 0)
        
        edit_button = Gtk.Button(label="Edit Host")
        edit_button.connect("clicked", lambda w: self._on_edit_host_clicked(w, treeview))
        button_box.pack_start(edit_button, True, True, 0)
        
        remove_button = Gtk.Button(label="Remove Host")
        remove_button.connect("clicked", lambda w: self._on_remove_host_clicked(w, treeview))
        button_box.pack_start(remove_button, True, True, 0)
        
        hosts_box.pack_start(button_box, False, False, 0)
        hosts_frame.add(hosts_box)
        box.pack_start(hosts_frame, True, True, 0)
        
        # Load saved hosts
        self._load_hosts_to_store()
        
        return box
        
    def _add_ssh_menu(self, parent_window):
        """Add SSH menu to the menubar"""
        menubar = self._get_menubar(parent_window)
        if not menubar:
            return
            
        # Create SSH menu
        ssh_menu = Gtk.MenuItem(label="SSH")
        ssh_submenu = Gtk.Menu()
        ssh_menu.set_submenu(ssh_submenu)
        
        # Quick Connect
        quick_connect = Gtk.MenuItem(label="Quick Connect...")
        quick_connect.connect("activate", self._on_quick_connect_activated, parent_window)
        ssh_submenu.append(quick_connect)
        
        # Separator
        ssh_submenu.append(Gtk.SeparatorMenuItem())
        
        # Saved Hosts submenu
        saved_hosts = Gtk.MenuItem(label="Saved Hosts")
        hosts_submenu = Gtk.Menu()
        saved_hosts.set_submenu(hosts_submenu)
        
        # Add saved hosts
        for name, details in self.settings["hosts"].items():
            # Create a copy of details for this specific connection
            connection_details = details.copy()
            # Store name as well for display purposes
            connection_details["name"] = name
            
            host_item = Gtk.MenuItem(label=name)
            # Use a data attribute to store connection details
            host_item.connect("activate", self._on_saved_host_activated, parent_window)
            # Store connection details in a property
            host_item.connection_details = connection_details
            hosts_submenu.append(host_item)
            
        ssh_submenu.append(saved_hosts)
        
        # Manage Hosts
        manage_hosts = Gtk.MenuItem(label="Manage Hosts...")
        manage_hosts.connect("activate", self._on_manage_hosts_activated, parent_window)
        ssh_submenu.append(manage_hosts)
        
        # Add menu to menubar
        menubar.append(ssh_menu)
        menubar.show_all()
        
    def _remove_ssh_menu(self, parent_window):
        """Remove SSH menu from menubar"""
        menubar = self._get_menubar(parent_window)
        if not menubar:
            return
            
        for item in menubar.get_children():
            if isinstance(item, Gtk.MenuItem) and item.get_label() == "SSH":
                menubar.remove(item)
                break
                
    def _get_menubar(self, parent_window):
        """Get the menubar widget from parent window"""
        for child in parent_window.get_children():
            if isinstance(child, Gtk.Box):
                for box_child in child.get_children():
                    if isinstance(box_child, Gtk.MenuBar):
                        return box_child
        return None
        
    def _show_quick_connect_dialog(self, parent_window):
        """Show quick connect dialog"""
        dialog = Gtk.Dialog(
            title="Quick Connect",
            parent=parent_window,
            flags=0
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_CONNECT, Gtk.ResponseType.OK
        )
        
        box = dialog.get_content_area()
        box.set_spacing(6)
        box.set_margin_start(10)
        box.set_margin_end(10)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        
        # Host entry
        host_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        host_label = Gtk.Label(label="Host:")
        host_entry = Gtk.Entry()
        host_box.pack_start(host_label, False, False, 0)
        host_box.pack_start(host_entry, True, True, 0)
        box.pack_start(host_box, False, False, 0)
        
        # Port entry
        port_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        port_label = Gtk.Label(label="Port:")
        port_spin = Gtk.SpinButton.new_with_range(1, 65535, 1)
        port_spin.set_value(self.settings["default_port"])
        port_box.pack_start(port_label, False, False, 0)
        port_box.pack_start(port_spin, True, True, 0)
        box.pack_start(port_box, False, False, 0)
        
        # Username entry
        user_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        user_label = Gtk.Label(label="Username:")
        user_entry = Gtk.Entry()
        user_entry.set_text(os.getenv("USER", ""))
        user_box.pack_start(user_label, False, False, 0)
        user_box.pack_start(user_entry, True, True, 0)
        box.pack_start(user_box, False, False, 0)
        
        # Identity file chooser
        identity_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        identity_label = Gtk.Label(label="Identity File:")
        identity_chooser = Gtk.FileChooserButton(title="Select Identity File")
        identity_chooser.set_current_folder(str(Path.home() / ".ssh"))
        identity_box.pack_start(identity_label, False, False, 0)
        identity_box.pack_start(identity_chooser, True, True, 0)
        box.pack_start(identity_box, False, False, 0)
        
        dialog.show_all()
        response = dialog.run()
        
        if response == Gtk.ResponseType.OK:
            host = host_entry.get_text()
            port = int(port_spin.get_value())
            username = user_entry.get_text()
            identity_file = identity_chooser.get_filename()
            
            # Create connection details
            details = {
                "host": host,
                "port": port,
                "username": username,
                "identity_file": identity_file
            }
            
            # Connect
            self._connect_to_host(parent_window, details)
            
        dialog.destroy()
        
    def _connect_to_host(self, parent_window, details):
        """Connect to SSH host"""
        try:
            # Create SSH client
            client = paramiko.SSHClient()
            client.load_system_host_keys()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Connect
            client.connect(
                hostname=details["host"],
                port=details["port"],
                username=details["username"],
                key_filename=details.get("identity_file"),
                timeout=self.settings["timeout"],
                banner_timeout=self.settings["timeout"]
            )
            
            # Create new terminal
            terminal = Vte.Terminal()
            
            # Create SSH command
            ssh_cmd = f"ssh {details['username']}@{details['host']} -p {details['port']}"
            if details.get("identity_file"):
                ssh_cmd += f" -i {details['identity_file']}"
                
            # Spawn the process without the DO_NOT_REAP_CHILD flag
            terminal.spawn_sync(
                Vte.PtyFlags.DEFAULT,
                None,
                ["/bin/sh", "-c", ssh_cmd],
                [],
                0,  # No spawn flags to avoid VTE warning
                None,
                None,
            )
            
            # Add terminal to window
            scrolled = Gtk.ScrolledWindow()
            scrolled.add(terminal)
            
            # Create new tab with terminal
            notebook = self._get_notebook(parent_window)
            if notebook:
                page_num = notebook.append_page(
                    scrolled,
                    Gtk.Label(label=f"SSH: {details['host']}")
                )
                notebook.set_current_page(page_num)
                notebook.show_all()
                
        except Exception as e:
            dialog = Gtk.MessageDialog(
                transient_for=parent_window,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Connection Error"
            )
            dialog.format_secondary_text(str(e))
            dialog.run()
            dialog.destroy()
            
    def _get_notebook(self, parent_window):
        """Get the notebook widget from parent window"""
        for child in parent_window.get_children():
            if isinstance(child, Gtk.Notebook):
                return child
        return None
        
    def _load_ssh_config(self):
        """Load SSH config file"""
        config_file = Path.home() / ".ssh" / "config"
        if config_file.exists():
            return paramiko.SSHConfig.from_file(open(config_file))
        return paramiko.SSHConfig()
        
    def _load_known_hosts(self):
        """Load known hosts file"""
        known_hosts_file = Path.home() / ".ssh" / "known_hosts"
        if known_hosts_file.exists():
            return paramiko.HostKeys(str(known_hosts_file))
        return paramiko.HostKeys()
        
    def _load_hosts_to_store(self):
        """Load saved hosts to list store"""
        self.hosts_store.clear()
        for name, details in self.settings["hosts"].items():
            self.hosts_store.append([
                name,
                details["host"],
                details["port"],
                details["username"]
            ])
            
    def _on_agent_switch_toggled(self, switch, gparam):
        self.settings["use_ssh_agent"] = switch.get_active()
        
    def _on_port_changed(self, spin):
        self.settings["default_port"] = spin.get_value_as_int()
        
    def _on_timeout_changed(self, spin):
        self.settings["timeout"] = spin.get_value_as_int()
        
    def _on_keepalive_changed(self, spin):
        self.settings["keepalive"] = spin.get_value_as_int()
        
    def _on_add_host_clicked(self, button):
        """Show dialog to add new host"""
        dialog = Gtk.Dialog(
            title="Add Host",
            parent=button.get_toplevel(),
            flags=0
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_ADD, Gtk.ResponseType.OK
        )
        
        box = dialog.get_content_area()
        box.set_spacing(6)
        box.set_margin_start(10)
        box.set_margin_end(10)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        
        # Name entry
        name_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        name_label = Gtk.Label(label="Name:")
        name_entry = Gtk.Entry()
        name_box.pack_start(name_label, False, False, 0)
        name_box.pack_start(name_entry, True, True, 0)
        box.pack_start(name_box, False, False, 0)
        
        # Host entry
        host_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        host_label = Gtk.Label(label="Host:")
        host_entry = Gtk.Entry()
        host_box.pack_start(host_label, False, False, 0)
        host_box.pack_start(host_entry, True, True, 0)
        box.pack_start(host_box, False, False, 0)
        
        # Port entry
        port_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        port_label = Gtk.Label(label="Port:")
        port_spin = Gtk.SpinButton.new_with_range(1, 65535, 1)
        port_spin.set_value(self.settings["default_port"])
        port_box.pack_start(port_label, False, False, 0)
        port_box.pack_start(port_spin, True, True, 0)
        box.pack_start(port_box, False, False, 0)
        
        # Username entry
        user_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        user_label = Gtk.Label(label="Username:")
        user_entry = Gtk.Entry()
        user_entry.set_text(os.getenv("USER", ""))
        user_box.pack_start(user_label, False, False, 0)
        user_box.pack_start(user_entry, True, True, 0)
        box.pack_start(user_box, False, False, 0)
        
        dialog.show_all()
        response = dialog.run()
        
        if response == Gtk.ResponseType.OK:
            name = name_entry.get_text()
            host = host_entry.get_text()
            port = int(port_spin.get_value())
            username = user_entry.get_text()
            
            if name and host and username:
                self.settings["hosts"][name] = {
                    "host": host,
                    "port": port,
                    "username": username
                }
                self.hosts_store.append([name, host, port, username])
                
        dialog.destroy()
        
    def _on_edit_host_clicked(self, button, treeview):
        """Show dialog to edit selected host"""
        selection = treeview.get_selection()
        model, iter = selection.get_selected()
        if not iter:
            return
            
        name = model[iter][0]
        host = model[iter][1]
        port = model[iter][2]
        username = model[iter][3]
        
        dialog = Gtk.Dialog(
            title="Edit Host",
            parent=button.get_toplevel(),
            flags=0
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE, Gtk.ResponseType.OK
        )
        
        box = dialog.get_content_area()
        box.set_spacing(6)
        box.set_margin_start(10)
        box.set_margin_end(10)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        
        # Name entry
        name_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        name_label = Gtk.Label(label="Name:")
        name_entry = Gtk.Entry()
        name_entry.set_text(name)
        name_box.pack_start(name_label, False, False, 0)
        name_box.pack_start(name_entry, True, True, 0)
        box.pack_start(name_box, False, False, 0)
        
        # Host entry
        host_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        host_label = Gtk.Label(label="Host:")
        host_entry = Gtk.Entry()
        host_entry.set_text(host)
        host_box.pack_start(host_label, False, False, 0)
        host_box.pack_start(host_entry, True, True, 0)
        box.pack_start(host_box, False, False, 0)
        
        # Port entry
        port_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        port_label = Gtk.Label(label="Port:")
        port_spin = Gtk.SpinButton.new_with_range(1, 65535, 1)
        port_spin.set_value(port)
        port_box.pack_start(port_label, False, False, 0)
        port_box.pack_start(port_spin, True, True, 0)
        box.pack_start(port_box, False, False, 0)
        
        # Username entry
        user_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        user_label = Gtk.Label(label="Username:")
        user_entry = Gtk.Entry()
        user_entry.set_text(username)
        user_box.pack_start(user_label, False, False, 0)
        user_box.pack_start(user_entry, True, True, 0)
        box.pack_start(user_box, False, False, 0)
        
        dialog.show_all()
        response = dialog.run()
        
        if response == Gtk.ResponseType.OK:
            new_name = name_entry.get_text()
            new_host = host_entry.get_text()
            new_port = int(port_spin.get_value())
            new_username = user_entry.get_text()
            
            if new_name and new_host and new_username:
                # Update settings
                if new_name != name:
                    del self.settings["hosts"][name]
                self.settings["hosts"][new_name] = {
                    "host": new_host,
                    "port": new_port,
                    "username": new_username
                }
                
                # Update list store
                model[iter][0] = new_name
                model[iter][1] = new_host
                model[iter][2] = new_port
                model[iter][3] = new_username
                
        dialog.destroy()
        
    def _on_remove_host_clicked(self, button, treeview):
        """Remove selected host"""
        selection = treeview.get_selection()
        model, iter = selection.get_selected()
        if not iter:
            return
            
        name = model[iter][0]
        
        dialog = Gtk.MessageDialog(
            transient_for=button.get_toplevel(),
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=f"Remove host '{name}'?"
        )
        
        response = dialog.run()
        dialog.destroy()
        
        if response == Gtk.ResponseType.YES:
            del self.settings["hosts"][name]
            model.remove(iter)
            
    def _on_quick_connect_activated(self, widget, parent_window):
        """Handler for quick connect menu item activation"""
        self._show_quick_connect_dialog(parent_window)
        
    def _on_saved_host_activated(self, widget, parent_window):
        """Handler for saved host menu item activation"""
        # Get connection details from the widget property
        connection_details = getattr(widget, "connection_details", None)
        if connection_details:
            self._connect_to_host(parent_window, connection_details)
        else:
            dialog = Gtk.MessageDialog(
                transient_for=parent_window,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Connection Error"
            )
            dialog.format_secondary_text("Could not retrieve connection details")
            dialog.run()
            dialog.destroy()
            
    def _on_manage_hosts_activated(self, widget, parent_window):
        """Handler for manage hosts menu item activation"""
        self._show_hosts_manager(parent_window)
        
    def _show_hosts_manager(self, parent_window):
        """Show hosts manager dialog"""
        # We'll reuse the settings widget for host management
        dialog = Gtk.Dialog(
            title="SSH Hosts Manager",
            parent=parent_window,
            flags=0
        )
        dialog.add_buttons(
            Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE
        )
        dialog.set_default_size(600, 400)
        
        # Create content box
        box = dialog.get_content_area()
        box.set_spacing(6)
        box.set_margin_start(10)
        box.set_margin_end(10)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        
        # Add settings widget with host management
        settings_widget = self.get_settings_widget()
        box.pack_start(settings_widget, True, True, 0)
        
        dialog.show_all()
        dialog.run()
        dialog.destroy() 