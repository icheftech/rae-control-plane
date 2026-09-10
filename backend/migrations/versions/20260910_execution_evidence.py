"""Add immutable execution context, decision snapshots and causal events."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '20260910_evidence'
down_revision = '20260910_ownership'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('execution_contexts',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('tenant_id', sa.UUID(), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('actor_id', sa.UUID(), nullable=False),
        sa.Column('workflow_id', sa.UUID(), nullable=False),
        sa.Column('protected_resource_scope', JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False))
    op.add_column('orchestration_runs', sa.Column('context_id', sa.UUID(), sa.ForeignKey('execution_contexts.id')))
    op.create_table('policy_snapshots',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('tenant_id', sa.UUID(), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('context_id', sa.UUID(), sa.ForeignKey('execution_contexts.id'), nullable=False),
        sa.Column('schema_version', sa.Integer(), nullable=False),
        sa.Column('content', JSONB(), nullable=False),
        sa.Column('content_hash', sa.String(64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False))
    op.create_table('execution_events',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('tenant_id', sa.UUID(), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('run_id', sa.UUID(), sa.ForeignKey('orchestration_runs.id'), nullable=False),
        sa.Column('context_id', sa.UUID(), sa.ForeignKey('execution_contexts.id'), nullable=False),
        sa.Column('actor_id', sa.UUID(), nullable=False),
        sa.Column('event_type', sa.String(40), nullable=False),
        sa.Column('step_id', sa.String(80)),
        sa.Column('parent_event_id', sa.UUID(), sa.ForeignKey('execution_events.id')),
        sa.Column('caused_by_event_id', sa.UUID(), sa.ForeignKey('execution_events.id')),
        sa.Column('policy_snapshot_id', sa.UUID(), sa.ForeignKey('policy_snapshots.id')),
        sa.Column('state', sa.String(20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('details', JSONB(), nullable=False))
    for table in ('execution_contexts','policy_snapshots','execution_events'):
        op.create_index(f'ix_{table}_tenant_id', table, ['tenant_id'])
    op.create_index('ix_execution_events_run_id', 'execution_events', ['run_id'])
    op.execute("CREATE FUNCTION rae_immutable_evidence() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Execution evidence is immutable'; END $$")
    for table in ('execution_contexts','policy_snapshots','execution_events'):
        op.execute(f'CREATE TRIGGER immutable_evidence BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION rae_immutable_evidence()')
    op.execute("CREATE FUNCTION rae_immutable_run_identity() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.context_id IS DISTINCT FROM OLD.context_id OR NEW.tenant_id IS DISTINCT FROM OLD.tenant_id OR NEW.actor_id IS DISTINCT FROM OLD.actor_id OR NEW.workflow_id IS DISTINCT FROM OLD.workflow_id THEN RAISE EXCEPTION 'Run identity is immutable'; END IF; RETURN NEW; END $$")
    op.execute('CREATE TRIGGER immutable_run_identity BEFORE UPDATE ON orchestration_runs FOR EACH ROW EXECUTE FUNCTION rae_immutable_run_identity()')


def downgrade():
    op.execute('DROP TRIGGER immutable_run_identity ON orchestration_runs')
    op.execute('DROP FUNCTION rae_immutable_run_identity()')
    op.drop_table('execution_events')
    op.drop_table('policy_snapshots')
    op.drop_column('orchestration_runs','context_id')
    op.drop_table('execution_contexts')
    op.execute('DROP FUNCTION rae_immutable_evidence()')
