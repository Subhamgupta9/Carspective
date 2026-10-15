"""phase17_market_observations

Revision ID: f3d730c46a23
Revises: e2c829b35f12
Create Date: 2026-10-09 14:42:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3d730c46a23'
down_revision: Union[str, Sequence[str], None] = 'e2c829b35f12'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    # current_market_observations
    if 'current_market_observations' not in existing_tables:
        op.create_table(
            'current_market_observations',
            sa.Column('id', sa.String(length=64), nullable=False),
            sa.Column('source_id', sa.String(length=64), nullable=False),
            sa.Column('source_record_reference', sa.String(length=128), nullable=False),
            sa.Column('observed_at', sa.DateTime(), nullable=False),
            sa.Column('published_at', sa.DateTime(), nullable=True),
            sa.Column('canonical_vehicle_id', sa.String(length=255), nullable=False),
            sa.Column('observation_type', sa.String(length=32), nullable=False),
            sa.Column('asking_price', sa.Float(), nullable=False),
            sa.Column('model_year', sa.Integer(), nullable=False),
            sa.Column('mileage', sa.Float(), nullable=False),
            sa.Column('location_city', sa.String(length=64), nullable=True),
            sa.Column('location_region', sa.String(length=64), nullable=True),
            sa.Column('seller_type', sa.String(length=32), nullable=False),
            sa.Column('transmission', sa.String(length=32), nullable=False),
            sa.Column('fuel_type', sa.String(length=32), nullable=False),
            sa.Column('body_type', sa.String(length=32), nullable=True),
            sa.Column('listing_status', sa.String(length=32), nullable=False),
            sa.Column('source_url', sa.String(length=512), nullable=True),
            sa.Column('evidence_state', sa.String(length=32), nullable=False),
            sa.Column('freshness_state', sa.String(length=32), nullable=False),
            sa.Column('ingestion_batch_id', sa.String(length=64), nullable=True),
            sa.Column('data_quality_status', sa.String(length=32), nullable=False),
            sa.Column('duplicate_status', sa.String(length=32), nullable=False),
            sa.Column('duplicate_of_id', sa.String(length=64), nullable=True),
            sa.Column('is_outlier', sa.Boolean(), nullable=False),
            sa.Column('outlier_reasons', sa.Text(), nullable=True),
            sa.Column('analytical_eligibility', sa.Boolean(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_current_market_observations_canonical_vehicle_id'), 'current_market_observations', ['canonical_vehicle_id'], unique=False)
        op.create_index(op.f('ix_current_market_observations_ingestion_batch_id'), 'current_market_observations', ['ingestion_batch_id'], unique=False)
        op.create_index(op.f('ix_current_market_observations_location_city'), 'current_market_observations', ['location_city'], unique=False)
        op.create_index(op.f('ix_current_market_observations_location_region'), 'current_market_observations', ['location_region'], unique=False)
        op.create_index(op.f('ix_current_market_observations_observed_at'), 'current_market_observations', ['observed_at'], unique=False)
        op.create_index(op.f('ix_current_market_observations_source_id'), 'current_market_observations', ['source_id'], unique=False)
        op.create_index(op.f('ix_current_market_observations_source_record_reference'), 'current_market_observations', ['source_record_reference'], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if 'current_market_observations' in existing_tables:
        op.drop_table('current_market_observations')
