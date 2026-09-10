"""Pytest configuration and fixtures for R.A.E. Control Plane test suite.

Uses Testcontainers to start a real postgres:15-alpine container once per
session. Each test function runs inside a nested transaction (SAVEPOINT) that
is rolled back on teardown — no data bleeds between tests.

Requires Docker Desktop to be running before pytest is invoked.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session

from testcontainers.postgres import PostgresContainer
from alembic.config import Config
from alembic import command

from app.db.base import Base
from app.db.database import get_db

# Import all models so they register on Base.metadata before create_all
import app.db.models  # noqa: F401

# Import the FastAPI instance AFTER `import app.db.models` to avoid
# the `app` name being shadowed by the `app` package module.
from app.main import app as fastapi_app


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
    """Create the test engine and apply the schema via Alembic migrations."""
    url = postgres_container.get_connection_url()
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.attributes["test_database"] = True
    alembic_cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(alembic_cfg, "head")
    engine = create_engine(url)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


# ---------------------------------------------------------------------------
# Layer 3 — per-test isolated session via nested SAVEPOINT
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def test_db(test_engine):
    """Return an isolated DB session for one test.

    SQLAlchemy owns a SAVEPOINT inside an outer connection transaction.
    Application commits release only the SAVEPOINT; teardown rolls back
    the outer transaction and erases all writes from the test.
    """
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    yield session

    session.close()
    transaction.rollback()
    connection.close()


# ---------------------------------------------------------------------------
# FastAPI test client — wires test_db into the app dependency graph
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def client(test_db, monkeypatch):
    """FastAPI TestClient backed by the isolated test session."""
    def override_get_db():
        yield test_db

    from app.services.rate_limit import _buckets
    _buckets.clear()

    monkeypatch.setenv("RAE_API_KEYS", '{"test-key":{"name":"test-harness","role":"admin"},"review-key":{"name":"reviewer","role":"admin"},"approve-key":{"name":"approver","role":"admin"},"viewer-key":{"name":"viewer","role":"viewer"}}')
    fastapi_app.dependency_overrides[get_db] = override_get_db
    with TestClient(fastapi_app, headers={"Authorization":"Bearer test-key"}) as test_client:
        yield test_client
    fastapi_app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Sample data fixtures (unchanged from prior implementation)
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_workflow_data(test_db):
    """Sample workflow for testing."""
    return {
        "tenant_id": test_db.scalar(text("SELECT id FROM tenants WHERE tenant_key='southern_shade_technologies'")),
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
