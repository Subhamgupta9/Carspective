"""phase11_vehicle_knowledge

Revision ID: d1b918a24e01
Revises: cb1c167fc450
Create Date: 2026-10-09 14:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1b918a24e01'
down_revision: Union[str, Sequence[str], None] = 'cb1c167fc450'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    # 1. vehicle_features
    if 'vehicle_features' not in existing_tables:
        op.create_table(
            'vehicle_features',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('feature_key', sa.String(length=100), nullable=False),
            sa.Column('feature_name', sa.String(length=150), nullable=False),
            sa.Column('category', sa.String(length=50), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_vehicle_features_feature_key'), 'vehicle_features', ['feature_key'], unique=True)

    # 2. vehicle_specifications
    if 'vehicle_specifications' not in existing_tables:
        op.create_table(
            'vehicle_specifications',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('canonical_vehicle_id', sa.String(length=255), nullable=False),
            sa.Column('generation_id', sa.String(length=36), nullable=True),
            sa.Column('variant_id', sa.String(length=36), nullable=True),
            sa.Column('powertrain_id', sa.String(length=36), nullable=True),
            sa.Column('engine_type', sa.String(length=150), nullable=True),
            sa.Column('displacement_cc', sa.Integer(), nullable=True),
            sa.Column('cylinders', sa.Integer(), nullable=True),
            sa.Column('valves_per_cylinder', sa.Integer(), nullable=True),
            sa.Column('aspiration', sa.String(length=50), nullable=True),
            sa.Column('max_power_bhp', sa.Float(), nullable=True),
            sa.Column('max_power_rpm', sa.Integer(), nullable=True),
            sa.Column('max_torque_nm', sa.Float(), nullable=True),
            sa.Column('max_torque_rpm', sa.String(length=50), nullable=True),
            sa.Column('transmission', sa.String(length=50), nullable=True),
            sa.Column('drivetrain', sa.String(length=20), nullable=True, server_default='FWD'),
            sa.Column('fuel_type', sa.String(length=50), nullable=False),
            sa.Column('arai_mileage_kmpl', sa.Float(), nullable=True),
            sa.Column('fuel_tank_capacity_l', sa.Float(), nullable=True),
            sa.Column('emission_norm', sa.String(length=30), nullable=True),
            sa.Column('battery_capacity_kwh', sa.Float(), nullable=True),
            sa.Column('electric_range_km', sa.Float(), nullable=True),
            sa.Column('motor_output_ps', sa.Float(), nullable=True),
            sa.Column('evidence_state', sa.Enum('VERIFIED', 'SUPPORTED', 'EMPIRICAL', 'MODEL_ESTIMATE', 'INSUFFICIENT_DATA', 'UNVERIFIED', 'DEPRECATED', name='evidencestate'), nullable=False),
            sa.Column('source_id', sa.String(length=36), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['generation_id'], ['vehicle_generations.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['variant_id'], ['vehicle_variants.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['powertrain_id'], ['powertrain_configurations.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['source_id'], ['evidence_sources.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_vehicle_specifications_canonical_vehicle_id'), 'vehicle_specifications', ['canonical_vehicle_id'], unique=False)

    # 3. vehicle_dimensions
    if 'vehicle_dimensions' not in existing_tables:
        op.create_table(
            'vehicle_dimensions',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('canonical_vehicle_id', sa.String(length=255), nullable=False),
            sa.Column('generation_id', sa.String(length=36), nullable=False),
            sa.Column('length_mm', sa.Integer(), nullable=True),
            sa.Column('width_mm', sa.Integer(), nullable=True),
            sa.Column('height_mm', sa.Integer(), nullable=True),
            sa.Column('wheelbase_mm', sa.Integer(), nullable=True),
            sa.Column('ground_clearance_mm', sa.Integer(), nullable=True),
            sa.Column('boot_capacity_l', sa.Integer(), nullable=True),
            sa.Column('seating_capacity', sa.Integer(), nullable=True, server_default='5'),
            sa.Column('kerb_weight_kg', sa.Integer(), nullable=True),
            sa.Column('turning_radius_m', sa.Float(), nullable=True),
            sa.Column('evidence_state', sa.Enum('VERIFIED', 'SUPPORTED', 'EMPIRICAL', 'MODEL_ESTIMATE', 'INSUFFICIENT_DATA', 'UNVERIFIED', 'DEPRECATED', name='evidencestate'), nullable=False),
            sa.Column('source_id', sa.String(length=36), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['generation_id'], ['vehicle_generations.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['source_id'], ['evidence_sources.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_vehicle_dimensions_canonical_vehicle_id'), 'vehicle_dimensions', ['canonical_vehicle_id'], unique=False)

    # 4. vehicle_safety_ratings
    if 'vehicle_safety_ratings' not in existing_tables:
        op.create_table(
            'vehicle_safety_ratings',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('canonical_vehicle_id', sa.String(length=255), nullable=False),
            sa.Column('generation_id', sa.String(length=36), nullable=False),
            sa.Column('organization', sa.String(length=100), nullable=False),
            sa.Column('test_year', sa.Integer(), nullable=False),
            sa.Column('adult_stars', sa.Integer(), nullable=False),
            sa.Column('adult_score', sa.Float(), nullable=True),
            sa.Column('child_stars', sa.Integer(), nullable=True),
            sa.Column('child_score', sa.Float(), nullable=True),
            sa.Column('bodyshell_integrity', sa.String(length=100), nullable=True),
            sa.Column('standard_safety_equipment', sa.String(length=255), nullable=True),
            sa.Column('test_protocol', sa.String(length=150), nullable=True),
            sa.Column('evidence_state', sa.Enum('VERIFIED', 'SUPPORTED', 'EMPIRICAL', 'MODEL_ESTIMATE', 'INSUFFICIENT_DATA', 'UNVERIFIED', 'DEPRECATED', name='evidencestate'), nullable=False),
            sa.Column('source_id', sa.String(length=36), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['generation_id'], ['vehicle_generations.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['source_id'], ['evidence_sources.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_vehicle_safety_ratings_canonical_vehicle_id'), 'vehicle_safety_ratings', ['canonical_vehicle_id'], unique=False)

    # 5. variant_feature_mappings
    if 'variant_feature_mappings' not in existing_tables:
        op.create_table(
            'variant_feature_mappings',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('variant_id', sa.String(length=36), nullable=False),
            sa.Column('feature_key', sa.String(length=100), nullable=False),
            sa.Column('availability', sa.String(length=30), nullable=False, server_default='STANDARD'),
            sa.Column('details', sa.String(length=255), nullable=True),
            sa.Column('evidence_state', sa.Enum('VERIFIED', 'SUPPORTED', 'EMPIRICAL', 'MODEL_ESTIMATE', 'INSUFFICIENT_DATA', 'UNVERIFIED', 'DEPRECATED', name='evidencestate'), nullable=False),
            sa.Column('source_id', sa.String(length=36), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['variant_id'], ['vehicle_variants.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['source_id'], ['evidence_sources.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('variant_id', 'feature_key', name='uq_variant_feature')
        )
        op.create_index(op.f('ix_variant_feature_mappings_feature_key'), 'variant_feature_mappings', ['feature_key'], unique=False)

    # 6. ownership_profiles
    if 'ownership_profiles' not in existing_tables:
        op.create_table(
            'ownership_profiles',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('canonical_vehicle_id', sa.String(length=255), nullable=False),
            sa.Column('generation_id', sa.String(length=36), nullable=False),
            sa.Column('service_interval_km', sa.Integer(), nullable=True, server_default='10000'),
            sa.Column('service_interval_months', sa.Integer(), nullable=True, server_default='12'),
            sa.Column('typical_annual_maintenance_inr', sa.String(length=100), nullable=True),
            sa.Column('parts_availability', sa.String(length=50), nullable=False, server_default='EXCELLENT'),
            sa.Column('maintenance_complexity', sa.String(length=30), nullable=False, server_default='LOW'),
            sa.Column('real_world_city_mileage_kmpl', sa.String(length=50), nullable=True),
            sa.Column('real_world_highway_mileage_kmpl', sa.String(length=50), nullable=True),
            sa.Column('ownership_strengths', sa.Text(), nullable=True),
            sa.Column('ownership_concerns', sa.Text(), nullable=True),
            sa.Column('evidence_state', sa.Enum('VERIFIED', 'SUPPORTED', 'EMPIRICAL', 'MODEL_ESTIMATE', 'INSUFFICIENT_DATA', 'UNVERIFIED', 'DEPRECATED', name='evidencestate'), nullable=False),
            sa.Column('source_id', sa.String(length=36), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['generation_id'], ['vehicle_generations.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['source_id'], ['evidence_sources.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_ownership_profiles_canonical_vehicle_id'), 'ownership_profiles', ['canonical_vehicle_id'], unique=False)

    # 7. reliability_issues
    if 'reliability_issues' not in existing_tables:
        op.create_table(
            'reliability_issues',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('canonical_vehicle_id', sa.String(length=255), nullable=False),
            sa.Column('generation_id', sa.String(length=36), nullable=False),
            sa.Column('issue_key', sa.String(length=100), nullable=False),
            sa.Column('category', sa.String(length=50), nullable=False),
            sa.Column('title', sa.String(length=200), nullable=False),
            sa.Column('description', sa.Text(), nullable=False),
            sa.Column('severity', sa.String(length=30), nullable=False, server_default='ADVISORY'),
            sa.Column('affected_years', sa.String(length=100), nullable=True),
            sa.Column('affected_powertrains', sa.String(length=150), nullable=True),
            sa.Column('verification_status', sa.String(length=100), nullable=False, server_default='COMMUNITY_DOCUMENTED'),
            sa.Column('evidence_state', sa.Enum('VERIFIED', 'SUPPORTED', 'EMPIRICAL', 'MODEL_ESTIMATE', 'INSUFFICIENT_DATA', 'UNVERIFIED', 'DEPRECATED', name='evidencestate'), nullable=False),
            sa.Column('source_id', sa.String(length=36), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['generation_id'], ['vehicle_generations.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['source_id'], ['evidence_sources.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_reliability_issues_canonical_vehicle_id'), 'reliability_issues', ['canonical_vehicle_id'], unique=False)
        op.create_index(op.f('ix_reliability_issues_issue_key'), 'reliability_issues', ['issue_key'], unique=False)

    # 8. vehicle_pros_cons
    if 'vehicle_pros_cons' not in existing_tables:
        op.create_table(
            'vehicle_pros_cons',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('canonical_vehicle_id', sa.String(length=255), nullable=False),
            sa.Column('generation_id', sa.String(length=36), nullable=False),
            sa.Column('is_pro', sa.Boolean(), nullable=False),
            sa.Column('statement', sa.String(length=255), nullable=False),
            sa.Column('category', sa.String(length=50), nullable=False, server_default='GENERAL'),
            sa.Column('source_type', sa.String(length=50), nullable=False, server_default='EVIDENCE_BACKED'),
            sa.Column('evidence_state', sa.Enum('VERIFIED', 'SUPPORTED', 'EMPIRICAL', 'MODEL_ESTIMATE', 'INSUFFICIENT_DATA', 'UNVERIFIED', 'DEPRECATED', name='evidencestate'), nullable=False),
            sa.Column('source_id', sa.String(length=36), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['generation_id'], ['vehicle_generations.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['source_id'], ['evidence_sources.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_vehicle_pros_cons_canonical_vehicle_id'), 'vehicle_pros_cons', ['canonical_vehicle_id'], unique=False)

    # 9. review_syntheses
    if 'review_syntheses' not in existing_tables:
        op.create_table(
            'review_syntheses',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('canonical_vehicle_id', sa.String(length=255), nullable=False),
            sa.Column('generation_id', sa.String(length=36), nullable=False),
            sa.Column('what_owners_say', sa.Text(), nullable=True),
            sa.Column('what_experts_say', sa.Text(), nullable=True),
            sa.Column('carspective_analysis', sa.Text(), nullable=False),
            sa.Column('has_owner_evidence', sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column('has_expert_evidence', sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column('evidence_state', sa.Enum('VERIFIED', 'SUPPORTED', 'EMPIRICAL', 'MODEL_ESTIMATE', 'INSUFFICIENT_DATA', 'UNVERIFIED', 'DEPRECATED', name='evidencestate'), nullable=False),
            sa.Column('source_id', sa.String(length=36), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['generation_id'], ['vehicle_generations.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['source_id'], ['evidence_sources.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_review_syntheses_canonical_vehicle_id'), 'review_syntheses', ['canonical_vehicle_id'], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    tables_to_drop = [
        'review_syntheses',
        'vehicle_pros_cons',
        'reliability_issues',
        'ownership_profiles',
        'variant_feature_mappings',
        'vehicle_safety_ratings',
        'vehicle_dimensions',
        'vehicle_specifications',
        'vehicle_features',
    ]

    for tbl in tables_to_drop:
        if tbl in existing_tables:
            op.drop_table(tbl)
