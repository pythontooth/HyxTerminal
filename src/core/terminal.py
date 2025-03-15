import os
import sys
import readline
import json
import atexit
from typing import List, Optional, Dict, Callable
from pathlib import Path

class Terminal:
    def __init__(self):
        self.history: List[str] = []
        self.prompt = "hyx> "
        self.commands: Dict[str, Callable] = {}
        self.command_help: Dict[str, str] = {}
        self.aliases: Dict[str, str] = {}
        self.config = self._load_config()
        self._load_commands()
        self._setup_readline()
        self._load_history()

    def _load_config(self) -> dict:
        config_path = Path.home() / '.hyx_config.json'
        default_config = {
            "history_file": str(Path.home() / '.hyx_history'),
            "max_history": 1000,
            "suggest_commands": True,
            "aliases": {}
        }
        
        if config_path.exists():
            with open(config_path) as f:
                return {**default_config, **json.load(f)}
        return default_config

    def _save_config(self):
        config_path = Path.home() / '.hyx_config.json'
        with open(config_path, 'w') as f:
            json.dump({**self.config, "aliases": self.aliases}, f, indent=2)

    def _load_history(self):
        history_file = self.config["history_file"]
        try:
            readline.read_history_file(history_file)
        except FileNotFoundError:
            pass
        atexit.register(readline.write_history_file, history_file)

    def _load_commands(self):
        self.register_command("help", self._help_command, "Show available commands and their usage")
        self.register_command("clear", self.clear, "Clear the screen")
        self.register_command("exit", self._exit_command, "Exit the terminal")
        self.register_command("history", self._history_command, "Show command history")
        self.register_command("alias", self._alias_command, "Create command alias (Usage: alias name='command')")
        self.register_command("config", self._config_command, "View or edit configuration")
        self.register_command("suggest", self._suggest_command, "Get command suggestions")

    def register_command(self, name: str, func: Callable, help_text: str):
        self.commands[name] = func
        self.command_help[name] = help_text

    def _setup_readline(self):
        readline.parse_and_bind('tab: complete')
        readline.set_completer(self._completer)

    def _completer(self, text: str, state: int) -> Optional[str]:
        if not text:
            commands = list(self.commands.keys())
        else:
            commands = [cmd for cmd in self.commands.keys() if cmd.startswith(text)]
        return commands[state] if state < len(commands) else None

    def _help_command(self, *args):
        print("\nAvailable commands:")
        for cmd, help_text in self.command_help.items():
            print(f"  {cmd:<15} - {help_text}")

    def _history_command(self, *args):
        for idx, cmd in enumerate(self.history, 1):
            print(f"{idx}: {cmd}")

    def _exit_command(self, *args):
        print("Goodbye!")
        sys.exit(0)

    def _alias_command(self, *args):
        if not args:
            print("Usage: alias name='command'")
            return
        try:
            name, command = args[0].split('=', 1)
            name = name.strip()
            command = command.strip("'\"")
            self.aliases[name] = command
            self.register_command(name, lambda *_: os.system(command), f"Alias for: {command}")
            self._save_config()
            print(f"Created alias: {name} -> {command}")
        except ValueError:
            print("Invalid alias format. Use: alias name='command'")

    def _suggest_command(self, *args):
        if not args:
            print("Usage: suggest <partial_command>")
            return

        partial = args[0]
        suggestions = []
        
        # Search in history
        history = list(set(self.history[-100:]))  # Last 100 unique commands
        for cmd in history:
            if partial in cmd and cmd != partial:
                suggestions.append(f"History: {cmd}")

        # Search in aliases
        for alias, cmd in self.aliases.items():
            if partial in alias or partial in cmd:
                suggestions.append(f"Alias: {alias} -> {cmd}")

        if suggestions:
            print("\nSuggestions:")
            for s in suggestions[:5]:  # Show top 5 suggestions
                print(f"  {s}")
        else:
            print("No suggestions found")

    def _config_command(self, *args):
        if not args:
            print("\nCurrent configuration:")
            for key, value in self.config.items():
                print(f"  {key}: {value}")
            return

        if len(args) == 2:
            key, value = args
            if key in self.config:
                # Convert string value to appropriate type
                if isinstance(self.config[key], bool):
                    value = value.lower() == 'true'
                elif isinstance(self.config[key], int):
                    value = int(value)
                self.config[key] = value
                self._save_config()
                print(f"Updated {key} = {value}")
            else:
                print(f"Unknown config key: {key}")

    def clear(self):
        os.system('clear' if os.name == 'posix' else 'cls')

    def run(self):
        self.clear()
        print("Welcome to HyxTerminal v0.3")
        print("Type 'help' for available commands")
        
        while True:
            try:
                command = input(self.prompt).strip()
                if not command:
                    continue

                self.history.append(command)
                
                parts = command.split()
                cmd_name, args = parts[0], parts[1:]
                
                if cmd_name in self.commands:
                    self.commands[cmd_name](*args)
                else:
                    os.system(command)

            except KeyboardInterrupt:
                print("\nUse 'exit' to quit")
            except Exception as e:
                print(f"Error: {e}")
