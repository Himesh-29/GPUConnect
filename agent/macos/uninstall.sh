#!/bin/bash
# ============================================
#  GPU Connect Agent — macOS Uninstaller
# ============================================

set -e

INSTALL_DIR="$HOME/.gpu-connect-agent"
PLIST_LABEL="com.gpuconnect.agent"
PLIST_PATH="$HOME/Library/LaunchAgents/${PLIST_LABEL}.plist"

echo ""
echo "  Uninstalling GPU Connect Agent..."
echo ""

# Stop the agent
if launchctl list | grep -q "$PLIST_LABEL" 2>/dev/null; then
    launchctl stop "$PLIST_LABEL" 2>/dev/null || true
    launchctl unload "$PLIST_PATH" 2>/dev/null || true
    echo "  ✅ Agent stopped."
fi

# Remove LaunchAgent plist
rm -f "$PLIST_PATH"
echo "  ✅ LaunchAgent removed."

# Remove helper commands
for cmd in gpu-connect-token gpu-connect-start gpu-connect-stop gpu-connect-status; do
    rm -f "/usr/local/bin/$cmd" 2>/dev/null || true
done
echo "  ✅ Helper commands removed."

# Remove install directory
rm -rf "$INSTALL_DIR"
echo "  ✅ Install directory removed."

# Ask about token data
echo ""
read -p "  Remove saved token (~/.gpuconnect)? [y/N] " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -rf "$HOME/.gpuconnect"
    echo "  ✅ Token data removed."
fi

echo ""
echo "  ✅ GPU Connect Agent uninstalled."
echo ""
