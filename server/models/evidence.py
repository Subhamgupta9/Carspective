"""
CARspective — Evidence & Provenance Models
Supports exact Phase 1.2 evidence states:
VERIFIED, SUPPORTED, EMPIRICAL, MODEL_ESTIMATE, INSUFFICIENT_DATA, UNVERIFIED, DEPRECATED
"""

import enum
import uuid
from datetime import datetime, date, timezone
from typing import Optional, List
from sqlalchemy import String, Text, Float, Date, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin

class EvidenceState(str, enum.Enum):
    VERIFIED = "VERIFIED"
    SUPPORTED = "SUPPORTED"
    EMPIRICAL = "EMPIRICAL"
    MODEL_ESTIMATE = "MODEL_ESTIMATE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    UNVERIFIED = "UNVERIFIED"
    DEPRECATED = "DEPRECATED"

class OrganizationType(str, enum.Enum):
    SAFETY_AGENCY = "SAFETY_AGENCY"
    REGULATORY_BODY = "REGULATORY_BODY"
    OEM_MANUFACTURER = "OEM_MANUFACTURER"
    EMPIRICAL_DATASET = "EMPIRICAL_DATASET"
    INDUSTRY_AUDIT = "INDUSTRY_AUDIT"
    OTHER = "OTHER"

class HierarchyLevel(str, enum.Enum):
    MANUFACTURER = "MANUFACTURER"
    MODEL = "MODEL"
    GENERATION = "GENERATION"
    MODEL_YEAR = "MODEL_YEAR"
    VARIANT = "VARIANT"
    POWERTRAIN = "POWERTRAIN"

class EvidenceSource(Base, TimestampMixin):
    __tablename__ = "evidence_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_name: Mapped[str] = mapped_column(String(150), nullable=False)
    organization_type: Mapped[OrganizationType] = mapped_column(SQLEnum(OrganizationType), nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    reference_document: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    published_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    valid_from: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    valid_until: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    verification_status: Mapped[EvidenceState] = mapped_column(
        SQLEnum(EvidenceState),
        default=EvidenceState.VERIFIED,
        nullable=False
    )
    confidence_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    claim_mappings: Mapped[List["ClaimEvidenceMapping"]] = relationship(
        "ClaimEvidenceMapping",
        back_populates="source",
        cascade="all, delete-orphan"
    )

    def is_currently_valid(self) -> bool:
        today = date.today()
        if self.valid_from and today < self.valid_from:
            return False
        if self.valid_until and today > self.valid_until:
            return False
        return self.verification_status != EvidenceState.DEPRECATED

class KnowledgeClaim(Base, TimestampMixin):
    __tablename__ = "knowledge_claims"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    canonical_vehicle_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    hierarchy_level: Mapped[HierarchyLevel] = mapped_column(SQLEnum(HierarchyLevel), nullable=False)
    
    attribute_category: Mapped[str] = mapped_column(String(50), nullable=False) # SAFETY, RELIABILITY, MAINTENANCE, SPEC
    attribute_key: Mapped[str] = mapped_column(String(100), nullable=False)
    claim_value: Mapped[str] = mapped_column(Text, nullable=False)
    
    evidence_state: Mapped[EvidenceState] = mapped_column(
        SQLEnum(EvidenceState),
        default=EvidenceState.UNVERIFIED,
        nullable=False
    )
    
    valid_from: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    valid_until: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    verification_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    evidence_mappings: Mapped[List["ClaimEvidenceMapping"]] = relationship(
        "ClaimEvidenceMapping",
        back_populates="claim",
        cascade="all, delete-orphan"
    )

class ClaimEvidenceMapping(Base):
    __tablename__ = "claim_evidence_mappings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    claim_id: Mapped[str] = mapped_column(String(36), ForeignKey("knowledge_claims.id", ondelete="CASCADE"), nullable=False)
    source_id: Mapped[str] = mapped_column(String(36), ForeignKey("evidence_sources.id", ondelete="CASCADE"), nullable=False)
    citation_note: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    claim: Mapped["KnowledgeClaim"] = relationship("KnowledgeClaim", back_populates="evidence_mappings")
    source: Mapped["EvidenceSource"] = relationship("EvidenceSource", back_populates="claim_mappings")
