#!/bin/bash

# HyxTerminal Installation Script

set -e

# Check if running with sudo
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (use sudo)"
  exit 1
fi

echo "Installing HyxTerminal..."

# Install dependencies
if command -v apt-get &> /dev/null; then
  echo "Detected Debian/Ubuntu, installing dependencies..."
  apt-get update
  apt-get install -y python3 python3-gi gir1.2-gtk-3.0 gir1.2-vte-2.91
elif command -v dnf &> /dev/null; then
  echo "Detected Fedora, installing dependencies..."
  dnf install -y python3 python3-gobject gtk3 vte291
else
  echo "Couldn't detect package manager. Please install dependencies manually:"
  echo "- Python 3.x"
  echo "- GTK 3.0"
  echo "- VTE 2.91"
  echo "- PyGObject"
fi

# Create installation directories
mkdir -p /usr/local/share/hyxterminal
mkdir -p /usr/share/pixmaps
mkdir -p /usr/local/bin
mkdir -p /usr/share/applications

# Copy application files
cp -r *.py modules/ /usr/local/share/hyxterminal/
cp assets/HyxTerminal.png /usr/share/pixmaps/hyxterminal.png
cp hyxterminal.desktop /usr/share/applications/

# Create executable script
cat > /usr/local/bin/hyxterminal << EOF
#!/bin/bash
cd /usr/local/share/hyxterminal
python3 hyxterminal.py
EOF

# Make the script executable
chmod +x /usr/local/bin/hyxterminal

echo "HyxTerminal has been installed successfully!"
echo "You can launch it by typing 'hyxterminal' in your terminal or from your application menu." 