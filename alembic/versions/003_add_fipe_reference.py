"""add_fipe_reference

Revision ID: 003_add_fipe_reference
Revises: 002_parts_catalog
Create Date: 2025-01-16 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '003_add_fipe_reference'
down_revision = '002_parts_catalog'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('vehicle', sa.Column('fipe_reference', sa.String(length=50), nullable=True))

def downgrade() -> None:
    op.drop_column('vehicle', 'fipe_reference')
