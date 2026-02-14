#!/bin/bash
# ============================================
#  GPU Connect Agent — Linux Installer
#  Works on any Linux (x86_64, aarch64, armv7l)
#  Usage: chmod +x install.sh && sudo ./install.sh
# ============================================

set -e

INSTALL_DIR="/opt/gpu-connect-agent"
VENV_DIR="$INSTALL_DIR/venv"
SERVICE_NAME="gpu-connect-agent"
AGENT_USER="gpu-agent"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║       GPU Connect Agent — Linux Installer            ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# --- Pre-flight checks ---
if [ "$(id -u)" -ne 0 ]; then
    echo "  ❌ This script must be run as root (use sudo)."
    exit 1
fi

ARCH=$(uname -m)
echo "  Detected architecture: $ARCH"
if [[ "$ARCH" != "x86_64" && "$ARCH" != "aarch64" && "$ARCH" != "armv7l" ]]; then
    echo "  ⚠️  Unusual architecture: $ARCH — this may still work."
fi

echo "  [1/6] Installing system dependencies..."
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip curl > /dev/null 2>&1
echo "  ✅ System dependencies installed."

echo "  [2/6] Creating service user..."
if ! id "$AGENT_USER" &>/dev/null; then
    useradd --system --no-create-home --shell /usr/sbin/nologin "$AGENT_USER" 2>/dev/null || true
    echo "  ✅ User '$AGENT_USER' created."
else
    echo "  ✅ User '$AGENT_USER' already exists."
fi

echo "  [3/6] Setting up install directory..."
mkdir -p "$INSTALL_DIR"
cp agent_ollama.py "$INSTALL_DIR/"
cp requirements.txt "$INSTALL_DIR/"
echo "  ✅ Agent files copied to $INSTALL_DIR"

echo "  [4/6] Creating Python virtual environment..."
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip -q
"$VENV_DIR/bin/pip" install -r "$INSTALL_DIR/requirements.txt" -q
echo "  ✅ Python venv created and dependencies installed."

echo "  [5/6] Installing systemd service..."
cat > /etc/systemd/system/${SERVICE_NAME}.service << 'UNIT_EOF'
[Unit]
Description=GPU Connect Agent (Ollama)
After=network-online.target ollama.service
Wants=network-online.target

[Service]
Type=simple
User=gpu-agent
Group=gpu-agent
WorkingDirectory=/opt/gpu-connect-agent
ExecStart=/opt/gpu-connect-agent/venv/bin/python /opt/gpu-connect-agent/agent_ollama.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

# Environment — override via /etc/gpu-connect-agent.env
EnvironmentFile=-/etc/gpu-connect-agent.env

# Security hardening
ProtectSystem=strict
ProtectHome=read-only
PrivateTmp=true
NoNewPrivileges=true
ReadWritePaths=/opt/gpu-connect-agent

[Install]
WantedBy=multi-user.target
UNIT_EOF

# Create env file template if it doesn't exist
if [ ! -f /etc/gpu-connect-agent.env ]; then
    cat > /etc/gpu-connect-agent.env << 'ENV_EOF'
# GPU Connect Agent Configuration
# Uncomment and edit as needed

# SERVER_URL=wss://gpu-connect-api.onrender.com/ws/computing/
# API_URL=https://gpu-connect-api.onrender.com
# OLLAMA_URL=http://localhost:11434
# NODE_ID=rpi5-node-01
# FRONTEND_URL=https://gpu-connect.vercel.app
ENV_EOF
    echo "  ✅ Config template created at /etc/gpu-connect-agent.env"
fi

systemctl daemon-reload
echo "  ✅ Systemd service installed."

echo "  [6/6] Setting permissions..."
chown -R "$AGENT_USER:$AGENT_USER" "$INSTALL_DIR"
# Allow the service user to store tokens in its pseudo-home
mkdir -p /home/$AGENT_USER/.gpuconnect
chown -R "$AGENT_USER:$AGENT_USER" /home/$AGENT_USER
chmod 700 /home/$AGENT_USER/.gpuconnect
# Update user home dir so token storage works
usermod -d /home/$AGENT_USER "$AGENT_USER" 2>/dev/null || true
echo "  ✅ Permissions set."

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║                 Installation Complete!               ║"
echo "╠══════════════════════════════════════════════════════╣"
echo "║                                                      ║"
echo "║  Before starting, you need to:                       ║"
echo "║                                                      ║"
echo "║  1. Install Ollama (if not already):                 ║"
echo "║     curl -fsSL https://ollama.com/install.sh | sh    ║"
echo "║                                                      ║"
echo "║  2. Pull a model:                                    ║"
echo "║     ollama pull tinyllama                             ║"
echo "║                                                      ║"
echo "║  3. Set your agent token:                            ║"
echo "║     sudo gpu-connect-token <your_gpc_token>          ║"
echo "║                                                      ║"
echo "║  4. Start the service:                               ║"
echo "║     sudo systemctl start gpu-connect-agent           ║"
echo "║     sudo systemctl enable gpu-connect-agent          ║"
echo "║                                                      ║"
echo "║  View logs:                                          ║"
echo "║     journalctl -u gpu-connect-agent -f               ║"
echo "║                                                      ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# Install the token helper script
cat > /usr/local/bin/gpu-connect-token << 'TOKEN_EOF'
#!/bin/bash
# Helper to set the agent token for the gpu-connect service user
if [ "$(id -u)" -ne 0 ]; then
    echo "Usage: sudo gpu-connect-token <gpc_xxx...>"
    exit 1
fi
if [ -z "$1" ]; then
    echo "Usage: sudo gpu-connect-token <gpc_xxx...>"
    exit 1
fi
TOKEN="$1"
if [[ ! "$TOKEN" == gpc_* ]]; then
    echo "❌ Token must start with 'gpc_'"
    exit 1
fi
TOKEN_DIR="/home/gpu-agent/.gpuconnect"
mkdir -p "$TOKEN_DIR"
echo -n "$TOKEN" > "$TOKEN_DIR/token"
chown -R gpu-agent:gpu-agent "$TOKEN_DIR"
chmod 700 "$TOKEN_DIR"
chmod 600 "$TOKEN_DIR/token"
echo "✅ Token saved for gpu-connect-agent service."
echo "   Restart with: sudo systemctl restart gpu-connect-agent"
TOKEN_EOF
chmod +x /usr/local/bin/gpu-connect-token

echo "  Helper command installed: sudo gpu-connect-token <your_token>"
echo ""
