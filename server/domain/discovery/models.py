"""
CARspective — Phase 12: Discovery & Search Models
Typed deterministic search intent, result states, explainable match reasons,
provenance, clarification schemas, and autocomplete contracts.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class IntentFieldProvenance(str, Enum):
    USER_EXPLICIT = "USER_EXPLICIT"
    USER_INFERRED = "USER_INFERRED"
    SYSTEM_RESOLVED = "SYSTEM_RESOLVED"
    NOT_SPECIFIED = "NOT_SPECIFIED"

class IntentField(BaseModel):
    value: Any = None
    provenance: IntentFieldProvenance = IntentFieldProvenance.NOT_SPECIFIED
    confidence: float = 1.0
    raw_token: Optional[str] = None

class VehicleSearchIntent(BaseModel):
    raw_query: str = ""
    normalized_query: str = ""
    manufacturer: IntentField = Field(default_factory=IntentField)
    model: IntentField = Field(default_factory=IntentField)
    generation: IntentField = Field(default_factory=IntentField)
    model_year: IntentField = Field(default_factory=IntentField)
    variant: IntentField = Field(default_factory=IntentField)
    powertrain: IntentField = Field(default_factory=IntentField)
    fuel_type: IntentField = Field(default_factory=IntentField)
    transmission: IntentField = Field(default_factory=IntentField)
    body_type: IntentField = Field(default_factory=IntentField)
    budget_min: IntentField = Field(default_factory=IntentField)
    budget_max: IntentField = Field(default_factory=IntentField)
    seating_capacity: IntentField = Field(default_factory=IntentField)
    use_case: IntentField = Field(default_factory=IntentField)

class SearchResultType(str, Enum):
    EXACT_MATCH = "EXACT_MATCH"
    HIGH_CONFIDENCE_MATCH = "HIGH_CONFIDENCE_MATCH"
    AMBIGUOUS = "AMBIGUOUS"
    NO_MATCH = "NO_MATCH"
    FILTERED_RESULTS = "FILTERED_RESULTS"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"

class MatchReason(BaseModel):
    factor: str
    score_contribution: float
    description: str

class CandidateClarification(BaseModel):
    clarification_type: str  # "MULTIPLE_GENERATIONS", "MULTIPLE_VARIANTS", "SPELLING_AMBIGUITY"
    prompt: str
    options: List[Dict[str, Any]] = Field(default_factory=list)

class DiscoveryCandidate(BaseModel):
    canonical_vehicle_id: str
    title: str
    manufacturer: str
    model: str
    generation: str
    model_year: int
    variant: Optional[str] = None
    powertrain: Optional[str] = None
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    body_type: Optional[str] = None
    seating_capacity: Optional[int] = None
    coverage_tier: str = "TIER_1"
    evidence_state: str = "SUPPORTED"
    has_deep_knowledge: bool = False
    match_score: float = Field(ge=0.0, le=100.0)
    match_reasons: List[MatchReason] = Field(default_factory=list)
    available_actions: List[str] = Field(default_factory=lambda: ["view", "compare", "value", "deal", "inspect"])

class SearchProvenance(BaseModel):
    query_normalized: str = ""
    rules_applied: List[str] = Field(default_factory=list)
    taxonomy_version: str = "Phase 2 Canonical Taxonomy"
    resolution_method: str = "Deterministic Pattern Matching & Taxonomy Graph"
    evidence_sources_checked: int = 12

class DiscoveryFilterParams(BaseModel):
    q: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    generation: Optional[str] = None
    variant: Optional[str] = None
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    body_type: Optional[str] = None
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    seating_capacity: Optional[int] = None
    score_min: Optional[float] = None
    limit: int = 20
    offset: int = 0

class DiscoverySearchResponse(BaseModel):
    query: str
    intent: VehicleSearchIntent
    result_type: SearchResultType
    total_count: int
    results: List[DiscoveryCandidate] = Field(default_factory=list)
    clarification: Optional[CandidateClarification] = None
    suggestions: List[str] = Field(default_factory=list)
    provenance: SearchProvenance = Field(default_factory=SearchProvenance)

class AutocompleteItem(BaseModel):
    id: str
    title: str
    type: str  # "manufacturer", "model", "vehicle", "use_case"
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    canonical_vehicle_id: Optional[str] = None
    subtitle: Optional[str] = None

class AutocompleteResponse(BaseModel):
    query: str
    items: List[AutocompleteItem] = Field(default_factory=list)
