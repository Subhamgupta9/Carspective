"""phase16_data_pipeline_governance

Revision ID: e2c829b35f12
Revises: d1b918a24e01
Create Date: 2026-10-09 14:41:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e2c829b35f12'
down_revision: Union[str, Sequence[str], None] = 'd1b918a24e01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    # 1. ingestion_batches
    if 'ingestion_batches' not in existing_tables:
        op.create_table(
            'ingestion_batches',
            sa.Column('id', sa.String(length=64), nullable=False),
            sa.Column('source_id', sa.String(length=64), nullable=False),
            sa.Column('ingestion_timestamp', sa.DateTime(), nullable=False),
            sa.Column('source_snapshot_reference', sa.String(length=255), nullable=True),
            sa.Column('record_count', sa.Integer(), nullable=False),
            sa.Column('accepted_count', sa.Integer(), nullable=False),
            sa.Column('rejected_count', sa.Integer(), nullable=False),
            sa.Column('validation_status', sa.String(length=32), nullable=False),
            sa.Column('normalization_status', sa.String(length=32), nullable=False),
            sa.Column('canonical_mapping_status', sa.String(length=32), nullable=False),
            sa.Column('checksum', sa.String(length=64), nullable=False),
            sa.Column('processing_duration_ms', sa.Float(), nullable=False),
            sa.Column('commit_status', sa.String(length=32), nullable=False),
            sa.Column('error_summary', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_ingestion_batches_source_id'), 'ingestion_batches', ['source_id'], unique=False)

    # 2. ingestion_records
    if 'ingestion_records' not in existing_tables:
        op.create_table(
            'ingestion_records',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('batch_id', sa.String(length=64), nullable=False),
            sa.Column('record_index', sa.Integer(), nullable=False),
            sa.Column('raw_payload', sa.Text(), nullable=False),
            sa.Column('canonical_vehicle_id', sa.String(length=255), nullable=True),
            sa.Column('mapping_outcome', sa.String(length=32), nullable=False),
            sa.Column('is_valid', sa.Boolean(), nullable=False),
            sa.Column('rejection_reasons', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['batch_id'], ['ingestion_batches.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_ingestion_records_batch_id'), 'ingestion_records', ['batch_id'], unique=False)
        op.create_index(op.f('ix_ingestion_records_canonical_vehicle_id'), 'ingestion_records', ['canonical_vehicle_id'], unique=False)

    # 3. data_quality_reports
    if 'data_quality_reports' not in existing_tables:
        op.create_table(
            'data_quality_reports',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('batch_id', sa.String(length=64), nullable=True),
            sa.Column('dataset_name', sa.String(length=100), nullable=False),
            sa.Column('overall_score', sa.Float(), nullable=False),
            sa.Column('quality_status', sa.String(length=32), nullable=False),
            sa.Column('metrics_json', sa.Text(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_data_quality_reports_batch_id'), 'data_quality_reports', ['batch_id'], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    tables_to_drop = [
        'data_quality_reports',
        'ingestion_records',
        'ingestion_batches',
    ]

    for tbl in tables_to_drop:
        if tbl in existing_tables:
            op.drop_table(tbl)
