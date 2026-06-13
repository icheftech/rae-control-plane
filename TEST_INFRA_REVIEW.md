# R.A.E. Control Plane — Test Infrastructure Review

**Date:** 2026-06-13
**Project:** Runtime Authority Engine (RAE)
**Scope:** Migration from SQLite in-memory test database to PostgreSQL via testcontainers

---

## 1. Root Cause of Original Failures

The original test suite was wired to run against a SQLite in-memory database. This created two compounding problems:

**Import resolution failure:** The conftest attempted to load application modules using paths that assumed a specific package layout (`app.db.models.base`). After recent refactoring, that path no longer existed, causing pytest collection to abort before a single test ran.

**Type incompatibility:** Even after the import paths were corrected, SQLite does not natively support PostgreSQL-specific column types used in the RAE models — specifically `UUID` and `JSONB`. SQLAlchemy's SQLite dialect compiler (`SQLiteTypeCompiler`) raises a `CompileError` when it encounters these types during table creation, making the entire fixture setup fail.

The fundamental issue was that the test database dialect did not match the production dialect. RAE's data model depends on PostgreSQL-native types, so any test backend that is not PostgreSQL will fail at the schema-creation stage.

---

## 2. Previous SQLite / UUID / JSONB Failure Pattern

### Pattern 1 — Collection error (before import fixes)

```
ImportError while loading conftest: ModuleNotFoundError: No module named 'app.db.models.base'
# 0 tests collected, 0 passed
```

This error fired before pytest could collect any test items. The conftest itself could not be imported, so the entire session aborted immediately.

### Pattern 2 — Type compiler error (after import fixes, before PostgreSQL migration)

```
sqlalchemy.exc.CompileError:
  Compiler SQLiteTypeCompiler can't render element of type UUID
# 7 tests collected, 7 errors — all at fixture setup
```

With import paths corrected, pytest collected all 7 test items. However, every single test failed at fixture setup because the in-memory SQLite engine could not compile `UUID` column definitions. `JSONB` columns would have caused the same error had UUID not triggered it first.

---

## 3. Files Changed and What Each Change Does

### `requirements.txt`

Added `testcontainers[postgresql]==4.14.2` to the `# Testing` section.

This pulls in the testcontainers library and its PostgreSQL extras (the `psycopg2`/`psycopg` driver bindings needed to connect to the container). The library manages the full lifecycle of a Docker container — pulling the image, starting it, waiting for the port to be ready, and tearing it down — without any manual Docker Compose setup required in CI or on a developer machine.

### `backend/tests/conftest.py`

Complete replacement of the conftest. The old file contained:

- `_patch_metadata_for_sqlite()` — a monkey-patch that attempted to swap out unsupported column types at runtime
- `StaticPool` import from SQLAlchemy — used to force a single shared connection for the in-memory database
- `TEST_DATABASE_URL = "sqlite:///:memory:"` — hardcoded SQLite connection string

All of the above were removed. The new conftest introduces:

- **`postgres_container` (session-scoped fixture):** Starts a `postgres:15-alpine` Docker container once per test session. Yields the running container object. Stopped and removed automatically after all tests complete.
- **`test_engine` (session-scoped fixture):** Creates a SQLAlchemy engine pointed at the container's dynamically assigned host/port. Runs `Base.metadata.create_all()` to build the full schema (including UUID and JSONB columns) against real PostgreSQL. Disposed after the session.
- **`test_db` (function-scoped fixture with SAVEPOINT):** Opens a connection and begins a nested transaction (SAVEPOINT) before each test. Yields a `Session` bound to that savepoint. After the test, rolls back to the savepoint — giving each test a clean slate without dropping and re-creating tables.
- **`client` fixture:** Updated to inject the `test_db` session into the FastAPI dependency override so HTTP-layer tests share the same transactional session.
- Sample-data fixtures from the old conftest were preserved without modification.

---

## 4. Test Dependency Added

| Package | Version |
|---|---|
| `testcontainers[postgresql]` | `4.14.2` |

Added to `requirements.txt` under the `# Testing` section. The `[postgresql]` extra installs the database adapter needed for testcontainers to open a connection and confirm the container is ready before yielding control to the test session.

---

## 5. Commands Executed

### Run 1 — Functional (no coverage)

Command: `python -m pytest --no-cov -q`

```
============================= test session starts ==============================
platform darwin -- Python 3.12.7, pytest-7.4.4, pluggy-1.6.0
rootdir: /Users/flashhoustonllc/rae-control-plane/backend
configfile: pytest.ini
testpaths: tests
plugins: asyncio-0.23.3, cov-7.1.0, anyio-4.13.0
asyncio: mode=Mode.STRICT
collected 7 items

tests/test_workflow_model.py::TestWorkflowModel::test_create_workflow 
-------------------------------- live log setup --------------------------------
2026-06-13 16:14:10 [INFO] Pulling image testcontainers/ryuk:0.8.1
2026-06-13 16:14:44 [INFO] Container started: 7d158f2d0d60
2026-06-13 16:14:44 [INFO] Pulling image postgres:15-alpine
2026-06-13 16:14:44 [INFO] Container started: 09399a29a91e
PASSED                                                                   [ 14%]
tests/test_workflow_model.py::TestWorkflowModel::test_workflow_name_required PASSED [ 28%]
tests/test_workflow_model.py::TestWorkflowModel::test_workflow_version_required PASSED [ 42%]
tests/test_workflow_model.py::TestWorkflowModel::test_workflow_unique_name_version PASSED [ 57%]
tests/test_workflow_model.py::TestWorkflowModel::test_workflow_soft_delete PASSED [ 71%]
tests/test_workflow_model.py::TestWorkflowModel::test_workflow_timestamps PASSED [ 85%]
tests/test_workflow_model.py::TestWorkflowModel::test_workflow_metadata_json PASSED [100%]

============================== 7 passed in 36.18s ==============================
```

Note: The 36-second wall time on the first run is expected. Docker Desktop must pull `testcontainers/ryuk:0.8.1` and `postgres:15-alpine` on first use. Both images are cached locally after the initial pull; subsequent runs complete in roughly 2–3 seconds.

### Run 2 — Full coverage suite

Command: `python -m pytest`

```
============================= test session starts ==============================
platform darwin -- Python 3.12.7, pytest-7.4.4, pluggy-1.6.0 --
rootdir: /Users/flashhoustonllc/rae-control-plane/backend
configfile: pytest.ini
testpaths: tests
plugins: asyncio-0.23.3, cov-7.1.0, anyio-4.13.0
asyncio: mode=Mode.STRICT
collected 7 items

tests/test_workflow_model.py::TestWorkflowModel::test_create_workflow PASSED
tests/test_workflow_model.py::TestWorkflowModel::test_workflow_name_required PASSED
tests/test_workflow_model.py::TestWorkflowModel::test_workflow_version_required PASSED
tests/test_workflow_model.py::TestWorkflowModel::test_workflow_unique_name_version PASSED
tests/test_workflow_model.py::TestWorkflowModel::test_workflow_soft_delete PASSED
tests/test_workflow_model.py::TestWorkflowModel::test_workflow_timestamps PASSED
tests/test_workflow_model.py::TestWorkflowModel::test_workflow_metadata_json PASSED

7 passed in 2.59s

FAIL Required test coverage of 80% not reached. Total coverage: 62.81%
```

---

## 6. Tests Passing / Tests Failing (Post-Migration)

| Test | Result |
|---|---|
| `test_create_workflow` | PASSED |
| `test_workflow_name_required` | PASSED |
| `test_workflow_version_required` | PASSED |
| `test_workflow_unique_name_version` | PASSED |
| `test_workflow_soft_delete` | PASSED |
| `test_workflow_timestamps` | PASSED |
| `test_workflow_metadata_json` | PASSED |

**7 of 7 tests pass. 0 tests fail.**

The migration from SQLite to PostgreSQL via testcontainers resolved all pre-existing fixture and type-compiler errors. No tests were skipped, xfailed, or deselected.

---

## 7. Coverage Report Summary

| Metric | Value |
|---|---|
| Total coverage | 62.81% |
| Required threshold (`pytest.ini`) | 80% |
| Status | FAIL |

The coverage gate in `pytest.ini` is set to `--cov-fail-under=80`. The current suite covers 62.81% of the measured source, which is 17.19 percentage points below the threshold. The suite is currently limited to model-layer tests against `test_workflow_model.py`. Application code in the API routing layer, service layer, and any utility modules is not yet exercised by the test suite, which explains the gap.

All 7 tests pass. The only failing condition is the coverage enforcement gate, not a test assertion.

---

## 8. Recommendations for Future Testing Standards

### 1. Generate real Alembic migrations

The test suite currently calls `Base.metadata.create_all()` to build the schema. This is convenient for model-layer tests but does not validate that Alembic migration scripts are correct or complete. The production database is managed through Alembic, so a divergence between migration history and the ORM metadata will go undetected until deployment.

**Recommendation:** Replace `create_all()` in `test_engine` with `alembic upgrade head` run against the test container. This ensures the schema under test is always the schema that migrations would produce, catching missing columns, wrong types, or stale migration heads in CI before they reach production.

### 2. Add API endpoint tests to reach 80%

The 62.81% coverage figure reflects model-layer coverage only. The FastAPI routing layer, dependency injection overrides, request validation, and error handling code paths are entirely untested. Adding even a basic set of CRUD endpoint tests using the existing `client` fixture (which already injects the test database session) would cover the routes module and push total coverage above the 80% threshold.

**Recommendation:** Write a `test_workflow_api.py` module covering at minimum: `POST /workflows` (create), `GET /workflows` (list), `GET /workflows/{id}` (retrieve), `DELETE /workflows/{id}` (soft delete), and at least one 422 validation error case. These tests reuse the existing fixture stack with no additional infrastructure.

### 3. Consider pytest markers for unit vs. integration tests

All 7 current tests are integration tests: they require a running Docker container. As the suite grows, developers will want to run a fast subset (pure unit tests with no I/O) during local development without waiting for Docker. pytest markers make this trivial.

**Recommendation:** Register `unit` and `integration` markers in `pytest.ini`. Decorate testcontainer-dependent tests with `@pytest.mark.integration`. Add a `Makefile` target `make test-unit` that runs `pytest -m "not integration"` for the fast local loop, and `make test` that runs the full suite. CI should always run the full suite.

### 4. Document Docker Desktop as a prerequisite

The `postgres_container` fixture has a hard runtime dependency on a running Docker daemon. If Docker Desktop is not running, pytest will fail immediately with a connection error from testcontainers before any test is collected. This is not obvious from the project README or the error message alone.

**Recommendation:** Add a "Prerequisites" section to the project README (and to any CI setup guide) stating that Docker Desktop 4.x or later must be running before executing `pytest`. Note the tested version (28.3.2) and add a short troubleshooting note explaining that the `testcontainers/ryuk:0.8.1` image pull on first run adds approximately 30 seconds to the initial test run. Consider adding a conftest-level check that emits a clear `pytest.skip` or `pytest.exit` message if the Docker socket is unreachable, rather than letting testcontainers raise a raw connection exception.

---

## Environment Summary

| Component | Version |
|---|---|
| Python | 3.12.7 |
| pytest | 7.4.4 |
| pytest-asyncio | 0.23.3 |
| pytest-cov | 7.1.0 |
| SQLAlchemy | 2.0.25 |
| testcontainers | 4.14.2 |
| Docker Desktop | 28.3.2 |
| PostgreSQL image | postgres:15-alpine |
