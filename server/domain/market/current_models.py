"""
CARspective — Phase 17 Current Market Intelligence Domain Models
Defines governed schemas for live market observations, deduplication states,
statistical price distributions, supply tiers, regional breakdowns, and historical/current separation.

Data Semantics:
- Historical: 57,480 historical used-car listing records (2018–2024).
- Current: Newly ingested current asking-price observations (2026-Q3).
- Strict Rule: Current market observations represent seller asking prices; never transaction settlement prices.
"""

import uuid
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class CurrentObservationType(str, Enum):
    CURRENT_LISTING = "CURRENT_LISTING"
    AGGREGATOR_FEED = "AGGREGATOR_FEED"
    VERIFIED_DEALER_FEED = "VERIFIED_DEALER_FEED"


class SellerType(str, Enum):
    INDIVIDUAL = "INDIVIDUAL"
    DEALER = "DEALER"
    CERTIFIED_PLATFORM = "CERTIFIED_PLATFORM"
    UNKNOWN = "UNKNOWN"


class ListingStatus(str, Enum):
    ACTIVE = "ACTIVE"
    DELISTED = "DELISTED"
    PRICE_REDUCED = "PRICE_REDUCED"
    UNKNOWN = "UNKNOWN"


class DuplicateClassification(str, Enum):
    DISTINCT = "DISTINCT"
    EXACT_DUPLICATE = "EXACT_DUPLICATE"
    PROBABLE_DUPLICATE = "PROBABLE_DUPLICATE"


class CurrentFreshnessState(str, Enum):
    CURRENT = "CURRENT"   # <= 30 days
    AGING = "AGING"       # 31 - 90 days
    STALE = "STALE"       # 91 - 180 days
    EXPIRED = "EXPIRED"   # > 180 days


class CurrentSupplyTier(str, Enum):
    STRONG_CURRENT_SUPPLY = "STRONG_CURRENT_SUPPLY"       # >= 25 observations
    MODERATE_CURRENT_SUPPLY = "MODERATE_CURRENT_SUPPLY"   # 10 - 24 observations
    LIMITED_CURRENT_SUPPLY = "LIMITED_CURRENT_SUPPLY"     # 1 - 9 observations
    INSUFFICIENT_CURRENT_DATA = "INSUFFICIENT_CURRENT_DATA" # 0 observations


class CurrentMarketObservationRecord(BaseModel):
    observation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str
    source_record_reference: str
    observed_at: datetime
    published_at: Optional[datetime] = None
    canonical_vehicle_id: str
    observation_type: CurrentObservationType = CurrentObservationType.CURRENT_LISTING
    
    asking_price: float = Field(gt=0)
    model_year: int = Field(ge=1990, le=2030)
    mileage: float = Field(ge=0)
    location_city: Optional[str] = None
    location_region: Optional[str] = None
    seller_type: SellerType = SellerType.DEALER
    transmission: str = "Manual"
    fuel_type: str = "Petrol"
    body_type: Optional[str] = None
    listing_status: ListingStatus = ListingStatus.ACTIVE
    
    source_url: Optional[str] = None
    evidence_state: str = "EMPIRICAL"
    freshness_state: CurrentFreshnessState = CurrentFreshnessState.CURRENT
    ingestion_batch_id: Optional[str] = None
    data_quality_status: str = "GOOD"
    
    duplicate_status: DuplicateClassification = DuplicateClassification.DISTINCT
    duplicate_of_id: Optional[str] = None
    
    is_outlier: bool = False
    outlier_reasons: List[str] = Field(default_factory=list)
    analytical_eligibility: bool = True


class CurrentPriceDistribution(BaseModel):
    canonical_vehicle_id: str
    sample_size: int
    min_price_inr: float
    p10_price_inr: float
    p25_price_inr: float
    median_price_inr: float # p50
    p75_price_inr: float
    p90_price_inr: float
    max_price_inr: float
    iqr_inr: float
    std_dev_price_inr: float
    mean_price_inr: float
    currency: str = "INR"
    semantics: str = "Current observed seller asking-price distribution. Not realized transaction sale prices."


class CurrentMarketSupply(BaseModel):
    canonical_vehicle_id: str
    total_observation_count: int
    usable_observation_count: int
    supply_tier: CurrentSupplyTier
    regional_supply: Dict[str, int] = Field(default_factory=dict)
    seller_distribution: Dict[str, int] = Field(default_factory=dict)
    freshness_distribution: Dict[str, int] = Field(default_factory=dict)
    observation_period: str = "2026-Q3 (Current Market Observations)"
    coverage_scope: str = "Observed in available source coverage"


class CurrentRegionalIntelligence(BaseModel):
    region_name: str
    observation_count: int
    median_asking_price_inr: float
    iqr_low_inr: float
    iqr_high_inr: float
    median_mileage_km: float
    coverage_disclaimer: str = (
        "Observed in available source coverage across regional listings; not exhaustive market census."
    )


class CurrentVsHistoricalComparison(BaseModel):
    canonical_vehicle_id: str
    historical_observation_period: str = "2018–2024 (57,480 Historical Listings Baseline)"
    historical_sample_size: int
    historical_median_asking_price_inr: float
    current_observation_period: str = "2026-Q3 (Current Market Observations)"
    current_sample_size: int
    current_median_asking_price_inr: float
    asking_price_shift_pct: Optional[float] = None
    supply_context: str
    semantics_clarification: str = (
        "Both historical baseline and current observations represent seller asking prices. "
        "Neither represents verified dealer transaction clearing prices."
    )


class CurrentMarketEvidence(BaseModel):
    sources_contributed: List[str] = Field(default_factory=list)
    total_observations: int
    usable_observations: int
    duplicate_count: int
    outlier_count: int
    geographic_coverage: List[str] = Field(default_factory=list)
    collection_window: str = "2026-07-01 to 2026-10-08"
    freshness_distribution: Dict[str, int] = Field(default_factory=dict)
    evidence_state: str = "EMPIRICAL"
    limitations: List[str] = Field(default_factory=list)


class CurrentMarketIntelligenceResponse(BaseModel):
    canonical_vehicle_id: str
    observation_period: str = "2026-Q3"
    supply: CurrentMarketSupply
    price_distribution: Optional[CurrentPriceDistribution] = None
    regional_breakdown: List[CurrentRegionalIntelligence] = Field(default_factory=list)
    comparison_with_historical: Optional[CurrentVsHistoricalComparison] = None
    evidence: CurrentMarketEvidence
    limitations: List[str] = Field(default_factory=list)


class CurrentMarketIngestionResult(BaseModel):
    batch_id: str
    source_id: str
    records_received: int
    accepted_count: int
    duplicate_count: int
    outlier_count: int
    rejected_count: int
    processing_duration_ms: float
    validation_status: str
    commit_status: str
