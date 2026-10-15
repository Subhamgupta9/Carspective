"""
CARspective — Evidence Domain Service
Manages factual provenance, citation verification, and evidence state enforcement.
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from server.repositories.evidence_repository import EvidenceRepository
from server.schemas.evidence import (
    EvidenceSourceSchema,
    KnowledgeClaimSchema,
    EvidenceProvenanceResponse,
)
from server.models.evidence import EvidenceState, HierarchyLevel, KnowledgeClaim, EvidenceSource

class EvidenceService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = EvidenceRepository(session)

    def list_sources(self) -> List[EvidenceSourceSchema]:
        sources = self.repo.list_sources()
        return [EvidenceSourceSchema.model_validate(s) for s in sources]

    def get_provenance_for_vehicle(
        self,
        canonical_vehicle_id: str,
        category: Optional[str] = None
    ) -> EvidenceProvenanceResponse:
        claims = self.repo.get_claims_for_vehicle(canonical_vehicle_id, category=category)
        claim_schemas = []
        for c in claims:
            # Resolve sources linked via mappings
            linked_sources = [
                EvidenceSourceSchema.model_validate(m.source)
                for m in c.evidence_mappings
                if m.source
            ]
            claim_schemas.append(
                KnowledgeClaimSchema(
                    id=c.id,
                    canonical_vehicle_id=c.canonical_vehicle_id,
                    hierarchy_level=c.hierarchy_level,
                    attribute_category=c.attribute_category,
                    attribute_key=c.attribute_key,
                    claim_value=c.claim_value,
                    evidence_state=c.evidence_state,
                    valid_from=c.valid_from,
                    valid_until=c.valid_until,
                    verification_notes=c.verification_notes,
                    sources=linked_sources
                )
            )

        return EvidenceProvenanceResponse(
            canonical_vehicle_id=canonical_vehicle_id,
            total_claims=len(claim_schemas),
            claims=claim_schemas
        )
