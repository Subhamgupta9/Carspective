"""
CARspective — Phase 6 Comparison Domain Service
Orchestrates evidence-aware, canonical, explainable vehicle comparison (2-3 vehicles).

Service orchestration:
    Taxonomy → Evidence → Score → Valuation → Deal Analyzer (if listing) → User Fit (if personalized) → Comparison Engine

All conclusions are deterministic and traceable to structured inputs.
No LLM is used for decision-making, winner selection, or trade-off generation.
"""

import uuid
import time
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session

from server.domain.comparison.models import (
    ComparisonRequest,
    ComparisonResponse,
    ComparisonMode,
    ComparisonVehicle,
    ComparisonListing,
    ComparisonUserProfile,
    SpecificationValue,
    SpecificationComparison,
    DifferenceSignificance,
    CategoryResult,
    CategoryWinnerStatus,
    VehicleScoreSummary,
    ScoreComparison,
    VehicleValuationSummary,
    ValuationComparison,
    VehicleDealSummary,
    DealComparison,
    VehicleUserFitSummary,
    UserFitComparison,
    TradeOff,
    BestForLabel,
    VehicleResearchSummary,
    OverallResult,
    OverallResultType,
    EvidenceState,
)
from server.domain.scoring.models import ScoreRequest, ScoreResponse, ScoreDimensionName
from server.domain.scoring.service import ScoringService
from server.domain.valuation.models import ValuationRequest, ValuationResponse
from server.domain.valuation.service import ValuationService
from server.domain.deal_analyzer.models import DealAnalysisRequest, DealAnalysisResponse
from server.domain.deal_analyzer.service import DealAnalyzerService
from server.domain.recommendation.models import (
    RecommendationRequest,
    RecommendationResponse,
    ListingContext,
    UserProfile,
)
from server.domain.recommendation.service import RecommendationService, format_inr
from server.domain.knowledge.service import KnowledgeService
from server.schemas.taxonomy import CanonicalResolutionRequest, CanonicalResolutionResult
from server.infrastructure.database import ScopedSession



# ────────────────────────────────────────────────────────────────────
# Verified Specification Database
# ────────────────────────────────────────────────────────────────────

# Evidence-grounded vehicle specifications from manufacturer OEM data (SUPPORTED)
# and authoritative crash-test registries (VERIFIED).
VEHICLE_SPECS_DB: Dict[str, Dict[str, Any]] = {
    "tata::nexon": {
        "engine_displacement_cc": 1199, "fuel_type": "Petrol", "transmission": "Manual",
        "power_bhp": 120, "torque_nm": 170, "drivetrain": "FWD",
        "claimed_efficiency_kmpl": 17.4,
        "length_mm": 3993, "width_mm": 1811, "height_mm": 1607, "wheelbase_mm": 2498,
        "ground_clearance_mm": 209, "boot_capacity_l": 350, "seating_capacity": 5,
        "fuel_tank_l": 44, "kerb_weight_kg": 1280,
        "airbags": 6, "esc": True, "abs": True,
        "ncap_stars": 5, "ncap_source": "Global NCAP 2022", "ncap_evidence": "VERIFIED",
        "body_type": "Compact SUV",
    },
    "hyundai::creta": {
        "engine_displacement_cc": 1497, "fuel_type": "Petrol", "transmission": "Manual",
        "power_bhp": 115, "torque_nm": 144, "drivetrain": "FWD",
        "claimed_efficiency_kmpl": 16.8,
        "length_mm": 4300, "width_mm": 1790, "height_mm": 1635, "wheelbase_mm": 2610,
        "ground_clearance_mm": 190, "boot_capacity_l": 433, "seating_capacity": 5,
        "fuel_tank_l": 50, "kerb_weight_kg": 1300,
        "airbags": 6, "esc": True, "abs": True,
        "ncap_stars": 3, "ncap_source": "Global NCAP 2023", "ncap_evidence": "VERIFIED",
        "body_type": "Mid-size SUV",
    },
    "maruti::swift": {
        "engine_displacement_cc": 1197, "fuel_type": "Petrol", "transmission": "Manual",
        "power_bhp": 90, "torque_nm": 113, "drivetrain": "FWD",
        "claimed_efficiency_kmpl": 22.38,
        "length_mm": 3845, "width_mm": 1735, "height_mm": 1530, "wheelbase_mm": 2450,
        "ground_clearance_mm": 163, "boot_capacity_l": 268, "seating_capacity": 5,
        "fuel_tank_l": 37, "kerb_weight_kg": 900,
        "airbags": 2, "esc": True, "abs": True,
        "ncap_stars": 2, "ncap_source": "Global NCAP 2024", "ncap_evidence": "VERIFIED",
        "body_type": "Hatchback",
    },
    "honda::city": {
        "engine_displacement_cc": 1498, "fuel_type": "Petrol", "transmission": "Manual",
        "power_bhp": 121, "torque_nm": 145, "drivetrain": "FWD",
        "claimed_efficiency_kmpl": 18.4,
        "length_mm": 4549, "width_mm": 1748, "height_mm": 1489, "wheelbase_mm": 2600,
        "ground_clearance_mm": 165, "boot_capacity_l": 506, "seating_capacity": 5,
        "fuel_tank_l": 40, "kerb_weight_kg": 1107,
        "airbags": 6, "esc": True, "abs": True,
        "ncap_stars": None, "ncap_source": None, "ncap_evidence": "INSUFFICIENT_DATA",
        "body_type": "Sedan",
    },
    "hyundai::verna": {
        "engine_displacement_cc": 1497, "fuel_type": "Petrol", "transmission": "Manual",
        "power_bhp": 115, "torque_nm": 144, "drivetrain": "FWD",
        "claimed_efficiency_kmpl": 18.6,
        "length_mm": 4535, "width_mm": 1765, "height_mm": 1475, "wheelbase_mm": 2600,
        "ground_clearance_mm": 170, "boot_capacity_l": 480, "seating_capacity": 5,
        "fuel_tank_l": 45, "kerb_weight_kg": 1200,
        "airbags": 6, "esc": True, "abs": True,
        "ncap_stars": None, "ncap_source": None, "ncap_evidence": "INSUFFICIENT_DATA",
        "body_type": "Sedan",
    },
    "mahindra::thar": {
        "engine_displacement_cc": 1997, "fuel_type": "Diesel", "transmission": "Manual",
        "power_bhp": 130, "torque_nm": 300, "drivetrain": "4WD",
        "claimed_efficiency_kmpl": 15.2,
        "length_mm": 3985, "width_mm": 1820, "height_mm": 1844, "wheelbase_mm": 2450,
        "ground_clearance_mm": 226, "boot_capacity_l": 210, "seating_capacity": 4,
        "fuel_tank_l": 57, "kerb_weight_kg": 1750,
        "airbags": 2, "esc": True, "abs": True,
        "ncap_stars": None, "ncap_source": None, "ncap_evidence": "INSUFFICIENT_DATA",
        "body_type": "Off-road SUV",
    },
    "kia::seltos": {
        "engine_displacement_cc": 1497, "fuel_type": "Petrol", "transmission": "Manual",
        "power_bhp": 115, "torque_nm": 144, "drivetrain": "FWD",
        "claimed_efficiency_kmpl": 16.8,
        "length_mm": 4315, "width_mm": 1800, "height_mm": 1620, "wheelbase_mm": 2610,
        "ground_clearance_mm": 190, "boot_capacity_l": 433, "seating_capacity": 5,
        "fuel_tank_l": 50, "kerb_weight_kg": 1310,
        "airbags": 6, "esc": True, "abs": True,
        "ncap_stars": 3, "ncap_source": "Global NCAP 2023", "ncap_evidence": "VERIFIED",
        "body_type": "Mid-size SUV",
    },
    "toyota::fortuner": {
        "engine_displacement_cc": 2755, "fuel_type": "Diesel", "transmission": "Automatic",
        "power_bhp": 204, "torque_nm": 500, "drivetrain": "4WD",
        "claimed_efficiency_kmpl": 10.0,
        "length_mm": 4795, "width_mm": 1855, "height_mm": 1835, "wheelbase_mm": 2745,
        "ground_clearance_mm": 221, "boot_capacity_l": 296, "seating_capacity": 7,
        "fuel_tank_l": 80, "kerb_weight_kg": 2210,
        "airbags": 7, "esc": True, "abs": True,
        "ncap_stars": None, "ncap_source": None, "ncap_evidence": "INSUFFICIENT_DATA",
        "body_type": "Full-size SUV",
    },
    "maruti::baleno": {
        "engine_displacement_cc": 1197, "fuel_type": "Petrol", "transmission": "Manual",
        "power_bhp": 90, "torque_nm": 113, "drivetrain": "FWD",
        "claimed_efficiency_kmpl": 22.35,
        "length_mm": 3990, "width_mm": 1745, "height_mm": 1500, "wheelbase_mm": 2520,
        "ground_clearance_mm": 170, "boot_capacity_l": 318, "seating_capacity": 5,
        "fuel_tank_l": 37, "kerb_weight_kg": 935,
        "airbags": 2, "esc": True, "abs": True,
        "ncap_stars": None, "ncap_source": None, "ncap_evidence": "INSUFFICIENT_DATA",
        "body_type": "Premium Hatchback",
    },
    "hyundai::venue": {
        "engine_displacement_cc": 1197, "fuel_type": "Petrol", "transmission": "Manual",
        "power_bhp": 83, "torque_nm": 114, "drivetrain": "FWD",
        "claimed_efficiency_kmpl": 18.15,
        "length_mm": 3995, "width_mm": 1770, "height_mm": 1590, "wheelbase_mm": 2500,
        "ground_clearance_mm": 195, "boot_capacity_l": 350, "seating_capacity": 5,
        "fuel_tank_l": 45, "kerb_weight_kg": 1045,
        "airbags": 6, "esc": True, "abs": True,
        "ncap_stars": None, "ncap_source": None, "ncap_evidence": "INSUFFICIENT_DATA",
        "body_type": "Sub-compact SUV",
    },
    "volkswagen::virtus": {
        "engine_displacement_cc": 999, "fuel_type": "Petrol", "transmission": "Manual",
        "power_bhp": 115, "torque_nm": 178, "drivetrain": "FWD",
        "claimed_efficiency_kmpl": 18.12,
        "length_mm": 4561, "width_mm": 1752, "height_mm": 1507, "wheelbase_mm": 2651,
        "ground_clearance_mm": 179, "boot_capacity_l": 521, "seating_capacity": 5,
        "fuel_tank_l": 45, "kerb_weight_kg": 1215,
        "airbags": 6, "esc": True, "abs": True,
        "ncap_stars": 5, "ncap_source": "Global NCAP 2023", "ncap_evidence": "VERIFIED",
        "body_type": "Sedan",
    },
    "skoda::slavia": {
        "engine_displacement_cc": 999, "fuel_type": "Petrol", "transmission": "Manual",
        "power_bhp": 115, "torque_nm": 178, "drivetrain": "FWD",
        "claimed_efficiency_kmpl": 18.07,
        "length_mm": 4541, "width_mm": 1752, "height_mm": 1487, "wheelbase_mm": 2651,
        "ground_clearance_mm": 179, "boot_capacity_l": 521, "seating_capacity": 5,
        "fuel_tank_l": 45, "kerb_weight_kg": 1205,
        "airbags": 6, "esc": True, "abs": True,
        "ncap_stars": 5, "ncap_source": "Global NCAP 2023", "ncap_evidence": "VERIFIED",
        "body_type": "Sedan",
    },
    "maruti::brezza": {
        "engine_displacement_cc": 1462, "fuel_type": "Petrol", "transmission": "Manual",
        "power_bhp": 102, "torque_nm": 137, "drivetrain": "FWD",
        "claimed_efficiency_kmpl": 19.8,
        "length_mm": 3995, "width_mm": 1790, "height_mm": 1685, "wheelbase_mm": 2500,
        "ground_clearance_mm": 198, "boot_capacity_l": 328, "seating_capacity": 5,
        "fuel_tank_l": 48, "kerb_weight_kg": 1130,
        "airbags": 6, "esc": True, "abs": True,
        "ncap_stars": 4, "ncap_source": "Global NCAP 2022", "ncap_evidence": "VERIFIED",
        "body_type": "Compact SUV",
    },
    "tata::punch": {
        "engine_displacement_cc": 1199, "fuel_type": "Petrol", "transmission": "Manual",
        "power_bhp": 86, "torque_nm": 115, "drivetrain": "FWD",
        "claimed_efficiency_kmpl": 18.82,
        "length_mm": 3827, "width_mm": 1742, "height_mm": 1615, "wheelbase_mm": 2445,
        "ground_clearance_mm": 187, "boot_capacity_l": 366, "seating_capacity": 5,
        "fuel_tank_l": 37, "kerb_weight_kg": 1000,
        "airbags": 2, "esc": True, "abs": True,
        "ncap_stars": 5, "ncap_source": "Global NCAP 2021", "ncap_evidence": "VERIFIED",
        "body_type": "Micro SUV",
    },
}


# ────────────────────────────────────────────────────────────────────
# Specification Definition Registry
# ────────────────────────────────────────────────────────────────────

SPEC_DEFINITIONS = [
    # Engine / Powertrain
    {"key": "engine_displacement_cc", "name": "Engine Displacement", "category": "Engine / Powertrain",
     "unit": "cc", "higher_better": None, "significance_threshold": 100},
    {"key": "fuel_type", "name": "Fuel Type", "category": "Engine / Powertrain",
     "unit": None, "higher_better": None, "significance_threshold": None},
    {"key": "transmission", "name": "Transmission", "category": "Engine / Powertrain",
     "unit": None, "higher_better": None, "significance_threshold": None},
    {"key": "drivetrain", "name": "Drivetrain", "category": "Engine / Powertrain",
     "unit": None, "higher_better": None, "significance_threshold": None},
    {"key": "power_bhp", "name": "Power", "category": "Engine / Powertrain",
     "unit": "bhp", "higher_better": True, "significance_threshold": 10},
    {"key": "torque_nm", "name": "Torque", "category": "Engine / Powertrain",
     "unit": "Nm", "higher_better": True, "significance_threshold": 20},
    # Efficiency
    {"key": "claimed_efficiency_kmpl", "name": "Claimed Fuel Efficiency", "category": "Efficiency",
     "unit": "km/l", "higher_better": True, "significance_threshold": 1.5},
    # Dimensions
    {"key": "length_mm", "name": "Length", "category": "Dimensions",
     "unit": "mm", "higher_better": None, "significance_threshold": 100},
    {"key": "width_mm", "name": "Width", "category": "Dimensions",
     "unit": "mm", "higher_better": None, "significance_threshold": 50},
    {"key": "height_mm", "name": "Height", "category": "Dimensions",
     "unit": "mm", "higher_better": None, "significance_threshold": 50},
    {"key": "wheelbase_mm", "name": "Wheelbase", "category": "Dimensions",
     "unit": "mm", "higher_better": True, "significance_threshold": 50},
    {"key": "ground_clearance_mm", "name": "Ground Clearance", "category": "Dimensions",
     "unit": "mm", "higher_better": True, "significance_threshold": 15},
    {"key": "boot_capacity_l", "name": "Boot / Cargo Capacity", "category": "Dimensions",
     "unit": "L", "higher_better": True, "significance_threshold": 30},
    # Capacity
    {"key": "seating_capacity", "name": "Seating Capacity", "category": "Capacity",
     "unit": "seats", "higher_better": None, "significance_threshold": 1},
    {"key": "fuel_tank_l", "name": "Fuel Tank Capacity", "category": "Capacity",
     "unit": "L", "higher_better": True, "significance_threshold": 5},
    # Safety
    {"key": "airbags", "name": "Airbags", "category": "Safety",
     "unit": None, "higher_better": True, "significance_threshold": 1},
    {"key": "ncap_stars", "name": "Crash Test Rating", "category": "Safety",
     "unit": "stars", "higher_better": True, "significance_threshold": 1},
]

# Dimension display names to key mapping for score comparison
DIMENSION_KEYS = {
    ScoreDimensionName.STRUCTURAL_SAFETY: "Structural Safety",
    ScoreDimensionName.RELIABILITY_AND_LONGEVITY: "Reliability & Longevity",
    ScoreDimensionName.MAINTENANCE_AND_OWNERSHIP: "Maintenance & Ownership",
    ScoreDimensionName.RESALE_AND_MARKET_LIQUIDITY: "Resale & Market Liquidity",
    ScoreDimensionName.REAL_WORLD_PRACTICALITY: "Real-World Practicality",
}


class ComparisonService:
    """
    Orchestrates evidence-aware vehicle comparison across 2-3 vehicles.
    Reuses Phase 2-5 services; does not duplicate upstream business logic.
    """

    def __init__(
        self,
        scoring_service: Optional[ScoringService] = None,
        valuation_service: Optional[ValuationService] = None,
        deal_service: Optional[DealAnalyzerService] = None,
        recommendation_service: Optional[RecommendationService] = None,
        session: Optional[Session] = None,
    ):
        self._session = session
        self.scoring_service = scoring_service or ScoringService(session=session)
        self.valuation_service = valuation_service or ValuationService(session=session)
        self.deal_service = deal_service or DealAnalyzerService(valuation_service=self.valuation_service)
        self.recommendation_service = recommendation_service or RecommendationService(
            scoring_service=self.scoring_service,
            deal_service=self.deal_service,
            session=session,
        )
        self.knowledge_service = KnowledgeService(session=session)
        self.taxonomy_resolver = getattr(self.scoring_service, "taxonomy_resolver", None)

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
        if hasattr(self, "recommendation_service"):
            self.recommendation_service.session = value
        if hasattr(self, "knowledge_service"):
            self.knowledge_service.session = value
        if hasattr(self, "taxonomy_resolver") and hasattr(self.taxonomy_resolver, "repo"):
            self.taxonomy_resolver.repo.session = value


    def compare(self, req: ComparisonRequest) -> ComparisonResponse:
        """Execute a full vehicle comparison."""
        t_start = time.perf_counter()
        comparison_id = f"cmp-{uuid.uuid4().hex[:12]}"
        n = len(req.vehicles)

        # ── 0. Resolve canonical taxonomy once per vehicle (Reuse) ──
        resolved_taxonomies: List[Optional[CanonicalResolutionResult]] = []
        if self.taxonomy_resolver:
            for v in req.vehicles:
                try:
                    tax_req = CanonicalResolutionRequest(
                        brand=v.brand,
                        model=v.model,
                        year=v.manufacturing_year,
                        variant=v.variant,
                        fuel_type=v.fuel_type,
                        transmission_type=v.transmission_type,
                    )
                    resolved_taxonomies.append(self.taxonomy_resolver.resolve(tax_req))
                except Exception:
                    resolved_taxonomies.append(None)
        else:
            resolved_taxonomies = [None] * n

        # ── 1. Score all vehicles (reuses Phase 5) ──────────────────
        score_results: List[ScoreResponse] = []
        for idx, v in enumerate(req.vehicles):
            score_req = ScoreRequest(
                brand=v.brand, model=v.model,
                manufacturing_year=v.manufacturing_year,
                fuel_type=v.fuel_type,
                transmission_type=v.transmission_type,
                variant=v.variant,
            )
            res_tax = resolved_taxonomies[idx] if idx < len(resolved_taxonomies) else None
            score_results.append(self.scoring_service.calculate_score(score_req, resolved_taxonomy=res_tax))

        # ── 2. Valuate all vehicles (reuses Phase 3) ────────────────
        valuation_results: List[ValuationResponse] = []
        for idx, v in enumerate(req.vehicles):
            val_req = ValuationRequest(
                brand=v.brand, model=v.model,
                manufacturing_year=v.manufacturing_year or 2019,
                km_driven=v.km_driven or 45000.0,
                fuel_type=v.fuel_type or "Petrol",
                transmission_type=v.transmission_type or "Manual",
                city=v.city or "Delhi",
                number_of_owners=v.number_of_owners or 1,
                variant=v.variant,
            )
            res_tax = resolved_taxonomies[idx] if idx < len(resolved_taxonomies) else None
            valuation_results.append(self.valuation_service.evaluate_valuation(val_req, resolved_taxonomy=res_tax))

        # ── 3. Deal analysis for vehicles with listings (reuses Phase 4) ──
        listing_map: Dict[int, ComparisonListing] = {}
        if req.listings:
            for listing in req.listings:
                listing_map[listing.vehicle_index] = listing

        deal_results: Dict[int, DealAnalysisResponse] = {}
        for idx, listing in listing_map.items():
            v = req.vehicles[idx]
            deal_req = DealAnalysisRequest(
                brand=v.brand, model=v.model,
                manufacturing_year=v.manufacturing_year or 2019,
                km_driven=listing.km_driven or v.km_driven or 45000.0,
                asking_price=listing.asking_price,
                fuel_type=v.fuel_type or "Petrol",
                transmission_type=v.transmission_type or "Manual",
                city=v.city or "Delhi",
                number_of_owners=v.number_of_owners or 1,
                variant=v.variant,
                condition_notes=listing.condition_notes,
                service_history_status=listing.service_history_status,
                accident_history_status=listing.accident_history_status,
                insurance_status=listing.insurance_status,
            )
            deal_results[idx] = self.deal_service.analyze_deal(deal_req)

        # ── 4. User fit for personalized mode (reuses Phase 5) ──────
        user_fit_results: Dict[int, Any] = {}
        if req.mode == ComparisonMode.PERSONALIZED and req.user_profile:
            for idx, v in enumerate(req.vehicles):
                listing_ctx = None
                if idx in listing_map:
                    lm = listing_map[idx]
                    listing_ctx = ListingContext(
                        asking_price=lm.asking_price,
                        km_driven=lm.km_driven,
                        condition_notes=lm.condition_notes,
                        service_history_status=lm.service_history_status,
                        accident_history_status=lm.accident_history_status,
                        insurance_status=lm.insurance_status,
                    )
                rec_req = RecommendationRequest(
                    brand=v.brand, model=v.model,
                    manufacturing_year=v.manufacturing_year,
                    fuel_type=v.fuel_type,
                    transmission_type=v.transmission_type,
                    city=v.city,
                    variant=v.variant,
                    listing=listing_ctx or ListingContext(),
                    user_profile=UserProfile(
                        budget_max=req.user_profile.budget_max,
                        budget_flexible=req.user_profile.budget_flexible,
                        monthly_km=req.user_profile.monthly_km,
                        primary_usage=req.user_profile.primary_usage,
                        family_size=req.user_profile.family_size,
                        fuel_preference=req.user_profile.fuel_preference,
                        transmission_preference=req.user_profile.transmission_preference,
                        safety_priority=req.user_profile.safety_priority,
                        mileage_priority=req.user_profile.mileage_priority,
                        performance_priority=req.user_profile.performance_priority,
                        maintenance_priority=req.user_profile.maintenance_priority,
                        resale_priority=req.user_profile.resale_priority,
                        ownership_horizon_years=req.user_profile.ownership_horizon_years,
                    ),
                )
                rec_res = self.recommendation_service.evaluate_recommendation(rec_req)
                user_fit_results[idx] = rec_res

        # ── 5. Build response sections ──────────────────────────────
        vehicles_summary = self._build_vehicles_summary(req.vehicles, score_results)
        specifications = self._build_specifications(req.vehicles, n, resolved_taxonomies=resolved_taxonomies)
        category_winners = self._build_category_winners(score_results, n)
        score_comparison = self._build_score_comparison(score_results, n)
        valuation_comparison = self._build_valuation_comparison(valuation_results, n)
        deal_comparison = self._build_deal_comparison(deal_results, n) if deal_results else None
        user_fit_comparison = self._build_user_fit_comparison(user_fit_results, n) if user_fit_results else None
        tradeoffs = self._build_tradeoffs(score_results, specifications, n)
        best_for = self._build_best_for_labels(score_results, req.vehicles, specifications, n)
        research_summaries = self._build_research_summaries(
            req.vehicles, score_results, valuation_results, specifications, n
        )
        overall_result = self._build_overall_result(
            req, score_results, deal_results, user_fit_results, n
        )
        limitations = self._build_limitations(req, deal_results, user_fit_results)

        elapsed_ms = (time.perf_counter() - t_start) * 1000

        return ComparisonResponse(
            comparison_id=comparison_id,
            mode=req.mode,
            vehicles=vehicles_summary,
            specifications=specifications,
            category_winners=category_winners,
            score_comparison=score_comparison,
            valuation_comparison=valuation_comparison,
            deal_comparison=deal_comparison,
            user_fit_comparison=user_fit_comparison,
            tradeoffs=tradeoffs,
            best_for=best_for,
            overall_result=overall_result,
            research_summaries=research_summaries,
            limitations=limitations,
            computation_latency_ms=round(elapsed_ms, 2),
        )

    # ────────────────────────────────────────────────────────────────
    # Build Vehicle Summaries
    # ────────────────────────────────────────────────────────────────

    def _build_vehicles_summary(
        self, vehicles: List[ComparisonVehicle], score_results: List[ScoreResponse]
    ) -> List[Dict[str, Any]]:
        summaries = []
        for idx, (v, sr) in enumerate(zip(vehicles, score_results)):
            summaries.append({
                "index": idx,
                "brand": v.brand,
                "model": v.model,
                "manufacturing_year": v.manufacturing_year,
                "fuel_type": v.fuel_type,
                "transmission_type": v.transmission_type,
                "variant": v.variant,
                "canonical_vehicle_id": sr.canonical_vehicle_id,
                "vehicle_summary": sr.vehicle_summary,
            })
        return summaries

    # ────────────────────────────────────────────────────────────────
    # Specification Normalization & Comparison
    # ────────────────────────────────────────────────────────────────

    def _get_spec_key(self, vehicle: ComparisonVehicle) -> str:
        return f"{vehicle.brand.lower().strip()}::{vehicle.model.lower().strip()}"

    def _build_specifications(
        self,
        vehicles: List[ComparisonVehicle],
        n: int,
        resolved_taxonomies: Optional[List[Optional[CanonicalResolutionResult]]] = None,
    ) -> List[SpecificationComparison]:
        specs_list = []
        vehicle_specs = []
        for idx, v in enumerate(vehicles):
            static_spec = dict(VEHICLE_SPECS_DB.get(self._get_spec_key(v), {}))
            try:
                res_tax = resolved_taxonomies[idx] if resolved_taxonomies and idx < len(resolved_taxonomies) else None
                can_id = (
                    v.canonical_vehicle_id
                    or (res_tax.canonical_vehicle_id if res_tax else None)
                    or f"{v.brand.lower().replace(' ', '-')}:{v.model.lower().replace(' ', '-')}"
                )
                specs_data = self.knowledge_service.get_comparison_specifications(can_id)
                if specs_data:
                    spec = specs_data.get("specifications")
                    if spec:
                        if spec.displacement_cc: static_spec["engine_displacement_cc"] = spec.displacement_cc
                        if spec.max_power_bhp: static_spec["power_bhp"] = spec.max_power_bhp
                        if spec.max_torque_nm: static_spec["torque_nm"] = spec.max_torque_nm
                        if spec.arai_mileage_kmpl: static_spec["claimed_efficiency_kmpl"] = spec.arai_mileage_kmpl
                    dims = specs_data.get("dimensions")
                    if dims:
                        if dims.length_mm: static_spec["length_mm"] = dims.length_mm
                        if dims.width_mm: static_spec["width_mm"] = dims.width_mm
                        if dims.height_mm: static_spec["height_mm"] = dims.height_mm
                        if dims.wheelbase_mm: static_spec["wheelbase_mm"] = dims.wheelbase_mm
                        if dims.ground_clearance_mm: static_spec["ground_clearance_mm"] = dims.ground_clearance_mm
                        if dims.boot_capacity_l: static_spec["boot_capacity_l"] = dims.boot_capacity_l
                    safety = specs_data.get("safety")
                    if safety:
                        static_spec["ncap_stars"] = safety.adult_stars
                        static_spec["ncap_source"] = f"{safety.organization} {safety.test_year}"
                        static_spec["ncap_evidence"] = safety.evidence_state
            except Exception:
                pass
            vehicle_specs.append(static_spec)


        for spec_def in SPEC_DEFINITIONS:
            key = spec_def["key"]
            values: List[SpecificationValue] = []
            raw_values = []

            for idx in range(n):
                spec_data = vehicle_specs[idx]
                raw_val = spec_data.get(key)
                raw_values.append(raw_val)

                if raw_val is None:
                    values.append(SpecificationValue(
                        value=None,
                        display_value="Data unavailable",
                        unit=spec_def.get("unit"),
                        evidence_state=EvidenceState.INSUFFICIENT_DATA,
                    ))
                elif key == "ncap_stars":
                    evidence = spec_data.get("ncap_evidence", "INSUFFICIENT_DATA")
                    source = spec_data.get("ncap_source")
                    values.append(SpecificationValue(
                        value=raw_val,
                        display_value=f"{raw_val}-Star" if raw_val else "Not Rated",
                        unit=spec_def.get("unit"),
                        evidence_state=EvidenceState(evidence),
                        source=source,
                    ))
                elif key in ("esc", "abs"):
                    values.append(SpecificationValue(
                        value=raw_val,
                        display_value="Yes" if raw_val else "No",
                        evidence_state=EvidenceState.SUPPORTED,
                        source="Manufacturer OEM specification",
                    ))
                else:
                    unit_suffix = f" {spec_def['unit']}" if spec_def.get("unit") else ""
                    values.append(SpecificationValue(
                        value=raw_val,
                        display_value=f"{raw_val}{unit_suffix}",
                        unit=spec_def.get("unit"),
                        evidence_state=EvidenceState.SUPPORTED,
                        source="Manufacturer OEM specification",
                    ))

            # Determine winner and significance
            winner_idx, significance, note = self._evaluate_spec_winner(
                raw_values, spec_def, n
            )

            specs_list.append(SpecificationComparison(
                spec_name=spec_def["name"],
                spec_key=key,
                category=spec_def["category"],
                values=values,
                winner_index=winner_idx,
                significance=significance,
                comparison_note=note,
            ))

        return specs_list

    def _evaluate_spec_winner(
        self, raw_values: List[Any], spec_def: Dict, n: int
    ) -> Tuple[Optional[int], DifferenceSignificance, Optional[str]]:
        """Determine winner for a spec based on domain semantics."""
        higher_better = spec_def.get("higher_better")
        threshold = spec_def.get("significance_threshold")

        # Non-numeric or directionless specs → no winner
        if higher_better is None or threshold is None:
            return None, DifferenceSignificance.UNKNOWN, None

        # Filter out None values
        numeric_vals = [(i, v) for i, v in enumerate(raw_values) if v is not None and isinstance(v, (int, float))]
        if len(numeric_vals) < 2:
            return None, DifferenceSignificance.UNKNOWN, "Insufficient comparable data for all vehicles."

        if higher_better:
            best_idx, best_val = max(numeric_vals, key=lambda x: x[1])
            second_val = sorted([v for _, v in numeric_vals], reverse=True)[1]
        else:
            best_idx, best_val = min(numeric_vals, key=lambda x: x[1])
            second_val = sorted([v for _, v in numeric_vals])[1]

        diff = abs(best_val - second_val)
        if diff < threshold:
            return None, DifferenceSignificance.MINOR, (
                f"Difference of {diff} {spec_def.get('unit', '')} is below the meaningful threshold of {threshold}."
            )

        return best_idx, DifferenceSignificance.MEANINGFUL, (
            f"Difference of {diff} {spec_def.get('unit', '')} is meaningful."
        )

    # ────────────────────────────────────────────────────────────────
    # Category Winners
    # ────────────────────────────────────────────────────────────────

    def _build_category_winners(
        self, score_results: List[ScoreResponse], n: int
    ) -> List[CategoryResult]:
        categories = []
        dim_map = {
            "Safety": ScoreDimensionName.STRUCTURAL_SAFETY,
            "Reliability": ScoreDimensionName.RELIABILITY_AND_LONGEVITY,
            "Maintenance": ScoreDimensionName.MAINTENANCE_AND_OWNERSHIP,
            "Resale / Liquidity": ScoreDimensionName.RESALE_AND_MARKET_LIQUIDITY,
            "Practicality": ScoreDimensionName.REAL_WORLD_PRACTICALITY,
        }

        for cat_name, dim_name in dim_map.items():
            scores = []
            values = []
            for idx, sr in enumerate(score_results):
                dim_score = None
                ev_state = "INSUFFICIENT_DATA"
                for d in sr.dimensions:
                    if d.dimension_name == dim_name:
                        dim_score = d.score
                        ev_state = d.evidence_state.value
                        break
                scores.append(dim_score)
                values.append({
                    "vehicle_index": idx,
                    "vehicle_summary": sr.vehicle_summary,
                    "score": dim_score,
                    "evidence_state": ev_state,
                })

            # Determine winner
            valid_scores = [(i, s) for i, s in enumerate(scores) if s is not None]
            if len(valid_scores) < 2:
                categories.append(CategoryResult(
                    category=cat_name, values=values,
                    winner_index=None, status=CategoryWinnerStatus.INSUFFICIENT_DATA,
                    evidence_quality="INSUFFICIENT_DATA",
                    rationale=f"Insufficient verified evidence to determine a {cat_name} winner.",
                ))
                continue

            best_idx, best_score = max(valid_scores, key=lambda x: x[1])
            second_score = sorted([s for _, s in valid_scores], reverse=True)[1]

            if best_score - second_score < 5:
                categories.append(CategoryResult(
                    category=cat_name, values=values,
                    winner_index=None, status=CategoryWinnerStatus.TIE,
                    evidence_quality="EMPIRICAL",
                    rationale=f"{cat_name} scores are within 5 points ({best_score} vs {second_score}), indicating no defensible winner.",
                ))
            else:
                winner_summary = score_results[best_idx].vehicle_summary
                categories.append(CategoryResult(
                    category=cat_name, values=values,
                    winner_index=best_idx, status=CategoryWinnerStatus.WINNER,
                    evidence_quality="EMPIRICAL",
                    rationale=f"{winner_summary} leads in {cat_name} ({best_score}/100 vs {second_score}/100).",
                ))

        return categories

    # ────────────────────────────────────────────────────────────────
    # CARspective Score Comparison
    # ────────────────────────────────────────────────────────────────

    def _build_score_comparison(
        self, score_results: List[ScoreResponse], n: int
    ) -> ScoreComparison:
        vehicle_scores = []
        for idx, sr in enumerate(score_results):
            dims = {}
            for d in sr.dimensions:
                dims[d.dimension_name.value] = d.score
            vehicle_scores.append(VehicleScoreSummary(
                vehicle_index=idx,
                vehicle_summary=sr.vehicle_summary,
                canonical_vehicle_id=sr.canonical_vehicle_id,
                overall_score=sr.overall_score,
                evidence_quality=sr.evidence_quality.value,
                dimensions=dims,
            ))

        # Overall winner
        valid = [(idx, vs.overall_score) for idx, vs in enumerate(vehicle_scores) if vs.overall_score is not None]
        if len(valid) < 2:
            return ScoreComparison(
                vehicle_scores=vehicle_scores,
                overall_winner_index=None,
                overall_status=CategoryWinnerStatus.INSUFFICIENT_DATA,
                dimension_winners={},
                rationale="Insufficient CARspective Score data to determine overall winner.",
            )

        best_idx, best_score = max(valid, key=lambda x: x[1])
        second_score = sorted([s for _, s in valid], reverse=True)[1]

        if best_score - second_score < 3:
            overall_status = CategoryWinnerStatus.TIE
            overall_winner = None
            rationale = f"CARspective Scores are within 3 points ({best_score} vs {second_score}), making this a close comparison on intrinsic merit."
        else:
            overall_status = CategoryWinnerStatus.WINNER
            overall_winner = best_idx
            rationale = f"{score_results[best_idx].vehicle_summary} leads on intrinsic merit ({best_score}/100 vs {second_score}/100)."

        # Dimension winners
        dimension_winners = {}
        all_dim_names = [dn.value for dn in ScoreDimensionName]
        for dim_name in all_dim_names:
            dim_scores = []
            for idx, vs in enumerate(vehicle_scores):
                s = vs.dimensions.get(dim_name)
                if s is not None:
                    dim_scores.append((idx, s))
            if len(dim_scores) < 2:
                dimension_winners[dim_name] = None
            else:
                best_d_idx, best_d_score = max(dim_scores, key=lambda x: x[1])
                second_d = sorted([s for _, s in dim_scores], reverse=True)[1]
                dimension_winners[dim_name] = best_d_idx if (best_d_score - second_d) >= 5 else None

        return ScoreComparison(
            vehicle_scores=vehicle_scores,
            overall_winner_index=overall_winner,
            overall_status=overall_status,
            dimension_winners=dimension_winners,
            rationale=rationale,
        )

    # ────────────────────────────────────────────────────────────────
    # Valuation Comparison
    # ────────────────────────────────────────────────────────────────

    def _build_valuation_comparison(
        self, valuation_results: List[ValuationResponse], n: int
    ) -> ValuationComparison:
        vehicle_valuations = []
        for idx, vr in enumerate(valuation_results):
            lower = vr.expected_fair_market_range.lower_bound if vr.expected_fair_market_range else None
            upper = vr.expected_fair_market_range.upper_bound if vr.expected_fair_market_range else None
            vehicle_valuations.append(VehicleValuationSummary(
                vehicle_index=idx,
                estimated_fair_market_value=vr.estimated_fair_market_value,
                estimated_fair_market_value_formatted=format_inr(vr.estimated_fair_market_value),
                expected_fair_range_lower=lower,
                expected_fair_range_upper=upper,
                confidence_state=vr.confidence_state,
                evidence_quality=vr.evidence_quality,
            ))

        return ValuationComparison(vehicle_valuations=vehicle_valuations)

    # ────────────────────────────────────────────────────────────────
    # Deal Comparison
    # ────────────────────────────────────────────────────────────────

    def _build_deal_comparison(
        self, deal_results: Dict[int, DealAnalysisResponse], n: int
    ) -> DealComparison:
        vehicle_deals = []
        for idx, dr in deal_results.items():
            vehicle_deals.append(VehicleDealSummary(
                vehicle_index=idx,
                asking_price=dr.asking_price,
                asking_price_formatted=dr.asking_price_formatted,
                deal_quality=dr.deal_quality.value,
                price_deviation_percent=dr.price_deviation.relative_difference_percent,
                range_position=dr.range_position.category.value,
            ))

        # Determine stronger deal
        stronger_idx = None
        rationale = None
        if len(vehicle_deals) >= 2:
            deal_quality_rank = {
                "GREAT_DEAL": 4, "FAIR_DEAL": 3, "OVERPRICED": 2,
                "UNUSUALLY_LOW_ASKING_PRICE": 1, "INSUFFICIENT_DATA": 0,
            }
            ranked = sorted(
                vehicle_deals,
                key=lambda d: (deal_quality_rank.get(d.deal_quality, 0), -d.price_deviation_percent),
                reverse=True,
            )
            if ranked[0].deal_quality != ranked[1].deal_quality:
                stronger_idx = ranked[0].vehicle_index
                rationale = (
                    f"Vehicle {ranked[0].vehicle_index} ({ranked[0].deal_quality}) "
                    f"represents a stronger deal than Vehicle {ranked[1].vehicle_index} ({ranked[1].deal_quality})."
                )
            else:
                # Same quality tier - compare deviation
                if abs(ranked[0].price_deviation_percent - ranked[1].price_deviation_percent) > 5.0:
                    # The one with lower deviation is better
                    better = min(vehicle_deals[:2], key=lambda d: d.price_deviation_percent)
                    stronger_idx = better.vehicle_index
                    rationale = (
                        f"Both listings classified as {ranked[0].deal_quality}, "
                        f"but Vehicle {better.vehicle_index} has a lower deviation from fair market value."
                    )
                else:
                    rationale = (
                        f"Both listings classified as {ranked[0].deal_quality} with similar deviation from fair market value."
                    )

        return DealComparison(
            vehicle_deals=vehicle_deals,
            stronger_deal_index=stronger_idx,
            rationale=rationale,
        )

    # ────────────────────────────────────────────────────────────────
    # User Fit Comparison
    # ────────────────────────────────────────────────────────────────

    def _build_user_fit_comparison(
        self, user_fit_results: Dict[int, RecommendationResponse], n: int
    ) -> UserFitComparison:
        vehicle_fits = []
        for idx in sorted(user_fit_results.keys()):
            rec = user_fit_results[idx]
            uf = rec.user_fit
            vehicle_fits.append(VehicleUserFitSummary(
                vehicle_index=idx,
                overall_fit=uf.overall_fit,
                budget_fit=uf.budget_fit,
                usage_fit=uf.usage_fit,
                family_fit=uf.family_fit,
                powertrain_fit=uf.powertrain_fit,
                priority_alignment=uf.priority_alignment,
                fit_summary=uf.fit_summary,
                evidence_state="USER_STATED",
            ))

        best_fit_idx = None
        status = CategoryWinnerStatus.NOT_APPLICABLE
        rationale = None

        if len(vehicle_fits) >= 2:
            sorted_fits = sorted(vehicle_fits, key=lambda f: f.overall_fit, reverse=True)
            diff = sorted_fits[0].overall_fit - sorted_fits[1].overall_fit
            if diff >= 10:
                best_fit_idx = sorted_fits[0].vehicle_index
                status = CategoryWinnerStatus.WINNER
                rationale = (
                    f"Vehicle {best_fit_idx} has meaningfully stronger user fit "
                    f"({sorted_fits[0].overall_fit}/100 vs {sorted_fits[1].overall_fit}/100)."
                )
            elif diff >= 3:
                best_fit_idx = sorted_fits[0].vehicle_index
                status = CategoryWinnerStatus.WINNER
                rationale = (
                    f"Vehicle {best_fit_idx} has a slight user fit advantage "
                    f"({sorted_fits[0].overall_fit}/100 vs {sorted_fits[1].overall_fit}/100)."
                )
            else:
                status = CategoryWinnerStatus.TIE
                rationale = (
                    f"User fit is within 3 points ({sorted_fits[0].overall_fit}/100 vs "
                    f"{sorted_fits[1].overall_fit}/100), indicating no clear preference."
                )

        return UserFitComparison(
            vehicle_fits=vehicle_fits,
            best_fit_index=best_fit_idx,
            status=status,
            rationale=rationale,
        )

    # ────────────────────────────────────────────────────────────────
    # Trade-offs
    # ────────────────────────────────────────────────────────────────

    def _build_tradeoffs(
        self,
        score_results: List[ScoreResponse],
        specifications: List[SpecificationComparison],
        n: int,
    ) -> List[TradeOff]:
        tradeoffs = []
        if n < 2:
            return tradeoffs

        # Score-based trade-offs: find dimensions where different vehicles win
        dim_winners: Dict[str, Tuple[int, int]] = {}
        for sr_idx, sr in enumerate(score_results):
            for d in sr.dimensions:
                if d.score is not None:
                    key = d.dimension_name.value
                    if key not in dim_winners:
                        dim_winners[key] = (sr_idx, d.score)
                    elif d.score > dim_winners[key][1]:
                        dim_winners[key] = (sr_idx, d.score)

        # Find dimensions won by different vehicles
        unique_winners = {}
        for dim_name, (winner_idx, winner_score) in dim_winners.items():
            other_scores = []
            for sr_idx, sr in enumerate(score_results):
                if sr_idx != winner_idx:
                    for d in sr.dimensions:
                        if d.dimension_name.value == dim_name and d.score is not None:
                            other_scores.append((sr_idx, d.score))
            if other_scores:
                worst_idx, worst_score = min(other_scores, key=lambda x: x[1])
                if winner_score - worst_score >= 10:
                    if winner_idx not in unique_winners:
                        unique_winners[winner_idx] = []
                    unique_winners[winner_idx].append((dim_name, worst_idx, winner_score, worst_score))

        # Generate trade-off pairs
        winner_indices = list(unique_winners.keys())
        for i in range(len(winner_indices)):
            for j in range(i + 1, len(winner_indices)):
                idx_a = winner_indices[i]
                idx_b = winner_indices[j]
                dims_a = unique_winners[idx_a]
                dims_b = unique_winners.get(idx_b, [])

                # Find dims where A beats B and B beats A
                a_beats_b = [d for d in dims_a if d[1] == idx_b]
                b_beats_a = [d for d in dims_b if d[1] == idx_a]

                if a_beats_b and b_beats_a:
                    a_dim = a_beats_b[0][0]
                    b_dim = b_beats_a[0][0]
                    tradeoffs.append(TradeOff(
                        dimension=f"{a_dim} vs {b_dim}",
                        advantage_vehicle_index=idx_a,
                        disadvantage_vehicle_index=idx_b,
                        description=(
                            f"{score_results[idx_a].vehicle_summary} leads in {a_dim} "
                            f"({a_beats_b[0][2]}/100 vs {a_beats_b[0][3]}/100), "
                            f"while {score_results[idx_b].vehicle_summary} leads in {b_dim} "
                            f"({b_beats_a[0][2]}/100 vs {b_beats_a[0][3]}/100). "
                            f"The main trade-off is {a_dim.lower()} versus {b_dim.lower()}."
                        ),
                        evidence_quality="EMPIRICAL",
                    ))

        return tradeoffs

    # ────────────────────────────────────────────────────────────────
    # Best-For Labels
    # ────────────────────────────────────────────────────────────────

    def _build_best_for_labels(
        self,
        score_results: List[ScoreResponse],
        vehicles: List[ComparisonVehicle],
        specifications: List[SpecificationComparison],
        n: int,
    ) -> List[BestForLabel]:
        labels = []
        if n < 2:
            return labels

        # Ground clearance winner → "Best for rough roads"
        gc_spec = next((s for s in specifications if s.spec_key == "ground_clearance_mm"), None)
        if gc_spec and gc_spec.winner_index is not None and gc_spec.significance == DifferenceSignificance.MEANINGFUL:
            labels.append(BestForLabel(
                label="Best for rough roads / monsoon conditions",
                vehicle_index=gc_spec.winner_index,
                rationale=f"Highest verified ground clearance at {gc_spec.values[gc_spec.winner_index].display_value}.",
                evidence_quality="SUPPORTED",
            ))

        # Boot capacity winner → "Best for families / cargo"
        boot_spec = next((s for s in specifications if s.spec_key == "boot_capacity_l"), None)
        if boot_spec and boot_spec.winner_index is not None and boot_spec.significance == DifferenceSignificance.MEANINGFUL:
            labels.append(BestForLabel(
                label="Best for families / cargo space",
                vehicle_index=boot_spec.winner_index,
                rationale=f"Largest boot capacity at {boot_spec.values[boot_spec.winner_index].display_value}.",
                evidence_quality="SUPPORTED",
            ))

        # Fuel efficiency winner → "Best for city driving / fuel economy"
        eff_spec = next((s for s in specifications if s.spec_key == "claimed_efficiency_kmpl"), None)
        if eff_spec and eff_spec.winner_index is not None and eff_spec.significance == DifferenceSignificance.MEANINGFUL:
            labels.append(BestForLabel(
                label="Best for fuel economy",
                vehicle_index=eff_spec.winner_index,
                rationale=f"Highest claimed fuel efficiency at {eff_spec.values[eff_spec.winner_index].display_value}.",
                evidence_quality="SUPPORTED",
            ))

        # Safety winner → "Best for safety"
        safety_scores = []
        for idx, sr in enumerate(score_results):
            for d in sr.dimensions:
                if d.dimension_name == ScoreDimensionName.STRUCTURAL_SAFETY and d.score is not None:
                    safety_scores.append((idx, d.score))
        if len(safety_scores) >= 2:
            best_safety = max(safety_scores, key=lambda x: x[1])
            second_safety = sorted([s for _, s in safety_scores], reverse=True)[1]
            if best_safety[1] - second_safety >= 10:
                labels.append(BestForLabel(
                    label="Best for safety",
                    vehicle_index=best_safety[0],
                    rationale=f"Highest Structural Safety score at {best_safety[1]}/100.",
                    evidence_quality="VERIFIED" if best_safety[1] >= 80 else "EMPIRICAL",
                ))

        # Resale winner → "Best for resale value"
        resale_scores = []
        for idx, sr in enumerate(score_results):
            for d in sr.dimensions:
                if d.dimension_name == ScoreDimensionName.RESALE_AND_MARKET_LIQUIDITY and d.score is not None:
                    resale_scores.append((idx, d.score))
        if len(resale_scores) >= 2:
            best_resale = max(resale_scores, key=lambda x: x[1])
            second_resale = sorted([s for _, s in resale_scores], reverse=True)[1]
            if best_resale[1] - second_resale >= 5:
                labels.append(BestForLabel(
                    label="Best for resale value",
                    vehicle_index=best_resale[0],
                    rationale=f"Highest Resale & Market Liquidity score at {best_resale[1]}/100.",
                    evidence_quality="EMPIRICAL",
                ))

        # Maintenance winner → "Best for low maintenance"
        maint_scores = []
        for idx, sr in enumerate(score_results):
            for d in sr.dimensions:
                if d.dimension_name == ScoreDimensionName.MAINTENANCE_AND_OWNERSHIP and d.score is not None:
                    maint_scores.append((idx, d.score))
        if len(maint_scores) >= 2:
            best_maint = max(maint_scores, key=lambda x: x[1])
            second_maint = sorted([s for _, s in maint_scores], reverse=True)[1]
            if best_maint[1] - second_maint >= 5:
                labels.append(BestForLabel(
                    label="Best for low-maintenance ownership",
                    vehicle_index=best_maint[0],
                    rationale=f"Highest Maintenance & Ownership score at {best_maint[1]}/100.",
                    evidence_quality="EMPIRICAL",
                ))

        return labels

    # ────────────────────────────────────────────────────────────────
    # Research Summaries
    # ────────────────────────────────────────────────────────────────

    def _build_research_summaries(
        self,
        vehicles: List[ComparisonVehicle],
        score_results: List[ScoreResponse],
        valuation_results: List[ValuationResponse],
        specifications: List[SpecificationComparison],
        n: int,
    ) -> List[VehicleResearchSummary]:
        summaries = []
        for idx in range(n):
            sr = score_results[idx]
            vr = valuation_results[idx]
            spec_key = self._get_spec_key(vehicles[idx])
            spec_data = VEHICLE_SPECS_DB.get(spec_key, {})

            strengths = []
            weaknesses = []
            unknowns = []
            ownership_notes = []

            # Derive from score dimensions
            for d in sr.dimensions:
                if d.score is not None and d.score >= 80:
                    strengths.append(f"{d.dimension_name.value}: {d.score}/100 — {d.contributing_factors[0] if d.contributing_factors else 'Strong performance'}")
                elif d.score is not None and d.score < 65:
                    weaknesses.append(f"{d.dimension_name.value}: {d.score}/100 — {d.contributing_factors[0] if d.contributing_factors else 'Below average'}")
                elif d.evidence_state == EvidenceState.INSUFFICIENT_DATA:
                    unknowns.append(f"{d.dimension_name.value}: Verified evidence unavailable")

            # Specification-based insights
            if spec_data.get("ground_clearance_mm") and spec_data["ground_clearance_mm"] >= 200:
                ownership_notes.append(f"High ground clearance ({spec_data['ground_clearance_mm']}mm) suitable for Indian road conditions.")
            if spec_data.get("claimed_efficiency_kmpl") and spec_data["claimed_efficiency_kmpl"] >= 20:
                ownership_notes.append(f"High claimed fuel efficiency ({spec_data['claimed_efficiency_kmpl']} km/l) reduces operating costs.")
            if spec_data.get("ncap_stars") and spec_data["ncap_stars"] >= 4:
                ownership_notes.append(f"Verified {spec_data['ncap_stars']}-Star Global NCAP rating provides occupant protection confidence.")

            # Missing specs
            if not spec_data:
                unknowns.append("Detailed OEM specifications not in CARspective verified database.")

            # Market position
            market_position = None
            if vr.estimated_fair_market_value:
                val_fmt = format_inr(vr.estimated_fair_market_value)
                market_position = f"Estimated fair market asking-price baseline: {val_fmt} ({vr.confidence_state})."

            summaries.append(VehicleResearchSummary(
                vehicle_index=idx,
                vehicle_summary=sr.vehicle_summary,
                strengths=strengths,
                weaknesses=weaknesses,
                unknowns=unknowns,
                ownership_notes=ownership_notes,
                market_position=market_position,
            ))

        return summaries

    # ────────────────────────────────────────────────────────────────
    # Overall Result
    # ────────────────────────────────────────────────────────────────

    def _build_overall_result(
        self,
        req: ComparisonRequest,
        score_results: List[ScoreResponse],
        deal_results: Dict[int, DealAnalysisResponse],
        user_fit_results: Dict[int, RecommendationResponse],
        n: int,
    ) -> OverallResult:
        """
        Deterministic overall winner synthesis.
        General mode: intrinsic quality + category strengths + evidence.
        Personalized mode: intrinsic quality + user fit + deal quality + risk + evidence.
        """
        # Gather scores
        overall_scores = []
        for idx, sr in enumerate(score_results):
            if sr.overall_score is not None:
                overall_scores.append((idx, sr.overall_score))

        if len(overall_scores) < 2:
            return OverallResult(
                result_type=OverallResultType.INSUFFICIENT_DATA,
                winner_index=None,
                winner_vehicle_summary=None,
                confidence="LIMITED",
                rationale="Insufficient CARspective Score data across compared vehicles.",
            )

        if req.mode == ComparisonMode.PERSONALIZED and user_fit_results:
            # Personalized composite: 40% intrinsic score + 30% user fit + 30% deal quality
            composite = {}
            for idx, score in overall_scores:
                intrinsic = score
                fit_score = 50  # default
                deal_score = 50  # default (neutral)

                if idx in user_fit_results:
                    fit_score = user_fit_results[idx].user_fit.overall_fit

                if idx in deal_results:
                    dq = deal_results[idx].deal_quality.value
                    deal_score = {"GREAT_DEAL": 95, "FAIR_DEAL": 75, "OVERPRICED": 30,
                                  "UNUSUALLY_LOW_ASKING_PRICE": 20, "INSUFFICIENT_DATA": 50}.get(dq, 50)

                composite[idx] = 0.4 * intrinsic + 0.3 * fit_score + 0.3 * deal_score

            sorted_comp = sorted(composite.items(), key=lambda x: x[1], reverse=True)
            best_idx, best_comp = sorted_comp[0]
            second_comp = sorted_comp[1][1]
            diff = best_comp - second_comp

        else:
            # General mode: primarily intrinsic score with category depth as tiebreaker
            sorted_scores = sorted(overall_scores, key=lambda x: x[1], reverse=True)
            best_idx, best_score = sorted_scores[0]
            second_score = sorted_scores[1][1]
            diff = best_score - second_score

        if diff < 3:
            return OverallResult(
                result_type=OverallResultType.CLOSE_DECISION,
                winner_index=None,
                winner_vehicle_summary=None,
                confidence="LIMITED",
                rationale=(
                    f"The compared vehicles are within {diff:.1f} points of each other "
                    f"in {'composite personalized scoring' if req.mode == ComparisonMode.PERSONALIZED else 'intrinsic merit'}. "
                    f"This is a close decision and the preferred choice depends on individual priorities."
                ),
                major_tradeoff="Vehicle strengths differ by category — review dimension-level comparisons for informed decision-making.",
            )

        confidence = "HIGH" if diff >= 10 else "MODERATE"
        winner_summary = score_results[best_idx].vehicle_summary

        # Identify major trade-off
        major_tradeoff = None
        loser_idx = sorted_scores[1][0] if req.mode != ComparisonMode.PERSONALIZED else sorted_comp[1][0]
        loser_advantages = []
        for d in score_results[loser_idx].dimensions:
            winner_d = None
            for wd in score_results[best_idx].dimensions:
                if wd.dimension_name == d.dimension_name:
                    winner_d = wd
                    break
            if d.score is not None and winner_d and winner_d.score is not None:
                if d.score > winner_d.score + 5:
                    loser_advantages.append(d.dimension_name.value)
        if loser_advantages:
            loser_summary = score_results[loser_idx].vehicle_summary
            major_tradeoff = (
                f"{loser_summary} offers advantages in {', '.join(loser_advantages)}, "
                f"but {winner_summary} achieves a stronger overall result."
            )

        return OverallResult(
            result_type=OverallResultType.CLEAR_WINNER,
            winner_index=best_idx,
            winner_vehicle_summary=winner_summary,
            confidence=confidence,
            rationale=(
                f"{winner_summary} achieves the strongest overall result "
                f"{'across intrinsic merit, user fit, and deal quality' if req.mode == ComparisonMode.PERSONALIZED else 'on intrinsic vehicle merit'}."
            ),
            major_tradeoff=major_tradeoff,
        )

    # ────────────────────────────────────────────────────────────────
    # Limitations
    # ────────────────────────────────────────────────────────────────

    def _build_limitations(
        self,
        req: ComparisonRequest,
        deal_results: Dict[int, DealAnalysisResponse],
        user_fit_results: Dict[int, Any],
    ) -> List[str]:
        limitations = [
            "Comparison reflects available evidence and may not capture post-production variants or undisclosed modifications.",
            "CARspective Scores evaluate intrinsic vehicle quality and are independent of asking price or user budget.",
            "Specifications are sourced from manufacturer OEM data (SUPPORTED) and crash-test registries (VERIFIED).",
            "Missing specifications are reported as 'Data unavailable' rather than estimated or inferred.",
        ]

        if deal_results:
            limitations.append(
                "Deal quality reflects asking price positioning relative to empirical fair market range. "
                "A stronger deal does not imply a better vehicle."
            )

        if user_fit_results:
            limitations.append(
                "User fit calculations use USER_STATED preferences and do not represent verified constraints."
            )

        limitations.append(
            "Always perform independent mechanical, electrical, and legal title verification before purchase."
        )

        return limitations
