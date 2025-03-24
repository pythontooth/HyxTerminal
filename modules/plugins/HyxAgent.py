import gi
import os
import json
import requests
import threading
import logging
import tempfile
import uuid
import re
from pathlib import Path
from dotenv import load_dotenv
from enum import Enum
from gi.repository import Gtk, Gdk, GLib, Vte, Pango

# Import Plugin class directly using a relative import
from modules.plugins import Plugin

class HyxAgent(Plugin):
    """HyxAgent plugin for HyxTerminal using Groq API"""
    
    def __init__(self):
        super().__init__()
        self.name = "HyxAgent"
        self.description = "Use AI to generate terminal commands from natural language"
        self.version = "1.0"
        self.author = "HyxTerminal Team"
        self.enabled = False
        self.settings = {
            "api_key": "",
            "max_context_lines": 20,
            "model": "llama3-70b-8192",
            "agent_mode": False
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
        """Get recent terminal context as text with enhanced information"""
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
                
            # If we have content, process and extract key information
            if text:
                lines = text.splitlines()
                context_lines = lines[-max_lines:] if len(lines) > max_lines else lines
                
                # Extract current directory and recent commands for better context
                current_dir = ""
                recent_commands = []
                
                # Look for directory indicators (e.g., user@host:~/path$)
                for line in reversed(context_lines):
                    # Check for common prompt patterns to extract current directory
                    dir_match = re.search(r':[~\/]([^$#>]*)[#$>]', line)
                    if dir_match:
                        current_dir = dir_match.group(1).strip()
                        break
                
                # Extract likely commands (lines ending with common prompt symbols)
                for i, line in enumerate(context_lines):
                    if re.search(r'[#$>]\s*[a-zA-Z0-9.\-_/]+', line):
                        # This looks like a command line
                        cmd = re.sub(r'^.*[#$>]\s*', '', line).strip()
                        if cmd and not cmd.startswith('#'):
                            recent_commands.append(cmd)
                
                # Format the enhanced context
                enhanced_context = []
                
                if current_dir:
                    enhanced_context.append(f"Current directory appears to be: {current_dir}")
                
                if recent_commands:
                    enhanced_context.append("Recent commands detected:")
                    enhanced_context.extend([f"  - {cmd}" for cmd in recent_commands[-5:]])
                
                enhanced_context.append("\nTerminal content:")
                enhanced_context.extend(context_lines)
                
                return "\n".join(enhanced_context)
                
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
        
        # Create a custom styled dialog
        dialog = Gtk.Dialog(
            title="",  # No title for cleaner look
            parent=self.parent_window,
            flags=0  # Remove modal flag to prevent parent window darkening
        )
        dialog.set_decorated(False)  # Remove the window's title bar
        dialog.set_keep_above(True)  # Keep above parent window
        dialog.set_transient_for(self.parent_window)  # Maintain proper window relationship
        
        # Remove default buttons
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OK, Gtk.ResponseType.OK
        )
        
        # Set wide aspect ratio (10:1)
        screen_width = self.parent_window.get_screen().get_width()
        dialog_width = min(int(screen_width * 0.7), 800)  # 70% of screen width or 800px max
        dialog_height = int(dialog_width / 10) + 40 # Add extra for controls
        dialog.set_default_size(dialog_width, dialog_height)
        
        # Make it look sleek and modern
        dialog_style_provider = Gtk.CssProvider()
        dialog_css = """
        dialog {
            border-radius: 8px;
            border: 1px solid rgba(0, 0, 0, 0.3);
            background-color: rgba(30, 30, 30, 0.3);
        }
        label {
            color: #f0f0f0;
        }
        entry {
            border-radius: 4px;
            padding: 8px;
            background-color: rgba(50, 50, 50, 0.8);
            color: white;
            border: none;
        }
        button {
            border-radius: 4px;
            background: transparent;
            border: none;
        }
        button:hover {
            background-color: rgba(80, 80, 80, 0.3);
        }
        """
        dialog_style_provider.load_from_data(dialog_css.encode())
        dialog.get_style_context().add_provider(
            dialog_style_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        
        # Remove the action buttons and manage our own layout
        action_area = dialog.get_action_area()
        for widget in action_area.get_children():
            action_area.remove(widget)
            
        # Get content area
        content_box = dialog.get_content_area()
        content_box.set_margin_start(12)
        content_box.set_margin_end(12)
        content_box.set_margin_top(12)
        content_box.set_margin_bottom(12)
        content_box.set_spacing(8)
        
        # Create a top bar with title and close button
        top_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        top_bar.set_margin_bottom(8)
        
        # Make top bar draggable so window can be moved
        top_bar.connect("button-press-event", self.on_drag_start, dialog)
        top_bar.connect("button-release-event", self.on_drag_end, dialog)
        top_bar.connect("motion-notify-event", self.on_drag_motion, dialog)
        
        # Title label (left aligned)
        title_label = Gtk.Label()
        title_label.set_markup("<b>HyxAgent</b> - AI Command Generator")
        title_label.set_halign(Gtk.Align.START)
        title_label.set_hexpand(True)
        
        # Close button (X) - right aligned
        close_button = Gtk.Button()
        close_icon = Gtk.Image.new_from_icon_name("window-close-symbolic", Gtk.IconSize.SMALL_TOOLBAR)
        close_button.add(close_icon)
        close_button.set_relief(Gtk.ReliefStyle.NONE)
        close_button.get_style_context().add_class("no-border")
        close_button.connect("clicked", lambda w: dialog.response(Gtk.ResponseType.CANCEL))
        
        top_bar.pack_start(title_label, True, True, 0)
        top_bar.pack_end(close_button, False, False, 0)
        
        # Main input area
        input_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        
        # Text entry with custom styling
        entry = Gtk.Entry()
        entry.set_placeholder_text("Describe what you want to do in terminal (e.g., find all python files modified in the last week)")
        entry.set_size_request(-1, 34)  # Make entry taller
        entry.set_can_default(True)  # Allow this entry to be the default
        
        # Bottom status bar with hints and model selection
        bottom_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        bottom_bar.set_margin_top(8)
        
        # Escape hint (left aligned)
        self.hint_label = Gtk.Label()
        self.hint_label.set_markup("<small>Press <b>Esc</b> to close</small>")
        self.hint_label.set_halign(Gtk.Align.START)
        self.hint_label.set_hexpand(True)
        
        # Agent mode checkbox
        agent_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        agent_checkbox = Gtk.CheckButton.new_with_label("Agent")
        agent_checkbox.set_active(self.settings.get("agent_mode", False))
        agent_checkbox.connect("toggled", lambda w: self.update_setting("agent_mode", w.get_active()))
        self.agent_mode = agent_checkbox.get_active()
        
        # Add a small tooltip-style info icon
        info_icon = Gtk.Image.new_from_icon_name("dialog-information-symbolic", Gtk.IconSize.SMALL_TOOLBAR)
        info_icon.set_tooltip_text("Agent mode enables multi-step commands with verification")
        
        agent_box.pack_start(agent_checkbox, False, False, 0)
        agent_box.pack_start(info_icon, False, False, 0)
        
        # Model selection dropdown (right aligned)
        model_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        model_label = Gtk.Label()
        model_label.set_markup("<small>Model:</small>")
        
        model_combo = Gtk.ComboBoxText()
        models = ["llama3-70b-8192", "llama3-8b-8192", "mixtral-8x7b-32768"]
        current_model = self.settings.get("model", "llama3-70b-8192")
        
        for model in models:
            model_combo.append_text(model)
            
        if current_model in models:
            model_combo.set_active(models.index(current_model))
        else:
            model_combo.set_active(0)
            
        model_combo.connect("changed", lambda w: self.update_setting("model", w.get_active_text()))
        
        model_box.pack_start(model_label, False, False, 0)
        model_box.pack_start(model_combo, False, False, 0)
        
        bottom_bar.pack_start(self.hint_label, True, True, 0)
        bottom_bar.pack_end(agent_box, False, False, 0)
        bottom_bar.pack_end(model_box, False, False, 0)
        
        # Add all elements to the dialog
        content_box.pack_start(top_bar, False, False, 0)
        content_box.pack_start(entry, False, False, 0)
        
        # Add status/info area
        info_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        info_label = Gtk.Label()
        info_label.set_markup("<small><i>AI will generate a terminal command based on your description</i></small>")
        info_label.set_halign(Gtk.Align.START)
        
        # Add loading spinner (initially hidden)
        spinner = Gtk.Spinner()
        spinner.set_size_request(16, 16)
        
        info_box.pack_start(info_label, True, True, 0)
        info_box.pack_end(spinner, False, False, 0)
        content_box.pack_start(info_box, False, False, 0)
        
        content_box.pack_end(bottom_bar, False, False, 0)
        
        # Connect events for key handling
        dialog.connect("key-press-event", self.on_dialog_key_press)
        
        # Update hint when text is typed
        def on_entry_changed(entry):
            text = entry.get_text().strip()
            if text:
                self.hint_label.set_markup("<small>Press <b>Enter</b> to submit</small>")
            else:
                self.hint_label.set_markup("<small>Press <b>Esc</b> to close</small>")
        
        entry.connect("changed", on_entry_changed)
        entry.connect("activate", lambda w: dialog.response(Gtk.ResponseType.OK))
        
        dialog.show_all()
        spinner.hide()  # Hide spinner initially
        
        # Make sure OK button is default
        dialog.set_default_response(Gtk.ResponseType.OK)
        
        response = dialog.run()
        
        if response == Gtk.ResponseType.OK:
            query = entry.get_text().strip()
            if query:
                # Show spinner and update info text
                spinner.show()
                spinner.start()
                info_label.set_markup("<small><i>Generating command...</i></small>")
                
                # Make the dialog non-interactive during processing
                entry.set_sensitive(False)
                close_button.set_sensitive(False)
                model_combo.set_sensitive(False)
                
                # Process in background to keep UI responsive
                thread = threading.Thread(
                    target=self.process_command_query,
                    args=(query, terminal, dialog, info_label, spinner)
                )
                thread.daemon = True
                thread.start()
                return
                
        dialog.destroy()
    
    def on_dialog_key_press(self, widget, event):
        """Handle dialog key events"""
        # Handle Escape key to close
        if event.keyval == Gdk.KEY_Escape:
            widget.response(Gtk.ResponseType.CANCEL)
            return True
        return False
    
    def process_command_query(self, query, terminal, dialog, info_label, spinner):
        """Process the command query with Groq API"""
        try:
            # Get terminal context
            context = self.get_terminal_context(terminal)
            
            # Prepare API request
            terminal_content = f"Terminal Content (IMPORTANT - Use this for context):\n{context}" if context else "Terminal is empty"
            
            # Choose prompt based on agent mode
            if self.settings.get("agent_mode", False):
                prompt = f"""You are an advanced AI agent specialized in terminal commands and task automation.
Your goal is to break down complex tasks into a sequence of logical steps, execute them one by one with verification, and ensure task completion.

{terminal_content}

User Request: {query}

Analyze the terminal context thoroughly to understand:
1. Current directory and environment
2. Previously executed commands and their outputs
3. Potential errors or issues that need to be addressed

IMPORTANT: ALL COMMANDS MUST BE PRESENTED AS RAW TEXT WITHOUT ANY FORMATTING CHARACTERS. DO NOT USE BACKTICKS OR ANY OTHER MARKDOWN FORMATTING.

Respond in this format:
PLAN: <brief outline of the multi-step approach you'll take>

STEPS:
1. DESCRIPTION: <short description of first step>
   COMMAND: <precise command to execute - RAW TEXT ONLY, NO BACKTICKS>
   VERIFICATION: <how to verify this step succeeded>

2. DESCRIPTION: <short description of second step>
   COMMAND: <precise command to execute - RAW TEXT ONLY, NO BACKTICKS>
   VERIFICATION: <how to verify this step succeeded>

... (additional steps as needed)

Each step must include:
- A clear DESCRIPTION explaining what the step accomplishes
- An executable COMMAND that works in a bash terminal (AS RAW TEXT, NO BACKTICKS)
- A VERIFICATION method that explains how to confirm success

Keep each step focused on a single task. Commands should be concrete and executable without user modification.
"""
            else:
                prompt = f"""You are an AI assistant specialized in terminal commands. 
Generate a command based on the user's request, making specific use of the terminal context provided.

{terminal_content}

User Request: {query}

IMPORTANT: THE COMMAND MUST BE PRESENTED AS RAW TEXT WITHOUT ANY FORMATTING CHARACTERS. DO NOT USE BACKTICKS OR ANY OTHER MARKDOWN FORMATTING.

Your response MUST reference specific information from the terminal context if relevant.
Analyze the current directory, commands already run, and visible output to inform your suggestion.

Respond in this format:
REASONING: <explain your approach, specifically mentioning relevant context from the terminal>
COMMAND: <the raw command to execute without any quotes or backticks>

Keep your reasoning concise and clear. The command should be executable in a typical bash terminal and should not be wrapped in quotes or backticks."""
            
            # Make API request
            response = self.call_groq_api(prompt)
            
            # Process differently based on agent mode
            if self.settings.get("agent_mode", False):
                # Parse multi-step plan and show agent dialog
                plan, steps = self.parse_agent_response(response)
                GLib.idle_add(
                    self.show_agent_dialog,
                    dialog, plan, steps, terminal
                )
            else:
                # Extract single command and reasoning
                command, reasoning = self.parse_ai_response(response)
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
        
        # Choose system message based on agent mode
        if self.settings.get("agent_mode", False):
            system_message = """You are an advanced terminal command agent with expertise in breaking down complex tasks into logical, executable steps.

Your capabilities:
1. Analyze terminal context to understand the current environment
2. Plan multi-step approaches to solve complex problems
3. Create precise, executable commands
4. Provide verification methods for each step
5. Adapt based on terminal output

When operating as an agent, you will:
- Carefully analyze the current directory and command history
- Design a step-by-step plan where each command builds on previous ones
- Include clear verification criteria for each step
- Keep commands executable without user modification
- Ensure each step has a clear, focused purpose

You excel at understanding terminal output and using it to inform subsequent steps.
"""
        else:
            system_message = "You are an expert terminal command assistant. Always analyze and reference the terminal context provided when generating commands. Your responses should demonstrate awareness of the current directory, command history, and visible outputs in the terminal."
        
        data = {
            "model": self.settings.get("model", "llama3-70b-8192"),
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
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
    
    def parse_agent_response(self, response):
        """Parse the agent response to extract plan and steps"""
        plan = ""
        steps = []
        
        # Extract the overall plan
        plan_match = re.search(r'PLAN:\s*(.*?)(?:\n\n|\n(?=STEPS:))', response, re.DOTALL)
        if plan_match:
            plan = plan_match.group(1).strip()
        
        # Extract steps using regex pattern matching
        step_pattern = r'(\d+)\.\s*DESCRIPTION:\s*(.*?)\s*\n\s*COMMAND:\s*(.*?)\s*\n\s*VERIFICATION:\s*(.*?)(?:\n\n|\n(?=\d+\.)|\Z)'
        step_matches = re.finditer(step_pattern, response, re.DOTALL)
        
        for match in step_matches:
            step_num = match.group(1)
            description = match.group(2).strip()
            command = match.group(3).strip()
            verification = match.group(4).strip()
            
            # Create a step dictionary
            step = {
                "number": int(step_num),
                "description": description,
                "command": command,
                "verification": verification,
                "completed": False,
                "output": "",
            }
            steps.append(step)
        
        # If we couldn't parse steps properly, try a simpler approach
        if not steps:
            # Look for lines that have DESCRIPTION, COMMAND, VERIFICATION
            current_step = {}
            step_num = 1
            
            for line in response.split('\n'):
                line = line.strip()
                if line.startswith('DESCRIPTION:'):
                    # If we already have a step in progress, save it before starting a new one
                    if current_step.get('description') and current_step.get('command'):
                        current_step['number'] = step_num
                        current_step['completed'] = False
                        current_step['output'] = ""
                        steps.append(current_step.copy())
                        step_num += 1
                        current_step = {}
                    
                    current_step['description'] = line[len('DESCRIPTION:'):].strip()
                elif line.startswith('COMMAND:'):
                    current_step['command'] = line[len('COMMAND:'):].strip()
                elif line.startswith('VERIFICATION:'):
                    current_step['verification'] = line[len('VERIFICATION:'):].strip()
            
            # Add the last step if it wasn't added yet
            if current_step.get('description') and current_step.get('command'):
                current_step['number'] = step_num
                current_step['completed'] = False
                current_step['output'] = ""
                steps.append(current_step.copy())
        
        # Make sure we have at least an empty plan
        if not plan:
            plan = "Execute the following steps"
            
        # Sort steps by number just in case they were parsed out of order
        steps.sort(key=lambda s: s["number"])
        
        return plan, steps
    
    def show_command_result_dialog(self, dialog, command, reasoning, terminal):
        """Show dialog with the generated command and reasoning"""
        # Clean up the previous dialog
        dialog.hide()
        
        # Create a styled result dialog
        result_dialog = Gtk.Dialog(
            title="",
            parent=self.parent_window,
            flags=0
        )
        result_dialog.set_decorated(False)
        result_dialog.set_keep_above(True)
        result_dialog.set_transient_for(self.parent_window)
        
        # Calculate appropriate size - much more compact like agent dialog
        screen_width = self.parent_window.get_screen().get_width()
        dialog_width = min(int(screen_width * 0.8), 900)
        min_height = int(dialog_width / 6)  # Match agent dialog height
        result_dialog.set_default_size(dialog_width, min_height)
        
        # Apply styling to match agent dialog
        dialog_style_provider = Gtk.CssProvider()
        dialog_css = """
        dialog {
            border-radius: 8px;
            border: 1px solid rgba(0, 0, 0, 0.2);
            background-color: rgba(30, 30, 30, 0.5);
        }
        label {
            color: #f0f0f0;
        }
        entry {
            border-radius: 4px;
            padding: 8px;
            background-color: rgba(50, 50, 50, 0.8);
            color: white;
            border: none;
        }
        button {
            border-radius: 4px;
            background-image: none;
            background-color: rgba(60, 60, 60, 0.8);
            border: 1px solid rgba(80, 80, 80, 0.5);
            color: white;
            padding: 6px 12px;
        }
        button:hover {
            background-color: rgba(80, 80, 80, 0.9);
        }
        button.suggested-action {
            background-color: #282A36;
            border-color: rgba(80, 80, 80, 0.9);
            color: #FFFFFF;
        }
        button.suggested-action:hover {
            background-color: #3E4452;
        }
        .no-border {
            border: none;
            background-color: transparent;
            padding: 0;
        }
        .no-border:hover {
            background-color: rgba(80, 80, 80, 0.5);
        }
        """
        dialog_style_provider.load_from_data(dialog_css.encode())
        result_dialog.get_style_context().add_provider(
            dialog_style_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        
        # Get the content area
        box = result_dialog.get_content_area()
        box.set_spacing(6)  # Match agent dialog spacing
        box.set_margin_start(16)
        box.set_margin_end(16)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        
        # Create a header with title and close button
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        header_box.set_margin_bottom(8)
        
        # Make header draggable
        header_box.connect("button-press-event", self.on_drag_start, result_dialog)
        header_box.connect("button-release-event", self.on_drag_end, result_dialog)
        header_box.connect("motion-notify-event", self.on_drag_motion, result_dialog)
        
        title_label = Gtk.Label()
        title_label.set_markup("<b>Generated Command</b>")
        title_label.set_halign(Gtk.Align.START)
        title_label.set_hexpand(True)
        
        close_button = Gtk.Button()
        close_icon = Gtk.Image.new_from_icon_name("window-close-symbolic", Gtk.IconSize.SMALL_TOOLBAR)
        close_button.add(close_icon)
        close_button.set_relief(Gtk.ReliefStyle.NONE)
        close_button.get_style_context().add_class("no-border")
        close_button.connect("clicked", lambda w: result_dialog.response(Gtk.ResponseType.CANCEL))
        
        header_box.pack_start(title_label, True, True, 0)
        header_box.pack_end(close_button, False, False, 0)
        
        box.pack_start(header_box, False, False, 0)
        
        # Add reasoning in compact format
        if reasoning:
            reasoning_label = Gtk.Label()
            reasoning_label.set_markup(f"<small><i>{reasoning}</i></small>")
            reasoning_label.set_line_wrap(True)
            reasoning_label.set_halign(Gtk.Align.START)
            reasoning_label.set_margin_bottom(6)
            
            box.pack_start(reasoning_label, False, False, 0)
        
        # Command entry
        cmd_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        cmd_label = Gtk.Label()
        cmd_label.set_markup("<b>Command:</b>")
        cmd_label.set_halign(Gtk.Align.START)
        
        cmd_entry = Gtk.Entry()
        cmd_entry.set_text(command)
        cmd_entry.set_hexpand(True)
        
        cmd_box.pack_start(cmd_label, False, False, 0)
        cmd_box.pack_start(cmd_entry, True, True, 0)
        
        box.pack_start(cmd_box, False, False, 0)
        
        # Create a button bar
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        button_box.set_margin_top(4)
        button_box.set_halign(Gtk.Align.END)
        
        # Run button
        run_button = Gtk.Button(label="Run")
        run_button.get_style_context().add_class("suggested-action")
        run_button.connect("clicked", lambda w: result_dialog.response(Gtk.ResponseType.OK))
        
        button_box.pack_end(run_button, False, False, 0)
        
        box.pack_end(button_box, False, False, 0)
        
        # Connect escape key
        result_dialog.connect("key-press-event", lambda w, e: 
            result_dialog.response(Gtk.ResponseType.CANCEL) if e.keyval == Gdk.KEY_Escape else False
        )
        
        # Connect enter key in entry to run command
        cmd_entry.connect("activate", lambda w: result_dialog.response(Gtk.ResponseType.OK))
        
        result_dialog.show_all()
        response = result_dialog.run()
        
        if response == Gtk.ResponseType.OK:
            final_command = cmd_entry.get_text().strip()
            if final_command:
                # Apply the command to the terminal and press Enter
                terminal.feed_child((final_command + "\n").encode())
        
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
        
        # Agent mode toggle
        agent_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        agent_check = Gtk.CheckButton.new_with_label("Enable Agent Mode")
        agent_check.set_active(self.settings.get("agent_mode", False))
        agent_check.connect("toggled", lambda w: self.update_setting("agent_mode", w.get_active()))
        agent_box.pack_start(agent_check, True, True, 0)
        vbox.pack_start(agent_box, False, False, 0)
        
        # Agent mode explanation
        agent_info = Gtk.Label()
        agent_info.set_markup("<small><i>Agent mode enables multi-step commands with verification.\nThe AI will break down complex tasks into steps and execute them sequentially.</i></small>")
        agent_info.set_halign(Gtk.Align.START)
        agent_info.set_margin_start(24)
        vbox.pack_start(agent_info, False, False, 0)
        
        # Add a note about the keyboard shortcut
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        vbox.pack_start(separator, False, False, 10)
        
        shortcut_label = Gtk.Label()
        shortcut_label.set_markup("<i>Shortcut: Ctrl+Space to activate command builder</i>")
        shortcut_label.set_halign(Gtk.Align.START)
        vbox.pack_start(shortcut_label, False, False, 0)
        
        return vbox
    
    def update_setting(self, key, value):
        """Update a setting and notify the plugin manager"""
        self.settings[key] = value
        if key == "api_key":
            self.api_key = value 

    def on_drag_start(self, widget, event, dialog):
        """Handle drag start event"""
        if event.button == 1:  # Left mouse button
            dialog.drag_data = {
                'x': event.x_root,
                'y': event.y_root,
                'dragging': True
            }
            return True
        return False

    def on_drag_end(self, widget, event, dialog):
        """Handle drag end event"""
        if hasattr(dialog, 'drag_data'):
            dialog.drag_data['dragging'] = False
        return False

    def on_drag_motion(self, widget, event, dialog):
        """Handle drag motion event"""
        if hasattr(dialog, 'drag_data') and dialog.drag_data.get('dragging', False):
            # Calculate movement delta
            delta_x = event.x_root - dialog.drag_data['x']
            delta_y = event.y_root - dialog.drag_data['y']
            
            # Get current position and calculate new position
            pos = dialog.get_position()
            dialog.move(pos[0] + int(delta_x), pos[1] + int(delta_y))
            
            # Update starting position
            dialog.drag_data['x'] = event.x_root
            dialog.drag_data['y'] = event.y_root
            return True
        return False

    def show_agent_dialog(self, dialog, plan, steps, terminal):
        """Show dialog with the agent's multi-step plan"""
        # Clean up the previous dialog
        dialog.hide()
        
        # Create a styled result dialog
        agent_dialog = Gtk.Dialog(
            title="",
            parent=self.parent_window,
            flags=0
        )
        agent_dialog.set_decorated(False)
        agent_dialog.set_keep_above(True)
        agent_dialog.set_transient_for(self.parent_window)
        
        # Calculate appropriate size - much more compact
        screen_width = self.parent_window.get_screen().get_width()
        dialog_width = min(int(screen_width * 0.8), 900)
        min_height = int(dialog_width / 6)  # Much more compact height
        agent_dialog.set_default_size(dialog_width, min_height)
        
        # Apply styling
        dialog_style_provider = Gtk.CssProvider()
        dialog_css = """
        dialog {
            border-radius: 8px;
            border: 1px solid rgba(0, 0, 0, 0.2);
            background-color: rgba(30, 30, 30, 0.5);
        }
        label {
            color: #f0f0f0;
        }
        entry {
            border-radius: 4px;
            padding: 8px;
            background-color: rgba(50, 50, 50, 0.8);
            color: white;
            border: none;
        }
        button {
            border-radius: 4px;
            background-image: none;
            background-color: rgba(60, 60, 60, 0.8);
            border: 1px solid rgba(80, 80, 80, 0.5);
            color: white;
            padding: 6px 12px;
        }
        button:hover {
            background-color: rgba(80, 80, 80, 0.9);
        }
        button.suggested-action {
            background-color: #282A36;
            border-color: rgba(80, 80, 80, 0.9);
            color: #FFFFFF;
        }
        button.suggested-action:hover {
            background-color: #3E4452;
        }
        .no-border {
            border: none;
            background-color: transparent;
            padding: 0;
        }
        .no-border:hover {
            background-color: rgba(80, 80, 80, 0.5);
        }
        .separator {
            background-color: rgba(80, 80, 80, 0.5);
            min-height: 1px;
        }
        .step-box {
            border-radius: 4px;
            padding: 4px;
            margin: 0;
        }
        .step-active {
            background-color: rgba(53, 132, 228, 0.2);
            border: 1px solid rgba(53, 132, 228, 0.4);
        }
        .step-completed {
            background-color: rgba(87, 174, 71, 0.2);
            border: 1px solid rgba(87, 174, 71, 0.4);
        }
        .step-pending {
            background-color: rgba(80, 80, 80, 0.2);
            border: 1px solid rgba(80, 80, 80, 0.4);
        }
        """
        dialog_style_provider.load_from_data(dialog_css.encode())
        agent_dialog.get_style_context().add_provider(
            dialog_style_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        
        # Get the content area
        box = agent_dialog.get_content_area()
        box.set_spacing(6)  # Further reduced spacing
        box.set_margin_start(16)
        box.set_margin_end(16)
        box.set_margin_top(10)  # Further reduced margin
        box.set_margin_bottom(10)  # Further reduced margin
        
        # Create a header with title and close button
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        header_box.set_margin_bottom(8)  # Reduced margin
        
        # Make header draggable
        header_box.connect("button-press-event", self.on_drag_start, agent_dialog)
        header_box.connect("button-release-event", self.on_drag_end, agent_dialog)
        header_box.connect("motion-notify-event", self.on_drag_motion, agent_dialog)
        
        title_label = Gtk.Label()
        title_label.set_markup("<b>Multi-Step Plan</b>")  # Simplified title
        title_label.set_halign(Gtk.Align.START)
        title_label.set_hexpand(True)
        
        # Step progress indicator
        progress_label = Gtk.Label()
        progress_label.set_markup(f"<small>Step 1 of {len(steps)}</small>")
        
        close_button = Gtk.Button()
        close_icon = Gtk.Image.new_from_icon_name("window-close-symbolic", Gtk.IconSize.SMALL_TOOLBAR)
        close_button.add(close_icon)
        close_button.set_relief(Gtk.ReliefStyle.NONE)
        close_button.get_style_context().add_class("no-border")
        close_button.connect("clicked", lambda w: agent_dialog.response(Gtk.ResponseType.CANCEL))
        
        header_box.pack_start(title_label, True, True, 0)
        header_box.pack_start(progress_label, False, False, 0)
        header_box.pack_end(close_button, False, False, 0)
        
        box.pack_start(header_box, False, False, 0)
        
        # Add plan description in compact format
        plan_label = Gtk.Label()
        plan_label.set_markup(f"<small><i>{plan}</i></small>")
        plan_label.set_line_wrap(True)
        plan_label.set_halign(Gtk.Align.START)
        plan_label.set_margin_bottom(6)  # Further reduced margin
        
        box.pack_start(plan_label, False, False, 0)
        
        # Create step container - this will hold only the current step
        step_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)  # Further reduced spacing
        step_container.set_margin_start(0)
        step_container.set_margin_end(0)
        
        # Create widgets for each step but store them separately instead of adding to UI
        step_widgets = []
        for step in steps:
            step_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)  # Reduced spacing
            step_box.get_style_context().add_class("step-box")
            step_box.get_style_context().add_class("step-pending")
            
            # Step header with number and description (combined to save space)
            step_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)  # Further reduced spacing
            
            step_desc_label = Gtk.Label()
            step_desc_label.set_markup(f"<b>Step {step['number']}:</b> {step['description']}")
            step_desc_label.set_halign(Gtk.Align.START)
            step_desc_label.set_hexpand(True)
            step_desc_label.set_line_wrap(True)
            
            step_header.pack_start(step_desc_label, True, True, 0)
            
            # Command entry
            cmd_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)  # Reduced spacing
            cmd_label = Gtk.Label()
            cmd_label.set_markup("<b>Command:</b>")
            cmd_label.set_halign(Gtk.Align.START)
            
            cmd_entry = Gtk.Entry()
            cmd_entry.set_text(step['command'])
            cmd_entry.set_hexpand(True)
            
            cmd_box.pack_start(cmd_label, False, False, 0)
            cmd_box.pack_start(cmd_entry, True, True, 0)
            
            # Output area (initially hidden)
            output_scroll = Gtk.ScrolledWindow()
            output_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
            output_scroll.set_min_content_height(80)
            output_scroll.set_max_content_height(150)
            
            output_view = Gtk.TextView()
            output_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
            output_view.set_editable(False)
            output_view.set_cursor_visible(False)
            
            # Style the output text view
            output_view_provider = Gtk.CssProvider()
            output_css = """
            textview {
                background-color: rgba(40, 40, 40, 0.8);
                color: #e0e0e0;
                border-radius: 4px;
                padding: 8px;
            }
            textview text {
                color: #e0e0e0;
            }
            """
            output_view_provider.load_from_data(output_css.encode())
            output_view.get_style_context().add_provider(
                output_view_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
            
            output_buffer = output_view.get_buffer()
            output_buffer.set_text("")
            
            output_scroll.add(output_view)
            output_scroll.set_no_show_all(True)  # Initially hidden
            
            # Add all components to step box (without verification)
            step_box.pack_start(step_header, False, False, 0)
            step_box.pack_start(cmd_box, False, False, 0)
            step_box.pack_start(output_scroll, True, True, 0)
            
            # Store references to widgets we'll need to access later
            widget_refs = {
                "box": step_box,
                "entry": cmd_entry,
                "output_view": output_view,
                "output_scroll": output_scroll,
            }
            step_widgets.append(widget_refs)
            
            # We don't add steps to UI yet, we'll show them one at a time
        
        # Add step container to main box
        box.pack_start(step_container, True, True, 0)
        
        # Create a button bar
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)  # Further reduced spacing
        button_box.set_margin_top(4)  # Further reduced margin
        button_box.set_halign(Gtk.Align.END)
        
        # Navigation and execution buttons
        prev_button = Gtk.Button(label="Previous")  # Shortened label
        prev_button.set_sensitive(False)  # Initially disabled
        
        next_button = Gtk.Button(label="Run")  # Changed from "Execute" to "Run"
        next_button.get_style_context().add_class("suggested-action")
        
        run_all_button = Gtk.Button(label="Run All")  # Shortened label
        
        button_box.pack_end(run_all_button, False, False, 0)
        button_box.pack_end(next_button, False, False, 0)
        button_box.pack_end(prev_button, False, False, 0)
        
        box.pack_end(button_box, False, False, 0)
        
        # Set up state for step execution
        current_step_index = 0
        is_executing = False
        
        # Function to show only the current step
        def show_current_step():
            nonlocal current_step_index
            
            # Clear the step container
            for child in step_container.get_children():
                step_container.remove(child)
            
            # Add only the current step
            if 0 <= current_step_index < len(steps):
                step_container.add(step_widgets[current_step_index]["box"])
                
                # Update progress indicator
                progress_label.set_markup(f"<small>Step {current_step_index + 1} of {len(steps)}</small>")
                
                # Update navigation buttons
                prev_button.set_sensitive(current_step_index > 0)
                
                # Check if this is the last step
                if current_step_index == len(steps) - 1:
                    next_button.set_label("Run")
                else:
                    next_button.set_label("Run")
                
                # If step is completed, update button text
                if steps[current_step_index].get("completed", False):
                    next_button.set_label("Next")
                    
            step_container.show_all()
            
            # Hide output areas unless they have content
            for widget in step_widgets:
                if not widget["output_view"].get_buffer().get_text(
                    widget["output_view"].get_buffer().get_start_iter(),
                    widget["output_view"].get_buffer().get_end_iter(),
                    True
                ):
                    widget["output_scroll"].hide()
        
        # Function to go to previous step
        def go_to_previous_step():
            nonlocal current_step_index
            if current_step_index > 0 and not is_executing:
                current_step_index -= 1
                show_current_step()
        
        # Function to go to next step (without executing)
        def go_to_next_step():
            nonlocal current_step_index
            if current_step_index < len(steps) - 1 and not is_executing:
                current_step_index += 1
                show_current_step()
        
        # Function to execute a single step
        def execute_step(step_index):
            nonlocal is_executing
            
            if step_index >= len(steps) or is_executing:
                return False
                
            is_executing = True
            step = steps[step_index]
            widget = step_widgets[step_index]
            
            # Update UI
            widget["box"].get_style_context().remove_class("step-pending")
            widget["box"].get_style_context().add_class("step-active")
            
            # Show output area
            widget["output_scroll"].show()
            
            # Get command from entry (allowing user edits)
            command = widget["entry"].get_text().strip()
            
            # Disable buttons during execution
            prev_button.set_sensitive(False)
            next_button.set_sensitive(False)
            run_all_button.set_sensitive(False)
            
            # Execute the command
            terminal.feed_child((command + "\n").encode())
            
            # Wait briefly to let the command start execution
            GLib.timeout_add(500, check_command_output, step_index, "", 0)
            
            return True
        
        # Function to check command output periodically
        def check_command_output(step_index, previous_output, check_count):
            if step_index >= len(steps):
                return False
                
            # Maximum checks (10 seconds with 500ms intervals)
            max_checks = 20
            
            # Get latest terminal output
            latest_context = self.get_terminal_context(terminal)
            
            # If output hasn't changed for several checks, consider the command complete
            if latest_context == previous_output and check_count > 3:
                complete_step(step_index, latest_context)
                return False
                
            # If we've reached max checks, complete anyway
            if check_count >= max_checks:
                complete_step(step_index, latest_context)
                return False
                
            # Update output view with current terminal content
            widget = step_widgets[step_index]
            output_buffer = widget["output_view"].get_buffer()
            output_buffer.set_text(latest_context)
            
            # Schedule another check
            GLib.timeout_add(500, check_command_output, step_index, latest_context, check_count + 1)
            return False
        
        # Function to mark a step as complete and move to next
        def complete_step(step_index, output):
            nonlocal is_executing, current_step_index
            
            if step_index >= len(steps):
                return
                
            step = steps[step_index]
            widget = step_widgets[step_index]
            
            # Update step data
            step["completed"] = True
            step["output"] = output
            
            # Update UI
            widget["box"].get_style_context().remove_class("step-active")
            widget["box"].get_style_context().add_class("step-completed")
            
            is_executing = False
            
            # Enable navigation buttons again
            prev_button.set_sensitive(current_step_index > 0)
            
            # If all steps complete
            if current_step_index >= len(steps) - 1:
                next_button.set_sensitive(False)
                run_all_button.set_sensitive(False)
                return
            
            # Update Next button to go to next step
            next_button.set_label("Next")
            next_button.set_sensitive(True)
            run_all_button.set_sensitive(True)
            
            # If running all steps, continue with the next one automatically
            if run_all_active[0]:
                # Advance to next step
                current_step_index += 1
                show_current_step()
                # Execute after a brief pause
                GLib.timeout_add(1000, execute_step, current_step_index)
        
        # Flag to track if "Run All" is active
        run_all_active = [False]
        
        # Connect navigation buttons
        prev_button.connect("clicked", lambda w: go_to_previous_step())
        
        # Connect execution buttons
        def on_next_clicked(button):
            nonlocal current_step_index
            # If current step is completed, just move to next step
            if steps[current_step_index].get("completed", False):
                if current_step_index < len(steps) - 1:
                    current_step_index += 1
                    show_current_step()
            else:
                # Otherwise execute current step
                execute_step(current_step_index)
                
        next_button.connect("clicked", on_next_clicked)
        
        # Connect the "Run All" button
        def on_run_all_clicked(button):
            run_all_active[0] = True
            # Start with current step
            execute_step(current_step_index)
            
        run_all_button.connect("clicked", on_run_all_clicked)
        
        # Connect escape key
        agent_dialog.connect("key-press-event", lambda w, e: 
            agent_dialog.response(Gtk.ResponseType.CANCEL) if e.keyval == Gdk.KEY_Escape else False
        )
        
        # Show the first step only
        show_current_step()
        
        agent_dialog.show_all()
        
        # Hide output areas initially for the current step
        step_widgets[current_step_index]["output_scroll"].hide()
        
        response = agent_dialog.run()
        agent_dialog.destroy()
        dialog.destroy() 