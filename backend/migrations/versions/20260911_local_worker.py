"""Persistent local queue and worker presence."""
from alembic import op
import sqlalchemy as sa

revision = '20260911_worker'
down_revision = '20260910_evidence'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('local_workers',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('tenant_id', sa.UUID(), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('heartbeat_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('stopped_at', sa.DateTime(timezone=True)))
    op.create_index('ix_local_workers_tenant_id', 'local_workers', ['tenant_id'])
    op.create_table('local_jobs',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('tenant_id', sa.UUID(), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('workflow_id', sa.UUID(), sa.ForeignKey('workflows.id'), nullable=False),
        sa.Column('requested_by', sa.UUID(), nullable=False),
        sa.Column('idempotency_key', sa.UUID(), nullable=False),
        sa.Column('task_key', sa.String(80), nullable=False),
        sa.Column('task_hash', sa.String(64), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('run_id', sa.UUID(), unique=True),
        sa.Column('worker_id', sa.UUID(), sa.ForeignKey('local_workers.id')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True)),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('reason', sa.String(500)),
        sa.UniqueConstraint('tenant_id', 'idempotency_key', name='uq_job_submission'),
        sa.ForeignKeyConstraint(['tenant_id','workflow_id'], ['workflows.tenant_id','workflows.id']),
        sa.CheckConstraint("status IN ('queued','running','success','denied','error','interrupted')", name='local_job_status'))
    op.create_index('ix_local_jobs_tenant_id', 'local_jobs', ['tenant_id'])
    op.create_index('ix_local_jobs_status', 'local_jobs', ['status'])


def downgrade():
    op.drop_table('local_jobs')
    op.drop_table('local_workers')
