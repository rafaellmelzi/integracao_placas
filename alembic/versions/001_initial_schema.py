"""initial_schema

Revision ID: 001_initial_schema
Revises:
Create Date: 2025-01-15 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. Vehicles Schema Tables
    op.create_table(
        'vehicle_make',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('normalized_name', sa.String(length=100), nullable=False)
    )
    op.create_index('ix_vehicle_make_name', 'vehicle_make', ['name'], unique=True)
    op.create_index('ix_vehicle_make_normalized_name', 'vehicle_make', ['normalized_name'], unique=True)

    op.create_table(
        'vehicle_model',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('make_id', sa.Integer(), sa.ForeignKey('vehicle_make.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('normalized_name', sa.String(length=100), nullable=False),
        sa.UniqueConstraint('make_id', 'normalized_name', name='uq_make_model_normalized')
    )
    op.create_index('ix_vehicle_model_name', 'vehicle_model', ['name'])
    op.create_index('ix_vehicle_model_normalized_name', 'vehicle_model', ['normalized_name'])

    op.create_table(
        'vehicle_generation',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('model_id', sa.Integer(), sa.ForeignKey('vehicle_model.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('start_year', sa.Integer(), nullable=True),
        sa.Column('end_year', sa.Integer(), nullable=True)
    )

    op.create_table(
        'vehicle_version',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('normalized_name', sa.String(length=150), nullable=False)
    )
    op.create_index('ix_vehicle_version_name', 'vehicle_version', ['name'])
    op.create_index('ix_vehicle_version_normalized_name', 'vehicle_version', ['normalized_name'])

    op.create_table(
        'vehicle_engine',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('code', sa.String(length=50), nullable=True),
        sa.Column('description', sa.String(length=100), nullable=False),
        sa.Column('displacement', sa.String(length=20), nullable=True),
        sa.Column('valves', sa.Integer(), nullable=True),
        sa.Column('power_hp', sa.Integer(), nullable=True)
    )

    op.create_table(
        'vehicle_transmission',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('gears', sa.Integer(), nullable=True)
    )

    op.create_table(
        'vehicle_fuel',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(length=50), nullable=False, unique=True)
    )

    op.create_table(
        'vehicle',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('make_id', sa.Integer(), sa.ForeignKey('vehicle_make.id'), nullable=False),
        sa.Column('model_id', sa.Integer(), sa.ForeignKey('vehicle_model.id'), nullable=False),
        sa.Column('version_id', sa.Integer(), sa.ForeignKey('vehicle_version.id'), nullable=True),
        sa.Column('engine_id', sa.Integer(), sa.ForeignKey('vehicle_engine.id'), nullable=True),
        sa.Column('transmission_id', sa.Integer(), sa.ForeignKey('vehicle_transmission.id'), nullable=True),
        sa.Column('fuel_id', sa.Integer(), sa.ForeignKey('vehicle_fuel.id'), nullable=True),
        sa.Column('year_manufacture', sa.Integer(), nullable=False),
        sa.Column('year_model', sa.Integer(), nullable=False),
        sa.Column('fipe_code', sa.String(length=20), nullable=True)
    )
    op.create_index('ix_vehicle_make_id', 'vehicle', ['make_id'])
    op.create_index('ix_vehicle_model_id', 'vehicle', ['model_id'])
    op.create_index('ix_vehicle_version_id', 'vehicle', ['version_id'])
    op.create_index('ix_vehicle_engine_id', 'vehicle', ['engine_id'])
    op.create_index('ix_vehicle_year_manufacture', 'vehicle', ['year_manufacture'])
    op.create_index('ix_vehicle_year_model', 'vehicle', ['year_model'])
    op.create_index('ix_vehicle_fipe_code', 'vehicle', ['fipe_code'])

    op.create_table(
        'vehicle_plate_cache',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('plate', sa.String(length=10), nullable=False, unique=True),
        sa.Column('vehicle_id', sa.Integer(), sa.ForeignKey('vehicle.id'), nullable=True),
        sa.Column('is_ambiguous', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('possible_vehicle_ids', sa.Text(), nullable=True),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('source_vehicle_id', sa.String(length=100), nullable=True),
        sa.Column('consulted_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('data_quality', sa.String(length=20), nullable=False, server_default='HIGH'),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('raw_response_hash', sa.String(length=64), nullable=False),
        sa.Column('raw_response_json', sa.Text(), nullable=True)
    )
    op.create_index('ix_vehicle_plate_cache_plate', 'vehicle_plate_cache', ['plate'])
    op.create_index('ix_vehicle_plate_cache_vehicle_id', 'vehicle_plate_cache', ['vehicle_id'])
    op.create_index('ix_vehicle_plate_cache_expires_at', 'vehicle_plate_cache', ['expires_at'])

    # 2. Parts Schema Tables (Original initial state WITHOUT 002 enhanced columns)
    op.create_table(
        'part_manufacturer',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(length=100), nullable=False, unique=True),
        sa.Column('code', sa.String(length=50), nullable=True)
    )
    op.create_index('ix_part_manufacturer_name', 'part_manufacturer', ['name'])

    op.create_table(
        'part_category',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('code', sa.String(length=50), nullable=False, unique=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('synonyms', sa.Text(), nullable=True)
    )
    op.create_index('ix_part_category_code', 'part_category', ['code'])

    op.create_table(
        'part',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('manufacturer_id', sa.Integer(), sa.ForeignKey('part_manufacturer.id'), nullable=False),
        sa.Column('category_id', sa.Integer(), sa.ForeignKey('part_category.id'), nullable=False),
        sa.Column('manufacturer_part_number', sa.String(length=100), nullable=False),
        sa.Column('ean', sa.String(length=20), nullable=True),
        sa.Column('description', sa.String(length=255), nullable=False),
        sa.UniqueConstraint('manufacturer_id', 'manufacturer_part_number', name='uq_mfg_part_number')
    )
    op.create_index('ix_part_manufacturer_id', 'part', ['manufacturer_id'])
    op.create_index('ix_part_category_id', 'part', ['category_id'])
    op.create_index('ix_part_manufacturer_part_number', 'part', ['manufacturer_part_number'])
    op.create_index('ix_part_ean', 'part', ['ean'])

    op.create_table(
        'part_application',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('part_id', sa.Integer(), sa.ForeignKey('part.id', ondelete='CASCADE'), nullable=False),
        sa.Column('vehicle_id', sa.Integer(), sa.ForeignKey('vehicle.id', ondelete='CASCADE'), nullable=False),
        sa.Column('year_from', sa.Integer(), nullable=True),
        sa.Column('year_to', sa.Integer(), nullable=True),
        sa.Column('engine_spec', sa.String(length=100), nullable=True),
        sa.Column('position', sa.String(length=50), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('source', sa.String(length=100), nullable=False, server_default='CATALOGO_FABRICANTE'),
        sa.Column('source_updated_at', sa.DateTime(), nullable=False),
        sa.Column('confidence', sa.Enum('CONFIRMED', 'HIGH_CONFIDENCE', 'POSSIBLE', 'UNVERIFIED', name='confidencelevel'), nullable=False)
    )
    op.create_index('ix_part_application_part_id', 'part_application', ['part_id'])
    op.create_index('ix_part_application_vehicle_id', 'part_application', ['vehicle_id'])

    op.create_table(
        'part_cross_reference',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('part_id', sa.Integer(), sa.ForeignKey('part.id', ondelete='CASCADE'), nullable=False),
        sa.Column('reference_part_id', sa.Integer(), sa.ForeignKey('part.id', ondelete='CASCADE'), nullable=False),
        sa.Column('reference_type', sa.Enum('OEM', 'AFTERMARKET', 'EQUIVALENT', 'REPLACEMENT', name='crossreferencetype'), nullable=False),
        sa.Column('source', sa.String(length=100), nullable=False, server_default='MANUFACTURER'),
        sa.Column('confidence', sa.Enum('CONFIRMED', 'HIGH_CONFIDENCE', 'POSSIBLE', 'UNVERIFIED', name='confidencelevel'), nullable=False)
    )
    op.create_index('ix_part_cross_reference_part_id', 'part_cross_reference', ['part_id'])
    op.create_index('ix_part_cross_reference_reference_part_id', 'part_cross_reference', ['reference_part_id'])

    op.create_table(
        'erp_product_mapping',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('erp_product_id', sa.String(length=100), nullable=False, unique=True),
        sa.Column('part_id', sa.Integer(), sa.ForeignKey('part.id'), nullable=True),
        sa.Column('manufacturer_code', sa.String(length=100), nullable=True),
        sa.Column('ean', sa.String(length=20), nullable=True),
        sa.Column('mapping_type', sa.Enum('EAN', 'MANUFACTURER_CODE', 'OEM_CODE', 'CROSS_REFERENCE', 'MANUAL', 'SUGGESTED_AI', name='erpproductmappingtype'), nullable=False),
        sa.Column('confidence', sa.Enum('CONFIRMED', 'HIGH_CONFIDENCE', 'POSSIBLE', 'UNVERIFIED', name='confidencelevel'), nullable=False),
        sa.Column('verified', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False)
    )
    op.create_index('ix_erp_product_mapping_erp_product_id', 'erp_product_mapping', ['erp_product_id'])
    op.create_index('ix_erp_product_mapping_part_id', 'erp_product_mapping', ['part_id'])
    op.create_index('ix_erp_product_mapping_manufacturer_code', 'erp_product_mapping', ['manufacturer_code'])
    op.create_index('ix_erp_product_mapping_ean', 'erp_product_mapping', ['ean'])

    # 3. System & Log Tables
    op.create_table(
        'data_source',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(length=100), nullable=False, unique=True),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('config_json', sa.Text(), nullable=True)
    )

    op.create_table(
        'api_request_log',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('endpoint', sa.String(length=100), nullable=False),
        sa.Column('query_params', sa.Text(), nullable=True),
        sa.Column('status_code', sa.Integer(), nullable=False),
        sa.Column('response_time_ms', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False)
    )
    op.create_index('ix_api_request_log_created_at', 'api_request_log', ['created_at'])

    op.create_table(
        'sync_log',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('source_name', sa.String(length=100), nullable=False),
        sa.Column('records_processed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('records_success', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('records_failed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False)
    )

def downgrade() -> None:
    op.drop_table('sync_log')
    op.drop_table('api_request_log')
    op.drop_table('data_source')
    op.drop_table('erp_product_mapping')
    op.drop_table('part_cross_reference')
    op.drop_table('part_application')
    op.drop_table('part')
    op.drop_table('part_category')
    op.drop_table('part_manufacturer')
    op.drop_table('vehicle_plate_cache')
    op.drop_table('vehicle')
    op.drop_table('vehicle_fuel')
    op.drop_table('vehicle_transmission')
    op.drop_table('vehicle_engine')
    op.drop_table('vehicle_version')
    op.drop_table('vehicle_generation')
    op.drop_table('vehicle_model')
    op.drop_table('vehicle_make')
