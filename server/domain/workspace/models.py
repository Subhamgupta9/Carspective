"""
CARspective — Phase 13 Vehicle Intelligence Workspace Models
Defines contracts for identity confidence, executive intelligence summary,
variant switcher metadata, and unified workspace response payload.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class IdentityConfidenceLevel(str, Enum):
    EXACT = "exact"          # Full 6-tier canonical resolution (variant & powertrain specified)
    RESOLVED = "resolved"    # Generation/year resolved, baseline trim/powertrain defaults applied
    AMBIGUOUS = "ambiguous"  # Multiple potential generations/variants matching, user confirmation prompted
    LIMITED = "limited"      # Canonical model in taxonomy, but deep 9-table knowledge is partial/unavailable


class SiblingVariantInfo(BaseModel):
    name: str
    slug: str
    trim_level: Optional[str] = None
    powertrains: List[str] = Field(default_factory=list)
    canonical_id: str
    is_current: bool = False


class SiblingGenInfo(BaseModel):
    name: str
    slug: str
    year_start: int
    year_end: Optional[int] = None
    canonical_id: str
    is_current: bool = False


class IdentityConfidenceInfo(BaseModel):
    level: IdentityConfidenceLevel
    title: str
    description: str
    is_confirmed: bool = True
    needs_user_confirmation: bool = False
    sibling_variants: List[SiblingVariantInfo] = Field(default_factory=list)
    sibling_generations: List[SiblingGenInfo] = Field(default_factory=list)


class VehicleIdentity(BaseModel):
    canonical_vehicle_id: str
    brand: str
    brand_slug: str
    model: str
    model_slug: str
    generation: Optional[str] = None
    generation_slug: Optional[str] = None
    year: Optional[int] = None
    variant: Optional[str] = None
    variant_slug: Optional[str] = None
    fuel_type: Optional[str] = None
    transmission_type: Optional[str] = None
    drivetrain: Optional[str] = None
    body_type: Optional[str] = None
    segment: Optional[str] = None
    coverage_tier: str = "TIER_1_DEEP"


class ExecutiveSummary(BaseModel):
    carspective_score: Optional[int] = None
    score_band: str  # "EXCELLENT" | "GOOD" | "FAIR" | "CAUTION" | "UNAVAILABLE"
    estimated_fair_market_value_inr: Optional[int] = None
    estimated_fair_market_value_lakhs: Optional[float] = None
    expected_fair_market_range_low_inr: Optional[int] = None
    expected_fair_market_range_high_inr: Optional[int] = None
    expected_fair_market_range_low_lakhs: Optional[float] = None
    expected_fair_market_range_high_lakhs: Optional[float] = None
    deal_quality: Optional[str] = None
    recommendation_verdict: str
    safety_stars: Optional[int] = None
    safety_agency: Optional[str] = None
    bodyshell_integrity: Optional[str] = None
    typical_annual_maintenance_inr: Optional[str] = None
    maintenance_complexity: Optional[str] = None
    reliability_watchpoints_count: int = 0
    one_line_summary: str


class WorkspaceInspectionSummary(BaseModel):
    total_applicable_items: int
    critical_items_count: int
    top_watchpoints: List[str] = Field(default_factory=list)
    documentation_requirements: List[str] = Field(default_factory=list)
    purchase_readiness: str


class VehicleWorkspaceResponse(BaseModel):
    canonical_vehicle_id: str
    identity: VehicleIdentity
    identity_confidence: IdentityConfidenceInfo
    executive_summary: ExecutiveSummary
    valuation: Optional[Dict[str, Any]] = None
    deal_analysis: Optional[Dict[str, Any]] = None
    score: Optional[Dict[str, Any]] = None
    knowledge: Optional[Dict[str, Any]] = None
    recommendation: Optional[Dict[str, Any]] = None
    inspection_summary: WorkspaceInspectionSummary
    alternatives: List[Dict[str, Any]] = Field(default_factory=list)
    visual: Dict[str, Any] = Field(default_factory=dict)
    market_profile: Optional[Dict[str, Any]] = None
    ownership_intelligence: Optional[Dict[str, Any]] = None
    personalized_decision: Optional[Dict[str, Any]] = None
    evidence_freshness: Optional[Dict[str, Any]] = None
    data_governance: Optional[Dict[str, Any]] = None
    current_market: Optional[Dict[str, Any]] = None
    limitations: List[str] = Field(default_factory=list)
    computation_latency_ms: Optional[float] = None

