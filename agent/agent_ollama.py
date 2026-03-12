import asyncio
import json
import logging
import os
import sys
import uuid
import webbrowser
import aiohttp
import platform
from pathlib import Path

# Load .env.local if present (next to this script, next to the exe, or in parent dir)
def _load_env_local():
    """Load key=value pairs from .env.local into os.environ (won't overwrite existing vars)."""
    if getattr(sys, 'frozen', False):
        # PyInstaller bundled exe — check next to exe and parent of exe
        exe_dir = Path(sys.executable).resolve().parent
        candidates = [exe_dir / ".env.local", exe_dir.parent / ".env.local"]
    else:
        # Running as plain .py
        candidates = [Path(__file__).resolve().parent / ".env.local"]

    for env_path in candidates:
        if env_path.is_file():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    os.environ.setdefault(key.strip(), value.strip())
            break

_load_env_local()

# Configuration
SERVER_URL = os.environ.get("SERVER_URL", "wss://gpu-connect-api.onrender.com/ws/computing/")
API_URL = os.environ.get("API_URL", "https://gpu-connect-api.onrender.com")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
NODE_ID = os.environ.get("NODE_ID", f"node-{uuid.uuid4().hex[:8]}")

# Token storage
TOKEN_DIR = Path.home() / ".gpuconnect"
TOKEN_FILE = TOKEN_DIR / "token"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("GPU-Agent")


def save_token(token: str):
    """Save token to ~/.gpuconnect/token"""
    TOKEN_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(token, encoding='utf-8')
    # Restrict file permissions (owner-only on Unix, best-effort on Windows)
    try:
        TOKEN_FILE.chmod(0o600)
    except Exception:
        pass
    logger.info(f"Token saved to {TOKEN_FILE}")


def load_token() -> str | None:
    """Load token from ~/.gpuconnect/token"""
    if TOKEN_FILE.exists():
        token = TOKEN_FILE.read_text(encoding='utf-8').strip()
        if token.startswith("gpc_"):
            return token
    return None


def clear_token():
    """Delete stored token."""
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()


async def verify_token(token: str) -> bool:
    """Quick check that the token is still valid by calling the backend."""
    try:
        async with aiohttp.ClientSession() as session:
            # We'll test by connecting to WebSocket briefly
            async with session.ws_connect(SERVER_URL, heartbeat=10) as ws:
                await ws.send_str(json.dumps({
                    "type": "register",
                    "node_id": "verify-check",
                    "auth_token": token,
                    "gpu_info": {"models": [], "provider": "verify"}
                }))
                msg = await asyncio.wait_for(ws.receive(), timeout=5)
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    if data.get("type") == "registered":
                        return True
                    elif data.get("type") == "auth_error":
                        return False
                return False
    except Exception:
        return False


async def check_ollama_status():
    """Checks if local Ollama is running and lists models."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{OLLAMA_URL}/api/tags") as response:
                if response.status == 200:
                    data = await response.json()
                    models = [m['name'] for m in data.get('models', [])]
                    logger.info(f"Ollama connected. Available models: {models}")
                    return models
                else:
                    logger.error(f"Ollama returned status {response.status}")
                    return []
    except Exception as e:
        logger.error(f"Could not connect to Ollama at {OLLAMA_URL}: {e}")
        return []


async def execute_task(ws, task_data):
    """Executes a task on local Ollama, optionally streaming results."""
    task_id = task_data.get('task_id')
    owner_id = task_data.get('owner_id')
    model = task_data.get('model')
    prompt = task_data.get('prompt')
    stream = task_data.get('stream', False)

    logger.info(f"Executing Task {task_id}: model={model} prompt='{prompt[:50]}...' stream={stream}")

    full_response = ""
    try:
        async with aiohttp.ClientSession() as session:
            payload = {"model": model, "prompt": prompt, "stream": stream}
            async with session.post(
                f"{OLLAMA_URL}/api/generate",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=600)
            ) as response:
                if response.status == 200:
                    if stream:
                        # Read streaming chunks line by line
                        async for line in response.content:
                            if line:
                                try:
                                    chunk_data = json.loads(line.decode('utf-8'))
                                    chunk_text = chunk_data.get("response", "")
                                    full_response += chunk_text
                                    
                                    if chunk_text:
                                        # Send partial chunk to server
                                        stream_payload = json.dumps({
                                            "type": "job_stream",
                                            "result": {
                                                "task_id": task_id,
                                                "owner_id": owner_id,
                                                "chunk": chunk_text
                                            }
                                        }, ensure_ascii=False)
                                        await ws.send_str(stream_payload)
                                    
                                    if chunk_data.get("done"):
                                        break
                                except json.JSONDecodeError:
                                    continue
                        
                        logger.info(f"Streaming Task {task_id} Completed. ({len(full_response)} chars)")
                        return {"status": "success", "response": full_response, "task_id": task_id}
                    else:
                        result = await response.json()
                        output_text = result.get("response", "")
                        logger.info(f"Task {task_id} Completed. ({len(output_text)} chars)")
                        return {"status": "success", "response": output_text, "task_id": task_id}
                else:
                    error_text = await response.text()
                    logger.error(f"Task {task_id} Failed: Ollama {response.status}")
                    return {"status": "failed", "error": error_text[:500], "task_id": task_id}
    except asyncio.TimeoutError:
        logger.error(f"Task {task_id} timed out (600s)")
        return {"status": "failed", "error": "Inference timed out after 600s", "task_id": task_id}
    except Exception as e:
        logger.error(f"Task {task_id} Exception: {e}")
        return {"status": "failed", "error": str(e), "task_id": task_id}


async def handle_job(ws, job_data):
    """Run a job in the background and send the result back."""
    result = await execute_task(ws, job_data)
    try:
        payload = json.dumps({"type": "job_result", "result": result}, ensure_ascii=False)
        await ws.send_str(payload)
        logger.info(f"Result for Task {result.get('task_id')} sent successfully")
    except Exception as e:
        logger.error(f"Failed to send result for Task {result.get('task_id')}: {e}")


async def agent_loop(auth_token: str):
    """Main Agent Loop: Connects, Registers with token, Handles Tasks."""
    models = await check_ollama_status()
    if not models:
        logger.warning("No models found or Ollama not running.")

    logger.info(f"Starting agent with NODE_ID={NODE_ID}")

    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(SERVER_URL, heartbeat=20) as ws:
                    logger.info(f"Connected to Server at {SERVER_URL}")

                    # Register with agent token
                    register_msg = {
                        "type": "register",
                        "node_id": NODE_ID,
                        "auth_token": auth_token,
                        "gpu_info": {
                            "provider": "Ollama-Local",
                            "models": models,
                            "platform": platform.platform()
                        }
                    }
                    await ws.send_str(json.dumps(register_msg, ensure_ascii=False))

                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            msg_type = data.get("type")

                            if msg_type == "registered":
                                owner = data.get("owner", "unknown")
                                logger.info(f"✅ Node registered as {NODE_ID} (owner: {owner})")
                            elif msg_type == "auth_error":
                                logger.error(f"❌ Token rejected: {data.get('error')}")
                                clear_token()
                                logger.info("Stored token cleared. Please re-authenticate.")
                                print("\n  ❌ Authentication failed. Token revoked or invalid.")
                                input("  Press Enter to exit...")
                                return
                            elif msg_type == "job_dispatch":
                                asyncio.create_task(handle_job(ws, data.get("job_data")))
                            elif msg_type == "ping":
                                await ws.send_str(json.dumps({"type": "pong"}))

                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            logger.error(f"WebSocket error: {ws.exception()}")
                            break
                        elif msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSING, aiohttp.WSMsgType.CLOSED):
                            logger.warning("WebSocket closed by server")
                            break

        except aiohttp.ClientError as e:
            logger.error(f"Connection failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")

        logger.info("Reconnecting in 5 seconds...")
        await asyncio.sleep(5)


def get_dashboard_url():
    """Get the frontend dashboard URL."""
    frontend_url = os.environ.get("FRONTEND_URL", "https://gpu-connect.vercel.app")
    return f"{frontend_url}/dashboard?tab=provider"


def main():
    print(f"""
╔══════════════════════════════════════════════════════╗
║             GPU Connect Agent v2.1                  ║
║                                                      ║
║  Node ID:  {NODE_ID:<40} ║
║  Server:   {API_URL:<40} ║
║  Ollama:   {OLLAMA_URL:<40} ║
╚══════════════════════════════════════════════════════╝
""")

    # --- Check for stored token ---
    token = load_token()

    if token:
        print(f"  ✅ Found saved token: {token[:12]}...")
        print("  Verifying token...\n")
        # Don't verify interactively — just try to connect. 
        # If the token is invalid, the server will send auth_error 
        # and the agent will clear the token and exit.
    else:
        print("  ⚡ First-time setup — you need to generate an Agent Token.\n")
        print("  1. Open your browser to the GPU Connect Dashboard")
        print("  2. Go to the 'Provider' tab")
        print("  3. Click 'Generate Agent Token'")
        print("  4. Copy the token and paste it below\n")

        # Try to open browser
        dashboard_url = get_dashboard_url()
        print(f"  Opening {dashboard_url} ...\n")
        try:
            webbrowser.open(dashboard_url)
        except Exception:
            print(f"  (Could not open browser. Please navigate to {dashboard_url} manually)\n")

        token = input("  Paste your Agent Token: ").strip()

        if not token or not token.startswith("gpc_"):
            print("\n  ❌ Invalid token. Token must start with 'gpc_'.")
            print("  Generate one from the Dashboard → Provider tab.\n")
            input("  Press Enter to exit...")
            return

        save_token(token)
        print(f"\n  ✅ Token saved to {TOKEN_FILE}")
        print("  You won't need to paste it again.\n")

    print("  Starting GPU agent...\n")

    try:
        asyncio.run(agent_loop(token))
    except KeyboardInterrupt:
        logger.info("Agent stopped by user")


if __name__ == "__main__":
    main()
