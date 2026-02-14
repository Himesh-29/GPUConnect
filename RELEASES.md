# GPU Connect Releases

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
