"""
CARspective — Canonical Vehicle Resolver
Resolves incoming raw vehicle parameters to a deterministic Canonical Vehicle Identity.
Handles case differences, whitespace, brand prefixes, aliases, and ambiguous boundaries.
"""

import re
from typing import Optional, Dict, Any, List, TYPE_CHECKING
if TYPE_CHECKING:
    from server.repositories.taxonomy_repository import TaxonomyRepository

from server.domain.taxonomy.slugifier import slugify
from server.schemas.taxonomy import (
    CanonicalResolutionRequest,
    CanonicalResolutionResult,
    ResolutionStatus,
)
from server.models.taxonomy import build_canonical_id
from collections import OrderedDict
import threading
from typing import Tuple


def make_canonical_cache_key(req: CanonicalResolutionRequest) -> Tuple[str, str, Optional[int], Optional[str], Optional[str], Optional[str]]:
    """Generates a normalized, deterministic cache key from canonical resolution request fields."""
    norm_brand = (req.brand or "").strip().lower()
    norm_model = (req.model or "").strip().lower()
    norm_year = int(req.year) if req.year is not None else None
    norm_variant = req.variant.strip().lower() if (req.variant and req.variant.strip()) else None
    norm_fuel = req.fuel_type.strip().lower() if (req.fuel_type and req.fuel_type.strip()) else None
    norm_transmission = req.transmission_type.strip().lower() if (req.transmission_type and req.transmission_type.strip()) else None
    return (norm_brand, norm_model, norm_year, norm_variant, norm_fuel, norm_transmission)


class CanonicalResolutionCache:
    """Thread-safe LRU cache storing deep-copied CanonicalResolutionResult objects."""
    def __init__(self, maxsize: int = 4096):
        self.maxsize = maxsize
        self._cache: OrderedDict = OrderedDict()
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    @property
    def hits(self) -> int:
        with self._lock:
            return self._hits

    @property
    def misses(self) -> int:
        with self._lock:
            return self._misses

    def get(self, key: tuple) -> Optional[CanonicalResolutionResult]:
        with self._lock:
            if key in self._cache:
                self._hits += 1
                self._cache.move_to_end(key)
                return self._cache[key].model_copy(deep=True)
            self._misses += 1
            return None

    def set(self, key: tuple, result: CanonicalResolutionResult) -> None:
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = result.model_copy(deep=True)
            if len(self._cache) > self.maxsize:
                self._cache.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def __len__(self) -> int:
        with self._lock:
            return len(self._cache)


class CanonicalResolver:
    _GLOBAL_RESOLUTION_CACHE = CanonicalResolutionCache(maxsize=4096)

    def __init__(self, repo: "TaxonomyRepository", cache: Optional[CanonicalResolutionCache] = None):
        self.repo = repo
        self._cache = cache if cache is not None else self.__class__._GLOBAL_RESOLUTION_CACHE

    @classmethod
    def clear_resolution_cache(cls) -> None:
        """Flushes the global canonical resolution cache."""
        cls._GLOBAL_RESOLUTION_CACHE.clear()

    @classmethod
    def get_resolution_cache_stats(cls) -> Dict[str, int]:
        return {
            "size": len(cls._GLOBAL_RESOLUTION_CACHE),
            "hits": cls._GLOBAL_RESOLUTION_CACHE.hits,
            "misses": cls._GLOBAL_RESOLUTION_CACHE.misses
        }

    def resolve(self, req: CanonicalResolutionRequest, use_cache: bool = True) -> CanonicalResolutionResult:
        """
        Resolves incoming raw vehicle parameters to a deterministic Canonical Vehicle Identity.
        Leverages thread-safe in-memory LRU cache on repeated requests to eliminate DB reads.
        """
        if not use_cache or self._cache is None:
            return self._resolve_internal(req)

        key = make_canonical_cache_key(req)
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        result = self._resolve_internal(req)
        self._cache.set(key, result)
        return result.model_copy(deep=True)

    def _resolve_internal(self, req: CanonicalResolutionRequest) -> CanonicalResolutionResult:
        notes: List[str] = []
        raw_brand = (req.brand or "").strip()
        raw_model = (req.model or "").strip()

        if not raw_brand and not raw_model:
            return CanonicalResolutionResult(
                status=ResolutionStatus.UNRESOLVED,
                confidence_score=0.0,
                match_notes=["Both brand and model parameters are empty."]
            )

        # 1. Resolve Manufacturer
        manufacturer = self.repo.find_manufacturer(raw_brand)
        if not manufacturer:
            # Check if brand was embedded in model string (e.g. brand="", model="Hyundai Creta")
            for prefix in ["Maruti Suzuki", "Maruti", "Hyundai", "Honda", "Tata", "Toyota", "Mahindra", "Kia", "BMW", "Mercedes-Benz", "Audi", "Skoda", "Volkswagen", "Renault", "Ford"]:
                if raw_model.lower().startswith(prefix.lower() + " "):
                    cand_m = self.repo.find_manufacturer(prefix)
                    if cand_m:
                        manufacturer = cand_m
                        raw_model = raw_model[len(prefix):].strip()
                        notes.append(f"Extracted manufacturer '{manufacturer.name}' from model string.")
                        break

        if not manufacturer:
            return CanonicalResolutionResult(
                status=ResolutionStatus.UNRESOLVED,
                confidence_score=0.0,
                match_notes=[f"Manufacturer '{raw_brand}' could not be resolved to any canonical manufacturer or alias."]
            )

        notes.append(f"Resolved manufacturer: {manufacturer.name} ({manufacturer.slug})")

        # 2. Normalize and Resolve Model
        cleaned_model_name = raw_model
        # Strip redundant manufacturer prefix if present (e.g., "Hyundai Creta" -> "Creta")
        for m_name in [manufacturer.name, manufacturer.slug, "Maruti Suzuki", "Maruti"]:
            if cleaned_model_name.lower().startswith(m_name.lower() + " "):
                cleaned_model_name = cleaned_model_name[len(m_name):].strip()
                notes.append(f"Stripped redundant manufacturer prefix '{m_name}' from model name.")
                break

        # Check for bracketed generation hint like "Thar [2020-2025]"
        gen_bracket_match = re.search(r'\[(\d{4})-(\d{4})\]', cleaned_model_name)
        gen_hint_start = int(gen_bracket_match.group(1)) if gen_bracket_match else None
        if gen_bracket_match:
            cleaned_model_name = re.sub(r'\[\d{4}-\d{4}\]', '', cleaned_model_name).strip()
            notes.append(f"Extracted generation boundary hint: {gen_bracket_match.group(0)}")

        vehicle_model = self.repo.find_model(manufacturer.id, cleaned_model_name)
        if not vehicle_model:
            return CanonicalResolutionResult(
                status=ResolutionStatus.UNRESOLVED,
                confidence_score=0.2,
                match_notes=notes + [f"Model '{raw_model}' could not be resolved under manufacturer '{manufacturer.name}'."]
            )

        notes.append(f"Resolved model: {vehicle_model.name} ({vehicle_model.slug}) [Tier: {vehicle_model.coverage_tier}]")

        # 3. Resolve Generation & Model Year
        target_year = req.year or gen_hint_start
        generation = None

        if target_year:
            generation = self.repo.find_generation_for_year(vehicle_model.id, target_year)
            if generation:
                notes.append(f"Resolved generation for year {target_year}: {generation.name} ({generation.slug})")
            else:
                notes.append(f"Model year {target_year} falls outside all verified generations for {vehicle_model.name}.")

        # If no year or no year-matched generation, inspect available generations
        all_generations = self.repo.list_generations(vehicle_model.id)
        if not generation:
            if len(all_generations) == 1:
                generation = all_generations[0]
                notes.append(f"Single active generation available: defaulted to {generation.name} ({generation.slug}).")
            elif len(all_generations) > 1 and not target_year:
                # Ambiguous: multiple generations exist, but user provided no year to differentiate
                candidates = [
                    {
                        "generation_name": g.name,
                        "generation_slug": g.slug,
                        "year_start": g.year_start,
                        "year_end": g.year_end
                    }
                    for g in all_generations
                ]
                return CanonicalResolutionResult(
                    status=ResolutionStatus.AMBIGUOUS_MATCH,
                    canonical_vehicle_id=f"{manufacturer.slug}::{vehicle_model.slug}",
                    hierarchy={
                        "manufacturer": manufacturer.name,
                        "model": vehicle_model.name,
                        "coverage_tier": vehicle_model.coverage_tier
                    },
                    matched_tier=vehicle_model.coverage_tier,
                    confidence_score=0.5,
                    match_notes=notes + ["Model has multiple generations. Model Year is required to resolve unambiguous canonical identity."],
                    ambiguous_candidates=candidates
                )
            elif len(all_generations) > 0 and target_year:
                # Year provided but out of range: pick closest generation as partial match
                generation = all_generations[-1]
                notes.append(f"Target year {target_year} outside bounds; defaulted to latest generation {generation.name} as partial match.")

        if not generation:
            # No generations defined yet (e.g. Tier 2 model with only model-level entry)
            return CanonicalResolutionResult(
                status=ResolutionStatus.PARTIAL_MATCH,
                canonical_vehicle_id=f"{manufacturer.slug}::{vehicle_model.slug}::gen-unspecified",
                hierarchy={
                    "manufacturer": manufacturer.name,
                    "model": vehicle_model.name,
                    "coverage_tier": vehicle_model.coverage_tier
                },
                matched_tier=vehicle_model.coverage_tier,
                confidence_score=0.6,
                match_notes=notes + ["No generation boundary verified for this model."]
            )

        # 4. Resolve Variant & Powertrain
        variant = None
        powertrain = None

        if req.variant:
            variant = self.repo.find_variant(generation.id, req.variant)
            if variant:
                notes.append(f"Resolved variant: {variant.name} ({variant.slug})")
                powertrain = self.repo.find_powertrain(
                    variant.id,
                    fuel_type=req.fuel_type,
                    transmission_type=req.transmission_type
                )
                if powertrain:
                    notes.append(f"Resolved powertrain configuration: {powertrain.fuel_type} · {powertrain.transmission_type}")

        # 5. Build Canonical Identity Output
        resolved_year = target_year or (generation.year_end or generation.year_start)
        variant_slug = variant.slug if variant else "standard"
        powertrain_slug = powertrain.slug if powertrain else (
            f"{slugify(req.fuel_type or 'unspecified')}-{slugify(req.transmission_type or 'unspecified')}"
        )

        canonical_id = build_canonical_id(
            make_slug=manufacturer.slug,
            model_slug=vehicle_model.slug,
            generation_slug=generation.slug,
            model_year=resolved_year,
            variant_slug=variant_slug,
            powertrain_slug=powertrain_slug
        )

        hierarchy = {
            "manufacturer": {
                "name": manufacturer.name,
                "slug": manufacturer.slug
            },
            "model": {
                "name": vehicle_model.name,
                "slug": vehicle_model.slug,
                "body_type": vehicle_model.body_type,
                "coverage_tier": vehicle_model.coverage_tier
            },
            "generation": {
                "name": generation.name,
                "slug": generation.slug,
                "year_start": generation.year_start,
                "year_end": generation.year_end
            },
            "model_year": resolved_year,
            "variant": {
                "name": variant.name if variant else None,
                "slug": variant_slug
            },
            "powertrain": {
                "fuel_type": powertrain.fuel_type if powertrain else req.fuel_type,
                "transmission_type": powertrain.transmission_type if powertrain else req.transmission_type,
                "slug": powertrain_slug
            }
        }

        # Calculate confidence score
        confidence = 0.7  # Baseline for make + model + generation
        if target_year and generation.year_start <= target_year <= (generation.year_end or 2026):
            confidence += 0.15
        if variant:
            confidence += 0.10
        if powertrain:
            confidence += 0.05
        confidence = min(1.0, confidence)

        status = ResolutionStatus.EXACT_MATCH if (variant and powertrain and target_year) else ResolutionStatus.PARTIAL_MATCH

        return CanonicalResolutionResult(
            status=status,
            canonical_vehicle_id=canonical_id,
            hierarchy=hierarchy,
            matched_tier=vehicle_model.coverage_tier,
            confidence_score=round(confidence, 2),
            match_notes=notes
        )
