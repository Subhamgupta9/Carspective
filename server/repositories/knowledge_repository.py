"""
CARspective — Vehicle Knowledge Repository
Encapsulates database queries and transactions for all Phase 11 expanded knowledge models:
specifications, dimensions, safety ratings, features, ownership, reliability, pros/cons, and reviews.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
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
from server.models.evidence import EvidenceSource

class KnowledgeRepository:
    def __init__(self, session: Optional[Session] = None):
        self._session = session

    @property
    def session(self) -> Session:
        if self._session is not None:
            return self._session
        from server.infrastructure.database import ScopedSession
        return ScopedSession()

    @session.setter
    def session(self, value: Optional[Session]) -> None:
        self._session = value

    def _get_hierarchy_prefixes(self, canonical_vehicle_id: str) -> List[str]:
        """Returns hierarchy prefixes [make, make::model, make::model::gen, ...]"""
        parts = canonical_vehicle_id.split("::")
        return ["::".join(parts[:i]) for i in range(1, len(parts) + 1)]

    def get_specifications_for_vehicle(self, canonical_vehicle_id: str) -> List[VehicleSpecification]:
        prefixes = self._get_hierarchy_prefixes(canonical_vehicle_id)
        stmt = (
            select(VehicleSpecification)
            .options(
                joinedload(VehicleSpecification.source),
                joinedload(VehicleSpecification.generation),
                joinedload(VehicleSpecification.variant),
                joinedload(VehicleSpecification.powertrain)
            )
            .where(VehicleSpecification.canonical_vehicle_id.in_(prefixes))
        )
        return list(self.session.scalars(stmt).unique().all())

    def get_dimensions_for_vehicle(self, canonical_vehicle_id: str) -> Optional[VehicleDimensions]:
        prefixes = self._get_hierarchy_prefixes(canonical_vehicle_id)
        stmt = (
            select(VehicleDimensions)
            .options(joinedload(VehicleDimensions.source))
            .where(VehicleDimensions.canonical_vehicle_id.in_(prefixes))
        )
        return self.session.scalars(stmt).first()

    def get_safety_rating_for_vehicle(self, canonical_vehicle_id: str) -> Optional[VehicleSafetyRating]:
        prefixes = self._get_hierarchy_prefixes(canonical_vehicle_id)
        # Match only exact generation or specific vehicle, never inherit across generation boundaries
        stmt = (
            select(VehicleSafetyRating)
            .options(joinedload(VehicleSafetyRating.source))
            .where(VehicleSafetyRating.canonical_vehicle_id.in_(prefixes))
        )
        return self.session.scalars(stmt).first()

    def get_features_for_variant(self, variant_id: str) -> List[VariantFeatureMapping]:
        stmt = (
            select(VariantFeatureMapping)
            .options(joinedload(VariantFeatureMapping.source))
            .where(VariantFeatureMapping.variant_id == variant_id)
            .order_by(VariantFeatureMapping.feature_key)
        )
        return list(self.session.scalars(stmt).all())

    def get_features_for_generation(self, generation_id: str) -> List[VariantFeatureMapping]:
        from server.models.taxonomy import VehicleVariant
        stmt = (
            select(VariantFeatureMapping)
            .options(joinedload(VariantFeatureMapping.source), joinedload(VariantFeatureMapping.variant))
            .join(VehicleVariant, VariantFeatureMapping.variant_id == VehicleVariant.id)
            .where(VehicleVariant.generation_id == generation_id)
            .order_by(VariantFeatureMapping.feature_key)
        )
        return list(self.session.scalars(stmt).all())


    def get_ownership_profile_for_vehicle(self, canonical_vehicle_id: str) -> Optional[OwnershipProfile]:
        prefixes = self._get_hierarchy_prefixes(canonical_vehicle_id)
        stmt = (
            select(OwnershipProfile)
            .options(joinedload(OwnershipProfile.source))
            .where(OwnershipProfile.canonical_vehicle_id.in_(prefixes))
        )
        return self.session.scalars(stmt).first()

    def get_reliability_issues_for_vehicle(self, canonical_vehicle_id: str) -> List[ReliabilityIssue]:
        prefixes = self._get_hierarchy_prefixes(canonical_vehicle_id)
        stmt = (
            select(ReliabilityIssue)
            .options(joinedload(ReliabilityIssue.source))
            .where(ReliabilityIssue.canonical_vehicle_id.in_(prefixes))
            .order_by(ReliabilityIssue.severity.desc())
        )
        return list(self.session.scalars(stmt).all())

    def get_pros_cons_for_vehicle(self, canonical_vehicle_id: str) -> List[VehicleProCon]:
        prefixes = self._get_hierarchy_prefixes(canonical_vehicle_id)
        stmt = (
            select(VehicleProCon)
            .options(joinedload(VehicleProCon.source))
            .where(VehicleProCon.canonical_vehicle_id.in_(prefixes))
        )
        return list(self.session.scalars(stmt).all())

    def get_review_synthesis_for_vehicle(self, canonical_vehicle_id: str) -> Optional[ReviewSynthesis]:
        prefixes = self._get_hierarchy_prefixes(canonical_vehicle_id)
        stmt = (
            select(ReviewSynthesis)
            .options(joinedload(ReviewSynthesis.source))
            .where(ReviewSynthesis.canonical_vehicle_id.in_(prefixes))
        )
        return self.session.scalars(stmt).first()
