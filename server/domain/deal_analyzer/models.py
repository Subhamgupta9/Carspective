"""
CARspective — Deal Analyzer Domain Models & Schemas
Defines request contracts, deal quality classifications, negotiation guidance,
risk signal models, price deviation metrics, and full deal analysis response payloads.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timezone

CURRENT_YEAR = 2026

class DealQualityEnum(str, Enum):
    GREAT_DEAL = "GREAT_DEAL"
    FAIR_DEAL = "FAIR_DEAL"
    OVERPRICED = "OVERPRICED"
    UNUSUALLY_LOW_ASKING_PRICE = "UNUSUALLY_LOW_ASKING_PRICE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"

class RangePositionCategory(str, Enum):
    BELOW_RANGE = "BELOW_RANGE"
    INSIDE_RANGE = "INSIDE_RANGE"
    ABOVE_RANGE = "ABOVE_RANGE"
    UNAVAILABLE = "UNAVAILABLE"

class NegotiationStrength(str, Enum):
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    LIMITED = "LIMITED"

class RiskCategory(str, Enum):
    PRICE_RISK = "PRICE_RISK"
    DOCUMENTATION_RISK = "DOCUMENTATION_RISK"
    CONDITION_RISK = "CONDITION_RISK"
    DATA_RISK = "DATA_RISK"

class RiskSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class EvidenceState(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    EMPIRICAL = "EMPIRICAL"
    MODEL_ESTIMATE = "MODEL_ESTIMATE"
    VERIFIED = "VERIFIED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    DISPUTED = "DISPUTED"
    HISTORICAL = "HISTORICAL"

class DealAnalysisRequest(BaseModel):
    # Required parameters
    brand: str = Field(..., min_length=1, description="Vehicle manufacturer (e.g. Maruti, Hyundai, Tata)")
    model: str = Field(..., min_length=1, description="Vehicle model name (e.g. Swift, Creta, Nexon)")
    manufacturing_year: int = Field(..., ge=1980, le=CURRENT_YEAR, description="Year of vehicle manufacture")
    km_driven: float = Field(..., ge=0, le=2000000, description="Total kilometers traveled")
    asking_price: float = Field(..., gt=0, le=1000000000, description="Seller asking price in INR (strictly isolated from ML valuation model)")
    
    # Optional vehicle parameters
    number_of_owners: Optional[int] = Field(1, ge=1, le=10, description="Previous owner count")
    fuel_type: Optional[str] = Field("Petrol", description="Fuel type (Petrol, Diesel, CNG, Electric)")
    transmission_type: Optional[str] = Field("Manual", description="Transmission type (Manual, Automatic)")
    city: Optional[str] = Field("Delhi", description="City of registration / sale")
    bodytype: Optional[str] = Field(None, description="Vehicle body type")
    variant: Optional[str] = Field(None, description="Specific vehicle variant if known (e.g. VXi, SX Option)")
    
    # Optional condition & provenance parameters
    condition_notes: Optional[str] = Field(None, description="General physical condition notes")
    service_history_status: Optional[str] = Field(None, description="FULL_SERVICE_HISTORY | PARTIAL | UNAVAILABLE | UNKNOWN")
    accident_history_status: Optional[str] = Field(None, description="NO_ACCIDENTS_REPORTED | MINOR_ACCIDENT | MAJOR_ACCIDENT | UNKNOWN")
    insurance_status: Optional[str] = Field(None, description="COMPREHENSIVE | THIRD_PARTY | EXPIRED | UNAVAILABLE")
    tyre_condition: Optional[str] = Field(None, description="GOOD | WORN | REPLACED_RECENTLY | UNKNOWN")
    seller_notes: Optional[str] = Field(None, description="Additional claims or seller-provided notes")

    @field_validator("brand", "model", "fuel_type", "transmission_type", "city", "bodytype", "variant")
    @classmethod
    def strip_whitespace(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v

class PriceDeviation(BaseModel):
    absolute_difference: int = Field(..., description="Absolute difference: asking_price - estimated_fair_value (INR)")
    relative_difference_percent: float = Field(..., description="Relative percentage difference: (asking_price - estimated) / estimated * 100")
    user_facing_summary: str = Field(..., description="Plain-language summary of price deviation")
    evidence_state: str = Field(EvidenceState.MODEL_ESTIMATE.value, description="Evidence state for deviation")

class FairRangePosition(BaseModel):
    position_ratio: Optional[float] = Field(None, description="Relative position within range: (ask - low) / (high - low)")
    category: RangePositionCategory = Field(..., description="BELOW_RANGE | INSIDE_RANGE | ABOVE_RANGE | UNAVAILABLE")
    explanation: str = Field(..., description="Explanation of where asking price sits relative to expected bounds")

class AnomalyStatus(BaseModel):
    is_anomaly: bool = Field(..., description="Whether asking price is statistically anomalous")
    anomaly_type: str = Field("NONE", description="ANOMALOUS_LOW | ANOMALOUS_HIGH | NONE")
    anomaly_metric: str = Field("EMPIRICAL_RATIO_AND_ROBUST_Z", description="Statistical method used for anomaly detection")
    anomaly_score: Optional[float] = Field(None, description="Robust Z-Score or standardized deviation")
    advisory: Optional[str] = Field(None, description="Verification advisory for anomalous asking prices")

class NegotiationGuidance(BaseModel):
    target_price: Optional[int] = Field(None, description="Primary defensible negotiation target price (INR)")
    target_price_formatted: Optional[str] = Field(None, description="Formatted target price (e.g. ₹8,50,000)")
    target_range_low: Optional[int] = Field(None, description="Recommended negotiation range lower bound (INR)")
    target_range_high: Optional[int] = Field(None, description="Recommended negotiation range upper bound (INR)")
    target_range_formatted: Optional[str] = Field(None, description="Formatted negotiation range (e.g. ₹8,20,000 – ₹8,60,000)")
    negotiation_strength: NegotiationStrength = Field(..., description="STRONG | MODERATE | LIMITED")
    walk_away_signal: bool = Field(False, description="Flag indicating asking price is detached from market reality")
    walk_away_rationale: Optional[str] = Field(None, description="Reason for walk-away advisory if triggered")
    rationale: str = Field(..., description="Defensible rationale grounded in empirical market valuation")
    safety_disclaimer: str = Field(
        "A reasonable negotiation target based on the current valuation evidence is indicated above. "
        "Negotiation targets represent statistical guidance and do not guarantee seller acceptance.",
        description="Negotiation safety disclaimer prohibiting false certainty"
    )

class RiskSignal(BaseModel):
    category: RiskCategory = Field(..., description="PRICE_RISK | DOCUMENTATION_RISK | CONDITION_RISK | DATA_RISK")
    code: str = Field(..., description="Machine-readable risk code (e.g. PRICE_ABOVE_FAIR_RANGE)")
    severity: RiskSeverity = Field(..., description="LOW | MEDIUM | HIGH | CRITICAL")
    evidence_state: str = Field(..., description="Evidence provenance state (UNVERIFIED, EMPIRICAL, etc.)")
    title: str = Field(..., description="Brief risk title")
    explanation: str = Field(..., description="Detailed explanation of the risk signal")
    recommended_action: str = Field(..., description="Concrete action recommended to verify or mitigate risk")

class ValuationContext(BaseModel):
    estimated_fair_market_value: Optional[int] = Field(None, description="Model baseline asking price estimate")
    estimated_fair_market_value_formatted: Optional[str] = Field(None, description="Formatted baseline in INR")
    expected_fair_market_lower: Optional[int] = Field(None, description="Conformal lower bound")
    expected_fair_market_upper: Optional[int] = Field(None, description="Conformal upper bound")
    confidence_state: str = Field(..., description="HIGH_CONFIDENCE | MODERATE_CONFIDENCE | LIMITED_CONFIDENCE | INSUFFICIENT_DATA")
    evidence_quality: str = Field(..., description="SUPPORTED | EMPIRICAL | MODEL_ESTIMATE | INSUFFICIENT_DATA")
    model_version: str = Field(..., description="Valuation model version")
    target_semantic_concept: str = Field(..., description="Concept definition")

class DealAnalysisResponse(BaseModel):
    canonical_vehicle_id: Optional[str] = Field(None, description="Canonical vehicle identifier from taxonomy")
    vehicle_summary: str = Field(..., description="Human-readable vehicle summary")
    asking_price: int = Field(..., description="Seller asking price (INR)")
    asking_price_formatted: str = Field(..., description="Formatted asking price")
    asking_price_evidence_state: str = Field(EvidenceState.UNVERIFIED.value, description="Evidence state of user asking price")
    valuation: ValuationContext = Field(..., description="Primary valuation baseline from Phase 3 Valuation Service")
    deal_quality: DealQualityEnum = Field(..., description="GREAT_DEAL | FAIR_DEAL | OVERPRICED | UNUSUALLY_LOW_ASKING_PRICE | INSUFFICIENT_DATA")
    deal_quality_label: str = Field(..., description="Formatted user-facing label")
    price_deviation: PriceDeviation = Field(..., description="Absolute and relative deviation from model baseline")
    range_position: FairRangePosition = Field(..., description="Position relative to calibrated fair market range")
    anomaly_status: AnomalyStatus = Field(..., description="Anomaly detection outcome and advisory")
    negotiation: NegotiationGuidance = Field(..., description="Evidence-grounded negotiation target and strength")
    risk_signals: List[RiskSignal] = Field(default_factory=list, description="Structured risk signals")
    explanation: str = Field(..., description="Deterministic plain-language explanation of deal assessment")
    limitations: List[str] = Field(default_factory=list, description="Explicit disclosures, scope, and concept separation notes")
    computation_latency_ms: Optional[float] = Field(None, description="Execution latency of deal analysis in milliseconds")
    analysis_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
