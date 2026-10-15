"""
CARspective — Evidence Repository
Encapsulates all database operations for EvidenceSources, KnowledgeClaims, and Provenance Mappings.
"""

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from server.models.evidence import (
    EvidenceSource,
    KnowledgeClaim,
    ClaimEvidenceMapping,
    EvidenceState,
)

class EvidenceRepository:
    def __init__(self, session: Optional[Session] = None):
        self._session = session

    @property
    def session(self) -> Session:
        if self._session is not None:
            return self._session
        from server.infrastructure.database import ScopedSession
        return ScopedSession()

    @session.setter
    def session(self, value: Optional[Session]) -> None:
        self._session = value

    def get_source(self, source_id: str) -> Optional[EvidenceSource]:
        stmt = select(EvidenceSource).where(EvidenceSource.id == source_id)
        return self.session.scalars(stmt).first()

    def list_sources(self) -> List[EvidenceSource]:
        stmt = select(EvidenceSource).order_by(EvidenceSource.organization_name)
        return list(self.session.scalars(stmt).all())

    def get_claims_for_vehicle(
        self,
        canonical_vehicle_id: str,
        category: Optional[str] = None
    ) -> List[KnowledgeClaim]:
        # Support hierarchical claim inheritance from model and generation up to full variant
        parts = canonical_vehicle_id.split("::")
        prefixes = ["::".join(parts[:i]) for i in range(2, len(parts) + 1)] if len(parts) >= 2 else [canonical_vehicle_id]

        stmt = select(KnowledgeClaim).options(
            joinedload(KnowledgeClaim.evidence_mappings).joinedload(ClaimEvidenceMapping.source)
        ).where(
            KnowledgeClaim.canonical_vehicle_id.in_(prefixes)
        )
        if category:
            stmt = stmt.where(KnowledgeClaim.attribute_category == category.upper())
        return list(self.session.scalars(stmt).unique().all())

    def add_source(self, source: EvidenceSource) -> EvidenceSource:
        self.session.add(source)
        self.session.commit()
        return source

    def add_claim(self, claim: KnowledgeClaim) -> KnowledgeClaim:
        self.session.add(claim)
        self.session.commit()
        return claim

    def link_claim_to_source(self, claim_id: str, source_id: str, note: Optional[str] = None) -> ClaimEvidenceMapping:
        mapping = ClaimEvidenceMapping(
            claim_id=claim_id,
            source_id=source_id,
            citation_note=note
        )
        self.session.add(mapping)
        self.session.commit()
        return mapping
