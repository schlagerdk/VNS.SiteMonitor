#!/bin/bash
# Installation script for WebWatch service

set -e

echo "==================================="
echo "VNS.WebWatch Service Installation"
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
mkdir -p /opt/webwatch
mkdir -p /var/log

# Copy files
echo "Copying files..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Only copy runtime files (check if we're not in /opt/webwatch already)
if [ "$SCRIPT_DIR" != "/opt/webwatch" ]; then
    cp "$SCRIPT_DIR/webwatch.py" /opt/webwatch/
fi
chmod +x /opt/webwatch/webwatch.py

# Only copy config files if they don't exist (preserve existing configs)
if [ ! -f /opt/webwatch/config.json ]; then
    cp "$SCRIPT_DIR/config.json.template" /opt/webwatch/config.json
    echo "Created config.json - please edit with your settings"
else
    echo "Preserved existing config.json"
fi

if [ ! -f /opt/webwatch/sites.json ]; then
    cp "$SCRIPT_DIR/sites.json.template" /opt/webwatch/sites.json
    echo "Created sites.json - please edit with your sites"
else
    echo "Preserved existing sites.json"
fi

# Create log file
touch /var/log/webwatch.log
chmod 644 /var/log/webwatch.log

# Install systemd service
echo "Installing systemd service..."
cp "$SCRIPT_DIR/webwatch.service" /etc/systemd/system/
systemctl daemon-reload

echo ""
echo "==================================="
echo "Installation complete!"
echo "==================================="
echo ""
echo "Next steps:"
echo "1. Edit /opt/webwatch/config.json with your email settings"
echo "2. Edit /opt/webwatch/sites.json to add/modify sites to monitor"
echo "3. Enable the service: sudo systemctl enable webwatch"
echo "4. Start the service: sudo systemctl start webwatch"
echo "5. Check status: sudo systemctl status webwatch"
echo "6. View logs: sudo journalctl -u webwatch -f"
echo ""
echo "To test before running as service:"
echo "  cd /opt/webwatch && python3 webwatch.py --once"
echo ""
