"""
CARspective — Phase 15 Personalized Decision Intelligence Domain Models
Defines User Requirements Profile, explicit requirement provenance,
hard constraints, explainable User Fit scoring, decision quality,
personalized alternatives, shortlist structures, and comparison schemas.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator


class ProvenanceState(str, Enum):
    USER_EXPLICIT = "USER_EXPLICIT"
    USER_INFERRED = "USER_INFERRED"
    SYSTEM_DEFAULT = "SYSTEM_DEFAULT"
    NOT_SPECIFIED = "NOT_SPECIFIED"


class RequirementProvenance(BaseModel):
    state: ProvenanceState = ProvenanceState.NOT_SPECIFIED
    source_phrase: Optional[str] = None
    explanation: Optional[str] = None


class PurchaseType(str, Enum):
    NEW = "NEW"
    USED = "USED"
    EITHER = "EITHER"
    NOT_SPECIFIED = "NOT_SPECIFIED"


class UsageProfile(str, Enum):
    CITY = "CITY"
    HIGHWAY = "HIGHWAY"
    MIXED = "MIXED"
    NOT_SPECIFIED = "NOT_SPECIFIED"


class PriorityLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    NOT_SPECIFIED = "NOT_SPECIFIED"


class ToleranceLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    NOT_SPECIFIED = "NOT_SPECIFIED"


class HardConstraintStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


class DecisionQuality(str, Enum):
    HIGH = "HIGH"
    MODERATE = "MODERATE"
    LIMITED = "LIMITED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class HardConstraintsConfig(BaseModel):
    strict_budget_ceiling: bool = False
    strict_transmission: bool = False
    strict_fuel_type: bool = False
    strict_min_seating: bool = False
    strict_body_type: bool = False


class UserRequirementsProfile(BaseModel):
    """
    Structured user decision profile with field-level provenance tracking.
    Never infers sensitive personal characteristics (income, race, religion, etc.).
    """
    budget_min_inr: Optional[float] = Field(None, ge=0, le=1000000000, description="Minimum acquisition budget in INR")
    budget_max_inr: Optional[float] = Field(None, ge=0, le=1000000000, description="Maximum acquisition budget in INR")
    budget_flexible: bool = Field(False, description="Whether budget ceiling allows moderate stretch")
    monthly_running_budget_max_inr: Optional[float] = Field(None, ge=0, description="Monthly ownership expenditure ceiling in INR")

    purchase_type: PurchaseType = PurchaseType.NOT_SPECIFIED
    usage_profile: UsageProfile = UsageProfile.NOT_SPECIFIED
    annual_km: Optional[float] = Field(None, ge=0, le=200000, description="Projected annual distance in km")
    family_size: Optional[int] = Field(None, ge=1, le=12, description="Primary occupant headcount")

    fuel_preferences: List[str] = Field(default_factory=list, description="Preferred fuel types e.g. Petrol, Diesel, CNG, Electric")
    transmission_preferences: List[str] = Field(default_factory=list, description="Preferred transmission types e.g. Manual, Automatic")
    body_type_preferences: List[str] = Field(default_factory=list, description="Preferred body types e.g. Hatchback, Sedan, SUV")

    safety_priority: PriorityLevel = PriorityLevel.NOT_SPECIFIED
    reliability_priority: PriorityLevel = PriorityLevel.NOT_SPECIFIED
    maintenance_priority: PriorityLevel = PriorityLevel.NOT_SPECIFIED
    practicality_priority: PriorityLevel = PriorityLevel.NOT_SPECIFIED
    resale_priority: PriorityLevel = PriorityLevel.NOT_SPECIFIED
    performance_priority: PriorityLevel = PriorityLevel.NOT_SPECIFIED
    efficiency_priority: PriorityLevel = PriorityLevel.NOT_SPECIFIED
    value_priority: PriorityLevel = PriorityLevel.NOT_SPECIFIED

    ownership_years: Optional[int] = Field(None, ge=1, le=15, description="Anticipated holding period in years")
    maintenance_tolerance: ToleranceLevel = ToleranceLevel.NOT_SPECIFIED

    hard_constraints: HardConstraintsConfig = Field(default_factory=HardConstraintsConfig)
    provenance_map: Dict[str, RequirementProvenance] = Field(default_factory=dict)

    def get_provenance(self, field_name: str) -> RequirementProvenance:
        return self.provenance_map.get(field_name, RequirementProvenance(state=ProvenanceState.NOT_SPECIFIED))

    def set_provenance(self, field_name: str, state: ProvenanceState, source_phrase: Optional[str] = None):
        self.provenance_map[field_name] = RequirementProvenance(
            state=state, source_phrase=source_phrase
        )


class ConstraintCheckItem(BaseModel):
    constraint_name: str
    status: HardConstraintStatus
    required_value: Any
    actual_value: Any
    explanation: str


class ConstraintValidationResult(BaseModel):
    overall_status: HardConstraintStatus
    violations: List[str] = Field(default_factory=list)
    checks: List[ConstraintCheckItem] = Field(default_factory=list)


class PersonalizedFitBreakdown(BaseModel):
    budget_fit: Optional[int] = None
    ownership_budget_fit: Optional[int] = None
    usage_fit: Optional[int] = None
    family_fit: Optional[int] = None
    powertrain_fit: Optional[int] = None
    safety_fit: Optional[int] = None
    reliability_fit: Optional[int] = None
    maintenance_fit: Optional[int] = None
    practicality_fit: Optional[int] = None
    resale_fit: Optional[int] = None
    performance_fit: Optional[int] = None
    ownership_horizon_fit: Optional[int] = None

    component_weights: Dict[str, float] = Field(default_factory=dict)
    overall_user_fit_score: int = Field(..., ge=0, le=100)
    decision_quality: DecisionQuality
    data_limitations: List[str] = Field(default_factory=list)


class PersonalizedAlternative(BaseModel):
    canonical_vehicle_id: str
    vehicle_summary: str
    intrinsic_score: Optional[int] = None
    user_fit_score: int
    advantage_over_target: str
    tradeoff_vs_target: str
    verdict_label: str


class DecisionEvaluationResponse(BaseModel):
    canonical_vehicle_id: str
    vehicle_summary: str
    intrinsic_score: Optional[int] = None
    user_fit_score: int
    vehicle_fit_score: int
    deal_fit_score: Optional[int] = None
    hard_constraint_status: HardConstraintStatus
    recommendation_verdict: str
    verdict_label: str

    fit_breakdown: PersonalizedFitBreakdown
    why_it_fits: List[str] = Field(default_factory=list)
    why_it_may_not_fit: List[str] = Field(default_factory=list)
    tradeoffs: List[str] = Field(default_factory=list)
    what_to_verify_before_buying: List[str] = Field(default_factory=list)
    alternatives: List[PersonalizedAlternative] = Field(default_factory=list)

    decision_quality: DecisionQuality
    limitations: List[str] = Field(default_factory=list)
    computation_latency_ms: Optional[float] = None


class ShortlistVehicleItem(BaseModel):
    canonical_vehicle_id: str
    brand: str
    model: str
    year: Optional[int] = None
    variant: Optional[str] = None
    intrinsic_score: Optional[int] = None
    user_fit_score: int
    estimated_fair_market_range: Optional[str] = None
    ownership_burden_5yr_inr: Optional[float] = None
    decision_quality: str
    key_tradeoffs: List[str] = Field(default_factory=list)
    hard_constraint_status: str
    is_eligible: bool = True


class ShortlistRankResponse(BaseModel):
    ranked_vehicles: List[DecisionEvaluationResponse]
    user_profile_summary: Dict[str, Any]
    top_recommendation_id: Optional[str] = None
    ranking_notes: List[str] = Field(default_factory=list)
    computation_latency_ms: Optional[float] = None


class PersonalizedComparisonResponse(BaseModel):
    general_winner_index: int
    general_winner_rationale: str
    user_winner_index: int
    user_winner_rationale: str
    divergence_explanation: Optional[str] = None
    vehicles: List[DecisionEvaluationResponse]
    computation_latency_ms: Optional[float] = None


class PersonalizedInspectionPrioritizationResponse(BaseModel):
    canonical_vehicle_id: str
    vehicle_summary: str
    prioritized_checklist: List[Dict[str, Any]]
    priority_reasons: List[str]
    computation_latency_ms: Optional[float] = None


class NaturalLanguageRequirementsQuery(BaseModel):
    query: str = Field(..., min_length=2, description="User natural language statement e.g. 'I need a reliable family car under 10 lakh'")


class NaturalLanguageRequirementsResponse(BaseModel):
    parsed_profile: UserRequirementsProfile
    extracted_fields_count: int
    clarification_questions: List[str] = Field(default_factory=list)
    provenance_summary: Dict[str, str] = Field(default_factory=dict)
    parser_state: str = Field("SUCCESS", description="Parser result state: 'SUCCESS' or 'AMBIGUOUS'")
    computation_latency_ms: Optional[float] = None
