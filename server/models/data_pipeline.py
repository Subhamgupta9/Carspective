"""
CARspective — Data Pipeline & Ingestion Audit SQLAlchemy Models
Supports controlled, auditable two-phase ingestion batches and quality reports.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import String, Text, Float, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin

class IngestionBatch(Base, TimestampMixin):
    __tablename__ = "ingestion_batches"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    ingestion_timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    source_snapshot_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    record_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    accepted_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rejected_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    validation_status: Mapped[str] = mapped_column(String(32), default="PASSED", nullable=False) # PASSED, PARTIAL_FAILURE, FAILED
    normalization_status: Mapped[str] = mapped_column(String(32), default="COMPLETED", nullable=False)
    canonical_mapping_status: Mapped[str] = mapped_column(String(32), default="COMPLETED", nullable=False)
    
    checksum: Mapped[str] = mapped_column(String(64), nullable=False) # SHA-256 of raw data payload
    processing_duration_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    commit_status: Mapped[str] = mapped_column(String(32), default="STAGED", nullable=False) # STAGED, COMMITTED, ROLLED_BACK
    
    error_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    records: Mapped[List["IngestionRecord"]] = relationship(
        "IngestionRecord",
        back_populates="batch",
        cascade="all, delete-orphan"
    )

class IngestionRecord(Base):
    __tablename__ = "ingestion_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    batch_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("ingestion_batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    record_index: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_payload: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_vehicle_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    mapping_outcome: Mapped[str] = mapped_column(String(32), nullable=False) # EXACT_MATCH, SAFE_ALIAS_MATCH, AMBIGUOUS, UNMAPPED, REJECTED
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    rejection_reasons: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # JSON serialized errors
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    batch: Mapped["IngestionBatch"] = relationship("IngestionBatch", back_populates="records")

class DataQualityReportModel(Base):
    __tablename__ = "data_quality_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    batch_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    dataset_name: Mapped[str] = mapped_column(String(100), nullable=False)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False) # 0.0 - 1.0
    quality_status: Mapped[str] = mapped_column(String(32), nullable=False) # EXCELLENT, GOOD, MARGINAL, POOR
    metrics_json: Mapped[str] = mapped_column(Text, nullable=False) # Full JSON metrics breakdown
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
