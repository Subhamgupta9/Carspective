"""
CARspective — Recommendation Domain Models & Schemas
Defines user preferences (USER_STATED), listing contexts, user-fit scoring,
market alternative models, and the locked four-tier recommendation verdict contract.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timezone

class RecommendationVerdict(str, Enum):
    STRONG_CONSIDERATION = "STRONG CONSIDERATION"
    CONSIDER = "CONSIDER"
    PROCEED_WITH_CAUTION = "PROCEED WITH CAUTION"
    NOT_RECOMMENDED = "NOT RECOMMENDED"

class UserProfile(BaseModel):
    """User-stated preferences and constraints. Marked explicitly as USER_STATED."""
    budget_max: Optional[float] = Field(None, ge=50000, le=1000000000, description="Maximum total acquisition budget (INR)")
    budget_flexible: Optional[bool] = Field(False, description="Whether user budget can stretch if high value exists")
    monthly_km: Optional[float] = Field(1000.0, ge=0, description="Estimated monthly driving distance in km")
    primary_usage: Optional[str] = Field("CITY", description="CITY | HIGHWAY | MIXED")
    family_size: Optional[int] = Field(4, ge=1, le=10, description="Number of primary occupants")
    fuel_preference: Optional[str] = Field(None, description="PETROL | DIESEL | CNG | ELECTRIC | ANY")
    transmission_preference: Optional[str] = Field(None, description="MANUAL | AUTOMATIC | ANY")
    safety_priority: Optional[str] = Field("HIGH", description="LOW | MEDIUM | HIGH | CRITICAL")
    mileage_priority: Optional[str] = Field("MEDIUM", description="LOW | MEDIUM | HIGH")
    performance_priority: Optional[str] = Field("MEDIUM", description="LOW | MEDIUM | HIGH")
    maintenance_priority: Optional[str] = Field("HIGH", description="LOW | MEDIUM | HIGH")
    resale_priority: Optional[str] = Field("MEDIUM", description="LOW | MEDIUM | HIGH")
    ownership_horizon_years: Optional[int] = Field(5, ge=1, le=15, description="Intended retention period in years")

class ListingContext(BaseModel):
    """Optional listing details evaluated against Deal Analyzer."""
    asking_price: Optional[float] = Field(None, gt=0, description="Seller asking price (INR)")
    km_driven: Optional[float] = Field(None, ge=0, description="Odometer reading")
    condition_notes: Optional[str] = Field(None, description="Physical condition notes")
    service_history_status: Optional[str] = Field(None, description="FULL_SERVICE_HISTORY | PARTIAL | UNAVAILABLE | UNKNOWN")
    accident_history_status: Optional[str] = Field(None, description="NO_ACCIDENTS_REPORTED | MINOR_ACCIDENT | MAJOR_ACCIDENT | UNKNOWN")
    insurance_status: Optional[str] = Field(None, description="COMPREHENSIVE | THIRD_PARTY | EXPIRED | UNAVAILABLE")
    tyre_condition: Optional[str] = Field(None, description="GOOD | WORN | REPLACED_RECENTLY | UNKNOWN")

class RecommendationRequest(BaseModel):
    brand: str = Field(..., min_length=1, description="Vehicle manufacturer")
    model: str = Field(..., min_length=1, description="Vehicle model")
    manufacturing_year: Optional[int] = Field(2019, ge=1980, le=2026, description="Manufacturing year")
    fuel_type: Optional[str] = Field("Petrol", description="Fuel type")
    transmission_type: Optional[str] = Field("Manual", description="Transmission type")
    city: Optional[str] = Field("Delhi", description="City of registration / purchase")
    variant: Optional[str] = Field(None, description="Trim variant if known")
    
    listing: Optional[ListingContext] = Field(default_factory=ListingContext, description="Optional listing information")
    user_profile: Optional[UserProfile] = Field(default_factory=UserProfile, description="User-stated preferences")

    @field_validator("brand", "model", "fuel_type", "transmission_type", "city", "variant")
    @classmethod
    def strip_whitespace(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v

class UserFitScore(BaseModel):
    overall_fit: int = Field(..., ge=0, le=100, description="Composite fit score 0-100")
    budget_fit: int = Field(..., ge=0, le=100, description="Budget alignment")
    usage_fit: int = Field(..., ge=0, le=100, description="City/highway usage fit")
    family_fit: int = Field(..., ge=0, le=100, description="Passenger and cargo accommodation")
    powertrain_fit: int = Field(..., ge=0, le=100, description="Fuel and transmission compatibility")
    priority_alignment: int = Field(..., ge=0, le=100, description="Alignment with safety/resale/maintenance priorities")
    fit_summary: str = Field(..., description="Summary of user fit evaluation")
    evidence_state: str = Field("USER_STATED", description="Provenance marker for user preference calculations")

class MarketAlternative(BaseModel):
    brand: str = Field(..., description="Alternative brand")
    model: str = Field(..., description="Alternative model")
    manufacturing_year: int = Field(..., description="Representative year")
    typical_price_inr: int = Field(..., description="Representative market price")
    typical_price_formatted: str = Field(..., description="Formatted price in INR")
    carspective_score: int = Field(..., description="Intrinsic CARspective Score")
    rationale: str = Field(..., description="Concrete reason for recommendation")
    advantage_over_target: str = Field(..., description="Key comparative advantage")

class RecommendationExplanation(BaseModel):
    strongest_positive_factor: str = Field(..., description="Primary strength supporting recommendation")
    biggest_tradeoff: str = Field(..., description="Primary compromise or watchpoint")
    deal_consideration: str = Field(..., description="Impact of current asking price / deal quality")
    user_fit_consideration: str = Field(..., description="Alignment with stated buyer priorities")
    evidence_limitation: Optional[str] = Field(None, description="Data or verification gaps if applicable")
    detailed_rationale: str = Field(..., description="Complete plain-language decision support narrative")

class RecommendationResponse(BaseModel):
    canonical_vehicle_id: Optional[str] = Field(None, description="Canonical vehicle ID from taxonomy")
    vehicle_summary: str = Field(..., description="Evaluated vehicle summary")
    verdict: RecommendationVerdict = Field(..., description="STRONG CONSIDERATION | CONSIDER | PROCEED WITH CAUTION | NOT RECOMMENDED")
    verdict_label: str = Field(..., description="User-facing verdict string")
    carspective_score: Optional[int] = Field(None, description="Intrinsic vehicle proposition (0-100)")
    carspective_score_quality: str = Field(..., description="HIGH | MODERATE | LIMITED | INSUFFICIENT_DATA")
    deal_quality: Optional[str] = Field(None, description="Commercial asking price quality from Phase 4")
    user_fit: UserFitScore = Field(..., description="Detailed user-fit scoring breakdown")
    risk_summary: Dict[str, Any] = Field(default_factory=dict, description="Identified risk counts and highest severity")
    explanation: RecommendationExplanation = Field(..., description="Structured deterministic explanation")
    alternatives: List[MarketAlternative] = Field(default_factory=list, description="Ground-truthed market alternatives")
    limitations: List[str] = Field(default_factory=list, description="Explicit decision support boundaries")
    analysis_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
