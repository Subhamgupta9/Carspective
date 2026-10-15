"""
CARspective — Phase 14 Market Intelligence Domain Models
Defines canonical market profile, explainable liquidity, supply indicators,
demand proxies, empirical asking-price depreciation, segment benchmarks,
and explicit evidence provenance.

Data Basis: Historical Indian used-car listings (Seller Asking Price Baseline).
Strict Rule: Never represent listing asking data as realized transaction sales.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class MarketScope(str, Enum):
    NATIONAL = "NATIONAL"
    REGIONAL = "REGIONAL"
    VEHICLE = "VEHICLE"
    SEGMENT = "SEGMENT"


class MarketLiquidityIndicator(str, Enum):
    HIGH_LIQUIDITY = "HIGH_LIQUIDITY"
    MODERATE_LIQUIDITY = "MODERATE_LIQUIDITY"
    LIMITED_LIQUIDITY = "LIMITED_LIQUIDITY"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class MarketSupplyIndicator(str, Enum):
    HIGH = "HIGH"
    MODERATE = "MODERATE"
    LIMITED = "LIMITED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class DemandIndicator(str, Enum):
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    LIMITED = "LIMITED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class ResaleIndicator(str, Enum):
    ABOVE_SEGMENT_MEDIAN = "ABOVE_SEGMENT_MEDIAN"
    AVERAGE_SEGMENT_MEDIAN = "AVERAGE_SEGMENT_MEDIAN"
    BELOW_SEGMENT_MEDIAN = "BELOW_SEGMENT_MEDIAN"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class ValuePositionIndicator(str, Enum):
    COMPETITIVE = "COMPETITIVE"
    PREMIUM = "PREMIUM"
    BUDGET = "BUDGET"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class EvidenceState(str, Enum):
    VERIFIED = "VERIFIED"
    SUPPORTED = "SUPPORTED"
    EMPIRICAL = "EMPIRICAL"
    MODEL_ESTIMATE = "MODEL_ESTIMATE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    UNVERIFIED = "UNVERIFIED"
    DEPRECATED = "DEPRECATED"


class DepreciationPoint(BaseModel):
    manufacturing_year: int
    age_years: int
    sample_size: int
    median_price_inr: float
    mean_price_inr: float
    price_iqr_low_inr: float
    price_iqr_high_inr: float
    observed_retention_pct: Optional[float] = None
    is_statistically_robust: bool = True


class DepreciationProfile(BaseModel):
    canonical_vehicle_id: str
    model_name: str
    sample_size: int
    observation_period: str
    data_basis: str
    points: List[DepreciationPoint]
    annual_depreciation_rate_pct: Optional[float] = None
    evidence_state: EvidenceState = EvidenceState.EMPIRICAL
    methodology_notes: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)


class SegmentBenchmark(BaseModel):
    canonical_vehicle_id: str
    segment_name: str
    segment_listing_count: int
    segment_share_of_market_pct: float
    segment_median_price_inr: float
    segment_mean_price_inr: float
    segment_median_km: float
    vehicle_rank_in_segment: Optional[int] = None
    vehicle_share_in_segment_pct: Optional[float] = None
    top_segment_rivals: List[str] = Field(default_factory=list)
    evidence_state: EvidenceState = EvidenceState.EMPIRICAL
    methodology_notes: List[str] = Field(default_factory=list)


class MarketPositionSummary(BaseModel):
    observed_supply: MarketSupplyIndicator
    liquidity: MarketLiquidityIndicator
    resale_position: ResaleIndicator
    value_position: ValuePositionIndicator
    one_line_summary: str


class VehicleMarketProfile(BaseModel):
    canonical_vehicle_id: str
    brand: str
    model: str
    market_scope: MarketScope = MarketScope.NATIONAL
    geography: str = "India (National Aggregation)"
    observation_period: str = "2018–2024 (Historical Secondary Market Listings)"
    data_basis: str = "Seller Asking Price Baseline (Historical Secondary Market Listings)"
    
    listing_count: int
    market_share_pct: float
    national_rank: Optional[int] = None
    relative_supply: MarketSupplyIndicator
    
    liquidity_indicator: MarketLiquidityIndicator
    liquidity_rationale: str
    
    demand_indicator: DemandIndicator
    demand_rationale: str
    
    resale_indicator: ResaleIndicator
    resale_rationale: str
    
    valuation_position: ValuePositionIndicator
    market_position_summary: MarketPositionSummary
    
    top_regional_markets: Dict[str, int] = Field(default_factory=dict)
    
    evidence_state: EvidenceState = EvidenceState.EMPIRICAL
    freshness: str = "HISTORICAL_STATIC_ARCHIVE"
    calculation_method: str = "Empirical frequency, CDF ranking, and quartile positioning across 57,480-listing dataset"
    limitations: List[str] = Field(default_factory=list)
