#!/bin/bash

# HyxTerminal Complete Uninstaller
# This script removes all traces of HyxTerminal from your system

echo "Uninstalling HyxTerminal from your system..."

# Check if running with sudo
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (use sudo)"
  exit 1
fi

# Remove executable script
if [ -f /usr/local/bin/hyxterminal ]; then
  echo "Removing executable script..."
  rm -f /usr/local/bin/hyxterminal
fi

# Remove application directory
if [ -d /usr/local/share/hyxterminal ]; then
  echo "Removing application files..."
  rm -rf /usr/local/share/hyxterminal
fi

# Remove desktop file
if [ -f /usr/share/applications/HyxTerminal.desktop ]; then
  echo "Removing desktop file..."
  rm -f /usr/share/applications/HyxTerminal.desktop
fi

# Remove icon
if [ -f /usr/share/pixmaps/hyxterminal.png ]; then
  echo "Removing icon file..."
  rm -f /usr/share/pixmaps/hyxterminal.png
fi

# Remove any cache files
if [ -d "$HOME/.cache/hyxterminal" ]; then
  echo "Removing cache files..."
  rm -rf "$HOME/.cache/hyxterminal"
fi

# Remove config files (optional, comment out if you want to keep configs)
if [ -d "$HOME/.config/hyxterminal" ]; then
  echo "Removing configuration files..."
  rm -rf "$HOME/.config/hyxterminal"
fi

echo "HyxTerminal has been completely removed from your system."
echo "You can still run it directly from the project directory with:"
echo "python3 hyxterminal.py" 