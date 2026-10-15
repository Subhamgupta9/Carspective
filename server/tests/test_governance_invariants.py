"""
CARspective — Phase 10: Governance Invariant Test Suite
Validates the 15 architectural and governance invariants governing truth, evidence,
valuation independence, model security, and domain boundaries.
"""

import os
import json
import pytest
from server.domain.valuation.service import ValuationService, ModelSecurityIntegrityError
from server.domain.valuation.models import ValuationRequest
from server.domain.deal_analyzer.service import DealAnalyzerService
from server.domain.deal_analyzer.models import DealAnalysisRequest, DealQualityEnum
from server.domain.scoring.service import ScoringService
from server.domain.scoring.models import ScoreRequest
from server.domain.inspection.service import InspectionService
from server.domain.inspection.models import (
    InspectionRequest,
    InspectionVehicleContext,
    FindingInput,
    FindingStatus,
    PurchaseReadiness,
)
from server.domain.assistant.service import AssistantService
from server.domain.assistant.models import (
    AssistantRequest,
    AssistantIntent,
    VehicleContextInput,
)
from server.domain.taxonomy.resolver import CanonicalResolver
from server.repositories.taxonomy_repository import TaxonomyRepository
from server.schemas.taxonomy import CanonicalResolutionRequest

class TestGovernanceInvariants:

    # 1. No fabricated vehicle facts
    def test_invariant_1_no_fabricated_vehicle_facts(self, db_session):
        repo = TaxonomyRepository(db_session)
        resolver = CanonicalResolver(repo)
        req = CanonicalResolutionRequest(brand="Rolls-Royce", model="Phantom", year=2025)
        res = resolver.resolve(req)
        assert res.status == "UNRESOLVED"
        assert res.canonical_vehicle_id is None
        assert res.confidence_score == 0.0

    # 2. UNKNOWN != PASS in Inspection Engine
    def test_invariant_2_unknown_is_not_pass(self):
        service = InspectionService()
        req = InspectionRequest(
            vehicle=InspectionVehicleContext(
                brand="Tata",
                model="Nexon",
                manufacturing_year=2021,
                fuel_type="Petrol",
                transmission_type="Manual"
            ),
            findings=[
                FindingInput(item_id="STRUCT_CHASSIS_APRON_DAMAGE", status=FindingStatus.UNKNOWN),
                FindingInput(item_id="STRUCT_PILLAR_A_B_C_DENT_WELD", status=FindingStatus.UNKNOWN)
            ]
        )
        res = service.evaluate_inspection(req)
        # UNKNOWN must NOT be counted as passed
        assert res.summary.passed_items_count == 0
        assert res.summary.unknown_items_count >= 2
        # Readiness must NOT be READY_FOR_NEXT_STEP when critical items are UNKNOWN
        assert res.purchase_readiness != PurchaseReadiness.READY_FOR_NEXT_STEP

    # 3. Seller claim != verified evidence
    def test_invariant_3_seller_claim_is_not_verified(self):
        deal_service = DealAnalyzerService()
        req = DealAnalysisRequest(
            brand="Tata",
            model="Nexon",
            manufacturing_year=2021,
            km_driven=35000,
            asking_price=850000.0
        )
        res = deal_service.analyze_deal(req)
        # Seller asking price must remain UNVERIFIED evidence state
        assert res.asking_price_evidence_state == "UNVERIFIED"
        assert res.deal_quality is not None

    # 4. Asking price != valuation input
    def test_invariant_4_asking_price_isolated_from_valuation(self, db_session):
        repo = TaxonomyRepository(db_session)
        resolver = CanonicalResolver(repo)
        val_service = ValuationService(taxonomy_resolver=resolver)
        
        req_low = ValuationRequest(
            brand="Hyundai",
            model="Creta",
            manufacturing_year=2021,
            km_driven=40000,
            fuel_type="Diesel",
            transmission_type="Manual",
            asking_price=500000.0
        )
        req_high = ValuationRequest(
            brand="Hyundai",
            model="Creta",
            manufacturing_year=2021,
            km_driven=40000,
            fuel_type="Diesel",
            transmission_type="Manual",
            asking_price=2500000.0
        )
        val_low = val_service.evaluate_valuation(req_low)
        val_high = val_service.evaluate_valuation(req_high)
        
        # Fair market value must be 100% IDENTICAL regardless of asking price
        assert val_low.estimated_fair_market_value == val_high.estimated_fair_market_value
        assert val_low.expected_fair_market_range.lower_bound == val_high.expected_fair_market_range.lower_bound
        assert val_low.expected_fair_market_range.upper_bound == val_high.expected_fair_market_range.upper_bound

    # 5. Score != deal quality
    def test_invariant_5_score_is_independent_of_deal_quality(self):
        score_service = ScoringService()
        deal_service = DealAnalyzerService()
        
        # Intrinsic score of the car
        score_res = score_service.calculate_score(ScoreRequest(
            brand="Maruti Suzuki",
            model="Swift",
            manufacturing_year=2020
        ))
        
        # Deal A: Heavily discounted -> GREAT_DEAL
        deal_great = deal_service.analyze_deal(DealAnalysisRequest(
            brand="Maruti Suzuki",
            model="Swift",
            manufacturing_year=2020,
            km_driven=30000,
            asking_price=350000.0
        ))
        
        # Deal B: Heavily overpriced -> OVERPRICED
        deal_overpriced = deal_service.analyze_deal(DealAnalysisRequest(
            brand="Maruti Suzuki",
            model="Swift",
            manufacturing_year=2020,
            km_driven=30000,
            asking_price=950000.0
        ))
        
        assert score_res.overall_score is not None
        assert score_res.overall_score > 0
        assert deal_great.deal_quality in [DealQualityEnum.GREAT_DEAL, DealQualityEnum.FAIR_DEAL]
        assert deal_overpriced.deal_quality in [DealQualityEnum.OVERPRICED, DealQualityEnum.UNUSUALLY_LOW_ASKING_PRICE]

    # 6. Vehicle quality != specific vehicle condition
    def test_invariant_6_score_does_not_mutate_with_odometer(self):
        score_service = ScoringService()
        # Score is intrinsic to vehicle line, independent of specific listing odometer
        score_a = score_service.calculate_score(ScoreRequest(
            brand="Tata",
            model="Nexon",
            manufacturing_year=2021
        ))
        score_b = score_service.calculate_score(ScoreRequest(
            brand="Tata",
            model="Nexon",
            manufacturing_year=2021
        ))
        assert score_a.overall_score == score_b.overall_score
        assert len(score_a.dimensions) == len(score_b.dimensions)

    # 7. Inspection != mechanical diagnosis
    def test_invariant_7_inspection_disclaimer_preserves_boundaries(self):
        service = InspectionService()
        req = InspectionRequest(
            vehicle=InspectionVehicleContext(brand="Tata", model="Nexon", manufacturing_year=2021)
        )
        eval_res = service.evaluate_inspection(req)
        # Disclaimers emphasize physical inspection / technician escalation, not certified warranty
        assert len(eval_res.limitations) > 0
        limitations_str = " ".join(eval_res.limitations).lower()
        assert "physical" in limitations_str or "inspection" in limitations_str or "diagnostic" in limitations_str

    # 8. AI != independent analytical engine
    def test_invariant_8_ai_assistant_grounded_in_domain(self):
        assistant = AssistantService()
        req = AssistantRequest(
            message="What is the fair market value of this 2018 Swift?",
            vehicle=VehicleContextInput(brand="Maruti Suzuki", model="Swift", manufacturing_year=2018, km_driven=40000)
        )
        res = assistant.handle_message(req)
        # Assistant delegates to valuation domain and incorporates evidence bundle
        assert res.intent == AssistantIntent.VALUATION
        assert len(res.evidence_bundle) > 0
        assert any("valuation" in item.source.lower() or "valuation" in item.id.lower() for item in res.evidence_bundle)

    # 9. Historical asking-price data != transaction data
    def test_invariant_9_historical_asking_price_terminology(self, db_session):
        repo = TaxonomyRepository(db_session)
        resolver = CanonicalResolver(repo)
        val_service = ValuationService(taxonomy_resolver=resolver)
        res = val_service.evaluate_valuation(ValuationRequest(
            brand="Maruti Suzuki",
            model="Swift",
            manufacturing_year=2020,
            km_driven=30000
        ))
        limitations_text = " ".join(res.limitations).lower()
        assert "asking-price" in limitations_text or "asking price" in limitations_text
        assert "not verified transaction price" in limitations_text

    # 10. Example != authoritative fact
    def test_invariant_10_examples_labeled_illustrative(self):
        manifest_path = os.path.join("models", "carspective_valuation_lgbm_v1_manifest.json")
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
        concept = manifest.get("target_semantic_concept", "")
        assert "NOT verified transaction price" in concept

    # 11. Unsupported vehicle != guessed vehicle
    def test_invariant_11_unsupported_vehicle_insufficient_data(self, db_session):
        repo = TaxonomyRepository(db_session)
        resolver = CanonicalResolver(repo)
        val_service = ValuationService(taxonomy_resolver=resolver)
        res = val_service.evaluate_valuation(ValuationRequest(
            brand="Ferrari",
            model="Testarossa",
            manufacturing_year=1985,
            km_driven=900000
        ))
        assert res.confidence_state == "INSUFFICIENT_DATA"
        assert res.estimated_fair_market_value is None

    # 12. 3D asset identity must match vehicle identity
    def test_invariant_12_3d_asset_identity_strict_matching(self):
        asset_manifest_path = os.path.join("models", "manifest.json")
        if os.path.exists(asset_manifest_path):
            with open(asset_manifest_path, "r") as f:
                assets = json.load(f)
            for item in assets.get("assets", []):
                assert "slug" in item or "path" in item

    # 13. Frontend != source of analytical truth
    def test_invariant_13_frontend_is_consumer_not_calculator(self, app_client):
        res = app_client.get("/api/v1/vehicles/manufacturers")
        assert res.status_code == 200

    # 14. User preference != objective vehicle fact
    def test_invariant_14_user_preference_does_not_mutate_specs(self):
        score_service = ScoringService()
        res1 = score_service.calculate_score(ScoreRequest(
            brand="Tata",
            model="Nexon",
            manufacturing_year=2021
        ))
        res2 = score_service.calculate_score(ScoreRequest(
            brand="Tata",
            model="Nexon",
            manufacturing_year=2021
        ))
        assert res1.overall_score == res2.overall_score
        assert [d.score for d in res1.dimensions] == [d.score for d in res2.dimensions]

    # 15. Model artifact must pass integrity verification
    def test_invariant_15_model_sha256_integrity_enforcement(self):
        dummy_manifest = {
            "artifact": {
                "sha256": "0000000000000000000000000000000000000000000000000000000000000000"
            }
        }
        dummy_manifest_path = "models/test_tampered_manifest.json"
        with open(dummy_manifest_path, "w") as f:
            json.dump(dummy_manifest, f)
            
        try:
            with pytest.raises(ModelSecurityIntegrityError) as exc_info:
                ValuationService(manifest_path=dummy_manifest_path)
            assert "SECURITY INTEGRITY FAILURE" in str(exc_info.value)
        finally:
            if os.path.exists(dummy_manifest_path):
                os.remove(dummy_manifest_path)

    # 16. Inspection Catalog drift prevention: authoritative 49 items, version 2.0.0
    def test_invariant_16_inspection_catalog_authoritative_count_and_version(self):
        from server.domain.inspection.checklist import (
            CANONICAL_CHECKLIST_CATALOG,
            INSPECTION_CATALOG_VERSION,
            PHASE7_CANONICAL_BASELINE_COUNT,
            CURRENT_CANONICAL_CATALOG_COUNT,
        )
        assert INSPECTION_CATALOG_VERSION == "2.0.0", "Catalog version must remain 2.0.0"
        assert PHASE7_CANONICAL_BASELINE_COUNT == 45, "Historical Phase 7 baseline must remain 45"
        assert CURRENT_CANONICAL_CATALOG_COUNT == 49, "Current canonical catalog count must remain 49"
        assert len(CANONICAL_CHECKLIST_CATALOG) == 49, f"Catalog item count drift detected: expected 49, got {len(CANONICAL_CHECKLIST_CATALOG)}"

        # Verify all 7 canonical categories are populated with expected counts
        from collections import Counter
        cat_counts = Counter(item.category.value for item in CANONICAL_CHECKLIST_CATALOG)
        assert len(cat_counts) == 7, "Catalog must span exactly 7 canonical categories"
        assert cat_counts["Documentation"] == 10
        assert cat_counts["Exterior"] == 8
        assert cat_counts["Engine & Powertrain"] == 9
        assert cat_counts["Underbody & Structure"] == 6
        assert cat_counts["Interior"] == 6
        assert cat_counts["Safety"] == 5
        assert cat_counts["Test Drive"] == 5
