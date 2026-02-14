# GPU Connect Agent — Linux

Run the GPU Connect agent on any Linux machine to share Ollama inference as a compute provider.

## Requirements

- **Any Linux system** (x86_64, aarch64/ARM64, or armv7l)
- **Python 3.9+**
- **Ollama** installed and running
- Internet connection

## Quick Start

### 1. Transfer the package to your Linux machine

From your PC, copy the package:

```bash
scp gpu-connect-agent-linux.zip user@<host-ip>:~/
```

### 2. Install

SSH into your machine and run:

```bash
unzip gpu-connect-agent-linux.zip -d gpu-connect-agent
cd gpu-connect-agent
chmod +x install.sh uninstall.sh
sudo ./install.sh
```

This will:
- Install Python 3 and create a virtual environment
- Copy the agent to `/opt/gpu-connect-agent/`
- Create a systemd service for auto-start
- Install a helper command for token setup

### 3. Install Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull tinyllama    # or any model you want to share
```

### 4. Set your agent token

Get a token from the GPU Connect Dashboard → Provider tab, then:

```bash
sudo gpu-connect-token gpc_your_token_here
```

### 5. Start the service

```bash
sudo systemctl start gpu-connect-agent
sudo systemctl enable gpu-connect-agent   # auto-start on boot
```

## Management

| Action | Command |
|--------|---------|
| Start agent | `sudo systemctl start gpu-connect-agent` |
| Stop agent | `sudo systemctl stop gpu-connect-agent` |
| View logs | `journalctl -u gpu-connect-agent -f` |
| Check status | `sudo systemctl status gpu-connect-agent` |
| Update token | `sudo gpu-connect-token gpc_new_token` |
| Restart | `sudo systemctl restart gpu-connect-agent` |

## Configuration

Edit `/etc/gpu-connect-agent.env` to customize:

```bash
sudo nano /etc/gpu-connect-agent.env
```

Available variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVER_URL` | `wss://gpu-connect-api.onrender.com/ws/computing/` | WebSocket server |
| `API_URL` | `https://gpu-connect-api.onrender.com` | REST API endpoint |
| `OLLAMA_URL` | `http://localhost:11434` | Local Ollama address |
| `NODE_ID` | auto-generated | Unique node identifier |
| `FRONTEND_URL` | `https://gpu-connect.vercel.app` | Dashboard URL |

After changing config, restart:

```bash
sudo systemctl restart gpu-connect-agent
```

## Running Manually (without systemd)

If you prefer to run the agent directly:

```bash
cd /opt/gpu-connect-agent
source venv/bin/activate
python agent_ollama.py
```

## Performance Notes

- On GPU-equipped machines, Ollama will use CUDA/ROCm automatically for fast inference
- On CPU-only or ARM devices (e.g. Raspberry Pi), small models work well (tinyllama, phi-3-mini, gemma:2b)
- Set `OLLAMA_NUM_PARALLEL=1` in Ollama's config to avoid OOM on limited RAM

## Uninstall

```bash
cd ~/gpu-connect-agent
sudo ./uninstall.sh
```

## Troubleshooting

**Agent won't connect:**
- Check internet: `ping google.com`
- Check Ollama is running: `curl http://localhost:11434/api/tags`
- Check logs: `journalctl -u gpu-connect-agent -f`

**Token rejected:**
- Generate a new token from the Dashboard
- `sudo gpu-connect-token gpc_new_token`
- `sudo systemctl restart gpu-connect-agent`

**Ollama not found:**
- Make sure Ollama is installed: `which ollama`
- Start it: `sudo systemctl start ollama`
