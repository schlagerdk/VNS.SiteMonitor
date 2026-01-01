#!/bin/bash
# Installation script for KeepAlive service

set -e

echo "==================================="
echo "VNS.KeepAlive Service Installation"
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
mkdir -p /opt/keepalive
mkdir -p /var/log

# Copy files
echo "Copying files..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Only copy runtime files (check if we're not in /opt/keepalive already)
if [ "$SCRIPT_DIR" != "/opt/keepalive" ]; then
    cp "$SCRIPT_DIR/keepalive.py" /opt/keepalive/
fi
chmod +x /opt/keepalive/keepalive.py

# Only copy config files if they don't exist (preserve existing configs)
if [ ! -f /opt/keepalive/config.json ]; then
    cp "$SCRIPT_DIR/config.json.template" /opt/keepalive/config.json
    echo "Created config.json - please edit with your settings"
else
    echo "Preserved existing config.json"
fi

if [ ! -f /opt/keepalive/sites.json ]; then
    cp "$SCRIPT_DIR/sites.json.template" /opt/keepalive/sites.json
    echo "Created sites.json - please edit with your sites"
else
    echo "Preserved existing sites.json"
fi

# Create log file
touch /var/log/keepalive.log
chmod 644 /var/log/keepalive.log

# Install systemd service
echo "Installing systemd service..."
cp "$SCRIPT_DIR/keepalive.service" /etc/systemd/system/
systemctl daemon-reload

echo ""
echo "==================================="
echo "Installation complete!"
echo "==================================="
echo ""
echo "Next steps:"
echo "1. Edit /opt/keepalive/config.json with your email settings"
echo "2. Edit /opt/keepalive/sites.json to add/modify sites to monitor"
echo "3. Enable the service: sudo systemctl enable keepalive"
echo "4. Start the service: sudo systemctl start keepalive"
echo "5. Check status: sudo systemctl status keepalive"
echo "6. View logs: sudo journalctl -u keepalive -f"
echo ""
echo "To test before running as service:"
echo "  cd /opt/keepalive && python3 keepalive.py --once"
echo ""
