"""Pytest configuration and fixtures for R.A.E. Control Plane test suite

Provides reusable test fixtures for:
- Database sessions (isolated test DB)
- Test client (FastAPI TestClient)
- Sample data fixtures for all models
- Authentication mocking
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.database import Base, get_db

# Test database URL (in-memory SQLite for speed)
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def test_db():
    """Create a fresh test database for each test function."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(test_db):
    """Create FastAPI test client with test database."""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Clean up
    app.dependency_overrides.clear()


# Sample data fixtures
@pytest.fixture
def sample_workflow_data():
    """Sample workflow for testing."""
    return {
        "name": "test-workflow",
        "description": "Test workflow for unit tests",
        "version": "1.0.0",
        "is_active": True
    }


@pytest.fixture
def sample_capability_data():
    """Sample capability for testing."""
    return {
        "name": "test-capability",
        "description": "Test capability for unit tests",
        "risk_level": "MEDIUM",
        "requires_approval": False,
        "is_active": True
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
        "is_active": True
    }
