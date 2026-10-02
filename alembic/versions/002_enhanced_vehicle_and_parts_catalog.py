"""enhanced_vehicle_and_parts_catalog

Revision ID: 002_enhanced_vehicle_and_parts_catalog
Revises: 001_initial_schema
Create Date: 2025-01-15 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from app.db.models import Base

revision = '002_enhanced_vehicle_and_parts_catalog'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None

def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)

def downgrade() -> None:
    pass
