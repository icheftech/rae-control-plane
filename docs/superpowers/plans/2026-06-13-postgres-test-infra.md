# PostgreSQL Test Infrastructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the temporary SQLite + type-patching test fixtures with a real PostgreSQL 15-Alpine container via Testcontainers, then produce `TEST_INFRA_REVIEW.md` documenting all changes and results.

**Architecture:** A session-scoped Testcontainers `PostgresContainer` starts once per pytest run; a session-scoped `test_engine` runs `Base.metadata.create_all()` against it; a function-scoped `test_db` fixture wraps each test in a nested SAVEPOINT transaction that rolls back on teardown, preventing data bleed between tests.

**Tech Stack:** Python 3.12.7 · pytest 7.4.4 · SQLAlchemy 2.0 · testcontainers[postgresql]==4.14.2 · psycopg2-binary 2.9.9 (already installed) · postgres:15-alpine Docker image

---

## File Map

| File | Action | What changes |
|---|---|---|
| `/Users/flashhoustonllc/rae-control-plane/requirements.txt` | Modify | Add `testcontainers[postgresql]==4.14.2` to Testing section |
| `/Users/flashhoustonllc/rae-control-plane/backend/tests/conftest.py` | Replace | Remove SQLite fixtures + patch fn; add three-layer Testcontainers fixtures |
| `/Users/flashhoustonllc/rae-control-plane/TEST_INFRA_REVIEW.md` | Create | Root cause, changes, both test run outputs verbatim, recommendations |

No production files are touched.

---

### Task 1: Push the unpushed commit

The handoff noted commit `a63a8ef` (PostgreSQL test infra design spec) was not yet pushed.

**Files:** none

- [ ] **Step 1: Verify the unpushed commit**

```bash
cd /Users/flashhoustonllc/rae-control-plane
git log --oneline origin/main..HEAD
```

Expected output: one line containing `a63a8ef` (or similar) with "PostgreSQL test infra design spec".

- [ ] **Step 2: Push**

```bash
cd /Users/flashhoustonllc/rae-control-plane
git push origin main
```

Expected: `main -> main` with no errors.

---

### Task 2: Install testcontainers into the venv

**Files:**
- Modify: `/Users/flashhoustonllc/rae-control-plane/requirements.txt`

- [ ] **Step 1: Add the dependency to requirements.txt**

Open `/Users/flashhoustonllc/rae-control-plane/requirements.txt`. Find the `# Testing` section (currently contains `pytest==7.4.4` and `pytest-asyncio==0.23.3`). Add one line after the existing testing deps:

```
# Testing
pytest==7.4.4
pytest-asyncio==0.23.3
pytest-cov==4.1.0
testcontainers[postgresql]==4.14.2
```

Note: `pytest-cov` is already used (the `pytest.ini` has `--cov` flags) — add it here only if it's missing from the file. If it's already present, just add `testcontainers[postgresql]==4.14.2`.

- [ ] **Step 2: Install into venv**

```bash
cd /Users/flashhoustonllc/rae-control-plane
/Users/flashhoustonllc/rae-control-plane/backend/venv/bin/pip install "testcontainers[postgresql]==4.14.2"
```

Expected: `Successfully installed testcontainers-4.14.2 ...` (or "already satisfied" for deps already present).

If 4.14.2 is not available on PyPI, install the latest stable 4.x:
```bash
/Users/flashhoustonllc/rae-control-plane/backend/venv/bin/pip install "testcontainers[postgresql]"
```
Then record the version actually installed — you will need it for `TEST_INFRA_REVIEW.md` and to pin it in `requirements.txt`.

- [ ] **Step 3: Record exact installed version**

```bash
/Users/flashhoustonllc/rae-control-plane/backend/venv/bin/pip show testcontainers | grep Version
```

Update `requirements.txt` to use the exact version string returned (e.g. `testcontainers[postgresql]==4.9.0`).

- [ ] **Step 4: Ensure Docker Desktop is running**

```bash
docker info --format '{{.ServerVersion}}' 2>/dev/null && echo "Docker OK" || echo "Docker not running"
```

If "Docker not running": `open -a Docker && sleep 10` then re-run the check.

- [ ] **Step 5: Commit the requirements change**

```bash
cd /Users/flashhoustonllc/rae-control-plane
git add requirements.txt
git commit -m "chore: add testcontainers[postgresql] to requirements"
```

---

### Task 3: Replace conftest.py with Testcontainers fixtures

**Files:**
- Modify: `/Users/flashhoustonllc/rae-control-plane/backend/tests/conftest.py`

Replace the **entire file** with the content below. The sample-data fixtures at the bottom are preserved unchanged.

- [ ] **Step 1: Write the new conftest.py**

Replace `/Users/flashhoustonllc/rae-control-plane/backend/tests/conftest.py` with:

```python
"""Pytest configuration and fixtures for R.A.E. Control Plane test suite.

Uses Testcontainers to start a real postgres:15-alpine container once per
session. Each test function runs inside a nested transaction (SAVEPOINT) that
is rolled back on teardown — no data bleeds between tests.

Requires Docker Desktop to be running before pytest is invoked.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from testcontainers.postgres import PostgresContainer

from app.main import app
from app.db.base import Base, get_db

# Import all models so they register on Base.metadata before create_all
import app.db.models  # noqa: F401


# ---------------------------------------------------------------------------
# Layer 1 — one real PostgreSQL container per pytest session
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def postgres_container():
    """Start a postgres:15-alpine container for the duration of the test session."""
    with PostgresContainer("postgres:15-alpine") as pg:
        yield pg


# ---------------------------------------------------------------------------
# Layer 2 — one SQLAlchemy engine + schema per session
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def test_engine(postgres_container):
    """Create the test engine and materialise the full schema via create_all.

    NOTE: Uses Base.metadata.create_all() as a temporary shortcut because the
    Alembic migration (migrations/versions/001_initial_schema.py) has an empty
    upgrade() body. Once a real autogenerated migration exists, switch this to
    run `alembic upgrade head` against postgres_container.get_connection_url().
    """
    engine = create_engine(postgres_container.get_connection_url())
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


# ---------------------------------------------------------------------------
# Layer 3 — per-test isolated session via nested SAVEPOINT
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def test_db(test_engine):
    """Return an isolated DB session for one test.

    Opens an outer transaction on a raw connection, then issues a SAVEPOINT.
    An event listener re-issues the SAVEPOINT each time application code calls
    session.commit(), so committed writes stay visible to the session but are
    erased when the outer transaction rolls back at teardown.
    """
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    nested = connection.begin_nested()  # SAVEPOINT

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, transaction):
        nonlocal nested
        if transaction.nested and not transaction._parent.nested:
            session.expire_all()
            nested = connection.begin_nested()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


# ---------------------------------------------------------------------------
# FastAPI test client — wires test_db into the app dependency graph
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def client(test_db):
    """FastAPI TestClient backed by the isolated test session."""
    def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Sample data fixtures (unchanged from prior implementation)
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_workflow_data():
    """Sample workflow for testing."""
    return {
        "name": "test-workflow",
        "description": "Test workflow for unit tests",
        "version": "1.0.0",
        "is_active": True,
    }


@pytest.fixture
def sample_capability_data():
    """Sample capability for testing."""
    return {
        "name": "test-capability",
        "description": "Test capability for unit tests",
        "risk_level": "MEDIUM",
        "requires_approval": False,
        "is_active": True,
    }


@pytest.fixture
def sample_policy_data():
    """Sample control policy for testing."""
    return {
        "name": "test-policy",
        "description": "Test policy for unit tests",
        "policy_type": "ALLOW",
        "priority": 100,
        "conditions": {"environment": "test"},
        "is_active": True,
    }
```

- [ ] **Step 2: Commit**

```bash
cd /Users/flashhoustonllc/rae-control-plane
git add backend/tests/conftest.py
git commit -m "feat(tests): replace SQLite fixtures with Testcontainers PostgreSQL"
```

---

### Task 4: Run functional test suite and capture output

**Files:** none (read-only validation)

- [ ] **Step 1: Ensure Docker Desktop is running**

```bash
docker info --format '{{.ServerVersion}}' 2>/dev/null && echo "Docker OK" || (open -a Docker && sleep 10 && docker info --format '{{.ServerVersion}}')
```

- [ ] **Step 2: Run functional tests (no coverage)**

```bash
cd /Users/flashhoustonllc/rae-control-plane/backend
source venv/bin/activate
python -m pytest --no-cov -q 2>&1 | tee /tmp/rae_functional_run.txt
cat /tmp/rae_functional_run.txt
```

Expected: `7 passed` with no errors. Container startup adds ~2–10 s on first run while Docker pulls the image (cached on subsequent runs).

**If tests fail:** do NOT modify production models. Read the failure message carefully:
- `ModuleNotFoundError: testcontainers` → the pip install in Task 2 didn't target the right venv; re-run with the explicit venv pip path.
- `docker.errors.DockerException` → Docker Desktop isn't running; run `open -a Docker && sleep 10` and retry.
- Any other failure → apply `superpowers:systematic-debugging` before proceeding.

Save the complete output — you need it verbatim for `TEST_INFRA_REVIEW.md`.

---

### Task 5: Run full coverage suite and capture output

**Files:** none (read-only validation)

- [ ] **Step 1: Run with full pytest.ini addopts (coverage)**

```bash
cd /Users/flashhoustonllc/rae-control-plane/backend
source venv/bin/activate
python -m pytest 2>&1 | tee /tmp/rae_coverage_run.txt
cat /tmp/rae_coverage_run.txt
```

Expected: `7 passed` (tests pass); coverage gate likely still fails with `FAIL Required test coverage of 80% not reached. Total coverage: 62.81%` — this is a **pre-existing gap** outside this task's scope. Document it; do not fix it here.

Save the complete output verbatim for `TEST_INFRA_REVIEW.md`.

---

### Task 6: Write TEST_INFRA_REVIEW.md

**Files:**
- Create: `/Users/flashhoustonllc/rae-control-plane/TEST_INFRA_REVIEW.md`

- [ ] **Step 1: Read both captured outputs**

```bash
cat /tmp/rae_functional_run.txt
cat /tmp/rae_coverage_run.txt
```

- [ ] **Step 2: Create TEST_INFRA_REVIEW.md**

Create `/Users/flashhoustonllc/rae-control-plane/TEST_INFRA_REVIEW.md` with the following structure. Fill in `[PLACEHOLDER]` sections with the actual output you captured in Tasks 4 and 5.

```markdown
# R.A.E. Test Infrastructure Review

**Date:** 2026-06-13
**Author:** Claude Code (Sonnet 4.6) on behalf of Southern Shade Technologies (SST)
**Scope:** Migration from SQLite + type-patching workaround to real PostgreSQL via Testcontainers

---

## 1. Root Cause of Original Failures

The production models in `backend/app/db/models/` use PostgreSQL-specific SQLAlchemy column types:
- `sqlalchemy.dialects.postgresql.UUID` — PostgreSQL UUID column with native indexing
- `sqlalchemy.dialects.postgresql.JSONB` — Binary JSON with operator support
- `sqlalchemy.dialects.postgresql.ARRAY` — PostgreSQL native array column

SQLite's DDL compiler (`SQLiteTypeCompiler`) cannot render these types. Attempting to run `Base.metadata.create_all()` against a SQLite engine raised:

```
sqlalchemy.exc.CompileError:
  Compiler SQLiteTypeCompiler can't render element of type UUID
```

The workaround applied was `_patch_metadata_for_sqlite()` in `backend/tests/conftest.py`, which mutated `Base.metadata` in-place before each test run, swapping PostgreSQL types for SQLite equivalents. This introduced two risks:
1. Any new PostgreSQL-specific column added to a model would silently break tests unless the patch was also updated.
2. SQLite and PostgreSQL differ in constraint enforcement, UUID handling, and JSONB semantics — tests passing on SQLite do not guarantee PostgreSQL correctness.

---

## 2. Previous Failure Pattern

### Collection error (before import fix, pre-session)
```
ImportError while loading conftest: ModuleNotFoundError: No module named 'app.db.models.base'
# 0 tests collected, 0 passed
```

### UUID compile error (after import fix, before SQLite workaround)
```
sqlalchemy.exc.CompileError:
  Compiler SQLiteTypeCompiler can't render element of type UUID
# 7 tests collected, 7 errors — all at fixture setup
```

---

## 3. Files Changed

| File | Change |
|---|---|
| `requirements.txt` | Added `testcontainers[postgresql]==<VERSION>` to Testing section |
| `backend/tests/conftest.py` | Full replacement: removed `_patch_metadata_for_sqlite()`, `StaticPool`, `TEST_DATABASE_URL = "sqlite:///:memory:"`; added three-layer Testcontainers fixtures |

### What each change does

**`requirements.txt`** — Adds the `testcontainers` library with its `[postgresql]` extra, which includes the `psycopg2` integration for starting and connecting to ephemeral PostgreSQL containers. `psycopg2-binary==2.9.9` was already present and is reused as the driver.

**`backend/tests/conftest.py`** — Three fixture layers replace the SQLite approach:
- `postgres_container` (session scope): starts `postgres:15-alpine` once per pytest run via Testcontainers; yields the container object; container is stopped on session teardown.
- `test_engine` (session scope): creates a SQLAlchemy engine pointed at the container's connection URL; calls `Base.metadata.create_all()` to materialise all 11 model tables; drops all tables on teardown.
- `test_db` (function scope): opens a raw connection + outer transaction, issues a `SAVEPOINT` (`connection.begin_nested()`), and wraps a `Session` around it. An `after_transaction_end` event listener re-issues the SAVEPOINT each time application code calls `session.commit()`. The outer `transaction.rollback()` on teardown erases all writes — no data bleeds between tests.
- `client` fixture: unchanged in interface — wires `test_db` into `app.dependency_overrides[get_db]`.

---

## 4. Dependency Added

| Package | Version installed | How verified |
|---|---|---|
| `testcontainers[postgresql]` | `<INSERT pip show output here>` | `pip show testcontainers \| grep Version` |

---

## 5. Test Run Outputs

### Run 1 — Functional (no coverage)

Command: `python -m pytest --no-cov -q`

```
[INSERT VERBATIM OUTPUT FROM /tmp/rae_functional_run.txt HERE]
```

### Run 2 — Full (with coverage gate)

Command: `python -m pytest`

```
[INSERT VERBATIM OUTPUT FROM /tmp/rae_coverage_run.txt HERE]
```

---

## 6. Test Results After Migration

| Test | Result |
|---|---|
| `test_workflow_model.py::TestWorkflowModel::test_create_workflow` | PASSED |
| `test_workflow_model.py::TestWorkflowModel::test_workflow_name_required` | PASSED |
| `test_workflow_model.py::TestWorkflowModel::test_workflow_version_required` | PASSED |
| `test_workflow_model.py::TestWorkflowModel::test_workflow_unique_name_version` | PASSED |
| `test_workflow_model.py::TestWorkflowModel::test_workflow_soft_delete` | PASSED |
| `test_workflow_model.py::TestWorkflowModel::test_workflow_timestamps` | PASSED |
| `test_workflow_model.py::TestWorkflowModel::test_workflow_metadata_json` | PASSED |

**Total: 7/7 passed**

---

## 7. Coverage Summary

[INSERT COVERAGE TABLE FROM Run 2 OUTPUT HERE]

**Coverage gate status:** FAIL — `Total coverage: 62.81%` vs required `80%`

This is a **pre-existing gap**. The API endpoint modules (`capabilities.py`, `change_requests.py`, `workflows.py`, `kill_switches.py`, etc.) have no tests. This predates the test infrastructure migration and is out of scope for this task.

---

## 8. Recommendations for Future Testing Standards

### 8.1 Generate real Alembic migrations
`backend/migrations/versions/001_initial_schema.py` has an empty `upgrade()` body. Run:
```bash
alembic revision --autogenerate -m "Initial schema"
```
against a live PostgreSQL instance (the Testcontainers container works). Replace the stub. Switch the test fixture from `Base.metadata.create_all()` to:
```python
from alembic.config import Config
from alembic import command
alembic_cfg = Config("/path/to/backend/alembic.ini")
alembic_cfg.set_main_option("sqlalchemy.url", postgres_container.get_connection_url())
command.upgrade(alembic_cfg, "head")
```
At that point, Alembic becomes the single source of truth for schema in both tests and production.

### 8.2 Reach 80% coverage with API endpoint tests
The five worst-covered modules are all API route files. Each needs a test module using the `client` fixture. Targets:
- `backend/tests/test_workflows_api.py`
- `backend/tests/test_capabilities_api.py`
- `backend/tests/test_change_requests_api.py`
- `backend/tests/test_kill_switches_api.py`
- `backend/tests/test_tenants_api.py`

### 8.3 Separate unit and integration tests with pytest markers
Add to `backend/pytest.ini`:
```ini
markers =
    unit: pure-logic tests with no I/O
    integration: tests that require Docker / a live database
```
Mark Testcontainers tests with `@pytest.mark.integration`. Run `pytest -m unit` in CI pre-merge for speed; run `pytest` (all) in a nightly or pre-deploy gate.

### 8.4 Docker Desktop prerequisite
Tests will hang or error if Docker Desktop is not running. Add to `QUICKSTART.md` and CI pipeline setup: Docker Desktop must be started before running `pytest`.
```

- [ ] **Step 3: Replace all [PLACEHOLDER] sections**

Fill in:
- `<VERSION>` with the actual version from `pip show testcontainers | grep Version`
- `<INSERT pip show output here>` with the actual version
- The Run 1 output block with the verbatim content of `/tmp/rae_functional_run.txt`
- The Run 2 output block with the verbatim content of `/tmp/rae_coverage_run.txt`
- The coverage table section with the table from the Run 2 output

---

### Task 7: Final commit, push, and verification

**Files:** `TEST_INFRA_REVIEW.md`

- [ ] **Step 1: Commit TEST_INFRA_REVIEW.md**

```bash
cd /Users/flashhoustonllc/rae-control-plane
git add TEST_INFRA_REVIEW.md
git commit -m "docs: add TEST_INFRA_REVIEW.md — postgres test infra migration results"
```

- [ ] **Step 2: Push all commits**

```bash
git push origin main
```

Expected: `main -> main` with 3 new commits (requirements, conftest, review doc).

- [ ] **Step 3: Verify push succeeded**

```bash
git log --oneline -5
git status
```

Expected: clean working tree, `HEAD` on `main`, matching `origin/main`.

- [ ] **Step 4: Final smoke test**

```bash
cd /Users/flashhoustonllc/rae-control-plane/backend
source venv/bin/activate
python -m pytest --no-cov -q
```

Expected: `7 passed` with no errors.

- [ ] **Step 5: Report completion**

Report to the user:
- All 7 tests pass against real PostgreSQL 15-Alpine
- `TEST_INFRA_REVIEW.md` committed at repo root
- All commits pushed to `icheftech/rae-control-plane` main
- Coverage gate still fails (pre-existing 62.81% gap — not part of this task)
- Next recommended steps from the handoff: fix frontend MSAL package name, generate real Alembic migrations, review merged tenants API

---

## Self-Review

**Spec coverage check:**

| Spec section | Covered by |
|---|---|
| §3 Dependency change (`testcontainers[postgresql]`) | Task 2 |
| §4 Layer 1 `postgres_container` fixture | Task 3 |
| §4 Layer 2 `test_engine` fixture | Task 3 |
| §4 Layer 3 `test_db` nested transaction fixture | Task 3 |
| §4 `client` fixture wiring | Task 3 |
| §5 `create_all` as temporary shortcut, documented | Task 3 (code comment) + Task 6 (§8.1) |
| §6 pytest.ini unchanged | N/A — no change needed |
| §7 No production files modified | All tasks: only touch requirements.txt, conftest.py, TEST_INFRA_REVIEW.md |
| §8 Files changed list | Tasks 2, 3, 6 |
| §9 TEST_INFRA_REVIEW.md all 8 sections | Task 6 |
| §10 DoD: 7 passed --no-cov | Task 4 |
| §10 DoD: coverage run documented | Task 5 |
| §10 DoD: TEST_INFRA_REVIEW.md committed | Task 7 |
| §10 DoD: pushed to main | Task 7 |
| Handoff §7 item 1: push unpushed commit | Task 1 |

All spec requirements covered. No placeholders remain in task code blocks. Types and method names are consistent across all tasks (`postgres_container`, `test_engine`, `test_db`, `client`, `Base`, `get_db`).
