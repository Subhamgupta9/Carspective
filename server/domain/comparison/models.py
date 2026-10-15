"""
CARspective — Phase 6 Comparison Domain Models & Schemas
Defines request contracts, normalized specification categories, category comparison
results, evidence-aware specification values, trade-off structures, personalized
comparison outputs, and the full comparison response payload.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime, timezone


# ────────────────────────────────────────────────────────────────────
# Enums
# ────────────────────────────────────────────────────────────────────

class ComparisonMode(str, Enum):
    GENERAL = "general"
    PERSONALIZED = "personalized"


class CategoryWinnerStatus(str, Enum):
    WINNER = "WINNER"
    TIE = "TIE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class DifferenceSignificance(str, Enum):
    MEANINGFUL = "MEANINGFUL"
    MINOR = "MINOR"
    UNKNOWN = "UNKNOWN"


class OverallResultType(str, Enum):
    CLEAR_WINNER = "CLEAR_WINNER"
    CLOSE_DECISION = "CLOSE_DECISION"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class EvidenceState(str, Enum):
    VERIFIED = "VERIFIED"
    SUPPORTED = "SUPPORTED"
    EMPIRICAL = "EMPIRICAL"
    MODEL_ESTIMATE = "MODEL_ESTIMATE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    UNVERIFIED = "UNVERIFIED"
    DEPRECATED = "DEPRECATED"


# ────────────────────────────────────────────────────────────────────
# Request Models
# ────────────────────────────────────────────────────────────────────

class ComparisonVehicle(BaseModel):
    """Single vehicle entry in a comparison request."""
    brand: str = Field(..., min_length=1, description="Vehicle manufacturer")
    model: str = Field(..., min_length=1, description="Vehicle model name")
    manufacturing_year: Optional[int] = Field(None, ge=1980, le=2026, description="Manufacturing year")
    fuel_type: Optional[str] = Field("Petrol", description="Fuel type")
    transmission_type: Optional[str] = Field("Manual", description="Transmission type")
    city: Optional[str] = Field("Delhi", description="City of registration/sale")
    variant: Optional[str] = Field(None, description="Trim variant if known")
    km_driven: Optional[float] = Field(None, ge=0, description="Odometer reading")
    number_of_owners: Optional[int] = Field(1, ge=1, le=10, description="Owner count")
    canonical_vehicle_id: Optional[str] = Field(None, description="Canonical vehicle identifier if known")

    @field_validator("brand", "model", "fuel_type", "transmission_type", "city", "variant", "canonical_vehicle_id")
    @classmethod
    def strip_whitespace(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v



class ComparisonListing(BaseModel):
    """Optional listing context for a specific vehicle in the comparison."""
    vehicle_index: int = Field(..., ge=0, le=2, description="0-based index referencing the vehicle in the vehicles array")
    asking_price: float = Field(..., gt=0, description="Seller asking price (INR)")
    km_driven: Optional[float] = Field(None, ge=0, description="Odometer reading")
    condition_notes: Optional[str] = Field(None, description="Physical condition notes")
    service_history_status: Optional[str] = Field(None, description="FULL_SERVICE_HISTORY | PARTIAL | UNAVAILABLE | UNKNOWN")
    accident_history_status: Optional[str] = Field(None, description="NO_ACCIDENTS_REPORTED | MINOR_ACCIDENT | MAJOR_ACCIDENT | UNKNOWN")
    insurance_status: Optional[str] = Field(None, description="COMPREHENSIVE | THIRD_PARTY | EXPIRED | UNAVAILABLE")


class ComparisonUserProfile(BaseModel):
    """User-stated requirements for personalized comparison. Tagged USER_STATED."""
    budget_max: Optional[float] = Field(None, ge=50000, le=1000000000, description="Maximum budget (INR)")
    budget_flexible: Optional[bool] = Field(False, description="Budget flexibility")
    monthly_km: Optional[float] = Field(1000.0, ge=0, description="Monthly driving distance in km")
    primary_usage: Optional[str] = Field("CITY", description="CITY | HIGHWAY | MIXED")
    family_size: Optional[int] = Field(4, ge=1, le=10, description="Number of occupants")
    fuel_preference: Optional[str] = Field(None, description="PETROL | DIESEL | CNG | ELECTRIC | ANY")
    transmission_preference: Optional[str] = Field(None, description="MANUAL | AUTOMATIC | ANY")
    safety_priority: Optional[str] = Field("HIGH", description="LOW | MEDIUM | HIGH | CRITICAL")
    mileage_priority: Optional[str] = Field("MEDIUM", description="LOW | MEDIUM | HIGH")
    performance_priority: Optional[str] = Field("MEDIUM", description="LOW | MEDIUM | HIGH")
    maintenance_priority: Optional[str] = Field("HIGH", description="LOW | MEDIUM | HIGH")
    resale_priority: Optional[str] = Field("MEDIUM", description="LOW | MEDIUM | HIGH")
    ownership_horizon_years: Optional[int] = Field(5, ge=1, le=15, description="Intended retention")


class ComparisonRequest(BaseModel):
    """Top-level comparison request. Accepts 2-3 vehicles."""
    vehicles: List[ComparisonVehicle] = Field(..., min_length=2, max_length=3,
        description="2-3 vehicles to compare")
    mode: ComparisonMode = Field(ComparisonMode.GENERAL, description="general | personalized")
    user_profile: Optional[ComparisonUserProfile] = Field(None, description="Required for personalized mode")
    listings: Optional[List[ComparisonListing]] = Field(None, description="Optional listing contexts")

    @model_validator(mode="after")
    def validate_personalized_requires_profile(self):
        if self.mode == ComparisonMode.PERSONALIZED and self.user_profile is None:
            raise ValueError("user_profile is required for personalized comparison mode")
        if self.listings:
            for listing in self.listings:
                if listing.vehicle_index >= len(self.vehicles):
                    raise ValueError(
                        f"listing vehicle_index {listing.vehicle_index} exceeds vehicles array length {len(self.vehicles)}"
                    )
        return self


# ────────────────────────────────────────────────────────────────────
# Specification Models
# ────────────────────────────────────────────────────────────────────

class SpecificationValue(BaseModel):
    """A single specification value with evidence provenance."""
    value: Optional[Any] = Field(None, description="The specification value (string, int, float, or None)")
    display_value: str = Field(..., description="Human-readable formatted value")
    unit: Optional[str] = Field(None, description="Unit (e.g. cc, mm, L, bhp)")
    evidence_state: EvidenceState = Field(EvidenceState.INSUFFICIENT_DATA, description="Evidence provenance")
    source: Optional[str] = Field(None, description="Source citation if available")


class SpecificationComparison(BaseModel):
    """Comparison of a single specification across all vehicles."""
    spec_name: str = Field(..., description="Specification name (e.g. 'Ground Clearance')")
    spec_key: str = Field(..., description="Machine-readable key (e.g. 'ground_clearance_mm')")
    category: str = Field(..., description="Specification category (e.g. 'Dimensions')")
    values: List[SpecificationValue] = Field(..., description="One value per vehicle, in order")
    winner_index: Optional[int] = Field(None, description="Index of the winning vehicle (None if tie or insufficient)")
    significance: DifferenceSignificance = Field(DifferenceSignificance.UNKNOWN, description="Difference significance")
    comparison_note: Optional[str] = Field(None, description="Contextual note about the difference")


# ────────────────────────────────────────────────────────────────────
# Category & Score Comparison Models
# ────────────────────────────────────────────────────────────────────

class CategoryResult(BaseModel):
    """Result of comparing a conceptual category across vehicles."""
    category: str = Field(..., description="Category name (e.g. Safety, Reliability)")
    values: List[Dict[str, Any]] = Field(default_factory=list, description="Per-vehicle summary data")
    winner_index: Optional[int] = Field(None, description="Index of the winner vehicle (None if tie/insufficient)")
    status: CategoryWinnerStatus = Field(..., description="WINNER | TIE | INSUFFICIENT_DATA | NOT_APPLICABLE")
    evidence_quality: str = Field("INSUFFICIENT_DATA", description="Composite evidence quality for this category")
    rationale: str = Field(..., description="Explanation of category outcome")


class VehicleScoreSummary(BaseModel):
    """Score summary for a single vehicle in the comparison."""
    vehicle_index: int = Field(..., description="0-based index in the vehicles array")
    vehicle_summary: str = Field(..., description="Human-readable vehicle name")
    canonical_vehicle_id: Optional[str] = Field(None, description="Canonical ID from taxonomy")
    overall_score: Optional[int] = Field(None, ge=0, le=100, description="CARspective Score (0-100)")
    evidence_quality: str = Field(..., description="HIGH | MODERATE | LIMITED | INSUFFICIENT_DATA")
    dimensions: Dict[str, Optional[int]] = Field(default_factory=dict,
        description="Dimension name -> score (None if INSUFFICIENT_DATA)")


class ScoreComparison(BaseModel):
    """CARspective Score comparison across all vehicles."""
    vehicle_scores: List[VehicleScoreSummary] = Field(..., description="Per-vehicle score summaries")
    overall_winner_index: Optional[int] = Field(None, description="Index of highest-scoring vehicle (None if tie)")
    overall_status: CategoryWinnerStatus = Field(..., description="WINNER | TIE | INSUFFICIENT_DATA")
    dimension_winners: Dict[str, Optional[int]] = Field(default_factory=dict,
        description="Dimension name -> winner index (None if tie/insufficient)")
    rationale: str = Field(..., description="Explanation of score comparison")


# ────────────────────────────────────────────────────────────────────
# Valuation & Deal Comparison Models
# ────────────────────────────────────────────────────────────────────

class VehicleValuationSummary(BaseModel):
    """Valuation summary for a single vehicle."""
    vehicle_index: int
    estimated_fair_market_value: Optional[int] = None
    estimated_fair_market_value_formatted: Optional[str] = None
    expected_fair_range_lower: Optional[int] = None
    expected_fair_range_upper: Optional[int] = None
    confidence_state: str = "INSUFFICIENT_DATA"
    evidence_quality: str = "INSUFFICIENT_DATA"


class ValuationComparison(BaseModel):
    """Phase 3 valuation comparison across vehicles."""
    vehicle_valuations: List[VehicleValuationSummary] = Field(default_factory=list)
    note: str = Field(
        "Valuation differences reflect different vehicle segments and must not be interpreted as direct value rankings.",
        description="Anti-misinterpretation note"
    )


class VehicleDealSummary(BaseModel):
    """Deal analysis summary for a vehicle with listing data."""
    vehicle_index: int
    asking_price: int
    asking_price_formatted: str
    deal_quality: str
    price_deviation_percent: float
    range_position: str
    evidence_state: str = "MODEL_ESTIMATE"


class DealComparison(BaseModel):
    """Phase 4 deal comparison for vehicles that have listing data."""
    vehicle_deals: List[VehicleDealSummary] = Field(default_factory=list)
    stronger_deal_index: Optional[int] = Field(None, description="Index of vehicle with stronger deal (None if not comparable)")
    rationale: Optional[str] = Field(None, description="Explanation")
    note: str = Field(
        "Deal quality reflects asking price positioning relative to empirical fair market range. A stronger deal does not imply a better vehicle.",
        description="Anti-conflation note"
    )


# ────────────────────────────────────────────────────────────────────
# User Fit & Personalized Models
# ────────────────────────────────────────────────────────────────────

class VehicleUserFitSummary(BaseModel):
    """User fit summary for one vehicle."""
    vehicle_index: int
    overall_fit: int = Field(..., ge=0, le=100)
    budget_fit: int = Field(..., ge=0, le=100)
    usage_fit: int = Field(..., ge=0, le=100)
    family_fit: int = Field(..., ge=0, le=100)
    powertrain_fit: int = Field(..., ge=0, le=100)
    priority_alignment: int = Field(..., ge=0, le=100)
    fit_summary: str
    evidence_state: str = "USER_STATED"


class UserFitComparison(BaseModel):
    """User fit comparison across vehicles (personalized mode only)."""
    vehicle_fits: List[VehicleUserFitSummary] = Field(default_factory=list)
    best_fit_index: Optional[int] = Field(None, description="Index of best-fit vehicle")
    status: CategoryWinnerStatus = Field(CategoryWinnerStatus.NOT_APPLICABLE)
    rationale: Optional[str] = None


# ────────────────────────────────────────────────────────────────────
# Trade-off, Best-For, and Research Summary Models
# ────────────────────────────────────────────────────────────────────

class TradeOff(BaseModel):
    """A single identified trade-off between vehicles."""
    dimension: str = Field(..., description="Area of trade-off (e.g. Safety vs Performance)")
    advantage_vehicle_index: int = Field(..., description="Index of vehicle with advantage")
    disadvantage_vehicle_index: int = Field(..., description="Index of vehicle with disadvantage")
    description: str = Field(..., description="Evidence-grounded trade-off description")
    evidence_quality: str = Field("EMPIRICAL", description="Evidence quality for this trade-off")


class BestForLabel(BaseModel):
    """A contextual 'best for' label assigned to a vehicle."""
    label: str = Field(..., description="e.g. 'Best for city driving'")
    vehicle_index: int = Field(..., description="Index of the vehicle this label applies to")
    rationale: str = Field(..., description="Evidence-based reason")
    evidence_quality: str = Field("SUPPORTED", description="Evidence quality")


class VehicleResearchSummary(BaseModel):
    """Structured research summary for a single vehicle."""
    vehicle_index: int
    vehicle_summary: str
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    unknowns: List[str] = Field(default_factory=list)
    ownership_notes: List[str] = Field(default_factory=list)
    market_position: Optional[str] = None


# ────────────────────────────────────────────────────────────────────
# Overall Result
# ────────────────────────────────────────────────────────────────────

class OverallResult(BaseModel):
    """The overall comparison conclusion."""
    result_type: OverallResultType = Field(..., description="CLEAR_WINNER | CLOSE_DECISION | INSUFFICIENT_DATA")
    winner_index: Optional[int] = Field(None, description="Index of winning vehicle (None if close/insufficient)")
    winner_vehicle_summary: Optional[str] = Field(None, description="Name of the winning vehicle")
    confidence: str = Field(..., description="HIGH | MODERATE | LIMITED")
    rationale: str = Field(..., description="Evidence-grounded explanation for the overall outcome")
    major_tradeoff: Optional[str] = Field(None, description="Key trade-off considered in the decision")


# ────────────────────────────────────────────────────────────────────
# Full Comparison Response
# ────────────────────────────────────────────────────────────────────

class ComparisonResponse(BaseModel):
    """Complete comparison response payload."""
    comparison_id: str = Field(..., description="Unique comparison identifier")
    mode: ComparisonMode = Field(..., description="general | personalized")
    vehicles: List[Dict[str, Any]] = Field(..., description="Resolved vehicle summaries")
    specifications: List[SpecificationComparison] = Field(default_factory=list,
        description="Normalized specification comparisons")
    category_winners: List[CategoryResult] = Field(default_factory=list,
        description="Category-level comparison results")
    score_comparison: ScoreComparison = Field(..., description="CARspective Score comparison")
    valuation_comparison: ValuationComparison = Field(..., description="Phase 3 valuation comparison")
    deal_comparison: Optional[DealComparison] = Field(None, description="Phase 4 deal comparison (if listings provided)")
    user_fit_comparison: Optional[UserFitComparison] = Field(None, description="User fit comparison (personalized mode)")
    tradeoffs: List[TradeOff] = Field(default_factory=list, description="Identified trade-offs")
    best_for: List[BestForLabel] = Field(default_factory=list, description="Evidence-grounded best-for labels")
    overall_result: OverallResult = Field(..., description="Overall comparison conclusion")
    research_summaries: List[VehicleResearchSummary] = Field(default_factory=list,
        description="Per-vehicle research summaries")
    limitations: List[str] = Field(default_factory=list, description="Explicit disclosures and scope boundaries")
    computation_latency_ms: Optional[float] = Field(None, description="Total comparison latency in ms")
    comparison_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
