"""
CARspective — CARspective Score Domain Models & Schemas
Defines request contracts, dimension scores, evidence-weighted composite score,
contributing factors, and structured score explanations.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timezone

class ScoreDimensionName(str, Enum):
    STRUCTURAL_SAFETY = "Structural Safety"
    RELIABILITY_AND_LONGEVITY = "Reliability & Longevity"
    MAINTENANCE_AND_OWNERSHIP = "Maintenance & Ownership"
    RESALE_AND_MARKET_LIQUIDITY = "Resale & Market Liquidity"
    REAL_WORLD_PRACTICALITY = "Real-World Practicality"

class EvidenceQuality(str, Enum):
    HIGH = "HIGH"
    MODERATE = "MODERATE"
    LIMITED = "LIMITED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"

class EvidenceState(str, Enum):
    VERIFIED = "VERIFIED"
    SUPPORTED = "SUPPORTED"
    EMPIRICAL = "EMPIRICAL"
    MODEL_ESTIMATE = "MODEL_ESTIMATE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    UNVERIFIED = "UNVERIFIED"

class ScoreRequest(BaseModel):
    brand: str = Field(..., min_length=1, description="Vehicle manufacturer (e.g. Tata, Hyundai, Maruti)")
    model: str = Field(..., min_length=1, description="Vehicle model (e.g. Nexon, Creta, Swift)")
    manufacturing_year: Optional[int] = Field(None, ge=1980, le=2026, description="Manufacturing year")
    fuel_type: Optional[str] = Field("Petrol", description="Fuel type (Petrol, Diesel, CNG, Electric)")
    transmission_type: Optional[str] = Field("Manual", description="Transmission type (Manual, Automatic)")
    variant: Optional[str] = Field(None, description="Trim variant if known")
    
    # Intrinsic score strictly ignores asking price even if passed
    asking_price: Optional[float] = Field(
        None,
        description="ISOLATED: Asking price is strictly ignored by the intrinsic scoring system"
    )

    @field_validator("brand", "model", "fuel_type", "transmission_type", "variant")
    @classmethod
    def strip_whitespace(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v

class DimensionScore(BaseModel):
    dimension_name: ScoreDimensionName = Field(..., description="Locked dimension name")
    score: Optional[int] = Field(None, ge=0, le=100, description="Normalized score 0-100 (None if INSUFFICIENT_DATA)")
    score_formatted: str = Field(..., description="User-facing score representation (e.g. '85/100' or 'Insufficient Data')")
    evidence_state: EvidenceState = Field(..., description="VERIFIED, SUPPORTED, EMPIRICAL, INSUFFICIENT_DATA")
    confidence: str = Field(..., description="HIGH, MODERATE, LIMITED, INSUFFICIENT_DATA")
    contributing_factors: List[str] = Field(default_factory=list, description="Specific factual contributing points")
    sources: List[str] = Field(default_factory=list, description="Authoritative documentary or dataset citations")
    limitations: List[str] = Field(default_factory=list, description="Scope limitations or missing evidence disclosures")

class ScoreExplanation(BaseModel):
    strong_areas: List[str] = Field(default_factory=list, description="Dimensions scoring >= 80/100")
    watch_areas: List[str] = Field(default_factory=list, description="Dimensions scoring < 70/100 or missing evidence")
    summary: str = Field(..., description="Deterministic plain-language score overview")

class ScoreResponse(BaseModel):
    canonical_vehicle_id: Optional[str] = Field(None, description="Canonical vehicle identifier from taxonomy")
    vehicle_summary: str = Field(..., description="Resolved vehicle descriptor")
    overall_score: Optional[int] = Field(None, ge=0, le=100, description="Intrinsic composite vehicle score (0-100)")
    overall_score_formatted: str = Field(..., description="Formatted overall score (e.g. '82/100' or 'Limited Analysis')")
    evidence_quality: EvidenceQuality = Field(..., description="Completeness of supporting evidence (HIGH, MODERATE, LIMITED, INSUFFICIENT_DATA)")
    dimensions: List[DimensionScore] = Field(..., description="Scores for the five locked dimensions")
    explanation: ScoreExplanation = Field(..., description="Deterministic explanation of strengths and watch areas")
    limitations: List[str] = Field(default_factory=list, description="Overall scoring boundaries and disclosures")
    score_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
