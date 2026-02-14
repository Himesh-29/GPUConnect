#!/bin/bash
# ============================================
#  GPU Connect Agent — Linux Package Builder
#  Run this to create a .tar.gz for deployment
#  on any Linux machine.
#  Usage: bash build_linux.sh
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
AGENT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BUILD_DIR="$SCRIPT_DIR/dist"
PKG_NAME="gpu-connect-agent-linux"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║   GPU Connect Agent — Linux Package Builder         ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# Clean previous builds
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/$PKG_NAME"

# Copy files into package
cp "$AGENT_DIR/agent_ollama.py"    "$BUILD_DIR/$PKG_NAME/"
cp "$SCRIPT_DIR/requirements.txt"  "$BUILD_DIR/$PKG_NAME/"
cp "$SCRIPT_DIR/install.sh"        "$BUILD_DIR/$PKG_NAME/"
cp "$SCRIPT_DIR/uninstall.sh"      "$BUILD_DIR/$PKG_NAME/"
cp "$SCRIPT_DIR/README.md"         "$BUILD_DIR/$PKG_NAME/"

# Make scripts executable
chmod +x "$BUILD_DIR/$PKG_NAME/install.sh"
chmod +x "$BUILD_DIR/$PKG_NAME/uninstall.sh"

# Create tarball
cd "$BUILD_DIR"
tar -czf "${PKG_NAME}.tar.gz" "$PKG_NAME/"

echo "  ✅ Package built: $BUILD_DIR/${PKG_NAME}.tar.gz"
echo ""
echo "  Transfer to your Raspberry Pi 5:"
echo "    scp $BUILD_DIR/${PKG_NAME}.tar.gz pi@<pi-ip>:~/"
echo ""
echo "  Then on the Pi:"
echo "    tar xzf ${PKG_NAME}.tar.gz"
echo "    cd ${PKG_NAME}"
echo "    sudo ./install.sh"
echo ""
