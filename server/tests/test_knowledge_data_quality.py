"""
CARspective — Phase 11: Vehicle Knowledge Data Quality Test Suite
Validates schema constraints, referential integrity, duplicate prevention,
generation boundary isolation, and evidence staleness detection.
"""

import pytest
from datetime import date, timedelta
from sqlalchemy import select, func
from server.models.knowledge import (
    VehicleSpecification,
    VehicleDimensions,
    VehicleSafetyRating,
    VehicleFeature,
    VariantFeatureMapping,
    OwnershipProfile,
    ReliabilityIssue,
    VehicleProCon,
    ReviewSynthesis,
)
from server.models.evidence import EvidenceSource, EvidenceState, OrganizationType

from server.domain.knowledge.service import KnowledgeService
from server.domain.knowledge.ingestion import KnowledgeIngestionPipeline


class TestKnowledgeDataQuality:

    def test_unique_canonical_ids_in_specifications(self, db_session):
        """Ensure no duplicate canonical_vehicle_id entries in specifications."""
        stmt = (
            select(VehicleSpecification.canonical_vehicle_id, func.count(VehicleSpecification.id))
            .group_by(VehicleSpecification.canonical_vehicle_id)
            .having(func.count(VehicleSpecification.id) > 1)
        )
        duplicates = db_session.execute(stmt).all()
        assert len(duplicates) == 0, f"Found duplicate specifications: {duplicates}"

    def test_unique_canonical_ids_in_dimensions(self, db_session):
        """Ensure no duplicate canonical_vehicle_id entries in dimensions."""
        stmt = (
            select(VehicleDimensions.canonical_vehicle_id, func.count(VehicleDimensions.id))
            .group_by(VehicleDimensions.canonical_vehicle_id)
            .having(func.count(VehicleDimensions.id) > 1)
        )
        duplicates = db_session.execute(stmt).all()
        assert len(duplicates) == 0, f"Found duplicate dimensions: {duplicates}"

    def test_unique_canonical_ids_in_safety_ratings(self, db_session):
        """Ensure no duplicate canonical_vehicle_id entries in safety ratings."""
        stmt = (
            select(VehicleSafetyRating.canonical_vehicle_id, func.count(VehicleSafetyRating.id))
            .group_by(VehicleSafetyRating.canonical_vehicle_id)
            .having(func.count(VehicleSafetyRating.id) > 1)
        )
        duplicates = db_session.execute(stmt).all()
        assert len(duplicates) == 0, f"Found duplicate safety ratings: {duplicates}"

    def test_unique_variant_feature_mappings(self, db_session):
        """Ensure no duplicate (variant_id, feature_key) pairs exist."""
        stmt = (
            select(
                VariantFeatureMapping.variant_id,
                VariantFeatureMapping.feature_key,
                func.count(VariantFeatureMapping.id),
            )
            .group_by(VariantFeatureMapping.variant_id, VariantFeatureMapping.feature_key)
            .having(func.count(VariantFeatureMapping.id) > 1)
        )
        duplicates = db_session.execute(stmt).all()
        assert len(duplicates) == 0, f"Found duplicate variant feature mappings: {duplicates}"

    def test_generation_safety_isolation(self, db_session):
        """Ensure safety ratings are attached strictly to their tested generation."""
        service = KnowledgeService(db_session)
        # Swift Gen 3 has verified crash test
        gen3_prof = service.get_vehicle_profile("maruti-suzuki::swift::gen-3-2018")
        assert gen3_prof is not None
        assert gen3_prof.safety is not None
        assert gen3_prof.safety.adult_stars == 2

        # Swift Gen 2 must NOT inherit Gen 3 crash test rating
        gen2_prof = service.get_vehicle_profile("maruti-suzuki::swift::gen-2-2011")
        assert gen2_prof is not None
        assert gen2_prof.safety is None

    def test_feature_leakage_prevention_across_generations(self, db_session):
        """Ensure variants in Gen 2 do not inherit Gen 3 equipment mappings."""
        service = KnowledgeService(db_session)
        # Gen 3 VXi has seeded features
        gen3_vxi = service.get_vehicle_profile("maruti-suzuki::swift::gen-3-2018::2020::vxi")
        assert gen3_vxi is not None
        gen3_keys = [f.feature_key for f in gen3_vxi.features]

        # Gen 2 VXi has no seeded Phase 11 features
        gen2_vxi = service.get_vehicle_profile("maruti-suzuki::swift::gen-2-2011::2015::vxi")
        assert gen2_vxi is not None
        gen2_keys = [f.feature_key for f in gen2_vxi.features]

        assert len(gen2_keys) == 0
        assert len(gen3_keys) > 0

    def test_stale_evidence_detection(self, db_session):
        """Verify that stale evidence dates are correctly flagged by KnowledgeService."""
        service = KnowledgeService(db_session)

        # 1. Active source
        active_source = EvidenceSource(
            organization_name="Automotive Test Agency",
            organization_type=OrganizationType.SAFETY_AGENCY,
            reference_document="Doc Active 2026",
            published_at=date.today() - timedelta(days=100),
            valid_until=date.today() + timedelta(days=365),
            confidence_score=0.95,
            verification_status=EvidenceState.VERIFIED,
            payload_hash="active_hash_123",
        )
        db_session.add(active_source)
        db_session.flush()

        active_meta = service._format_source(active_source)
        assert active_meta.is_stale is False

        # 2. Expired validity source
        expired_source = EvidenceSource(
            organization_name="Automotive Test Agency",
            organization_type=OrganizationType.SAFETY_AGENCY,
            reference_document="Doc Expired 2020",
            published_at=date(2020, 1, 1),
            valid_until=date(2022, 1, 1),
            confidence_score=0.90,
            verification_status=EvidenceState.VERIFIED,
            payload_hash="expired_hash_123",
        )
        db_session.add(expired_source)
        db_session.flush()

        expired_meta = service._format_source(expired_source)
        assert expired_meta.is_stale is True

    def test_idempotent_ingestion_pipeline(self, db_session):
        """Ensure repeated execution of KnowledgeIngestionPipeline does not fail or duplicate."""
        pipeline = KnowledgeIngestionPipeline(db_session)
        source = EvidenceSource(
            organization_name="Test OEM",
            organization_type=OrganizationType.OEM_MANUFACTURER,
            reference_document="Test Manual 2024",
            confidence_score=1.0,
            verification_status=EvidenceState.VERIFIED,
            payload_hash="idempotent_hash_123",
        )
        db_session.add(source)
        db_session.flush()



        # Ingest twice
        spec_payload = {
            "canonical_vehicle_id": "maruti-suzuki::swift::gen-3-2018",
            "generation_slug": "gen-3-2018",
            "engine_type": "DualJet 1.2L",
            "displacement_cc": 1197,
            "evidence_state": "VERIFIED",
        }
        spec1 = pipeline.ingest_specification(spec_payload, source_id=source.id)
        assert spec1 is not None

        spec2 = pipeline.ingest_specification(spec_payload, source_id=source.id)
        assert spec2 is not None
        assert spec1.id == spec2.id  # Same record updated idempotently
