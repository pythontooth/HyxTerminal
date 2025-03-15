import os
import sys
import readline
from typing import List, Optional

class Terminal:
    def __init__(self):
        self.history: List[str] = []
        self.prompt = "hyx> "
        self._setup_readline()

    def _setup_readline(self):
        readline.parse_and_bind('tab: complete')
        readline.set_completer(self._completer)

    def _completer(self, text: str, state: int) -> Optional[str]:
        # Simple command completion
        commands = ['help', 'clear', 'exit', 'history']
        matches = [cmd for cmd in commands if cmd.startswith(text)]
        return matches[state] if state < len(matches) else None

    def clear(self):
        os.system('clear' if os.name == 'posix' else 'cls')

    def run(self):
        self.clear()
        print("Welcome to HyxTerminal v0.1")
        
        while True:
            try:
                command = input(self.prompt).strip()
                if not command:
                    continue

                self.history.append(command)
                
                if command == 'exit':
                    break
                elif command == 'clear':
                    self.clear()
                elif command == 'history':
                    for idx, cmd in enumerate(self.history, 1):
                        print(f"{idx}: {cmd}")
                else:
                    os.system(command)

            except KeyboardInterrupt:
                print("\nUse 'exit' to quit")
            except Exception as e:
                print(f"Error: {e}")
