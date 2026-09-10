"""Backfill installation resources to Southern Shade; enforce ownership."""
from alembic import op
import sqlalchemy as sa
from uuid import uuid4

revision = '20260910_ownership'
down_revision = '20260910_sessions'
branch_labels = None
depends_on = None
TABLES = ('workflows', 'capabilities', 'connectors', 'control_policies',
          'kill_switches', 'break_glass', 'audit_events', 'enforcement_gates',
          'gate_executions', 'change_requests', 'orchestration_runs', 'orchestration_run_events')


def upgrade():
    db = op.get_bind()
    tenant = db.scalar(sa.text("SELECT id FROM tenants WHERE tenant_key='southern_shade_technologies'"))
    if tenant is None:
        tenant = uuid4()
        db.execute(sa.text("INSERT INTO tenants (id,tenant_key,tenant_name,is_active,settings,created_at,updated_at,created_by) VALUES (:id,'southern_shade_technologies','Southern Shade Technologies',true,'{}',now(),now(),'ownership-migration')"), {'id':tenant})
    for table in TABLES:
        op.add_column(table, sa.Column('tenant_id', sa.UUID(), nullable=True))
        db.execute(sa.text(f'UPDATE {table} SET tenant_id=:tenant'), {'tenant':tenant})
        op.alter_column(table, 'tenant_id', nullable=False)
        op.create_foreign_key(f'fk_{table}_tenant', table, 'tenants', ['tenant_id'], ['id'])
        op.create_index(f'ix_{table}_tenant_id', table, ['tenant_id'])
        op.create_unique_constraint(f'uq_{table}_tenant_resource',table,['tenant_id','id'])
    inspector = sa.inspect(db)
    for table in TABLES:
        for fk in inspector.get_foreign_keys(table):
            if fk['referred_table'] in TABLES and fk['referred_columns'] == ['id']:
                column = fk['constrained_columns'][0]
                op.create_foreign_key(f'ownership_{table}_{column}', table, fk['referred_table'],
                                     ['tenant_id',column], ['tenant_id','id'])
    # Equal names/versions in different tenants must not conflict.
    op.drop_constraint('uq_workflow_name_version', 'workflows', type_='unique')
    op.create_unique_constraint('uq_workflow_name_version', 'workflows', ['tenant_id','name','version'])


def downgrade():
    # This may reject a downgrade when different tenants use the same name/version.
    op.drop_constraint('uq_workflow_name_version', 'workflows', type_='unique')
    op.create_unique_constraint('uq_workflow_name_version', 'workflows', ['name','version'])
    inspector = sa.inspect(op.get_bind())
    for table in TABLES:
        for fk in inspector.get_foreign_keys(table):
            if (fk['name'] or '').startswith('ownership_'):
                op.drop_constraint(fk['name'], table, type_='foreignkey')
    for table in reversed(TABLES):
        op.drop_column(table, 'tenant_id')
