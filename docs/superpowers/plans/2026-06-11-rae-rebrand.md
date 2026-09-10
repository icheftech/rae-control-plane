# R.A.E. Rebrand Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebrand the repository from S.S.O. (Southern Shade Orchestrator) to R.A.E. (Runtime Authority Engine) per `docs/superpowers/specs/2026-06-11-rae-rebrand-design.md`, including technical identifiers, the GitHub repo name, and the local folder — with nothing left broken.

**Architecture:** This is a rename/rebrand with zero behavioral change. Work proceeds in commit-sized tasks: cleanup → config/infra identifiers → backend strings → frontend strings → docs rewrite → verification sweep → repo/folder rename. Each task ends with a verification command and a commit. A final grep gate proves no stray brand references remain.

**Tech Stack:** Python/FastAPI backend (SQLAlchemy, Alembic, pytest), Next.js 15 frontend, Docker Compose, GitHub via `gh` CLI.

**Repo root for all tasks:** `/Users/flashhoustonllc/sso-control-plane` (becomes `/Users/flashhoustonllc/rae-control-plane` in Task 8).

## Global Naming Rules (apply in every task)

| Old | New |
|---|---|
| `S.S.O. (Southern Shade Orchestrator)` | `R.A.E. (Runtime Authority Engine)` |
| `S.S.O.` | `R.A.E.` |
| `SSO Control Plane` (brand) | `R.A.E. Control Plane` |
| `Southern Shade Orchestrator` | `Runtime Authority Engine` |
| `Southern Shade LLC` (as platform owner/author) | `Southern Shade Technologies (SST)` |
| `Southern Shade LLC` (as the *tenant* in tenant.py / onboarding doc) | **Unchanged** |
| `sso_control_plane` | `rae_control_plane` |
| `sso_user` / `sso_password` | `rae_user` / `rae_password` |
| `sso-postgres`, `sso-redis`, `sso-api`, `sso-celery-worker`, `sso-celery-beat`, `sso-network` | same with `rae-` prefix |
| `sso_dev.db` | `rae_dev.db` |
| `sso-control-plane-frontend` | `rae-control-plane-frontend` |
| "SSO" meaning Microsoft Entra single sign-on | **Unchanged** |
| `PROD_CHANGE_GOLDEN_PATH` | **Unchanged** |
| LICENSE file | **Unchanged** (matches only the word "associated") |

---

### Task 1: Baseline + Riding-Along Cleanup

**Files:**
- Modify: `requirements.txt` (revert stray edit), `.gitignore`, `backend/.env`
- Delete: `sso-control-plane/` (nested accidental clone), `backend/.env.save`, stray `.DS_Store` files

- [ ] **Step 1: Record test baseline**

```bash
cd /Users/flashhoustonllc/sso-control-plane/backend
source venv/bin/activate 2>/dev/null && python -m pytest --no-cov -q; deactivate 2>/dev/null
```

Record the pass/fail counts. If pytest is not installed in the venv, run `python3 -m venv venv && source venv/bin/activate && pip install -r ../requirements.txt && pip install pytest pytest-cov httpx` first. The rebrand must not make this baseline worse.

- [ ] **Step 2: Revert the stray requirements.txt edit**

```bash
cd /Users/flashhoustonllc/sso-control-plane && git checkout -- requirements.txt
```

- [ ] **Step 3: Delete the nested accidental clone**

First confirm it has no unique work: `cd sso-control-plane && git status --short && git log --oneline -1` (it is a stale clone of the same repo). Then:

```bash
cd /Users/flashhoustonllc/sso-control-plane && rm -rf sso-control-plane
```

If `git status` inside it showed uncommitted changes, STOP and ask the user instead of deleting.

- [ ] **Step 4: Preserve the real Groq key, then delete .env.save**

`backend/.env.save` holds the real `LLM_API_KEY` while `backend/.env` has a placeholder. Copy the `LLM_API_KEY=gsk_...` line from `backend/.env.save` over the placeholder line in `backend/.env`, then:

```bash
rm /Users/flashhoustonllc/sso-control-plane/backend/.env.save
```

Also delete the stray trailing lines in `backend/.env` (the pasted `uvicorn app.main:app ...` command and the comment above it — lines after `DEFAULT_MODEL=...`).

- [ ] **Step 5: Add gitignore entries and remove .DS_Store files**

Append to `.gitignore` (create the lines if absent):

```
.DS_Store
*.env.save
```

```bash
cd /Users/flashhoustonllc/sso-control-plane && find . -name .DS_Store -not -path './backend/venv/*' -delete
```

- [ ] **Step 6: Commit**

```bash
git add .gitignore && git commit -m "chore: repo cleanup before R.A.E. rebrand"
```

---

### Task 2: Infrastructure & Config Identifiers

**Files:**
- Modify: `docker-compose.yml`, `Dockerfile`, `.env.example`, `backend/alembic.ini`, `backend/app/db/database.py:26`, `backend/app/db/base.py:20`, `backend/pytest.ini:2`, `backend/.env:3`

- [ ] **Step 1: docker-compose.yml** — apply the naming rules table. Exact renames: `container_name: sso-postgres` → `rae-postgres`; `POSTGRES_DB: sso_control_plane` → `rae_control_plane`; `POSTGRES_USER: sso_user` → `rae_user`; healthcheck `pg_isready -U sso_user -d sso_control_plane` → `-U rae_user -d rae_control_plane`; `sso-redis` → `rae-redis`; `sso-api` → `rae-api`; `sso-celery-worker` → `rae-celery-worker`; `sso-celery-beat` → `rae-celery-beat`; all three `DATABASE_URL: postgresql://sso_user:...@postgres:5432/sso_control_plane` → `rae_user`/`rae_control_plane`; network `sso-network` → `rae-network` (both per-service and the top-level `networks:` key).

- [ ] **Step 2: Dockerfile** — system user rename: `useradd -m -u 1000 sso && chown -R sso:sso /app` → `useradd -m -u 1000 rae && chown -R rae:rae /app`; `COPY --from=builder /root/.local /home/sso/.local` → `/home/rae/.local`; all `COPY --chown=sso:sso` → `--chown=rae:rae`; `USER sso` → `USER rae`; `ENV PATH=/home/sso/.local/bin:$PATH` → `/home/rae/.local/bin`.

- [ ] **Step 3: .env.example** — line 8: `DATABASE_URL=postgresql://sso_user:${POSTGRES_PASSWORD}@postgres:5432/sso_control_plane` → `rae_user` / `rae_control_plane`. Line 23 (`# Microsoft Entra ID (Azure AD) - SSO Authentication`) is single sign-on — leave it.

- [ ] **Step 4: backend/alembic.ini line 32** — `sqlalchemy.url = postgresql://sso_user:sso_password@localhost:5432/sso_control_plane` → `postgresql://rae_user:rae_password@localhost:5432/rae_control_plane`.

- [ ] **Step 5: backend/app/db/database.py line 26 and backend/app/db/base.py line 20** — same URL replacement as Step 4 in both default-URL strings.

- [ ] **Step 6: backend/pytest.ini line 2** — `# Pytest configuration for S.S.O. Control Plane test suite` → `# Pytest configuration for R.A.E. Control Plane test suite`.

- [ ] **Step 7: backend/.env line 3** (untracked, local) — `DATABASE_URL=sqlite:///./sso_dev.db` → `sqlite:///./rae_dev.db`. No `sso_dev.db` file exists on disk, so nothing else to migrate.

- [ ] **Step 8: Validate compose file**

```bash
cd /Users/flashhoustonllc/sso-control-plane && docker compose config --quiet && echo OK
```

Expected: `OK` (config parses).

- [ ] **Step 9: Verify no leftover infra identifiers**

```bash
grep -rn 'sso_user\|sso_control_plane\|sso-postgres\|sso-redis\|sso-api\|sso-celery\|sso-network\|sso_dev\|sso_password' --exclude-dir=venv --exclude-dir=node_modules --exclude-dir=.git . ; echo "exit=$?"
```

Expected: no matches, `exit=1`.

- [ ] **Step 10: Commit**

```bash
git add docker-compose.yml Dockerfile .env.example backend/alembic.ini backend/app/db/database.py backend/app/db/base.py backend/pytest.ini
git commit -m "refactor: rename infra identifiers from sso to rae"
```

---

### Task 3: Backend Source Strings

**Files:**
- Modify: `backend/app/__init__.py`, `backend/app/main.py`, `backend/app/agents/__init__.py`, `backend/app/agents/AGENT_EXAMPLE.md`, `backend/app/api/llm.py`, `backend/app/db/models/__init__.py`, `backend/app/db/models/tenant.py`, `backend/app/db/base.py`, `backend/migrations/env.py`, `backend/migrations/versions/001_initial_schema.py`, `backend/tests/__init__.py`, `backend/tests/conftest.py`, `backend/tests/test_workflow_model.py`, `backend/app/services/model_provider.py`, plus any other backend file the Step 2 grep finds.

- [ ] **Step 1: Apply naming rules to the known lines.** Exact edits:
  - `backend/app/__init__.py:1` docstring → `"""R.A.E. Control Plane - Application Package`; line 6 `__author__ = "Southern Shade LLC"` → `"Southern Shade Technologies (SST)"`.
  - `backend/app/main.py`: line 1 → `"""R.A.E. Control Plane - FastAPI Application`; line 4 → `Main application entry point for the R.A.E. (Runtime Authority Engine)`; line 30 → `TITLE = "R.A.E. Control Plane API"`; lines 68/80 startup/shutdown prints → `R.A.E. Control Plane ...`; line 133 → `"service": "R.A.E. Control Plane",`.
  - `backend/app/agents/__init__.py`: line 1 → `"""Agent runtime package for R.A.E. workflows.`; line 4: `for Southern Shade workflows defined in SOUTHERN_SHADE_ONBOARDING.md.` — keep "Southern Shade" here only if it refers to the tenant; it does, so leave the sentence but it still reads fine.
  - `backend/app/api/llm.py`: lines 1, 49 → `R.A.E.`; line 4 `(like the Southern Shade website)` → unchanged (refers to the company website, not the platform brand) — but change `for S.S.O.` → `for R.A.E.`.
  - `backend/app/db/models/__init__.py`: line 1 → `"""R.A.E. Control Plane - Database Models Package`; line 112 `__author__` → `"Southern Shade Technologies (SST)"`; line 113 → `"R.A.E. Control Plane - Enterprise AI Governance Platform"`.
  - `backend/app/db/models/tenant.py`: line 3 → `Enables R.A.E. Control Plane to serve multiple organizations (tenants)`; line 21 → `the R.A.E. platform`; lines 6 and 31 mention Southern Shade LLC *as tenant* → **unchanged**.
  - `backend/migrations/env.py:2`, `backend/migrations/versions/001_initial_schema.py:1,7`, `backend/tests/__init__.py:1`, `backend/tests/conftest.py:1`, `backend/tests/test_workflow_model.py:3`, `backend/app/db/base.py:3` → replace `S.S.O.` with `R.A.E.` in each docstring.
  - `backend/app/agents/AGENT_EXAMPLE.md`: line 120 `DATABASE_URL=postgresql://user:pass@localhost/sso` → `.../rae`; lines 27/29 reference Southern Shade LLC as the example tenant company → **unchanged**.
  - `backend/app/services/model_provider.py`: replace any `S.S.O.`/`SSO` brand strings with `R.A.E.` per the rules table (grep the file first).

- [ ] **Step 2: Sweep for stragglers**

```bash
cd /Users/flashhoustonllc/sso-control-plane/backend
grep -rn -e 'S\.S\.O' -e 'SSO' --exclude-dir=venv app/ migrations/ tests/ pytest.ini alembic.ini
```

Expected: zero brand hits (Entra single-sign-on mentions, if any, stay). Fix anything found using the rules table.

- [ ] **Step 3: Run tests — must match Task 1 baseline**

```bash
cd /Users/flashhoustonllc/sso-control-plane/backend && source venv/bin/activate && python -m pytest --no-cov -q
```

Expected: same or better than baseline.

- [ ] **Step 4: Smoke-import the app**

```bash
cd /Users/flashhoustonllc/sso-control-plane/backend && source venv/bin/activate && python -c "from app.main import app; print(app.title)"
```

Expected: `R.A.E. Control Plane API`.

- [ ] **Step 5: Commit**

```bash
git add backend/ && git commit -m "refactor: rebrand backend strings to R.A.E."
```

---

### Task 4: Frontend Strings

**Files:**
- Modify: `frontend/package.json:2`, `frontend/app/layout.tsx:9-11`, `frontend/app/page.tsx:8`, `frontend/lib/api.ts:2`, `frontend/README.md`

- [ ] **Step 1: Exact edits**
  - `frontend/package.json:2` → `"name": "rae-control-plane-frontend",`
  - `frontend/app/layout.tsx:9` → `title: 'R.A.E. Control Plane - Enterprise AI Governance',`; line 11 keywords: `'AI governance, NIST AI RMF, R.A.E., control plane, compliance, HIPAA, SOC 2',`
  - `frontend/app/page.tsx:8` → `R.A.E. Control Plane`
  - `frontend/lib/api.ts:2` → ` * R.A.E. Control Plane - Frontend API Client`
  - `frontend/README.md`: line 1 → `# R.A.E. Control Plane - Frontend Dashboard`; line 3 → `Next.js 15 dashboard for the R.A.E. Control Plane's enterprise-grade AI governance system... with Microsoft Entra ID (Azure AD) SSO.` (trailing "SSO" = single sign-on, keep); line 10 (`MSAL.js ... browser-based SSO`) keep; line 37 → `**Backend API**: R.A.E. Control Plane FastAPI service running`; line 45 → `Name: \`R.A.E. Control Plane Dashboard\``. Grep the rest of the file and apply the rules table.

- [ ] **Step 2: Sweep**

```bash
cd /Users/flashhoustonllc/sso-control-plane/frontend
grep -rn -i 'sso' --exclude-dir=node_modules --exclude-dir=.next . | grep -vi 'single sign-on\|Entra\|MSAL'
```

Expected: only legitimate single-sign-on references (manually confirm each remaining hit is auth-related, not brand).

- [ ] **Step 3: Build the frontend**

```bash
cd /Users/flashhoustonllc/sso-control-plane/frontend && npm install --no-audit --no-fund && npm run build
```

Expected: build succeeds (or fails identically to pre-change baseline — if it was already broken, record and move on; do not fix unrelated build errors in this task).

- [ ] **Step 4: Commit**

```bash
git add frontend/ && git commit -m "refactor: rebrand frontend to R.A.E."
```

---

### Task 5: README Rewrite

**Files:**
- Modify: `README.md` (full rewrite of branded sections)

- [ ] **Step 1: Rewrite README.md.** Keep the existing structure (badges, architecture tree, schema tables, usage examples, compliance section) but apply:
  - Title block:

```markdown
# R.A.E. Control Plane

**Runtime Authority Engine — Enterprise AI Governance Platform**

> R.A.E. is Southern Shade Technologies' flagship AI governance platform: a control plane and Chief Orchestrator system that governs how AI agents operate inside enterprise and federal environments. Agents propose actions only — execution is gated by registry, policy, kill-switch, and audit layers.
```

  - Overview section: replace the S.S.O. paragraph with:

```markdown
The **R.A.E. (Runtime Authority Engine) Control Plane** is an enterprise-grade governance platform for AI agent systems, designed for regulated industries requiring PHI/PII-grade compliance. R.A.E. operates on two layers: the **control plane** (a structured registry of AI agents, policy controls, enforcement rules, a compliance engine, and identity federation) and the **Chief Orchestrator** (a conversational AI command layer atop the control plane whose own actions appear in the audit chain as a distinct actor type — the governance system is itself governed).

R.A.E. is built on four core tenets: **visibility** (every agent action is logged and traceable), **control** (policies constrain any registered agent in real time), **compliance** (evidence is generated automatically for regulatory frameworks), and **federation** (identity and authority span organizational and agency boundaries without sacrificing auditability).
```

  - Architecture tree header: `S.S.O. Control Plane` → `R.A.E. Control Plane`.
  - Clone instructions (lines 79-80) → `git clone https://github.com/icheftech/rae-control-plane.git` / `cd rae-control-plane`.
  - Database commands (lines 91, 94) → `rae_control_plane`.
  - Contributing/About sections: `Southern Shade LLC` → `Southern Shade Technologies (SST)`, adding one clarifying line: `Southern Shade Technologies is the operating brand of Southern Shade LLC (Texas, USA).` Keep email/website as-is.
  - Add a short `## 🎖️ Federal Readiness` section before Compliance: R.A.E. provides the governance wrapper that makes autonomous AI deployable at scale in federal contexts — provable agent behavior, mid-mission shutdown via kill switches, and automated policy-compliance evidence.
  - `acme_invoice_processor` example content is brand-neutral — unchanged.

- [ ] **Step 2: Verify no stray brand strings**

```bash
grep -n -e 'S\.S\.O' -e 'SSO' -e 'Southern Shade Orchestrator' -e 'sso-control-plane' /Users/flashhoustonllc/sso-control-plane/README.md
```

Expected: no matches.

- [ ] **Step 3: Commit**

```bash
git add README.md && git commit -m "docs: rewrite README for R.A.E. brand"
```

---

### Task 6: Remaining Docs

**Files:**
- Modify: `AGENT_NOTES.md`, `SOUTHERN_SHADE_ONBOARDING.md`

- [ ] **Step 1: AGENT_NOTES.md** — apply the rules table throughout. Line 8 becomes: `You are implementing the **R.A.E. (Runtime Authority Engine)** control plane for **Southern Shade Technologies (SST)**.` Header line 1 → `# 🔒 R.A.E. CONTROL PLANE — AGENT IMPLEMENTATION NOTES`. `workflow_key = "PROD_CHANGE_GOLDEN_PATH"` unchanged. Grep the file afterward for `S\.S\.O\|SSO` — expect zero hits.

- [ ] **Step 2: SOUTHERN_SHADE_ONBOARDING.md** — file name stays (Southern Shade LLC is the tenant). Inside, replace platform-brand references (`S.S.O.`, `Southern Shade Orchestrator`) with `R.A.E.` / `Runtime Authority Engine`; references to Southern Shade LLC *as the tenant being onboarded* stay. Grep afterward: remaining `Southern Shade` hits must all be tenant-context.

- [ ] **Step 3: Commit**

```bash
git add AGENT_NOTES.md SOUTHERN_SHADE_ONBOARDING.md && git commit -m "docs: rebrand agent notes and onboarding doc to R.A.E."
```

---

### Task 7: Full Verification Sweep

- [ ] **Step 1: Brand grep gate**

```bash
cd /Users/flashhoustonllc/sso-control-plane
grep -rniE '\bs\.s\.o|\bsso[_-]|[_-]sso\b|southern shade orchestrator' --exclude-dir=venv --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=.next --exclude-dir=docs . ; echo "exit=$?"
```

Expected: `exit=1` (no matches). Then a looser check — every remaining case-insensitive `sso` hit must be single-sign-on or a false positive (e.g. "associated"):

```bash
grep -rni 'sso' --exclude-dir=venv --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=.next --exclude-dir=docs . | grep -vi 'associat\|single sign\|entra\|msal\|azure'
```

Manually confirm each remaining line is legitimate.

- [ ] **Step 2: Tests + import smoke**

```bash
cd backend && source venv/bin/activate && python -m pytest --no-cov -q && python -c "from app.main import app; print(app.title)"
```

Expected: baseline-or-better test results; title prints `R.A.E. Control Plane API`.

- [ ] **Step 3: Compose validation**

```bash
cd /Users/flashhoustonllc/sso-control-plane && docker compose config --quiet && echo OK
```

- [ ] **Step 4: Commit anything the sweep fixed**

```bash
git add -A ':!backend/venv' && git commit -m "chore: final R.A.E. rebrand sweep" || echo "nothing to fix"
```

---

### Task 8: Repo + Folder Rename

- [ ] **Step 1: Push all commits to the current remote first**

```bash
cd /Users/flashhoustonllc/sso-control-plane && git push origin main
```

- [ ] **Step 2: Rename the GitHub repo**

```bash
gh repo rename rae-control-plane --repo icheftech/sso-control-plane --yes
```

Expected: repo is now `icheftech/rae-control-plane`; GitHub auto-redirects the old name.

- [ ] **Step 3: Update the local remote URL**

```bash
cd /Users/flashhoustonllc/sso-control-plane && git remote set-url origin https://github.com/icheftech/rae-control-plane.git && git remote -v && git fetch origin
```

- [ ] **Step 4: Rename the local folder**

```bash
cd /Users/flashhoustonllc && mv sso-control-plane rae-control-plane
```

- [ ] **Step 5: Recreate the backend venv** (its scripts hardcode the old absolute path)

```bash
cd /Users/flashhoustonllc/rae-control-plane/backend && rm -rf venv && python3 -m venv venv && source venv/bin/activate && pip install -r ../requirements.txt && pip install pytest pytest-cov httpx
```

- [ ] **Step 6: Final smoke from the new path**

```bash
cd /Users/flashhoustonllc/rae-control-plane/backend && source venv/bin/activate && python -m pytest --no-cov -q && python -c "from app.main import app; print(app.title)"
cd /Users/flashhoustonllc/rae-control-plane && git status && git log --oneline -3
```

Expected: tests at baseline, title `R.A.E. Control Plane API`, clean git status, remote reachable.

---

## Definition of Done

- All commits pushed to `icheftech/rae-control-plane`
- Brand grep gate passes (Task 7 Step 1)
- Backend tests at or above the Task 1 baseline; app imports with the new title
- `docker compose config` validates
- Frontend builds (or matches its pre-existing baseline)
- Local folder is `~/rae-control-plane` with a working venv and updated remote
