"""
CARspective — Taxonomy Repository
Encapsulates all database interactions for the 6-tier canonical vehicle hierarchy.
"""

from dataclasses import dataclass
import threading
from typing import List, Optional, Tuple
from sqlalchemy import select, or_, func
from sqlalchemy.orm import Session, joinedload, selectinload
from server.models.taxonomy import (
    Manufacturer,
    ManufacturerAlias,
    VehicleModel,
    ModelAlias,
    VehicleGeneration,
    ModelYear,
    VehicleVariant,
    PowertrainConfiguration,
)
from server.utils.slugifier import slugify


@dataclass(frozen=True)
class PowertrainSnapshot:
    slug: str
    fuel_type: str
    transmission_type: str


@dataclass(frozen=True)
class VariantSnapshot:
    name: str
    slug: str
    powertrains: Tuple[PowertrainSnapshot, ...]


@dataclass(frozen=True)
class GenerationSnapshot:
    name: str
    slug: str
    year_start: int
    year_end: Optional[int]
    variants: Tuple[VariantSnapshot, ...]


@dataclass(frozen=True)
class ModelSnapshot:
    name: str
    slug: str
    body_type: Optional[str]
    coverage_tier: str
    generations: Tuple[GenerationSnapshot, ...]


@dataclass(frozen=True)
class ManufacturerSnapshot:
    name: str
    slug: str
    models: Tuple[ModelSnapshot, ...]


class TaxonomyRepository:
    _HIERARCHY_SNAPSHOT_CACHE: Optional[Tuple[ManufacturerSnapshot, ...]] = None
    _HIERARCHY_LOCK: threading.Lock = threading.Lock()
    _HIERARCHY_VERSION: int = 1

    def __init__(self, session: Optional[Session] = None):
        self._session = session
        self._mfg_cache = {}
        self._model_cache = {}

    @classmethod
    def invalidate_hierarchy_cache(cls) -> None:
        """Invalidates the in-memory taxonomy hierarchy snapshot cache."""
        with cls._HIERARCHY_LOCK:
            cls._HIERARCHY_SNAPSHOT_CACHE = None
            cls._HIERARCHY_VERSION += 1
        try:
            from server.domain.taxonomy.resolver import CanonicalResolver
            CanonicalResolver.clear_resolution_cache()
        except (ImportError, AttributeError):
            pass

    @classmethod
    def get_hierarchy_cache_version(cls) -> int:
        return cls._HIERARCHY_VERSION

    def get_taxonomy_hierarchy_snapshot(self, force_refresh: bool = False) -> Tuple[ManufacturerSnapshot, ...]:
        """
        Retrieves a thread-safe immutable snapshot of the 6-tier vehicle taxonomy hierarchy.
        Constructed from database on first call (or force_refresh), cached in memory thereafter.
        Guarantees zero detached-session errors and zero cross-thread database contention.
        """
        if not force_refresh and self.__class__._HIERARCHY_SNAPSHOT_CACHE is not None:
            return self.__class__._HIERARCHY_SNAPSHOT_CACHE

        with self.__class__._HIERARCHY_LOCK:
            if not force_refresh and self.__class__._HIERARCHY_SNAPSHOT_CACHE is not None:
                return self.__class__._HIERARCHY_SNAPSHOT_CACHE

            raw_mfgs = self.list_manufacturers(active_only=True, eager_hierarchy=True)
            snapshot_list = []
            for m in raw_mfgs:
                model_snapshots = []
                for mod in m.models:
                    gen_snapshots = []
                    for gen in mod.generations:
                        var_snapshots = []
                        for var in gen.variants:
                            pt_snapshots = []
                            for pt in var.powertrains:
                                pt_snapshots.append(PowertrainSnapshot(
                                    slug=pt.slug,
                                    fuel_type=pt.fuel_type,
                                    transmission_type=pt.transmission_type
                                ))
                            var_snapshots.append(VariantSnapshot(
                                name=var.name,
                                slug=var.slug,
                                powertrains=tuple(pt_snapshots)
                            ))
                        gen_snapshots.append(GenerationSnapshot(
                            name=gen.name,
                            slug=gen.slug,
                            year_start=gen.year_start,
                            year_end=gen.year_end,
                            variants=tuple(var_snapshots)
                        ))
                    model_snapshots.append(ModelSnapshot(
                        name=mod.name,
                        slug=mod.slug,
                        body_type=mod.body_type,
                        coverage_tier=mod.coverage_tier,
                        generations=tuple(gen_snapshots)
                    ))
                snapshot_list.append(ManufacturerSnapshot(
                    name=m.name,
                    slug=m.slug,
                    models=tuple(model_snapshots)
                ))

            frozen_hierarchy = tuple(snapshot_list)
            self.__class__._HIERARCHY_SNAPSHOT_CACHE = frozen_hierarchy
            return frozen_hierarchy

    @property
    def session(self) -> Session:
        if self._session is not None:
            return self._session
        from server.infrastructure.database import ScopedSession
        return ScopedSession()

    @session.setter
    def session(self, value: Optional[Session]) -> None:
        self._session = value

    # 1. Manufacturers
    def list_manufacturers(
        self,
        active_only: bool = True,
        eager_hierarchy: bool = False
    ) -> List[Manufacturer]:
        stmt = select(Manufacturer).order_by(Manufacturer.name)
        if active_only:
            stmt = stmt.where(Manufacturer.is_active == True)
        if eager_hierarchy:
            stmt = stmt.options(
                selectinload(Manufacturer.models)
                .selectinload(VehicleModel.generations)
                .selectinload(VehicleGeneration.variants)
                .selectinload(VehicleVariant.powertrains)
            )
        return list(self.session.scalars(stmt).all())

    def get_manufacturer_by_slug(self, slug: str) -> Optional[Manufacturer]:
        clean_slug = slugify(slug)
        stmt = select(Manufacturer).options(
            joinedload(Manufacturer.models),
            joinedload(Manufacturer.aliases)
        ).where(Manufacturer.slug == clean_slug)
        return self.session.scalars(stmt).first()

    def find_manufacturer(self, query: str) -> Optional[Manufacturer]:
        key = query.lower().strip()
        if key in self._mfg_cache:
            return self._mfg_cache[key]

        clean_slug = slugify(query)
        # Direct slug or name match with eager-loaded models and aliases
        stmt = select(Manufacturer).options(
            joinedload(Manufacturer.models),
            joinedload(Manufacturer.aliases)
        ).where(
            or_(
                Manufacturer.slug == clean_slug,
                func.lower(Manufacturer.name) == query.lower().strip()
            )
        )
        m = self.session.scalars(stmt).first()
        if m:
            self._mfg_cache[key] = m
            return m
        # Check alias
        alias_stmt = select(ManufacturerAlias).options(
            joinedload(ManufacturerAlias.manufacturer).joinedload(Manufacturer.models),
            joinedload(ManufacturerAlias.manufacturer).joinedload(Manufacturer.aliases)
        ).where(
            or_(
                func.lower(ManufacturerAlias.alias) == query.lower().strip(),
                func.lower(ManufacturerAlias.alias) == clean_slug
            )
        )
        ma = self.session.scalars(alias_stmt).first()
        res = ma.manufacturer if ma else None
        self._mfg_cache[key] = res
        return res

    # 2. Vehicle Models
    def list_models_by_manufacturer(self, manufacturer_slug: str, active_only: bool = True) -> List[VehicleModel]:
        m = self.get_manufacturer_by_slug(manufacturer_slug)
        if not m:
            return []
        stmt = select(VehicleModel).where(VehicleModel.manufacturer_id == m.id).order_by(VehicleModel.name)
        if active_only:
            stmt = stmt.where(VehicleModel.is_active == True)
        return list(self.session.scalars(stmt).all())

    def get_model_by_slug(self, manufacturer_slug: str, model_slug: str) -> Optional[VehicleModel]:
        m = self.get_manufacturer_by_slug(manufacturer_slug)
        if not m:
            return None
        stmt = select(VehicleModel).options(
            joinedload(VehicleModel.generations).joinedload(VehicleGeneration.model_years),
            joinedload(VehicleModel.generations).joinedload(VehicleGeneration.variants).joinedload(VehicleVariant.powertrains),
            joinedload(VehicleModel.aliases),
            joinedload(VehicleModel.manufacturer)
        ).where(
            VehicleModel.manufacturer_id == m.id,
            VehicleModel.slug == slugify(model_slug)
        )
        return self.session.scalars(stmt).first()

    def find_model(self, manufacturer_id: str, query: str) -> Optional[VehicleModel]:
        key = (manufacturer_id, query.lower().strip())
        if key in self._model_cache:
            return self._model_cache[key]

        clean_slug = slugify(query)
        # Direct slug or name match with eager-loaded relations
        stmt = select(VehicleModel).options(
            joinedload(VehicleModel.manufacturer),
            joinedload(VehicleModel.aliases),
            joinedload(VehicleModel.generations).joinedload(VehicleGeneration.model_years),
            joinedload(VehicleModel.generations).joinedload(VehicleGeneration.variants).joinedload(VehicleVariant.powertrains)
        ).where(
            VehicleModel.manufacturer_id == manufacturer_id,
            or_(
                VehicleModel.slug == clean_slug,
                func.lower(VehicleModel.name) == query.lower().strip()
            )
        )
        mod = self.session.scalars(stmt).first()
        if mod:
            self._model_cache[key] = mod
            return mod
        # Alias match
        alias_stmt = select(ModelAlias).options(
            joinedload(ModelAlias.model).joinedload(VehicleModel.manufacturer),
            joinedload(ModelAlias.model).joinedload(VehicleModel.aliases),
            joinedload(ModelAlias.model).joinedload(VehicleModel.generations).joinedload(VehicleGeneration.model_years),
            joinedload(ModelAlias.model).joinedload(VehicleModel.generations).joinedload(VehicleGeneration.variants).joinedload(VehicleVariant.powertrains)
        ).where(
            ModelAlias.model_id.in_(
                select(VehicleModel.id).where(VehicleModel.manufacturer_id == manufacturer_id)
            ),
            or_(
                func.lower(ModelAlias.alias) == query.lower().strip(),
                func.lower(ModelAlias.alias) == clean_slug
            )
        )
        ma = self.session.scalars(alias_stmt).first()
        res = ma.model if ma else None
        self._model_cache[key] = res
        return res

    def resolve_make_model_from_slug(self, identifier: str) -> Tuple[Optional[Manufacturer], Optional[VehicleModel]]:
        """
        Resolves a raw or slugified vehicle identifier to its canonical Manufacturer and VehicleModel.
        Handles canonical 'make::model' format, hyphenated slugs ('toyota-innova-crysta', 'Toyota-Innova Crysta'),
        and manufacturer aliases ('Maruti-Swift').
        Returns (None, None) if not resolved.
        """
        if not identifier or not identifier.strip():
            return None, None

        cid = identifier.strip()
        if "::" in cid:
            parts = cid.split("::")
            m = self.get_manufacturer_by_slug(parts[0]) or self.find_manufacturer(parts[0])
            mod = self.get_model_by_slug(m.slug, parts[1]) if m and len(parts) > 1 else None
            if not mod and m and len(parts) > 1:
                mod = self.find_model(m.id, parts[1])
            return m, mod

        all_mfgs = self.list_manufacturers(active_only=True)
        candidates = []
        for m in all_mfgs:
            candidates.append((slugify(m.slug), m))
            candidates.append((slugify(m.name), m))
            candidates.append((m.name.lower(), m))
            for a in getattr(m, "aliases", []):
                candidates.append((slugify(a.alias), m))
                candidates.append((a.alias.lower(), m))
        candidates.sort(key=lambda x: len(x[0]), reverse=True)

        cid_lower = cid.lower()
        cid_slug = slugify(cid)
        matched_mfg = None
        remaining_model = None

        for prefix, m in candidates:
            for sep in ["-", " ", "_"]:
                if cid_lower.startswith(prefix + sep):
                    matched_mfg = m
                    remaining_model = cid[len(prefix) + len(sep):].strip()
                    break
                if cid_slug.startswith(prefix + "-"):
                    matched_mfg = m
                    remaining_model = cid_slug[len(prefix) + 1:].strip()
                    break
            if matched_mfg:
                break

        if not matched_mfg and "-" in cid:
            parts_h = cid.split("-", 1)
            m = self.find_manufacturer(parts_h[0])
            if m:
                matched_mfg = m
                remaining_model = parts_h[1].strip()

        if matched_mfg and remaining_model:
            mod = self.find_model(matched_mfg.id, remaining_model)
            if not mod:
                mod = self.find_model(matched_mfg.id, slugify(remaining_model))
            return matched_mfg, mod

        return None, None

    # 3. Generations & Years
    def list_generations(self, model_id: str) -> List[VehicleGeneration]:
        stmt = select(VehicleGeneration).where(VehicleGeneration.model_id == model_id).order_by(VehicleGeneration.year_start)
        return list(self.session.scalars(stmt).all())

    def get_generation_by_slug(self, model_id: str, gen_slug: str) -> Optional[VehicleGeneration]:
        stmt = select(VehicleGeneration).options(
            joinedload(VehicleGeneration.model_years),
            joinedload(VehicleGeneration.variants).joinedload(VehicleVariant.powertrains)
        ).where(
            VehicleGeneration.model_id == model_id,
            VehicleGeneration.slug == slugify(gen_slug)
        )
        return self.session.scalars(stmt).first()

    def find_generation_for_year(self, model_id: str, year: int) -> Optional[VehicleGeneration]:
        # First check explicit model_years link
        my_stmt = select(ModelYear).options(
            joinedload(ModelYear.generation)
        ).where(
            ModelYear.calendar_year == year,
            ModelYear.generation_id.in_(
                select(VehicleGeneration.id).where(VehicleGeneration.model_id == model_id)
            )
        )
        my = self.session.scalars(my_stmt).first()
        if my:
            return my.generation

        # Fallback to year_start and year_end boundaries
        gen_stmt = select(VehicleGeneration).where(
            VehicleGeneration.model_id == model_id,
            VehicleGeneration.year_start <= year,
            or_(
                VehicleGeneration.year_end == None,
                VehicleGeneration.year_end >= year
            )
        ).order_by(VehicleGeneration.year_start.desc())
        return self.session.scalars(gen_stmt).first()

    # 4. Variants & Powertrains
    def list_variants(self, generation_id: str) -> List[VehicleVariant]:
        stmt = select(VehicleVariant).options(
            joinedload(VehicleVariant.powertrains)
        ).where(VehicleVariant.generation_id == generation_id).order_by(VehicleVariant.name)
        return list(self.session.scalars(stmt).unique().all())

    def get_variant_by_slug(self, generation_id: str, variant_slug: str) -> Optional[VehicleVariant]:
        stmt = select(VehicleVariant).options(
            joinedload(VehicleVariant.powertrains)
        ).where(
            VehicleVariant.generation_id == generation_id,
            VehicleVariant.slug == slugify(variant_slug)
        )
        return self.session.scalars(stmt).first()

    def find_variant(self, generation_id: str, query: str) -> Optional[VehicleVariant]:
        clean_slug = slugify(query)
        stmt = select(VehicleVariant).where(
            VehicleVariant.generation_id == generation_id,
            or_(
                VehicleVariant.slug == clean_slug,
                func.lower(VehicleVariant.name) == query.lower().strip()
            )
        )
        return self.session.scalars(stmt).first()

    def find_powertrain(
        self,
        variant_id: str,
        fuel_type: Optional[str] = None,
        transmission_type: Optional[str] = None
    ) -> Optional[PowertrainConfiguration]:
        stmt = select(PowertrainConfiguration).where(PowertrainConfiguration.variant_id == variant_id)
        if fuel_type:
            stmt = stmt.where(func.lower(PowertrainConfiguration.fuel_type) == fuel_type.lower().strip())
        if transmission_type:
            stmt = stmt.where(func.lower(PowertrainConfiguration.transmission_type) == transmission_type.lower().strip())
        return self.session.scalars(stmt).first()
