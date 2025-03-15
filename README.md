# HyxTerminal v0.5

A smart terminal emulator with advanced features.

## Features
- Plugin system
- Command chaining
- Themes support
- Command history search
- All v0.3 features

## Installation
```bash
pip install -r requirements.txt
```

## Usage
```bash
python src/main.py
```

## Commands
- All v0.3 commands
- `theme` - Change terminal theme
- `plugins` - Manage plugins
- `search` - Search command history
- Custom commands from plugins

## Command Chaining
Chain multiple commands with &&:
```bash
clear && ls && echo "Done"
```

## Plugins
Place plugin files in `src/plugins/`. Example:
```python
def setup(terminal):
    # Register commands here
    return {"name": "My Plugin"}
```

## Themes
Custom themes can be defined in `src/themes.json`
