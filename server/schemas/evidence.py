"""
CARspective — Evidence & Provenance Pydantic v2 Schemas
"""

from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field
from server.models.evidence import EvidenceState, OrganizationType, HierarchyLevel

class EvidenceSourceBase(BaseModel):
    organization_name: str
    organization_type: OrganizationType
    source_url: Optional[str] = None
    reference_document: Optional[str] = None
    published_at: Optional[date] = None
    valid_from: Optional[date] = None
    valid_until: Optional[date] = None
    verification_status: EvidenceState = EvidenceState.VERIFIED
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    payload_hash: str

class EvidenceSourceSchema(EvidenceSourceBase):
    id: str
    retrieved_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class KnowledgeClaimBase(BaseModel):
    canonical_vehicle_id: str
    hierarchy_level: HierarchyLevel
    attribute_category: str
    attribute_key: str
    claim_value: str
    evidence_state: EvidenceState
    valid_from: Optional[date] = None
    valid_until: Optional[date] = None
    verification_notes: Optional[str] = None

class KnowledgeClaimSchema(KnowledgeClaimBase):
    id: str
    sources: List[EvidenceSourceSchema] = []
    
    model_config = ConfigDict(from_attributes=True)

class EvidenceProvenanceResponse(BaseModel):
    canonical_vehicle_id: str
    total_claims: int
    claims: List[KnowledgeClaimSchema]
