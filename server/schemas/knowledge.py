"""
CARspective — Vehicle Knowledge Schemas
Pydantic v2 schemas for expanded vehicle knowledge, specifications, safety,
dimensions, features, ownership, reliability, pros/cons, reviews, and freshness metadata.
"""

from typing import Optional, List, Dict, Any
from datetime import date, datetime
from pydantic import BaseModel, Field

class SourceMetadataSchema(BaseModel):
    source_id: Optional[str] = None
    organization_name: str
    organization_type: Optional[str] = None
    source_url: Optional[str] = None
    reference_document: Optional[str] = None
    published_at: Optional[str] = None
    retrieved_at: Optional[str] = None
    valid_until: Optional[str] = None
    review_due: Optional[str] = None
    is_stale: bool = False
    confidence_score: float = 1.0
    verification_status: str = "VERIFIED"

class VehicleSpecificationSchema(BaseModel):
    engine_type: Optional[str] = None
    displacement_cc: Optional[int] = None
    cylinders: Optional[int] = None
    valves_per_cylinder: Optional[int] = None
    aspiration: Optional[str] = None
    max_power_bhp: Optional[float] = None
    max_power_rpm: Optional[int] = None
    max_torque_nm: Optional[float] = None
    max_torque_rpm: Optional[str] = None
    transmission: Optional[str] = None
    drivetrain: Optional[str] = "FWD"
    fuel_type: str
    arai_mileage_kmpl: Optional[float] = None
    fuel_tank_capacity_l: Optional[float] = None
    emission_norm: Optional[str] = None
    battery_capacity_kwh: Optional[float] = None
    electric_range_km: Optional[float] = None
    motor_output_ps: Optional[float] = None
    evidence_state: str = "SUPPORTED"
    source: Optional[SourceMetadataSchema] = None

class VehicleDimensionsSchema(BaseModel):
    length_mm: Optional[int] = None
    width_mm: Optional[int] = None
    height_mm: Optional[int] = None
    wheelbase_mm: Optional[int] = None
    ground_clearance_mm: Optional[int] = None
    boot_capacity_l: Optional[int] = None
    seating_capacity: Optional[int] = 5
    kerb_weight_kg: Optional[int] = None
    turning_radius_m: Optional[float] = None
    evidence_state: str = "SUPPORTED"
    source: Optional[SourceMetadataSchema] = None

class VehicleSafetyRatingSchema(BaseModel):
    organization: str
    test_year: int
    adult_stars: int
    adult_score: Optional[float] = None
    child_stars: Optional[int] = None
    child_score: Optional[float] = None
    bodyshell_integrity: Optional[str] = None
    standard_safety_equipment: Optional[str] = None
    test_protocol: Optional[str] = None
    evidence_state: str = "VERIFIED"
    source: Optional[SourceMetadataSchema] = None

class VariantFeatureSchema(BaseModel):
    feature_key: str
    feature_name: str
    category: str
    availability: str # STANDARD, OPTIONAL, NOT_AVAILABLE, NOT_VERIFIED
    details: Optional[str] = None
    variant_name: Optional[str] = None
    evidence_state: str = "SUPPORTED"
    source: Optional[SourceMetadataSchema] = None


class OwnershipProfileSchema(BaseModel):
    service_interval_km: Optional[int] = 10000
    service_interval_months: Optional[int] = 12
    typical_annual_maintenance_inr: Optional[str] = None
    parts_availability: str = "EXCELLENT"
    maintenance_complexity: str = "LOW"
    real_world_city_mileage_kmpl: Optional[str] = None
    real_world_highway_mileage_kmpl: Optional[str] = None
    ownership_strengths: List[str] = []
    ownership_concerns: List[str] = []
    evidence_state: str = "SUPPORTED"
    source: Optional[SourceMetadataSchema] = None

class ReliabilityIssueSchema(BaseModel):
    issue_key: str
    category: str
    title: str
    description: str
    severity: str # LOW, MODERATE, HIGH, ADVISORY
    affected_years: Optional[str] = None
    affected_powertrains: Optional[str] = None
    verification_status: str = "COMMUNITY_DOCUMENTED"
    evidence_state: str = "SUPPORTED"
    source: Optional[SourceMetadataSchema] = None

class VehicleProConSchema(BaseModel):
    is_pro: bool
    statement: str
    category: str = "GENERAL"
    source_type: str = "EVIDENCE_BACKED"
    evidence_state: str = "SUPPORTED"
    source: Optional[SourceMetadataSchema] = None

class ReviewSynthesisSchema(BaseModel):
    what_owners_say: Optional[str] = None
    what_experts_say: Optional[str] = None
    carspective_analysis: str
    has_owner_evidence: bool = False
    has_expert_evidence: bool = False
    evidence_state: str = "SUPPORTED"
    source: Optional[SourceMetadataSchema] = None

class VehicleKnowledgeProfileSchema(BaseModel):
    canonical_vehicle_id: str
    make: str
    model: str
    generation_name: Optional[str] = None
    year: Optional[int] = None
    variant_name: Optional[str] = None
    body_type: Optional[str] = None
    segment: Optional[str] = None
    coverage_tier: str = "TIER_1_DEEP"

    specifications: Optional[VehicleSpecificationSchema] = None
    dimensions: Optional[VehicleDimensionsSchema] = None
    safety: Optional[VehicleSafetyRatingSchema] = None
    features: List[VariantFeatureSchema] = []
    ownership: Optional[OwnershipProfileSchema] = None
    reliability_issues: List[ReliabilityIssueSchema] = []
    pros: List[VehicleProConSchema] = []
    cons: List[VehicleProConSchema] = []
    reviews: Optional[ReviewSynthesisSchema] = None

    freshness_summary: Dict[str, Any] = Field(default_factory=dict)
