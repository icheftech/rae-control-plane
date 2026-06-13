"""SQLAlchemy Base Class and Database Session

Central database configuration for R.A.E. Control Plane
Enterprise-grade: Connection pooling, retry logic, audit logging
"""
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool, QueuePool
import os
import logging
from typing import Generator

# Configure logging
logger = logging.getLogger(__name__)

# Database URL from environment (12-factor app)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://rae_user:rae_password@localhost:5432/rae_control_plane"
)

# Engine configuration for production
# - pool_size: Max connections in pool
# - max_overflow: Additional connections beyond pool_size
# - pool_pre_ping: Test connections before using (handles stale connections)
# - echo: SQL logging (disable in production)
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,  # Critical for AWS RDS/Aurora
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",
    connect_args={
        "options": "-c timezone=utc",  # Force UTC for all connections
    }
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False  # Prevent lazy-loading issues after commit
)

# Declarative base for all models
Base = declarative_base()


# Database session dependency for FastAPI
def get_db() -> Generator[Session, None, None]:
    """Dependency for FastAPI endpoints
    
    Usage:
        @app.get("/workflows")
        def list_workflows(db: Session = Depends(get_db)):
            return db.query(Workflow).all()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()  # Auto-commit on success
    except Exception as e:
        db.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        db.close()


# Event listeners for audit logging
@event.listens_for(engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    """Log database connections for audit"""
    logger.info(f"Database connection established: {connection_record.info}")


@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    """Log connection checkout from pool"""
    logger.debug(f"Connection checked out from pool")


def init_db():
    """Initialize database schema
    
    Creates all tables defined in models.
    Use Alembic migrations in production.
    """
    Base.metadata.create_all(bind=engine)
    logger.info("Database schema initialized")


def dispose_db():
    """Dispose of database engine and connections
    
    Call on application shutdown
    """
    engine.dispose()
    logger.info("Database connections disposed")
