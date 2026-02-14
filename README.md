# GPU Connect - Decentralized AI Compute Marketplace

**GPU Connect** is a next-generation decentralized platform that connects AI researchers with idle GPU power. By leveraging a peer-to-peer architecture, it enables instant access to high-performance LLMs and compute resources at a fraction of cloud costs.

![Status](https://img.shields.io/badge/Status-Beta-gold?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)
![Stack](https://img.shields.io/badge/Tech-Django%20%7C%20React%20%7C%20Ollama-black?style=flat-square)

## 🚀 Key Features

*   **🎨 Premium Dark UI**: A completely redesigned "Midnight Gold" aesthetic featuring glassmorphism, smooth animations, and high-contrast typography for a professional experience.
*   **🧠 Dynamic Marketplace**: Real-time discovery of available models. The platform automatically aggregates models (Llama 3, Mistral, Gemma, etc.) from all connected providers.
*   **⚡ Zero-Config Provider Agent**: providers can join the network in seconds by downloading a standalone executable (`.exe`) - **no Python or complex setup required**.
*   **🔄 Unified User Roles**: Everyone is a peer. A single account allows you to both rent GPU power (Consumer) and monetize your own hardware (Provider).
*   **📊 Live Real-Time Dashboard**: Watch the network pulse with live stats on active nodes, completed jobs, and model availability, updating every second without page refreshes.

## 🛠️ Tech Stack

### Backend (The Brain)
*   **Framework**: Python Django 5.0 + Django REST Framework
*   **Real-time**: Django Channels (WebSockets) + Asyncio
*   **Database**: PostgreSQL / SQLite (Dev)
*   **AI Engine**: Ollama (Local LLM Inference)

### Frontend (The Face)
*   **Framework**: React + TypeScript + Vite
*   **Styling**: Custom CSS Variables, Glassmorphism, Inter/Space Grotesk Typography
*   **State**: Real-time Polling + React Hooks

### Agent (The Muscle)
*   **Core**: Python + Aiohttp
*   **Distribution**: PyInstaller Standalone Executable (Windows/Linux)
*   **Discovery**: Auto-detects local Ollama models

## 🏃‍♂️ Quick Start

### For Consumers (Rent Compute)
1.  **Register**: Create an account at `http://localhost:5173/register`.
2.  **Explore**: Browse the **Marketplace** to see live models.
3.  **Compute**: Go to the **Dashboard**, select a model (e.g., `llama3.2`), and submit your prompt.

### For Providers (Earn Credits)
1.  **Install Ollama**: [Download Ollama](https://ollama.com/) and pull your favorite models (e.g., `ollama pull llama3.2`).
2.  **Download Agent**: Get the standalone **GPU Connect Agent** from the "Run a Node" section on the homepage.
3.  **Run**: Double-click the executable (or run `.\gpu-connect.exe`).
4.  **Earn**: Your node automatically registers, lists its models, and begins accepting jobs.

## 💻 Developer Setup

### Prerequisites
*   Python 3.11+
*   Node.js 18+
*   `uv` (Python Package Manager)

### 1. Clone & Environment
```bash
git clone https://github.com/Himesh-29/GPU-For-Everyone.git
cd GPU-For-Everyone
```

### 2. Backend Setup
```bash
# Create virtual env & install dependencies
uv venv .venv
.\.venv\Scripts\Activate.ps1
uv pip install -r backend/requirements.txt

# Run Migrations
cd backend
python manage.py migrate

# Start Server
python manage.py runserver
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Visit `http://localhost:5173` to launch the application.

## ⚙️ Make Commands

Run from the project root (Windows: `.\make.bat`, Linux/Mac: `make`):

| Command | Description |
|---------|-------------|
| `make agent` | Build standalone `gpu-connect-agent.exe` via PyInstaller |
| `make clean` | Remove all build artifacts (build/, dist/, .spec) |
| `make dev` | Start backend + frontend dev servers in new windows |
| `make test` | Run the full backend test suite |
| `make help` | Show all available commands |

## 🧪 Testing

Run the full backend test suite:
```bash
cd backend
uv run pytest
```

## 📜 License
MIT License.
