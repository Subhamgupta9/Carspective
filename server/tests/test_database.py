"""
CARspective — Database Integrity Tests
Asserts foreign key enforcement, uniqueness constraints, relationships, and cascade deletions.
"""

import pytest
from sqlalchemy.exc import IntegrityError
from server.models.taxonomy import (
    Manufacturer,
    VehicleModel,
    VehicleGeneration,
    VehicleVariant,
    PowertrainConfiguration,
    ModelYear,
)
from server.models.evidence import (
    EvidenceSource,
    KnowledgeClaim,
    EvidenceState,
    OrganizationType,
    HierarchyLevel,
)

def test_foreign_key_enforcement_on_model(db_session):
    """Attempting to create a VehicleModel with invalid manufacturer_id must fail."""
    orphan_model = VehicleModel(
        manufacturer_id="non-existent-manufacturer-uuid",
        name="Ghost Model",
        slug="ghost-model",
        body_type="Sedan",
        coverage_tier="TIER_3_UNSUPPORTED",
        is_active=True
    )
    db_session.add(orphan_model)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()

def test_manufacturer_slug_uniqueness(db_session):
    """Duplicate manufacturer slugs must trigger unique constraint violation."""
    dup_make = Manufacturer(
        name="Hyundai Motors Duplicate",
        slug="hyundai",  # Already exists in seed
        country_of_origin="South Korea"
    )
    db_session.add(dup_make)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()

def test_model_slug_uniqueness_within_same_manufacturer(db_session):
    """Duplicate model slugs under the same manufacturer must violate unique constraint."""
    hyundai = db_session.query(Manufacturer).filter_by(slug="hyundai").first()
    assert hyundai is not None
    
    dup_model = VehicleModel(
        manufacturer_id=hyundai.id,
        name="Creta Clone",
        slug="creta",  # Already exists for Hyundai
        body_type="SUV",
        coverage_tier="TIER_1_DEEP"
    )
    db_session.add(dup_model)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()

def test_relationship_navigation_across_all_6_tiers(db_session):
    """Navigate from Manufacturer all the way down to PowertrainConfiguration."""
    creta = db_session.query(VehicleModel).filter_by(slug="creta").first()
    assert creta is not None
    assert creta.manufacturer.name == "Hyundai"
    
    # Check generations
    assert len(creta.generations) >= 2
    gen2 = next(g for g in creta.generations if g.slug == "gen-2-2020")
    assert gen2.year_start == 2020
    assert 2021 in [my.calendar_year for my in gen2.model_years]
    
    # Check variants
    sx_opt = next(v for v in gen2.variants if v.slug == "sx-opt")
    assert sx_opt.trim_level == "Top"
    
    # Check powertrains
    pt_diesel_at = next(p for p in sx_opt.powertrains if p.fuel_type == "Diesel")
    assert pt_diesel_at.transmission_type == "Automatic"
    assert pt_diesel_at.power_bhp == 113.4

def test_cascade_deletion_behavior(db_session):
    """Deleting a model must cascade delete its generations, variants, and powertrains."""
    thar = db_session.query(VehicleModel).filter_by(slug="thar").first()
    assert thar is not None
    thar_id = thar.id
    
    # Ensure child generations exist
    gen_count_before = db_session.query(VehicleGeneration).filter_by(model_id=thar_id).count()
    assert gen_count_before >= 1
    
    # Delete model
    db_session.delete(thar)
    db_session.flush()
    
    # Child generations must be gone
    gen_count_after = db_session.query(VehicleGeneration).filter_by(model_id=thar_id).count()
    assert gen_count_after == 0
    db_session.rollback()
