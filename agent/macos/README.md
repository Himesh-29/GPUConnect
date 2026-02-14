# GPU Connect Agent — macOS

Run the GPU Connect agent on your Mac to share Ollama inference as a compute provider. On Apple Silicon Macs, Ollama uses **Metal GPU acceleration** for fast local inference.

## Requirements

- **macOS 12 (Monterey) or later**
- **Python 3.9+** (pre-installed on modern macOS, or via `brew install python3`)
- **Ollama** installed and running
- Internet connection

## Quick Start

### 1. Extract the package

```bash
tar xzf gpu-connect-agent-macos.tar.gz
cd gpu-connect-agent-macos
```

### 2. Install

```bash
chmod +x install.sh
./install.sh
```

This will:
- Create a virtual environment at `~/.gpu-connect-agent/`
- Install a macOS LaunchAgent for auto-start
- Add helper commands to your PATH

### 3. Install Ollama

```bash
brew install ollama
```

Or download from [ollama.com/download/mac](https://ollama.com/download/mac).

Then pull a model:

```bash
ollama pull tinyllama
```

### 4. Set your agent token

Get a token from the GPU Connect Dashboard → Provider tab, then:

```bash
gpu-connect-token gpc_your_token_here
```

### 5. Start the agent

```bash
gpu-connect-start
```

## Commands

| Command | Description |
|---------|-------------|
| `gpu-connect-start` | Start the agent |
| `gpu-connect-stop` | Stop the agent |
| `gpu-connect-status` | Check if the agent is running |
| `gpu-connect-token <token>` | Set or update your agent token |

## Logs

```bash
# Live log stream
tail -f ~/.gpu-connect-agent/agent.log

# Error log
tail -f ~/.gpu-connect-agent/agent.err.log
```

## Configuration

Set environment variables in the LaunchAgent plist or export them before running manually:

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVER_URL` | `wss://gpu-connect-api.onrender.com/ws/computing/` | WebSocket server |
| `API_URL` | `https://gpu-connect-api.onrender.com` | REST API endpoint |
| `OLLAMA_URL` | `http://localhost:11434` | Local Ollama address |
| `NODE_ID` | auto-generated | Unique node identifier |

To set custom env vars, edit the plist:

```bash
open ~/Library/LaunchAgents/com.gpuconnect.agent.plist
```

Add entries under the `EnvironmentVariables` dict, then restart:

```bash
gpu-connect-stop
gpu-connect-start
```

## Running Manually

```bash
cd ~/.gpu-connect-agent
source venv/bin/activate
python agent_ollama.py
```

## Performance Notes

- **Apple Silicon (M1/M2/M3/M4)**: Ollama uses Metal GPU acceleration — expect fast inference even on larger models (llama3, mistral, etc.)
- **Intel Macs**: CPU-only inference — best with smaller models (tinyllama, phi-3-mini, gemma:2b)
- Recommended: at least 8 GB RAM for most models

## Uninstall

```bash
cd gpu-connect-agent-macos
./uninstall.sh
```

## Troubleshooting

**Agent won't connect:**
- Check internet: `ping google.com`
- Check Ollama is running: `curl http://localhost:11434/api/tags`
- Check logs: `tail -f ~/.gpu-connect-agent/agent.log`

**Token rejected:**
- Generate a new token from the Dashboard
- `gpu-connect-token gpc_new_token`
- `gpu-connect-stop && gpu-connect-start`

**Ollama not found:**
- Install via `brew install ollama`
- Or download from https://ollama.com/download/mac
- Make sure Ollama app is running (check menu bar)

**Permission denied on install:**
- If symlinks fail, run: `sudo ./install.sh`
