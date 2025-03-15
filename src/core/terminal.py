import os
import sys
import readline
import json
import atexit
import importlib.util
import watchdog.observers
import watchdog.events
from typing import List, Optional, Dict, Callable, Any
from pathlib import Path
from datetime import datetime
from .ai_suggest import AISuggester

class Terminal:
    def __init__(self):
        self.history: List[str] = []
        self.prompt = "hyx> "
        self.commands: Dict[str, Callable] = {}
        self.command_help: Dict[str, str] = {}
        self.aliases: Dict[str, str] = {}
        self.config = self._load_config()
        self.plugins: Dict[str, object] = {}
        self.themes = self._load_themes()
        self._load_commands()
        self._setup_readline()
        self._load_history()
        self._load_plugins()
        self.ai_suggester = AISuggester()
        self.command_groups: Dict[str, List[str]] = {}
        self.plugin_observer = None
        self._setup_plugin_watcher()
        
    def _setup_plugin_watcher(self):
        if not self.config["plugins_enabled"]:
            return
            
        class PluginHandler(watchdog.events.FileSystemEventHandler):
            def __init__(self, terminal):
                self.terminal = terminal

            def on_modified(self, event):
                if event.src_path.endswith('.py'):
                    self.terminal._reload_plugin(Path(event.src_path))

        plugin_dir = Path(__file__).parent.parent / "plugins"
        if plugin_dir.exists():
            self.plugin_observer = watchdog.observers.Observer()
            self.plugin_observer.schedule(PluginHandler(self), str(plugin_dir))
            self.plugin_observer.start()

    def _reload_plugin(self, plugin_path: Path):
        try:
            name = plugin_path.stem
            if name in self.plugins:
                # Remove old commands
                old_commands = [cmd for cmd, func in self.commands.items() 
                              if getattr(func, '__plugin__', '') == name]
                for cmd in old_commands:
                    del self.commands[cmd]
                    del self.command_help[cmd]

            # Load new version
            spec = importlib.util.spec_from_file_location(name, plugin_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, "setup"):
                self.plugins[name] = module.setup(self)
                print(f"Reloaded plugin: {name}")
        except Exception as e:
            print(f"Failed to reload plugin {plugin_path}: {e}")

    def _load_config(self) -> dict:
        config_path = Path.home() / '.hyx_config.json'
        default_config = {
            "history_file": str(Path.home() / '.hyx_history'),
            "max_history": 1000,
            "suggest_commands": True,
            "aliases": {},
            "theme": "default",
            "plugins_enabled": True,
            "ai_suggestions": True,
            "max_chain_depth": 10
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

    def _load_plugins(self):
        if not self.config["plugins_enabled"]:
            return

        plugin_dir = Path(__file__).parent.parent / "plugins"
        if not plugin_dir.exists():
            return

        for plugin_file in plugin_dir.glob("*.py"):
            try:
                spec = importlib.util.spec_from_file_location(
                    plugin_file.stem, plugin_file
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                if hasattr(module, "setup"):
                    plugin = module.setup(self)
                    self.plugins[plugin_file.stem] = plugin
                    print(f"Loaded plugin: {plugin_file.stem}")
            except Exception as e:
                print(f"Failed to load plugin {plugin_file}: {e}")

    def _load_themes(self):
        theme_file = Path(__file__).parent.parent / "themes.json"
        default_theme = {
            "prompt": "hyx> ",
            "text_color": "white",
            "error_color": "red",
            "success_color": "green"
        }
        
        if theme_file.exists():
            with open(theme_file) as f:
                return {**{"default": default_theme}, **json.load(f)}
        return {"default": default_theme}

    def _load_commands(self):
        self.register_command("help", self._help_command, "Show available commands and their usage")
        self.register_command("clear", self.clear, "Clear the screen")
        self.register_command("exit", self._exit_command, "Exit the terminal")
        self.register_command("history", self._history_command, "Show command history")
        self.register_command("alias", self._alias_command, "Create command alias (Usage: alias name='command')")
        self.register_command("config", self._config_command, "View or edit configuration")
        self.register_command("suggest", self._suggest_command, "Get command suggestions")
        self.register_command("theme", self._theme_command, "Change terminal theme")
        self.register_command("plugins", self._plugins_command, "List/enable/disable plugins")
        self.register_command("search", self._search_command, "Search command history")

    def register_command(self, name: str, func: Callable, help_text: str, group: str = "general"):
        self.commands[name] = func
        self.command_help[name] = help_text
        self.command_groups.setdefault(group, []).append(name)
        # Mark command with plugin name for hot-reloading
        if sys._getframe(1).f_globals.get('__file__', '').endswith('.py'):
            setattr(func, '__plugin__', Path(sys._getframe(1).f_globals['__file__']).stem)

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
        if not args:
            print("\nCommand Groups:")
            for group, cmds in self.command_groups.items():
                print(f"\n{group.title()}:")
                for cmd in cmds:
                    print(f"  {cmd:<15} - {self.command_help[cmd]}")
        else:
            # Show detailed help for specific command
            cmd = args[0]
            if cmd in self.commands:
                print(f"\n{cmd} - {self.command_help[cmd]}")
                if hasattr(self.commands[cmd], '__doc__'):
                    print(f"\nDetails:\n{self.commands[cmd].__doc__}")

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

    def _theme_command(self, *args):
        if not args:
            print("\nAvailable themes:")
            for theme in self.themes:
                print(f"  {theme}")
            return
        
        theme = args[0]
        if theme in self.themes:
            self.config["theme"] = theme
            self._save_config()
            print(f"Theme changed to {theme}")
        else:
            print(f"Theme {theme} not found")

    def _plugins_command(self, *args):
        if not args:
            print("\nLoaded plugins:")
            for name, plugin in self.plugins.items():
                print(f"  {name}")
            return

        action, plugin = args[0], args[1]
        if action == "disable":
            # Implementation for disabling plugins
            pass

    def _search_command(self, *args):
        if not args:
            print("Usage: search <pattern>")
            return

        pattern = args[0].lower()
        matches = [cmd for cmd in self.history if pattern in cmd.lower()]
        if matches:
            print("\nMatching commands:")
            for idx, cmd in enumerate(matches[-5:], 1):
                print(f"  {idx}: {cmd}")
        else:
            print("No matching commands found")

    def _execute_chain(self, commands: List[str]):
        if len(commands) > self.config["max_chain_depth"]:
            raise Exception("Command chain too deep")

        for cmd in commands:
            parts = cmd.strip().split()
            cmd_name, args = parts[0], parts[1:]
            
            if cmd_name in self.commands:
                self.commands[cmd_name](*args)
            else:
                os.system(cmd)

    def _process_pipeline(self, commands: List[str]) -> Any:
        result = None
        for cmd in commands:
            parts = cmd.strip().split()
            cmd_name, args = parts[0], parts[1:]
            
            if cmd_name in self.commands:
                # Capture output
                import io
                import contextlib
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    self.commands[cmd_name](*args, input_data=result)
                result = output.getvalue()
            else:
                # Handle system commands in pipeline
                import subprocess
                proc = subprocess.run(cmd, shell=True, input=str(result).encode() if result else None,
                                   capture_output=True, text=True)
                result = proc.stdout
        return result

    def clear(self):
        os.system('clear' if os.name == 'posix' else 'cls')

    def run(self):
        self.clear()
        print(f"Welcome to HyxTerminal v0.6 ({len(self.plugins)} plugins loaded)")
        print("Type 'help' for available commands")
        
        while True:
            try:
                command = input(self.prompt).strip()
                if not command:
                    continue

                self.history.append(command)
                
                # Handle pipelines
                if " |> " in command:
                    commands = command.split(" |> ")
                    result = self._process_pipeline(commands)
                    if result:
                        print(result.strip())
                    continue
                    
                # Handle command chaining
                elif " && " in command:
                    commands = command.split(" && ")
                    self._execute_chain(commands)
                    continue

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
