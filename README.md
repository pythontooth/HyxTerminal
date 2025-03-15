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

## Features

- Basic terminal functionality
- Copy/Paste support (Ctrl+Shift+C / Ctrl+Shift+V)
- Scrollback buffer
- Multiple window support
```
