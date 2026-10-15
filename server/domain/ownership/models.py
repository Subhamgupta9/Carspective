"""
CARspective — Phase 14 Ownership Intelligence Domain Models
Defines contracts for structured ownership profiles, interactive Fuel Cost Calculator,
transparent Total Cost of Ownership (TCO) framework, deterministic ownership risks,
and multi-source assumption labeling.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class TCOComponentStatus(str, Enum):
    USER_PROVIDED = "USER_PROVIDED"
    EVIDENCE_BACKED = "EVIDENCE_BACKED"
    MODEL_ESTIMATED = "MODEL_ESTIMATED"
    UNAVAILABLE = "UNAVAILABLE"


class OwnershipRiskCategory(str, Enum):
    FUEL_COST_RISK = "Fuel Cost Risk"
    MAINTENANCE_COMPLEXITY = "Maintenance Complexity"
    PARTS_COST_RISK = "Parts Cost Risk"
    RELIABILITY_RISK = "Reliability Risk"
    RESALE_RISK = "Resale Risk"
    USAGE_FIT_RISK = "Usage Fit Risk"


class RiskSeverity(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    ELEVATED = "ELEVATED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class EvidenceState(str, Enum):
    VERIFIED = "VERIFIED"
    SUPPORTED = "SUPPORTED"
    EMPIRICAL = "EMPIRICAL"
    MODEL_ESTIMATE = "MODEL_ESTIMATE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    UNVERIFIED = "UNVERIFIED"
    DEPRECATED = "DEPRECATED"


# 1. Fuel Cost Calculator Models
class FuelCostRequest(BaseModel):
    canonical_vehicle_id: Optional[str] = None
    fuel_type: str = Field("Petrol", description="Petrol | Diesel | CNG | Electric")
    annual_km: float = Field(..., gt=0, le=150000, description="Annual distance driven in km")
    fuel_price_per_unit: Optional[float] = Field(None, gt=0, le=500, description="Price in INR per Litre/Kg/kWh")
    mileage_kmpl: Optional[float] = Field(None, gt=0, le=100, description="Expected fuel economy (km/l or km/kg or km/kWh)")
    city_driving_ratio: float = Field(0.70, ge=0.0, le=1.0, description="Fraction of driving in city conditions")


class FuelCostResponse(BaseModel):
    annual_km: float
    fuel_type: str
    fuel_price_per_unit: float
    effective_mileage_kmpl: float
    annual_fuel_cost_inr: float
    monthly_fuel_cost_inr: float
    cost_per_km_inr: float
    assumptions_used: List[str]
    evidence_state: EvidenceState = EvidenceState.SUPPORTED


# 2. TCO Models
class TCOComponent(BaseModel):
    component_name: str
    annual_cost_inr: float
    total_period_cost_inr: float
    status: TCOComponentStatus
    data_source: str
    calculation_method: str
    notes: Optional[str] = None


class TCORequest(BaseModel):
    canonical_vehicle_id: str
    ownership_years: int = Field(5, ge=1, le=10, description="Intended retention horizon in years")
    annual_km: float = Field(12000.0, gt=0, le=100000, description="Expected annual distance in km")
    custom_purchase_price: Optional[float] = Field(None, gt=0, description="Custom vehicle purchase price in INR")
    custom_fuel_price: Optional[float] = Field(None, gt=0, description="Custom fuel price per unit")
    custom_mileage: Optional[float] = Field(None, gt=0, description="Custom expected fuel economy")
    custom_annual_insurance: Optional[float] = Field(None, gt=0, description="Custom annual insurance premium")


class TCOResponse(BaseModel):
    canonical_vehicle_id: str
    vehicle_summary: str
    ownership_years: int
    annual_km: float
    total_distance_km: float
    purchase_price_baseline_inr: float
    expected_residual_value_inr: float
    net_depreciation_loss_inr: float
    
    total_cost_of_ownership_inr: float
    annualized_tco_inr: float
    cost_per_km_inr: float
    
    components: List[TCOComponent]
    assumptions: List[str]
    evidence_state: EvidenceState = EvidenceState.MODEL_ESTIMATE
    limitations: List[str] = Field(default_factory=list)


# 3. Ownership Risk Signal
class OwnershipRiskSignal(BaseModel):
    category: OwnershipRiskCategory
    severity: RiskSeverity
    title: str
    description: str
    mitigation_advice: str
    evidence_state: EvidenceState = EvidenceState.SUPPORTED


# 4. Comprehensive Vehicle Ownership Profile
class MaintenanceSchedule(BaseModel):
    service_interval_km: int
    service_interval_months: int
    typical_annual_maintenance_inr: str
    maintenance_complexity: str
    parts_availability: str
    routine_checklist: List[str]
    evidence_state: EvidenceState = EvidenceState.SUPPORTED


class PracticalityProfile(BaseModel):
    city_suitability: str
    highway_suitability: str
    family_suitability: str
    boot_space_assessment: str
    ground_clearance_assessment: str


class VehicleOwnershipIntelligence(BaseModel):
    canonical_vehicle_id: str
    brand: str
    model: str
    generation: Optional[str] = None
    variant: Optional[str] = None
    fuel_type: str
    transmission: str
    
    maintenance: MaintenanceSchedule
    practicality: PracticalityProfile
    real_world_city_mileage: str
    real_world_highway_mileage: str
    
    strengths: List[str]
    concerns: List[str]
    risk_signals: List[OwnershipRiskSignal]
    
    default_tco_summary: Optional[TCOResponse] = None
    
    one_line_synthesis: str
    evidence_state: EvidenceState = EvidenceState.SUPPORTED
    limitations: List[str] = Field(default_factory=list)
