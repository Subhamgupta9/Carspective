"""
CARspective — Safe Canonical Mapping Engine
Deterministic vehicle entity resolution enforcing strict zero-silent-mutation rules.
Categorizes mapping outcomes into:
EXACT_MATCH, SAFE_ALIAS_MATCH, AMBIGUOUS, UNMAPPED, REJECTED.
"""

from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from server.repositories.taxonomy_repository import TaxonomyRepository
from server.models.taxonomy import VehicleGeneration, VehicleVariant
from server.utils.slugifier import slugify
from .models import MappingOutcome, CanonicalMappingResult

class CanonicalMappingEngine:
    """Safe vehicle taxonomy mapping engine."""

    def __init__(self, session: Session):
        self.session = session
        self.repo = TaxonomyRepository(session)

    def resolve_vehicle(
        self,
        make: str,
        model: str,
        year: Optional[int] = None,
        variant: Optional[str] = None
    ) -> CanonicalMappingResult:
        """
        Deterministically resolves a vehicle record to its canonical identity.
        NEVER silently invents an identity or guesses when ambiguous.
        """
        clean_make = (make or "").strip()
        clean_model = (model or "").strip()
        clean_variant = (variant or "").strip() if variant else None

        # 1. Reject empty or invalid input strings
        if not clean_make or not clean_model:
            return CanonicalMappingResult(
                outcome=MappingOutcome.REJECTED,
                input_make=clean_make,
                input_model=clean_model,
                input_variant=clean_variant,
                input_year=year,
                canonical_vehicle_id=None,
                resolution_notes="Empty or invalid make/model input.",
                candidate_matches=[]
            )

        # 2. Resolve Manufacturer
        mfg = self.repo.find_manufacturer(clean_make)
        if not mfg:
            return CanonicalMappingResult(
                outcome=MappingOutcome.UNMAPPED,
                input_make=clean_make,
                input_model=clean_model,
                input_variant=clean_variant,
                input_year=year,
                canonical_vehicle_id=None,
                resolution_notes=f"Manufacturer '{clean_make}' is not recognized in canonical taxonomy.",
                candidate_matches=[]
            )

        is_mfg_alias = (mfg.name.lower() != clean_make.lower() and mfg.slug != slugify(clean_make))

        # 3. Resolve Model
        veh_model = self.repo.find_model(mfg.id, clean_model)
        if not veh_model:
            # Check available models under this manufacturer for reporting candidates
            all_models = self.repo.list_models_by_manufacturer(mfg.slug)
            similar = [m.name for m in all_models if clean_model.lower() in m.name.lower() or m.slug in slugify(clean_model)]
            return CanonicalMappingResult(
                outcome=MappingOutcome.UNMAPPED,
                input_make=clean_make,
                input_model=clean_model,
                input_variant=clean_variant,
                input_year=year,
                canonical_vehicle_id=None,
                resolution_notes=f"Model '{clean_model}' is not recognized under manufacturer '{mfg.name}'.",
                candidate_matches=similar
            )

        is_model_alias = (veh_model.name.lower() != clean_model.lower() and veh_model.slug != slugify(clean_model))

        # 4. Resolve Generation
        generations: List[VehicleGeneration] = veh_model.generations
        if not generations:
            canonical_id = f"{mfg.slug}::{veh_model.slug}"
            return CanonicalMappingResult(
                outcome=MappingOutcome.SAFE_ALIAS_MATCH if (is_mfg_alias or is_model_alias) else MappingOutcome.EXACT_MATCH,
                input_make=clean_make,
                input_model=clean_model,
                input_variant=clean_variant,
                input_year=year,
                canonical_vehicle_id=canonical_id,
                resolution_notes="Resolved to model-level canonical ID (no generations defined).",
                candidate_matches=[canonical_id]
            )

        matched_gens: List[VehicleGeneration] = []
        if year is not None:
            for g in generations:
                start = getattr(g, "year_start", getattr(g, "start_year", 1980))
                end = getattr(g, "year_end", getattr(g, "end_year", 2099)) or 2099
                if start <= year <= end:
                    matched_gens.append(g)

        # Ambiguity check for generations
        if len(matched_gens) > 1:
            candidates = [f"{mfg.slug}::{veh_model.slug}::{g.slug}" for g in matched_gens]
            return CanonicalMappingResult(
                outcome=MappingOutcome.AMBIGUOUS,
                input_make=clean_make,
                input_model=clean_model,
                input_variant=clean_variant,
                input_year=year,
                canonical_vehicle_id=None,
                resolution_notes=f"Year {year} overlaps multiple production generations ({[g.name for g in matched_gens]}). Disambiguation required.",
                candidate_matches=candidates
            )

        if len(matched_gens) == 0 and len(generations) > 1 and year is None:
            # Model has multiple generations but no year is provided to disambiguate
            candidates = [f"{mfg.slug}::{veh_model.slug}::{g.slug}" for g in generations]
            return CanonicalMappingResult(
                outcome=MappingOutcome.AMBIGUOUS,
                input_make=clean_make,
                input_model=clean_model,
                input_variant=clean_variant,
                input_year=year,
                canonical_vehicle_id=None,
                resolution_notes=f"Model has {len(generations)} generations; year or generation identifier required to disambiguate.",
                candidate_matches=candidates
            )

        target_gen = matched_gens[0] if len(matched_gens) == 1 else generations[0]

        # 5. Resolve Variant
        if clean_variant:
            var_slug = slugify(clean_variant)
            gen_variants: List[VehicleVariant] = target_gen.variants
            
            # Direct match
            exact_var = next((v for v in gen_variants if v.slug == var_slug or v.name.lower() == clean_variant.lower()), None)
            if exact_var:
                canonical_id = f"{mfg.slug}::{veh_model.slug}::{target_gen.slug}::{exact_var.slug}"
                outcome = MappingOutcome.SAFE_ALIAS_MATCH if (is_mfg_alias or is_model_alias) else MappingOutcome.EXACT_MATCH
                return CanonicalMappingResult(
                    outcome=outcome,
                    input_make=clean_make,
                    input_model=clean_model,
                    input_variant=clean_variant,
                    input_year=year,
                    canonical_vehicle_id=canonical_id,
                    resolution_notes=f"Successfully mapped to variant '{exact_var.name}'.",
                    candidate_matches=[canonical_id]
                )

            # Substring / Alias variant match
            matching_vars = [v for v in gen_variants if var_slug in v.slug or v.slug in var_slug]
            if len(matching_vars) == 1:
                matched_v = matching_vars[0]
                canonical_id = f"{mfg.slug}::{veh_model.slug}::{target_gen.slug}::{matched_v.slug}"
                return CanonicalMappingResult(
                    outcome=MappingOutcome.SAFE_ALIAS_MATCH,
                    input_make=clean_make,
                    input_model=clean_model,
                    input_variant=clean_variant,
                    input_year=year,
                    canonical_vehicle_id=canonical_id,
                    resolution_notes=f"Safely mapped variant via alias/substring to '{matched_v.name}'.",
                    candidate_matches=[canonical_id]
                )
            elif len(matching_vars) > 1:
                candidates = [f"{mfg.slug}::{veh_model.slug}::{target_gen.slug}::{v.slug}" for v in matching_vars]
                return CanonicalMappingResult(
                    outcome=MappingOutcome.AMBIGUOUS,
                    input_make=clean_make,
                    input_model=clean_model,
                    input_variant=clean_variant,
                    input_year=year,
                    canonical_vehicle_id=None,
                    resolution_notes=f"Variant string '{clean_variant}' matches multiple variants ({[v.name for v in matching_vars]}).",
                    candidate_matches=candidates
                )
            else:
                # Variant not found under this generation
                canonical_id = f"{mfg.slug}::{veh_model.slug}::{target_gen.slug}"
                return CanonicalMappingResult(
                    outcome=MappingOutcome.UNMAPPED,
                    input_make=clean_make,
                    input_model=clean_model,
                    input_variant=clean_variant,
                    input_year=year,
                    canonical_vehicle_id=canonical_id,
                    resolution_notes=f"Variant '{clean_variant}' not found in generation '{target_gen.name}'. Mapped to generation level only.",
                    candidate_matches=[canonical_id]
                )

        # No variant specified -> Generation level mapping
        canonical_id = f"{mfg.slug}::{veh_model.slug}::{target_gen.slug}"
        outcome = MappingOutcome.SAFE_ALIAS_MATCH if (is_mfg_alias or is_model_alias) else MappingOutcome.EXACT_MATCH
        return CanonicalMappingResult(
            outcome=outcome,
            input_make=clean_make,
            input_model=clean_model,
            input_variant=None,
            input_year=year,
            canonical_vehicle_id=canonical_id,
            resolution_notes=f"Mapped to generation '{target_gen.name}'.",
            candidate_matches=[canonical_id]
        )
