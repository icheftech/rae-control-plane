"""Server-side SSO sessions for the first installation tenant."""
from alembic import op
import sqlalchemy as sa
revision = '20260910_sessions'
down_revision = '20260910_runs'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('browser_sessions',
        sa.Column('token_hash', sa.String(64), primary_key=True),
        sa.Column('subject', sa.String(255), nullable=False),
        sa.Column('tenant_id', sa.UUID(), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False))


def downgrade():
    op.drop_table('browser_sessions')
