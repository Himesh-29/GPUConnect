# GPU Connect - Decentralized AI Compute Marketplace

**GPU Connect** is a next-generation decentralized platform that connects AI researchers with idle GPU power. By leveraging a peer-to-peer architecture, it enables instant access to high-performance LLMs and compute resources at a fraction of cloud costs.

![Status](https://img.shields.io/badge/Status-Beta-gold?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)
![Stack](https://img.shields.io/badge/Tech-Django%20%7C%20React%20%7C%20Ollama-black?style=flat-square)

## 🚀 Key Features

*   **🎨 Premium Dark UI**: A completely redesigned "Midnight Gold" aesthetic featuring glassmorphism, smooth animations, and high-contrast typography for a professional experience.
*   **🔒 Secure Provider Authentication**: **Browser-based token flow** replaces insecure password prompts. Agents authenticate via cryptographically secure tokens (`gpc_...`) managed from the dashboard.
*   **💰 Provider Economy**: Earn credits ($0.80/job) for sharing your GPU. Detailed **Provider Analytics** dashboard features earnings charts, job history, model breakdown, and transaction logs.
*   **🧠 Dynamic Marketplace**: Real-time discovery of available models. The platform automatically aggregates models (Llama 3, Mistral, Gemma) from all connected providers.
*   **⚡ Zero-Config Agent**: Download the standalone agent (`.exe`), paste your token, and start earning. No Python or complex setup required.
*   **📊 Live Real-Time Stats**: Watch the network pulse with live stats on active nodes, completed jobs, and earnings updating every second.

## 🛠️ Tech Stack

### Backend (The Brain)
*   **Framework**: Python Django 5.0 + Django REST Framework
*   **Real-time**: Django Channels (WebSockets) + Asyncio
*   **Database**: PostgreSQL / SQLite (Dev)
*   **Security**: SHA-256 Hashed Agent Tokens + JWT Context

### Frontend (The Face)
*   **Framework**: React + TypeScript + Vite
*   **Visualization**: Recharts for analytics (Area, Bar, Pie charts)
*   **Styling**: Custom CSS Variables, Glassmorphism
*   **State**: Real-time Polling + React Hooks

### Agent (The Muscle)
*   **Core**: Python + Aiohttp
*   **Auth**: Browser-based token flow + Local secure storage (`~/.gpuconnect/token`)
*   **Distribution**: PyInstaller Standalone Executable
*   **Discovery**: Auto-detects local Ollama models

## 🏃‍♂️ Quick Start

### For Consumers (Rent Compute)
1.  **Register**: Create an account at `http://localhost:5173/register`.
2.  **Explore**: Browse the **Marketplace** to see live models.
3.  **Compute**: Go to the **Dashboard**, add funds (simulated), select a model, and submit your prompt.

### For Providers (Earn Credits)
1.  **Install Ollama**: [Download Ollama](https://ollama.com/) and pull models (e.g., `ollama pull llama3.2`).
2.  **Get Your Token**:
    *   Log in to the **Dashboard** (`http://localhost:5173`).
    *   Go to the **Provider** tab.
    *   Click **Generate Agent Token** and copy it.
3.  **Run the Agent**:
    *   Download `gpu-connect.exe` (or run from source).
    *   Run it: `.\gpu-connect-agent.exe`
    *   **Paste your token** when prompted.
4.  **Earn**: Your node registers securely and starts accepting jobs. Track earnings live in the Provider Dashboard!

## 💻 Developer Setup

### Prerequisites
*   Python 3.11+
*   Node.js 18+
*   `uv` (Python Package Manager)

### 1. Clone & Environment
```bash
git clone https://github.com/Himesh-29/GPUConnect.git
cd GPUConnect
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
