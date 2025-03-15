# HyxTerminal v0.3

A smart terminal emulator with advanced features.

## Features
- Persistent command history
- Configuration system
- Command suggestions
- Enhanced alias system
- All v0.2 features

## Installation
```bash
pip install -r requirements.txt
```

## Usage
```bash
python src/main.py
```

## Commands
- `help` - Show available commands and their usage
- `clear` - Clear the screen
- `history` - Show command history
- `alias` - Create command aliases
- `config` - View or edit configuration
- `suggest` - Get command suggestions
- `exit` - Exit the terminal

## Configuration
Configuration is stored in `~/.hyx_config.json`:
```json
{
  "history_file": "~/.hyx_history",
  "max_history": 1000,
  "suggest_commands": true,
  "aliases": {}
}
