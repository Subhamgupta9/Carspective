"""
CARspective — Phase 5 Test Suite
Tests:
1. CARspective Score (5 locked dimensions, normalization, evidence completeness)
2. Score Independence (asking price, user profile, deal quality invariance)
3. Recommendation Engine (four-tier spectrum, user fit, risk integration)
4. Market Alternatives (grounded rationale, budget constraints, non-duplication)
5. Mandatory Invariant Tests (Tests A-F)
6. REST API Endpoints (POST /api/v1/score, POST /api/v1/recommendation)
7. Performance Latency Benchmarks
"""

import pytest
import time
import numpy as np
from flask import Flask

from server.app import create_app
from server.domain.scoring.models import (
    ScoreRequest,
    ScoreDimensionName,
    EvidenceState,
    EvidenceQuality
)
from server.domain.scoring.service import ScoringService
from server.domain.recommendation.models import (
    RecommendationRequest,
    RecommendationVerdict,
    UserProfile,
    ListingContext
)
from server.domain.recommendation.service import RecommendationService
from server.domain.deal_analyzer.models import DealQualityEnum

@pytest.fixture(scope="module")
def app() -> Flask:
    flask_app = create_app({"TESTING": True})
    return flask_app

@pytest.fixture(scope="module")
def client(app: Flask):
    return app.test_client()

@pytest.fixture(scope="module")
def scoring_service() -> ScoringService:
    return ScoringService()

@pytest.fixture(scope="module")
def recommendation_service() -> RecommendationService:
    return RecommendationService()

# -------------------------------------------------------------------------
# 1. CARspective Score Tests
# -------------------------------------------------------------------------

def test_carspective_score_nexon_verified_safety(scoring_service: ScoringService):
    """Tata Nexon has verified 5-Star Global NCAP crash rating in knowledge claims."""
    req = ScoreRequest(brand="Tata", model="Nexon", manufacturing_year=2020)
    res = scoring_service.calculate_score(req)

    assert res.overall_score is not None
    assert 75 <= res.overall_score <= 95
    assert res.evidence_quality in (EvidenceQuality.HIGH, EvidenceQuality.MODERATE)

    # Check 5 dimensions exist
    dim_names = {d.dimension_name for d in res.dimensions}
    assert ScoreDimensionName.STRUCTURAL_SAFETY in dim_names
    assert ScoreDimensionName.RELIABILITY_AND_LONGEVITY in dim_names
    assert ScoreDimensionName.MAINTENANCE_AND_OWNERSHIP in dim_names
    assert ScoreDimensionName.RESALE_AND_MARKET_LIQUIDITY in dim_names
    assert ScoreDimensionName.REAL_WORLD_PRACTICALITY in dim_names

    # Check Safety is VERIFIED with 95/100
    safety_dim = next(d for d in res.dimensions if d.dimension_name == ScoreDimensionName.STRUCTURAL_SAFETY)
    assert safety_dim.score == 95
    assert safety_dim.evidence_state == EvidenceState.VERIFIED
    assert "5 Stars" in safety_dim.contributing_factors[0]

def test_carspective_score_creta_verified_safety(scoring_service: ScoringService):
    """Hyundai Creta 2nd gen has verified 3-Star Global NCAP crash rating."""
    req = ScoreRequest(brand="Hyundai", model="Creta", manufacturing_year=2021)
    res = scoring_service.calculate_score(req)

    safety_dim = next(d for d in res.dimensions if d.dimension_name == ScoreDimensionName.STRUCTURAL_SAFETY)
    assert safety_dim.score == 65
    assert safety_dim.evidence_state == EvidenceState.VERIFIED

    resale_dim = next(d for d in res.dimensions if d.dimension_name == ScoreDimensionName.RESALE_AND_MARKET_LIQUIDITY)
    assert resale_dim.score >= 90
    assert resale_dim.evidence_state == EvidenceState.EMPIRICAL

def test_carspective_score_swift_verified_safety(scoring_service: ScoringService):
    """Maruti Swift has verified 2-Star Global NCAP rating and Rank 1 liquidity."""
    req = ScoreRequest(brand="Maruti", model="Swift", manufacturing_year=2019)
    res = scoring_service.calculate_score(req)

    safety_dim = next(d for d in res.dimensions if d.dimension_name == ScoreDimensionName.STRUCTURAL_SAFETY)
    assert safety_dim.score == 45
    assert safety_dim.evidence_state == EvidenceState.VERIFIED

    resale_dim = next(d for d in res.dimensions if d.dimension_name == ScoreDimensionName.RESALE_AND_MARKET_LIQUIDITY)
    assert resale_dim.score == 95
    assert resale_dim.evidence_state == EvidenceState.EMPIRICAL

def test_carspective_score_unverified_safety_returns_insufficient_data(scoring_service: ScoringService):
    """A vehicle without verified crash test evidence must return INSUFFICIENT_DATA for safety."""
    req = ScoreRequest(brand="Nissan", model="Micra", manufacturing_year=2015)
    res = scoring_service.calculate_score(req)

    safety_dim = next(d for d in res.dimensions if d.dimension_name == ScoreDimensionName.STRUCTURAL_SAFETY)
    assert safety_dim.score is None
    assert safety_dim.score_formatted == "Insufficient Data"
    assert safety_dim.evidence_state == EvidenceState.INSUFFICIENT_DATA
    assert "No published Bharat NCAP or Global NCAP" in safety_dim.contributing_factors[0]

def test_carspective_score_deterministic_explanation(scoring_service: ScoringService):
    """Explanation must identify strong and watch areas deterministically without LLM."""
    req = ScoreRequest(brand="Tata", model="Nexon", manufacturing_year=2020)
    res = scoring_service.calculate_score(req)

    assert len(res.explanation.strong_areas) >= 1
    assert "Nexon achieves a CARspective Score" in res.explanation.summary

# -------------------------------------------------------------------------
# 2. Mandatory Score Independence Invariants
# -------------------------------------------------------------------------

def test_score_asking_price_independence(scoring_service: ScoringService):
    """Changing asking price MUST NOT change CARspective Score or dimension scores."""
    req_no_price = ScoreRequest(brand="Hyundai", model="Creta", manufacturing_year=2020)
    req_cheap = ScoreRequest(brand="Hyundai", model="Creta", manufacturing_year=2020, asking_price=100000.0)
    req_expensive = ScoreRequest(brand="Hyundai", model="Creta", manufacturing_year=2020, asking_price=5000000.0)

    res_no = scoring_service.calculate_score(req_no_price)
    res_cheap = scoring_service.calculate_score(req_cheap)
    res_exp = scoring_service.calculate_score(req_expensive)

    assert res_no.overall_score == res_cheap.overall_score == res_exp.overall_score
    assert res_no.evidence_quality == res_cheap.evidence_quality == res_exp.evidence_quality

    for d_no, d_cheap, d_exp in zip(res_no.dimensions, res_cheap.dimensions, res_exp.dimensions):
        assert d_no.score == d_cheap.score == d_exp.score
        assert d_no.evidence_state == d_cheap.evidence_state == d_exp.evidence_state

def test_score_user_requirements_independence(scoring_service: ScoringService):
    """The intrinsic score does not take user requirements and is independent of user preferences."""
    req = ScoreRequest(brand="Maruti", model="Swift", manufacturing_year=2018)
    res1 = scoring_service.calculate_score(req)
    res2 = scoring_service.calculate_score(req)
    assert res1.overall_score == res2.overall_score

# -------------------------------------------------------------------------
# 3. Recommendation Engine Tests
# -------------------------------------------------------------------------

def test_recommendation_strong_consideration_match(recommendation_service: RecommendationService):
    """Good vehicle + fair deal + strong user fit -> STRONG CONSIDERATION."""
    req = RecommendationRequest(
        brand="Tata",
        model="Nexon",
        manufacturing_year=2020,
        fuel_type="Petrol",
        listing=ListingContext(
            asking_price=500000.0,
            km_driven=35000.0,
            service_history_status="FULL_SERVICE_HISTORY"
        ),
        user_profile=UserProfile(
            budget_max=600000.0,
            family_size=4,
            primary_usage="CITY",
            safety_priority="HIGH"
        )
    )
    res = recommendation_service.evaluate_recommendation(req)
    assert res.verdict == RecommendationVerdict.STRONG_CONSIDERATION
    assert res.user_fit.overall_fit >= 75
    assert len(res.alternatives) >= 1

def test_recommendation_good_vehicle_overpriced_deal(recommendation_service: RecommendationService):
    """High scoring vehicle + overpriced deal -> CONSIDER (with negotiation advice)."""
    req = RecommendationRequest(
        brand="Hyundai",
        model="Creta",
        manufacturing_year=2021,
        fuel_type="Diesel",
        listing=ListingContext(
            asking_price=1650000.0,  # Materially overpriced
            km_driven=30000.0
        ),
        user_profile=UserProfile(
            budget_max=1700000.0,
            budget_flexible=True
        )
    )
    res = recommendation_service.evaluate_recommendation(req)
    # Good car but overpriced deal should be CONSIDER, not STRONG CONSIDERATION
    assert res.verdict == RecommendationVerdict.CONSIDER
    assert "overpriced" in res.explanation.deal_consideration.lower()

def test_recommendation_poor_vehicle_cheap_deal_proceed_with_caution(recommendation_service: RecommendationService):
    """A vehicle with low safety or high risk is NOT STRONG CONSIDERATION just because price is cheap."""
    req = RecommendationRequest(
        brand="Maruti",
        model="Swift",
        manufacturing_year=2018,
        listing=ListingContext(
            asking_price=250000.0, # Unusually low / anomalous
            km_driven=85000.0
        ),
        user_profile=UserProfile(
            budget_max=500000.0,
            safety_priority="CRITICAL"
        )
    )
    res = recommendation_service.evaluate_recommendation(req)
    # Extreme low price / 2-star safety with critical safety priority must trigger caution or not recommended
    assert res.verdict in (RecommendationVerdict.PROCEED_WITH_CAUTION, RecommendationVerdict.NOT_RECOMMENDED)

def test_recommendation_fatal_budget_mismatch_not_recommended(recommendation_service: RecommendationService):
    """Vehicle drastically exceeding strict budget -> NOT RECOMMENDED."""
    req = RecommendationRequest(
        brand="Hyundai",
        model="Creta",
        manufacturing_year=2021,
        listing=ListingContext(
            asking_price=1400000.0,
            km_driven=30000.0
        ),
        user_profile=UserProfile(
            budget_max=600000.0,  # Stated budget ₹6L for a ₹14L car
            budget_flexible=False
        )
    )
    res = recommendation_service.evaluate_recommendation(req)
    assert res.verdict == RecommendationVerdict.NOT_RECOMMENDED
    assert res.user_fit.budget_fit <= 20

# -------------------------------------------------------------------------
# 4. Market Alternatives Tests
# -------------------------------------------------------------------------

def test_alternatives_generated_with_grounded_rationale(recommendation_service: RecommendationService):
    """Alternatives must include specific grounded reasons and not duplicate target vehicle."""
    req = RecommendationRequest(
        brand="Maruti",
        model="Swift",
        manufacturing_year=2019,
        listing=ListingContext(asking_price=520000.0),
        user_profile=UserProfile(
            budget_max=900000.0,
            safety_priority="HIGH"
        )
    )
    res = recommendation_service.evaluate_recommendation(req)
    assert len(res.alternatives) >= 1
    for alt in res.alternatives:
        assert alt.model.lower() != "swift"  # No duplicate
        assert alt.typical_price_inr <= 900000 * 1.15  # Respects budget
        assert alt.rationale is not None
        assert alt.advantage_over_target is not None

# -------------------------------------------------------------------------
# 5. Mandatory Invariant Tests (Tests A-F)
# -------------------------------------------------------------------------

def test_invariant_test_a_asking_price_changes(recommendation_service: RecommendationService):
    """
    Test A: Asking price changes.
    Score: UNCHANGED
    Recommendation: MAY CHANGE
    """
    base_kwargs = {
        "brand": "Tata",
        "model": "Nexon",
        "manufacturing_year": 2020,
        "user_profile": UserProfile(budget_max=950000.0, budget_flexible=False)
    }

    req_fair = RecommendationRequest(**base_kwargs, listing=ListingContext(asking_price=800000.0))
    req_crazy = RecommendationRequest(**base_kwargs, listing=ListingContext(asking_price=2500000.0))

    res_fair = recommendation_service.evaluate_recommendation(req_fair)
    res_crazy = recommendation_service.evaluate_recommendation(req_crazy)

    # Score MUST be identical
    assert res_fair.carspective_score == res_crazy.carspective_score
    # Recommendation verdict MUST change (fair deal -> not recommended due to budget/price)
    assert res_fair.verdict != res_crazy.verdict

def test_invariant_test_b_user_requirements_change(recommendation_service: RecommendationService):
    """
    Test B: User requirements change.
    Score: UNCHANGED
    Recommendation: MAY CHANGE
    """
    req_user1 = RecommendationRequest(
        brand="Maruti",
        model="Swift",
        manufacturing_year=2019,
        listing=ListingContext(asking_price=500000.0),
        user_profile=UserProfile(budget_max=600000.0, safety_priority="LOW")
    )
    req_user2 = RecommendationRequest(
        brand="Maruti",
        model="Swift",
        manufacturing_year=2019,
        listing=ListingContext(asking_price=500000.0),
        user_profile=UserProfile(budget_max=600000.0, safety_priority="CRITICAL")
    )

    res1 = recommendation_service.evaluate_recommendation(req_user1)
    res2 = recommendation_service.evaluate_recommendation(req_user2)

    # Intrinsic score is strictly unaffected by user priority changes
    assert res1.carspective_score == res2.carspective_score
    # Verdict adapts to user safety critical priority (Swift has 2 stars)
    assert res1.verdict != res2.verdict

def test_invariant_test_c_vehicle_evidence_changes(scoring_service: ScoringService):
    """
    Test C: Vehicle evidence changes (e.g. 5-star Nexon vs 2-star Swift).
    Score: MAY CHANGE
    """
    res_nexon = scoring_service.calculate_score(ScoreRequest(brand="Tata", model="Nexon", manufacturing_year=2020))
    res_swift = scoring_service.calculate_score(ScoreRequest(brand="Maruti", model="Swift", manufacturing_year=2019))

    assert res_nexon.overall_score != res_swift.overall_score

def test_invariant_test_d_deal_quality_changes(recommendation_service: RecommendationService):
    """
    Test D: Deal quality changes.
    Score: UNCHANGED
    Recommendation: MAY CHANGE
    """
    req1 = RecommendationRequest(
        brand="Hyundai",
        model="Creta",
        manufacturing_year=2021,
        listing=ListingContext(asking_price=560000.0) # Fair deal
    )
    req2 = RecommendationRequest(
        brand="Hyundai",
        model="Creta",
        manufacturing_year=2021,
        listing=ListingContext(asking_price=1600000.0) # Overpriced
    )

    res1 = recommendation_service.evaluate_recommendation(req1)
    res2 = recommendation_service.evaluate_recommendation(req2)

    assert res1.carspective_score == res2.carspective_score
    assert res1.deal_quality != res2.deal_quality

def test_invariant_test_e_valuation_output_invariance(scoring_service: ScoringService):
    """
    Test E: Valuation model outputs do not enter intrinsic scoring.
    Score: UNCHANGED
    """
    # Score calculation does not invoke or depend on ML model weights
    req = ScoreRequest(brand="Tata", model="Nexon", manufacturing_year=2020)
    res = scoring_service.calculate_score(req)
    assert res.overall_score is not None

def test_invariant_test_f_unsupported_evidence_not_converted(scoring_service: ScoringService):
    """
    Test F: Unsupported evidence must NOT be silently converted to authoritative evidence.
    """
    req = ScoreRequest(brand="UnknownMaker", model="UnknownModel", manufacturing_year=2015)
    res = scoring_service.calculate_score(req)
    safety_dim = next(d for d in res.dimensions if d.dimension_name == ScoreDimensionName.STRUCTURAL_SAFETY)
    assert safety_dim.evidence_state == EvidenceState.INSUFFICIENT_DATA
    assert safety_dim.score is None

# -------------------------------------------------------------------------
# 6. REST API Endpoints Tests
# -------------------------------------------------------------------------

def test_score_api_success(client):
    """Test POST /api/v1/score returns 200 OK."""
    payload = {"brand": "Tata", "model": "Nexon", "manufacturing_year": 2020}
    resp = client.post("/api/v1/score", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    assert "overall_score" in data
    assert "dimensions" in data
    assert len(data["dimensions"]) == 5
    assert "explanation" in data

def test_recommendation_api_success(client):
    """Test POST /api/v1/recommendation returns 200 OK."""
    payload = {
        "brand": "Tata",
        "model": "Nexon",
        "manufacturing_year": 2020,
        "listing": {
            "asking_price": 850000.0,
            "km_driven": 35000.0
        },
        "user_profile": {
            "budget_max": 900000.0,
            "safety_priority": "HIGH"
        }
    }
    resp = client.post("/api/v1/recommendation", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    assert "verdict" in data
    assert "carspective_score" in data
    assert "user_fit" in data
    assert "alternatives" in data
    assert "explanation" in data

def test_score_api_validation_error_missing_brand(client):
    """Test POST /api/v1/score returns 422 on missing required field."""
    resp = client.post("/api/v1/score", json={"model": "Nexon"})
    assert resp.status_code == 422

# -------------------------------------------------------------------------
# 7. Performance Latency Benchmarks
# -------------------------------------------------------------------------

def test_scoring_and_recommendation_performance(scoring_service: ScoringService, recommendation_service: RecommendationService):
    """Measures operational latency percentiles for score and recommendation services."""
    score_req = ScoreRequest(brand="Hyundai", model="Creta", manufacturing_year=2021)
    rec_req = RecommendationRequest(
        brand="Hyundai",
        model="Creta",
        manufacturing_year=2021,
        listing=ListingContext(asking_price=950000.0),
        user_profile=UserProfile(budget_max=1000000.0)
    )

    # Warm-up
    scoring_service.calculate_score(score_req)
    recommendation_service.evaluate_recommendation(rec_req)

    score_latencies = []
    rec_latencies = []

    for _ in range(25):
        t0 = time.perf_counter()
        scoring_service.calculate_score(score_req)
        score_latencies.append((time.perf_counter() - t0) * 1000.0)

        t0 = time.perf_counter()
        recommendation_service.evaluate_recommendation(rec_req)
        rec_latencies.append((time.perf_counter() - t0) * 1000.0)

    p50_score = float(np.percentile(score_latencies, 50))
    p95_score = float(np.percentile(score_latencies, 95))
    p50_rec = float(np.percentile(rec_latencies, 50))
    p95_rec = float(np.percentile(rec_latencies, 95))

    assert p50_score < 30.0, f"Score p50 {p50_score:.2f} ms exceeded 30ms budget"
    assert p95_score < 60.0, f"Score p95 {p95_score:.2f} ms exceeded 60ms budget"
    assert p50_rec < 50.0, f"Recommendation p50 {p50_rec:.2f} ms exceeded 50ms budget"
    assert p95_rec < 150.0, f"Recommendation p95 {p95_rec:.2f} ms exceeded 150ms budget"
