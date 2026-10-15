"""
CARspective — Valuation Pydantic v2 Models & Schemas
Defines request contracts, fair market range, and valuation response payloads.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timezone

CURRENT_YEAR = 2026

class ValuationRequest(BaseModel):
    brand: str = Field(..., min_length=1, description="Vehicle manufacturer (e.g. Maruti, Hyundai, Tata)")
    model: str = Field(..., min_length=1, description="Vehicle model name (e.g. Swift, Creta, Nexon)")
    manufacturing_year: int = Field(..., ge=1980, le=CURRENT_YEAR, description="Year of vehicle manufacture")
    km_driven: float = Field(..., ge=0, le=2000000, description="Total kilometers traveled")
    fuel_type: Optional[str] = Field("Petrol", description="Fuel type (Petrol, Diesel, CNG, Electric)")
    transmission_type: Optional[str] = Field("Manual", description="Transmission type (Manual, Automatic)")
    city: Optional[str] = Field("Delhi", description="City of registration / sale")
    bodytype: Optional[str] = Field("Hatchback", description="Vehicle body type")
    number_of_owners: Optional[int] = Field(1, ge=1, le=10, description="Previous owner count")
    variant: Optional[str] = Field(None, description="Specific vehicle variant if known (e.g. VXi, XZ Plus)")
    
    # Explicit separation of asking price
    asking_price: Optional[float] = Field(
        None,
        ge=0,
        description="Seller asking price (ISOLATED: Reserved for future Deal Analyzer; strictly ignored by valuation engine)"
    )

    @field_validator("brand", "model", "fuel_type", "transmission_type", "city", "bodytype")
    @classmethod
    def strip_whitespace(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v

class FairMarketRange(BaseModel):
    lower_bound: int = Field(..., description="Lower bound of expected fair market asking price")
    upper_bound: int = Field(..., description="Upper bound of expected fair market asking price")
    confidence_interval_percent: float = Field(80.0, description="Empirical conformal coverage percentage")
    multiplier: float = Field(..., description="Conformal calibration multiplier (e.g. +/- 0.2178)")

class ValuationResponse(BaseModel):
    canonical_vehicle_id: Optional[str] = Field(None, description="Invariant Canonical Vehicle Identifier")
    vehicle_resolution_status: str = Field(..., description="Resolution status from Canonical Taxonomy Engine")
    estimated_fair_market_value: Optional[int] = Field(None, description="Statistical Model Estimate of the Historical Market Asking-Price Baseline")
    expected_fair_market_range: Optional[FairMarketRange] = Field(None, description="Empirically calibrated conformal fair market range")
    confidence_state: str = Field(..., description="HIGH_CONFIDENCE | MODERATE_CONFIDENCE | LIMITED_CONFIDENCE | INSUFFICIENT_DATA")
    evidence_quality: str = Field(..., description="SUPPORTED | EMPIRICAL | MODEL_ESTIMATE | INSUFFICIENT_DATA")
    market_evidence: Optional[Dict[str, Any]] = Field(None, description="Empirical listing statistics and comparable volume")
    model_metadata: Dict[str, Any] = Field(..., description="Algorithm, version, and integrity metadata")
    valuation_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    limitations: List[str] = Field(default_factory=list, description="Explicit disclosures, anti-hallucination disclaimers and scope")
