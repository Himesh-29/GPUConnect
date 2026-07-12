---
name: remediate-vulnerabilities
description: >
  Remediate security vulnerabilities detected by GitHub Actions CI workflows
  (pip-audit, npm audit, Trivy) in backend and frontend dependencies. Upgrades
  packages, rebuilds agent binaries, updates RELEASES.md, and drafts PR
  descriptions and GitHub release notes.
---

# Remediate Security Vulnerabilities

This skill guides you through the complete vulnerability remediation workflow for the GPU Connect project. Follow each phase in order.

## When to Trigger

Activate this skill when the user:
- Shares GitHub Actions failure logs from `pip-audit`, `npm audit`, or `Trivy`
- Asks to "fix vulnerabilities", "patch security issues", or "remediate CVEs"
- Asks to "draft a new security release" or "update for security scan failures"

---

## Phase 1: Investigate

Before making any changes, identify exactly what is vulnerable and where.

### Backend Vulnerabilities (pip-audit / Trivy)

1. **Check which scanner reported the issue:**
   - `pip-audit` scans `backend/requirements.txt`
   - Trivy scans `backend/uv.lock` (and `backend/requirements.txt`)
   - Both must be clean for CI to pass.

2. **Identify affected packages** from the CI log. Note:
   - Package name
   - Installed version
   - Fixed version
   - CVE identifier (if provided)

### Frontend Vulnerabilities (npm audit)

1. The CI runs: `npm audit --audit-level=high --omit=dev`
   - Only **production** dependencies matter (devDependencies are excluded).
2. Identify affected packages from the CI log.

---

## Phase 2: Fix Backend Dependencies

Run these commands **in order** from the project root:

```bash
# Step 1: Upgrade requirements.txt to latest versions
cd backend
uv pip compile pyproject.toml --upgrade -o requirements.txt

# Step 2: Upgrade uv.lock to latest versions
uv lock --upgrade
```

> **CRITICAL**: You MUST update BOTH `requirements.txt` AND `uv.lock`.
> - `pip-audit` scans `requirements.txt`
> - Trivy scans `uv.lock`
> - If you only update one, the other scanner will still fail.

### Verify Backend Fix

```bash
# This should report 0 vulnerabilities
# (Use uvx or install pip-audit to verify locally if possible)
uvx pip-audit -r requirements.txt
```

---

## Phase 3: Fix Frontend Dependencies

Run these commands from the project root:

```bash
# Step 1: Auto-fix vulnerabilities
cd frontend
npm audit fix

# Step 2: Check if production vulnerabilities remain
npm audit --audit-level=high --omit=dev
```

If `npm audit fix` doesn't fully resolve issues:

```bash
# Force fix (may include breaking changes — verify tests after)
npm audit fix --force
```

### Update package.json Explicitly

After `npm audit fix` or `npm audit fix --force`, check what versions were actually installed:

```bash
npm list <package-name>
```

Then **explicitly update `package.json`** to match the installed versions. This includes:
- The `dependencies` section
- The `overrides` section (if the upgraded package has an override entry)

> **CRITICAL**: Do NOT rely on `package-lock.json` alone. The `package.json` file
> must explicitly declare the new version ranges. This is a common mistake.

### Verify Frontend Fix

```bash
# This should report "found 0 vulnerabilities"
npm audit --audit-level=high --omit=dev

# Verify build still works
npm run build

# Verify all tests pass
npm run test
```

---

## Phase 4: Rebuild Agent Binaries (Only if Backend Changed)

If backend dependencies were updated, the agent binaries must be rebuilt:

```bash
# From project root (Windows)
.\make.bat agent

# From project root (Linux/macOS)
make agent
```

This will:
1. Build the Windows `.exe` via PyInstaller
2. Package Linux and macOS `.zip` bundles
3. Copy all outputs to `frontend/public/downloads/`

---

## Phase 5: Update RELEASES.md

Open `RELEASES.md` and prepend a new release entry at the top (below the `# GPU Connect Releases` header).

### Template for Security Patch Release

```markdown
## [vX.Y.Z](https://github.com/Himesh-29/GPUConnect/releases/tag/vX.Y.Z) — Security Patch & Agent Rebuild Latest

**Release Date**: <Month Day, Year>

### 🛡️ Security
This release is a dedicated security patch that resolves <description of scope>.

**Backend (`pyproject.toml`, `uv.lock`, `requirements.txt`)**
- <Bullet points describing what was upgraded and which CVEs/vulnerabilities were fixed>

**Frontend (`package.json`, `package-lock.json`)**
- <Bullet points describing what was upgraded — OMIT this section if frontend was not changed>

### 🔧 CI Fixes
<OMIT this section entirely if no CI changes were made>

**<Workflow file name>**
- <Description of CI fix>

### 📦 Agent Downloads (Updated)
The agent packages have been recompiled to bundle the updated dependencies and are available at [gpu-connect.vercel.app](https://gpu-connect.vercel.app):

| Platform | File |
|----------|------|
| Windows | `gpu-connect.exe` |
| Linux | `gpu-connect-agent-linux.zip` |
| macOS | `gpu-connect-agent-macos.zip` |
```

### Rules for RELEASES.md

1. **Mark the new entry as `Latest`** in the heading.
2. **Remove `Latest`** from the previous latest release heading.
3. **Determine the version number**: Increment the patch version from the last release (e.g., v1.0.7 → v1.0.8).
4. **Only include sections that are relevant** (omit Frontend section if only backend changed, omit CI Fixes if no workflow changes, etc.).

---

## Phase 6: Commit and Stage

### Determine Which Files Changed

| Scenario | Files to stage |
|----------|---------------|
| Backend only | `backend/requirements.txt`, `backend/uv.lock`, `frontend/public/downloads/gpu-connect.exe`, `RELEASES.md` |
| Frontend only | `frontend/package.json`, `frontend/package-lock.json`, `RELEASES.md` |
| Both | All of the above |
| CI fix included | Add `.github/workflows/<file>.yml` |

### Commit

Follow the repository's commit message style:

```bash
git add <files>
git commit -m "<Subject line>" \
           -m "- <Change 1>" \
           -m "- <Change 2>"
```

Example:
```bash
git commit -m "Patch multiple vulnerabilities and rebuild agent binaries" \
           -m "- Upgraded backend dependencies to fix N vulnerabilities identified by pip-audit" \
           -m "- Rebuilt Windows, Linux, and macOS agent packages to bundle the updated dependencies"
```

---

## Phase 7: Draft PR Description

Use the template from `.github/PULL_REQUEST_TEMPLATE.md`. Here is how to fill it for vulnerability patches:

```markdown
## Description
This PR remediates <N> security vulnerabilities identified by `<scanner>` in the <backend/frontend> dependencies.

**Backend:**
- <What was upgraded and why>

**Frontend:**
- <What was upgraded and why — OMIT if not applicable>

**CI:**
- <CI fixes — OMIT if not applicable>

**Documentation:**
- Updates `RELEASES.md` with `vX.Y.Z` release notes.

## Type of change
- [x] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [x] Documentation update

## How Has This Been Tested?
- [x] Unit tests
  - Ran `npm run test` in the frontend; verified all tests pass.
- [x] Manual testing
  - Ran `pip-audit` on the backend — reports 0 vulnerabilities.
  - Ran `npm audit --audit-level=high --omit=dev` — reports 0 vulnerabilities.
  - Ran `npm run build` — frontend builds successfully.
  - Rebuilt agent binaries via `make agent` — all platforms built successfully.

## Checklist:
- [x] My code follows the style guidelines of this project
- [x] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas *(N/A)*
- [x] I have made corresponding changes to the documentation
- [x] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works *(N/A)*
- [x] New and existing unit tests pass locally with my changes
```

---

## Phase 8: Draft GitHub Release Notes

Present the release title and body to the user for them to paste into GitHub's "Draft a new release" page.

### Release Title Format
```
vX.Y.Z — Security Patch & Agent Rebuild Latest
```

### Release Body
Use the same content you wrote in `RELEASES.md` for this version, but **without** the `## [vX.Y.Z](...) — ...` heading (GitHub already shows the tag name as the title).

---

## Checklist Before Finishing

- [ ] `pip-audit` reports 0 vulnerabilities on `backend/requirements.txt`
- [ ] Trivy-scanned `backend/uv.lock` has no MEDIUM+ vulnerabilities
- [ ] `npm audit --audit-level=high --omit=dev` reports 0 vulnerabilities
- [ ] `frontend/package.json` explicitly declares the new dependency versions
- [ ] `frontend/package.json` `overrides` section is in sync
- [ ] `npm run build` succeeds
- [ ] `npm run test` — all tests pass
- [ ] Agent binaries rebuilt (if backend changed)
- [ ] `RELEASES.md` updated with new version entry
- [ ] Previous `Latest` tag removed from old release heading
- [ ] Commit message follows project conventions
- [ ] PR description drafted using the template
- [ ] GitHub release title and notes drafted
