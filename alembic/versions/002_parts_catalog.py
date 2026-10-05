"""parts_catalog

Revision ID: 002_parts_catalog
Revises: 001_initial_schema
Create Date: 2025-01-15 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from app.db.models import Base

revision = '002_parts_catalog'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. Add columns to part table
    op.add_column('part', sa.Column('oem_codes', sa.Text(), nullable=True))
    op.add_column('part', sa.Column('equivalent_codes', sa.Text(), nullable=True))
    op.add_column('part', sa.Column('technical_specs', sa.Text(), nullable=True))
    op.add_column('part', sa.Column('source', sa.String(length=100), nullable=False, server_default='CATALOGO_OFICIAL'))

    # 2. Add column to part_application table
    op.add_column('part_application', sa.Column('axis', sa.String(length=50), nullable=True))

    # 3. Create missing tables if they don't exist
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)

def downgrade() -> None:
    op.drop_column('part_application', 'axis')
    op.drop_column('part', 'source')
    op.drop_column('part', 'technical_specs')
    op.drop_column('part', 'equivalent_codes')
    op.drop_column('part', 'oem_codes')
