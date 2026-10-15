"""
CARspective — Taxonomy Pydantic v2 Schemas
"""

import enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field

class ResolutionStatus(str, enum.Enum):
    EXACT_MATCH = "EXACT_MATCH"
    PARTIAL_MATCH = "PARTIAL_MATCH"
    AMBIGUOUS_MATCH = "AMBIGUOUS_MATCH"
    UNRESOLVED = "UNRESOLVED"

# 1. Powertrain Configuration
class PowertrainConfigurationSchema(BaseModel):
    id: str
    slug: str
    engine_name: Optional[str] = None
    displacement_cc: Optional[int] = None
    fuel_type: str
    transmission_type: str
    power_bhp: Optional[float] = None
    torque_nm: Optional[float] = None
    arai_mileage_kmpl: Optional[float] = None
    
    model_config = ConfigDict(from_attributes=True)

# 2. Variant
class VehicleVariantSchema(BaseModel):
    id: str
    name: str
    slug: str
    trim_level: Optional[str] = None
    powertrains: List[PowertrainConfigurationSchema] = []
    
    model_config = ConfigDict(from_attributes=True)

# 3. Model Year
class ModelYearSchema(BaseModel):
    calendar_year: int
    
    model_config = ConfigDict(from_attributes=True)

# 4. Generation
class VehicleGenerationSchema(BaseModel):
    id: str
    name: str
    slug: str
    year_start: int
    year_end: Optional[int] = None
    is_facelift: bool
    model_years: List[ModelYearSchema] = []
    variants: List[VehicleVariantSchema] = []
    
    model_config = ConfigDict(from_attributes=True)

# 5. Model
class VehicleModelSummarySchema(BaseModel):
    id: str
    name: str
    slug: str
    body_type: str
    segment: Optional[str] = None
    coverage_tier: str
    is_active: bool
    
    model_config = ConfigDict(from_attributes=True)

class VehicleModelDetailSchema(VehicleModelSummarySchema):
    manufacturer_name: str
    manufacturer_slug: str
    generations: List[VehicleGenerationSchema] = []
    aliases: List[str] = []

# 6. Manufacturer
class ManufacturerSummarySchema(BaseModel):
    id: str
    name: str
    slug: str
    country_of_origin: Optional[str] = None
    is_active: bool
    
    model_config = ConfigDict(from_attributes=True)

class ManufacturerDetailSchema(ManufacturerSummarySchema):
    models: List[VehicleModelSummarySchema] = []
    aliases: List[str] = []

# 7. Canonical Resolution Request & Result
class CanonicalResolutionRequest(BaseModel):
    brand: str
    model: str
    year: Optional[int] = None
    variant: Optional[str] = None
    fuel_type: Optional[str] = None
    transmission_type: Optional[str] = None

class CanonicalResolutionResult(BaseModel):
    status: ResolutionStatus
    canonical_vehicle_id: Optional[str] = None
    hierarchy: Optional[Dict[str, Any]] = None
    matched_tier: Optional[str] = None
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    match_notes: List[str] = []
    ambiguous_candidates: Optional[List[Dict[str, Any]]] = None
