"""
CARspective — Phase 8 Controlled Domain Tool & Service Dispatcher
Coordinates calls to authoritative domain services and constructs structured EvidenceBundles.
Strictly read-only; guarantees zero silent recalculations or model mutations.
"""

from typing import Optional, List, Dict, Any
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


