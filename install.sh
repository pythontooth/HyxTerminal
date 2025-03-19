#!/bin/bash

# HyxTerminal Development Setup Script

set -e

echo "Setting up development environment for HyxTerminal..."

# Install dependencies
if command -v apt-get &> /dev/null; then
  echo "Detected Debian/Ubuntu, installing dependencies..."
  sudo apt-get update
  sudo apt-get install -y python3 python3-gi gir1.2-gtk-3.0 gir1.2-vte-2.91
elif command -v dnf &> /dev/null; then
  echo "Detected Fedora, installing dependencies..."
  sudo dnf install -y python3 python3-gobject gtk3 vte291
else
  echo "Couldn't detect package manager. Please install dependencies manually:"
  echo "- Python 3.x"
  echo "- GTK 3.0"
  echo "- VTE 2.91"
  echo "- PyGObject"
fi

echo "Dependencies installed. To run HyxTerminal, use:"
echo "python3 hyxterminal.py" 