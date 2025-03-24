import gi
import os
import json
import requests
import threading
from pathlib import Path
from dotenv import load_dotenv

gi.require_version('Gtk', '3.0')
gi.require_version('Vte', '2.91')
from gi.repository import Gtk, Gdk, GLib, Vte, Pango

# Import Plugin class directly using a relative import
from modules.plugins import Plugin

class AICommandAgent(Plugin):
    """AI Command Agent plugin for HyxTerminal using Groq API"""
    
    def __init__(self):
        super().__init__()
        self.name = "AI Command Agent"
        self.description = "Use AI to generate terminal commands from natural language"
        self.version = "1.0"
        self.author = "HyxTerminal Team"
        self.enabled = False
        self.settings = {
            "api_key": "",
            "max_context_lines": 20,
            "model": "llama3-70b-8192"
        }
        self.categories = ["AI", "Terminal"]
        self.tags = ["AI", "command", "natural language", "assistant"]
        self.parent_window = None
        self.api_key = None
        self.load_api_key()
        
    def load_api_key(self):
        """Load API key from .env file or settings"""
        # Try to load from .env file first
        try:
            load_dotenv()
            env_key = os.getenv("GROQ_API_KEY")
            if env_key:
                self.api_key = env_key
                self.settings["api_key"] = env_key
                return
        except Exception as e:
            print(f"Error loading .env file: {e}")
            
        # Otherwise use the key from settings
        self.api_key = self.settings.get("api_key", "")
        
    def on_enable(self, parent_window):
        """Called when the plugin is enabled"""
        self.parent_window = parent_window
        
        # Register keyboard shortcut
        parent_window.connect("key-press-event", self.on_key_press)
        
        # Check if we have an API key
        if not self.api_key:
            self.show_api_key_dialog()
    
    def on_disable(self, parent_window):
        """Called when the plugin is disabled"""
        # Nothing to clean up for now
        pass
    
    def on_settings_changed(self, settings):
        """Called when plugin settings are changed"""
        self.settings.update(settings)
        self.api_key = self.settings.get("api_key", "")
    
    def on_key_press(self, widget, event):
        """Handle Ctrl+Space keyboard shortcut"""
        keyval = event.keyval
        keyval_name = Gdk.keyval_name(keyval)
        
        # Check for Ctrl+Space
        if keyval_name == "space" and event.state & Gdk.ModifierType.CONTROL_MASK:
            self.show_command_dialog()
            return True
        
        return False
    
    def get_current_terminal(self):
        """Get the current terminal from the parent window"""
        if not self.parent_window:
            return None
            
        current_page = self.parent_window.notebook.get_current_page()
        if current_page != -1:
            tab = self.parent_window.notebook.get_nth_page(current_page)
            if hasattr(tab, 'terminals') and tab.terminals:
                return tab.terminal
        return None
    
    def get_terminal_context(self, terminal):
        """Get recent terminal context as text"""
        if not terminal:
            return ""
            
        # Get terminal contents
        max_lines = self.settings.get("max_context_lines", 20)
        
        # First try using get_text()
        try:
            # This gets all the terminal content
            content = terminal.get_text(lambda *args: True)
            if isinstance(content, tuple):
                text = content[0]
            else:
                text = content
                
            # If we have content, return the last 'max_lines' lines
            if text:
                lines = text.splitlines()
                return "\n".join(lines[-max_lines:])
        except Exception as e:
            print(f"Error using get_text(): {e}")
        
        # Fall back to row-by-row approach
        try:
            # VTE doesn't have a direct API to get content, so we'll use a workaround
            # This is a simplified approach and might not work perfectly in all cases
            column_count = terminal.get_column_count()
            row_count = terminal.get_row_count()
            
            # Calculate number of rows to fetch (limited by max_lines)
            rows_to_fetch = min(max_lines, row_count)
            start_row = max(0, row_count - rows_to_fetch)
            
            context_lines = []
            for row in range(start_row, row_count):
                try:
                    # Different VTE versions may return different number of values
                    result = terminal.get_text_range(row, 0, row, column_count, lambda *args: True)
                    if isinstance(result, tuple):
                        text = result[0]  # First item is the text
                    else:
                        text = result     # Some versions just return the text directly
                    
                    if text:
                        context_lines.append(text)
                except Exception as e:
                    print(f"Error getting text from row {row}: {e}")
                    # Continue even if we can't get text from this row
                    continue
            
            return "\n".join(context_lines)
        except Exception as e:
            print(f"Failed to get terminal context: {e}")
            return "Failed to access terminal content."
    
    def show_api_key_dialog(self):
        """Show dialog to enter Groq API key"""
        dialog = Gtk.Dialog(
            title="Groq API Key",
            parent=self.parent_window,
            flags=0
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OK, Gtk.ResponseType.OK
        )
        
        box = dialog.get_content_area()
        box.set_spacing(6)
        box.set_margin_start(10)
        box.set_margin_end(10)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        
        label = Gtk.Label(label="Please enter your Groq API key:")
        box.add(label)
        
        entry = Gtk.Entry()
        entry.set_visibility(False)  # Password-style entry
        entry.set_text(self.api_key)
        box.add(entry)
        
        box.show_all()
        response = dialog.run()
        
        if response == Gtk.ResponseType.OK:
            self.api_key = entry.get_text().strip()
            self.settings["api_key"] = self.api_key
            
        dialog.destroy()
        
        # Return True if API key is set
        return bool(self.api_key)
    
    def show_command_dialog(self):
        """Show dialog to enter a natural language command"""
        terminal = self.get_current_terminal()
        if not terminal:
            dialog = Gtk.MessageDialog(
                parent=self.parent_window,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="No active terminal found"
            )
            dialog.format_secondary_text("Please make sure you have an active terminal tab open.")
            dialog.run()
            dialog.destroy()
            return
            
        # Check if API key is set
        if not self.api_key:
            if not self.show_api_key_dialog():
                return
                
        dialog = Gtk.Dialog(
            title="AI Command Builder",
            parent=self.parent_window,
            flags=0
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OK, Gtk.ResponseType.OK
        )
        dialog.set_default_size(500, 200)
        
        box = dialog.get_content_area()
        box.set_spacing(6)
        box.set_margin_start(10)
        box.set_margin_end(10)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        
        # Add description
        desc_label = Gtk.Label()
        desc_label.set_markup("<b>Describe what you want to do:</b>")
        desc_label.set_halign(Gtk.Align.START)
        box.add(desc_label)
        
        # Add text entry
        entry = Gtk.Entry()
        entry.set_placeholder_text("E.g. find all python files modified in the last week")
        box.add(entry)
        
        # Add status/info area
        info_label = Gtk.Label()
        info_label.set_markup("<i>Press Enter or OK to generate command</i>")
        info_label.set_halign(Gtk.Align.START)
        box.add(info_label)
        
        # Add loading spinner (initially hidden)
        spinner = Gtk.Spinner()
        box.add(spinner)
        
        # Connect Enter key to OK button
        entry.connect("activate", lambda w: dialog.response(Gtk.ResponseType.OK))
        
        box.show_all()
        spinner.hide()  # Hide spinner initially
        
        response = dialog.run()
        
        if response == Gtk.ResponseType.OK:
            query = entry.get_text().strip()
            if query:
                # Show spinner and update info text
                spinner.show()
                spinner.start()
                info_label.set_markup("<i>Generating command...</i>")
                dialog.get_widget_for_response(Gtk.ResponseType.CANCEL).set_sensitive(False)
                dialog.get_widget_for_response(Gtk.ResponseType.OK).set_sensitive(False)
                
                # Process in background to keep UI responsive
                thread = threading.Thread(
                    target=self.process_command_query,
                    args=(query, terminal, dialog, info_label, spinner)
                )
                thread.daemon = True
                thread.start()
                return
                
        dialog.destroy()
    
    def process_command_query(self, query, terminal, dialog, info_label, spinner):
        """Process the command query with Groq API"""
        try:
            # Get terminal context
            context = self.get_terminal_context(terminal)
            
            # Prepare API request
            terminal_content = f"Terminal Content:\n{context}" if context else "Terminal is empty"
            
            prompt = f"""You are an AI assistant specialized in terminal commands. 
Generate a command based on the user's request.

{terminal_content}

User Request: {query}

Respond in this format:
REASONING: <brief explanation of your approach>
COMMAND: <the command to execute>

Keep your reasoning concise and clear. The command should be executable in a typical bash terminal."""
            
            # Make API request
            response = self.call_groq_api(prompt)
            
            # Extract command from response
            command, reasoning = self.parse_ai_response(response)
            
            # Update UI with result
            GLib.idle_add(
                self.show_command_result_dialog,
                dialog, command, reasoning, terminal
            )
            
        except Exception as e:
            # Handle errors
            error_message = str(e)
            GLib.idle_add(
                self.show_error_dialog,
                dialog, error_message
            )
    
    def call_groq_api(self, prompt):
        """Call the Groq API to generate a response"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.settings.get("model", "llama3-70b-8192"),
            "messages": [
                {"role": "system", "content": "You are an expert terminal command assistant."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 1000
        }
        
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=data
        )
        
        if response.status_code != 200:
            raise Exception(f"API Error: {response.status_code} - {response.text}")
            
        result = response.json()
        return result["choices"][0]["message"]["content"]
    
    def parse_ai_response(self, response):
        """Parse the AI response to extract command and reasoning"""
        command = ""
        reasoning = ""
        
        # Look for COMMAND: and REASONING: patterns
        for line in response.split('\n'):
            if line.startswith("COMMAND:"):
                command = line[len("COMMAND:"):].strip()
            elif line.startswith("REASONING:"):
                reasoning = line[len("REASONING:"):].strip()
        
        # If we didn't find explicit markers, try to parse more generally
        if not command:
            # Look for what might be a command (typically lines with special chars)
            lines = response.split('\n')
            for line in lines:
                stripped = line.strip()
                if stripped and any(c in stripped for c in '|&;><$'):
                    command = stripped
                    break
            
            # If we still don't have a command, just take the last line
            if not command and lines:
                command = lines[-1].strip()
        
        # If we didn't find explicit reasoning, use the whole response minus the command
        if not reasoning:
            reasoning = response.replace(command, "").strip()
        
        return command, reasoning
    
    def show_command_result_dialog(self, dialog, command, reasoning, terminal):
        """Show dialog with the generated command and reasoning"""
        # Clean up the previous dialog
        dialog.hide()
        
        result_dialog = Gtk.Dialog(
            title="Generated Command",
            parent=self.parent_window,
            flags=Gtk.DialogFlags.MODAL
        )
        result_dialog.add_buttons(
            "Cancel", Gtk.ResponseType.CANCEL,
            "Apply", Gtk.ResponseType.APPLY,
            "Apply & Run", Gtk.ResponseType.OK
        )
        result_dialog.set_default_size(500, 300)
        
        box = result_dialog.get_content_area()
        box.set_spacing(10)
        box.set_margin_start(10)
        box.set_margin_end(10)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        
        # Reasoning section
        if reasoning:
            reason_label = Gtk.Label()
            reason_label.set_markup("<b>Reasoning:</b>")
            reason_label.set_halign(Gtk.Align.START)
            box.add(reason_label)
            
            reason_text = Gtk.Label(label=reasoning)
            reason_text.set_line_wrap(True)
            reason_text.set_xalign(0)
            reason_text.set_max_width_chars(60)
            box.add(reason_text)
            
            box.add(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        
        # Command section
        cmd_label = Gtk.Label()
        cmd_label.set_markup("<b>Command:</b>")
        cmd_label.set_halign(Gtk.Align.START)
        box.add(cmd_label)
        
        # Create an editable entry for the command
        cmd_entry = Gtk.Entry()
        cmd_entry.set_text(command)
        box.add(cmd_entry)
        
        help_label = Gtk.Label()
        help_label.set_markup("<i>You can edit the command before applying it</i>")
        help_label.set_halign(Gtk.Align.START)
        box.add(help_label)
        
        box.show_all()
        response = result_dialog.run()
        
        if response in (Gtk.ResponseType.APPLY, Gtk.ResponseType.OK):
            final_command = cmd_entry.get_text().strip()
            if final_command:
                # Apply the command to the terminal
                terminal.feed_child(final_command.encode())
                
                # If "Apply & Run" was clicked, also press Enter
                if response == Gtk.ResponseType.OK:
                    terminal.feed_child("\n".encode())
        
        result_dialog.destroy()
        dialog.destroy()
    
    def show_error_dialog(self, parent_dialog, error_message):
        """Show error dialog when something goes wrong"""
        parent_dialog.hide()
        
        error_dialog = Gtk.MessageDialog(
            parent=self.parent_window,
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="Error generating command"
        )
        error_dialog.format_secondary_text(error_message)
        error_dialog.run()
        error_dialog.destroy()
        parent_dialog.destroy()
    
    def get_settings_widget(self):
        """Return widget for plugin settings"""
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        vbox.set_margin_start(10)
        vbox.set_margin_end(10)
        vbox.set_margin_top(10)
        vbox.set_margin_bottom(10)
        
        # API Key setting
        api_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        api_label = Gtk.Label(label="Groq API Key:")
        api_entry = Gtk.Entry()
        api_entry.set_visibility(False)  # Password style
        api_entry.set_text(self.settings.get("api_key", ""))
        api_entry.connect("changed", lambda w: self.update_setting("api_key", w.get_text()))
        api_box.pack_start(api_label, False, False, 0)
        api_box.pack_start(api_entry, True, True, 0)
        vbox.pack_start(api_box, False, False, 0)
        
        # Context lines setting
        context_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        context_label = Gtk.Label(label="Max Context Lines:")
        context_spin = Gtk.SpinButton.new_with_range(5, 100, 5)
        context_spin.set_value(self.settings.get("max_context_lines", 20))
        context_spin.connect("value-changed", lambda w: self.update_setting("max_context_lines", int(w.get_value())))
        context_box.pack_start(context_label, False, False, 0)
        context_box.pack_start(context_spin, True, True, 0)
        vbox.pack_start(context_box, False, False, 0)
        
        # Model selection
        model_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        model_label = Gtk.Label(label="Groq Model:")
        model_combo = Gtk.ComboBoxText()
        
        models = ["llama3-70b-8192", "llama3-8b-8192", "mixtral-8x7b-32768"]
        current_model = self.settings.get("model", "llama3-70b-8192")
        
        for model in models:
            model_combo.append_text(model)
        
        # Set active based on current setting
        if current_model in models:
            model_combo.set_active(models.index(current_model))
        else:
            model_combo.set_active(0)
            
        model_combo.connect("changed", lambda w: self.update_setting("model", w.get_active_text()))
        model_box.pack_start(model_label, False, False, 0)
        model_box.pack_start(model_combo, True, True, 0)
        vbox.pack_start(model_box, False, False, 0)
        
        # Add a note about the keyboard shortcut
        shortcut_label = Gtk.Label()
        shortcut_label.set_markup("<i>Shortcut: Ctrl+Space to activate command builder</i>")
        shortcut_label.set_halign(Gtk.Align.START)
        vbox.pack_start(shortcut_label, False, False, 10)
        
        return vbox
    
    def update_setting(self, key, value):
        """Update a setting and notify the plugin manager"""
        self.settings[key] = value
        if key == "api_key":
            self.api_key = value 