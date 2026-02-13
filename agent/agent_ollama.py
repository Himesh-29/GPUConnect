import asyncio
import json
import logging
import os
import sys
import aiohttp
import platform

# Configuration
SERVER_URL = os.environ.get("SERVER_URL", "ws://localhost:8000/ws/computing/")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
NODE_ID = os.environ.get("NODE_ID", "local-node-1")
AUTH_TOKEN = os.environ.get("AUTH_TOKEN", "dummy-token") # Replace with real token flow later

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("GPU-Agent")

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

async def execute_task(task_data):
    """Executes a task on local Ollama."""
    task_id = task_data.get('task_id')
    model = task_data.get('model')
    prompt = task_data.get('prompt')
    
    logger.info(f"Executing Task {task_id}: Run {model} with prompt '{prompt}'")
    
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False
            }
            async with session.post(f"{OLLAMA_URL}/api/generate", json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Task {task_id} Completed.")
                    return {"status": "success", "response": result.get("response"), "task_id": task_id}
                else:
                    logger.error(f"Task {task_id} Failed: Ollama Error {response.status}")
                    return {"status": "failed", "error": f"Ollama status {response.status}", "task_id": task_id}
    except Exception as e:
        logger.error(f"Task {task_id} Exception: {e}")
        return {"status": "failed", "error": str(e), "task_id": task_id}

async def agent_loop():
    """Main Agent Loop: Connects to Server, Registers, and Handles Tasks."""
    models = await check_ollama_status()
    if not models:
        logger.warning("No models found or Ollama not running. Agent starting anyway but may not invoke LLMs.")
    
    headers = {"Authorization": f"Bearer {AUTH_TOKEN}"}
    
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(SERVER_URL, headers=headers) as ws:
            logger.info(f"Connected to Server at {SERVER_URL}")
            
            # 1. Register
            register_msg = {
                "type": "register",
                "node_id": NODE_ID,
                "gpu_info": {
                    "provider": "Ollama-Local",
                    "models": models,
                    "platform": platform.platform()
                }
            }
            await ws.send_json(register_msg)
            
            # 2. Loop
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    msg_type = data.get("type")
                    
                    if msg_type == "job_dispatch":
                        # Execute Job
                        result = await execute_task(data.get("job_data"))
                        # Send Result
                        await ws.send_json({
                            "type": "job_result",
                            "result": result
                        })
                    elif msg_type == "ping":
                         await ws.send_json({"type": "pong"})
                         
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"WebSocket connection closed with exception {ws.exception()}")
                    break

if __name__ == "__main__":
    try:
        asyncio.run(agent_loop())
    except KeyboardInterrupt:
        pass
