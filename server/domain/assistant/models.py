"""
CARspective — Phase 8 Grounded Automotive AI Assistant Models
Defines strongly typed schemas for intent classification, evidence bundles,
assistant contexts, session turns, request/response contracts, and domain authority.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator, model_validator, computed_field


# ────────────────────────────────────────────────────────────────────
# Canonical Intents & Evidence Enums
# ────────────────────────────────────────────────────────────────────

class AssistantIntent(str, Enum):
    """Canonical automotive query intents supported by the CarSpective Assistant."""
    VEHICLE_OVERVIEW = "VEHICLE_OVERVIEW"
    SPECIFICATION = "SPECIFICATION"
    VALUATION = "VALUATION"
    DEAL_ANALYSIS = "DEAL_ANALYSIS"
    NEGOTIATION = "NEGOTIATION"
    RECOMMENDATION = "RECOMMENDATION"
    COMPARISON = "COMPARISON"
    INSPECTION = "INSPECTION"
    RISK = "RISK"
    OWNERSHIP = "OWNERSHIP"
    MARKET = "MARKET"
    SCORE = "SCORE"
    ALTERNATIVES = "ALTERNATIVES"
    EVIDENCE = "EVIDENCE"
    EXPLANATION = "EXPLANATION"
    UNKNOWN = "UNKNOWN"


class AssistantEvidenceState(str, Enum):
    """Evidence provenance states matching CarSpective canonical governance."""
    VERIFIED = "VERIFIED"
    SUPPORTED = "SUPPORTED"
    EMPIRICAL = "EMPIRICAL"
    MODEL_ESTIMATE = "MODEL_ESTIMATE"
    USER_STATED = "USER_STATED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    UNVERIFIED = "UNVERIFIED"
    DEPRECATED = "DEPRECATED"


class SourceDomain(str, Enum):
    """Authoritative source domain ownership boundaries."""
    TAXONOMY = "TAXONOMY"
    VALUATION = "VALUATION"
    DEAL_ANALYZER = "DEAL_ANALYZER"
    SCORE = "SCORE"
    RECOMMENDATION = "RECOMMENDATION"
    COMPARISON = "COMPARISON"
    INSPECTION = "INSPECTION"
    EVIDENCE_STORE = "EVIDENCE_STORE"
    USER_INPUT = "USER_INPUT"
    GENERAL_KNOWLEDGE = "GENERAL_KNOWLEDGE"


# ────────────────────────────────────────────────────────────────────
# Context Inputs
# ────────────────────────────────────────────────────────────────────

class VehicleContextInput(BaseModel):
    """Structured vehicle identity context for automotive assistant queries."""
    brand: str = Field(..., min_length=1, description="Vehicle manufacturer (e.g. Maruti, Honda, Hyundai)")
    model: str = Field(..., min_length=1, description="Vehicle model (e.g. City, Creta, Swift)")
    manufacturing_year: Optional[int] = Field(None, ge=1980, le=2026, description="Manufacturing model year")
    variant: Optional[str] = Field(None, description="Trim variant if known (e.g. V, SX, ZXi)")
    fuel_type: Optional[str] = Field("Petrol", description="Fuel type (Petrol, Diesel, CNG, Electric, Hybrid)")
    transmission_type: Optional[str] = Field("Manual", description="Transmission (Manual, Automatic)")
    city: Optional[str] = Field("Delhi", description="City for valuation/inspection context")
    km_driven: Optional[float] = Field(None, ge=0, description="Odometer mileage in km")
    number_of_owners: Optional[int] = Field(1, ge=1, le=10, description="Previous owner count")
    canonical_vehicle_id: Optional[str] = Field(None, description="Pre-resolved canonical vehicle ID")

    @field_validator("brand", "model", "variant", "fuel_type", "transmission_type", "city")
    @classmethod
    def strip_whitespace(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v


class ListingContextInput(BaseModel):
    """Commercial listing details accompanying vehicle context."""
    asking_price: Optional[float] = Field(None, gt=0, description="Seller asking price in INR")
    negotiable: Optional[bool] = Field(True, description="Whether price is stated as negotiable")
    seller_type: Optional[str] = Field("INDIVIDUAL", description="INDIVIDUAL | DEALER | CERTIFIED_PLATFORM")


class UserProfileInput(BaseModel):
    """User preferences modulating explanations and recommendations."""
    budget_max: Optional[float] = Field(None, gt=0, description="Maximum budget in INR")
    safety_priority: Optional[str] = Field("HIGH", description="LOW | MEDIUM | HIGH | CRITICAL")
    daily_commute_km: Optional[float] = Field(30.0, ge=0, description="Daily commute distance in km")
    family_orientation: Optional[bool] = Field(True, description="Family safety/space orientation")
    intended_ownership_years: Optional[int] = Field(5, ge=1, le=15, description="Planned years of ownership")
    risk_tolerance: Optional[str] = Field("MODERATE", description="CONSERVATIVE | MODERATE | AGGRESSIVE")


# ────────────────────────────────────────────────────────────────────
# Evidence Bundle Models
# ────────────────────────────────────────────────────────────────────

class EvidenceItem(BaseModel):
    """An individual structured piece of evidence from a deterministic domain engine."""
    id: str = Field(..., description="Unique evidence reference ID (e.g. valuation.fair_market_value)")
    claim: str = Field(..., description="Clear human-readable claim description")
    value: Any = Field(..., description="Authoritative factual value from domain engine")
    source: str = Field(..., description="Originating domain engine or component")
    evidence_state: AssistantEvidenceState = Field(
        AssistantEvidenceState.EMPIRICAL,
        description="Provenance state (VERIFIED, MODEL_ESTIMATE, EMPIRICAL, etc.)"
    )
    domain: SourceDomain = Field(..., description="Authoritative domain boundary owning this claim")
    confidence: Optional[str] = Field(None, description="Confidence level or rating where applicable")
    applicability: Optional[str] = Field(None, description="Applicability condition or scope")
    notes: Optional[str] = Field(None, description="Additional context or limitations")


class EvidenceBundle(BaseModel):
    """Collection of structured evidence items retrieved for the current user query."""
    items: List[EvidenceItem] = Field(default_factory=list, description="Structured factual evidence items")
    referenced_domains: List[str] = Field(default_factory=list, description="Domain engines contributing evidence")
    missing_evidence: List[str] = Field(default_factory=list, description="Key evidence items currently unavailable")
    uncertainty_disclosures: List[str] = Field(default_factory=list, description="Explicit disclosures of epistemic gaps")

    def add_item(self, item: EvidenceItem) -> None:
        self.items.append(item)
        domain_str = item.domain.value if isinstance(item.domain, SourceDomain) else str(item.domain)
        if domain_str not in self.referenced_domains:
            self.referenced_domains.append(domain_str)

    def get_by_id(self, item_id: str) -> Optional[EvidenceItem]:
        for it in self.items:
            if it.id == item_id:
                return it
        return None

    def get_value(self, item_id: str, default: Any = None) -> Any:
        it = self.get_by_id(item_id)
        return it.value if it else default


# ────────────────────────────────────────────────────────────────────
# Conversation History & Session Context
# ────────────────────────────────────────────────────────────────────

class ConversationTurn(BaseModel):
    """A single turn in the assistant conversation."""
    role: str = Field(..., description="'user' | 'assistant'")
    content: str = Field(..., description="Text content of the message")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO timestamp"
    )
    intent: Optional[AssistantIntent] = Field(None, description="Detected intent for user turn")
    evidence_refs: Optional[List[str]] = Field(default_factory=list, description="Citations used in assistant turn")


class AssistantContext(BaseModel):
    """Persisted session state for conversational continuity across turns."""
    session_id: str = Field(..., description="Unique ephemeral session identifier")
    current_vehicle: Optional[VehicleContextInput] = Field(None, description="Active vehicle under discussion")
    compared_vehicles: List[VehicleContextInput] = Field(default_factory=list, description="Vehicles under comparison")
    listing: Optional[ListingContextInput] = Field(None, description="Active listing context")
    user_profile: Optional[UserProfileInput] = Field(None, description="Active user profile")
    conversation_history: List[ConversationTurn] = Field(default_factory=list, description="Recent conversation turns")
    last_intent: Optional[AssistantIntent] = Field(None, description="Most recent intent detected")
    cached_valuation: Optional[Dict[str, Any]] = Field(None, description="Cached Phase 3 valuation result")
    cached_deal: Optional[Dict[str, Any]] = Field(None, description="Cached Phase 4 deal analysis result")
    cached_score: Optional[Dict[str, Any]] = Field(None, description="Cached Phase 5 score result")
    cached_recommendation: Optional[Dict[str, Any]] = Field(None, description="Cached Phase 5 recommendation result")
    cached_comparison: Optional[Dict[str, Any]] = Field(None, description="Cached Phase 6 comparison result")
    cached_inspection: Optional[Dict[str, Any]] = Field(None, description="Cached Phase 7 inspection result")
    created_at: float = Field(default_factory=lambda: datetime.now(timezone.utc).timestamp())
    last_accessed_at: float = Field(default_factory=lambda: datetime.now(timezone.utc).timestamp())


# ────────────────────────────────────────────────────────────────────
# API Request & Response Contracts
# ────────────────────────────────────────────────────────────────────

class AssistantRequest(BaseModel):
    """Incoming user message and optional context for assistant explanation."""
    message: str = Field(..., min_length=1, max_length=2000, description="User question or statement")
    session_id: Optional[str] = Field(None, description="Optional existing session ID for continuity")
    vehicle: Optional[VehicleContextInput] = Field(None, description="Optional vehicle context if provided in UI")
    compared_vehicles: Optional[List[VehicleContextInput]] = Field(
        default=None,
        description="Optional vehicles for comparison queries"
    )
    listing: Optional[ListingContextInput] = Field(None, description="Optional listing pricing/seller info")
    user_profile: Optional[UserProfileInput] = Field(None, description="Optional buyer preferences")
    conversation_history: Optional[List[ConversationTurn]] = Field(
        default=None,
        description="Optional client-provided conversation history"
    )

    @model_validator(mode="before")
    @classmethod
    def handle_legacy_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Create a shallow copy so caller-owned dictionaries are never mutated
            data = dict(data)

            # 1. Map legacy 'query' to 'message' if 'message' is absent or None
            if not data.get("message") and data.get("query"):
                data["message"] = data["query"]

            # 2. Map legacy 'context_vehicle' to 'vehicle' and 'listing' if absent or None
            if not data.get("vehicle") and data.get("context_vehicle"):
                cv = data.get("context_vehicle")
                if isinstance(cv, dict):
                    v_dict = {}
                    if cv.get("brand"):
                        v_dict["brand"] = cv["brand"]
                    if cv.get("model"):
                        v_dict["model"] = cv["model"]
                    if cv.get("year") and not cv.get("manufacturing_year"):
                        v_dict["manufacturing_year"] = cv["year"]
                    elif cv.get("manufacturing_year"):
                        v_dict["manufacturing_year"] = cv["manufacturing_year"]
                    if cv.get("variant"):
                        v_dict["variant"] = cv["variant"]
                    if cv.get("fuel_type"):
                        v_dict["fuel_type"] = cv["fuel_type"]
                    if cv.get("transmission_type"):
                        v_dict["transmission_type"] = cv["transmission_type"]
                    if cv.get("km_driven") is not None:
                        v_dict["km_driven"] = cv["km_driven"]
                    if cv.get("canonical_id") and not cv.get("canonical_vehicle_id"):
                        v_dict["canonical_vehicle_id"] = cv["canonical_id"]
                    elif cv.get("canonical_vehicle_id"):
                        v_dict["canonical_vehicle_id"] = cv["canonical_vehicle_id"]

                    if v_dict.get("brand") and v_dict.get("model"):
                        data["vehicle"] = v_dict

                    if cv.get("asking_price") is not None and not data.get("listing"):
                        try:
                            data["listing"] = {"asking_price": float(cv["asking_price"])}
                        except (ValueError, TypeError):
                            pass

            # 3. Map legacy 'comparison_vehicles' to 'compared_vehicles' if absent or None
            if not data.get("compared_vehicles") and data.get("comparison_vehicles"):
                cv_list = data.get("comparison_vehicles")
                if isinstance(cv_list, list):
                    mapped_list = []
                    for cv in cv_list:
                        if isinstance(cv, dict) and cv.get("brand") and cv.get("model"):
                            mapped_list.append({
                                "brand": cv["brand"],
                                "model": cv["model"],
                                "manufacturing_year": cv.get("manufacturing_year") or cv.get("year"),
                                "variant": cv.get("variant"),
                                "fuel_type": cv.get("fuel_type") or "Petrol",
                                "transmission_type": cv.get("transmission_type") or "Manual",
                                "km_driven": cv.get("km_driven"),
                                "canonical_vehicle_id": cv.get("canonical_id") or cv.get("canonical_vehicle_id"),
                            })
                    if mapped_list:
                        data["compared_vehicles"] = mapped_list

        return data


class AssistantResponse(BaseModel):
    """Authoritative, evidence-grounded response from CarSpective Assistant."""
    session_id: str = Field(..., description="Session identifier for context continuation")
    answer: str = Field(..., description="Clear, conversational, evidence-grounded explanation")
    intent: AssistantIntent = Field(..., description="Classified intent of the user inquiry")
    referenced_domains: List[str] = Field(..., description="CarSpective domain engines providing evidence")
    evidence_refs: List[str] = Field(..., description="Citations to specific structured evidence IDs")
    evidence_bundle: List[EvidenceItem] = Field(
        default_factory=list,
        description="Complete structured evidence items used to formulate the answer"
    )
    uncertainty: Optional[str] = Field(
        None,
        description="Explicit disclosure of missing information, limitations, or unverified claims"
    )
    suggested_next_actions: List[str] = Field(
        default_factory=list,
        description="Concrete recommended next verification or negotiation steps"
    )
    session_context_updates: Dict[str, Any] = Field(
        default_factory=dict,
        description="Updates to the active session state (e.g. established vehicle context)"
    )
    disclaimer: str = Field(
        "The CarSpective AI Assistant is an evidence-constrained automotive explainer. It does not independently calculate valuation, scores, recommendations, comparisons, or inspection conclusions.",
        description="Standard CarSpective governance disclaimer"
    )

    @computed_field
    @property
    def citations(self) -> List[EvidenceItem]:
        """Backward-compatibility alias for evidence_bundle."""
        return self.evidence_bundle

    @computed_field
    @property
    def source_domains_queried(self) -> List[str]:
        """Backward-compatibility alias for referenced_domains."""
        return self.referenced_domains
