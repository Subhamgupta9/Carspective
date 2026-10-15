"""
CARspective — Canonical Vehicle Taxonomy Models
Implements the 6-tier canonical hierarchy:
Manufacturer -> Model -> Generation -> Model Year -> Variant -> Powertrain Configuration
"""

import uuid
from typing import Optional, List
from sqlalchemy import String, Integer, Float, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin

def build_canonical_id(
    make_slug: str,
    model_slug: str,
    generation_slug: str,
    model_year: int | str,
    variant_slug: str,
    powertrain_slug: str
) -> str:
    """Deterministic Canonical Vehicle ID builder."""
    return f"{make_slug}::{model_slug}::{generation_slug}::{model_year}::{variant_slug}::{powertrain_slug}"

class Manufacturer(Base, TimestampMixin):
    __tablename__ = "manufacturers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    country_of_origin: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    models: Mapped[List["VehicleModel"]] = relationship(
        "VehicleModel",
        back_populates="manufacturer",
        cascade="all, delete-orphan"
    )
    aliases: Mapped[List["ManufacturerAlias"]] = relationship(
        "ManufacturerAlias",
        back_populates="manufacturer",
        cascade="all, delete-orphan"
    )

class ManufacturerAlias(Base):
    __tablename__ = "manufacturer_aliases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    manufacturer_id: Mapped[str] = mapped_column(String(36), ForeignKey("manufacturers.id", ondelete="CASCADE"), nullable=False)
    alias: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)

    manufacturer: Mapped["Manufacturer"] = relationship("Manufacturer", back_populates="aliases")

class VehicleModel(Base, TimestampMixin):
    __tablename__ = "vehicle_models"
    __table_args__ = (
        UniqueConstraint("manufacturer_id", "slug", name="uq_manufacturer_model_slug"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    manufacturer_id: Mapped[str] = mapped_column(String(36), ForeignKey("manufacturers.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    body_type: Mapped[str] = mapped_column(String(50), nullable=False)
    segment: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    coverage_tier: Mapped[str] = mapped_column(String(20), default="TIER_2_CANONICAL", nullable=False) # TIER_1_DEEP, TIER_2_CANONICAL, TIER_3_UNSUPPORTED
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    manufacturer: Mapped["Manufacturer"] = relationship("Manufacturer", back_populates="models")
    generations: Mapped[List["VehicleGeneration"]] = relationship(
        "VehicleGeneration",
        back_populates="model",
        cascade="all, delete-orphan"
    )
    aliases: Mapped[List["ModelAlias"]] = relationship(
        "ModelAlias",
        back_populates="model",
        cascade="all, delete-orphan"
    )

class ModelAlias(Base):
    __tablename__ = "model_aliases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    model_id: Mapped[str] = mapped_column(String(36), ForeignKey("vehicle_models.id", ondelete="CASCADE"), nullable=False)
    alias: Mapped[str] = mapped_column(String(150), unique=True, index=True, nullable=False)
    raw_listing_pattern: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)

    model: Mapped["VehicleModel"] = relationship("VehicleModel", back_populates="aliases")

class VehicleGeneration(Base, TimestampMixin):
    __tablename__ = "vehicle_generations"
    __table_args__ = (
        UniqueConstraint("model_id", "slug", name="uq_model_generation_slug"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    model_id: Mapped[str] = mapped_column(String(36), ForeignKey("vehicle_models.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    year_start: Mapped[int] = mapped_column(Integer, nullable=False)
    year_end: Mapped[Optional[int]] = mapped_column(Integer, nullable=True) # None = present
    is_facelift: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    model: Mapped["VehicleModel"] = relationship("VehicleModel", back_populates="generations")
    model_years: Mapped[List["ModelYear"]] = relationship(
        "ModelYear",
        back_populates="generation",
        cascade="all, delete-orphan"
    )
    variants: Mapped[List["VehicleVariant"]] = relationship(
        "VehicleVariant",
        back_populates="generation",
        cascade="all, delete-orphan"
    )

class ModelYear(Base):
    __tablename__ = "model_years"
    __table_args__ = (
        UniqueConstraint("generation_id", "calendar_year", name="uq_generation_calendar_year"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    generation_id: Mapped[str] = mapped_column(String(36), ForeignKey("vehicle_generations.id", ondelete="CASCADE"), nullable=False)
    calendar_year: Mapped[int] = mapped_column(Integer, index=True, nullable=False)

    generation: Mapped["VehicleGeneration"] = relationship("VehicleGeneration", back_populates="model_years")

class VehicleVariant(Base, TimestampMixin):
    __tablename__ = "vehicle_variants"
    __table_args__ = (
        UniqueConstraint("generation_id", "slug", name="uq_generation_variant_slug"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    generation_id: Mapped[str] = mapped_column(String(36), ForeignKey("vehicle_generations.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    trim_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    generation: Mapped["VehicleGeneration"] = relationship("VehicleGeneration", back_populates="variants")
    powertrains: Mapped[List["PowertrainConfiguration"]] = relationship(
        "PowertrainConfiguration",
        back_populates="variant",
        cascade="all, delete-orphan"
    )

class PowertrainConfiguration(Base, TimestampMixin):
    __tablename__ = "powertrain_configurations"
    __table_args__ = (
        UniqueConstraint("variant_id", "slug", name="uq_variant_powertrain_slug"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    variant_id: Mapped[str] = mapped_column(String(36), ForeignKey("vehicle_variants.id", ondelete="CASCADE"), nullable=False)
    engine_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    displacement_cc: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    fuel_type: Mapped[str] = mapped_column(String(50), nullable=False) # Petrol, Diesel, CNG, Electric, Hybrid
    transmission_type: Mapped[str] = mapped_column(String(50), nullable=False) # Manual, Automatic (TC), DCT, CVT, AMT
    power_bhp: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    torque_nm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    arai_mileage_kmpl: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    slug: Mapped[str] = mapped_column(String(150), index=True, nullable=False)

    variant: Mapped["VehicleVariant"] = relationship("VehicleVariant", back_populates="powertrains")
