"""Add content-free run history without changing existing tables."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '20260910_runs'
down_revision = 'bdc5931c12bf'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('orchestration_runs',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('workflow_id', sa.UUID(), nullable=False),
        sa.Column('source', sa.String(30), nullable=False),
        sa.Column('request_id', sa.String(36), nullable=False),
        sa.Column('actor_id', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('step_count', sa.Integer(), nullable=False),
        sa.Column('decision_reason', sa.String(500)),
        sa.CheckConstraint("status IN ('pending','success','error','denied')", name='run_status'))
    op.create_index('ix_orchestration_runs_workflow_id', 'orchestration_runs', ['workflow_id'])
    op.create_index('ix_runs_status_time', 'orchestration_runs', ['status', 'started_at'])
    op.create_table('orchestration_run_events',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('run_id', sa.UUID(), sa.ForeignKey('orchestration_runs.id'), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('step_id', sa.String(80), nullable=False),
        sa.Column('step_type', sa.String(30), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('decision_reason', sa.String(500)),
        sa.Column('model', sa.String(120)),
        sa.Column('token_usage', JSONB(), nullable=False),
        sa.Column('input_ref', sa.String(160), nullable=False),
        sa.Column('output_ref', sa.String(160)),
        sa.CheckConstraint("status IN ('pending','success','error','denied')", name='run_event_status'))
    op.create_index('ix_orchestration_run_events_run_id', 'orchestration_run_events', ['run_id'])


def downgrade():
    op.drop_table('orchestration_run_events')
    op.drop_table('orchestration_runs')
