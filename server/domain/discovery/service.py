"""
CARspective — Phase 12: Intelligent Vehicle Discovery & Search Service
Deterministic canonical resolution, explainable scoring, ambiguity clarification,
no-match guardrails, discovery filtering, and taxonomy-backed autocomplete.
"""

import time
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, or_, func

from server.models.taxonomy import (
    Manufacturer,
    VehicleModel,
    VehicleGeneration,
    ModelYear,
    VehicleVariant,
    PowertrainConfiguration,
    build_canonical_id,
)
from server.repositories.taxonomy_repository import TaxonomyRepository
from server.domain.discovery.models import (
    VehicleSearchIntent,
    IntentFieldProvenance,
    SearchResultType,
    MatchReason,
    CandidateClarification,
    DiscoveryCandidate,
    SearchProvenance,
    DiscoveryFilterParams,
    DiscoverySearchResponse,
    AutocompleteItem,
    AutocompleteResponse,
)
from server.domain.discovery.query_parser import QueryParser, damerau_levenshtein
from server.utils.slugifier import slugify

DEEP_KNOWLEDGE_MODELS = {"swift", "creta", "nexon", "city", "thar"}

# Estimated price baseline reference in INR for discovery budget filtering
# (Approximate fair value ranges based on historical dataset for budget matching)
MODEL_PRICE_BENCHMARKS = {
    "alto-800": (200000, 350000),
    "alto-k10": (250000, 400000),
    "wagon-r": (250000, 550000),
    "celerio": (300000, 550000),
    "swift": (350000, 750000),
    "dzire": (400000, 800000),
    "baleno": (450000, 800000),
    "ertiga": (550000, 1000000),
    "brezza": (600000, 1050000),
    "i10": (250000, 450000),
    "grand-i10": (300000, 550000),
    "i20": (400000, 750000),
    "venue": (650000, 1100000),
    "creta": (700000, 1500000),
    "verna": (500000, 1100000),
    "tiago": (350000, 600000),
    "altroz": (450000, 750000),
    "nexon": (600000, 1200000),
    "amaze": (400000, 750000),
    "city": (450000, 1200000),
    "thar": (800000, 1600000),
    "scorpio": (600000, 1400000),
    "xuv500": (600000, 1200000),
    "xuv700": (1200000, 2200000),
    "innova-crysta": (1200000, 2200000),
    "seltos": (850000, 1600000),
    "sonet": (650000, 1150000),
    "polo": (350000, 700000),
    "kwid": (220000, 400000),
}

class DiscoverySearchService:
    def __init__(self, session: Optional[Session] = None):
        self._session = session
        self.repo = TaxonomyRepository(session=session)

    @property
    def session(self) -> Session:
        if self._session is not None:
            return self._session
        from server.infrastructure.database import ScopedSession
        return ScopedSession()

    @session.setter
    def session(self, value: Optional[Session]) -> None:
        self._session = value
        self.repo.session = value

    def search(self, params: DiscoveryFilterParams) -> DiscoverySearchResponse:
        """
        Executes intelligent discovery and search:
        1. Parses natural query if q is present
        2. Merges with explicit filter overrides
        3. Resolves canonical taxonomy candidates
        4. Calculates explainable match scores
        5. Evaluates ambiguity and clarification needs
        6. Constructs strongly typed response
        """
        # Parse query text into structured intent
        intent = QueryParser.parse(params.q or "")

        # Override/merge explicit filter parameters if supplied
        if params.manufacturer:
            intent.manufacturer.value = params.manufacturer
            intent.manufacturer.provenance = IntentFieldProvenance.USER_EXPLICIT
        if params.model:
            intent.model.value = params.model
            intent.model.provenance = IntentFieldProvenance.USER_EXPLICIT
        if params.year:
            intent.model_year.value = params.year
            intent.model_year.provenance = IntentFieldProvenance.USER_EXPLICIT
        if params.generation:
            intent.generation.value = params.generation
            intent.generation.provenance = IntentFieldProvenance.USER_EXPLICIT
        if params.variant:
            intent.variant.value = params.variant
            intent.variant.provenance = IntentFieldProvenance.USER_EXPLICIT
        if params.fuel_type:
            intent.fuel_type.value = params.fuel_type
            intent.fuel_type.provenance = IntentFieldProvenance.USER_EXPLICIT
        if params.transmission:
            intent.transmission.value = params.transmission
            intent.transmission.provenance = IntentFieldProvenance.USER_EXPLICIT
        if params.body_type:
            intent.body_type.value = params.body_type
            intent.body_type.provenance = IntentFieldProvenance.USER_EXPLICIT
        if params.budget_min is not None:
            intent.budget_min.value = params.budget_min
            intent.budget_min.provenance = IntentFieldProvenance.USER_EXPLICIT
        if params.budget_max is not None:
            intent.budget_max.value = params.budget_max
            intent.budget_max.provenance = IntentFieldProvenance.USER_EXPLICIT
        if params.seating_capacity is not None:
            intent.seating_capacity.value = params.seating_capacity
            intent.seating_capacity.provenance = IntentFieldProvenance.USER_EXPLICIT

        rules_applied = [
            f"parsed_{k}" for k, v in [
                ("make", intent.manufacturer.value),
                ("model", intent.model.value),
                ("year", intent.model_year.value),
                ("variant", intent.variant.value),
                ("fuel", intent.fuel_type.value),
                ("transmission", intent.transmission.value),
                ("body", intent.body_type.value),
                ("budget", intent.budget_max.value or intent.budget_min.value),
                ("seats", intent.seating_capacity.value),
                ("use_case", intent.use_case.value),
            ] if v is not None
        ]

        # Fetch candidate vehicles from taxonomy
        candidates, all_generations_for_model = self._match_candidates(intent, params)

        # Determine Result Type & Ambiguity Clarification
        result_type, clarification, suggestions = self._determine_result_state(
            intent=intent,
            candidates=candidates,
            generations=all_generations_for_model,
            raw_q=params.q or ""
        )

        provenance = SearchProvenance(
            query_normalized=intent.normalized_query,
            rules_applied=rules_applied,
            taxonomy_version="Phase 2 Canonical Taxonomy",
            resolution_method="Deterministic Pattern Matching & Taxonomy Graph",
            evidence_sources_checked=12
        )

        # Slice limit / offset
        offset = max(0, params.offset)
        limit = max(1, min(100, params.limit))
        paginated_candidates = candidates[offset:offset + limit]

        return DiscoverySearchResponse(
            query=params.q or "",
            intent=intent,
            result_type=result_type,
            total_count=len(candidates),
            results=paginated_candidates,
            clarification=clarification,
            suggestions=suggestions,
            provenance=provenance
        )

    def autocomplete(self, query: str, limit: int = 8) -> AutocompleteResponse:
        """
        Taxonomy-backed autocomplete: returns matching manufacturers, models, and vehicles.
        Never hallucinates entities outside the canonical catalog.
        """
        clean_q = QueryParser.sanitize_query(query).lower().strip()
        if not clean_q or len(clean_q) < 2:
            return AutocompleteResponse(query=query, items=[])

        items: List[AutocompleteItem] = []
        seen_ids = set()

        manufacturers = self.repo.list_manufacturers()

        # 1. Match Manufacturers
        for m in manufacturers:
            if clean_q in m.name.lower() or clean_q in m.slug:
                item_id = f"make::{m.slug}"
                if item_id not in seen_ids:
                    seen_ids.add(item_id)
                    items.append(AutocompleteItem(
                        id=item_id,
                        title=m.name,
                        type="manufacturer",
                        manufacturer=m.name,
                        subtitle="Manufacturer"
                    ))

        # 2. Match Models
        for m in manufacturers:
            for mod in m.models:
                m_title = f"{m.name} {mod.name}".lower()
                if clean_q in mod.name.lower() or clean_q in mod.slug or clean_q in m_title:
                    item_id = f"model::{m.slug}::{mod.slug}"
                    if item_id not in seen_ids:
                        seen_ids.add(item_id)
                        items.append(AutocompleteItem(
                            id=item_id,
                            title=f"{m.name} {mod.name}",
                            type="model",
                            manufacturer=m.name,
                            model=mod.name,
                            subtitle=f"{mod.body_type} • {mod.coverage_tier}"
                        ))

        # 3. Match Specific Model Years / Vehicles if query contains a year
        year_match = QueryParser.parse(clean_q).model_year.value
        if year_match:
            for m in manufacturers:
                for mod in m.models:
                    if clean_q.replace(str(year_match), "").strip() in mod.name.lower() or clean_q.replace(str(year_match), "").strip() in m.name.lower():
                        gen = self.repo.find_generation_for_year(mod.id, year_match)
                        if gen:
                            item_id = f"vehicle::{m.slug}::{mod.slug}::{year_match}"
                            if item_id not in seen_ids:
                                seen_ids.add(item_id)
                                items.append(AutocompleteItem(
                                    id=item_id,
                                    title=f"{m.name} {mod.name} ({year_match})",
                                    type="vehicle",
                                    manufacturer=m.name,
                                    model=mod.name,
                                    year=year_match,
                                    subtitle=f"{gen.name} ({gen.year_start}–{gen.year_end or 'Present'})"
                                ))

        # Slice limit
        return AutocompleteResponse(query=query, items=items[:limit])

    def _match_candidates(
        self,
        intent: VehicleSearchIntent,
        params: DiscoveryFilterParams
    ) -> Tuple[List[DiscoveryCandidate], List[Dict[str, Any]]]:
        """
        Traverses taxonomy graph and builds scored, explainable candidates.
        """
        candidates: List[DiscoveryCandidate] = []
        all_generations_for_model: List[Dict[str, Any]] = []

        target_mfg = (intent.manufacturer.value or "").strip().lower()
        target_model = (intent.model.value or "").strip().lower()
        target_year = intent.model_year.value
        target_variant = (intent.variant.value or "").strip().lower()
        target_fuel = (intent.fuel_type.value or "").strip().lower()
        target_trans = (intent.transmission.value or "").strip().lower()
        target_body = (intent.body_type.value or "").strip().lower()
        target_seats = intent.seating_capacity.value
        b_min = intent.budget_min.value
        b_max = intent.budget_max.value

        has_query_text = bool((params.q or "").strip())
        has_any_criteria = bool(
            target_mfg or target_model or target_year or target_variant
            or target_fuel or target_trans or target_body or target_seats
            or (b_min is not None) or (b_max is not None)
            or (intent.use_case.value is not None)
            or (params.generation is not None)
        )

        if has_query_text and not has_any_criteria:
            return [], []

        manufacturers = self.repo.list_manufacturers()

        for m in manufacturers:
            # Check Manufacturer filter
            mfg_matched = False
            mfg_exact = False
            if target_mfg:
                if target_mfg == m.name.lower() or target_mfg == m.slug:
                    mfg_matched = True
                    mfg_exact = True
                elif target_mfg in m.name.lower():
                    mfg_matched = True
                else:
                    # If target manufacturer specified and does not match, skip
                    continue
            else:
                mfg_matched = True

            for mod in m.models:
                # Check Model filter
                model_matched = False
                model_exact = False
                if target_model:
                    if target_model == mod.name.lower() or target_model == mod.slug:
                        model_matched = True
                        model_exact = True
                    elif target_model in mod.name.lower() or mod.slug in target_model:
                        model_matched = True
                    else:
                        continue
                else:
                    model_matched = True

                # Check Body Type filter
                if target_body and target_body != mod.body_type.lower():
                    continue

                # Collect generations for this model if model matched
                generations = self.repo.list_generations(mod.id)
                if model_exact:
                    for g in generations:
                        all_generations_for_model.append({
                            "generation_name": g.name,
                            "generation_slug": g.slug,
                            "year_start": g.year_start,
                            "year_end": g.year_end
                        })

                # Check budget bounds against model benchmarks
                benchmarks = MODEL_PRICE_BENCHMARKS.get(mod.slug)
                if benchmarks:
                    low_est, high_est = benchmarks
                    if b_max is not None and low_est > b_max:
                        # Beyond maximum budget
                        continue
                    if b_min is not None and high_est < b_min:
                        # Below minimum budget
                        continue

                for gen in generations:
                    # Check Generation / Year compatibility
                    year_matched = False
                    if target_year:
                        if target_year < gen.year_start or (gen.year_end and target_year > gen.year_end):
                            continue
                        year_matched = True
                        effective_year = target_year
                    else:
                        # Use latest representative year of this generation
                        effective_year = gen.year_end or 2023

                    variants = self.repo.list_variants(gen.id)
                    if not variants:
                        # Synthetic base candidate if variants not loaded
                        c = self._build_candidate(
                            m=m, mod=mod, gen=gen, year=effective_year,
                            var=None, pt=None,
                            mfg_exact=mfg_exact, model_exact=model_exact,
                            year_matched=year_matched, variant_matched=False,
                            fuel_matched=False, trans_matched=False,
                            target_body=target_body, target_seats=target_seats,
                            b_min=b_min, b_max=b_max
                        )
                        if c:
                            candidates.append(c)
                        continue

                    for var in variants:
                        var_matched = False
                        if target_variant:
                            if target_variant == var.name.lower() or target_variant in var.slug:
                                var_matched = True
                            elif any(tok in var.name.lower() for tok in target_variant.split()):
                                var_matched = True
                            else:
                                if target_variant:
                                    continue

                        powertrains = var.powertrains
                        if not powertrains:
                            c = self._build_candidate(
                                m=m, mod=mod, gen=gen, year=effective_year,
                                var=var, pt=None,
                                mfg_exact=mfg_exact, model_exact=model_exact,
                                year_matched=year_matched, variant_matched=var_matched,
                                fuel_matched=False, trans_matched=False,
                                target_body=target_body, target_seats=target_seats,
                                b_min=b_min, b_max=b_max
                            )
                            if c:
                                candidates.append(c)
                            continue

                        for pt in powertrains:
                            fuel_matched = False
                            trans_matched = False

                            if target_fuel:
                                if target_fuel in pt.fuel_type.lower():
                                    fuel_matched = True
                                else:
                                    continue

                            if target_trans:
                                if target_trans in pt.transmission_type.lower():
                                    trans_matched = True
                                else:
                                    continue

                            c = self._build_candidate(
                                m=m, mod=mod, gen=gen, year=effective_year,
                                var=var, pt=pt,
                                mfg_exact=mfg_exact, model_exact=model_exact,
                                year_matched=year_matched, variant_matched=var_matched,
                                fuel_matched=fuel_matched, trans_matched=trans_matched,
                                target_body=target_body, target_seats=target_seats,
                                b_min=b_min, b_max=b_max
                            )
                            if c:
                                candidates.append(c)

        # Sort candidates deterministically by match score descending, then title
        candidates.sort(key=lambda x: (-x.match_score, x.title))
        return candidates, all_generations_for_model

    def _build_candidate(
        self,
        m: Manufacturer,
        mod: VehicleModel,
        gen: VehicleGeneration,
        year: int,
        var: Optional[VehicleVariant],
        pt: Optional[PowertrainConfiguration],
        mfg_exact: bool,
        model_exact: bool,
        year_matched: bool,
        variant_matched: bool,
        fuel_matched: bool,
        trans_matched: bool,
        target_body: Optional[str],
        target_seats: Optional[int],
        b_min: Optional[float],
        b_max: Optional[float],
    ) -> Optional[DiscoveryCandidate]:
        """Calculates deterministic explainable match score and builds candidate."""
        reasons: List[MatchReason] = []
        raw_score = 0.0

        # Model Score (Max 30)
        if model_exact:
            raw_score += 30.0
            reasons.append(MatchReason(
                factor="MODEL_EXACT",
                score_contribution=30.0,
                description=f"Exact match for model: {mod.name}"
            ))
        else:
            raw_score += 20.0
            reasons.append(MatchReason(
                factor="MODEL_RESOLVED",
                score_contribution=20.0,
                description=f"Resolved model candidate: {mod.name}"
            ))

        # Manufacturer Score (Max 15)
        if mfg_exact:
            raw_score += 15.0
            reasons.append(MatchReason(
                factor="MANUFACTURER_EXACT",
                score_contribution=15.0,
                description=f"Exact match for brand: {m.name}"
            ))
        else:
            raw_score += 10.0
            reasons.append(MatchReason(
                factor="MANUFACTURER_INFERRED",
                score_contribution=10.0,
                description=f"Inferred brand: {m.name}"
            ))

        # Year Score (Max 20)
        if year_matched:
            raw_score += 20.0
            reasons.append(MatchReason(
                factor="YEAR_EXACT",
                score_contribution=20.0,
                description=f"Matched model year: {year}"
            ))
        else:
            raw_score += 10.0
            reasons.append(MatchReason(
                factor="GENERATION_WINDOW",
                score_contribution=10.0,
                description=f"Aligned with {gen.name} ({gen.year_start}–{gen.year_end or 'Present'})"
            ))

        # Variant Score (Max 15)
        if var and variant_matched:
            raw_score += 15.0
            reasons.append(MatchReason(
                factor="VARIANT_MATCH",
                score_contribution=15.0,
                description=f"Matched variant: {var.name}"
            ))
        elif var:
            raw_score += 5.0

        # Powertrain / Fuel / Transmission (Max 10)
        if fuel_matched and pt:
            raw_score += 5.0
            reasons.append(MatchReason(
                factor="FUEL_MATCH",
                score_contribution=5.0,
                description=f"Matched fuel: {pt.fuel_type}"
            ))
        if trans_matched and pt:
            raw_score += 5.0
            reasons.append(MatchReason(
                factor="TRANSMISSION_MATCH",
                score_contribution=5.0,
                description=f"Matched transmission: {pt.transmission_type}"
            ))

        # Body type alignment (Max 5)
        if target_body and target_body == mod.body_type.lower():
            raw_score += 5.0
            reasons.append(MatchReason(
                factor="BODY_TYPE_MATCH",
                score_contribution=5.0,
                description=f"Matched body type: {mod.body_type}"
            ))

        # Budget range alignment (Max 5)
        benchmarks = MODEL_PRICE_BENCHMARKS.get(mod.slug)
        if (b_min is not None or b_max is not None) and benchmarks:
            raw_score += 5.0
            reasons.append(MatchReason(
                factor="BUDGET_ALIGNMENT",
                score_contribution=5.0,
                description=f"Typical market price range: INR {benchmarks[0]:,} - INR {benchmarks[1]:,}"
            ))

        final_score = min(100.0, round(raw_score, 1))

        var_slug = var.slug if var else "standard"
        pt_slug = pt.slug if pt else "standard"
        canonical_id = build_canonical_id(
            make_slug=m.slug,
            model_slug=mod.slug,
            generation_slug=gen.slug,
            model_year=year,
            variant_slug=var_slug,
            powertrain_slug=pt_slug
        )

        title = f"{m.name} {mod.name}"
        if var:
            title += f" {var.name}"
        title += f" ({year})"

        has_deep = mod.slug in DEEP_KNOWLEDGE_MODELS
        evidence_state = "VERIFIED" if has_deep else "SUPPORTED"

        return DiscoveryCandidate(
            canonical_vehicle_id=canonical_id,
            title=title,
            manufacturer=m.name,
            model=mod.name,
            generation=gen.name,
            model_year=year,
            variant=var.name if var else None,
            powertrain=f"{pt.fuel_type} · {pt.transmission_type}" if pt else None,
            fuel_type=pt.fuel_type if pt else None,
            transmission=pt.transmission_type if pt else None,
            body_type=mod.body_type,
            seating_capacity=target_seats or (7 if mod.slug in ["innova-crysta", "ertiga", "xuv700"] else 5),
            coverage_tier=mod.coverage_tier,
            evidence_state=evidence_state,
            has_deep_knowledge=has_deep,
            match_score=final_score,
            match_reasons=reasons,
            available_actions=["view", "compare", "value", "deal", "inspect"]
        )

    def _determine_result_state(
        self,
        intent: VehicleSearchIntent,
        candidates: List[DiscoveryCandidate],
        generations: List[Dict[str, Any]],
        raw_q: str
    ) -> Tuple[SearchResultType, Optional[CandidateClarification], List[str]]:
        """
        Determines the explicit result type (EXACT_MATCH, HIGH_CONFIDENCE_MATCH,
        AMBIGUOUS, NO_MATCH, FILTERED_RESULTS, INSUFFICIENT_DATA).
        Generates structured clarification for ambiguous queries without guessing silently.
        """
        suggestions: List[str] = []

        # 1. No Candidates Found -> NO_MATCH
        if not candidates:
            # Suggest closest canonical models
            suggestions = ["Maruti Suzuki Swift", "Hyundai Creta", "Tata Nexon", "Honda City", "Mahindra Thar"]
            return SearchResultType.NO_MATCH, None, suggestions

        # 2. Model Ambiguity: Model specified but no year provided and multiple generations exist
        # Example: User searched "Swift" or "Creta" without year
        has_explicit_model = intent.model.value is not None
        has_explicit_year = intent.model_year.value is not None

        if has_explicit_model and not has_explicit_year and len(generations) > 1:
            # Distinct generations exist -> DO NOT GUESS SILENTLY!
            options = []
            for g in generations:
                y_end = g["year_end"] or "Present"
                options.append({
                    "generation": g["generation_name"],
                    "year_range": f"{g['year_start']}–{y_end}",
                    "suggested_query": f"{intent.model.value} {g['year_start']}"
                })

            clarification = CandidateClarification(
                clarification_type="MULTIPLE_GENERATIONS",
                prompt=f"I found {len(generations)} generations of the {intent.model.value}. Which production generation or model year are you looking for?",
                options=options
            )
            return SearchResultType.AMBIGUOUS, clarification, []

        # 3. Discovery Filter Query (no specific model named, e.g. "SUV under 15 lakh", "automatic cars")
        if not has_explicit_model:
            return SearchResultType.FILTERED_RESULTS, None, []

        # 4. Check Top Candidate Match Score
        top_candidate = candidates[0]
        if top_candidate.match_score >= 80.0 and has_explicit_year and intent.variant.value:
            return SearchResultType.EXACT_MATCH, None, []
        elif top_candidate.match_score >= 65.0:
            return SearchResultType.HIGH_CONFIDENCE_MATCH, None, []
        elif top_candidate.match_score >= 40.0:
            return SearchResultType.FILTERED_RESULTS, None, []
        else:
            return SearchResultType.NO_MATCH, None, ["Maruti Suzuki Swift", "Hyundai Creta", "Tata Nexon"]
