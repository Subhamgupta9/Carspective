"""
CARspective — Phase 7 Inspection Intelligence Domain Models & Schemas
Defines request contracts, canonical inspection categories, checklist item definitions,
finding models with strict evidence provenance, deterministic risk structures,
document verification requirements, and the complete inspection evaluation response payload.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timezone


# ────────────────────────────────────────────────────────────────────
# Enums
# ────────────────────────────────────────────────────────────────────

class InspectionCategory(str, Enum):
    DOCUMENTATION = "Documentation"
    EXTERIOR = "Exterior"
    ENGINE_AND_POWERTRAIN = "Engine & Powertrain"
    UNDERBODY_AND_STRUCTURE = "Underbody & Structure"
    INTERIOR = "Interior"
    SAFETY = "Safety"
    TEST_DRIVE = "Test Drive"


class ImportanceLevel(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class FindingStatus(str, Enum):
    PASS = "PASS"
    ATTENTION = "ATTENTION"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class FindingSource(str, Enum):
    SELLER = "SELLER"
    BUYER_OBSERVATION = "BUYER_OBSERVATION"
    DOCUMENTED_EVIDENCE = "DOCUMENTED_EVIDENCE"
    THIRD_PARTY_REPORT = "THIRD_PARTY_REPORT"
    CARSPECTIVE_INFERENCE = "CARSPECTIVE_INFERENCE"


class EvidenceState(str, Enum):
    VERIFIED = "VERIFIED"
    SUPPORTED = "SUPPORTED"
    EMPIRICAL = "EMPIRICAL"
    MODEL_ESTIMATE = "MODEL_ESTIMATE"
    USER_STATED = "USER_STATED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    UNVERIFIED = "UNVERIFIED"
    DEPRECATED = "DEPRECATED"


class RiskCategory(str, Enum):
    DOCUMENTATION_RISK = "DOCUMENTATION_RISK"
    STRUCTURAL_RISK = "STRUCTURAL_RISK"
    POWERTRAIN_RISK = "POWERTRAIN_RISK"
    SAFETY_RISK = "SAFETY_RISK"
    CONDITION_RISK = "CONDITION_RISK"
    ODOMETER_RISK = "ODOMETER_RISK"
    OWNERSHIP_RISK = "OWNERSHIP_RISK"
    MAINTENANCE_RISK = "MAINTENANCE_RISK"
    DATA_QUALITY_RISK = "DATA_QUALITY_RISK"


class RiskSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class OverallInspectionStatus(str, Enum):
    CLEAR = "CLEAR"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    HIGH_RISK = "HIGH_RISK"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class PurchaseReadiness(str, Enum):
    READY_FOR_NEXT_STEP = "READY_FOR_NEXT_STEP"
    VERIFY_BEFORE_NEGOTIATING = "VERIFY_BEFORE_NEGOTIATING"
    PROFESSIONAL_INSPECTION_RECOMMENDED = "PROFESSIONAL_INSPECTION_RECOMMENDED"
    HIGH_RISK_DO_NOT_PROCEED_YET = "HIGH_RISK_DO_NOT_PROCEED_YET"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


# ────────────────────────────────────────────────────────────────────
# Request Models
# ────────────────────────────────────────────────────────────────────

class InspectionVehicleContext(BaseModel):
    """Canonical vehicle context for adaptive checklist generation."""
    brand: str = Field(..., min_length=1, description="Vehicle manufacturer (e.g. Tata, Hyundai, Maruti)")
    model: str = Field(..., min_length=1, description="Vehicle model (e.g. Nexon, Creta, Swift)")
    manufacturing_year: Optional[int] = Field(None, ge=1980, le=2026, description="Manufacturing year")
    fuel_type: Optional[str] = Field("Petrol", description="Petrol, Diesel, CNG, Electric, Hybrid")
    transmission_type: Optional[str] = Field("Manual", description="Manual, Automatic")
    variant: Optional[str] = Field(None, description="Trim variant if known")
    city: Optional[str] = Field("Delhi", description="Registration / inspection city")
    km_driven: Optional[float] = Field(None, ge=0, description="Odometer reading in kilometers")
    number_of_owners: Optional[int] = Field(1, ge=1, le=10, description="Previous owner count")
    service_history_status: Optional[str] = Field(None, description="FULL_SERVICE_HISTORY | PARTIAL | UNAVAILABLE | UNKNOWN")
    insurance_status: Optional[str] = Field(None, description="COMPREHENSIVE | THIRD_PARTY | EXPIRED | UNAVAILABLE")
    accident_history_status: Optional[str] = Field(None, description="NO_ACCIDENTS_REPORTED | MINOR_ACCIDENT | MAJOR_ACCIDENT | UNKNOWN")
    seller_type: Optional[str] = Field("INDIVIDUAL", description="INDIVIDUAL | DEALER | CERTIFIED_PLATFORM")

    @field_validator("brand", "model", "fuel_type", "transmission_type", "variant", "city")
    @classmethod
    def strip_whitespace(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v


class UserInspectionProfile(BaseModel):
    """User-stated priorities that modulate checklist prioritization (USER_STATED)."""
    safety_priority: Optional[str] = Field("HIGH", description="LOW | MEDIUM | HIGH | CRITICAL")
    daily_commute_km: Optional[float] = Field(30.0, ge=0, description="Daily commute distance in km")
    family_orientation: Optional[bool] = Field(True, description="Whether safety/comfort for family is primary")
    budget_sensitivity: Optional[str] = Field("MEDIUM", description="LOW | MEDIUM | HIGH")
    intended_ownership_years: Optional[int] = Field(5, ge=1, le=15, description="Planned years of ownership")


class InspectionListingContext(BaseModel):
    """Commercial listing details for contextual deal risk interpretation."""
    asking_price: Optional[float] = Field(None, gt=0, description="Seller asking price (INR)")
    negotiable: Optional[bool] = Field(True, description="Whether seller indicated price flexibility")


class FindingInput(BaseModel):
    """User- or inspector-supplied observation for a specific checklist item."""
    item_id: str = Field(..., description="Checklist item ID being reported")
    status: FindingStatus = Field(..., description="PASS | ATTENTION | FAIL | UNKNOWN | NOT_APPLICABLE")
    observation: Optional[str] = Field(None, description="Specific observed condition description")
    source: FindingSource = Field(FindingSource.BUYER_OBSERVATION, description="Source of the finding (BUYER_OBSERVATION, SELLER, etc.)")
    seller_claim: Optional[bool] = Field(False, description="Flag indicating if observation is based solely on seller statement")
    notes: Optional[str] = Field(None, description="Additional context or notes")


class InspectionRequest(BaseModel):
    """Top-level inspection intelligence request."""
    vehicle: InspectionVehicleContext = Field(..., description="Vehicle to be inspected")
    listing: Optional[InspectionListingContext] = Field(default_factory=InspectionListingContext, description="Optional commercial listing info")
    user_profile: Optional[UserInspectionProfile] = Field(default_factory=UserInspectionProfile, description="Optional user priorities")
    findings: Optional[List[FindingInput]] = Field(default_factory=list, description="Observed inspection findings")
    documentation_records: Optional[Dict[str, str]] = Field(default_factory=dict, description="Document verification statuses (e.g. {'rc': 'AVAILABLE', 'insurance': 'EXPIRED'})")


# ────────────────────────────────────────────────────────────────────
# Checklist & Finding Models
# ────────────────────────────────────────────────────────────────────

class ChecklistItem(BaseModel):
    """Structured checklist item definition."""
    item_id: str = Field(..., description="Unique machine-readable ID (e.g. DOC_RC_VERIFICATION)")
    category: InspectionCategory = Field(..., description="Inspection category")
    title: str = Field(..., description="Clear human-readable item title")
    purpose: str = Field(..., description="Explanation of why this inspection item matters")
    importance: ImportanceLevel = Field(..., description="CRITICAL | HIGH | MEDIUM | LOW")
    applicable_to: str = Field("ALL", description="Applicability condition (ALL, MANUAL, AUTOMATIC, DIESEL, CNG, EV, etc.)")
    inspection_method: str = Field(..., description="How to physically verify this item")
    expected_observation: str = Field(..., description="What normal/acceptable condition looks like")
    warning_signs: List[str] = Field(default_factory=list, description="Red flags or symptoms of concern")
    verification_action: str = Field(..., description="Concrete verification step to perform")
    evidence_required: str = Field(..., description="Document, physical check, or scan required")
    evidence_state: EvidenceState = Field(EvidenceState.SUPPORTED, description="Underlying domain evidence state")
    severity_if_failed: RiskSeverity = Field(RiskSeverity.MEDIUM, description="Potential risk severity if item fails")
    professional_inspection_required: bool = Field(False, description="Whether failure or anomaly warrants mechanic hoist inspection")
    source: str = Field("CarSpective Canonical Automotive Inspection Framework", description="Provenance citation")
    user_priority_elevated: bool = Field(False, description="Flag indicating item is elevated based on user context")
    notes: Optional[str] = Field(None, description="Additional technical guidance")


class InspectionFinding(BaseModel):
    """Evaluated inspection finding with evidence provenance."""
    finding_id: str = Field(..., description="Unique finding ID")
    item_id: str = Field(..., description="Associated checklist item ID")
    category: InspectionCategory = Field(..., description="Inspection category")
    title: str = Field(..., description="Item title")
    status: FindingStatus = Field(..., description="PASS | ATTENTION | FAIL | UNKNOWN | NOT_APPLICABLE")
    severity: RiskSeverity = Field(RiskSeverity.LOW, description="Severity of the finding")
    source: FindingSource = Field(..., description="Source of information (SELLER, BUYER_OBSERVATION, DOCUMENTED_EVIDENCE, etc.)")
    evidence_state: EvidenceState = Field(..., description="Evidence provenance (UNVERIFIED for seller, USER_STATED for buyer observation, VERIFIED for docs)")
    observation: str = Field(..., description="Observed condition narrative")
    interpretation: str = Field(..., description="Objective significance of what was observed")
    verification_action: str = Field(..., description="Actionable recommended next step")
    risk_effect: str = Field(..., description="Impact on deal, purchase safety, or cost")
    professional_inspection_required: bool = Field(False, description="Whether this finding triggers professional escalation")


# ────────────────────────────────────────────────────────────────────
# Risk & Document Verification Models
# ────────────────────────────────────────────────────────────────────

class InspectionRisk(BaseModel):
    """Structured inspection risk signal."""
    category: RiskCategory = Field(..., description="Risk dimension")
    severity: RiskSeverity = Field(..., description="CRITICAL | HIGH | MEDIUM | LOW")
    evidence_state: EvidenceState = Field(..., description="Evidence provenance state")
    title: str = Field(..., description="Risk title")
    explanation: str = Field(..., description="Detailed explanation of the risk")
    verification_action: str = Field(..., description="Recommended mitigation or verification action")


class DocumentationRequirement(BaseModel):
    """Required documentary evidence for buyer verification."""
    document_name: str = Field(..., description="Name of document (e.g. Registration Certificate (RC))")
    purpose: str = Field(..., description="Why this document is vital")
    importance: ImportanceLevel = Field(..., description="CRITICAL | HIGH | MEDIUM | LOW")
    status: str = Field("PENDING_VERIFICATION", description="VERIFIED | PENDING_VERIFICATION | MISSING | DISCREPANCY")
    verification_checks: List[str] = Field(default_factory=list, description="Specific checks on the document")
    consequence_if_missing: str = Field(..., description="Legal, financial, or mechanical risk if missing")


# ────────────────────────────────────────────────────────────────────
# Summary & Contextual Deal/Score Models
# ────────────────────────────────────────────────────────────────────

class InspectionSummary(BaseModel):
    """Deterministic summary of inspection status and findings."""
    overall_status: OverallInspectionStatus = Field(..., description="CLEAR | REVIEW_REQUIRED | HIGH_RISK | INSUFFICIENT_EVIDENCE")
    critical_findings_count: int = Field(0, description="Count of CRITICAL severity findings")
    high_risk_findings_count: int = Field(0, description="Count of HIGH severity findings")
    attention_items_count: int = Field(0, description="Count of ATTENTION items")
    unknown_items_count: int = Field(0, description="Count of UNKNOWN / unverified items")
    passed_items_count: int = Field(0, description="Count of confirmed PASS items")
    not_applicable_count: int = Field(0, description="Count of NOT_APPLICABLE items")
    total_applicable_items: int = Field(..., description="Total items in active checklist")
    documentation_completeness: str = Field(..., description="COMPLETE | PARTIAL | INSUFFICIENT | UNKNOWN")
    evidence_quality: str = Field(..., description="HIGH | MODERATE | LIMITED | INSUFFICIENT_DATA")
    professional_inspection_required: bool = Field(False, description="Flag indicating professional mechanic escalation is recommended")
    professional_inspection_reasons: List[str] = Field(default_factory=list, description="Concrete triggers for professional escalation")
    recommended_next_steps: List[str] = Field(default_factory=list, description="Sequential actionable guidance for the buyer")


class ContextualDealNote(BaseModel):
    """Deal context interpretation without mutating the underlying Phase 3 valuation."""
    asking_price: Optional[int] = Field(None, description="Seller asking price (INR)")
    deal_interpretation: str = Field(..., description="Contextual interpretation combining asking price and inspection findings")
    valuation_isolation_note: str = Field(
        "Underlying statistical fair market valuation remains strictly independent and is not altered by physical inspection findings.",
        description="Preservation of valuation integrity"
    )


class ContextualScoreNote(BaseModel):
    """Score context interpretation without mutating the underlying Phase 5 intrinsic score."""
    carspective_score: Optional[int] = Field(None, description="Intrinsic vehicle score (0-100)")
    condition_vs_intrinsic_distinction: str = Field(
        "CarSpective Score measures intrinsic vehicle ownership merit across the platform. Physical inspection findings reflect this individual vehicle's specific condition and do not alter the intrinsic score.",
        description="Preservation of score integrity"
    )
    purchase_readiness: PurchaseReadiness = Field(..., description="Deterministic purchase readiness verdict")


# ────────────────────────────────────────────────────────────────────
# Full Response Model
# ────────────────────────────────────────────────────────────────────

class InspectionResponse(BaseModel):
    """Complete inspection intelligence evaluation response payload."""
    session_id: str = Field(..., description="Unique inspection session ID")
    vehicle_summary: str = Field(..., description="Human-readable vehicle summary")
    canonical_vehicle_id: Optional[str] = Field(None, description="Canonical vehicle ID from taxonomy")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    checklist: List[ChecklistItem] = Field(..., description="Vehicle-aware adaptive inspection checklist")
    findings: List[InspectionFinding] = Field(default_factory=list, description="Evaluated findings with evidence provenance")
    risks: List[InspectionRisk] = Field(default_factory=list, description="Identified inspection risks across 9 dimensions")
    documentation_requirements: List[DocumentationRequirement] = Field(default_factory=list, description="Document verification checklist")
    summary: InspectionSummary = Field(..., description="Aggregated inspection summary")
    purchase_readiness: PurchaseReadiness = Field(..., description="READY_FOR_NEXT_STEP | VERIFY_BEFORE_NEGOTIATING | PROFESSIONAL_INSPECTION_RECOMMENDED | HIGH_RISK_DO_NOT_PROCEED_YET | INSUFFICIENT_EVIDENCE")
    deal_context: Optional[ContextualDealNote] = Field(None, description="Contextual deal interpretation")
    score_context: Optional[ContextualScoreNote] = Field(None, description="Contextual score interpretation")
    limitations: List[str] = Field(default_factory=list, description="Explicit disclosures, safety boundaries, and anti-hallucination disclaimers")
    computation_latency_ms: Optional[float] = Field(None, description="Execution latency in milliseconds")
