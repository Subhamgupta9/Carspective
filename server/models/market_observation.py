"""
CARspective — Current Market Observation SQLAlchemy Model
Stores auditable, governed current-market vehicle observations.
Maintains raw lineage, data quality flags, deduplication status, and analytical eligibility.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Text, Float, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, TimestampMixin


class CurrentMarketObservation(Base, TimestampMixin):
    __tablename__ = "current_market_observations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_record_reference: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    
    observed_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    canonical_vehicle_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    observation_type: Mapped[str] = mapped_column(String(32), default="CURRENT_LISTING", nullable=False)
    
    # Financial & Vehicle State (Seller Asking Baseline)
    asking_price: Mapped[float] = mapped_column(Float, nullable=False)
    model_year: Mapped[int] = mapped_column(Integer, nullable=False)
    mileage: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Geographic Context (Never PII)
    location_city: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    location_region: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    
    # Classification Metadata
    seller_type: Mapped[str] = mapped_column(String(32), default="DEALER", nullable=False)
    transmission: Mapped[str] = mapped_column(String(32), default="Manual", nullable=False)
    fuel_type: Mapped[str] = mapped_column(String(32), default="Petrol", nullable=False)
    body_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    listing_status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)
    
    # Provenance & Lineage
    source_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    evidence_state: Mapped[str] = mapped_column(String(32), default="EMPIRICAL", nullable=False)
    freshness_state: Mapped[str] = mapped_column(String(32), default="CURRENT", nullable=False)
    
    ingestion_batch_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True
    )
    data_quality_status: Mapped[str] = mapped_column(String(32), default="GOOD", nullable=False)
    
    # Deduplication Signals
    duplicate_status: Mapped[str] = mapped_column(String(32), default="DISTINCT", nullable=False) # DISTINCT, EXACT_DUPLICATE, PROBABLE_DUPLICATE
    duplicate_of_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    
    # Outlier Governance & Analytical Eligibility
    is_outlier: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    outlier_reasons: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # JSON serialized list of reason strings
    analytical_eligibility: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
