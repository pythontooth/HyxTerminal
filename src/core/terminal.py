import os
import sys
import readline
import json
from typing import List, Optional, Dict, Callable

class Terminal:
    def __init__(self):
        self.history: List[str] = []
        self.prompt = "hyx> "
        self.commands: Dict[str, Callable] = {}
        self.command_help: Dict[str, str] = {}
        self._load_commands()
        self._setup_readline()

    def _load_commands(self):
        self.register_command("help", self._help_command, "Show available commands and their usage")
        self.register_command("clear", self.clear, "Clear the screen")
        self.register_command("exit", self._exit_command, "Exit the terminal")
        self.register_command("history", self._history_command, "Show command history")
        self.register_command("alias", self._alias_command, "Create command alias (Usage: alias name='command')")

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
            self.register_command(name, lambda *_: os.system(command), f"Alias for: {command}")
            print(f"Created alias: {name} -> {command}")
        except ValueError:
            print("Invalid alias format. Use: alias name='command'")

    def clear(self):
        os.system('clear' if os.name == 'posix' else 'cls')

    def run(self):
        self.clear()
        print("Welcome to HyxTerminal v0.2")
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
