import difflib
from typing import List

class AISuggester:
    def __init__(self):
        self.command_patterns = {}
        self.recent_commands = []
        
    def learn_pattern(self, command: str):
        parts = command.split()
        if len(parts) > 1:
            self.command_patterns.setdefault(parts[0], set()).add(tuple(parts[1:]))
            
    def suggest(self, partial: str) -> List[str]:
        suggestions = []
        
        # Pattern-based suggestions
        if partial in self.command_patterns:
            patterns = self.command_patterns[partial]
            suggestions.extend([f"{partial} {' '.join(p)}" for p in patterns][:3])
            
        # Fuzzy matching
        all_commands = list(self.command_patterns.keys())
        matches = difflib.get_close_matches(partial, all_commands, n=3)
        suggestions.extend(matches)
        
        return suggestions
