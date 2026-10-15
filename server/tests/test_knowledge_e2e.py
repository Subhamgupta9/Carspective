"""
CARspective — Phase 11: Full End-to-End Analytical Chain Integration Test
Verifies the complete 10-stage intelligent chain:
Search -> Vehicle -> Knowledge -> Valuation -> Deal -> Score -> Recommendation -> Compare -> Inspection -> Assistant
"""

import pytest
from server.domain.knowledge.service import KnowledgeService
from server.domain.valuation.service import ValuationService
from server.domain.valuation.models import ValuationRequest
from server.domain.deal_analyzer.service import DealAnalyzerService
from server.domain.deal_analyzer.models import DealAnalysisRequest
from server.domain.scoring.service import ScoringService
from server.domain.scoring.models import ScoreRequest
from server.domain.recommendation.service import RecommendationService
from server.domain.recommendation.models import RecommendationRequest, ListingContext, UserProfile
from server.domain.comparison.service import ComparisonService
from server.domain.comparison.models import ComparisonRequest, ComparisonVehicle
from server.domain.inspection.service import InspectionService
from server.domain.inspection.models import InspectionRequest, InspectionVehicleContext, InspectionListingContext
from server.domain.assistant.service import AssistantService
from server.domain.assistant.models import AssistantRequest, VehicleContextInput, ListingContextInput


class TestKnowledgeEndToEndChain:

    def test_complete_10_stage_analytical_chain(self, db_session):
        """
        Executes and validates all 10 stages of the CARspective platform:
        1. Search
        2. Canonical Vehicle Identity
        3. Real Knowledge Intelligence
        4. Statistical Valuation
        5. Deal Analyzer
        6. CARspective Intrinsic Score
        7. Personalized Recommendation
        8. Multi-Vehicle Comparison
        9. Inspection Intelligence
        10. Grounded AI Assistant
        """

        # ── Stage 1: Search ──────────────────────────────────────────
        knowledge_svc = KnowledgeService(db_session)
        search_results = knowledge_svc.search_vehicles(query="Swift 2020", limit=5)
        assert len(search_results) > 0
        candidate = search_results[0]
        assert "canonical_vehicle_id" in candidate
        can_id = candidate["canonical_vehicle_id"]
        assert "swift" in can_id


        # ── Stage 2 & 3: Vehicle & Real Knowledge Intelligence ──────
        profile = knowledge_svc.get_vehicle_profile(can_id)
        assert profile is not None
        assert profile.make == "Maruti Suzuki"
        assert profile.model == "Swift"
        assert profile.specifications is not None
        assert profile.specifications.displacement_cc == 1197
        assert profile.safety is not None
        assert profile.safety.adult_stars == 2
        assert len(profile.features) > 0
        assert profile.ownership is not None
        assert len(profile.reliability_issues) > 0

        # ── Stage 4: Valuation Engine ────────────────────────────────
        val_svc = ValuationService()
        val_req = ValuationRequest(
            brand="Maruti",
            model="Swift",
            manufacturing_year=2020,
            km_driven=35000,
            fuel_type="Petrol",
            transmission_type="Manual",
            city="Delhi",
        )
        val_res = val_svc.evaluate_valuation(val_req)
        assert val_res.estimated_fair_market_value > 200000
        assert val_res.expected_fair_market_range.lower_bound < val_res.estimated_fair_market_value < val_res.expected_fair_market_range.upper_bound

        # ── Stage 5: Deal Analyzer ───────────────────────────────────
        deal_svc = DealAnalyzerService(valuation_service=val_svc)
        deal_req = DealAnalysisRequest(
            brand="Maruti",
            model="Swift",
            manufacturing_year=2020,
            km_driven=35000,
            asking_price=val_res.estimated_fair_market_value * 1.02, # 2% above market
            fuel_type="Petrol",
            transmission_type="Manual",
            city="Delhi",
        )
        deal_res = deal_svc.analyze_deal(deal_req)
        assert deal_res.deal_quality is not None
        assert deal_res.negotiation.target_price > 0

        # ── Stage 6: CARspective Score ──────────────────────────────
        score_svc = ScoringService(session=db_session)
        score_req = ScoreRequest(
            brand="Maruti",
            model="Swift",
            manufacturing_year=2020,
            fuel_type="Petrol",
            transmission_type="Manual",
        )
        score_res = score_svc.calculate_score(score_req)
        assert 0 <= score_res.overall_score <= 100
        assert len(score_res.dimensions) == 5

        # ── Stage 7: Recommendation Engine ──────────────────────────
        rec_svc = RecommendationService(session=db_session, scoring_service=score_svc)
        rec_req = RecommendationRequest(
            brand="Maruti",
            model="Swift",
            manufacturing_year=2020,
            fuel_type="Petrol",
            transmission_type="Manual",
            listing=ListingContext(asking_price=val_res.estimated_fair_market_value),
            user_profile=UserProfile(
                monthly_km=1200,
                safety_priority="MEDIUM",
                mileage_priority="HIGH",
            ),
        )
        rec_res = rec_svc.evaluate_recommendation(rec_req)
        assert rec_res.verdict is not None
        assert rec_res.user_fit is not None

        # ── Stage 8: Comparison Engine ──────────────────────────────
        comp_svc = ComparisonService(session=db_session, scoring_service=score_svc)
        comp_req = ComparisonRequest(
            vehicles=[
                ComparisonVehicle(brand="Maruti", model="Swift", manufacturing_year=2020),
                ComparisonVehicle(brand="Tata", model="Nexon", manufacturing_year=2021),
            ]
        )
        comp_res = comp_svc.compare(comp_req)
        assert len(comp_res.specifications) > 10
        assert comp_res.overall_result is not None

        # ── Stage 9: Inspection Intelligence ────────────────────────
        insp_svc = InspectionService(session=db_session)
        insp_req = InspectionRequest(
            vehicle=InspectionVehicleContext(
                brand="Maruti",
                model="Swift",
                manufacturing_year=2020,
                km_driven=35000,
                fuel_type="Petrol",
                transmission_type="Manual",
            ),
            listing=InspectionListingContext(asking_price=val_res.estimated_fair_market_value),
        )
        insp_res = insp_svc.evaluate_inspection(insp_req)
        assert len(insp_res.checklist) > 20
        assert insp_res.purchase_readiness is not None

        # ── Stage 10: Grounded AI Assistant ──────────────────────────
        assistant_svc = AssistantService()
        ast_req = AssistantRequest(
            message="What are the engine specs and known reliability watchpoints for this Swift?",
            vehicle=VehicleContextInput(brand="Maruti", model="Swift", manufacturing_year=2020),
            listing=ListingContextInput(asking_price=val_res.estimated_fair_market_value),
        )
        ast_res = assistant_svc.handle_message(ast_req)
        assert "1197" in ast_res.answer or "1,197" in ast_res.answer
        assert len(ast_res.evidence_refs) > 0
        assert len(ast_res.suggested_next_actions) > 0
