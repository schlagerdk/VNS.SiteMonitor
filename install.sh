#!/bin/bash
# Installation script for SiteMonitor service

set -e

echo "==================================="
echo "VNS.SiteMonitor Service Installation"
echo "==================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: Please run as root (use sudo)"
    exit 1
fi

# Install Python dependencies
echo "Installing Python dependencies..."
apt-get update
apt-get install -y python3 python3-pip
pip3 install --break-system-packages -r requirements.txt

# Create installation directory
echo "Creating installation directory..."
mkdir -p /opt/sitemonitor
mkdir -p /var/log

# Copy files
echo "Copying files..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Only copy runtime files (check if we're not in /opt/sitemonitor already)
if [ "$SCRIPT_DIR" != "/opt/sitemonitor" ]; then
    cp "$SCRIPT_DIR/sitemonitor.py" /opt/sitemonitor/
fi
chmod +x /opt/sitemonitor/sitemonitor.py

# Only copy config files if they don't exist (preserve existing configs)
if [ ! -f /opt/sitemonitor/config.json ]; then
    cp "$SCRIPT_DIR/config.json.template" /opt/sitemonitor/config.json
    echo "Created config.json - please edit with your settings"
else
    echo "Preserved existing config.json"
fi

if [ ! -f /opt/sitemonitor/sites.json ]; then
    cp "$SCRIPT_DIR/sites.json.template" /opt/sitemonitor/sites.json
    echo "Created sites.json - please edit with your sites"
else
    echo "Preserved existing sites.json"
fi

# Create log file
touch /var/log/sitemonitor.log
chmod 644 /var/log/sitemonitor.log

# Install systemd service
echo "Installing systemd service..."
cp "$SCRIPT_DIR/sitemonitor.service" /etc/systemd/system/
systemctl daemon-reload

echo ""
echo "==================================="
echo "Installation complete!"
echo "==================================="
echo ""
echo "Next steps:"
echo "1. Edit /opt/sitemonitor/config.json with your email settings"
echo "2. Edit /opt/sitemonitor/sites.json to add/modify sites to monitor"
echo "3. Enable the service: sudo systemctl enable sitemonitor"
echo "4. Start the service: sudo systemctl start sitemonitor"
echo "5. Check status: sudo systemctl status sitemonitor"
echo "6. View logs: sudo journalctl -u sitemonitor -f"
echo ""
echo "To test before running as service:"
echo "  cd /opt/sitemonitor && python3 sitemonitor.py --once"
echo ""
