# GPU Connect Releases

## [v1.0.3](https://github.com/Himesh-29/GPUConnect/releases/tag/v1.0.3) — Real-Time Chat Streaming & UI Polish

**Release Date**: March 13, 2026

### 🎉 Highlights

Live response streaming with token-by-token rendering, optimistic UI updates for instant feedback, and a fully redesigned chat experience with maximized screen real estate.

### ✨ New Features

#### ⚡ Real-Time Response Streaming
- Agent streams Ollama responses **token by token** back to the frontend via WebSocket
- New `job_stream` message type routes chunks through Django Channels to the user's dashboard
- Optional **+5% cost surcharge** ($1.05 vs $1.00) for streaming — toggled via a premium slider switch in the chat footer

#### 🚀 Optimistic UI Updates
- User prompts appear **instantly** in the chat window — no waiting for the API round-trip
- Animated 3-dot "thinking" indicator while the job is pending
- Temporary job entries are replaced with real server IDs once confirmed

#### 💬 Chat Session History (Database-Backed)
- New `ChatSession` model persists all chat sessions in the database
- REST endpoints for creating, listing, renaming, and deleting sessions
- Jobs are linked to sessions via foreign key — full history retrieval on reload

#### 🎨 Playground Layout Overhaul
- Chat window now fills **~85% of viewport height** — removed global stat cards
- User balance displayed inline within the chat input footer
- Chat input field always visible at the bottom — no more scrolling

### 🔧 Improvements

- **Chat name editing**: Inline rename with ✅ green checkmark (works on mobile + PC via Enter key)
- **Recent Chats cards**: Yellow/black theme with model info and cost details on the Overview page
- **Dropdown animations**: All dropdowns now have smooth open/close hover transitions
- **Chat name persistence**: Fixed bug where renamed sessions didn't persist after page refresh
- **Stream toggle**: Premium custom slider switch replaces raw checkbox

### 🏗️ Architecture Changes

| Component | Change |
|-----------|--------|
| `backend/computing/views.py` | `stream` parameter + dynamic cost ($1.00 / $1.05) |
| `backend/computing/consumers.py` | `job_stream` event routing to user channel groups |
| `backend/computing/models.py` | `ChatSession` model with job foreign key |
| `agent/agent_ollama.py` | Async line-by-line streaming from Ollama API |
| `frontend/DashboardContext.tsx` | `job_stream` handler + optimistic job insertion |
| `frontend/Dashboard.tsx` | Streaming render, thinking animation, stream toggle |

### 🛡️ CI Updates

- Added `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true` to all GitHub Actions workflows to resolve Node.js 20 deprecation warnings

### 📦 Agent Downloads (Updated)

Rebuilt with streaming support — available at [gpu-connect.vercel.app](https://gpu-connect.vercel.app):

| Platform | File |
|----------|------|
| Windows | `gpu-connect.exe` |
| Linux | `gpu-connect-agent-linux.zip` |
| macOS | `gpu-connect-agent-macos.zip` |

---


## [v1.0.2](https://github.com/Himesh-29/GPUConnect/releases/tag/v1.0.2) — CI, coverage, and deployment fixes

**Release Date**: February 15, 2026

### 🔧 Improvements & Fixes

- Increased test coverage from ~75% to 95% by adding and improving tests across `computing`, `core`, and `payments` (195 tests total).
- Fixed Pylint false positives by adding `pylint-django` and cleaning up lint issues.
- Stabilized serializers and tests (read-only field handling, async test fixes) and added `pytest-asyncio` support.
- Hardened the deployment workflow:
  - Validates deploy configuration before attempting deployments and fails fast with clear errors.
  - Added `workflow_dispatch` for safe manual deploys and clearer logs.
  - Added `DEPLOYMENT.md` with setup instructions and troubleshooting for maintainers.
  - Improved Vercel and Render integration and clearer error messages.

### CI Workflows

- `Test & Code Quality` (CI):
	- Runs unit and async tests, enforces a coverage gate (historically 70%; current coverage: ~95%).
	- Runs static analysis (`pylint` with `pylint-django`), `radon` complexity checks, and other quality gates.
	- On success, it triggers the deploy workflow via `workflow_run`.

- `Security Scan`:
	- Runs repository security checks including CodeQL analysis and dependency scanning.
	- Reports potential vulnerabilities and fails on critical findings to prevent risky deployments.

Maintenance / Next Steps

- Review deployment configuration and environment protections in the repository settings as needed. See `DEPLOYMENT.md` for internal setup and troubleshooting.

---

## [v1.0.1](https://github.com/Himesh-29/GPUConnect/releases/tag/v1.0.1) — OAuth Fix for Chrome & Incognito

**Release Date**: February 15, 2026

### 🐛 Bug Fix

Fixed OAuth login (Google, GitHub, Microsoft) failing with "Authentication failed, try again" in Chrome, Firefox, Safari, and all incognito/private browsing modes.

### Root Cause

The OAuth flow relied on **cross-site cookies** to exchange a Django session for JWT tokens. After OAuth with Google/GitHub completed, the backend set a session cookie on `onrender.com`, then redirected to the frontend on `vercel.app`. When the frontend called the backend API to exchange the session for JWT, browsers blocked the session cookie as a **third-party cookie** — resulting in a 401 "Not authenticated" error.

This worked in Edge (normal mode) because Edge has a more lenient third-party cookie policy, but failed everywhere else.

### The Fix

Redesigned the OAuth callback flow to eliminate cross-site cookie dependency entirely:

**Before (broken in Chrome):**
```
Frontend (vercel.app) → Backend OAuth → Set session cookie (onrender.com)
→ Redirect to frontend → Frontend calls backend API with cookie
→ ❌ Cookie blocked as third-party → 401 error
```

**After (works everywhere):**
```
Frontend (vercel.app) → Backend OAuth → Set session cookie (onrender.com)
→ Redirect to backend /api/auth/oauth/callback/complete/ (same domain — cookie works ✅)
→ Backend reads session, generates JWT tokens
→ Redirect to frontend with tokens in URL hash fragment
→ Frontend reads tokens from hash — no API call, no cookies needed ✅
```

### Files Changed

- `backend/core/oauth_views.py` — New `OAuthCompleteView` that generates JWT and redirects with tokens in URL fragment
- `backend/core/oauth_urls.py` — Added `/complete/` route
- `backend/config/settings.py` — `LOGIN_REDIRECT_URL` now points to backend instead of frontend
- `frontend/src/pages/OAuthCallback.tsx` — Reads tokens from URL hash instead of making API call; cleans hash from browser history

### Security Notes

- JWT tokens are passed via URL **fragment** (`#`), which is never sent to servers or logged
- Tokens are cleaned from browser history immediately after reading
- Legacy session-exchange endpoint kept for backward compatibility

---

## [v1.0.0](https://github.com/Himesh-29/GPUConnect/releases/tag/v1.0.0) — Cross-Platform & Production Ready

**Release Date**: February 14, 2026

### 🎉 Highlights

Full cross-platform support for Windows, Linux (including Raspberry Pi 5), and macOS. Agent packages now available for download directly from the web interface.

### ✨ New Features

#### 🖥️ Cross-Platform Agent Support

- **Windows**: Standalone `.exe` executable via PyInstaller
- **Linux**: Systemd-based installation for Raspberry Pi and Ubuntu/Debian systems
- **macOS**: LaunchAgent-based auto-start with Metal GPU acceleration support on Apple Silicon

#### 📦 Easy Installation

- One-click downloads from [gpu-connect.vercel.app/integrate](https://gpu-connect.vercel.app/#integrate)
- Platform-specific installers (`install.sh` for Linux/macOS)
- Comprehensive installation guides included in each package
- Helper commands for token management and service control

#### 🐧 Linux Agent (`agent/linux/`)

- Installs to `/opt/gpu-connect-agent/` with systemd service
- Auto-start on boot with `systemctl enable gpu-connect-agent`
- Service restart on failure with 10-second throttle interval
- Verified on Raspberry Pi 5 (aarch64, armv7l) and Ubuntu 22.04+

#### 🍎 macOS Agent (`agent/macos/`)

- Installs to `~/.gpu-connect-agent/` with LaunchAgent for login session auto-start
- Metal GPU acceleration support for Apple Silicon (M1/M2/M3/M4)
- Helper commands: `gpu-connect-start`, `gpu-connect-stop`, `gpu-connect-status`, `gpu-connect-token`
- Tested on macOS 12+ (Intel and Apple Silicon)

#### 🔌 Health Check Endpoint

- New `/api/core/health/` endpoint for monitoring and cron jobs
- **No authentication required** — prevents 401 errors that disable Render deployment
- Returns service status, timestamp, and version info
- Ideal for keeping production deployments active

#### 🎯 Frontend Enhancements

- Updated Integrate section with platform-specific download buttons
- Windows (⊞), Linux (🐧), and macOS () download links
- Fixed Vercel routing to allow direct file downloads from `/downloads/`

#### 📊 Build System Updates

- `make agent` now builds all three platforms in one command
- Automatic package generation and copying to frontend downloads folder
- Organized build artifacts: `agent/windows/`, `agent/linux/`, `agent/macos/`

### 🐛 Bug Fixes

- Fixed Vercel routing intercepting `/downloads/` files (now served as static files)
- Download buttons now properly serve agent packages instead of returning index.html
- Build script paths corrected for new directory structure
- Agent packages now included in Vercel deployments

### 📝 Documentation

- New [INSTALLATION.md](INSTALLATION.md) with complete platform-specific guides
- SSH/Remote installation guides for Raspberry Pi and Linux servers
- Troubleshooting sections for each platform
- Quick copy-paste installation commands

### 🏗️ Architecture Changes

**Agent Directory Restructure:**
```
agent/
├── windows/
│   ├── build_agent.bat
│   └── gpu-connect-agent.exe
├── linux/
│   ├── install.sh / uninstall.sh
│   ├── build_linux.bat / build_linux.sh
│   ├── requirements.txt
│   └── README.md
├── macos/
│   ├── install.sh / uninstall.sh
│   ├── build_macos.bat / build_macos.sh
│   ├── requirements.txt
│   └── README.md
└── agent_ollama.py (shared)
```

### 🚀 Deployment Notes

**For Vercel:**
- Updated `vercel.json` to exclude `/downloads/` from SPA routing
- Download files now included in deployments via `.gitignore` exceptions
- Deploy triggers automatic Vercel build with agent packages

**For Render (Backend):**
- Health check endpoint ready: `https://gpu-connect-api.onrender.com/api/core/health/`
- Use this URL in cron jobs instead of `/profile/` to keep deployment active
- No authentication required — prevents 401 errors

### 📦 Downloads

Available at [gpu-connect.vercel.app](https://gpu-connect.vercel.app):

| Platform | File | Size |
|----------|------|------|
| Windows | `gpu-connect.exe` | 11 MB |
| Linux | `gpu-connect-agent-linux.zip` | 8 KB |
| macOS | `gpu-connect-agent-macos.zip` | 8 KB |

---

## v0.1.0 — Initial Release
