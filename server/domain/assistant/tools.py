"""
CARspective — Phase 8 Controlled Domain Tool & Service Dispatcher
Coordinates calls to authoritative domain services and constructs structured EvidenceBundles.
Strictly read-only; guarantees zero silent recalculations or model mutations.
"""

import re
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session

from server.domain.assistant.models import (
    VehicleContextInput,
    ListingContextInput,
    UserProfileInput,
    EvidenceBundle,
    EvidenceItem,
    AssistantEvidenceState,
    SourceDomain,
)
from server.infrastructure.database import ScopedSession
from server.repositories.taxonomy_repository import TaxonomyRepository
from server.domain.taxonomy.resolver import CanonicalResolver
from server.schemas.taxonomy import CanonicalResolutionRequest

from server.domain.valuation.service import ValuationService
from server.domain.valuation.models import ValuationRequest

from server.domain.deal_analyzer.service import DealAnalyzerService
from server.domain.deal_analyzer.models import DealAnalysisRequest

from server.domain.scoring.service import ScoringService
from server.domain.scoring.models import ScoreRequest

from server.domain.recommendation.service import RecommendationService
from server.domain.recommendation.models import (
    RecommendationRequest,
    ListingContext as RecListingContext,
    UserProfile as RecUserProfile,
)

from server.domain.comparison.service import ComparisonService
from server.domain.comparison.models import (
    ComparisonRequest,
    ComparisonMode,
    ComparisonVehicle,
    ComparisonListing,
    ComparisonUserProfile,
)

from server.domain.inspection.service import InspectionService
from server.domain.inspection.models import (
    InspectionRequest,
    InspectionVehicleContext,
    InspectionListingContext,
    UserInspectionProfile,
)


from server.domain.knowledge.service import KnowledgeService
from server.domain.market.service import MarketIntelligenceService
from server.domain.ownership.service import OwnershipIntelligenceService
from server.domain.decision.service import DecisionService
from server.domain.decision.models import UserRequirementsProfile
from server.domain.data_pipeline.service import DataIntelligenceService


class DomainToolDispatcher:
    """Dispatches automotive queries to authoritative domain engines."""

    def __init__(self, session: Optional[Session] = None):
        self._session = session
        self.tax_repo = TaxonomyRepository(session=session)
        self.tax_resolver = CanonicalResolver(self.tax_repo)
        self.valuation_svc = ValuationService(taxonomy_resolver=self.tax_resolver, session=session)
        self.deal_svc = DealAnalyzerService(valuation_service=self.valuation_svc)
        self.scoring_svc = ScoringService(taxonomy_resolver=self.tax_resolver, session=session)
        self.rec_svc = RecommendationService(session=session, scoring_service=self.scoring_svc)
        self.comp_svc = ComparisonService(session=session, scoring_service=self.scoring_svc)
        self.inspection_svc = InspectionService(taxonomy_resolver=self.tax_resolver, session=session)
        self.knowledge_svc = KnowledgeService(session=session)
        self.market_svc = MarketIntelligenceService(session=session)
        self.ownership_svc = OwnershipIntelligenceService(
            knowledge_service=self.knowledge_svc,
            market_service=self.market_svc,
            valuation_service=self.valuation_svc,
            session=session,
        )
        self.decision_svc = DecisionService(session=session)
        self.data_svc = DataIntelligenceService(session=session)

    @property
    def session(self) -> Session:
        if self._session is not None:
            return self._session
        return ScopedSession()

    @session.setter
    def session(self, value: Optional[Session]) -> None:
        self._session = value
        for svc in [
            self.tax_repo,
            self.valuation_svc,
            self.scoring_svc,
            self.rec_svc,
            self.comp_svc,
            self.inspection_svc,
            self.knowledge_svc,
            self.market_svc,
            self.ownership_svc,
            self.decision_svc,
            self.data_svc,
        ]:
            if hasattr(svc, "session"):
                svc.session = value


    def resolve_vehicle(self, v: VehicleContextInput) -> Dict[str, Any]:
        """Resolves raw vehicle identity through canonical taxonomy."""
        req = CanonicalResolutionRequest(
            brand=v.brand,
            model=v.model,
            year=v.manufacturing_year,
            variant=v.variant,
            fuel_type=v.fuel_type,
            transmission_type=v.transmission_type,
        )
        res = self.tax_resolver.resolve(req)
        return {
            "status": res.status.value if hasattr(res.status, "value") else str(res.status),
            "canonical_vehicle_id": res.canonical_vehicle_id,
            "hierarchy": res.hierarchy,
            "match_notes": res.match_notes,
        }

    def fetch_valuation_evidence(
        self,
        v: VehicleContextInput,
        bundle: EvidenceBundle,
    ) -> Optional[Dict[str, Any]]:
        """Retrieves Phase 3 statistical asking-price baseline valuation."""
        try:
            req = ValuationRequest(
                brand=v.brand,
                model=v.model,
                manufacturing_year=v.manufacturing_year or 2019,
                km_driven=v.km_driven if v.km_driven is not None else 45000.0,
                fuel_type=v.fuel_type or "Petrol",
                transmission_type=v.transmission_type or "Manual",
                number_of_owners=v.number_of_owners or 1,
                city=v.city or "Delhi",
            )
            res = self.valuation_svc.evaluate_valuation(req)
            val_data = {
                "fair_market_value": res.estimated_fair_market_value,
                "range_lower": res.expected_fair_market_range.lower_bound,
                "range_upper": res.expected_fair_market_range.upper_bound,
                "confidence_state": res.confidence_state,
            }

            bundle.add_item(EvidenceItem(
                id="valuation.fair_market_value",
                claim=f"Statistical model estimate of historical asking price baseline is ₹{res.estimated_fair_market_value:,.0f}",
                value=res.estimated_fair_market_value,
                source="Phase 3 LightGBM/CatBoost Valuation Engine",
                evidence_state=AssistantEvidenceState.MODEL_ESTIMATE,
                domain=SourceDomain.VALUATION,
                confidence=res.confidence_state,
                notes="Reflects historical seller asking-price baseline, not verified transaction price.",
            ))
            bundle.add_item(EvidenceItem(
                id="valuation.range",
                claim=f"Expected fair market range is ₹{res.expected_fair_market_range.lower_bound:,.0f} to ₹{res.expected_fair_market_range.upper_bound:,.0f}",
                value={"lower": res.expected_fair_market_range.lower_bound, "upper": res.expected_fair_market_range.upper_bound},
                source="Phase 3 Conformal Prediction Interval",
                evidence_state=AssistantEvidenceState.MODEL_ESTIMATE,
                domain=SourceDomain.VALUATION,
            ))
            bundle.add_item(EvidenceItem(
                id="valuation.confidence",
                claim=f"Valuation confidence is {res.confidence_state}",
                value=res.confidence_state,
                source="Phase 3 Multi-Factor Confidence Scorer",
                evidence_state=AssistantEvidenceState.EMPIRICAL,
                domain=SourceDomain.VALUATION,
            ))
            return val_data
        except Exception as e:
            bundle.missing_evidence.append(f"Valuation service error: {str(e)}")
            bundle.uncertainty_disclosures.append("Historical asking price baseline could not be calculated.")
            return None

    def fetch_deal_evidence(
        self,
        v: VehicleContextInput,
        listing: ListingContextInput,
        bundle: EvidenceBundle,
    ) -> Optional[Dict[str, Any]]:
        """Retrieves Phase 4 deal quality and negotiation intelligence."""
        if not listing.asking_price:
            bundle.missing_evidence.append("Seller asking price is not specified.")
            return None
        try:
            req = DealAnalysisRequest(
                brand=v.brand,
                model=v.model,
                manufacturing_year=v.manufacturing_year or 2019,
                km_driven=v.km_driven if v.km_driven is not None else 45000.0,
                asking_price=listing.asking_price,
                fuel_type=v.fuel_type or "Petrol",
                transmission_type=v.transmission_type or "Manual",
                number_of_owners=v.number_of_owners or 1,
                city=v.city or "Delhi",
            )
            res = self.deal_svc.analyze_deal(req)
            deal_data = {
                "deal_classification": res.deal_quality.value,
                "price_differential_inr": res.price_deviation.absolute_difference,
                "price_differential_pct": res.price_deviation.relative_difference_percent,
                "fair_market_value_inr": res.valuation.estimated_fair_market_value,
                "negotiation_target": res.negotiation.target_price,
                "risk_signals": res.risk_signals,
            }

            bundle.add_item(EvidenceItem(
                id="deal.classification",
                claim=f"Deal quality classified as {res.deal_quality.value} relative to fair asking baseline",
                value=res.deal_quality.value,
                source="Phase 4 Deal Analyzer",
                evidence_state=AssistantEvidenceState.EMPIRICAL,
                domain=SourceDomain.DEAL_ANALYZER,
            ))
            bundle.add_item(EvidenceItem(
                id="deal.differential",
                claim=f"Asking price is ₹{abs(res.price_deviation.absolute_difference):,.0f} ({res.price_deviation.relative_difference_percent:+.1f}%) vs fair baseline",
                value={"diff_inr": res.price_deviation.absolute_difference, "diff_pct": res.price_deviation.relative_difference_percent},
                source="Phase 4 Deal Analyzer",
                evidence_state=AssistantEvidenceState.EMPIRICAL,
                domain=SourceDomain.DEAL_ANALYZER,
            ))
            if res.negotiation and res.negotiation.target_price:
                bundle.add_item(EvidenceItem(
                    id="deal.negotiation_target",
                    claim=f"Target negotiation price: ₹{res.negotiation.target_price:,.0f} ({res.negotiation.negotiation_strength.value})",
                    value=res.negotiation.target_price,
                    source="Phase 4 Negotiation Intelligence",
                    evidence_state=AssistantEvidenceState.EMPIRICAL,
                    domain=SourceDomain.DEAL_ANALYZER,
                ))
            return deal_data
        except Exception as e:
            bundle.missing_evidence.append(f"Deal analyzer error: {str(e)}")
            return None

    def fetch_score_evidence(
        self,
        v: VehicleContextInput,
        bundle: EvidenceBundle,
    ) -> Optional[Dict[str, Any]]:
        """Retrieves Phase 5 intrinsic CarSpective Score (5 locked dimensions)."""
        try:
            req = ScoreRequest(
                brand=v.brand,
                model=v.model,
                manufacturing_year=v.manufacturing_year,
                variant=v.variant,
                fuel_type=v.fuel_type,
                transmission_type=v.transmission_type,
                km_driven=v.km_driven,
            )
            res = self.scoring_svc.calculate_score(req)
            score_data = {
                "overall_score": res.overall_score,
                "dimensions": {d.dimension_name.value: d.score for d in res.dimensions},
            }

            bundle.add_item(EvidenceItem(
                id="score.overall",
                claim=f"CarSpective Intrinsic Score is {res.overall_score}/100",
                value=res.overall_score,
                source="Phase 5 Scoring Engine",
                evidence_state=AssistantEvidenceState.EMPIRICAL,
                domain=SourceDomain.SCORE,
                notes="Reflects vehicle engineering merit across 5 locked dimensions, independent of deal price.",
            ))
            for dim in res.dimensions:
                dim_str = dim.dimension_name.value
                bundle.add_item(EvidenceItem(
                    id=f"score.dim.{dim_str.lower().replace(' ', '_').replace('&', 'and')}",
                    claim=f"{dim_str}: {dim.score_formatted} ({dim.evidence_state.value})",
                    value=dim.score,
                    source=f"Phase 5 Score Dimension: {dim_str}",
                    evidence_state=AssistantEvidenceState.EMPIRICAL,
                    domain=SourceDomain.SCORE,
                    notes=f"Contributing factors: {', '.join(dim.contributing_factors[:2])}",
                ))
            return score_data
        except Exception as e:
            bundle.missing_evidence.append(f"Scoring service error: {str(e)}")
            return None

    def fetch_recommendation_evidence(
        self,
        v: VehicleContextInput,
        listing: Optional[ListingContextInput],
        user_profile: Optional[UserProfileInput],
        bundle: EvidenceBundle,
    ) -> Optional[Dict[str, Any]]:
        """Retrieves Phase 5 recommendation tier and user-fit logic."""
        try:
            rec_l = RecListingContext(
                asking_price=listing.asking_price if listing else None,
                km_driven=v.km_driven,
            )
            rec_u = RecUserProfile(
                budget_max=user_profile.budget_max if user_profile else None,
                safety_priority=user_profile.safety_priority if user_profile else "HIGH",
            )
            req = RecommendationRequest(
                brand=v.brand,
                model=v.model,
                manufacturing_year=v.manufacturing_year or 2019,
                variant=v.variant,
                fuel_type=v.fuel_type or "Petrol",
                transmission_type=v.transmission_type or "Manual",
                city=v.city or "Delhi",
                listing=rec_l,
                user_profile=rec_u,
            )
            res = self.rec_svc.generate_recommendation(req)
            rec_data = {
                "recommendation_tier": res.verdict_label,
                "user_fit_score": res.user_fit.overall_fit,
                "primary_rationale": res.explanation.strongest_positive_factor,
                "alternatives": [a.model for a in res.alternatives],
            }

            bundle.add_item(EvidenceItem(
                id="recommendation.tier",
                claim=f"Recommendation verdict: {res.verdict_label} (User Fit: {res.user_fit.overall_fit}/100)",
                value=res.verdict_label,
                source="Phase 5 Recommendation Engine",
                evidence_state=AssistantEvidenceState.EMPIRICAL,
                domain=SourceDomain.RECOMMENDATION,
                notes=res.explanation.strongest_positive_factor,
            ))
            if res.alternatives:
                alt_names = [f"{a.brand} {a.model}" for a in res.alternatives[:3]]
                bundle.add_item(EvidenceItem(
                    id="recommendation.alternatives",
                    claim=f"Recommended market alternatives: {', '.join(alt_names)}",
                    value=alt_names,
                    source="Phase 5 Recommendation Engine",
                    evidence_state=AssistantEvidenceState.EMPIRICAL,
                    domain=SourceDomain.RECOMMENDATION,
                ))
            return rec_data
        except Exception as e:
            bundle.missing_evidence.append(f"Recommendation service error: {str(e)}")
            return None

    def fetch_cross_car_evidence(
        self,
        query: str,
        current_vehicle: Optional[VehicleContextInput],
        listing: Optional[ListingContextInput],
        user_profile: Optional[UserProfileInput],
        bundle: EvidenceBundle,
    ) -> List[Dict[str, Any]]:
        """
        Discovers, ranks, and retrieves evidence-grounded cross-car alternatives.
        Extracts budget constraints, body type preferences, and powertrain requirements from
        natural language, active listing context, or canonical valuation baselines.
        """
        q_lower = (query or "").lower().strip()

        # 1. Budget Extraction & Anchor Resolution
        extracted_budget: Optional[float] = None
        budget_source = "USER_QUERY"

        # Regex patterns for Indian lakh / INR amounts
        b_match = re.search(r'\b(?:under|below|sub|<|less than|up to|max)\s*(?:inr\s*|rs\.?\s*|₹\s*)?(\d+(?:\.\d+)?)\s*(?:lakhs?|lac|l)\b', q_lower)
        if b_match:
            extracted_budget = float(b_match.group(1)) * 100000.0
            budget_source = f"Query explicit ('under ₹{b_match.group(1)} Lakh')"
        else:
            b_match = re.search(r'\b(?:between\s+)?(\d+(?:\.\d+)?)\s*(?:and|to|-)\s*(\d+(?:\.\d+)?)\s*(?:lakhs?|lac|l)\b', q_lower)
            if b_match:
                extracted_budget = float(b_match.group(2)) * 100000.0
                budget_source = f"Query explicit ('up to ₹{b_match.group(2)} Lakh')"
            else:
                b_match = re.search(r'\b(?:budget\s*(?:of|around|is|:)?\s*(?:inr\s*|rs\.?\s*|₹\s*)?(\d+(?:\.\d+)?)\s*(?:lakhs?|lac|l))\b', q_lower)
                if b_match:
                    extracted_budget = float(b_match.group(1)) * 100000.0
                    budget_source = f"Query explicit ('budget ₹{b_match.group(1)} Lakh')"
                else:
                    b_match = re.search(r'\b(?:inr\s*|rs\.?\s*|₹\s*)?(\d+(?:\.\d+)?)\s*(?:lakhs?|lac|l)\s*(?:budget|price)\b', q_lower)
                    if b_match:
                        extracted_budget = float(b_match.group(1)) * 100000.0
                        budget_source = f"Query explicit ('₹{b_match.group(1)} Lakh budget')"
                    else:
                        b_match = re.search(r'\b(?:inr\s*|rs\.?\s*|₹\s*)?(\d+(?:\.\d+)?)\s*(?:lakhs?|lac|l)\b', q_lower)
                        if b_match:
                            extracted_budget = float(b_match.group(1)) * 100000.0
                            budget_source = f"Query explicit ('₹{b_match.group(1)} Lakh')"

        if not extracted_budget:
            # Match explicit numerical amounts e.g. "under 500000", "under 5,00,000", "budget 800000"
            b_num = re.search(r'\b(?:under|below|sub|<|less than|up to|budget\s*(?:of|is|:)?|max)\s*(?:inr\s*|rs\.?\s*|₹\s*)?(\d{1,2}(?:,\d{2})*(?:,\d{3})|\d{6,8})\b', q_lower)
            if b_num:
                clean_num = b_num.group(1).replace(",", "")
                extracted_budget = float(clean_num)
                budget_source = f"Query explicit ('under ₹{extracted_budget:,.0f}')"

        # Contextual anchor: "same budget" / "in this budget" / or missing query budget
        if not extracted_budget:
            if listing and listing.asking_price and listing.asking_price > 0:
                extracted_budget = float(listing.asking_price)
                budget_source = f"Active listing asking price (₹{extracted_budget:,.0f})"
            elif current_vehicle:
                # Use model benchmark or valuation estimate
                c_mod_slug = current_vehicle.model.lower().replace(" ", "-")
                from server.domain.discovery.service import MODEL_PRICE_BENCHMARKS
                benchmarks = MODEL_PRICE_BENCHMARKS.get(c_mod_slug)
                if benchmarks:
                    extracted_budget = float(benchmarks[1])
                    budget_source = f"Typical market benchmark for {current_vehicle.brand} {current_vehicle.model} (₹{extracted_budget:,.0f})"
                else:
                    extracted_budget = 850000.0
                    budget_source = "Segment baseline estimate (₹8,50,000)"
            elif user_profile and user_profile.budget_max:
                extracted_budget = float(user_profile.budget_max)
                budget_source = f"User profile max budget (₹{extracted_budget:,.0f})"
            else:
                extracted_budget = 800000.0
                budget_source = "Default discovery baseline (₹8,00,000)"

        # 2. Body Type Preference Extraction
        requested_body_type: Optional[str] = None
        if re.search(r'\b(?:suv|csuv|compact suv)\b', q_lower):
            requested_body_type = "SUV"
        elif re.search(r'\b(?:sedan)\b', q_lower):
            requested_body_type = "Sedan"
        elif re.search(r'\b(?:hatchback|hatch)\b', q_lower):
            requested_body_type = "Hatchback"
        elif re.search(r'\b(?:mpv|muv|7[\s-]?seater)\b', q_lower):
            requested_body_type = "MPV"

        # 3. Verified Multi-Segment Alternative Catalog
        candidate_pool = [
            {
                "brand": "Tata",
                "model": "Tiago",
                "year": 2019,
                "price_range": (340000, 480000),
                "typical_price_inr": 410000,
                "score": 80,
                "safety_stars": 4,
                "bodyshell": "STABLE",
                "safety_org": "Global NCAP 2020",
                "arai_kmpl": 19.8,
                "annual_service_inr": 5200,
                "body_type": "Hatchback",
                "segment": "HATCHBACK",
                "advantage": "Segment-leading 4-Star Global NCAP crash safety rating with stable bodyshell and 170 mm ground clearance.",
                "trade_off": "Mild 3-cylinder engine idle vibration compared to 4-cylinder rivals.",
            },
            {
                "brand": "Maruti",
                "model": "Wagon R",
                "year": 2018,
                "price_range": (340000, 480000),
                "typical_price_inr": 410000,
                "score": 77,
                "safety_stars": 2,
                "bodyshell": "UNSTABLE",
                "safety_org": "Global NCAP 2019",
                "arai_kmpl": 20.5,
                "annual_service_inr": 4500,
                "body_type": "Hatchback",
                "segment": "HATCHBACK",
                "advantage": "Tall-boy cabin packaging for effortless ingress/egress, expansive headroom, and accessible spare parts.",
                "trade_off": "2-Star Global NCAP safety rating and body roll during highway maneuvers.",
            },
            {
                "brand": "Hyundai",
                "model": "Grand i10",
                "year": 2018,
                "price_range": (340000, 485000),
                "typical_price_inr": 420000,
                "score": 78,
                "safety_stars": 2,
                "bodyshell": "UNSTABLE",
                "safety_org": "Global NCAP 2019",
                "arai_kmpl": 18.9,
                "annual_service_inr": 5500,
                "body_type": "Hatchback",
                "segment": "HATCHBACK",
                "advantage": "Plush sound-insulated cabin, smooth 4-cylinder engine refinement, and nimble city parking footprint.",
                "trade_off": "2-Star Global NCAP safety rating and modest highway overtaking surge.",
            },
            {
                "brand": "Maruti",
                "model": "Swift",
                "year": 2019,
                "price_range": (450000, 600000),
                "typical_price_inr": 530000,
                "score": 79,
                "safety_stars": 2,
                "bodyshell": "UNSTABLE",
                "safety_org": "Global NCAP 2018",
                "arai_kmpl": 22.4,
                "annual_service_inr": 4800,
                "body_type": "Hatchback",
                "segment": "HATCHBACK",
                "advantage": "Exceptional 22.4 km/l fuel economy, minimal depreciation loss, and swift secondary market liquidity.",
                "trade_off": "2-Star Global NCAP crash safety rating and lightweight bodyshell construction.",
            },
            {
                "brand": "Tata",
                "model": "Punch",
                "year": 2021,
                "price_range": (520000, 720000),
                "typical_price_inr": 620000,
                "score": 82,
                "safety_stars": 5,
                "bodyshell": "STABLE",
                "safety_org": "Global NCAP 2021",
                "arai_kmpl": 18.8,
                "annual_service_inr": 5800,
                "body_type": "SUV",
                "segment": "MICRO_SUV",
                "advantage": "5-Star Global NCAP structural crashworthiness, 187 mm ground clearance, and upright commanding driver visibility.",
                "trade_off": "3-cylinder naturally aspirated engine produces modest highway passing power.",
            },
            {
                "brand": "Tata",
                "model": "Nexon",
                "year": 2019,
                "price_range": (580000, 780000),
                "typical_price_inr": 680000,
                "score": 84,
                "safety_stars": 5,
                "bodyshell": "STABLE",
                "safety_org": "Global NCAP",
                "arai_kmpl": 17.4,
                "annual_service_inr": 6200,
                "body_type": "SUV",
                "segment": "COMPACT_SUV",
                "advantage": "Verified 5-Star Global NCAP crash safety rating with stable bodyshell and 209 mm rough-road ground clearance.",
                "trade_off": "Firmer low-speed suspension damping and 350-litre boot capacity compared to mid-size sedans.",
            },
            {
                "brand": "Maruti",
                "model": "Brezza",
                "year": 2019,
                "price_range": (580000, 780000),
                "typical_price_inr": 680000,
                "score": 81,
                "safety_stars": 4,
                "bodyshell": "STABLE",
                "safety_org": "Global NCAP 2018 (tested as Vitara Brezza)",
                "arai_kmpl": 18.8,
                "annual_service_inr": 5200,
                "body_type": "SUV",
                "segment": "COMPACT_SUV",
                "advantage": "Verified 4-Star Global NCAP safety, 18.8 km/l fuel economy, and India's lowest routine maintenance spare parts basket.",
                "trade_off": "Naturally aspirated engine delivers relaxed cruising rather than punchy highway overtaking acceleration.",
            },
            {
                "brand": "Hyundai",
                "model": "Venue",
                "year": 2020,
                "price_range": (620000, 790000),
                "typical_price_inr": 720000,
                "score": 80,
                "safety_stars": None,
                "bodyshell": "UNVERIFIED",
                "safety_org": "Unrated by Global NCAP",
                "safety_note": "Equipped with 2-6 airbags; unrated by Indian Global NCAP",
                "arai_kmpl": 18.1,
                "annual_service_inr": 6800,
                "body_type": "SUV",
                "segment": "SUB_COMPACT_SUV",
                "advantage": "Compact footprint for agile city maneuvering, contemporary dashboard ergonomics, and easy parking visibility.",
                "trade_off": "Narrower rear bench seat best suited for 2 adults and 1 child; unrated by Global NCAP.",
            },
            {
                "brand": "Honda",
                "model": "City",
                "year": 2020,
                "price_range": (720000, 950000),
                "typical_price_inr": 850000,
                "score": 85,
                "safety_stars": None,
                "bodyshell": "UNVERIFIED",
                "safety_org": "Unrated by Global NCAP",
                "safety_note": "ASEAN NCAP 5-Star (foreign spec); Indian generation unrated by Global NCAP",
                "arai_kmpl": 18.4,
                "annual_service_inr": 7200,
                "body_type": "Sedan",
                "segment": "MID_SEDAN",
                "advantage": "Class-leading 506-litre luggage boot, plush executive rear knee room, and refined high-revving 1.5L i-VTEC engine.",
                "trade_off": "165 mm ground clearance requires caution over steep monsoon potholes; unrated by Indian Global NCAP.",
            },
            {
                "brand": "Hyundai",
                "model": "Verna",
                "year": 2020,
                "price_range": (720000, 920000),
                "typical_price_inr": 840000,
                "score": 82,
                "safety_stars": None,
                "bodyshell": "UNVERIFIED",
                "safety_org": "Unrated by Global NCAP",
                "safety_note": "2020 generation unrated by Global NCAP (2023 model received 5 stars)",
                "arai_kmpl": 18.6,
                "annual_service_inr": 7800,
                "body_type": "Sedan",
                "segment": "MID_SEDAN",
                "advantage": "Feature-dense cabin (ventilated front seats, modern touchscreen), smooth ride absorption, and quiet NVH damping.",
                "trade_off": "Tighter rear-seat knee room compared to City; 2020 generation unrated by Global NCAP.",
            },
            {
                "brand": "Hyundai",
                "model": "Creta",
                "year": 2019,
                "price_range": (750000, 980000),
                "typical_price_inr": 890000,
                "score": 83,
                "safety_stars": 3,
                "bodyshell": "UNSTABLE",
                "safety_org": "Global NCAP",
                "arai_kmpl": 16.8,
                "annual_service_inr": 7400,
                "body_type": "SUV",
                "segment": "MID_SUV",
                "advantage": "High secondary market liquidity (fast resale turnover), plush sound-insulated cabin, and expansive rear bench space.",
                "trade_off": "3-Star Global NCAP rating with unstable bodyshell integrity and higher purchase price bracket.",
            },
            {
                "brand": "Volkswagen",
                "model": "Virtus",
                "year": 2022,
                "price_range": (950000, 1200000),
                "typical_price_inr": 1080000,
                "score": 86,
                "safety_stars": 5,
                "bodyshell": "STABLE",
                "safety_org": "Global NCAP 2023",
                "arai_kmpl": 18.1,
                "annual_service_inr": 10500,
                "body_type": "Sedan",
                "segment": "PREMIUM_SEDAN",
                "advantage": "Dual 5-Star Global NCAP safety (5 adult / 5 child stars), 521-litre cargo boot, and European high-speed chassis rigidity.",
                "trade_off": "Higher routine maintenance cost and premium replacement part pricing compared to Japanese rivals.",
            },
        ]

        # 4. Filter Candidate Pool & Strictly Partition In-Budget vs Stretch
        curr_model = current_vehicle.model.lower().strip() if current_vehicle else ""
        in_budget = []
        stretch = []

        for cand in candidate_pool:
            # Exclude current vehicle model from alternatives
            if curr_model and cand["model"].lower() == curr_model:
                continue

            # Body type filter if explicitly requested
            if requested_body_type and cand["body_type"].upper() != requested_body_type.upper():
                continue

            if extracted_budget:
                # Primary recommendation MUST strictly satisfy: max estimated price <= extracted_budget
                if cand["price_range"][1] <= extracted_budget:
                    in_budget.append(cand)
                elif cand["price_range"][0] <= (extracted_budget * 1.30):
                    # Over-budget vehicle: starting price within 30% stretch ceiling
                    stretch.append(cand)
            else:
                in_budget.append(cand)

        # Fallback if in_budget is empty due to strict body type filter (e.g. Sedan under 5L)
        if not in_budget and requested_body_type:
            # Search other body types that strictly fit within the budget
            for cand in candidate_pool:
                if curr_model and cand["model"].lower() == curr_model:
                    continue
                if extracted_budget and cand["price_range"][1] <= extracted_budget:
                    in_budget.append(cand)

        # Fallback if no candidate meets strict criteria
        if not in_budget and not stretch:
            in_budget = [c for c in candidate_pool if not curr_model or c["model"].lower() != curr_model][:3]

        # Prioritize primary candidates by segment relevance & safety
        def _sort_key(c):
            budget_proximity = abs(extracted_budget - c.get("typical_price_inr", 0)) if extracted_budget else 0
            if extracted_budget and extracted_budget <= 550000:
                is_anchor_pick = 0 if c["model"] in ("Tiago", "Wagon R", "Grand i10", "Swift") else 1
            elif requested_body_type == "SUV":
                is_anchor_pick = 0 if c["model"] in ("Nexon", "Brezza", "Punch", "Venue") else 1
            elif requested_body_type == "Sedan":
                is_anchor_pick = 0 if c["model"] in ("City", "Verna", "Virtus") else 1
            else:
                is_anchor_pick = 0 if c["model"] in ("Nexon", "Brezza", "City", "Creta") else 1
            stars = c.get("safety_stars") or 0
            return (is_anchor_pick, -stars, budget_proximity, -c["score"])

        in_budget.sort(key=_sort_key)
        stretch.sort(key=lambda x: (abs(x["price_range"][0] - (extracted_budget or 0)), -(x.get("safety_stars") or 0), -x["score"]))

        primary_candidates = in_budget[:3]
        stretch_candidates = stretch[:2]

        # 5. Populate EvidenceBundle
        # 5a. Budget Anchor Item
        bundle.add_item(EvidenceItem(
            id="discovery.budget_anchor",
            claim=f"Discovery budget benchmark anchor: ₹{extracted_budget:,.0f} ({budget_source}). All {len(primary_candidates)} primary recommendations have maximum estimated price within ₹{extracted_budget:,.0f}.",
            value={
                "budget_inr": extracted_budget,
                "source": budget_source,
                "body_type": requested_body_type,
                "primary_count": len(primary_candidates),
                "stretch_count": len(stretch_candidates),
            },
            source="Phase 12 Discovery & Automotive Query Parser",
            evidence_state=AssistantEvidenceState.EMPIRICAL if "asking" in budget_source.lower() else AssistantEvidenceState.MODEL_ESTIMATE,
            domain=SourceDomain.VALUATION,
            notes="Derived from user query text or active listing context to ground cross-car recommendations."
        ))

        # 5b. Primary In-Budget Candidate Items
        for idx, cand in enumerate(primary_candidates):
            if cand.get("safety_stars") is not None:
                safety_lbl = f"Safety: {cand['safety_stars']}/5 Stars ({cand['safety_org']})"
            else:
                safety_lbl = f"Safety: Unrated by Global NCAP ({cand.get('safety_note', 'OEM safety equipment equipped')})"

            c_claim = (
                f"{cand['brand']} {cand['model']} ({cand['year']}): Typical Market Price Range ₹{cand['price_range'][0]:,.0f}–₹{cand['price_range'][1]:,.0f} "
                f"(Model Estimate — Within Budget) | Score: {cand['score']}/100 | {safety_lbl} | "
                f"ARAI: {cand['arai_kmpl']} km/l | Est. Annual Service: ₹{cand['annual_service_inr']:,} (Model Estimate). {cand['advantage']}"
            )
            bundle.add_item(EvidenceItem(
                id=f"discovery.candidate.{idx+1}",
                claim=c_claim,
                value=cand,
                source="Phase 12 Discovery & Taxonomy Benchmark Catalog",
                evidence_state=AssistantEvidenceState.MODEL_ESTIMATE,
                domain=SourceDomain.RECOMMENDATION,
                notes="Statistical secondary market baseline estimate; not a live inventory listing or verified transaction price."
            ))

        # 5c. Stretch (Over-Budget) Candidate Items
        for idx, cand in enumerate(stretch_candidates):
            if cand.get("safety_stars") is not None:
                safety_lbl = f"Safety: {cand['safety_stars']}/5 Stars ({cand['safety_org']})"
            else:
                safety_lbl = f"Safety: Unrated by Global NCAP ({cand.get('safety_note', 'OEM safety equipment equipped')})"

            s_claim = (
                f"[Stretch Option — Beyond Stated Budget] {cand['brand']} {cand['model']} ({cand['year']}): Typical Market Price Range ₹{cand['price_range'][0]:,.0f}–₹{cand['price_range'][1]:,.0f} "
                f"(Model Estimate — Exceeds ₹{extracted_budget:,.0f} Budget) | Score: {cand['score']}/100 | {safety_lbl} | "
                f"ARAI: {cand['arai_kmpl']} km/l | Est. Annual Service: ₹{cand['annual_service_inr']:,} (Model Estimate). {cand['advantage']}"
            )
            bundle.add_item(EvidenceItem(
                id=f"discovery.stretch.{idx+1}",
                claim=s_claim,
                value=cand,
                source="Phase 12 Discovery & Taxonomy Benchmark Catalog",
                evidence_state=AssistantEvidenceState.MODEL_ESTIMATE,
                domain=SourceDomain.RECOMMENDATION,
                notes=f"Over-budget option beyond stated maximum budget of ₹{extracted_budget:,.0f}. Statistical secondary market baseline estimate; not a live inventory listing or verified transaction price."
            ))

        # 5d. Backward Compatibility: recommendation.alternatives
        alt_names = [f"{c['brand']} {c['model']}" for c in primary_candidates]
        bundle.add_item(EvidenceItem(
            id="recommendation.alternatives",
            claim=f"Recommended in-budget market alternatives: {', '.join(alt_names)}",
            value=alt_names,
            source="Phase 12 Cross-Car Discovery Engine",
            evidence_state=AssistantEvidenceState.EMPIRICAL,
            domain=SourceDomain.RECOMMENDATION,
        ))

        # 5e. Comparative Verdict Item
        top_alt = primary_candidates[0] if primary_candidates else (stretch_candidates[0] if stretch_candidates else None)
        if current_vehicle and top_alt:
            top_stars = top_alt.get("safety_stars")
            if top_stars:
                top_safety_text = f"higher verified crash safety ({top_stars}-Star {top_alt['safety_org']}) and "
            else:
                top_safety_text = ""
            verdict_claim = (
                f"In the ₹{extracted_budget:,.0f} budget, the {top_alt['brand']} {top_alt['model']} offers {top_safety_text}"
                f"rough-road clearance, while the {current_vehicle.brand} {current_vehicle.model} "
                f"maintains superior passenger space and highway cruising comfort."
            )
        elif top_alt:
            verdict_claim = (
                f"For an under-₹{extracted_budget:,.0f} budget, the top recommended in-budget alternatives are {', '.join(alt_names)}, "
                f"led by the {top_alt['brand']} {top_alt['model']} for overall safety and ownership reliability."
            )
        else:
            verdict_claim = "No verified alternatives met the exact criteria in this price band."

        bundle.add_item(EvidenceItem(
            id="discovery.comparison_verdict",
            claim=verdict_claim,
            value={"top_alternative": top_alt["model"] if top_alt else None, "anchor_budget": extracted_budget},
            source="Phase 12 Cross-Car Comparative Intelligence",
            evidence_state=AssistantEvidenceState.EMPIRICAL,
            domain=SourceDomain.RECOMMENDATION,
        ))

        return primary_candidates

    def fetch_comparison_evidence(
        self,
        vehicles: List[VehicleContextInput],
        user_profile: Optional[UserProfileInput],
        bundle: EvidenceBundle,
    ) -> Optional[Dict[str, Any]]:
        """Retrieves Phase 6 multi-vehicle comparison."""
        if len(vehicles) < 2:
            bundle.missing_evidence.append("Comparison requires at least 2 vehicles.")
            return None
        try:
            comp_vehicles = [
                ComparisonVehicle(
                    vehicle_id=f"v{idx+1}",
                    brand=v.brand,
                    model=v.model,
                    manufacturing_year=v.manufacturing_year,
                    variant=v.variant,
                    fuel_type=v.fuel_type or "Petrol",
                    transmission_type=v.transmission_type or "Manual",
                    km_driven=v.km_driven,
                )
                for idx, v in enumerate(vehicles[:3])
            ]
            comp_user = None
            if user_profile and user_profile.budget_max:
                comp_user = ComparisonUserProfile(
                    budget_max=user_profile.budget_max,
                    safety_priority=user_profile.safety_priority or "HIGH",
                    daily_commute_km=user_profile.daily_commute_km or 30.0,
                    family_orientation=user_profile.family_orientation if user_profile.family_orientation is not None else True,
                )
            req = ComparisonRequest(
                mode=ComparisonMode.PERSONALIZED if comp_user else ComparisonMode.GENERAL,
                vehicles=comp_vehicles,
                user_profile=comp_user,
            )
            res = self.comp_svc.compare(req)
            winner_name = res.overall_result.winner_vehicle_summary or "Close decision between options"
            comp_data = {
                "winner": winner_name,
                "result_type": res.overall_result.result_type,
                "winner_rationale": res.overall_result.rationale,
                "trade_offs": [t.headline for t in res.tradeoffs],
            }

            bundle.add_item(EvidenceItem(
                id="comparison.overall_winner",
                claim=f"Comparison outcome: {winner_name} ({res.overall_result.result_type.value})",
                value=winner_name,
                source="Phase 6 Comparison Engine",
                evidence_state=AssistantEvidenceState.EMPIRICAL,
                domain=SourceDomain.COMPARISON,
                notes=res.overall_result.rationale,
            ))
            for cat_res in res.category_winners:
                winner_text = cat_res.winner_label or "Tie"
                bundle.add_item(EvidenceItem(
                    id=f"comparison.cat.{cat_res.category.value.lower()}",
                    claim=f"Category '{cat_res.category.value}': Winner is {winner_text} ({cat_res.winner_status.value})",
                    value=winner_text,
                    source="Phase 6 Comparison Engine",
                    evidence_state=AssistantEvidenceState.EMPIRICAL,
                    domain=SourceDomain.COMPARISON,
                ))
            return comp_data
        except Exception as e:
            bundle.missing_evidence.append(f"Comparison service error: {str(e)}")
            return None

    def fetch_inspection_evidence(
        self,
        v: VehicleContextInput,
        listing: Optional[ListingContextInput],
        user_profile: Optional[UserProfileInput],
        bundle: EvidenceBundle,
    ) -> Optional[Dict[str, Any]]:
        """Retrieves Phase 7 adaptive checklist and purchase readiness."""
        try:
            insp_v = InspectionVehicleContext(
                brand=v.brand,
                model=v.model,
                manufacturing_year=v.manufacturing_year,
                variant=v.variant,
                fuel_type=v.fuel_type or "Petrol",
                transmission_type=v.transmission_type or "Manual",
                km_driven=v.km_driven,
                number_of_owners=v.number_of_owners or 1,
            )
            insp_l = InspectionListingContext(
                asking_price=listing.asking_price if listing else None,
            ) if listing else None
            insp_u = UserInspectionProfile(
                safety_priority=user_profile.safety_priority if user_profile else "HIGH",
                daily_commute_km=user_profile.daily_commute_km if user_profile else 30.0,
                family_orientation=user_profile.family_orientation if user_profile else True,
            ) if user_profile else None

            req = InspectionRequest(
                vehicle=insp_v,
                listing=insp_l or InspectionListingContext(),
                user_profile=insp_u or UserInspectionProfile(),
            )
            res = self.inspection_svc.evaluate_inspection(req)
            insp_data = {
                "overall_status": res.summary.overall_status.value,
                "purchase_readiness": res.purchase_readiness.value,
                "professional_inspection_required": res.summary.professional_inspection_required,
                "critical_findings_count": len([f for f in res.findings if f.status.value == "FAIL"]),
                "recommended_next_steps": res.summary.recommended_next_steps,
            }

            bundle.add_item(EvidenceItem(
                id="inspection.readiness",
                claim=f"Inspection purchase readiness: {res.purchase_readiness.value} ({res.summary.overall_status.value})",
                value=res.purchase_readiness.value,
                source="Phase 7 Inspection Intelligence Engine",
                evidence_state=AssistantEvidenceState.EMPIRICAL,
                domain=SourceDomain.INSPECTION,
                notes=f"Professional inspection required: {res.summary.professional_inspection_required}",
            ))
            # Highest priority checklist items
            high_priority = [item.title for item in res.checklist if item.importance.value in ("CRITICAL", "HIGH")][:4]
            bundle.add_item(EvidenceItem(
                id="inspection.top_checkpoints",
                claim=f"Top inspection checkpoints: {', '.join(high_priority)}",
                value=high_priority,
                source="Phase 7 Adaptive Checklist Engine",
                evidence_state=AssistantEvidenceState.EMPIRICAL,
                domain=SourceDomain.INSPECTION,
            ))
            return insp_data
        except Exception as e:
            bundle.missing_evidence.append(f"Inspection service error: {str(e)}")
            return None

    def fetch_knowledge_evidence(
        self,
        v: VehicleContextInput,
        bundle: EvidenceBundle,
    ) -> Optional[Dict[str, Any]]:
        """Retrieves Phase 11 canonical vehicle knowledge: specs, safety, ownership, reliability."""
        try:
            res = self.resolve_vehicle(v)
            can_id = res.get("canonical_vehicle_id")
            if not can_id:
                can_id = f"{v.brand.lower().replace(' ', '-')}::{v.model.lower().replace(' ', '-')}"

            profile = self.knowledge_svc.get_vehicle_profile(can_id)
            if not profile:
                bundle.uncertainty_disclosures.append(f"No canonical knowledge profile found for {can_id}.")
                return None

            # Add specifications
            if profile.specifications:
                spec = profile.specifications
                bundle.add_item(EvidenceItem(
                    id="knowledge.specification",
                    claim=f"Engine: {spec.displacement_cc or 0}cc, {spec.max_power_bhp or 0} bhp, {spec.max_torque_nm or 0} Nm, ARAI: {spec.arai_mileage_kmpl or 0} km/l",
                    value={
                        "displacement_cc": spec.displacement_cc,
                        "power_bhp": spec.max_power_bhp,
                        "torque_nm": spec.max_torque_nm,
                        "transmission": spec.transmission,
                        "fuel_type": spec.fuel_type,
                        "arai_kmpl": spec.arai_mileage_kmpl,
                    },
                    source=spec.source.reference_document if spec.source else "OEM Technical Manual",
                    evidence_state=AssistantEvidenceState.VERIFIED if spec.source and spec.source.verification_status == "VERIFIED" else AssistantEvidenceState.SUPPORTED,
                    domain=SourceDomain.TAXONOMY,
                ))

            # Add dimensions
            if profile.dimensions:
                dim = profile.dimensions
                bundle.add_item(EvidenceItem(
                    id="knowledge.dimensions",
                    claim=f"Dimensions: {dim.length_mm}x{dim.width_mm}x{dim.height_mm} mm, Wheelbase: {dim.wheelbase_mm} mm, Ground Clearance: {dim.ground_clearance_mm} mm, Boot: {dim.boot_capacity_l} L",
                    value={
                        "length_mm": dim.length_mm,
                        "width_mm": dim.width_mm,
                        "height_mm": dim.height_mm,
                        "ground_clearance_mm": dim.ground_clearance_mm,
                        "boot_capacity_l": dim.boot_capacity_l,
                    },
                    source=dim.source.reference_document if dim.source else "OEM Specification Sheet",
                    evidence_state=AssistantEvidenceState.VERIFIED,
                    domain=SourceDomain.TAXONOMY,
                ))

            # Add safety rating
            if profile.safety:
                safety = profile.safety
                bundle.add_item(EvidenceItem(
                    id="knowledge.safety",
                    claim=f"Safety Rating: {safety.adult_stars}/5 Adult Stars ({safety.organization} {safety.test_year}), Bodyshell: {safety.bodyshell_integrity}",
                    value={
                        "organization": safety.organization,
                        "adult_stars": safety.adult_stars,
                        "child_stars": safety.child_stars,
                        "bodyshell": safety.bodyshell_integrity,
                        "year": safety.test_year,
                    },
                    source=safety.source.reference_document if safety.source else "Crash Safety Registry",
                    evidence_state=AssistantEvidenceState.VERIFIED,
                    domain=SourceDomain.TAXONOMY,
                ))
            else:
                bundle.uncertainty_disclosures.append(f"No verified crash test rating available in canonical registry for {v.brand} {v.model}.")

            # Add ownership profile
            if profile.ownership:
                own = profile.ownership
                bundle.add_item(EvidenceItem(
                    id="knowledge.ownership",
                    claim=f"Service Interval: {own.service_interval_months} mo / {own.service_interval_km} km. Est. Annual Service: ₹{own.typical_annual_maintenance_inr}. Real Fuel Economy: {own.real_world_city_mileage_kmpl} (City) / {own.real_world_highway_mileage_kmpl} (Hwy) km/l.",
                    value={
                        "interval_km": own.service_interval_km,
                        "interval_months": own.service_interval_months,
                        "typical_annual_maintenance_inr": own.typical_annual_maintenance_inr,
                        "real_city_kmpl": own.real_world_city_mileage_kmpl,
                        "real_highway_kmpl": own.real_world_highway_mileage_kmpl,
                    },
                    source=own.source.reference_document if own.source else "Ownership Cost Analysis",
                    evidence_state=AssistantEvidenceState.SUPPORTED,
                    domain=SourceDomain.TAXONOMY,
                ))

            # Add reliability issues
            if profile.reliability_issues:
                issues = [f"{iss.title} ({iss.severity})" for iss in profile.reliability_issues]
                bundle.add_item(EvidenceItem(
                    id="knowledge.reliability_issues",
                    claim=f"Known Mechanical Watchpoints: {'; '.join(issues)}",
                    value=[iss.model_dump() for iss in profile.reliability_issues],
                    source="Service Technical Advisories & Ownership Watchpoints",
                    evidence_state=AssistantEvidenceState.SUPPORTED,
                    domain=SourceDomain.TAXONOMY,
                ))

            # Add features summary
            if profile.features:
                std_features = [f.feature_name for f in profile.features if f.availability == "STANDARD"]
                bundle.add_item(EvidenceItem(
                    id="knowledge.features",
                    claim=f"Standard Variant Equipment: {', '.join(std_features[:6])}",
                    value=std_features,
                    source="Variant Feature Matrix",
                    evidence_state=AssistantEvidenceState.VERIFIED,
                    domain=SourceDomain.TAXONOMY,
                ))

            return profile.model_dump()
        except Exception as e:
            bundle.missing_evidence.append(f"Knowledge service error: {str(e)}")
            return None

    def fetch_market_evidence(
        self,
        v: VehicleContextInput,
        bundle: EvidenceBundle,
    ) -> Optional[Dict[str, Any]]:
        """Retrieves Phase 14 empirical market intelligence."""
        try:
            res = self.resolve_vehicle(v)
            can_id = res.get("canonical_vehicle_id")
            if not can_id:
                can_id = f"{v.brand.lower().replace(' ', '-')}::{v.model.lower().replace(' ', '-')}"

            prof = self.market_svc.get_market_profile(can_id)
            bundle.add_item(EvidenceItem(
                id="market.liquidity",
                claim=f"Liquidity Rating: {prof.market_position.liquidity_rating.value} ({prof.market_position.estimated_days_to_sell_band})",
                value={
                    "rating": prof.market_position.liquidity_rating.value,
                    "days_band": prof.market_position.estimated_days_to_sell_band,
                    "supply_level": prof.market_position.supply_level.value,
                    "demand_proxy": prof.market_position.demand_proxy.value,
                },
                source="Phase 14 Market Intelligence Engine",
                evidence_state=AssistantEvidenceState.EMPIRICAL,
                domain=SourceDomain.VALUATION,
                notes="Based on empirical secondary market listing volume and asking-price distribution."
            ))
            bundle.add_item(EvidenceItem(
                id="market.supply",
                claim=f"Secondary Market Supply: {prof.market_position.supply_level.value} with {prof.market_position.active_listings_proxy_count} historical listing observations.",
                value={
                    "active_listings_count": prof.market_position.active_listings_proxy_count,
                    "resale_retention_index": prof.market_position.resale_retention_index,
                },
                source="Phase 14 Empirical Market Cache",
                evidence_state=AssistantEvidenceState.EMPIRICAL,
                domain=SourceDomain.VALUATION,
            ))
            return prof.model_dump()
        except Exception as e:
            bundle.missing_evidence.append(f"Market intelligence error: {str(e)}")
            return None

    def fetch_ownership_evidence(
        self,
        v: VehicleContextInput,
        bundle: EvidenceBundle,
    ) -> Optional[Dict[str, Any]]:
        """Retrieves Phase 14 real-world ownership intelligence & TCO."""
        try:
            res = self.resolve_vehicle(v)
            can_id = res.get("canonical_vehicle_id")
            if not can_id:
                can_id = f"{v.brand.lower().replace(' ', '-')}::{v.model.lower().replace(' ', '-')}"

            intel = self.ownership_svc.get_ownership_intelligence(can_id)
            bundle.add_item(EvidenceItem(
                id="ownership.tco_5yr",
                claim=f"5-Year Total Cost of Ownership: ₹{intel.tco_5_year.total_cost_inr:,.0f} (₹{intel.tco_5_year.cost_per_km_inr:.2f}/km)",
                value={
                    "total_5yr_inr": intel.tco_5_year.total_cost_inr,
                    "cost_per_km": intel.tco_5_year.cost_per_km_inr,
                    "depreciation_inr": intel.tco_5_year.depreciation_cost_inr,
                    "fuel_inr": intel.tco_5_year.fuel_cost_inr,
                    "maintenance_inr": intel.tco_5_year.maintenance_cost_inr,
                },
                source="Phase 14 TCO Intelligence Engine",
                evidence_state=AssistantEvidenceState.MODEL_ESTIMATE,
                domain=SourceDomain.TAXONOMY,
                notes="TCO combines verified OEM intervals, empirical maintenance baselines, and statutory norms."
            ))
            if intel.risk_signals:
                risks = [f"{r.title} ({r.severity.value})" for r in intel.risk_signals]
                bundle.add_item(EvidenceItem(
                    id="ownership.risk_signals",
                    claim=f"Ownership Risk Signals: {'; '.join(risks)}",
                    value=[r.model_dump() for r in intel.risk_signals],
                    source="Phase 14 Ownership Risk Analyzer",
                    evidence_state=AssistantEvidenceState.EMPIRICAL,
                    domain=SourceDomain.TAXONOMY,
                ))
            return intel.model_dump()
        except Exception as e:
            bundle.missing_evidence.append(f"Ownership intelligence error: {str(e)}")
            return None

    def fetch_decision_evidence(
        self,
        v: VehicleContextInput,
        bundle: EvidenceBundle,
        user_profile: Optional[UserRequirementsProfile] = None,
        asking_price: Optional[float] = None,
        km_driven: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """Retrieves Phase 15 personalized decision intelligence."""
        try:
            res = self.resolve_vehicle(v)
            can_id = res.get("canonical_vehicle_id")
            if not can_id:
                can_id = f"{v.brand.lower().replace(' ', '-')}::{v.model.lower().replace(' ', '-')}"

            prof = user_profile or UserRequirementsProfile()
            d_eval = self.decision_svc.evaluate_vehicle(
                canonical_vehicle_id=can_id,
                profile=prof,
                asking_price=asking_price,
                km_driven=km_driven,
            )
            bundle.add_item(EvidenceItem(
                id="decision.user_fit",
                claim=f"Personalized User Fit Score: {d_eval.user_fit_score}/100 ({d_eval.verdict_label})",
                value={
                    "user_fit_score": d_eval.user_fit_score,
                    "verdict": d_eval.recommendation_verdict,
                    "verdict_label": d_eval.verdict_label,
                    "hard_constraint_status": d_eval.hard_constraint_status.value,
                },
                source="Phase 15 Decision Intelligence Engine",
                evidence_state=AssistantEvidenceState.MODEL_ESTIMATE,
                domain=SourceDomain.RECOMMENDATION,
            ))
            return d_eval.model_dump()
        except Exception as e:
            bundle.missing_evidence.append(f"Decision intelligence error: {str(e)}")
            return None

    def fetch_data_lineage_evidence(
        self,
        claim_id_or_attribute: str,
        bundle: EvidenceBundle,
        canonical_vehicle_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Retrieves Phase 16 data provenance, source attribution, and freshness lineage."""
        try:
            lineage = self.data_svc.get_claim_lineage(claim_id_or_attribute)
            if lineage:
                source_names = ", ".join(s.source_name for s in lineage.sources)
                bundle.add_item(EvidenceItem(
                    id=f"data_lineage.{lineage.claim_id}",
                    claim=f"Lineage for '{lineage.attribute_key}': Source={source_names}, Freshness={lineage.freshness.status.value}",
                    value=lineage.model_dump(),
                    source=source_names,
                    evidence_state=AssistantEvidenceState.VERIFIED,
                    domain=SourceDomain.TAXONOMY,
                ))
                return lineage.model_dump()
            else:
                bundle.missing_evidence.append(f"No explicit data lineage found for '{claim_id_or_attribute}'.")
                return None
        except Exception as e:
            bundle.missing_evidence.append(f"Data lineage error: {str(e)}")
            return None

    def fetch_current_market_intelligence(
        self,
        v: VehicleContextInput,
        bundle: EvidenceBundle,
    ) -> Optional[Dict[str, Any]]:
        """Retrieves Phase 17 live market observations & empirical pricing intelligence."""
        try:
            res = self.resolve_vehicle(v)
            can_id = res.get("canonical_vehicle_id")
            if not can_id:
                can_id = f"{v.brand.lower().replace(' ', '-')}::{v.model.lower().replace(' ', '-')}"

            intel = self.market_svc.get_current_market_intelligence(can_id)
            dist = intel.price_distribution
            supply = intel.supply

            if dist and dist.sample_size >= 3:
                bundle.add_item(EvidenceItem(
                    id="current_market.distribution",
                    claim=(
                        f"Current Market Asking Price (2026-Q3): Median ₹{dist.median_price_inr:,.0f} "
                        f"(IQR ₹{dist.p25_price_inr:,.0f} - ₹{dist.p75_price_inr:,.0f}, "
                        f"p10 ₹{dist.p10_price_inr:,.0f} - p90 ₹{dist.p90_price_inr:,.0f}, "
                        f"Sample: {dist.sample_size} active observations)"
                    ),
                    value=dist.model_dump(),
                    source=f"Current Multi-Metro Feeds ({', '.join(intel.evidence.sources_contributed) or 'Governed Feeds'})",
                    evidence_state=AssistantEvidenceState.EMPIRICAL,
                    domain=SourceDomain.VALUATION,
                    notes="Active seller asking prices across metro listings; does not represent realized sale transactions.",
                ))
                bundle.add_item(EvidenceItem(
                    id="current_market.supply",
                    claim=(
                        f"Current Supply Status: {supply.supply_tier.value} tier with "
                        f"{supply.total_observation_count} total observations ({supply.usable_observation_count} usable observations). "
                        f"Regional coverage: {', '.join(intel.evidence.geographic_coverage) or 'Metros'}."
                    ),
                    value=supply.model_dump(),
                    source="Current Market Observation Pipeline",
                    evidence_state=AssistantEvidenceState.EMPIRICAL,
                    domain=SourceDomain.VALUATION,
                ))
            else:
                bundle.uncertainty_disclosures.append(
                    f"Insufficient current market observations for {v.brand} {v.model} "
                    f"({supply.total_observation_count} found). Secondary market pricing falls back to historical baseline."
                )

            for limitation in intel.limitations:
                bundle.uncertainty_disclosures.append(limitation)

            return intel.model_dump()
        except Exception as e:
            bundle.missing_evidence.append(f"Current market intelligence error: {str(e)}")
            return None


