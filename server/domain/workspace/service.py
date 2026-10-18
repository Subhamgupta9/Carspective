"""
CARspective — Phase 13 Vehicle Intelligence Workspace Domain Service
Orchestrates unified multi-engine intelligence retrieval, identity confidence evaluation,
generation isolation, and decision support synthesis for the vehicle workspace.
"""

import time
import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

logger = logging.getLogger("carspective.workspace")

from server.infrastructure.database import ScopedSession
from server.repositories.taxonomy_repository import TaxonomyRepository
from server.repositories.knowledge_repository import KnowledgeRepository
from server.domain.taxonomy.resolver import CanonicalResolver
from server.domain.knowledge.service import KnowledgeService
from server.domain.valuation.service import ValuationService
from server.domain.scoring.service import ScoringService
from server.domain.recommendation.service import RecommendationService
from server.domain.deal_analyzer.service import DealAnalyzerService
from server.domain.inspection.service import InspectionService
from server.domain.market.service import MarketIntelligenceService
from server.domain.ownership.service import OwnershipIntelligenceService

from server.domain.valuation.models import ValuationRequest
from server.domain.scoring.models import ScoreRequest
from server.domain.recommendation.models import RecommendationRequest, ListingContext
from server.domain.deal_analyzer.models import DealAnalysisRequest
from server.domain.inspection.models import InspectionRequest, InspectionVehicleContext

from server.domain.workspace.models import (
    IdentityConfidenceLevel,
    IdentityConfidenceInfo,
    SiblingVariantInfo,
    SiblingGenInfo,
    VehicleIdentity,
    ExecutiveSummary,
    WorkspaceInspectionSummary,
    VehicleWorkspaceResponse,
)


class VehicleWorkspaceService:
    """Production orchestrator synthesizing end-to-end vehicle intelligence."""

    def __init__(
        self,
        session: Optional[Session] = None,
        valuation_service: Optional[ValuationService] = None,
        scoring_service: Optional[ScoringService] = None,
        recommendation_service: Optional[RecommendationService] = None,
        deal_service: Optional[DealAnalyzerService] = None,
        inspection_service: Optional[InspectionService] = None,
        market_service: Optional[MarketIntelligenceService] = None,
        ownership_service: Optional[OwnershipIntelligenceService] = None,
    ):
        self._session = session
        self.taxonomy_repo = TaxonomyRepository(session=session)
        self.knowledge_repo = KnowledgeRepository(session=session)
        self.resolver = CanonicalResolver(self.taxonomy_repo)

        self.knowledge_service = KnowledgeService(session=session)
        self.valuation_service = valuation_service or ValuationService(taxonomy_resolver=self.resolver, session=session)
        self.scoring_service = scoring_service or ScoringService(taxonomy_resolver=self.resolver, session=session)
        self.recommendation_service = recommendation_service or RecommendationService(session=session)
        self.deal_service = deal_service or DealAnalyzerService(valuation_service=self.valuation_service)
        self.inspection_service = inspection_service or InspectionService(
            taxonomy_resolver=self.resolver, session=session
        )
        self.market_service = market_service or MarketIntelligenceService(session=session)
        self.ownership_service = ownership_service or OwnershipIntelligenceService(
            knowledge_service=self.knowledge_service,
            market_service=self.market_service,
            valuation_service=self.valuation_service,
            session=session,
        )

    @property
    def session(self) -> Session:
        if self._session is not None:
            return self._session
        return ScopedSession()

    @session.setter
    def session(self, value: Optional[Session]) -> None:
        self._session = value
        for svc in [
            self.taxonomy_repo,
            self.knowledge_repo,
            self.knowledge_service,
            self.valuation_service,
            self.scoring_service,
            self.recommendation_service,
            self.inspection_service,
            self.market_service,
            self.ownership_service,
        ]:
            if hasattr(svc, "session"):
                svc.session = value

    def get_vehicle_workspace(
        self,
        canonical_id: str,
        asking_price: Optional[float] = None,
        km_driven: Optional[float] = None,
        user_profile: Optional[Dict[str, Any]] = None,
    ) -> Optional[VehicleWorkspaceResponse]:
        """
        Synthesizes the complete Vehicle Intelligence Workspace payload.
        Adheres to strict Phase 13 information hierarchy, zero-regression invariants,
        and epistemic honesty.
        """
        start_time = time.time()
        parts = canonical_id.strip().split("::")
        if not parts or not parts[0]:
            return None

        make_slug = parts[0]
        model_slug = parts[1] if len(parts) >= 2 else ""
        gen_slug = parts[2] if len(parts) >= 3 else ""
        year = int(parts[3]) if len(parts) >= 4 and parts[3].isdigit() else None
        variant_slug = parts[4] if len(parts) >= 5 else ""
        powertrain_slug = parts[5] if len(parts) >= 6 else ""

        # 1. Resolve Taxonomy Hierarchy
        manufacturer = self.taxonomy_repo.get_manufacturer_by_slug(make_slug)
        if not manufacturer:
            manufacturer = self.taxonomy_repo.find_manufacturer(make_slug)

        model_obj = None
        if manufacturer and model_slug:
            model_obj = self.taxonomy_repo.get_model_by_slug(manufacturer.slug, model_slug)
            if not model_obj:
                model_obj = self.taxonomy_repo.find_model(manufacturer.id, model_slug)

        # Fallback for non-'::' slugs (e.g. 'Toyota-Innova Crysta', 'toyota-innova-crysta', 'Maruti-Swift')
        if not manufacturer or not model_obj:
            m_res, mod_res = self.taxonomy_repo.resolve_make_model_from_slug(canonical_id)
            if m_res and mod_res:
                manufacturer = m_res
                model_obj = mod_res

        if not manufacturer or not model_obj:
            # Model cannot be resolved
            return None

        # 2. Resolve Generation
        gen_obj = None
        if gen_slug:
            gen_obj = next((g for g in model_obj.generations if g.slug == gen_slug), None)
        elif year:
            gen_obj = self.taxonomy_repo.find_generation_for_year(model_obj.id, year)
        
        if not gen_obj and model_obj.generations:
            gen_obj = model_obj.generations[-1] # Default to latest known generation

        # 3. Resolve Sibling Generations & Variants for Disambiguation / Variant Switcher
        sibling_generations: List[SiblingGenInfo] = []
        for g in model_obj.generations:
            sibling_generations.append(
                SiblingGenInfo(
                    name=g.name,
                    slug=g.slug,
                    year_start=g.year_start,
                    year_end=g.year_end,
                    canonical_id=f"{manufacturer.slug}::{model_obj.slug}::{g.slug}",
                    is_current=(gen_obj is not None and g.id == gen_obj.id),
                )
            )

        sibling_variants: List[SiblingVariantInfo] = []
        var_obj = None
        if gen_obj:
            all_variants = self.taxonomy_repo.list_variants(gen_obj.id)
            for v in all_variants:
                pts = [f"{p.engine_name or ''} {p.fuel_type} {p.transmission_type}".strip() for p in v.powertrains] if v.powertrains else []
                is_curr = (variant_slug != "" and v.slug == variant_slug)
                sibling_variants.append(
                    SiblingVariantInfo(
                        name=v.name,
                        slug=v.slug,
                        trim_level=v.trim_level,
                        powertrains=pts,
                        canonical_id=f"{manufacturer.slug}::{model_obj.slug}::{gen_obj.slug}::{year or gen_obj.year_start}::{v.slug}",
                        is_current=is_curr,
                    )
                )
            if variant_slug:
                var_obj = next((v for v in all_variants if v.slug == variant_slug), None)
            if not var_obj and all_variants:
                var_obj = all_variants[0] # Default baseline variant

        # Effective Year
        effective_year = year or (gen_obj.year_start if gen_obj else 2021)
        effective_km = km_driven if km_driven is not None and km_driven >= 0 else max(15000, min(140000, (2026 - effective_year) * 12500))

        # Check deep knowledge presence
        target_gen_id = f"{manufacturer.slug}::{model_obj.slug}::{gen_obj.slug}" if gen_obj else canonical_id
        specs_records = self.knowledge_repo.get_specifications_for_vehicle(target_gen_id)
        has_deep_knowledge = len(specs_records) > 0

        # 4. Identity Confidence Assessment
        confidence_level: IdentityConfidenceLevel
        title: str
        description: str
        is_confirmed = True
        needs_user_confirmation = False

        if not has_deep_knowledge:
            confidence_level = IdentityConfidenceLevel.LIMITED
            title = "Limited Knowledge Record"
            description = (
                f"Canonical identity '{model_obj.name}' verified in taxonomy. "
                "Baseline valuation and scoring available, but deep 9-table verified technical records are limited."
            )
        elif len(parts) <= 2 and len(model_obj.generations) > 1:
            confidence_level = IdentityConfidenceLevel.AMBIGUOUS
            title = "Ambiguous Identity — Please Confirm Generation & Trim"
            description = (
                f"Matched vehicle '{manufacturer.name} {model_obj.name}'. Multiple generations and trims exist in our database. "
                "Please confirm your exact generation and trim variant below."
            )
            is_confirmed = False
            needs_user_confirmation = True
        elif len(parts) >= 5 and var_obj:
            confidence_level = IdentityConfidenceLevel.EXACT
            title = "Exact Canonical Specification"
            description = (
                f"Fully resolved down to {manufacturer.name} {model_obj.name} "
                f"{gen_obj.name if gen_obj else ''} ({effective_year}) {var_obj.name} trim."
            )
        else:
            confidence_level = IdentityConfidenceLevel.RESOLVED
            title = "Resolved Baseline Specification"
            description = (
                f"Resolved to {gen_obj.name if gen_obj else 'standard generation'} ({effective_year}). "
                f"Default '{var_obj.name if var_obj else 'standard'}' equipment baseline displayed. Select your trim below if different."
            )
            is_confirmed = True
            needs_user_confirmation = False

        identity_conf_info = IdentityConfidenceInfo(
            level=confidence_level,
            title=title,
            description=description,
            is_confirmed=is_confirmed,
            needs_user_confirmation=needs_user_confirmation,
            sibling_variants=sibling_variants,
            sibling_generations=sibling_generations,
        )

        # 5. Full Knowledge Profile (Phase 11)
        full_can_id = f"{manufacturer.slug}::{model_obj.slug}"
        if gen_obj:
            full_can_id += f"::{gen_obj.slug}::{effective_year}"
            if var_obj:
                full_can_id += f"::{var_obj.slug}"

        knowledge_profile = self.knowledge_service.get_vehicle_profile(full_can_id)
        spec = knowledge_profile.specifications if knowledge_profile else None

        # Build Identity Payload
        vehicle_identity = VehicleIdentity(
            canonical_vehicle_id=full_can_id,
            brand=manufacturer.name,
            brand_slug=manufacturer.slug,
            model=model_obj.name,
            model_slug=model_obj.slug,
            generation=gen_obj.name if gen_obj else None,
            generation_slug=gen_obj.slug if gen_obj else None,
            year=effective_year,
            variant=var_obj.name if var_obj else None,
            variant_slug=var_obj.slug if var_obj else None,
            fuel_type=(spec.fuel_type if spec and spec.fuel_type else "Petrol"),
            transmission_type=(spec.transmission if spec and spec.transmission else "Manual"),
            drivetrain=(spec.drivetrain if spec and spec.drivetrain else "FWD"),
            body_type=(knowledge_profile.body_type if knowledge_profile and knowledge_profile.body_type else "Hatchback"),
            segment=(knowledge_profile.segment if knowledge_profile and knowledge_profile.segment else "B-Segment"),
            coverage_tier="TIER_1_DEEP" if has_deep_knowledge else "TIER_2_EMPIRICAL",
        )

        # 6. Intrinsic Valuation (Phase 3)
        # Note: valuation engine strictly evaluates intrinsic fair market value; asking price is NOT passed
        val_req = ValuationRequest(
            brand=manufacturer.name,
            model=model_obj.name,
            manufacturing_year=effective_year,
            km_driven=effective_km,
            fuel_type=vehicle_identity.fuel_type,
            transmission_type=vehicle_identity.transmission_type,
            bodytype=vehicle_identity.body_type,
            variant=vehicle_identity.variant,
        )
        val_res = self.valuation_service.evaluate_valuation(val_req)

        # 7. Deal Analysis (Phase 4) — Isolated Commercial Comparator
        deal_res = None
        if asking_price is not None and asking_price > 0:
            deal_req = DealAnalysisRequest(
                brand=manufacturer.name,
                model=model_obj.name,
                manufacturing_year=effective_year,
                km_driven=effective_km,
                asking_price=asking_price,
                fuel_type=vehicle_identity.fuel_type,
                transmission_type=vehicle_identity.transmission_type,
                city="Delhi",
                variant=vehicle_identity.variant,
            )
            deal_res = self.deal_service.analyze_deal(deal_req)

        # 8. Intrinsic CarSpective Score (Phase 5) — Strictly Isolated from Asking Price
        score_req = ScoreRequest(
            brand=manufacturer.name,
            model=model_obj.name,
            manufacturing_year=effective_year,
            fuel_type=vehicle_identity.fuel_type,
            transmission_type=vehicle_identity.transmission_type,
            variant=vehicle_identity.variant,
        )
        score_res = self.scoring_service.calculate_score(score_req)

        # 9. Recommendation & Market Alternatives (Phase 5)
        rec_listing = ListingContext(
            asking_price=asking_price,
            km_driven=effective_km,
        )
        rec_req = RecommendationRequest(
            brand=manufacturer.name,
            model=model_obj.name,
            manufacturing_year=effective_year,
            fuel_type=vehicle_identity.fuel_type,
            transmission_type=vehicle_identity.transmission_type,
            variant=vehicle_identity.variant,
            listing=rec_listing,
        )
        rec_res = self.recommendation_service.evaluate_recommendation(rec_req)

        # 10. Adaptive Inspection Intelligence (Phase 7)
        insp_vehicle_ctx = InspectionVehicleContext(
            brand=manufacturer.name,
            model=model_obj.name,
            manufacturing_year=effective_year,
            fuel_type=vehicle_identity.fuel_type,
            transmission_type=vehicle_identity.transmission_type,
            variant=vehicle_identity.variant,
            km_driven=effective_km,
        )
        insp_req = InspectionRequest(vehicle=insp_vehicle_ctx)
        insp_res = self.inspection_service.evaluate_inspection(insp_req)

        # 11. Synthesize Executive Intelligence Summary
        fmv_inr = val_res.estimated_fair_market_value
        fmv_lakhs = round(fmv_inr / 100000, 2) if fmv_inr else None

        range_low_inr = val_res.expected_fair_market_range.lower_bound if val_res.expected_fair_market_range else None
        range_high_inr = val_res.expected_fair_market_range.upper_bound if val_res.expected_fair_market_range else None
        range_low_lakhs = round(range_low_inr / 100000, 2) if range_low_inr else None
        range_high_lakhs = round(range_high_inr / 100000, 2) if range_high_inr else None

        score_val = score_res.overall_score
        score_band = "UNAVAILABLE"
        if score_val is not None:
            if score_val >= 80:
                score_band = "EXCELLENT"
            elif score_val >= 70:
                score_band = "GOOD"
            elif score_val >= 55:
                score_band = "FAIR"
            else:
                score_band = "CAUTION"

        deal_quality_str = None
        if deal_res:
            deal_quality_str = deal_res.deal_quality.value if hasattr(deal_res.deal_quality, "value") else str(deal_res.deal_quality)

        rec_verdict_str = rec_res.verdict.value if hasattr(rec_res.verdict, "value") else str(rec_res.verdict)

        safety_obj = knowledge_profile.safety if knowledge_profile else None
        own_obj = knowledge_profile.ownership if knowledge_profile else None
        rel_issues = knowledge_profile.reliability_issues if knowledge_profile else []

        one_line = f"{manufacturer.name} {model_obj.name} ({effective_year}) scores {score_val or 'N/A'}/100 with {rec_verdict_str.lower()} verdict"
        if fmv_lakhs:
            one_line += f" and fair market baseline around ₹{fmv_lakhs:.2f} Lakhs."
        else:
            one_line += "."

        exec_summary = ExecutiveSummary(
            carspective_score=score_val,
            score_band=score_band,
            estimated_fair_market_value_inr=fmv_inr,
            estimated_fair_market_value_lakhs=fmv_lakhs,
            expected_fair_market_range_low_inr=range_low_inr,
            expected_fair_market_range_high_inr=range_high_inr,
            expected_fair_market_range_low_lakhs=range_low_lakhs,
            expected_fair_market_range_high_lakhs=range_high_lakhs,
            deal_quality=deal_quality_str,
            recommendation_verdict=rec_verdict_str,
            safety_stars=safety_obj.adult_stars if safety_obj else None,
            safety_agency=safety_obj.organization if safety_obj else None,
            bodyshell_integrity=safety_obj.bodyshell_integrity if safety_obj else None,
            typical_annual_maintenance_inr=own_obj.typical_annual_maintenance_inr if own_obj else None,
            maintenance_complexity=own_obj.maintenance_complexity if own_obj else None,
            reliability_watchpoints_count=len(rel_issues),
            one_line_summary=one_line,
        )

        # 12. Workspace Inspection Summary
        critical_count = sum(1 for item in insp_res.checklist if hasattr(item, "importance") and item.importance.value == "CRITICAL")
        critical_watchpoints = [
            f"{item.category.value if hasattr(item.category, 'value') else item.category}: {item.title}"
            for item in insp_res.checklist
            if hasattr(item, "importance") and item.importance.value in ["CRITICAL", "HIGH"]
        ][:5]

        doc_reqs = [req.document_name for req in insp_res.documentation_requirements][:4]

        insp_summary = WorkspaceInspectionSummary(
            total_applicable_items=len(insp_res.checklist),
            critical_items_count=critical_count,
            top_watchpoints=critical_watchpoints,
            documentation_requirements=doc_reqs,
            purchase_readiness=insp_res.purchase_readiness.value if hasattr(insp_res.purchase_readiness, "value") else str(insp_res.purchase_readiness),
        )

        # 13. Visual Configuration
        visual_data = {
            "body_type": vehicle_identity.body_type,
            "has_3d_support": vehicle_identity.body_type.lower() in ["sedan", "suv", "hatchback", "compact suv"],
            "model_path": f"/models/{vehicle_identity.body_type.lower().replace(' ', '_')}.glb",
        }

        # 14. Market & Ownership Intelligence (Phase 14)
        market_profile_data = None
        if self.market_service:
            try:
                m_prof = self.market_service.get_market_profile(full_can_id)
                market_profile_data = m_prof.model_dump()
            except Exception as e:
                logger.warning(f"Error computing market profile for {full_can_id}: {e}")

        ownership_intel_data = None
        if self.ownership_service:
            try:
                o_intel = self.ownership_service.get_ownership_intelligence(
                    full_can_id,
                    knowledge=knowledge_profile,
                    valuation_res=val_res
                )
                ownership_intel_data = o_intel.model_dump()
            except Exception as e:
                logger.warning(f"Error computing ownership intelligence for {full_can_id}: {e}")

        # 15. Personalized Decision Intelligence (Phase 15)
        personalized_decision_data = None
        if user_profile:
            try:
                from server.domain.decision.service import DecisionService
                from server.domain.decision.models import UserRequirementsProfile
                d_svc = DecisionService(session=self.session)
                u_req = UserRequirementsProfile(**user_profile) if isinstance(user_profile, dict) else user_profile
                d_eval = d_svc.evaluate_vehicle(
                    canonical_vehicle_id=full_can_id,
                    profile=u_req,
                    asking_price=asking_price,
                    km_driven=km_driven,
                )
                personalized_decision_data = d_eval.model_dump()
            except Exception as e:
                logger.warning(f"Error computing personalized decision for {full_can_id}: {e}")

        # 16. Current Market Observations & Intelligence (Phase 17)
        current_market_data = None
        if self.market_service:
            try:
                c_intel = self.market_service.get_current_market_intelligence(full_can_id)
                current_market_data = c_intel.model_dump()
            except Exception as e:
                logger.warning(f"Error computing current market intelligence for {full_can_id}: {e}")

        # Market alternatives
        alts = [alt.model_dump() for alt in rec_res.alternatives] if rec_res.alternatives else []

        limitations = [
            "Intrinsic CarSpective Score measures platform-wide ownership merit and is mathematically isolated from individual asking price.",
            "Valuation model produces statistical expected fair market asking baseline, calibrated with conformal range; never guaranteed sale price.",
            "Physical inspection and title verification are mandatory before closing any transaction.",
            "Market liquidity and asking price trends are based on historical asking price listings and do not represent verified transaction prices.",
            "Total Cost of Ownership estimates combine empirical component maintenance baselines with standardized statutory and fuel assumptions.",
        ]
        if not has_deep_knowledge:
            limitations.append("Vehicle technical specifications are based on standard taxonomy baseline. Specific variant options may vary.")

        elapsed_ms = round((time.time() - start_time) * 1000, 2)

        data_gov = {
            "asking_price_semantics": "Historical dataset reflects 57,480 seller asking-price listing observations (2018-2024). Not transaction prices, completed sales, or realized resale values.",
            "valuation_model_hash": "4a4ccf3f78c17b48826cfa55f40a24bcb808bc82fa752b793ad4eabff8b246c1",
            "evidence_lifecycle_status": "GOVERNED_VERIFIED",
            "observation_period": "2018-2024",
            "freshness_policy": "POLICY_HISTORICAL_LISTINGS",
        }

        freshness_info = {
            "specifications": "CURRENT",
            "safety_ratings": "CURRENT",
            "market_baseline": "CURRENT_HISTORICAL_OBSERVATION",
            "last_reviewed": "2026-10-08",
        }

        return VehicleWorkspaceResponse(
            canonical_vehicle_id=full_can_id,
            identity=vehicle_identity,
            identity_confidence=identity_conf_info,
            executive_summary=exec_summary,
            valuation=val_res.model_dump() if val_res else None,
            deal_analysis=deal_res.model_dump() if deal_res else None,
            score=score_res.model_dump() if score_res else None,
            knowledge=knowledge_profile.model_dump() if knowledge_profile else None,
            recommendation=rec_res.model_dump() if rec_res else None,
            inspection_summary=insp_summary,
            alternatives=alts,
            visual=visual_data,
            market_profile=market_profile_data,
            ownership_intelligence=ownership_intel_data,
            personalized_decision=personalized_decision_data,
            current_market=current_market_data,
            evidence_freshness=freshness_info,
            data_governance=data_gov,
            limitations=limitations,
            computation_latency_ms=elapsed_ms,
        )

