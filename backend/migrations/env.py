"""Alembic Migration Environment
R.A.E. Control Plane - Database Migration Runtime Environment

This module configures the Alembic migration environment for both offline
and online migration modes. It imports all models to ensure autogenerate
can detect schema changes.
"""

from logging.config import fileConfig
import os

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Import Base and all models for autogenerate support
from app.db.models import Base
from app.db.models.workflow import Workflow
from app.db.models.capability import Capability
from app.db.models.connector import Connector
from app.db.models.control_policy import ControlPolicy, PolicyStatus, PolicyEnforcement
from app.db.models.kill_switch import KillSwitch, KillSwitchState, KillSwitchScope
from app.db.models.break_glass import BreakGlass, BreakGlassStatus
from app.db.models.audit_event import AuditEvent
from app.db.models.enforcement_gate import EnforcementGate, GateExecution, GateType, GateOutcome
from app.db.models.change_request import ChangeRequest, ChangeType, ChangeStatus, ChangeRiskLevel

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata for autogenerate
target_metadata = Base.metadata

# Override sqlalchemy.url from environment variable if present
if os.getenv("DATABASE_URL"):
    config.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL"))


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.
    
    This configures the context with just a URL and not an Engine,
    though an Engine is acceptable here as well. By skipping the Engine
    creation we don't even need a DBAPI to be available.
    
    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.
    
    In this scenario we need to create an Engine and associate a
    connection with the context.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            # Include schemas for multi-tenant support if needed
            # include_schemas=True,
        )

        with context.begin_transaction():
            context.run_migrations()


# Determine which mode to run
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
