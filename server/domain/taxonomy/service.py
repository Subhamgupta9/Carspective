"""
CARspective — Taxonomy Domain Service
Coordinates taxonomy inquiries, entity retrieval, and canonical identity resolution.
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from server.repositories.taxonomy_repository import TaxonomyRepository
from server.domain.taxonomy.resolver import CanonicalResolver
from server.schemas.taxonomy import (
    ManufacturerSummarySchema,
    ManufacturerDetailSchema,
    VehicleModelSummarySchema,
    VehicleModelDetailSchema,
    CanonicalResolutionRequest,
    CanonicalResolutionResult,
)

class TaxonomyService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = TaxonomyRepository(session)
        self.resolver = CanonicalResolver(self.repo)

    def list_manufacturers(self) -> List[ManufacturerSummarySchema]:
        manufacturers = self.repo.list_manufacturers()
        return [ManufacturerSummarySchema.model_validate(m) for m in manufacturers]

    def get_manufacturer(self, make_slug: str) -> Optional[ManufacturerDetailSchema]:
        m = self.repo.get_manufacturer_by_slug(make_slug)
        if not m:
            return None
        models = [VehicleModelSummarySchema.model_validate(mod) for mod in m.models]
        aliases = [a.alias for a in m.aliases]
        return ManufacturerDetailSchema(
            id=m.id,
            name=m.name,
            slug=m.slug,
            country_of_origin=m.country_of_origin,
            is_active=m.is_active,
            models=models,
            aliases=aliases
        )

    def list_models_by_manufacturer(self, make_slug: str) -> List[VehicleModelSummarySchema]:
        models = self.repo.list_models_by_manufacturer(make_slug)
        return [VehicleModelSummarySchema.model_validate(m) for m in models]

    def get_model(self, make_slug: str, model_slug: str) -> Optional[VehicleModelDetailSchema]:
        mod = self.repo.get_model_by_slug(make_slug, model_slug)
        if not mod:
            return None
        return VehicleModelDetailSchema(
            id=mod.id,
            name=mod.name,
            slug=mod.slug,
            body_type=mod.body_type,
            segment=mod.segment,
            coverage_tier=mod.coverage_tier,
            is_active=mod.is_active,
            manufacturer_name=mod.manufacturer.name,
            manufacturer_slug=mod.manufacturer.slug,
            generations=mod.generations,
            aliases=[a.alias for a in mod.aliases]
        )

    def resolve_vehicle(self, req: CanonicalResolutionRequest) -> CanonicalResolutionResult:
        return self.resolver.resolve(req)
