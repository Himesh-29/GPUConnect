# GPU Connect — Agent Rules

## Project Overview
GPU Connect is a decentralized AI compute marketplace. It has three main components:
- **Backend** (`backend/`): Django REST API managed with `uv` (pyproject.toml, uv.lock, requirements.txt)
- **Frontend** (`frontend/`): React + TypeScript SPA managed with `npm` (package.json, package-lock.json)
- **Agent** (`agent/`): Python CLI packaged as standalone binaries for Windows, Linux, and macOS

## Repository Conventions

### Branch Naming
- Feature branches: `feature-<short-description>` (e.g., `feature-remediate-vulnerabilities`)
- Bug fix branches: `fix-<short-description>`
- Always branch from `main`.

### Commit Message Style
Follow the existing pattern in this repository:
- **Subject line**: Imperative mood, concise summary (e.g., `Patch idna vulnerability and rebuild agent binaries`)
- **Body** (optional, via separate `-m` flags): Bulleted list of specific changes prefixed with `-`
- Example:
  ```
  git commit -m "Patch multiple vulnerabilities and rebuild agent binaries" \
             -m "- Fixed 29 known vulnerabilities by updating packages in backend dependencies" \
             -m "- Rebuilt Windows, Linux, and macOS agent packages to bundle the updated dependencies"
  ```

### PR Description
Always use the template in `.github/PULL_REQUEST_TEMPLATE.md`. Fill in all sections:
- **Description**: Summarize what changed and why, grouped by Backend/Frontend/CI/Documentation.
- **Type of change**: Check `Bug fix` and `Documentation update` for security patches.
- **How Has This Been Tested**: Include specific commands run and their results.
- **Checklist**: Check all applicable items; mark N/A items with an italicized note.

### Release Notes
- File: `RELEASES.md` at project root.
- New releases are prepended at the top, below the `# GPU Connect Releases` header.
- Follow the exact format of existing entries (see v1.0.5–v1.0.7 for security patch examples).
- Mark the latest release with `Latest` in the heading.
- Remove `Latest` from the previously latest release.
- GitHub release title format: `vX.Y.Z — Short Description Latest`

## Tool Chain

### Backend (Python / uv)
- **Package manager**: `uv` (NOT pip directly)
- **Dependency spec**: `backend/pyproject.toml`
- **Lock file**: `backend/uv.lock`
- **Compiled requirements**: `backend/requirements.txt` (auto-generated via `uv pip compile`)
- **Run commands**: Always prefix with `uv run` (e.g., `uv run pytest`)

### Frontend (TypeScript / npm)
- **Package manager**: `npm`
- **Dependency spec**: `frontend/package.json`
- **Lock file**: `frontend/package-lock.json`
- **Important**: `package.json` has an `overrides` section — keep it in sync when upgrading dependencies.

### Agent Binaries
- Built via `make agent` (Windows: `.\make.bat agent`)
- Outputs are copied to `frontend/public/downloads/` automatically
- Three platforms: Windows (.exe), Linux (.zip), macOS (.zip)

## CI/CD Workflows (`.github/workflows/`)
- `test-and-quality.yml`: Backend tests, frontend tests, Pylint, Radon analysis
- `security-scan.yml`: Gitleaks, pip-audit, npm audit, Bandit, Trivy
- `deploy.yml`: Deployment to Vercel (frontend) and Render (backend)

## Important Rules
1. **Never use `pip` directly** — always use `uv` for backend dependency management.
2. **Always update both `uv.lock` AND `requirements.txt`** when changing backend dependencies.
3. **Always update `package.json`** explicitly when frontend dependencies change (don't rely on lock file alone).
4. **Rebuild agent binaries** whenever backend dependencies change that affect the agent.
5. **Run tests after changes**: `npm run build && npm run test` for frontend, `uv run pytest` for backend.
6. **Verify audits pass** before committing: `npm audit --audit-level=high --omit=dev` and `pip-audit -r requirements.txt`.
