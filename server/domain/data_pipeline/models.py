"""
CARspective — Data Pipeline & Evidence Intelligence Pydantic Models & Enums
Defines types for source registry, freshness policies, validation gates, canonical mapping,
data quality scoring, and evidence lineage.
"""

import enum
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

class SourceType(str, enum.Enum):
    MANUFACTURER = "MANUFACTURER"
    GOVERNMENT_AUTHORITY = "GOVERNMENT_AUTHORITY"
    SAFETY_ORGANIZATION = "SAFETY_ORGANIZATION"
    HISTORICAL_DATASET = "HISTORICAL_DATASET"
    MARKET_LISTING_SOURCE = "MARKET_LISTING_SOURCE"
    RESEARCH_PUBLICATION = "RESEARCH_PUBLICATION"
    EXPERT_SOURCE = "EXPERT_SOURCE"
    INTERNAL_EMPIRICAL_DATASET = "INTERNAL_EMPIRICAL_DATASET"

class ReliabilityClassification(str, enum.Enum):
    AUTHORITATIVE = "AUTHORITATIVE"
    REGULATORY_BENCHMARK = "REGULATORY_BENCHMARK"
    EMPIRICAL_OBSERVATION = "EMPIRICAL_OBSERVATION"
    INDUSTRY_AUDIT = "INDUSTRY_AUDIT"
    COMMUNITY_ESTIMATE = "COMMUNITY_ESTIMATE"
    UNVERIFIED = "UNVERIFIED"

class FreshnessState(str, enum.Enum):
    CURRENT = "CURRENT"
    REVIEW_DUE = "REVIEW_DUE"
    STALE = "STALE"
    DEPRECATED = "DEPRECATED"
    UNKNOWN = "UNKNOWN"

class MappingOutcome(str, enum.Enum):
    EXACT_MATCH = "EXACT_MATCH"
    SAFE_ALIAS_MATCH = "SAFE_ALIAS_MATCH"
    AMBIGUOUS = "AMBIGUOUS"
    UNMAPPED = "UNMAPPED"
    REJECTED = "REJECTED"

class BatchValidationStatus(str, enum.Enum):
    PASSED = "PASSED"
    PARTIAL_FAILURE = "PARTIAL_FAILURE"
    FAILED = "FAILED"

class BatchCommitStatus(str, enum.Enum):
    STAGED = "STAGED"
    COMMITTED = "COMMITTED"
    ROLLED_BACK = "ROLLED_BACK"

class DataQualityStatus(str, enum.Enum):
    EXCELLENT = "EXCELLENT"
    GOOD = "GOOD"
    MARGINAL = "MARGINAL"
    POOR = "POOR"

class FreshnessPolicy(BaseModel):
    policy_id: str
    name: str
    target_domain: str
    max_current_days: int
    review_due_days: int
    stale_threshold_days: int
    description: str

class FreshnessEvaluation(BaseModel):
    status: FreshnessState
    age_days: Optional[int] = None
    observation_period: Optional[str] = None
    last_observed: Optional[str] = None
    review_due_date: Optional[str] = None
    policy_id: str
    notes: str

class GovernedSource(BaseModel):
    source_id: str
    source_name: str
    source_type: SourceType
    publisher_organization: str
    source_url: Optional[str] = None
    reference_document: Optional[str] = None
    jurisdiction: str = "IN"
    coverage: str
    collection_method: str
    first_seen: str
    last_seen: str
    freshness_policy_id: str
    reliability_classification: ReliabilityClassification
    license_status: Optional[str] = None
    is_active: bool = True
    deprecated_at: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class ValidationFailure(BaseModel):
    record_index: int
    field_name: str
    error_code: str
    error_message: str
    raw_value: Optional[str] = None

class CanonicalMappingResult(BaseModel):
    outcome: MappingOutcome
    input_make: str
    input_model: str
    input_variant: Optional[str] = None
    input_year: Optional[int] = None
    canonical_vehicle_id: Optional[str] = None
    resolution_notes: str
    candidate_matches: List[str] = Field(default_factory=list)

class IngestionBatchMetadata(BaseModel):
    batch_id: str
    source_id: str
    ingestion_timestamp: str
    source_snapshot_reference: Optional[str] = None
    record_count: int
    accepted_count: int
    rejected_count: int
    validation_status: BatchValidationStatus
    normalization_status: str
    canonical_mapping_status: str
    checksum: str
    processing_duration_ms: float
    commit_status: BatchCommitStatus
    error_summary: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)

class DataQualityReport(BaseModel):
    completeness_score: float = Field(..., ge=0.0, le=1.0)
    validity_score: float = Field(..., ge=0.0, le=1.0)
    uniqueness_score: float = Field(..., ge=0.0, le=1.0)
    canonical_mapping_coverage: float = Field(..., ge=0.0, le=1.0)
    freshness_score: float = Field(..., ge=0.0, le=1.0)
    provenance_coverage: float = Field(..., ge=0.0, le=1.0)
    consistency_score: float = Field(..., ge=0.0, le=1.0)
    overall_quality_score: float = Field(..., ge=0.0, le=1.0)
    status: DataQualityStatus
    total_records: int
    invalid_records: int
    duplicate_records: int
    unmapped_records: int
    timestamp: str

class EvidenceLineageNode(BaseModel):
    claim_id: str
    canonical_vehicle_id: str
    attribute_category: str
    attribute_key: str
    claim_value: str
    evidence_state: str
    freshness: FreshnessEvaluation
    sources: List[GovernedSource]
    applicable_vehicle_scope: str
    product_surfaces: List[str]
    lineage_path: str

class DomainFreshnessSummary(BaseModel):
    domain: str
    policy_id: str
    current_count: int
    review_due_count: int
    stale_count: int
    deprecated_count: int
    unknown_count: int
    total_items: int
    dominant_status: FreshnessState
    evaluation_notes: str
