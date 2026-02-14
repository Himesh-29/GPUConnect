#!/bin/bash
# ============================================
#  GPU Connect Agent — Uninstaller
# ============================================

set -e

SERVICE_NAME="gpu-connect-agent"
INSTALL_DIR="/opt/gpu-connect-agent"
AGENT_USER="gpu-agent"

if [ "$(id -u)" -ne 0 ]; then
    echo "❌ This script must be run as root (use sudo)."
    exit 1
fi

echo ""
echo "  Uninstalling GPU Connect Agent..."
echo ""

# Stop and disable service
if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
    systemctl stop "$SERVICE_NAME"
    echo "  ✅ Service stopped."
fi
if systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
    systemctl disable "$SERVICE_NAME"
fi

# Remove service file
rm -f /etc/systemd/system/${SERVICE_NAME}.service
systemctl daemon-reload
echo "  ✅ Systemd service removed."

# Remove install directory
rm -rf "$INSTALL_DIR"
echo "  ✅ Install directory removed."

# Remove helper script
rm -f /usr/local/bin/gpu-connect-token
echo "  ✅ Helper script removed."

# Ask about config and user
read -p "  Remove config file /etc/gpu-connect-agent.env? [y/N] " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -f /etc/gpu-connect-agent.env
    echo "  ✅ Config removed."
fi

read -p "  Remove service user '$AGENT_USER' and token data? [y/N] " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -rf /home/$AGENT_USER
    userdel "$AGENT_USER" 2>/dev/null || true
    echo "  ✅ User and data removed."
fi

echo ""
echo "  ✅ GPU Connect Agent uninstalled."
echo ""
