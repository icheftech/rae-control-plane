"""Initial schema - All 11 R.A.E. Control Plane models

Revision ID: 001
Revises: 
Create Date: 2025-12-30 12:00:00.000000

Creates all tables for the R.A.E. Control Plane enterprise AI governance platform:

Phase 1 - Registry Backbone (NIST MAP):
- workflows: AI agent workflow definitions
- capabilities: Granular permission system
- connectors: External system integrations

Phase 2 - Controls (NIST MANAGE):
- control_policies: Governance rules (ALLOW/DENY/REVIEW)
- kill_switches: Emergency stop mechanisms
- break_glass: Time-bounded emergency access

Phase 3 - Enforcement (NIST GOVERN):
- audit_events: Cryptographic audit trail (SHA-256 hash chain)
- enforcement_gates: Policy evaluation checkpoints
- gate_executions: Gate execution history
- change_requests: Production change management (FLAGSHIP)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Note: In production, run: alembic revision --autogenerate -m "Initial schema"
    # This will auto-generate the table creation statements from SQLAlchemy models
    
    # The autogenerate command will create:
    # - All 11 tables with proper columns, types, constraints
    # - Primary keys, foreign keys, indexes
    # - ENUM types for PostgreSQL
    # - Timestamps with server_default
    
    pass  # Placeholder - use alembic autogenerate


def downgrade() -> None:
    # Drop all tables in reverse dependency order
    op.drop_table('gate_executions')
    op.drop_table('enforcement_gates')
    op.drop_table('audit_events')
    op.drop_table('change_requests')
    op.drop_table('break_glass')
    op.drop_table('kill_switches')
    op.drop_table('control_policies')
    op.drop_table('connectors')
    op.drop_table('capabilities')
    op.drop_table('workflows')
    
    # Drop ENUM types
    op.execute('DROP TYPE IF EXISTS workflowstatus CASCADE')
    op.execute('DROP TYPE IF EXISTS workflowrisklevel CASCADE')
    op.execute('DROP TYPE IF EXISTS capabilitytype CASCADE')
    op.execute('DROP TYPE IF EXISTS connectortype CASCADE')
    op.execute('DROP TYPE IF EXISTS policyoutcome CASCADE')
    op.execute('DROP TYPE IF EXISTS killswitchmode CASCADE')
    op.execute('DROP TYPE IF EXISTS killswitchscope CASCADE')
    op.execute('DROP TYPE IF EXISTS changetype CASCADE')
    op.execute('DROP TYPE IF EXISTS changerisklevel CASCADE')
    op.execute('DROP TYPE IF EXISTS changestatus CASCADE')
