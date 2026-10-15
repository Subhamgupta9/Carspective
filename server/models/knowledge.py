"""
CARspective — Expanded Vehicle Knowledge & Product Intelligence Models
Implements schema expansion for:
- Specifications & Technical Data
- Dimensions & Practicality
- Verified Safety Intelligence
- Variant-Aware Feature Equipment
- Ownership Intelligence & Service Costs
- Reliability & Technical Advisories
- Evidence-Grounded Pros & Cons
- Review Synthesis Architecture
All models maintain strict canonical vehicle identity resolution, scope isolation,
and immutable link to authoritative evidence sources.
"""

import uuid
from typing import Optional, List
from sqlalchemy import String, Integer, Float, Boolean, Text, ForeignKey, Enum as SQLEnum, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin
from .evidence import EvidenceState, EvidenceSource
from .taxonomy import VehicleGeneration, VehicleVariant, PowertrainConfiguration

class VehicleSpecification(Base, TimestampMixin):
    __tablename__ = "vehicle_specifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    canonical_vehicle_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    generation_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("vehicle_generations.id", ondelete="CASCADE"), nullable=True)
    variant_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("vehicle_variants.id", ondelete="CASCADE"), nullable=True)
    powertrain_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("powertrain_configurations.id", ondelete="CASCADE"), nullable=True)

    engine_type: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    displacement_cc: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cylinders: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    valves_per_cylinder: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    aspiration: Mapped[Optional[str]] = mapped_column(String(50), nullable=True) # Naturally Aspirated, Turbocharged
    max_power_bhp: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_power_rpm: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_torque_nm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_torque_rpm: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    transmission: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    drivetrain: Mapped[Optional[str]] = mapped_column(String(20), default="FWD", nullable=True) # FWD, RWD, 4x4, AWD
    fuel_type: Mapped[str] = mapped_column(String(50), nullable=False)
    arai_mileage_kmpl: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fuel_tank_capacity_l: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    emission_norm: Mapped[Optional[str]] = mapped_column(String(30), nullable=True) # BS4, BS6, BS6 Phase 2
    battery_capacity_kwh: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    electric_range_km: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    motor_output_ps: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    evidence_state: Mapped[EvidenceState] = mapped_column(
        SQLEnum(EvidenceState),
        default=EvidenceState.SUPPORTED,
        nullable=False
    )
    source_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("evidence_sources.id", ondelete="SET NULL"), nullable=True)

    source: Mapped[Optional["EvidenceSource"]] = relationship("EvidenceSource")
    generation: Mapped[Optional["VehicleGeneration"]] = relationship("VehicleGeneration")
    variant: Mapped[Optional["VehicleVariant"]] = relationship("VehicleVariant")
    powertrain: Mapped[Optional["PowertrainConfiguration"]] = relationship("PowertrainConfiguration")

class VehicleDimensions(Base, TimestampMixin):
    __tablename__ = "vehicle_dimensions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    canonical_vehicle_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    generation_id: Mapped[str] = mapped_column(String(36), ForeignKey("vehicle_generations.id", ondelete="CASCADE"), nullable=False)

    length_mm: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    width_mm: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height_mm: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    wheelbase_mm: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ground_clearance_mm: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    boot_capacity_l: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    seating_capacity: Mapped[Optional[int]] = mapped_column(Integer, default=5, nullable=True)
    kerb_weight_kg: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    turning_radius_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    evidence_state: Mapped[EvidenceState] = mapped_column(
        SQLEnum(EvidenceState),
        default=EvidenceState.SUPPORTED,
        nullable=False
    )
    source_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("evidence_sources.id", ondelete="SET NULL"), nullable=True)

    source: Mapped[Optional["EvidenceSource"]] = relationship("EvidenceSource")
    generation: Mapped["VehicleGeneration"] = relationship("VehicleGeneration")

class VehicleSafetyRating(Base, TimestampMixin):
    __tablename__ = "vehicle_safety_ratings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    canonical_vehicle_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    generation_id: Mapped[str] = mapped_column(String(36), ForeignKey("vehicle_generations.id", ondelete="CASCADE"), nullable=False)

    organization: Mapped[str] = mapped_column(String(100), nullable=False) # Global NCAP, Bharat NCAP
    test_year: Mapped[int] = mapped_column(Integer, nullable=False)
    adult_stars: Mapped[int] = mapped_column(Integer, nullable=False) # 0 - 5
    adult_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    child_stars: Mapped[Optional[int]] = mapped_column(Integer, nullable=True) # 0 - 5
    child_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bodyshell_integrity: Mapped[Optional[str]] = mapped_column(String(100), nullable=True) # Stable / Unstable
    standard_safety_equipment: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    test_protocol: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)

    evidence_state: Mapped[EvidenceState] = mapped_column(
        SQLEnum(EvidenceState),
        default=EvidenceState.VERIFIED,
        nullable=False
    )
    source_id: Mapped[str] = mapped_column(String(36), ForeignKey("evidence_sources.id", ondelete="CASCADE"), nullable=False)

    source: Mapped["EvidenceSource"] = relationship("EvidenceSource")
    generation: Mapped["VehicleGeneration"] = relationship("VehicleGeneration")

class VehicleFeature(Base, TimestampMixin):
    __tablename__ = "vehicle_features"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    feature_key: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    feature_name: Mapped[str] = mapped_column(String(150), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False) # SAFETY, INFOTAINMENT, COMFORT_CONVENIENCE, LIGHTING_EXTERIOR

class VariantFeatureMapping(Base, TimestampMixin):
    __tablename__ = "variant_feature_mappings"
    __table_args__ = (
        UniqueConstraint("variant_id", "feature_key", name="uq_variant_feature"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    variant_id: Mapped[str] = mapped_column(String(36), ForeignKey("vehicle_variants.id", ondelete="CASCADE"), nullable=False)
    feature_key: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    availability: Mapped[str] = mapped_column(String(30), default="STANDARD", nullable=False) # STANDARD, OPTIONAL, NOT_AVAILABLE, NOT_VERIFIED
    details: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    evidence_state: Mapped[EvidenceState] = mapped_column(
        SQLEnum(EvidenceState),
        default=EvidenceState.SUPPORTED,
        nullable=False
    )
    source_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("evidence_sources.id", ondelete="SET NULL"), nullable=True)

    variant: Mapped["VehicleVariant"] = relationship("VehicleVariant")
    source: Mapped[Optional["EvidenceSource"]] = relationship("EvidenceSource")

class OwnershipProfile(Base, TimestampMixin):
    __tablename__ = "ownership_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    canonical_vehicle_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    generation_id: Mapped[str] = mapped_column(String(36), ForeignKey("vehicle_generations.id", ondelete="CASCADE"), nullable=False)

    service_interval_km: Mapped[Optional[int]] = mapped_column(Integer, default=10000, nullable=True)
    service_interval_months: Mapped[Optional[int]] = mapped_column(Integer, default=12, nullable=True)
    typical_annual_maintenance_inr: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    parts_availability: Mapped[str] = mapped_column(String(50), default="EXCELLENT", nullable=False) # EXCELLENT, GOOD, MODERATE, DIFFICULT
    maintenance_complexity: Mapped[str] = mapped_column(String(30), default="LOW", nullable=False) # LOW, MODERATE, HIGH
    real_world_city_mileage_kmpl: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    real_world_highway_mileage_kmpl: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    ownership_strengths: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # JSON array string
    ownership_concerns: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # JSON array string

    evidence_state: Mapped[EvidenceState] = mapped_column(
        SQLEnum(EvidenceState),
        default=EvidenceState.SUPPORTED,
        nullable=False
    )
    source_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("evidence_sources.id", ondelete="SET NULL"), nullable=True)

    source: Mapped[Optional["EvidenceSource"]] = relationship("EvidenceSource")
    generation: Mapped["VehicleGeneration"] = relationship("VehicleGeneration")

class ReliabilityIssue(Base, TimestampMixin):
    __tablename__ = "reliability_issues"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    canonical_vehicle_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    generation_id: Mapped[str] = mapped_column(String(36), ForeignKey("vehicle_generations.id", ondelete="CASCADE"), nullable=False)

    issue_key: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False) # ENGINE, TRANSMISSION, ELECTRICAL, SUSPENSION, COOLING, HVAC, INFOTAINMENT, BODY_CHASSIS, BRAKES
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(30), default="ADVISORY", nullable=False) # LOW, MODERATE, HIGH, ADVISORY
    affected_years: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    affected_powertrains: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    verification_status: Mapped[str] = mapped_column(String(100), default="COMMUNITY_DOCUMENTED", nullable=False)

    evidence_state: Mapped[EvidenceState] = mapped_column(
        SQLEnum(EvidenceState),
        default=EvidenceState.SUPPORTED,
        nullable=False
    )
    source_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("evidence_sources.id", ondelete="SET NULL"), nullable=True)

    source: Mapped[Optional["EvidenceSource"]] = relationship("EvidenceSource")
    generation: Mapped["VehicleGeneration"] = relationship("VehicleGeneration")

class VehicleProCon(Base, TimestampMixin):
    __tablename__ = "vehicle_pros_cons"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    canonical_vehicle_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    generation_id: Mapped[str] = mapped_column(String(36), ForeignKey("vehicle_generations.id", ondelete="CASCADE"), nullable=False)

    is_pro: Mapped[bool] = mapped_column(Boolean, nullable=False) # True = Pro, False = Con
    statement: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="GENERAL", nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), default="EVIDENCE_BACKED", nullable=False) # EVIDENCE_BACKED, OWNER_REPORTED, CARSPECTIVE_ANALYSIS

    evidence_state: Mapped[EvidenceState] = mapped_column(
        SQLEnum(EvidenceState),
        default=EvidenceState.SUPPORTED,
        nullable=False
    )
    source_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("evidence_sources.id", ondelete="SET NULL"), nullable=True)

    source: Mapped[Optional["EvidenceSource"]] = relationship("EvidenceSource")
    generation: Mapped["VehicleGeneration"] = relationship("VehicleGeneration")

class ReviewSynthesis(Base, TimestampMixin):
    __tablename__ = "review_syntheses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    canonical_vehicle_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    generation_id: Mapped[str] = mapped_column(String(36), ForeignKey("vehicle_generations.id", ondelete="CASCADE"), nullable=False)

    what_owners_say: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    what_experts_say: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    carspective_analysis: Mapped[str] = mapped_column(Text, nullable=False)
    has_owner_evidence: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_expert_evidence: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    evidence_state: Mapped[EvidenceState] = mapped_column(
        SQLEnum(EvidenceState),
        default=EvidenceState.SUPPORTED,
        nullable=False
    )
    source_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("evidence_sources.id", ondelete="SET NULL"), nullable=True)

    source: Mapped[Optional["EvidenceSource"]] = relationship("EvidenceSource")
    generation: Mapped["VehicleGeneration"] = relationship("VehicleGeneration")
