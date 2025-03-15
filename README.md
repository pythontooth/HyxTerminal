# HyxTerminal

A simple terminal emulator built with Python, GTK, and VTE.

## Requirements

- Python 3.6+
- GTK 3
- VTE 2.91
- PyGObject

## Installation

1. Install system dependencies:

```bash
# Ubuntu/Debian
sudo apt-get install python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-vte-2.91

# Fedora
sudo dnf install python3-gobject gtk3 vte291
```

2. Install Python dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Run the terminal:

```bash
python3 hyxterminal.py
```

## Configuration

The terminal can be configured through `~/.config/hyxterminal/config.json`. Available options:

- `window_width`: Initial window width (default: 800)
- `window_height`: Initial window height (default: 600)
- `scrollback_lines`: Number of lines to keep in history (default: 10000)
- `font_scale`: Terminal font scaling (default: 1.0)
- `background_color`: Terminal background color in hex (default: "#000000")
- `foreground_color`: Terminal foreground color in hex (default: "#FFFFFF")

## Features

- Basic terminal functionality
- Copy/Paste support (Ctrl+Shift+C / Ctrl+Shift+V)
- Scrollback buffer
- Multiple window support
- Configurable appearance
- Persistent settings
- Enhanced scrollback support
- Font scaling
- Custom color schemes
