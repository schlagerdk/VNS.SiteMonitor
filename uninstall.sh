#!/bin/bash

# VNS.KeepAlive Uninstallation Script
# This script removes the KeepAlive service and all installed files

set -e

INSTALL_DIR="/opt/keepalive"
SERVICE_NAME="keepalive.service"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}"

echo "==================================="
echo "VNS.KeepAlive Uninstallation"
echo "==================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root (use sudo)"
    exit 1
fi

# Stop the service if running
echo "Stopping service..."
if systemctl is-active --quiet ${SERVICE_NAME}; then
    systemctl stop ${SERVICE_NAME}
    echo "✓ Service stopped"
else
    echo "Service is not running"
fi

# Disable the service
echo "Disabling service..."
if systemctl is-enabled --quiet ${SERVICE_NAME} 2>/dev/null; then
    systemctl disable ${SERVICE_NAME}
    echo "✓ Service disabled"
else
    echo "Service is not enabled"
fi

# Remove service file
if [ -f "${SERVICE_FILE}" ]; then
    echo "Removing service file..."
    rm -f "${SERVICE_FILE}"
    systemctl daemon-reload
    echo "✓ Service file removed"
else
    echo "Service file not found"
fi

# Remove installation directory
if [ -d "${INSTALL_DIR}" ]; then
    echo "Removing installation directory..."
    echo "This will delete: ${INSTALL_DIR}"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "${INSTALL_DIR}"
        echo "✓ Installation directory removed"
    else
        echo "Skipped removing installation directory"
    fi
else
    echo "Installation directory not found"
fi

echo ""
echo "==================================="
echo "Uninstallation complete!"
echo "==================================="
