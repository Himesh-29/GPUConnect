# Past Vulnerability Remediations — Reference Examples

This file contains real examples from past security patch releases to help AI assistants
match the exact output format and style expected by the maintainer.

---

## Example 1: v1.0.5 — Single Backend CVE (idna)

### Commit Message
```
Patch idna vulnerability and rebuild agent binaries

- Fixed CVE-2026-45409 by updating idna to >=3.15 (resolved to 3.17) in backend dependencies
- Rebuilt Windows, Linux, and macOS agent packages to bundle the updated dependency
```

### RELEASES.md Entry
```markdown
## [v1.0.5](https://github.com/Himesh-29/GPUConnect/releases/tag/v1.0.5) — Security Patch & Agent Rebuild

**Release Date**: May 31, 2026

### 🛡️ Security
This release is a dedicated security patch that resolves a medium-severity vulnerability in the `idna` dependency.

**Backend (`pyproject.toml`, `uv.lock`, `requirements.txt`)**
- Upgraded `idna` dependency to `>=3.15` (resolved to `3.17`) to fix CVE-2026-45409.

### 📦 Agent Downloads (Updated)
The agent packages have been recompiled to bundle the updated dependencies and are available at [gpu-connect.vercel.app](https://gpu-connect.vercel.app):

| Platform | File |
|----------|------|
| Windows | `gpu-connect.exe` |
| Linux | `gpu-connect-agent-linux.zip` |
| macOS | `gpu-connect-agent-macos.zip` |
```

### GitHub Release Title
```
v1.0.5 — Security Patch & Agent Rebuild Latest
```

---

## Example 2: v1.0.6 — Backend + Frontend Combined

### Commit Messages (multiple commits)
```
Patch multiple vulnerabilities and rebuild agent binaries
- Fixed 29 known vulnerabilities by updating packages in backend dependencies
- Rebuilt Windows agent package to bundle the updated dependencies

Fix frontend vulnerabilities and update RELEASES.md
- Updated package.json and package-lock.json to resolve 13 vulnerabilities
- Updated RELEASES.md with frontend security patches

Fix backend vulnerabilities in uv.lock and update RELEASES.md
- Upgraded dependencies in uv.lock to resolve vulnerabilities identified by Trivy
- Updated RELEASES.md to include uv.lock
```

### RELEASES.md Entry
```markdown
## [v1.0.6](https://github.com/Himesh-29/GPUConnect/releases/tag/v1.0.6) — Security Patch & Agent Rebuild

**Release Date**: June 24, 2026

### 🛡️ Security
This release is a dedicated security patch that resolves multiple high and critical vulnerabilities in both backend and frontend dependencies.

**Backend (`pyproject.toml`, `uv.lock`, `requirements.txt`)**
- Upgraded multiple vulnerable dependencies to their latest secure versions to fix vulnerabilities identified by pip-audit and Trivy.

**Frontend (`package.json`, `package-lock.json`)**
- Resolved 13 vulnerabilities (including high and critical severity in `react-router`, `react-router-dom`, and `form-data`) via `npm audit fix` for production dependencies.

### 📦 Agent Downloads (Updated)
The agent packages have been recompiled to bundle the updated dependencies and are available at [gpu-connect.vercel.app](https://gpu-connect.vercel.app):

| Platform | File |
|----------|------|
| Windows | `gpu-connect.exe` |
| Linux | `gpu-connect-agent-linux.zip` |
| macOS | `gpu-connect-agent-macos.zip` |
```

### PR Description
```markdown
## Description
This PR remediates known security vulnerabilities identified in both the backend and frontend dependencies.

**Backend:**
- Remediates 29 vulnerabilities identified by `pip-audit`.
- Upgrades vulnerable packages in `backend/requirements.txt` to their latest secure versions via `uv pip compile --upgrade`.
- Recompiles the Windows agent package (`gpu-connect.exe`) to bundle the updated secure dependencies.

**Frontend:**
- Remediates 13 vulnerabilities (including High and Critical severity) identified by `npm audit` in production dependencies.
- Explicitly bumps `react-router-dom` and `axios` in `package.json` to their secure versions, and updates `package-lock.json` via `npm install` and `npm audit fix`.

**Documentation:**
- Updates `RELEASES.md` with the new `v1.0.6` release notes documenting these security patches.

## Type of change
- [x] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [x] Documentation update

## How Has This Been Tested?
- [x] Unit tests
  - Ran `npm run test` in the frontend; verified all 42 tests pass successfully.
- [x] Manual testing
  - Ran `pip-audit` on the backend after the dependency upgrades, verifying that all 29 vulnerabilities were successfully resolved and it now reports 0 vulnerabilities.
  - Ran `npm audit --audit-level=high --omit=dev` on the frontend, verifying that it now reports 0 vulnerabilities in production dependencies.
  - Successfully rebuilt the agent binaries locally via `make agent` and verified their presence in the `frontend/public/downloads/` directory.
  - Successfully ran `npm run build` to verify frontend build integrity.

## Checklist:
- [x] My code follows the style guidelines of this project
- [x] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas *(N/A for dependency updates)*
- [x] I have made corresponding changes to the documentation
- [x] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works *(N/A for dependency updates)*
- [x] New and existing unit tests pass locally with my changes
```

---

## Example 3: v1.0.7 — Backend + CI Fix

### Commit Messages
```
Patch remaining backend vulnerabilities and rebuild agent binaries
- Upgraded all backend dependencies in requirements.txt and uv.lock to fix 3 vulnerabilities identified by pip-audit
- Rebuilt Windows, Linux, and macOS agent packages to bundle the updated dependencies

fix: exclude .venv and site-packages from radon analysis to reduce CI runtime

Update RELEASES.md for v1.0.7 with CI fix details
```

### RELEASES.md Entry
```markdown
## [v1.0.7](https://github.com/Himesh-29/GPUConnect/releases/tag/v1.0.7) — Security Patch & Agent Rebuild Latest

**Release Date**: July 12, 2026

### 🛡️ Security
This release is a dedicated security patch that resolves remaining vulnerabilities in the backend dependencies identified by pip-audit and Trivy.

**Backend (`pyproject.toml`, `uv.lock`, `requirements.txt`)**
- Upgraded all vulnerable dependencies to their latest secure versions to fix 3 remaining vulnerabilities identified by pip-audit.

### 🔧 CI Fixes

**Test & Code Quality Workflow (`.github/workflows/test-and-quality.yml`)**
- Excluded `.venv`, `venv`, and `site-packages` directories from `radon` cyclomatic complexity and maintainability index analysis to prevent scanning third-party packages and reduce CI runtime.

### 📦 Agent Downloads (Updated)
The agent packages have been recompiled to bundle the updated dependencies and are available at [gpu-connect.vercel.app](https://gpu-connect.vercel.app):

| Platform | File |
|----------|------|
| Windows | `gpu-connect.exe` |
| Linux | `gpu-connect-agent-linux.zip` |
| macOS | `gpu-connect-agent-macos.zip` |
```
