"""add_fipe_cache_tracking

Revision ID: 004_fipe_cache_tracking
Revises: 003_add_fipe_reference
Create Date: 2025-01-17 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '004_fipe_cache_tracking'
down_revision = '003_add_fipe_reference'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'fipe_cache_tracking',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('cache_key', sa.String(length=150), nullable=False, unique=True),
        sa.Column('fipe_reference', sa.String(length=50), nullable=False),
        sa.Column('last_synced_at', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='VALID')
    )
    op.create_index('ix_fipe_cache_tracking_cache_key', 'fipe_cache_tracking', ['cache_key'])
    op.create_index('ix_fipe_cache_tracking_fipe_reference', 'fipe_cache_tracking', ['fipe_reference'])

def downgrade() -> None:
    op.drop_table('fipe_cache_tracking')
