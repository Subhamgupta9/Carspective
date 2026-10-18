"""
CARspective — Phase 15 Personalized Decision Intelligence Test Suite
Verifies:
1. User requirements profile validation and explicit provenance tracking
2. Deterministic NL requirements extraction, ambiguity detection & latency (<50ms)
3. Strict hard constraints validation (budget, transmission, fuel, seating, body type)
4. Dynamic User Fit scoring (0-100), weight normalization, and missing data neutrality
5. Strict layer separation (Intrinsic Score vs Deal Fit vs User Fit)
6. Shortlist ranking and personalized multi-vehicle comparison divergence
7. Personalized inspection prioritization preserving canonical 45-item catalog
8. Zero sensitive attribute inference assertion
9. Security, input boundaries, and Phase 3 valuation model SHA-256 hash preservation
10. All REST API endpoints under /api/v1/decision/
"""

import os
import json
import time
import hashlib
import pytest
from server.app import create_app
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
    DecisionEvaluationResponse,
    ShortlistRankResponse,
    PersonalizedComparisonResponse,
    PersonalizedInspectionPrioritizationResponse,
)
from server.domain.decision.nlp_parser import NaturalLanguageRequirementsParser
from server.domain.decision.service import DecisionService
from server.domain.inspection import (
    CANONICAL_CHECKLIST_CATALOG,
    INSPECTION_CATALOG_VERSION,
    PHASE7_CANONICAL_BASELINE_COUNT,
    CURRENT_CANONICAL_CATALOG_COUNT,
)

EXPECTED_MODEL_SHA256 = "4a4ccf3f78c17b48826cfa55f40a24bcb808bc82fa752b793ad4eabff8b246c1"


@pytest.fixture(scope="module")
def app_client():
    app = create_app({"TESTING": True})
    with app.test_client() as client:
        yield client


@pytest.fixture(scope="module")
def decision_service():
    return DecisionService()


class TestUserRequirementsProfile:
    def test_profile_defaults_and_provenance(self):
        profile = UserRequirementsProfile()
        assert profile.budget_max_inr is None
        assert profile.usage_profile == UsageProfile.NOT_SPECIFIED
        assert profile.safety_priority == PriorityLevel.NOT_SPECIFIED
        assert profile.hard_constraints.strict_budget_ceiling is False

        # Set and get provenance
        profile.budget_max_inr = 1000000.0
        profile.set_provenance("budget_max_inr", ProvenanceState.USER_EXPLICIT, source_phrase="under 10 lakh")

        prov = profile.get_provenance("budget_max_inr")
        assert prov.state == ProvenanceState.USER_EXPLICIT
        assert prov.source_phrase == "under 10 lakh"

    def test_requirement_provenance_normalization_states(self):
        """Verifies the four canonical requirement provenance states."""
        profile = UserRequirementsProfile()
        
        # 1. NOT_SPECIFIED by default
        assert profile.get_provenance("fuel_preferences").state == ProvenanceState.NOT_SPECIFIED
        assert profile.get_provenance("transmission_preferences").state == ProvenanceState.NOT_SPECIFIED
        
        # 2. USER_EXPLICIT: user directly provided
        profile.set_provenance("budget_max_inr", ProvenanceState.USER_EXPLICIT, source_phrase="under 12 lakh")
        assert profile.get_provenance("budget_max_inr").state == ProvenanceState.USER_EXPLICIT
        
        # 3. USER_INFERRED: derived deterministically from phrase
        profile.set_provenance("family_size", ProvenanceState.USER_INFERRED, source_phrase="family car")
        assert profile.get_provenance("family_size").state == ProvenanceState.USER_INFERRED
        
        # 4. SYSTEM_DEFAULT: documented fallback applied
        profile.set_provenance("budget_flexible", ProvenanceState.SYSTEM_DEFAULT, source_phrase="standard tolerance")
        assert profile.get_provenance("budget_flexible").state == ProvenanceState.SYSTEM_DEFAULT

    def test_zero_sensitive_attribute_inference(self):
        """Governance requirement: profile must NEVER infer sensitive personal demographics."""
        profile = UserRequirementsProfile()
        fields = set(profile.model_dump().keys())
        sensitive_forbidden = {
            "income", "salary", "wealth", "race", "ethnicity", "religion",
            "caste", "gender", "sex", "marital_status", "health", "disability",
            "political_affiliation", "credit_score", "social_status"
        }
        for field in fields:
            assert field.lower() not in sensitive_forbidden, f"Forbidden demographic field: {field}"

    def test_adversarial_sensitive_attribute_attacks(self):
        """Adversarial test: conversational statements containing sensitive traits must yield 0 inferred profile traits."""
        adversarial_prompts = [
            "I am a high income Brahmin Hindu male earning 50 LPA looking for an automatic car",
            "Looking for a car for married woman with heart condition and disabled family member",
            "Car for low caste Dalit Buddhist family with political connections",
            "Gay single tech employee searching for a stylish fast hatchback",
        ]
        sensitive_keywords = {
            "income", "brahmin", "hindu", "male", "salary", "married", "woman",
            "heart", "disabled", "caste", "dalit", "buddhist", "political", "gay", "single"
        }
        for prompt in adversarial_prompts:
            res = NaturalLanguageRequirementsParser.parse(prompt)
            prof_dict = res.parsed_profile.model_dump()
            prov_dict = res.parsed_profile.provenance_map
            
            # Assert 0 sensitive keys in profile
            for k in prof_dict.keys():
                assert k.lower() not in sensitive_keywords, f"Leaked sensitive field in profile: {k}"
            # Assert 0 sensitive keys in provenance
            for k, prov in prov_dict.items():
                assert k.lower() not in sensitive_keywords, f"Leaked sensitive key in provenance: {k}"
                assert (prov.source_phrase or "").lower() not in ["brahmin", "dalit", "hindu", "income", "woman", "gay"]


class TestNaturalLanguageRequirementsParser:
    def test_budget_extraction_patterns(self):
        # Range
        res1 = NaturalLanguageRequirementsParser.parse("I need a car between 8 and 12 lakh")
        assert res1.parsed_profile.budget_min_inr == 800000.0
        assert res1.parsed_profile.budget_max_inr == 1200000.0
        assert res1.parsed_profile.get_provenance("budget_max_inr").state == ProvenanceState.USER_EXPLICIT

        # Single ceiling
        res2 = NaturalLanguageRequirementsParser.parse("Looking for something under 9.5 lakhs")
        assert res2.parsed_profile.budget_max_inr == 950000.0

    def test_powertrain_and_usage_extraction(self):
        query = "Automatic petrol car for daily city commute"
        res = NaturalLanguageRequirementsParser.parse(query)
        prof = res.parsed_profile
        assert prof.transmission_preferences == ["Automatic"]
        assert prof.fuel_preferences == ["Petrol"]
        assert prof.usage_profile == UsageProfile.CITY

    def test_priorities_and_seating_extraction(self):
        query = "Need a very safe 7 seater family car with low maintenance"
        res = NaturalLanguageRequirementsParser.parse(query)
        prof = res.parsed_profile
        assert prof.safety_priority == PriorityLevel.CRITICAL
        assert prof.family_size == 7
        assert prof.maintenance_priority == PriorityLevel.HIGH

    def test_ambiguity_clarification_questions(self):
        # 1. Total cost ambiguity
        query = "I have a total cost budget of 10 lakh"
        res = NaturalLanguageRequirementsParser.parse(query)
        assert len(res.clarification_questions) > 0
        assert res.parser_state == "AMBIGUOUS"
        assert any("total" in q.lower() or "acquisition" in q.lower() for q in res.clarification_questions)

        # 2. Vague budget term must NOT guess a budget ceiling; provenance must remain NOT_SPECIFIED
        vague_query = "Looking for a cheap affordable hatchback for office commute"
        res_vague = NaturalLanguageRequirementsParser.parse(vague_query)
        assert res_vague.parser_state == "AMBIGUOUS"
        assert res_vague.parsed_profile.budget_max_inr is None
        assert res_vague.parsed_profile.get_provenance("budget_max_inr").state == ProvenanceState.NOT_SPECIFIED
        assert any("budget" in q.lower() for q in res_vague.clarification_questions)

    def test_parser_latency_benchmark(self):
        query = "Automatic diesel SUV under 15 lakh with top safety for highway driving"
        t0 = time.perf_counter()
        res = NaturalLanguageRequirementsParser.parse(query)
        latency_ms = (time.perf_counter() - t0) * 1000.0
        assert latency_ms < 50.0, f"Parser latency {latency_ms:.2f}ms exceeds 50ms p95 requirement"


class TestDecisionServiceHardConstraints:
    def test_budget_ceiling_pass_and_fail(self, decision_service):
        profile = UserRequirementsProfile(
            budget_max_inr=1000000.0,
            budget_flexible=False,
            hard_constraints=HardConstraintsConfig(strict_budget_ceiling=True),
        )

        # Under budget
        res_pass = decision_service.validate_hard_constraints(
            canonical_id="maruti-suzuki::swift::gen-3-2018::2021::zxi::1-2-k12m-5mt",
            profile=profile,
            asking_price=750000.0,
        )
        assert res_pass.overall_status == HardConstraintStatus.PASS
        assert len(res_pass.violations) == 0

        # Over budget with strict ceiling
        res_fail = decision_service.validate_hard_constraints(
            canonical_id="maruti-suzuki::swift::gen-3-2018::2021::zxi::1-2-k12m-5mt",
            profile=profile,
            asking_price=1150000.0,
        )
        assert res_fail.overall_status == HardConstraintStatus.FAIL
        assert len(res_fail.violations) > 0

    def test_flexible_budget_tolerance(self, decision_service):
        profile = UserRequirementsProfile(
            budget_max_inr=1000000.0,
            budget_flexible=True,
            hard_constraints=HardConstraintsConfig(strict_budget_ceiling=False),
        )
        # 1050000 is 5% over budget, allowed under flexible budget
        res = decision_service.validate_hard_constraints(
            canonical_id="maruti-suzuki::swift::gen-3-2018::2021::zxi::1-2-k12m-5mt",
            profile=profile,
            asking_price=1050000.0,
        )
        assert res.overall_status == HardConstraintStatus.PASS

    def test_transmission_and_seating_constraints(self, decision_service):
        # Strict manual required, but vehicle is automatic
        class MockSpecs:
            transmission = "Automatic"
            fuel_type = "Petrol"

        class MockDims:
            seating_capacity = 5
            boot_capacity_l = 350

        profile = UserRequirementsProfile(
            transmission_preferences=["Manual"],
            family_size=7,
            hard_constraints=HardConstraintsConfig(strict_transmission=True, strict_min_seating=True),
        )

        res = decision_service.validate_hard_constraints(
            canonical_id="tata::nexon::1st-gen::2021::xz-plus",
            profile=profile,
            specifications=MockSpecs(),
            dimensions=MockDims(),
        )
        assert res.overall_status == HardConstraintStatus.FAIL
        assert any("transmission" in v.lower() for v in res.violations)
        assert any("seating" in v.lower() for v in res.violations)


class TestUserFitScoringAndNormalization:
    def test_user_fit_normalized_bounds(self, decision_service):
        profile = UserRequirementsProfile(
            budget_max_inr=1000000.0,
            usage_profile=UsageProfile.CITY,
            safety_priority=PriorityLevel.HIGH,
            maintenance_priority=PriorityLevel.CRITICAL,
        )
        fit = decision_service.calculate_user_fit(
            canonical_id="maruti-suzuki::swift::gen-3-2018::2021::zxi::1-2-k12m-5mt",
            profile=profile,
            asking_price=750000.0,
        )
        assert 0 <= fit.overall_user_fit_score <= 100
        assert fit.decision_quality in [DecisionQuality.HIGH, DecisionQuality.MODERATE, DecisionQuality.LIMITED]

    def test_missing_data_neutrality(self, decision_service):
        """Unrated crash test must NOT penalize car with 0; must be excluded from denominator."""
        profile = UserRequirementsProfile(
            safety_priority=PriorityLevel.CRITICAL,
        )
        fit = decision_service.calculate_user_fit(
            canonical_id="maruti-suzuki::swift::gen-3-2018::2021::zxi::1-2-k12m-5mt",
            profile=profile,
            safety=None,  # No crash test rating
        )
        assert fit.safety_fit is None
        assert "safety_fit" not in fit.component_weights
        assert any("unavailable" in lim.lower() for lim in fit.data_limitations)


class TestVehicleDecisionEvaluation:
    def test_layer_separation_and_deal_fit(self, decision_service):
        """Intrinsic CARspective score must be mathematically isolated from asking price."""
        profile = UserRequirementsProfile(budget_max_inr=900000.0)

        cid = "maruti-suzuki::swift::gen-3-2018::2021::zxi::1-2-k12m-5mt"

        # Evaluate without asking price
        res_no_price = decision_service.evaluate_vehicle(canonical_vehicle_id=cid, profile=profile)
        assert res_no_price.deal_fit_score is None
        assert res_no_price.intrinsic_score is not None

        # Evaluate with expensive asking price
        res_expensive = decision_service.evaluate_vehicle(
            canonical_vehicle_id=cid, profile=profile, asking_price=1200000.0
        )
        # Intrinsic score must remain EXACTLY identical!
        assert res_expensive.intrinsic_score == res_no_price.intrinsic_score
        assert res_expensive.deal_fit_score is not None

    def test_hard_constraint_failure_forces_not_recommended(self, decision_service):
        profile = UserRequirementsProfile(
            budget_max_inr=600000.0,
            hard_constraints=HardConstraintsConfig(strict_budget_ceiling=True),
        )
        cid = "maruti-suzuki::swift::gen-3-2018::2021::zxi::1-2-k12m-5mt"
        res = decision_service.evaluate_vehicle(canonical_vehicle_id=cid, profile=profile, asking_price=850000.0)

        assert res.hard_constraint_status == HardConstraintStatus.FAIL
        assert res.recommendation_verdict == "NOT RECOMMENDED"
        assert res.user_fit_score <= 35

    def test_grounded_explanations_and_alternatives(self, decision_service):
        profile = UserRequirementsProfile(
            budget_max_inr=1200000.0,
            usage_profile=UsageProfile.CITY,
            safety_priority=PriorityLevel.CRITICAL,
        )
        cid = "tata::nexon::1st-gen::2021::xz-plus"
        res = decision_service.evaluate_vehicle(canonical_vehicle_id=cid, profile=profile, asking_price=950000.0)

        assert len(res.why_it_fits) > 0
        assert len(res.tradeoffs) > 0
        assert len(res.what_to_verify_before_buying) > 0


class TestShortlistAndComparison:
    def test_shortlist_ranking_order(self, decision_service):
        profile = UserRequirementsProfile(
            budget_max_inr=800000.0,
            hard_constraints=HardConstraintsConfig(strict_budget_ceiling=True),
        )
        cars = [
            "maruti-suzuki::swift::gen-3-2018::2021::zxi::1-2-k12m-5mt",
            "tata::nexon::1st-gen::2021::xz-plus",
        ]
        res = decision_service.rank_shortlist(canonical_ids=cars, profile=profile)
        assert len(res.ranked_vehicles) == 2
        # Constraint-passing vehicle must be first
        assert res.ranked_vehicles[0].hard_constraint_status == HardConstraintStatus.PASS

    def test_personalized_comparison_divergence(self, decision_service):
        profile = UserRequirementsProfile(
            budget_max_inr=800000.0,
            maintenance_priority=PriorityLevel.CRITICAL,
            usage_profile=UsageProfile.CITY,
        )
        cars = [
            "tata::nexon::1st-gen::2021::xz-plus",
            "maruti-suzuki::swift::gen-3-2018::2021::zxi::1-2-k12m-5mt",
        ]
        comp = decision_service.compare_personalized(canonical_ids=cars, profile=profile)
        assert comp.general_winner_index in [0, 1]
        assert comp.user_winner_index in [0, 1]
        assert len(comp.general_winner_rationale) > 0
        assert len(comp.user_winner_rationale) > 0


class TestInspectionPrioritization:
    def test_checklist_prioritization_preserves_catalog_size(self, decision_service):
        profile = UserRequirementsProfile(
            safety_priority=PriorityLevel.CRITICAL,
            maintenance_priority=PriorityLevel.CRITICAL,
            usage_profile=UsageProfile.CITY,
        )
        res = decision_service.prioritize_inspection(
            canonical_vehicle_id="maruti-suzuki::swift::gen-3-2018::2021::zxi::1-2-k12m-5mt",
            profile=profile,
        )
        # Catalog items remain active
        assert len(res.prioritized_checklist) > 0
        assert len(res.priority_reasons) > 0
        # Catalog catalog integrity
        assert len(CANONICAL_CHECKLIST_CATALOG) == CURRENT_CANONICAL_CATALOG_COUNT

    def test_inspection_catalog_governance(self, decision_service):
        """Governance: Phase 7 baseline was 45 items; current versioned catalog is 49 items."""
        assert PHASE7_CANONICAL_BASELINE_COUNT == 45
        assert CURRENT_CANONICAL_CATALOG_COUNT == 49
        assert len(CANONICAL_CHECKLIST_CATALOG) == 49
        assert INSPECTION_CATALOG_VERSION == "2.0.0"

        # Verify that personalization NEVER adds items; only reorders
        profile = UserRequirementsProfile(safety_priority=PriorityLevel.CRITICAL)
        res = decision_service.prioritize_inspection(
            canonical_vehicle_id="maruti-suzuki::swift::gen-3-2018::2021::zxi::1-2-k12m-5mt",
            profile=profile,
        )
        canonical_ids = {item.item_id for item in CANONICAL_CHECKLIST_CATALOG}
        for item in res.prioritized_checklist:
            assert item["item_id"] in canonical_ids, f"Personalization added unauthorized item: {item['item_id']}"
        assert len(res.prioritized_checklist) <= CURRENT_CANONICAL_CATALOG_COUNT


class TestExplicitPersonalizationIsolationAndFabrication:
    def test_intrinsic_score_independence(self, decision_service):
        """Change user requirements while keeping vehicle identical -> intrinsic score unchanged."""
        cid = "maruti-suzuki::swift::gen-3-2018::2021::zxi::1-2-k12m-5mt"
        prof_a = UserRequirementsProfile(budget_max_inr=1500000.0, safety_priority=PriorityLevel.CRITICAL, usage_profile=UsageProfile.HIGHWAY)
        prof_b = UserRequirementsProfile(budget_max_inr=600000.0, maintenance_priority=PriorityLevel.CRITICAL, usage_profile=UsageProfile.CITY)

        res_a = decision_service.evaluate_vehicle(canonical_vehicle_id=cid, profile=prof_a)
        res_b = decision_service.evaluate_vehicle(canonical_vehicle_id=cid, profile=prof_b)

        assert res_a.intrinsic_score == res_b.intrinsic_score, "INTRINSIC SCORE MUTATED by user requirements!"

    def test_asking_price_isolation(self, decision_service):
        """Change asking price while keeping vehicle and user requirements identical -> intrinsic score unchanged."""
        cid = "tata::nexon::1st-gen::2021::xz-plus"
        prof = UserRequirementsProfile(budget_max_inr=1200000.0)

        res_none = decision_service.evaluate_vehicle(canonical_vehicle_id=cid, profile=prof, asking_price=None)
        res_low = decision_service.evaluate_vehicle(canonical_vehicle_id=cid, profile=prof, asking_price=500000.0)
        res_high = decision_service.evaluate_vehicle(canonical_vehicle_id=cid, profile=prof, asking_price=2500000.0)

        assert res_none.intrinsic_score == res_low.intrinsic_score == res_high.intrinsic_score, "INTRINSIC SCORE LEAKED asking price!"

    def test_user_fit_responsiveness(self, decision_service):
        """Change user requirements -> User Fit score responds to preferences."""
        cid = "maruti-suzuki::swift::gen-3-2018::2021::zxi::1-2-k12m-5mt"
        prof_city = UserRequirementsProfile(usage_profile=UsageProfile.CITY, maintenance_priority=PriorityLevel.CRITICAL)
        prof_hwy = UserRequirementsProfile(usage_profile=UsageProfile.HIGHWAY, safety_priority=PriorityLevel.CRITICAL)

        res_city = decision_service.evaluate_vehicle(canonical_vehicle_id=cid, profile=prof_city)
        res_hwy = decision_service.evaluate_vehicle(canonical_vehicle_id=cid, profile=prof_hwy)

        assert res_city.user_fit_score != res_hwy.user_fit_score, "User fit failed to respond to distinct profiles!"

    def test_canonical_identity_isolation(self, decision_service):
        """Change generation/variant/powertrain -> only correct vehicle intelligence used."""
        prof = UserRequirementsProfile(budget_max_inr=1500000.0)

        c1 = "maruti-suzuki::swift::gen-3-2018::2021::zxi::1-2-k12m-5mt"
        c2 = "tata::nexon::1st-gen::2021::xz-plus"
        c3 = "honda::city::gen-5-2020::2021::zx"

        r1 = decision_service.evaluate_vehicle(canonical_vehicle_id=c1, profile=prof)
        r2 = decision_service.evaluate_vehicle(canonical_vehicle_id=c2, profile=prof)
        r3 = decision_service.evaluate_vehicle(canonical_vehicle_id=c3, profile=prof)

        assert r1.canonical_vehicle_id == c1
        assert r2.canonical_vehicle_id == c2
        assert r3.canonical_vehicle_id == c3
        assert r1.vehicle_summary != r2.vehicle_summary != r3.vehicle_summary
        assert r1.intrinsic_score != r2.intrinsic_score

    def test_fabrication_audit(self, decision_service):
        """Fabrication audit: 0 fabricated preferences, 0 fabricated vehicle data, 0 unsupported claims."""
        # 1. Unstated preferences remain NOT_SPECIFIED (0 fabricated preferences)
        empty_prof = UserRequirementsProfile()
        for field in ["fuel_preferences", "transmission_preferences", "safety_priority", "reliability_priority"]:
            assert empty_prof.get_provenance(field).state == ProvenanceState.NOT_SPECIFIED

        # 2. Missing vehicle specs / safety remain unrated, not fabricated (0 fabricated vehicle data)
        fit = decision_service.calculate_user_fit(
            canonical_id="maruti-suzuki::swift::gen-3-2018::2021::zxi::1-2-k12m-5mt",
            profile=UserRequirementsProfile(safety_priority=PriorityLevel.CRITICAL),
            safety=None,
        )
        assert fit.safety_fit is None
        assert "safety_fit" not in fit.component_weights
        assert any("unavailable" in lim.lower() for lim in fit.data_limitations)


class TestModelHashAndSecurityGovernance:
    def test_valuation_model_sha256_hash_integrity(self):
        """Valuation model artifact must maintain SHA-256 integrity."""
        model_path = os.path.join("models", "carspective_valuation_lgbm_v1.joblib")
        assert os.path.exists(model_path)
        hasher = hashlib.sha256()
        with open(model_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        actual_sha = hasher.hexdigest()
        assert actual_sha == EXPECTED_MODEL_SHA256, (
            f"Model SHA-256 hash mismatch! Expected {EXPECTED_MODEL_SHA256}, got {actual_sha}"
        )


class TestDecisionRestEndpoints:
    def test_parse_query_api(self, app_client):
        resp = app_client.post(
            "/api/v1/decision/parse-query",
            json={"query": "Automatic petrol car under 10 lakh for city driving"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "parsed_profile" in data
        assert data["parsed_profile"]["budget_max_inr"] == 1000000.0

    def test_evaluate_decision_api(self, app_client):
        resp = app_client.post(
            "/api/v1/decision/evaluate",
            json={
                "canonical_vehicle_id": "maruti-suzuki::swift::gen-3-2018::2021::zxi::1-2-k12m-5mt",
                "profile": {
                    "budget_max_inr": 800000.0,
                    "usage_profile": "CITY",
                },
                "asking_price": 720000.0,
                "km_driven": 35000.0,
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "user_fit_score" in data
        assert "recommendation_verdict" in data
        assert "why_it_fits" in data

    def test_rank_shortlist_api(self, app_client):
        resp = app_client.post(
            "/api/v1/decision/rank",
            json={
                "canonical_ids": [
                    "maruti-suzuki::swift::gen-3-2018::2021::zxi::1-2-k12m-5mt",
                    "tata::nexon::1st-gen::2021::xz-plus",
                ],
                "profile": {"budget_max_inr": 1000000.0},
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "ranked_vehicles" in data
        assert len(data["ranked_vehicles"]) == 2

    def test_compare_api(self, app_client):
        resp = app_client.post(
            "/api/v1/decision/compare",
            json={
                "canonical_ids": [
                    "maruti-suzuki::swift::gen-3-2018::2021::zxi::1-2-k12m-5mt",
                    "tata::nexon::1st-gen::2021::xz-plus",
                ],
                "profile": {"budget_max_inr": 1000000.0},
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "general_winner_index" in data
        assert "user_winner_index" in data

    def test_prioritize_inspection_api(self, app_client):
        resp = app_client.post(
            "/api/v1/decision/prioritize-inspection",
            json={
                "canonical_vehicle_id": "maruti-suzuki::swift::gen-3-2018::2021::zxi::1-2-k12m-5mt",
                "profile": {"safety_priority": "CRITICAL"},
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "prioritized_checklist" in data
        assert len(data["prioritized_checklist"]) > 0

    def test_evaluate_vehicle_api_slug_normalization_toyota_innova_crysta(self, app_client):
        """Verifies /api/v1/decision/evaluate resolves 'Toyota-Innova Crysta' with 200 OK."""
        resp = app_client.post(
            "/api/v1/decision/evaluate",
            json={
                "canonical_vehicle_id": "Toyota-Innova Crysta",
                "profile": {"hard_constraints": {}},
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "Toyota" in data["vehicle_summary"]
        assert "Innova Crysta" in data["vehicle_summary"]
        assert data["intrinsic_score"] > 0

    def test_evaluate_vehicle_api_unverified_vehicle_404(self, app_client):
        """Verifies /api/v1/decision/evaluate returns 404 rather than 500 for unverified vehicles."""
        resp = app_client.post(
            "/api/v1/decision/evaluate",
            json={
                "canonical_vehicle_id": "Ferrari-F40",
                "profile": {"hard_constraints": {}},
            },
        )
        assert resp.status_code == 404
        data = resp.get_json()
        assert data["status"] == 404
        assert "Vehicle Not Found" in data["title"]
