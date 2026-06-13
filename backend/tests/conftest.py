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
from alembic.config import Config
from alembic import command

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
    """Create the test engine and apply the schema via Alembic migrations."""
    url = postgres_container.get_connection_url()
    alembic_cfg = Config("alembic.ini")
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
