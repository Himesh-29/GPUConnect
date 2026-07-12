# GPU Connect — Codex Instructions

This file provides instructions for OpenAI Codex CLI.
For the full skill library and detailed workflows, see `.agents/AGENTS.md` and `.agents/skills/`.

## Quick Reference

### Project Structure
- **Backend**: `backend/` — Django + DRF, managed with `uv` (NOT pip)
- **Frontend**: `frontend/` — React + TypeScript, managed with `npm`
- **Agent**: `agent/` — Python CLI, packaged as binaries for Windows/Linux/macOS
- **CI**: `.github/workflows/` — test-and-quality.yml, security-scan.yml, deploy.yml

### Key Rules
1. Use `uv` for ALL backend dependency management (never `pip` directly).
2. When upgrading backend deps, update BOTH `requirements.txt` AND `uv.lock`:
   ```bash
   cd backend
   uv pip compile pyproject.toml --upgrade -o requirements.txt
   uv lock --upgrade
   ```
3. When upgrading frontend deps, update `package.json` explicitly (not just the lock file).
4. Keep the `overrides` section in `frontend/package.json` in sync with upgraded versions.
5. Rebuild agent binaries after backend dependency changes: `make agent` or `.\make.bat agent`.
6. Always verify fixes: `npm audit --audit-level=high --omit=dev` and check pip-audit.
7. Update `RELEASES.md` for every security patch release.

### Commit Style
- Imperative mood subject line
- Body as bulleted list via separate `-m` flags
- Example: `git commit -m "Patch X vulnerability" -m "- Upgraded Y to Z"`

### For Security Vulnerability Remediation
Read the full step-by-step guide: `.agents/skills/remediate-vulnerabilities/SKILL.md`
Read real examples: `.agents/skills/remediate-vulnerabilities/references/past-remediations.md`
