"""Database Configuration and Session Management

Phase 4: Integration
Purpose: SQLAlchemy database engine, session management, and connection handling

This module provides:
- Database engine configuration
- Session factory for database transactions
- Dependency injection for FastAPI endpoints
- Connection pooling configuration
- Database initialization and health checks
"""
import os
from typing import Generator
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool, QueuePool

# Import Base and all models to ensure they're registered
from app.db.models import Base

# Database URL from environment variable
# Format: postgresql://user:password@host:port/database
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://rae_user:rae_password@localhost:5432/rae_control_plane"
)

# Engine configuration
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before using them
    pool_size=10,  # Number of connections to maintain
    max_overflow=20,  # Additional connections when pool is exhausted
    pool_recycle=3600,  # Recycle connections after 1 hour
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",  # Log SQL statements
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_db() -> Generator[Session, None, None]:
    """Dependency injection for FastAPI endpoints.
    
    Usage:
        @app.get("/workflows")
        def get_workflows(db: Session = Depends(get_db)):
            return db.query(Workflow).all()
    
    Yields:
        Database session
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """Initialize database tables.
    
    Creates all tables defined in the models.
    Should only be used for development/testing.
    In production, use Alembic migrations instead.
    """
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")


def drop_db() -> None:
    """Drop all database tables.
    
    WARNING: This will delete all data!
    Only use for development/testing.
    """
    Base.metadata.drop_all(bind=engine)
    print("⚠️  All database tables dropped")


def check_db_connection() -> bool:
    """Health check for database connection.
    
    Returns:
        True if database is reachable, False otherwise
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


# Enable PostgreSQL-specific optimizations
@event.listens_for(engine, "connect")
def set_postgresql_pragma(dbapi_conn, connection_record):
    """Set PostgreSQL connection parameters for optimal performance."""
    cursor = dbapi_conn.cursor()
    # Set statement timeout to prevent long-running queries
    cursor.execute("SET statement_timeout = '30s'")
    cursor.close()


if __name__ == "__main__":
    # Test database connection
    print("Testing database connection...")
    if check_db_connection():
        print("✅ Database connection successful")
        print(f"📊 Database URL: {DATABASE_URL.split('@')[1]}")
    else:
        print("❌ Database connection failed")
