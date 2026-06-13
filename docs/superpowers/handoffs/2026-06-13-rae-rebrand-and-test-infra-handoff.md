# Session Handoff: R.A.E. Rebrand + Test Infrastructure
**Date:** 2026-06-13
**Session Duration:** Multi-turn Claude Code session (Sonnet 4.6)
**Local repo:** `/Users/flashhoustonllc/rae-control-plane`
**GitHub:** `https://github.com/icheftech/rae-control-plane`

---

## 1. Executive Summary

**What was completed this session:**

1. **Full repo rebrand** — every occurrence of `S.S.O. (Southern Shade Orchestrator)` replaced with `R.A.E. (Runtime Authority Engine)` across all source files, config, docs, Docker stack, and the GitHub repo itself. The repo was renamed on GitHub from `icheftech/sso-control-plane` → `icheftech/rae-control-plane` and the local folder moved from `~/sso-control-plane` → `~/rae-control-plane`.

2. **Pre-existing import bugs fixed** — the backend app was unimportable before the session started due to 6 broken `Base` import paths, a SQLAlchemy reserved attribute conflict (`metadata`), mismatched enum exports, and API-layer import mismatches. All fixed.

3. **Test suite made to pass (SQLite baseline)** — 7 tests now pass using a SQLite + type-patching workaround. This was explicitly a temporary solution.

4. **PostgreSQL test infrastructure designed, implemented, and pushed** ✅ — SQLite workaround replaced with real Testcontainers `postgres:15-alpine`. 7/7 tests pass against real PostgreSQL. `TEST_INFRA_REVIEW.md` written and committed. Four commits pushed to `origin/main`:
   - `07b52f5` — docs: add PostgreSQL test infrastructure implementation plan
   - `c8c4d86` — chore: add testcontainers[postgresql] to requirements
   - `37f4279` — feat(tests): replace SQLite fixtures with Testcontainers PostgreSQL
   - `1764082` — docs: add TEST_INFRA_REVIEW.md — postgres test infra migration results

5. **Frontend MSAL package names fixed** ✅ — `frontend/package.json` corrected: `@msal/browser` → `@azure/msal-browser`, `@msal/react` → `@azure/msal-react`. Pending `npm install` verification.

6. **Tenants API stabilization** ✅ — Pydantic schemas aligned with Tenant SQLAlchemy model (`name`→`tenant_name`, `domain`→`tenant_key`), `created_by` added to `TenantCreate`, `.dict()`→`.model_dump()`, production `get_db` hardened with rollback-on-exception, `check_db_connection` fixed for SQLAlchemy 2.x (`text("SELECT 1")`), test `get_db` override fixed to target the correct function identity. 10 tenant API endpoint tests added. 17/17 tests pass. Coverage: 65.88% (up from 62.81%). Two commits pushed to `origin/main`:
   - `9f9188a` — fix: stabilize tenants API schemas and production get_db
   - `45bbb96` — test: add tenant API endpoint tests

**Current state:**
- Branch: `main`
- Remote: `https://github.com/icheftech/rae-control-plane.git`
- Tests: 17/17 passing against **real `postgres:15-alpine`** (Testcontainers)
- Coverage: 65.88% (below the 80% gate — pre-existing gap, not worsened)
- Working tree: clean (all commits pushed)

---

## 2. R.A.E. Rebrand Summary

### Brand identity
- **Platform name:** R.A.E. — Runtime Authority Engine (was: S.S.O. — Southern Shade Orchestrator)
- **Owner:** Southern Shade LLC dba **Southern Shade Technologies (SST)** — builds and operates R.A.E.
- **Southern Shade LLC as tenant** in `SOUTHERN_SHADE_ONBOARDING.md` and `tenant.py` — **intentionally preserved**

### Naming substitution table applied

| Old | New |
|---|---|
| `S.S.O. (Southern Shade Orchestrator)` | `R.A.E. (Runtime Authority Engine)` |
| `S.S.O.` | `R.A.E.` |
| `SSO Control Plane` (brand) | `R.A.E. Control Plane` |
| `sso_control_plane` (DB name) | `rae_control_plane` |
| `sso_user` / `sso_password` | `rae_user` / `rae_password` |
| Docker containers `sso-postgres`, `sso-redis`, `sso-api`, `sso-celery-*` | `rae-postgres`, `rae-redis`, `rae-api`, `rae-celery-*` |
| Docker network `sso-network` | `rae-network` |
| Dockerfile system user `sso` | `rae` |
| `sso_dev.db` | `rae_dev.db` |
| `sso-control-plane-frontend` (npm package) | `rae-control-plane-frontend` |
| `SSO_Tokenization_Strategy.md` | `RAE_Tokenization_Strategy.md` |
| `__author__ = "Southern Shade LLC"` | `"Southern Shade Technologies (SST)"` |
| GitHub repo `icheftech/sso-control-plane` | `icheftech/rae-control-plane` |
| Local folder `~/sso-control-plane` | `~/rae-control-plane` |

### Intentionally unchanged
- "SSO" meaning Microsoft Entra / single sign-on (MSAL, Azure AD auth) — untouched everywhere
- `PROD_CHANGE_GOLDEN_PATH` workflow key — brand-neutral, unchanged
- "Southern Shade LLC" as the first onboarded **tenant** in `SOUTHERN_SHADE_ONBOARDING.md` and `backend/app/db/models/tenant.py`
- `SOUTHERN_SHADE_ONBOARDING.md` filename — kept because it describes the Southern Shade tenant onboarding, not the platform brand
- `LICENSE` — "ChefEl33", unchanged

### Brand grep gate result
```bash
grep -rniE '\bs\.s\.o|\bsso[_-]|[_-]sso\b|southern shade orchestrator|sso-control-plane' \
  --exclude-dir=venv --exclude-dir=node_modules --exclude-dir=.git \
  --exclude-dir=.next --exclude-dir=docs .
# exit=1 (NO MATCHES) ✅
```

### GitHub repo rename
- `gh repo rename rae-control-plane --repo icheftech/sso-control-plane --yes` — completed successfully
- GitHub auto-redirects old URL `icheftech/sso-control-plane` → `icheftech/rae-control-plane`
- Local remote updated: `git remote set-url origin https://github.com/icheftech/rae-control-plane.git`

### Docker naming
- `docker compose config --quiet` passes (one pre-existing `version` attribute obsolete warning — harmless)
- No containers are currently running. Docker Desktop must be started before `docker compose up`.

---

## 3. Current Test Infrastructure Issue

### Original failures (pre-session baseline)
```
ImportError while loading conftest: ModuleNotFoundError: No module named 'app.db.models.base'
# 0 tests collected, 0 passed — collection error
```

### Why SQLite failed after import fix
After fixing the import bug, tests moved past collection but failed at DB setup:
```
sqlalchemy.exc.CompileError:
  Compiler SQLiteTypeCompiler can't render element of type UUID
# 7 tests collected, 7 errors — all at fixture setup
```

**Root cause:** The production models use PostgreSQL-specific column types (`postgresql.UUID`, `JSONB`, `ARRAY`). SQLite's DDL compiler cannot render these. No amount of SQLite workarounds covers behavioral differences like JSONB operators, UUID indexing, or constraint semantics.

### Current workaround (temporary — `e7534f9`)
`backend/tests/conftest.py` uses `_patch_metadata_for_sqlite()` which mutates `Base.metadata` in-place at test time, swapping:
- `postgresql.UUID` → `sqlalchemy.Uuid()`
- `JSONB` → `JSON`
- `ARRAY(...)` → `JSON`

This makes 7 tests pass. It is documented as temporary. It does not test PostgreSQL semantics.

### Why Testcontainers was selected
- Docker is available (Docker Desktop 28.3.2 confirmed running)
- `psycopg2-binary==2.9.9` already in `requirements.txt`
- `testcontainers==4.14.2` available on PyPI
- No local PostgreSQL installation exists (`pg_isready` not found)
- Testcontainers provides ephemeral real PostgreSQL with no manual server setup

### PostgreSQL image version
`postgres:15-alpine` — matches the version in `docker-compose.yml`

### Spec file path
`docs/superpowers/specs/2026-06-13-postgres-test-infra-design.md`

### Implementation status
**NOT STARTED.** The spec and design are complete and approved. The writing-plans session was interrupted to create this handoff. The implementation plan has not been written yet.

---

## 4. Files Changed (This Session)

### Backend — application code
| File | Change |
|---|---|
| `backend/app/__init__.py` | `__author__` rebranded to SST |
| `backend/app/main.py` | `TITLE`, startup/shutdown strings, service key rebranded |
| `backend/app/agents/__init__.py` | Docstring rebranded |
| `backend/app/agents/AGENT_EXAMPLE.md` | DB URL example updated |
| `backend/app/api/__init__.py` | Docstring rebranded |
| `backend/app/api/llm.py` | Module docstring rebranded |
| `backend/app/api/tenants.py` | Module docstring rebranded (from remote merge) |
| `backend/app/db/base.py` | Docstring rebranded; default DB URL → `rae_user/rae_control_plane` |
| `backend/app/db/database.py` | Default DB URL → `rae_user/rae_control_plane` |
| `backend/app/db/models/__init__.py` | `__author__`, `__description__` rebranded; enum exports fixed |
| `backend/app/db/models/tenant.py` | Platform-ref lines rebranded; tenant example lines preserved; stale relationship backrefs removed |
| `backend/app/db/models/workflow.py` | Added `version` column, `UniqueConstraint`, `is_active` column, `__init__` timestamps (for tests) |
| `backend/app/db/models/change_request.py` | `backref=` → `back_populates=` on workflow relationship; `metadata` → `extra_metadata` in `to_dict` |
| `backend/app/db/models/audit_event.py` | `metadata` → `extra_metadata` with `name="metadata"` |
| `backend/app/db/models/break_glass.py` | `metadata` → `extra_metadata`; `Integer` import added |
| `backend/app/db/models/enforcement_gate.py` | `metadata` → `extra_metadata`; `Integer` import added |
| `backend/app/db/models/capability.py` | `Base` import fixed |
| `backend/app/db/models/connector.py` | `Base` import fixed |
| `backend/app/db/models/control_policy.py` | `Base` import fixed |
| `backend/app/db/models/kill_switch.py` | `metadata` → `extra_metadata` |
| `backend/app/services/model_provider.py` | Docstring rebranded |
| `backend/alembic.ini` | Header comment rebranded; `sqlalchemy.url` → `rae_user/rae_control_plane` |
| `backend/pytest.ini` | Comment rebranded |
| `backend/migrations/env.py` | Docstring rebranded |
| `backend/migrations/versions/001_initial_schema.py` | Docstrings rebranded |
| `backend/tests/__init__.py` | Docstring rebranded |
| `backend/tests/conftest.py` | Full replacement: SQLite + `_patch_metadata_for_sqlite()` (temporary) |
| `backend/tests/test_workflow_model.py` | Import path fixed; `metadata` → `extra_metadata` |
| `backend/.env` (untracked) | `sso_dev.db` → `rae_dev.db`; Groq key restored from `.env.save` |

### Frontend
| File | Change |
|---|---|
| `frontend/package.json` | name → `rae-control-plane-frontend`; description rebranded |
| `frontend/app/layout.tsx` | Title and keywords rebranded |
| `frontend/app/page.tsx` | Heading rebranded |
| `frontend/lib/api.ts` | Docblock rebranded |
| `frontend/README.md` | Full rebranding |

### Docker / infra config
| File | Change |
|---|---|
| `docker-compose.yml` | All `sso-*` container/network/DB names → `rae-*`; pre-existing corrupt first-line artifact removed |
| `Dockerfile` | System user `sso` → `rae`; pre-existing corrupt first-line artifact removed |
| `.env.example` | `DATABASE_URL` → `rae_user/rae_control_plane` |
| `requirements.txt` | Blank-line stray edit reverted |
| `.gitignore` | Added `.DS_Store` and `*.env.save` entries |

### Root-level documentation
| File | Change |
|---|---|
| `README.md` | Full rewrite: R.A.E. identity, two-layer architecture, four tenets, Federal Readiness section, SST ownership |
| `AGENT_NOTES.md` | Full rebrand; `PROD_CHANGE_GOLDEN_PATH` unchanged |
| `SOUTHERN_SHADE_ONBOARDING.md` | Platform brand strings rebranded; Southern Shade LLC tenant context preserved |
| `PHASES.md` | Rebranded (from remote merge) |
| `QUICKSTART.md` | Rebranded; git clone URL updated (from remote merge) |
| `RAE_Tokenization_Strategy.md` | Renamed from `SSO_Tokenization_Strategy.md`; full rebrand inside |

### Deleted / cleaned up
- `backend/.env.save` — deleted after Groq API key preserved in `backend/.env`
- `sso-control-plane/sso-control-plane/` — accidental nested clone deleted
- `.DS_Store` files — deleted from repo root, `backend/`, `frontend/`
- `backend/venv/` — recreated from scratch after folder rename (old venv hardcoded the old absolute path)

### Specs and plans
| File | Note |
|---|---|
| `docs/superpowers/specs/2026-06-11-rae-rebrand-design.md` | Rebrand design spec (approved, implemented) |
| `docs/superpowers/plans/2026-06-11-rae-rebrand.md` | Rebrand implementation plan (8 tasks, all completed) |
| `docs/superpowers/specs/2026-06-13-postgres-test-infra-design.md` | PostgreSQL test infra spec (approved, NOT YET IMPLEMENTED) |
| `docs/superpowers/handoffs/2026-06-13-rae-rebrand-and-test-infra-handoff.md` | This file |

---

## 5. Tests and Validation

### Commands executed

**Functional test run (no coverage):**
```bash
cd /Users/flashhoustonllc/rae-control-plane/backend
source venv/bin/activate
python -m pytest --no-cov -q
```

**Full coverage run:**
```bash
python -m pytest
```

**App import smoke check:**
```bash
python -c "from app.main import app; print(app.title)"
```

**Docker compose validation:**
```bash
cd /Users/flashhoustonllc/rae-control-plane
docker compose config --quiet && echo OK
```

**Brand grep gate:**
```bash
grep -rniE '\bs\.s\.o|\bsso[_-]|[_-]sso\b|southern shade orchestrator|sso-control-plane' \
  --exclude-dir=venv --exclude-dir=node_modules --exclude-dir=.git \
  --exclude-dir=.next --exclude-dir=docs .
```

### Tests passing
```
17 passed in 2.87s
tests/test_workflow_model.py (7 tests)                                        PASSED
tests/test_tenants_api.py (10 tests)                                          PASSED
```

### Tests failing
None currently. All 17 pass.

### Known fragility of current test baseline
The tests pass because `conftest.py` patches PostgreSQL types to SQLite equivalents at runtime. This is fragile:
- Any new `postgresql.JSONB` or `postgresql.UUID` column added to a model without updating the patch function will silently break tests
- SQLite and PostgreSQL have different constraint enforcement, UUID handling, and JSONB behavior — tests passing here do not guarantee PostgreSQL correctness

### Coverage (full `pytest.ini` run)
```
TOTAL    1360    464    66%
FAIL Required test coverage of 80% not reached. Total coverage: 65.88%
17 passed in 2.87s
```

**Coverage gap is pre-existing** — the API endpoint modules (`capabilities.py`, `change_requests.py`, `workflows.py`, etc.) have no tests written for them yet. The coverage gate (`--cov-fail-under=80`) therefore fails on every run. This predates this session.

**Worst-covered modules:**
| Module | Coverage |
|---|---|
| `app/api/change_requests.py` | 22% |
| `app/api/workflows.py` | 35% |
| `app/api/kill_switches.py` | 33% |
| `app/services/model_provider.py` | 30% |
| `app/db/database.py` | 41% (improved) |

### Docker compose validation
```bash
docker compose config --quiet && echo OK
# → OK (plus pre-existing `version` obsolete warning — harmless)
```

### Frontend build status
**Unknown.** `npm install` fails because `@msal/browser@^3.0.0` does not exist (correct package is `@azure/msal-browser`). This is a pre-existing bug in `frontend/package.json` that predates this session. No attempt was made to fix it — out of scope for the rebrand.

### Backend import status
```bash
python -c "from app.main import app; print(app.title)"
# → R.A.E. Control Plane API ✅
```

---

## 6. Open Questions / Decisions Needed

### 1. PostgreSQL test infrastructure — proceed immediately?
**Status:** Spec and design approved. Implementation plan not yet written (writing-plans session was interrupted for this handoff). Decision: continue in next session with subagent-driven implementation.
**Recommended:** Yes — complete the implementation plan, then execute via subagent-driven development.

### 2. Docker Desktop SSO project residue
During the GitHub repo rename, Docker Desktop may still show the old `sso-control-plane` project name if Docker Compose was ever run under the old folder path. No containers are running and no volumes were created on this machine during this session, so there is no data to migrate. However, if any developer has run `docker compose up` previously under the old path, their local `rae-postgres` container will not exist and they will need to recreate volumes.
**Recommended:** Document in QUICKSTART.md that a fresh `docker compose up` is required after the rename; no volume migration is needed for clean environments.

### 3. Alembic migrations — generate real migrations?
**Current state:** `migrations/versions/001_initial_schema.py` has an empty `upgrade()` body (`pass`). This means `alembic upgrade head` does nothing. Schema is currently only created via `Base.metadata.create_all()` (both in tests and if anyone runs `init_db()`).
**Recommended:** Run `alembic revision --autogenerate -m "Initial schema"` against a live PostgreSQL instance once the test infra migration is done. Replace the stub migration. This also enables `alembic upgrade head` in the test fixtures instead of `create_all`.
**Risk:** The autogenerated migration will create all 11 tables. Running it on a database that already has tables (from a previous `create_all`) will fail unless the DB is dropped first.

### 4. Freeze new features until full system review?
**Context:** The remote `main` had 12 commits ahead (tenants API, business eval scorer) merged in during this session's Task 8. These add `backend/app/api/tenants.py` and related work. No review was done on the correctness of that code — it was merged and rebranded, but not audited.
**Recommended:** Perform a `/code-review` of the full diff before adding more features. The tenants API especially needs review since `tenant.py` had relationship bugs fixed during this session.

---

## 7. Next Recommended Actions

### Priority order

1. ~~**Push the unpushed commit**~~ ✅ DONE — `a63a8ef` was already pushed; handoff was stale.

2. ~~**Complete PostgreSQL test infrastructure**~~ ✅ DONE — 7/7 tests pass against `postgres:15-alpine`. Commits `07b52f5`, `c8c4d86`, `37f4279`, `1764082` pushed to `origin/main`.

3. ~~**Generate `TEST_INFRA_REVIEW.md`**~~ ✅ DONE — committed at repo root as `1764082`.

4. ~~**Fix the frontend MSAL package name**~~ ✅ DONE — `@msal/browser` → `@azure/msal-browser`, `@msal/react` → `@azure/msal-react`. `npm install` succeeded. Committed as `8204e51`.

5. ~~**Generate real Alembic migrations**~~ ✅ DONE — Dead stub `001_initial_schema.py` deleted. Real autogenerated migration `bdc5931c12bf` creates all 11 tables, 14 enums, all indexes/FKs/constraints. Verified: `upgrade head` → `downgrade base` → `upgrade head` clean. Test fixture switched from `Base.metadata.create_all()` to `alembic upgrade head`. 7/7 tests pass. `MIGRATION_REVIEW.md` committed at repo root. Also fixed: stale `env.py` imports (`PolicyStatus`, `KillSwitchState`, etc.), added missing `Tenant` import, created missing `script.py.mako`.

6. ~~**Code review and fix merged tenants API**~~ ✅ DONE — Tenants API schemas realigned with Tenant model, production `get_db` hardened, 10 endpoint tests added. 17/17 pass. Coverage improved to 65.88%. Commits `9f9188a`, `45bbb96` pushed to `origin/main`.

7. **Begin R.A.E. system review and phase remapping**
   - AGENT_NOTES.md describes Phases 1–5 (Registry, Controls, Enforcement, Compliance, Identity Federation)
   - Phase 5 (Identity Federation) was marked in-progress at session start
   - A full phase status audit should be conducted before continuing feature work

---

## 8. Next Session Prompt

Copy and paste this into the next Claude Code or ChatGPT session:

---

```
You are continuing work on R.A.E. (Runtime Authority Engine), SST's flagship AI governance platform.

**Repo:** /Users/flashhoustonllc/rae-control-plane
**GitHub:** https://github.com/icheftech/rae-control-plane
**Branch:** main
**Tech stack:** FastAPI + SQLAlchemy 2.0 + PostgreSQL 15 (backend), Next.js 15 (frontend)

## What was completed (all sessions to date)

1. Full rebrand from S.S.O. (Southern Shade Orchestrator) → R.A.E. (Runtime Authority Engine). Brand grep gate passes (exit=1). GitHub repo renamed `icheftech/sso-control-plane` → `icheftech/rae-control-plane`.

2. Pre-existing backend import bugs fixed: Base imports, SQLAlchemy reserved `metadata` attribute renamed to `extra_metadata` (with `name="metadata"`), backref conflicts resolved, enum export mismatches fixed.

3. PostgreSQL Testcontainers test infrastructure — COMPLETE. `backend/tests/conftest.py` replaced with three-layer fixtures: session-scoped `postgres_container` (postgres:15-alpine), session-scoped `test_engine` (create_all), function-scoped `test_db` (SAVEPOINT rollback). 7/7 tests pass against real PostgreSQL. `TEST_INFRA_REVIEW.md` committed at repo root.

4. Coverage gate fails: 62.81% vs required 80%. Pre-existing gap — no API endpoint tests exist yet.

5. Frontend MSAL package names corrected in `frontend/package.json`: `@msal/browser` → `@azure/msal-browser`, `@msal/react` → `@azure/msal-react`. `npm install` and build verification pending.

## Recent commits (pushed to origin/main)

- `1764082` — docs: add TEST_INFRA_REVIEW.md — postgres test infra migration results
- `37f4279` — feat(tests): replace SQLite fixtures with Testcontainers PostgreSQL
- `c8c4d86` — chore: add testcontainers[postgresql] to requirements
- `07b52f5` — docs: add PostgreSQL test infrastructure implementation plan

## Your immediate tasks

### 1. Verify and commit the frontend MSAL fix

`frontend/package.json` has already been edited — `@msal/browser` and `@msal/react` corrected to `@azure/msal-*`. Your job:

```bash
cd /Users/flashhoustonllc/rae-control-plane/frontend
npm install
npm run build
```

If the build passes, commit:
```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "fix: correct MSAL package names to @azure/msal-browser and @azure/msal-react"
git push origin main
```

If the build fails for any reason other than the MSAL package name, report what you find before fixing anything else.

### 2. Generate real Alembic migrations

`backend/migrations/versions/001_initial_schema.py` has an empty `upgrade()` body — it is a stub. With Testcontainers available, run autogenerate against a live container:

```bash
cd /Users/flashhoustonllc/rae-control-plane/backend
source venv/bin/activate
# start a throwaway postgres container for autogenerate
python -c "
from testcontainers.postgres import PostgresContainer
with PostgresContainer('postgres:15-alpine') as pg:
    print(pg.get_connection_url())
"
# use that URL for alembic
DATABASE_URL=<url> alembic revision --autogenerate -m 'Initial schema'
```

Replace the stub migration body with the autogenerated one. Switch the test fixture from `Base.metadata.create_all()` to `alembic upgrade head` once the migration is real.

### 3. Code review of merged remote work

The tenants API (`backend/app/api/tenants.py`) was merged without review. Run `/code-review` on the diff and pay particular attention to `tenant.py` model relationships.

## Key file locations

- Backend app: `backend/app/`
- Tests: `backend/tests/conftest.py`, `backend/tests/test_workflow_model.py`
- Models: `backend/app/db/models/` (11 model files + __init__.py)
- DB config: `backend/app/db/base.py` (has `Base` declarative base + `get_db`)
- API routes: `backend/app/api/` (workflows, capabilities, connectors, control_policies, kill_switches, change_requests, llm, tenants)
- Alembic migration (stub): `backend/migrations/versions/001_initial_schema.py`
- Requirements: repo root `requirements.txt` (no separate backend/requirements.txt)
- Venv: `backend/venv/` (Python 3.12.7)
- Docker stack: `docker-compose.yml` at repo root — uses postgres:15-alpine as `rae-postgres` container
- Frontend: `frontend/` (Next.js 15, package.json already edited)

## Important model notes

- `Base` is in `backend/app/db/base.py` (NOT `database.py` — that file has its own orphan Base)
- `get_db` FastAPI dependency is also in `backend/app/db/base.py`
- `metadata` column renamed to `extra_metadata` in Python (DB column name stays `metadata` via `name="metadata"`)
- All models import Base via `from app.db.base import Base` (not relative imports)
- `workflow.py` has `version` as a `Column(String(50))` and `UniqueConstraint("name", "version")`

## Environment

- Python 3.12.7 in `backend/venv/`
- Docker Desktop 28.3.2 (may need `open -a Docker && sleep 8` to start)
- psycopg2-binary 2.9.9 + testcontainers[postgresql]==4.14.2 installed in venv
- Node.js ≥18 required for frontend build
- No local PostgreSQL server installed (use Testcontainers)
```

---

*Document written by Claude Code (Sonnet 4.6) on 2026-06-13. Repo: icheftech/rae-control-plane.*
