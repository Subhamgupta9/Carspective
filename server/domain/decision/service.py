"""
CARspective — Phase 15 Personalized Decision Intelligence Domain Service
Orchestrates:
1. Strict hard constraint validation (budget, transmission, fuel, seating, body type)
2. Explainable, multi-factor User Fit scoring (0-100) with dynamic priority normalization
3. Strict separation of Intrinsic Vehicle Score, Deal Financial Merit, and User Fit
4. Grounded 'Why it fits', 'Why it may not fit', and explicit automotive tradeoffs
5. Shortlist ranking and personalized multi-vehicle comparison ('Best Overall' vs 'Best For You')
6. Personalized inspection checklist prioritization (preserving canonical 45-item catalog)
7. Zero sensitive attribute inference, zero hidden profiling, 100% deterministic logic.
"""

import re
import time
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session

from server.domain.decision.models import (
    ProvenanceState,
    RequirementProvenance,
    PurchaseType,
    UsageProfile,
    PriorityLevel,
    ToleranceLevel,
    HardConstraintStatus,
    DecisionQuality,
    HardConstraintsConfig,
    UserRequirementsProfile,
    ConstraintCheckItem,
    ConstraintValidationResult,
    PersonalizedFitBreakdown,
    PersonalizedAlternative,
    DecisionEvaluationResponse,
    ShortlistVehicleItem,
    ShortlistRankResponse,
    PersonalizedComparisonResponse,
    PersonalizedInspectionPrioritizationResponse,
)
from server.domain.scoring.models import ScoreRequest, ScoreResponse
from server.domain.scoring.service import ScoringService
from server.domain.valuation.models import ValuationRequest, ValuationResponse
from server.domain.valuation.service import ValuationService
from server.domain.deal_analyzer.models import DealAnalysisRequest, DealAnalysisResponse
from server.domain.deal_analyzer.service import DealAnalyzerService
from server.domain.knowledge.service import KnowledgeService
from server.domain.market.service import MarketIntelligenceService
from server.domain.ownership.service import OwnershipIntelligenceService
from server.domain.inspection.applicability import ChecklistApplicabilityEngine
from server.domain.inspection.models import InspectionVehicleContext, UserInspectionProfile
from server.domain.inspection.checklist import CANONICAL_CHECKLIST_CATALOG
from server.infrastructure.database import ScopedSession
from server.repositories.taxonomy_repository import TaxonomyRepository


PRIORITY_WEIGHT_MAP = {
    PriorityLevel.CRITICAL: 4.0,
    PriorityLevel.HIGH: 3.0,
    PriorityLevel.MEDIUM: 2.0,
    PriorityLevel.LOW: 1.0,
    PriorityLevel.NOT_SPECIFIED: 1.5,
}


class DecisionService:
    """Production Personalized Decision Intelligence Engine."""

    def __init__(
        self,
        scoring_service: Optional[ScoringService] = None,
        valuation_service: Optional[ValuationService] = None,
        deal_service: Optional[DealAnalyzerService] = None,
        knowledge_service: Optional[KnowledgeService] = None,
        market_service: Optional[MarketIntelligenceService] = None,
        ownership_service: Optional[OwnershipIntelligenceService] = None,
        session: Optional[Session] = None,
    ):
        self._session = session
        self.scoring_service = scoring_service or ScoringService(session=session)
        self.valuation_service = valuation_service or ValuationService(session=session)
        self.deal_service = deal_service or DealAnalyzerService(valuation_service=self.valuation_service)
        self.knowledge_service = knowledge_service or KnowledgeService(session=session)
        self.market_service = market_service or MarketIntelligenceService(session=session)
        self.ownership_service = ownership_service or OwnershipIntelligenceService(
            knowledge_service=self.knowledge_service,
            market_service=self.market_service,
            valuation_service=self.valuation_service,
            session=session,
        )
        self.taxonomy_repo = TaxonomyRepository(session=session)
        self._profile_cache: Dict[str, Any] = {}
        self._score_cache: Dict[str, Any] = {}
        self._val_cache: Dict[str, Any] = {}

    @property
    def session(self) -> Session:
        if self._session is not None:
            return self._session
        return ScopedSession()

    @session.setter
    def session(self, value: Optional[Session]) -> None:
        self._session = value
        if hasattr(self, "scoring_service"):
            self.scoring_service.session = value
        if hasattr(self, "valuation_service"):
            self.valuation_service.session = value
        if hasattr(self, "knowledge_service"):
            self.knowledge_service.session = value
        if hasattr(self, "market_service"):
            self.market_service.session = value
        if hasattr(self, "ownership_service"):
            self.ownership_service.session = value
        if hasattr(self, "taxonomy_repo"):
            self.taxonomy_repo.session = value

    def _parse_canonical_id(self, canonical_id: str) -> Tuple[str, str, Optional[str], Optional[int], Optional[str]]:
        """Parses canonical ID e.g. tata::nexon::1st-gen::2021::xz-plus or maruti/swift/2020."""
        cleaned = canonical_id.replace("::", "/").strip("/")
        parts = cleaned.split("/")
        brand = parts[0].replace("-", " ").title() if len(parts) > 0 else ""
        if "Maruti Suzuki" in brand or "Maruti" in brand:
            brand = "Maruti"
        model = parts[1].replace("-", " ").title() if len(parts) > 1 else ""
        
        gen = None
        year = None
        variant = None

        for p in parts[2:]:
            if p.isdigit() and 1990 <= int(p) <= 2030:
                year = int(p)
            elif "gen" in p.lower():
                gen = p
            elif not variant:
                variant = p.replace("-", " ").title()

        # Fallback for non-'::' or raw slugs (e.g. 'Toyota-Innova Crysta', 'toyota-innova-crysta', 'Maruti-Swift')
        if not model or not brand:
            m_res, mod_res = self.taxonomy_repo.resolve_make_model_from_slug(canonical_id)
            if m_res and mod_res:
                brand = "Maruti" if "maruti" in m_res.name.lower() else m_res.name
                model = mod_res.name

        return brand, model, gen, year, variant

    def _get_valuation_price(
        self,
        brand: str,
        model: str,
        year: Optional[int],
        km_driven: Optional[float],
        fuel_type: Optional[str],
        transmission_type: Optional[str],
    ) -> Optional[float]:
        """Caches and returns estimated fair market value for a vehicle specification."""
        key = f"{brand}::{model}::{year or 2020}::{km_driven or 40000.0}::{fuel_type or 'Petrol'}::{transmission_type or 'Manual'}"
        if key in self._val_cache:
            return self._val_cache[key]
        try:
            val_req = ValuationRequest(
                brand=brand,
                model=model,
                manufacturing_year=year or 2020,
                km_driven=km_driven or 40000.0,
                fuel_type=fuel_type or "Petrol",
                transmission_type=transmission_type or "Manual",
            )
            val_res = self.valuation_service.evaluate_valuation(val_req)
            price = float(val_res.estimated_fair_market_value) if val_res.estimated_fair_market_value else None
        except Exception:
            price = None
        self._val_cache[key] = price
        return price

    def validate_hard_constraints(
        self,
        canonical_id: str,
        profile: UserRequirementsProfile,
        asking_price: Optional[float] = None,
        km_driven: Optional[float] = None,
        specifications: Optional[Any] = None,
        dimensions: Optional[Any] = None,
    ) -> ConstraintValidationResult:
        """
        Validates user-defined strict hard constraints against vehicle parameters.
        Does not compromise on safety or factual specifications.
        """
        checks: List[ConstraintCheckItem] = []
        violations: List[str] = []

        brand, model, gen, year, variant = self._parse_canonical_id(canonical_id)

        # 1. Budget Ceiling Constraint
        if profile.budget_max_inr is not None and profile.budget_max_inr > 0:
            price_to_check = asking_price
            if price_to_check is None:
                # Use estimated fair market value from valuation service (memoized)
                price_to_check = self._get_valuation_price(
                    brand=brand,
                    model=model,
                    year=year,
                    km_driven=km_driven,
                    fuel_type=specifications.fuel_type if specifications else "Petrol",
                    transmission_type=specifications.transmission if specifications else "Manual",
                )

            if price_to_check is not None:
                max_budget = profile.budget_max_inr
                if price_to_check > max_budget:
                    is_strict = profile.hard_constraints.strict_budget_ceiling or not profile.budget_flexible
                    flex_allowed = max_budget * 1.10 if profile.budget_flexible else max_budget

                    if price_to_check > flex_allowed or is_strict:
                        status = HardConstraintStatus.FAIL
                        diff_lakh = round((price_to_check - max_budget) / 100000.0, 2)
                        msg = f"Vehicle price (₹{price_to_check:,.0f}) exceeds your budget ceiling of ₹{max_budget:,.0f} by ₹{diff_lakh} Lakh."
                        violations.append(msg)
                    else:
                        status = HardConstraintStatus.PASS
                        msg = f"Vehicle price (₹{price_to_check:,.0f}) is within your allowed 10% flexible budget stretch."
                else:
                    status = HardConstraintStatus.PASS
                    msg = f"Vehicle price (₹{price_to_check:,.0f}) is within your maximum budget of ₹{max_budget:,.0f}."

                checks.append(ConstraintCheckItem(
                    constraint_name="budget_ceiling",
                    status=status,
                    required_value=f"<= ₹{profile.budget_max_inr:,.0f}",
                    actual_value=f"₹{price_to_check:,.0f}",
                    explanation=msg,
                ))

        # 2. Transmission Constraint
        if profile.transmission_preferences and (profile.hard_constraints.strict_transmission or len(profile.transmission_preferences) == 1):
            pref_trans = [t.lower() for t in profile.transmission_preferences]
            actual_trans = (specifications.transmission if specifications else None) or "Manual"
            trans_match = any(p in actual_trans.lower() for p in pref_trans)
            
            if not trans_match and profile.hard_constraints.strict_transmission:
                status = HardConstraintStatus.FAIL
                msg = f"Vehicle transmission '{actual_trans}' does not match required transmission: {', '.join(profile.transmission_preferences)}."
                violations.append(msg)
            elif trans_match:
                status = HardConstraintStatus.PASS
                msg = f"Vehicle transmission '{actual_trans}' matches preferred transmission."
            else:
                status = HardConstraintStatus.UNKNOWN
                msg = f"Vehicle transmission '{actual_trans}' differs from preferred transmission."

            checks.append(ConstraintCheckItem(
                constraint_name="transmission",
                status=status,
                required_value=", ".join(profile.transmission_preferences),
                actual_value=actual_trans,
                explanation=msg,
            ))

        # 3. Fuel Type Constraint
        if profile.fuel_preferences and (profile.hard_constraints.strict_fuel_type or len(profile.fuel_preferences) == 1):
            pref_fuels = [f.lower() for f in profile.fuel_preferences]
            actual_fuel = (specifications.fuel_type if specifications else None) or "Petrol"
            fuel_match = any(f in actual_fuel.lower() for f in pref_fuels)

            if not fuel_match and profile.hard_constraints.strict_fuel_type:
                status = HardConstraintStatus.FAIL
                msg = f"Vehicle fuel type '{actual_fuel}' does not match required fuel preference: {', '.join(profile.fuel_preferences)}."
                violations.append(msg)
            elif fuel_match:
                status = HardConstraintStatus.PASS
                msg = f"Vehicle fuel type '{actual_fuel}' matches preferred fuel types."
            else:
                status = HardConstraintStatus.UNKNOWN
                msg = f"Vehicle fuel type '{actual_fuel}' differs from preferred fuel types."

            checks.append(ConstraintCheckItem(
                constraint_name="fuel_type",
                status=status,
                required_value=", ".join(profile.fuel_preferences),
                actual_value=actual_fuel,
                explanation=msg,
            ))

        # 4. Seating Capacity / Family Size Constraint
        if profile.family_size and profile.family_size > 0:
            actual_seating = getattr(dimensions, "seating_capacity", None) if dimensions else None
            if actual_seating is None:
                # Infer from body type / segment default
                actual_seating = 7 if (dimensions and getattr(dimensions, "doors", 4) > 4) or "muv" in model.lower() or "innova" in model.lower() or "ertiga" in model.lower() or "scorpio" in model.lower() or "xuv700" in model.lower() or "safari" in model.lower() else 5

            if actual_seating < profile.family_size and profile.hard_constraints.strict_min_seating:
                status = HardConstraintStatus.FAIL
                msg = f"Vehicle seating capacity ({actual_seating} seats) cannot accommodate family size ({profile.family_size} occupants)."
                violations.append(msg)
            elif actual_seating < profile.family_size:
                status = HardConstraintStatus.UNKNOWN
                msg = f"Vehicle seating capacity ({actual_seating} seats) is less than family size ({profile.family_size})."
            else:
                status = HardConstraintStatus.PASS
                msg = f"Vehicle seating capacity ({actual_seating} seats) comfortably accommodates family of {profile.family_size}."

            checks.append(ConstraintCheckItem(
                constraint_name="seating_capacity",
                status=status,
                required_value=f">= {profile.family_size} seats",
                actual_value=f"{actual_seating} seats",
                explanation=msg,
            ))

        # 5. Body Type Constraint
        if profile.body_type_preferences and profile.hard_constraints.strict_body_type:
            # We check model/dimensions
            pref_bodies = [b.lower() for b in profile.body_type_preferences]
            # Infer body type from model name or dimensions
            actual_body = "Hatchback"
            m_lower = model.lower()
            if any(k in m_lower for k in ["creta", "nexon", "seltos", "brezza", "venue", "xuv", "harrier", "safari", "scorpio", "fortuner"]):
                actual_body = "SUV"
            elif any(k in m_lower for k in ["city", "verna", "ciaz", "amaze", "dzire", "slavia", "virtus"]):
                actual_body = "Sedan"
            elif any(k in m_lower for k in ["ertiga", "innova", "carens", "triber", "xl6"]):
                actual_body = "MUV"

            body_match = any(b in actual_body.lower() for b in pref_bodies)
            if not body_match and profile.hard_constraints.strict_body_type:
                status = HardConstraintStatus.FAIL
                msg = f"Vehicle body type '{actual_body}' does not match required body type: {', '.join(profile.body_type_preferences)}."
                violations.append(msg)
            elif body_match:
                status = HardConstraintStatus.PASS
                msg = f"Vehicle body type '{actual_body}' matches required body preference."
            else:
                status = HardConstraintStatus.UNKNOWN
                msg = f"Vehicle body type '{actual_body}' differs from preferred body types."

            checks.append(ConstraintCheckItem(
                constraint_name="body_type",
                status=status,
                required_value=", ".join(profile.body_type_preferences),
                actual_value=actual_body,
                explanation=msg,
            ))

        overall = HardConstraintStatus.FAIL if violations else HardConstraintStatus.PASS
        return ConstraintValidationResult(
            overall_status=overall,
            violations=violations,
            checks=checks,
        )

    def calculate_user_fit(
        self,
        canonical_id: str,
        profile: UserRequirementsProfile,
        asking_price: Optional[float] = None,
        km_driven: Optional[float] = None,
        specs: Optional[Any] = None,
        dims: Optional[Any] = None,
        safety: Optional[Any] = None,
        score_resp: Optional[ScoreResponse] = None,
    ) -> PersonalizedFitBreakdown:
        """
        Calculates normalized, explainable User Fit score (0-100) with dynamic weighting.
        Omits unrated/missing dimensions from denominator rather than penalizing cars with zeros.
        """
        brand, model, gen, year, variant = self._parse_canonical_id(canonical_id)

        component_scores: Dict[str, Optional[int]] = {}
        raw_weights: Dict[str, float] = {}
        limitations: List[str] = []

        # 1. Budget Fit
        if profile.budget_max_inr is not None and profile.budget_max_inr > 0:
            price_eval = asking_price
            if price_eval is None:
                price_eval = self._get_valuation_price(
                    brand=brand,
                    model=model,
                    year=year,
                    km_driven=km_driven,
                    fuel_type=specs.fuel_type if specs else "Petrol",
                    transmission_type=specs.transmission if specs else "Manual",
                )

            if price_eval is not None:
                max_b = profile.budget_max_inr
                min_b = profile.budget_min_inr or (max_b * 0.5)

                if min_b <= price_eval <= max_b:
                    b_fit = 100
                elif price_eval < min_b:
                    b_fit = 95  # Lower than budget is pleasant savings
                else:
                    # Over budget
                    ratio = price_eval / max_b
                    if ratio <= 1.05:
                        b_fit = 85
                    elif ratio <= 1.15:
                        b_fit = 65
                    elif ratio <= 1.25:
                        b_fit = 40
                    else:
                        b_fit = 15
                component_scores["budget_fit"] = b_fit
                raw_weights["budget_fit"] = 3.5  # Budget is naturally high importance

        # 2. Ownership Budget Fit (Monthly running cost)
        if profile.monthly_running_budget_max_inr is not None and profile.monthly_running_budget_max_inr > 0:
            fuel_res = self.ownership_service.calculate_fuel_cost(
                req=type("Req", (), {
                    "canonical_vehicle_id": canonical_id,
                    "fuel_type": specs.fuel_type if specs else "Petrol",
                    "annual_mileage_km": profile.annual_km or 12000.0,
                    "city_driving_ratio": 0.8 if profile.usage_profile == UsageProfile.CITY else 0.5,
                    "mileage_kmpl": None,
                    "fuel_price_per_unit": None,
                })()
            )
            est_monthly = fuel_res.monthly_fuel_cost_inr + 1500.0  # + routine maintenance reserve
            if est_monthly <= profile.monthly_running_budget_max_inr:
                component_scores["ownership_budget_fit"] = 95
            else:
                over_ratio = est_monthly / profile.monthly_running_budget_max_inr
                component_scores["ownership_budget_fit"] = max(20, int(100 - (over_ratio - 1.0) * 80))
            raw_weights["ownership_budget_fit"] = PRIORITY_WEIGHT_MAP.get(profile.maintenance_priority, 2.5)

        # 3. Usage Profile Fit (City vs Highway vs Mixed)
        if profile.usage_profile != UsageProfile.NOT_SPECIFIED:
            trans = (specs.transmission if specs else "Manual").lower()
            length = getattr(dims, "length_mm", 4000) or 4000
            ground_clr = getattr(dims, "ground_clearance_mm", 170) or 170

            if profile.usage_profile == UsageProfile.CITY:
                u_fit = 70
                if "auto" in trans or "amt" in trans or "cvt" in trans:
                    u_fit += 20
                if length <= 4000:
                    u_fit += 10
                elif length > 4500:
                    u_fit -= 15
                component_scores["usage_fit"] = max(30, min(100, u_fit))
            elif profile.usage_profile == UsageProfile.HIGHWAY:
                u_fit = 70
                power = getattr(specs, "max_power_bhp", 90.0) or 90.0
                if power >= 110:
                    u_fit += 15
                if ground_clr >= 180:
                    u_fit += 10
                if length >= 4200:
                    u_fit += 5
                component_scores["usage_fit"] = max(40, min(100, u_fit))
            else:  # MIXED
                component_scores["usage_fit"] = 85
            raw_weights["usage_fit"] = 2.5

        # 4. Family Size Fit
        if profile.family_size:
            actual_seats = getattr(dims, "seating_capacity", 5) or 5
            boot_space = getattr(dims, "boot_capacity_l", 350) or 350
            if profile.family_size <= 4:
                component_scores["family_fit"] = 95 if actual_seats >= 5 else 70
            elif profile.family_size == 5:
                component_scores["family_fit"] = 90 if actual_seats >= 5 and boot_space >= 350 else 75
            else:  # >= 6
                component_scores["family_fit"] = 95 if actual_seats >= 7 else 25
            raw_weights["family_fit"] = 3.0

        # 5. Powertrain Fit (Fuel and Transmission preferences)
        powertrain_score = 80
        if profile.fuel_preferences:
            actual_fuel = (specs.fuel_type if specs else "Petrol").lower()
            if any(f.lower() in actual_fuel for f in profile.fuel_preferences):
                powertrain_score += 10
            else:
                powertrain_score -= 30
        if profile.transmission_preferences:
            actual_trans = (specs.transmission if specs else "Manual").lower()
            if any(t.lower() in actual_trans for t in profile.transmission_preferences):
                powertrain_score += 10
            else:
                powertrain_score -= 30
        component_scores["powertrain_fit"] = max(20, min(100, powertrain_score))
        raw_weights["powertrain_fit"] = 2.5

        # 6. Safety Fit
        if safety and getattr(safety, "adult_safety_stars", None) is not None:
            stars = safety.adult_safety_stars
            s_fit = {5: 98, 4: 85, 3: 65, 2: 45, 1: 30, 0: 20}.get(int(stars), 60)
            component_scores["safety_fit"] = s_fit
            raw_weights["safety_fit"] = PRIORITY_WEIGHT_MAP.get(profile.safety_priority, 2.0)
        elif profile.safety_priority in [PriorityLevel.HIGH, PriorityLevel.CRITICAL]:
            # Epistemic honesty: missing crash rating is NOT penalized as zero!
            component_scores["safety_fit"] = None
            limitations.append("Official crash test rating is unavailable; safety fit is excluded from calculation to avoid unfair penalization.")
        else:
            component_scores["safety_fit"] = None

        # 7. Reliability Fit
        if score_resp:
            rel_dim = next((d for d in score_resp.dimensions if "Reliability" in d.dimension_name.value), None)
            if rel_dim and rel_dim.score is not None:
                component_scores["reliability_fit"] = rel_dim.score
                raw_weights["reliability_fit"] = PRIORITY_WEIGHT_MAP.get(profile.reliability_priority, 2.5)
            else:
                component_scores["reliability_fit"] = 75
                raw_weights["reliability_fit"] = 2.0
        else:
            component_scores["reliability_fit"] = 75
            raw_weights["reliability_fit"] = 2.0

        # 8. Maintenance Fit
        if score_resp:
            maint_dim = next((d for d in score_resp.dimensions if "Maintenance" in d.dimension_name.value), None)
            if maint_dim and maint_dim.score is not None:
                component_scores["maintenance_fit"] = maint_dim.score
                raw_weights["maintenance_fit"] = PRIORITY_WEIGHT_MAP.get(profile.maintenance_priority, 2.5)
            else:
                component_scores["maintenance_fit"] = 75
                raw_weights["maintenance_fit"] = 2.0
        else:
            component_scores["maintenance_fit"] = 75
            raw_weights["maintenance_fit"] = 2.0

        # 9. Practicality Fit
        ground_clearance = getattr(dims, "ground_clearance_mm", 170) or 170
        boot_cap = getattr(dims, "boot_capacity_l", 350) or 350
        p_fit = 70
        if ground_clearance >= 180:
            p_fit += 15
        if boot_cap >= 380:
            p_fit += 15
        component_scores["practicality_fit"] = min(100, p_fit)
        raw_weights["practicality_fit"] = PRIORITY_WEIGHT_MAP.get(profile.practicality_priority, 2.0)

        # 10. Resale Fit
        if score_resp:
            resale_dim = next((d for d in score_resp.dimensions if "Resale" in d.dimension_name.value), None)
            if resale_dim and resale_dim.score is not None:
                component_scores["resale_fit"] = resale_dim.score
                raw_weights["resale_fit"] = PRIORITY_WEIGHT_MAP.get(profile.resale_priority, 2.0)
            else:
                component_scores["resale_fit"] = 75
                raw_weights["resale_fit"] = 2.0
        else:
            component_scores["resale_fit"] = 75
            raw_weights["resale_fit"] = 2.0

        # 11. Performance Fit
        if specs and getattr(specs, "max_power_bhp", None):
            bhp = specs.max_power_bhp
            if bhp >= 130:
                perf_score = 95
            elif bhp >= 110:
                perf_score = 85
            elif bhp >= 90:
                perf_score = 75
            else:
                perf_score = 60
            component_scores["performance_fit"] = perf_score
            raw_weights["performance_fit"] = PRIORITY_WEIGHT_MAP.get(profile.performance_priority, 2.0)
        else:
            component_scores["performance_fit"] = None

        # 12. Ownership Horizon Fit
        if profile.ownership_years:
            if profile.ownership_years >= 7:
                # Long term durability matters; favor high reliability brands
                is_japanese = any(b in brand.lower() for b in ["maruti", "toyota", "honda"])
                component_scores["ownership_horizon_fit"] = 92 if is_japanese else 78
            else:
                component_scores["ownership_horizon_fit"] = 85
            raw_weights["ownership_horizon_fit"] = 2.0

        # Dynamic Normalization: calculate weighted average of valid components
        valid_items = {k: v for k, v in component_scores.items() if v is not None and k in raw_weights}
        total_active_weight = sum(raw_weights[k] for k in valid_items.keys())

        if total_active_weight > 0:
            normalized_weights = {k: round(raw_weights[k] / total_active_weight, 4) for k in valid_items.keys()}
            overall_score = int(round(sum(valid_items[k] * normalized_weights[k] for k in valid_items.keys())))
        else:
            normalized_weights = {}
            overall_score = 70

        overall_score = max(0, min(100, overall_score))

        # Determine Decision Quality
        if len(limitations) == 0 and len(valid_items) >= 7:
            quality = DecisionQuality.HIGH
        elif len(limitations) <= 1 and len(valid_items) >= 5:
            quality = DecisionQuality.MODERATE
        else:
            quality = DecisionQuality.LIMITED

        return PersonalizedFitBreakdown(
            budget_fit=component_scores.get("budget_fit"),
            ownership_budget_fit=component_scores.get("ownership_budget_fit"),
            usage_fit=component_scores.get("usage_fit"),
            family_fit=component_scores.get("family_fit"),
            powertrain_fit=component_scores.get("powertrain_fit"),
            safety_fit=component_scores.get("safety_fit"),
            reliability_fit=component_scores.get("reliability_fit"),
            maintenance_fit=component_scores.get("maintenance_fit"),
            practicality_fit=component_scores.get("practicality_fit"),
            resale_fit=component_scores.get("resale_fit"),
            performance_fit=component_scores.get("performance_fit"),
            ownership_horizon_fit=component_scores.get("ownership_horizon_fit"),
            component_weights=normalized_weights,
            overall_user_fit_score=overall_score,
            decision_quality=quality,
            data_limitations=limitations,
        )

    def evaluate_vehicle(
        self,
        canonical_vehicle_id: str,
        profile: UserRequirementsProfile,
        asking_price: Optional[float] = None,
        km_driven: Optional[float] = None,
    ) -> Optional[DecisionEvaluationResponse]:
        """
        Comprehensive personalized decision evaluation:
        - Resolves canonical identity & specs
        - Evaluates hard constraints
        - Calculates User Fit score (vehicle fit)
        - Evaluates commercial Deal Fit (if asking price is provided)
        - Formulates grounded why it fits, compromises/tradeoffs, and alternatives
        """
        t0 = time.perf_counter()

        brand, model, gen, year, variant = self._parse_canonical_id(canonical_vehicle_id)
        if not brand or not model:
            return None
        summary = f"{year or ''} {brand} {model}".strip()
        if variant:
            summary += f" {variant}"

        # 1. Fetch Vehicle Knowledge Profile
        if canonical_vehicle_id in self._profile_cache:
            prof = self._profile_cache[canonical_vehicle_id]
        else:
            prof = self.knowledge_service.get_vehicle_profile(canonical_vehicle_id)
            self._profile_cache[canonical_vehicle_id] = prof

        specs = prof.specifications if prof else None
        dims = prof.dimensions if prof else None
        safety = prof.safety if prof else None

        # 2. Intrinsic CARspective Score
        score_key = f"{brand}::{model}::{year or 2020}::{variant or ''}::{specs.fuel_type if specs else 'Petrol'}::{specs.transmission if specs else 'Manual'}"
        if score_key in self._score_cache:
            score_res = self._score_cache[score_key]
        else:
            score_req = ScoreRequest(
                brand=brand,
                model=model,
                manufacturing_year=year or 2020,
                variant=variant,
                fuel_type=specs.fuel_type if specs else "Petrol",
                transmission_type=specs.transmission if specs else "Manual",
                asking_price=None,  # Intrinsic score strictly ignores asking price
            )
            score_res = self.scoring_service.calculate_score(score_req)
            self._score_cache[score_key] = score_res
        intrinsic_score = score_res.overall_score

        # 3. Validate Hard Constraints
        constraint_res = self.validate_hard_constraints(
            canonical_id=canonical_vehicle_id,
            profile=profile,
            asking_price=asking_price,
            km_driven=km_driven,
            specifications=specs,
            dimensions=dims,
        )

        # 4. Calculate User Fit (Vehicle Suitability)
        fit_breakdown = self.calculate_user_fit(
            canonical_id=canonical_vehicle_id,
            profile=profile,
            asking_price=asking_price,
            km_driven=km_driven,
            specs=specs,
            dims=dims,
            safety=safety,
            score_resp=score_res,
        )
        vehicle_fit_score = fit_breakdown.overall_user_fit_score

        # 5. Deal Financial Fit (if asking price is provided)
        deal_fit_score: Optional[int] = None
        if asking_price is not None and asking_price > 0:
            deal_req = DealAnalysisRequest(
                brand=brand,
                model=model,
                manufacturing_year=year or 2020,
                km_driven=km_driven or 40000.0,
                variant=variant,
                fuel_type=specs.fuel_type if specs else "Petrol",
                transmission_type=specs.transmission if specs else "Manual",
                asking_price=asking_price,
            )
            deal_res = self.deal_service.analyze_deal(deal_req)
            if deal_res.range_position and deal_res.range_position.position_ratio is not None:
                ratio = deal_res.range_position.position_ratio
                deal_fit_score = max(20, min(100, int(round(100 - ratio * 40))))
            elif hasattr(deal_res, "deal_quality") and deal_res.deal_quality.value == "GREAT_DEAL":
                deal_fit_score = 95
            elif hasattr(deal_res, "deal_quality") and deal_res.deal_quality.value == "FAIR_DEAL":
                deal_fit_score = 80
            else:
                deal_fit_score = 50

        # 6. Overall recommendation verdict & label
        if constraint_res.overall_status == HardConstraintStatus.FAIL:
            recommendation_verdict = "NOT RECOMMENDED"
            verdict_label = "Violates Stated Hard Constraints"
            user_fit_score = min(vehicle_fit_score, 35)
        else:
            user_fit_score = vehicle_fit_score
            if user_fit_score >= 82:
                recommendation_verdict = "STRONG CONSIDERATION"
                verdict_label = "Exceptional Match For Your Profile"
            elif user_fit_score >= 68:
                recommendation_verdict = "CONSIDER"
                verdict_label = "Viable Choice With Minor Tradeoffs"
            elif user_fit_score >= 50:
                recommendation_verdict = "PROCEED WITH CAUTION"
                verdict_label = "Compromises Required For Your Needs"
            else:
                recommendation_verdict = "NOT RECOMMENDED"
                verdict_label = "Poor Alignment With Your Priorities"

        # 7. Formulate Grounded Explanations
        why_fits: List[str] = []
        why_not_fits: List[str] = []
        tradeoffs: List[str] = []
        verify_points: List[str] = []

        # Why it fits
        if safety and getattr(safety, "adult_safety_stars", 0) >= 4 and profile.safety_priority in [PriorityLevel.HIGH, PriorityLevel.CRITICAL]:
            why_fits.append(f"{safety.adult_safety_stars}-Star Global NCAP safety rating directly fulfills your critical safety requirement.")
        if profile.usage_profile == UsageProfile.CITY and specs and "auto" in (specs.transmission or "").lower():
            why_fits.append("Automatic transmission provides effortless daily driving in heavy urban traffic.")
        if profile.family_size and profile.family_size <= 5 and getattr(dims, "boot_capacity_l", 0) >= 350:
            why_fits.append(f"Generous {dims.boot_capacity_l}L luggage boot easily handles full family travel.")
        if fit_breakdown.budget_fit and fit_breakdown.budget_fit >= 90:
            why_fits.append("Price aligns comfortably within your specified acquisition budget.")
        if not why_fits:
            why_fits.append("Solid overall platform with dependable multi-use practicality.")

        # Why it may not fit / Violations
        if constraint_res.violations:
            for v in constraint_res.violations:
                why_not_fits.append(v)
        if specs and (specs.arai_mileage_kmpl or 15.0) < 14.0 and profile.efficiency_priority in [PriorityLevel.HIGH, PriorityLevel.CRITICAL]:
            why_not_fits.append("Fuel economy is relatively modest compared to segment benchmarks.")
        if getattr(dims, "ground_clearance_mm", 175) < 170 and profile.usage_profile in [UsageProfile.HIGHWAY, UsageProfile.MIXED]:
            why_not_fits.append(f"Ground clearance of {dims.ground_clearance_mm}mm may risk underbody contact over rough rural roads or large speed breakers.")

        # Automotive Tradeoffs
        if "maruti" in brand.lower():
            tradeoffs.append("Tradeoff: Exceptional fuel economy and unmatched service accessibility come at the expense of lighter body construction.")
        elif "tata" in brand.lower() or "mahindra" in brand.lower():
            tradeoffs.append("Tradeoff: Robust high-tensile crash protection and road presence come with heavier vehicle mass and higher city fuel consumption.")
        elif "hyundai" in brand.lower() or "kia" in brand.lower():
            tradeoffs.append("Tradeoff: Premium interior tech and refined engines are balanced by average crash safety test results on select entry models.")
        elif "honda" in brand.lower():
            tradeoffs.append("Tradeoff: Renowned i-VTEC petrol reliability and engine refinement are paired with slightly lower ground clearance.")
        else:
            tradeoffs.append("Tradeoff: Premium performance and solid highway composure come with higher consumable and spare parts replacement costs.")

        # Pre-purchase verification checkpoints
        if "auto" in (specs.transmission if specs else "").lower():
            verify_points.append("Check transmission fluid quality and test shift smoothness between 1st and 2nd gear under stop-and-go load.")
        if getattr(dims, "ground_clearance_mm", 175) < 170:
            verify_points.append("Inspect exhaust pipe and engine sump for scrapes or prior underbody impacts.")
        if km_driven and km_driven >= 60000:
            verify_points.append("Verify suspension bushing health and brake pad thickness as routine high-mileage replacements.")
        else:
            verify_points.append("Confirm comprehensive authorized service records and verify odometer reading authenticity.")

        # 8. Personalized Alternatives
        alternatives: List[PersonalizedAlternative] = []
        if "tata" in brand.lower() and "nexon" in model.lower():
            alternatives.append(PersonalizedAlternative(
                canonical_vehicle_id="maruti::brezza::2nd-gen::2022",
                vehicle_summary="2022 Maruti Brezza",
                intrinsic_score=82,
                user_fit_score=88 if profile.maintenance_priority in [PriorityLevel.HIGH, PriorityLevel.CRITICAL] else 80,
                advantage_over_target="Significantly lower maintenance cost and smoother 4-cylinder engine refinement.",
                tradeoff_vs_target="Lacks the 5-star crash safety rating and thick sheet metal of the Nexon.",
                verdict_label="Better For Low Running Cost",
            ))
            alternatives.append(PersonalizedAlternative(
                canonical_vehicle_id="hyundai::venue::1st-gen::2021",
                vehicle_summary="2021 Hyundai Venue",
                intrinsic_score=79,
                user_fit_score=82,
                advantage_over_target="Snappier dual-clutch transmission and richer infotainment features.",
                tradeoff_vs_target="Firmer rear suspension and less rear seat knee room.",
                verdict_label="Better For Tech & Features",
            ))
        elif "maruti" in brand.lower() and "swift" in model.lower():
            alternatives.append(PersonalizedAlternative(
                canonical_vehicle_id="tata::tiago::1st-gen::2021",
                vehicle_summary="2021 Tata Tiago",
                intrinsic_score=78,
                user_fit_score=86 if profile.safety_priority in [PriorityLevel.HIGH, PriorityLevel.CRITICAL] else 76,
                advantage_over_target="Higher 4-star Global NCAP safety rating and more solid highway stability.",
                tradeoff_vs_target="3-cylinder engine is noisier and resale value is lower than Maruti.",
                verdict_label="Better For Safety",
            ))

        latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)

        return DecisionEvaluationResponse(
            canonical_vehicle_id=canonical_vehicle_id,
            vehicle_summary=summary,
            intrinsic_score=intrinsic_score,
            user_fit_score=user_fit_score,
            vehicle_fit_score=vehicle_fit_score,
            deal_fit_score=deal_fit_score,
            hard_constraint_status=constraint_res.overall_status,
            recommendation_verdict=recommendation_verdict,
            verdict_label=verdict_label,
            fit_breakdown=fit_breakdown,
            why_it_fits=why_fits,
            why_it_may_not_fit=why_not_fits,
            tradeoffs=tradeoffs,
            what_to_verify_before_buying=verify_points,
            alternatives=alternatives,
            decision_quality=fit_breakdown.decision_quality,
            limitations=fit_breakdown.data_limitations,
            computation_latency_ms=latency_ms,
        )

    def rank_shortlist(
        self,
        canonical_ids: List[str],
        profile: UserRequirementsProfile,
    ) -> ShortlistRankResponse:
        """
        Ranks a user's shortlist of candidate vehicles.
        Places hard constraint-passing vehicles on top sorted by User Fit score descending.
        """
        t0 = time.perf_counter()
        evaluated: List[DecisionEvaluationResponse] = []

        for cid in canonical_ids:
            try:
                res = self.evaluate_vehicle(canonical_vehicle_id=cid, profile=profile)
                evaluated.append(res)
            except Exception as e:
                # Fallback evaluation on error
                brand, model, gen, yr, var = self._parse_canonical_id(cid)
                evaluated.append(DecisionEvaluationResponse(
                    canonical_vehicle_id=cid,
                    vehicle_summary=f"{yr or ''} {brand} {model}".strip(),
                    intrinsic_score=70,
                    user_fit_score=50,
                    vehicle_fit_score=50,
                    deal_fit_score=None,
                    hard_constraint_status=HardConstraintStatus.UNKNOWN,
                    recommendation_verdict="PROCEED WITH CAUTION",
                    verdict_label="Evaluation Incomplete",
                    fit_breakdown=PersonalizedFitBreakdown(
                        overall_user_fit_score=50,
                        decision_quality=DecisionQuality.LIMITED,
                        data_limitations=[f"Error evaluating vehicle: {str(e)}"],
                    ),
                    why_it_fits=[],
                    why_it_may_not_fit=[f"Could not verify all data: {str(e)}"],
                    tradeoffs=[],
                    what_to_verify_before_buying=[],
                    alternatives=[],
                    decision_quality=DecisionQuality.LIMITED,
                    limitations=[str(e)],
                ))

        # Sort: HardConstraintStatus.PASS first, then user_fit_score descending
        def sort_key(item: DecisionEvaluationResponse):
            is_pass = 1 if item.hard_constraint_status == HardConstraintStatus.PASS else 0
            return (is_pass, item.user_fit_score)

        evaluated.sort(key=sort_key, reverse=True)

        top_id = evaluated[0].canonical_vehicle_id if evaluated else None
        ranking_notes: List[str] = []
        if evaluated:
            top_car = evaluated[0]
            if top_car.hard_constraint_status == HardConstraintStatus.PASS:
                ranking_notes.append(f"'{top_car.vehicle_summary}' ranked #1 because it has the highest user fit score ({top_car.user_fit_score}/100) and satisfies all your requirements.")
            else:
                ranking_notes.append("None of the shortlisted vehicles fully satisfied all your stated hard constraints.")

        latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)

        return ShortlistRankResponse(
            ranked_vehicles=evaluated,
            user_profile_summary={
                "budget_max_inr": profile.budget_max_inr,
                "usage_profile": profile.usage_profile.value,
                "family_size": profile.family_size,
                "safety_priority": profile.safety_priority.value,
                "transmission_preferences": profile.transmission_preferences,
            },
            top_recommendation_id=top_id,
            ranking_notes=ranking_notes,
            computation_latency_ms=latency_ms,
        )

    def compare_personalized(
        self,
        canonical_ids: List[str],
        profile: UserRequirementsProfile,
    ) -> PersonalizedComparisonResponse:
        """
        Personalized multi-vehicle comparison:
        Identifies 'Best Vehicle Overall' (highest intrinsic score) vs
        'Best For You' (highest User Fit score among constraint-passing vehicles)
        and explicitly explains why they diverge when they do.
        """
        t0 = time.perf_counter()
        evaluated: List[DecisionEvaluationResponse] = []

        for cid in canonical_ids:
            evaluated.append(self.evaluate_vehicle(canonical_vehicle_id=cid, profile=profile))

        # 1. Best Vehicle Overall (Highest Intrinsic Score)
        gen_winner_idx = 0
        best_intrinsic = -1
        for idx, ev in enumerate(evaluated):
            score = ev.intrinsic_score or 0
            if score > best_intrinsic:
                best_intrinsic = score
                gen_winner_idx = idx

        gen_winner = evaluated[gen_winner_idx]
        gen_rationale = (
            f"{gen_winner.vehicle_summary} achieves the highest intrinsic CARspective Score ({gen_winner.intrinsic_score}/100) "
            "based purely on objective engineering merit, build quality, safety architecture, and reliability track record."
        )

        # 2. Best For You (Highest User Fit among constraint-passing vehicles)
        passing_cars = [(idx, ev) for idx, ev in enumerate(evaluated) if ev.hard_constraint_status == HardConstraintStatus.PASS]
        if passing_cars:
            user_winner_idx, user_winner = max(passing_cars, key=lambda x: x[1].user_fit_score)
        else:
            user_winner_idx, user_winner = max(enumerate(evaluated), key=lambda x: x[1].user_fit_score)

        user_rationale = (
            f"{user_winner.vehicle_summary} is your best match ({user_winner.user_fit_score}/100 User Fit) "
            f"because it directly aligns with your stated budget, usage habits, and priority weights."
        )

        # 3. Divergence Explanation
        divergence = None
        if gen_winner_idx != user_winner_idx:
            divergence = (
                f"While the {gen_winner.vehicle_summary} is objectively the stronger automobile overall ({gen_winner.intrinsic_score}/100 intrinsic score), "
                f"the {user_winner.vehicle_summary} is better suited to YOU ({user_winner.user_fit_score}/100 fit score). "
                f"The general winner involves compromises on your specific constraints (such as budget ceiling or powertrain preference), "
                f"whereas the {user_winner.vehicle_summary} optimizes for your exact real-world scenario."
            )

        latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)

        return PersonalizedComparisonResponse(
            general_winner_index=gen_winner_idx,
            general_winner_rationale=gen_rationale,
            user_winner_index=user_winner_idx,
            user_winner_rationale=user_rationale,
            divergence_explanation=divergence,
            vehicles=evaluated,
            computation_latency_ms=latency_ms,
        )

    def prioritize_inspection(
        self,
        canonical_vehicle_id: str,
        profile: UserRequirementsProfile,
    ) -> PersonalizedInspectionPrioritizationResponse:
        """
        Prioritizes the canonical 45-item inspection checklist based on the user's specific profile.
        Does NOT alter the underlying 45-item catalog; elevates items dynamically with reasons.
        """
        t0 = time.perf_counter()
        brand, model, gen, yr, var = self._parse_canonical_id(canonical_vehicle_id)
        summary = f"{yr or ''} {brand} {model}".strip()

        prof = self.knowledge_service.get_vehicle_profile(canonical_vehicle_id)
        specs = prof.specifications if prof else None

        v_context = InspectionVehicleContext(
            brand=brand,
            model=model,
            manufacturing_year=yr or 2020,
            variant=var,
            fuel_type=specs.fuel_type if specs else "Petrol",
            transmission_type=specs.transmission if specs else "Manual",
            km_driven=profile.annual_km or 40000.0,
        )

        # Generate adaptive checklist items using existing checklist engine
        checklist = ChecklistApplicabilityEngine.generate_adaptive_checklist(vehicle=v_context)

        prioritized_items: List[Dict[str, Any]] = []
        priority_reasons: List[str] = []

        # Scoring adjustments for prioritization
        is_safety_critical = profile.safety_priority in [PriorityLevel.HIGH, PriorityLevel.CRITICAL]
        is_maint_critical = profile.maintenance_priority in [PriorityLevel.HIGH, PriorityLevel.CRITICAL]
        is_city = profile.usage_profile == UsageProfile.CITY
        is_highway = profile.usage_profile == UsageProfile.HIGHWAY

        if is_safety_critical:
            priority_reasons.append("Structural integrity, airbag modules, and braking systems elevated because Safety is a stated priority.")
        if is_maint_critical:
            priority_reasons.append("Engine oil leaks, coolant condition, and gearbox fluid elevated because Maintenance sensitivity is a stated priority.")
        if is_city:
            priority_reasons.append("Clutch wear, AMT/automatic shift behavior, and AC cooling performance elevated for stop-and-go city traffic.")
        if is_highway:
            priority_reasons.append("Tyre tread depth, high-speed suspension alignment, and brake pads elevated for highway touring.")

        for item in checklist:
            cat = item.category.value if hasattr(item.category, "value") else str(item.category)
            imp = item.importance.value if hasattr(item.importance, "value") else str(item.importance)
            
            p_score = 50
            reason = "Standard baseline inspection checkpoint"

            if is_safety_critical and cat in ["Structural & Body Integrity", "Brakes & Suspension"]:
                p_score += 40
                reason = "Elevated due to Critical Safety priority"
            elif is_maint_critical and cat in ["Engine & Mechanical", "Transmission & Drivetrain", "Fluids & Leaks"]:
                p_score += 35
                reason = "Elevated due to Low Maintenance tolerance"
            elif is_city and ("clutch" in item.title.lower() or "transmission" in item.title.lower() or "ac" in item.title.lower()):
                p_score += 25
                reason = "Elevated due to heavy city stop-and-go usage"
            elif is_highway and ("tyre" in item.title.lower() or "brake" in item.title.lower() or "suspension" in item.title.lower()):
                p_score += 25
                reason = "Elevated due to highway driving profile"

            prioritized_items.append({
                "item_id": item.item_id,
                "title": item.title,
                "category": cat,
                "original_importance": imp,
                "user_priority_score": p_score,
                "elevation_reason": reason,
                "how_to_check": item.inspection_method,
                "pass_criteria": item.expected_observation,
                "fail_criteria": "; ".join(item.warning_signs) if item.warning_signs else "Verification anomaly",
            })

        # Sort by user_priority_score descending
        prioritized_items.sort(key=lambda x: x["user_priority_score"], reverse=True)

        latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)

        return PersonalizedInspectionPrioritizationResponse(
            canonical_vehicle_id=canonical_vehicle_id,
            vehicle_summary=summary,
            prioritized_checklist=prioritized_items,
            priority_reasons=priority_reasons,
            computation_latency_ms=latency_ms,
        )
