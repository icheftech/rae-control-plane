# R.A.E. Rebrand — Design Spec

**Date:** 2026-06-11
**Status:** Approved by Leroy Brown
**Scope:** Full rebrand of this repository from S.S.O. (Southern Shade Orchestrator) to R.A.E. (Runtime Authority Engine)

## 1. Brand Identity

- **Product name:** R.A.E. — Runtime Authority Engine (replaces S.S.O. — Southern Shade Orchestrator).
- **Owner:** Southern Shade LLC (legal entity), doing business as **Southern Shade Technologies (SST)**, which builds and operates R.A.E.
- **Positioning (for README and docs):** R.A.E. is SST's flagship AI governance platform — a control plane and Chief Orchestrator system that governs how AI agents operate inside enterprise and federal environments. Agents propose actions only; execution is gated by registry, policy, kill-switch, and audit layers.
  - **Two layers:** the **control plane** (registry of agents, policy controls, enforcement rules, compliance engine, identity federation) and the **Chief Orchestrator** (conversational AI command layer atop the control plane; its own actions appear in the audit chain as a distinct actor type — the governance system is itself governed).
  - **Four tenets:** visibility, control, compliance, federation.
  - **Federal framing:** for CFIC/ARCYBER "AI Effects at the Edge" contexts, R.A.E. is the governance wrapper that makes autonomous AI deployable at scale (provable agent behavior, mid-mission shutdown, automated policy-compliance evidence).

### Naming rules

| Old | New |
|---|---|
| S.S.O. / SSO (brand) | R.A.E. / RAE |
| Southern Shade Orchestrator | Runtime Authority Engine |
| "Southern Shade LLC" as platform owner | "Southern Shade Technologies (SST)" (dba of Southern Shade LLC) |
| SSO meaning *single sign-on* (Microsoft Entra ID) | **Unchanged** — this is not the brand |
| `PROD_CHANGE_GOLDEN_PATH` workflow key | **Unchanged** — brand-neutral |

`SOUTHERN_SHADE_ONBOARDING.md` keeps its meaning (Southern Shade as first onboarded tenant); only S.S.O. brand references inside it change to R.A.E.

## 2. Technical Identifier Renames (full depth)

| Identifier | Old | New |
|---|---|---|
| Postgres database | `sso_control_plane` | `rae_control_plane` |
| Postgres user | `sso_user` | `rae_user` |
| Docker containers | `sso-postgres`, `sso-redis`, `sso-api`, `sso-celery-worker`, `sso-celery-beat` | `rae-postgres`, `rae-redis`, `rae-api`, `rae-celery-worker`, `rae-celery-beat` |
| Docker network | `sso-network` | `rae-network` |
| Dockerfile system user | `sso` | `rae` |
| Frontend package name | `sso-control-plane-frontend` | `rae-control-plane-frontend` |

Files affected include (not exhaustive — final sweep is grep-driven): `docker-compose.yml`, `Dockerfile`, `.env.example`, `backend/alembic.ini`, `backend/app/db/database.py`, `backend/pytest.ini`, `frontend/package.json`, plus docstrings/comments in ~37 files across `backend/` and `frontend/`.

## 3. Repository and Environment

- **GitHub:** rename `icheftech/sso-control-plane` → `icheftech/rae-control-plane` via `gh`. GitHub auto-redirects old URLs and remotes.
- **Local folder:** rename `~/sso-control-plane` → `~/rae-control-plane`; update `origin` remote URL to the new repo name.
- **Dev database:** recreate via docker compose with new names. Check container state first; confirm with the user before dropping any database that appears to hold non-seed data.
- **Verification (definition of done):**
  - `pytest` passes in `backend/`
  - `docker compose up` boots all services healthy under new names
  - frontend builds (`npm run build` or equivalent)
  - `grep -ri sso` returns only legitimate single-sign-on references

## 4. Riding-Along Cleanup

- Revert the stray blank-line edit at the top of `requirements.txt`.
- Delete the accidental nested clone `sso-control-plane/sso-control-plane/`.
- Add `.DS_Store` and `*.env.save` to `.gitignore`.
- Remove `backend/.env.save` from disk only after confirming it holds nothing unique vs. `.env`/`.env.example`.

## Out of Scope

- No functional/behavioral changes to the platform.
- No new features (Phase 5 Identity Federation work continues separately).
- No changes to the Executive Interface demo beyond brand strings if present.
