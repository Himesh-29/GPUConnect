#!/bin/bash
# ============================================
#  GPU Connect Agent — macOS Installer
#  Works on macOS (Apple Silicon & Intel)
#  Ollama uses Metal GPU acceleration on Apple Silicon.
#  Usage: chmod +x install.sh && ./install.sh
# ============================================

set -e

INSTALL_DIR="$HOME/.gpu-connect-agent"
VENV_DIR="$INSTALL_DIR/venv"
PLIST_LABEL="com.gpuconnect.agent"
PLIST_PATH="$HOME/Library/LaunchAgents/${PLIST_LABEL}.plist"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║      GPU Connect Agent — macOS Installer            ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# --- Pre-flight checks ---
if [ "$(uname)" != "Darwin" ]; then
    echo "  ❌ This installer is for macOS only."
    exit 1
fi

ARCH=$(uname -m)
echo "  Detected: macOS $(sw_vers -productVersion) ($ARCH)"
if [ "$ARCH" = "arm64" ]; then
    echo "  ✅ Apple Silicon — Ollama will use Metal GPU acceleration."
else
    echo "  ℹ️  Intel Mac — Ollama will use CPU inference."
fi

# Check for Python 3
if ! command -v python3 &>/dev/null; then
    echo ""
    echo "  ❌ Python 3 is required but not found."
    echo "  Install via: brew install python3"
    echo "  Or download from https://www.python.org/downloads/"
    exit 1
fi

PYTHON_VER=$(python3 --version 2>&1)
echo "  Using: $PYTHON_VER"

echo ""
echo "  [1/5] Setting up install directory..."
mkdir -p "$INSTALL_DIR"
cp agent_ollama.py "$INSTALL_DIR/"
cp requirements.txt "$INSTALL_DIR/"
echo "  ✅ Agent files copied to $INSTALL_DIR"

echo "  [2/5] Creating Python virtual environment..."
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip -q
"$VENV_DIR/bin/pip" install -r "$INSTALL_DIR/requirements.txt" -q
echo "  ✅ Python venv created and dependencies installed."

echo "  [3/5] Installing LaunchAgent (auto-start on login)..."
mkdir -p "$HOME/Library/LaunchAgents"

cat > "$PLIST_PATH" << PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${PLIST_LABEL}</string>

    <key>ProgramArguments</key>
    <array>
        <string>${INSTALL_DIR}/venv/bin/python</string>
        <string>${INSTALL_DIR}/agent_ollama.py</string>
    </array>

    <key>WorkingDirectory</key>
    <string>${INSTALL_DIR}</string>

    <key>RunAtLoad</key>
    <false/>

    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>

    <key>ThrottleInterval</key>
    <integer>10</integer>

    <key>StandardOutPath</key>
    <string>${INSTALL_DIR}/agent.log</string>

    <key>StandardErrorPath</key>
    <string>${INSTALL_DIR}/agent.err.log</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin</string>
    </dict>
</dict>
</plist>
PLIST_EOF

echo "  ✅ LaunchAgent installed at $PLIST_PATH"

echo "  [4/5] Creating helper commands..."

# Token helper
cat > "$INSTALL_DIR/set-token.sh" << 'TOKEN_EOF'
#!/bin/bash
if [ -z "$1" ]; then
    echo "Usage: gpu-connect-token <gpc_xxx...>"
    exit 1
fi
TOKEN="$1"
if [[ ! "$TOKEN" == gpc_* ]]; then
    echo "❌ Token must start with 'gpc_'"
    exit 1
fi
TOKEN_DIR="$HOME/.gpuconnect"
mkdir -p "$TOKEN_DIR"
echo -n "$TOKEN" > "$TOKEN_DIR/token"
chmod 700 "$TOKEN_DIR"
chmod 600 "$TOKEN_DIR/token"
echo "✅ Token saved."
echo "   Start with: gpu-connect-start"
TOKEN_EOF
chmod +x "$INSTALL_DIR/set-token.sh"

# Start/stop/status helpers — install to /usr/local/bin
BINDIR="/usr/local/bin"
mkdir -p "$BINDIR" 2>/dev/null || true

cat > "$INSTALL_DIR/gpu-connect-token" << HELPER_EOF
#!/bin/bash
exec "$INSTALL_DIR/set-token.sh" "\$@"
HELPER_EOF
chmod +x "$INSTALL_DIR/gpu-connect-token"

cat > "$INSTALL_DIR/gpu-connect-start" << HELPER_EOF
#!/bin/bash
launchctl load "$PLIST_PATH" 2>/dev/null
launchctl start "$PLIST_LABEL"
echo "✅ GPU Connect Agent started."
echo "   Logs: tail -f $INSTALL_DIR/agent.log"
HELPER_EOF
chmod +x "$INSTALL_DIR/gpu-connect-start"

cat > "$INSTALL_DIR/gpu-connect-stop" << HELPER_EOF
#!/bin/bash
launchctl stop "$PLIST_LABEL" 2>/dev/null
launchctl unload "$PLIST_PATH" 2>/dev/null
echo "✅ GPU Connect Agent stopped."
HELPER_EOF
chmod +x "$INSTALL_DIR/gpu-connect-stop"

cat > "$INSTALL_DIR/gpu-connect-status" << HELPER_EOF
#!/bin/bash
if launchctl list | grep -q "$PLIST_LABEL"; then
    echo "✅ GPU Connect Agent is running."
    echo "   Logs: tail -f $INSTALL_DIR/agent.log"
else
    echo "⏹  GPU Connect Agent is not running."
    echo "   Start with: gpu-connect-start"
fi
HELPER_EOF
chmod +x "$INSTALL_DIR/gpu-connect-status"

# Symlink helpers to PATH
for cmd in gpu-connect-token gpu-connect-start gpu-connect-stop gpu-connect-status; do
    ln -sf "$INSTALL_DIR/$cmd" "$BINDIR/$cmd" 2>/dev/null || {
        echo "  ⚠️  Could not symlink $cmd to $BINDIR (try: sudo ./install.sh)"
    }
done

echo "  ✅ Helper commands installed."

echo "  [5/5] Done!"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║                 Installation Complete!               ║"
echo "╠══════════════════════════════════════════════════════╣"
echo "║                                                      ║"
echo "║  Before starting, you need to:                       ║"
echo "║                                                      ║"
echo "║  1. Install Ollama (if not already):                 ║"
echo "║     brew install ollama                              ║"
echo "║     — or —                                           ║"
echo "║     Download from https://ollama.com/download/mac    ║"
echo "║                                                      ║"
echo "║  2. Pull a model:                                    ║"
echo "║     ollama pull tinyllama                             ║"
echo "║                                                      ║"
echo "║  3. Set your agent token:                            ║"
echo "║     gpu-connect-token <your_gpc_token>               ║"
echo "║                                                      ║"
echo "║  4. Start the agent:                                 ║"
echo "║     gpu-connect-start                                ║"
echo "║                                                      ║"
echo "║  View logs:                                          ║"
echo "║     tail -f ~/.gpu-connect-agent/agent.log           ║"
echo "║                                                      ║"
echo "║  Commands:                                           ║"
echo "║     gpu-connect-start   — Start agent                ║"
echo "║     gpu-connect-stop    — Stop agent                 ║"
echo "║     gpu-connect-status  — Check if running           ║"
echo "║     gpu-connect-token   — Update token               ║"
echo "║                                                      ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
