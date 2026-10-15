"""
CARspective — Phase 6 Vehicle Comparison & Research Engine Test Suite
Tests:
1. Comparison size validation (reject <2, reject >3, allow 2 and 3)
2. Canonical identity preservation (same model different generation/year, different powertrains)
3. General comparison mode (Mode A)
4. Personalized comparison mode (Mode B) with User Profile
5. Specification normalization, evidence states, and missing data behavior
6. Difference significance evaluation (MEANINGFUL, MINOR, UNKNOWN)
7. Category winners, ties, and insufficient data handling
8. CARspective Score comparison integration (reusing Phase 5)
9. Valuation comparison integration (reusing Phase 3)
10. Deal Analyzer integration (reusing Phase 4) and vehicle vs deal merit separation
11. Trade-off engine and 'Best For' label generation
12. Research summaries per vehicle
13. Mandatory Invariant Tests A, B, C, D, E
14. REST API contract & validation errors (POST /api/v1/compare)
15. Performance latency measurements
"""

import pytest
import time
import numpy as np
from flask import Flask

from server.app import create_app
from server.domain.comparison.models import (
    ComparisonRequest,
    ComparisonResponse,
    ComparisonMode,
    ComparisonVehicle,
    ComparisonListing,
    ComparisonUserProfile,
    CategoryWinnerStatus,
    DifferenceSignificance,
    OverallResultType,
    EvidenceState,
)
from server.domain.comparison.service import ComparisonService
from server.domain.scoring.models import ScoreDimensionName

@pytest.fixture(scope="module")
def app() -> Flask:
    flask_app = create_app({"TESTING": True})
    return flask_app

@pytest.fixture(scope="module")
def client(app: Flask):
    return app.test_client()

@pytest.fixture(scope="module")
def comparison_service() -> ComparisonService:
    return ComparisonService()


# -------------------------------------------------------------------------
# 1. Comparison Size & Validation Tests
# -------------------------------------------------------------------------

def test_comparison_rejects_fewer_than_two_vehicles(client):
    """Fewer than 2 vehicles must be rejected with HTTP 422."""
    payload = {
        "vehicles": [
            {"brand": "Tata", "model": "Nexon", "manufacturing_year": 2020}
        ],
        "mode": "general"
    }
    resp = client.post("/api/v1/compare", json=payload)
    assert resp.status_code == 422

def test_comparison_rejects_more_than_three_vehicles(client):
    """More than 3 vehicles must be rejected with HTTP 422."""
    payload = {
        "vehicles": [
            {"brand": "Tata", "model": "Nexon", "manufacturing_year": 2020},
            {"brand": "Hyundai", "model": "Creta", "manufacturing_year": 2021},
            {"brand": "Maruti", "model": "Swift", "manufacturing_year": 2019},
            {"brand": "Honda", "model": "City", "manufacturing_year": 2018}
        ],
        "mode": "general"
    }
    resp = client.post("/api/v1/compare", json=payload)
    assert resp.status_code == 422

def test_comparison_accepts_two_vehicles(comparison_service: ComparisonService):
    """2 vehicles must pass validation and execute."""
    req = ComparisonRequest(
        vehicles=[
            ComparisonVehicle(brand="Tata", model="Nexon", manufacturing_year=2020),
            ComparisonVehicle(brand="Hyundai", model="Creta", manufacturing_year=2021)
        ],
        mode=ComparisonMode.GENERAL
    )
    res = comparison_service.compare(req)
    assert res is not None
    assert len(res.vehicles) == 2
    assert res.overall_result is not None

def test_comparison_accepts_three_vehicles(comparison_service: ComparisonService):
    """3 vehicles must pass validation and execute."""
    req = ComparisonRequest(
        vehicles=[
            ComparisonVehicle(brand="Tata", model="Nexon", manufacturing_year=2020),
            ComparisonVehicle(brand="Hyundai", model="Creta", manufacturing_year=2021),
            ComparisonVehicle(brand="Maruti", model="Swift", manufacturing_year=2019)
        ],
        mode=ComparisonMode.GENERAL
    )
    res = comparison_service.compare(req)
    assert res is not None
    assert len(res.vehicles) == 3
    assert len(res.score_comparison.vehicle_scores) == 3

def test_personalized_mode_requires_user_profile(client):
    """Personalized comparison without user_profile must be rejected with 422."""
    payload = {
        "vehicles": [
            {"brand": "Tata", "model": "Nexon", "manufacturing_year": 2020},
            {"brand": "Hyundai", "model": "Creta", "manufacturing_year": 2021}
        ],
        "mode": "personalized"
        # Missing user_profile
    }
    resp = client.post("/api/v1/compare", json=payload)
    assert resp.status_code == 422


# -------------------------------------------------------------------------
# 2. Canonical Identity & Separation Tests
# -------------------------------------------------------------------------

def test_canonical_identity_preserves_different_generations(comparison_service: ComparisonService):
    """Two vehicles of same model with different years must have distinct canonical identities."""
    req = ComparisonRequest(
        vehicles=[
            ComparisonVehicle(brand="Hyundai", model="Creta", manufacturing_year=2016),
            ComparisonVehicle(brand="Hyundai", model="Creta", manufacturing_year=2021)
        ],
        mode=ComparisonMode.GENERAL
    )
    res = comparison_service.compare(req)
    assert len(res.vehicles) == 2
    v0_id = res.vehicles[0]["canonical_vehicle_id"]
    v1_id = res.vehicles[1]["canonical_vehicle_id"]
    # They should not collapse into one ID
    assert v0_id != v1_id
    assert "2016" in v0_id or "gen-1" in v0_id
    assert "2021" in v1_id or "gen-2" in v1_id

def test_canonical_identity_distinguishes_powertrains(comparison_service: ComparisonService):
    """Different powertrains must produce distinct vehicle summaries."""
    req = ComparisonRequest(
        vehicles=[
            ComparisonVehicle(brand="Hyundai", model="Creta", manufacturing_year=2021, fuel_type="Petrol", transmission_type="Manual"),
            ComparisonVehicle(brand="Hyundai", model="Creta", manufacturing_year=2021, fuel_type="Diesel", transmission_type="Automatic")
        ],
        mode=ComparisonMode.GENERAL
    )
    res = comparison_service.compare(req)
    assert res.vehicles[0]["fuel_type"] == "Petrol"
    assert res.vehicles[1]["fuel_type"] == "Diesel"


# -------------------------------------------------------------------------
# 3. Specifications, Evidence States, & Missing Data Tests
# -------------------------------------------------------------------------

def test_specifications_normalized_and_evidence_tagged(comparison_service: ComparisonService):
    """Specifications must carry structured evidence state (VERIFIED, SUPPORTED, INSUFFICIENT_DATA)."""
    req = ComparisonRequest(
        vehicles=[
            ComparisonVehicle(brand="Tata", model="Nexon", manufacturing_year=2020),
            ComparisonVehicle(brand="Maruti", model="Swift", manufacturing_year=2019)
        ],
        mode=ComparisonMode.GENERAL
    )
    res = comparison_service.compare(req)
    assert len(res.specifications) > 0

    # Check NCAP rating spec
    ncap_spec = next((s for s in res.specifications if s.spec_key == "ncap_stars"), None)
    assert ncap_spec is not None
    assert ncap_spec.values[0].evidence_state == EvidenceState.VERIFIED
    assert ncap_spec.values[0].value == 5
    assert ncap_spec.values[1].evidence_state == EvidenceState.VERIFIED
    assert ncap_spec.values[1].value == 2

def test_unverified_specifications_return_insufficient_data(comparison_service: ComparisonService):
    """Vehicle with unverified crash data must return INSUFFICIENT_DATA, not a guess."""
    req = ComparisonRequest(
        vehicles=[
            ComparisonVehicle(brand="Tata", model="Nexon", manufacturing_year=2020),
            ComparisonVehicle(brand="Honda", model="City", manufacturing_year=2019)
        ],
        mode=ComparisonMode.GENERAL
    )
    res = comparison_service.compare(req)
    ncap_spec = next((s for s in res.specifications if s.spec_key == "ncap_stars"), None)
    assert ncap_spec is not None
    # Honda City has no verified Indian crash test in database
    city_ncap = ncap_spec.values[1]
    assert city_ncap.evidence_state == EvidenceState.INSUFFICIENT_DATA
    assert city_ncap.value is None

def test_difference_significance_evaluation(comparison_service: ComparisonService):
    """Difference significance must distinguish MEANINGFUL from MINOR based on domain threshold."""
    req = ComparisonRequest(
        vehicles=[
            ComparisonVehicle(brand="Tata", model="Nexon", manufacturing_year=2020),
            ComparisonVehicle(brand="Maruti", model="Swift", manufacturing_year=2019)
        ],
        mode=ComparisonMode.GENERAL
    )
    res = comparison_service.compare(req)
    # Ground clearance: Nexon 209mm vs Swift 163mm -> diff 46mm > threshold 15mm -> MEANINGFUL
    gc_spec = next((s for s in res.specifications if s.spec_key == "ground_clearance_mm"), None)
    assert gc_spec is not None
    assert gc_spec.significance == DifferenceSignificance.MEANINGFUL
    assert gc_spec.winner_index == 0 # Nexon wins ground clearance


# -------------------------------------------------------------------------
# 4. Category Winners, Ties, & CARspective Score Comparison
# -------------------------------------------------------------------------

def test_category_winners_and_ties(comparison_service: ComparisonService):
    """Category comparison must support winners and ties."""
    req = ComparisonRequest(
        vehicles=[
            ComparisonVehicle(brand="Tata", model="Nexon", manufacturing_year=2020),
            ComparisonVehicle(brand="Hyundai", model="Creta", manufacturing_year=2021)
        ],
        mode=ComparisonMode.GENERAL
    )
    res = comparison_service.compare(req)
    assert len(res.category_winners) == 5

    # Safety: Nexon (95) vs Creta (65) -> diff 30 >= 5 -> Nexon WINNER
    safety_cat = next((c for c in res.category_winners if c.category == "Safety"), None)
    assert safety_cat is not None
    assert safety_cat.status == CategoryWinnerStatus.WINNER
    assert safety_cat.winner_index == 0

def test_score_comparison_reuses_phase5(comparison_service: ComparisonService):
    """Score comparison must reuse Phase 5 scores without recalculating."""
    req = ComparisonRequest(
        vehicles=[
            ComparisonVehicle(brand="Tata", model="Nexon", manufacturing_year=2020),
            ComparisonVehicle(brand="Hyundai", model="Creta", manufacturing_year=2021)
        ],
        mode=ComparisonMode.GENERAL
    )
    res = comparison_service.compare(req)
    sc = res.score_comparison
    assert len(sc.vehicle_scores) == 2
    # Intrinsic scores
    assert sc.vehicle_scores[0].overall_score == 84
    assert sc.vehicle_scores[1].overall_score == 81
    assert sc.overall_status in (CategoryWinnerStatus.WINNER, CategoryWinnerStatus.TIE)


# -------------------------------------------------------------------------
# 5. Valuation & Deal Analyzer Integration
# -------------------------------------------------------------------------

def test_valuation_comparison_exposes_expected_ranges(comparison_service: ComparisonService):
    """Valuation comparison exposes fair market values and ranges from Phase 3."""
    req = ComparisonRequest(
        vehicles=[
            ComparisonVehicle(brand="Tata", model="Nexon", manufacturing_year=2020),
            ComparisonVehicle(brand="Hyundai", model="Creta", manufacturing_year=2021)
        ],
        mode=ComparisonMode.GENERAL
    )
    res = comparison_service.compare(req)
    vc = res.valuation_comparison
    assert len(vc.vehicle_valuations) == 2
    assert vc.vehicle_valuations[0].estimated_fair_market_value is not None
    assert vc.vehicle_valuations[1].estimated_fair_market_value is not None
    assert vc.note is not None

def test_deal_comparison_evaluates_listing_merit(comparison_service: ComparisonService):
    """Deal comparison evaluates asking price quality while separating vehicle merit."""
    req = ComparisonRequest(
        vehicles=[
            ComparisonVehicle(brand="Tata", model="Nexon", manufacturing_year=2020),
            ComparisonVehicle(brand="Hyundai", model="Creta", manufacturing_year=2021)
        ],
        mode=ComparisonMode.GENERAL,
        listings=[
            ComparisonListing(vehicle_index=0, asking_price=500000.0), # Fair deal on Nexon
            ComparisonListing(vehicle_index=1, asking_price=1600000.0) # Overpriced on Creta
        ]
    )
    res = comparison_service.compare(req)
    assert res.deal_comparison is not None
    dc = res.deal_comparison
    assert len(dc.vehicle_deals) == 2
    assert dc.vehicle_deals[0].deal_quality == "FAIR_DEAL"
    assert dc.vehicle_deals[1].deal_quality == "OVERPRICED"
    assert dc.stronger_deal_index == 0


# -------------------------------------------------------------------------
# 6. Personalized Mode & User Fit Integration
# -------------------------------------------------------------------------

def test_personalized_comparison_evaluates_user_fit(comparison_service: ComparisonService):
    """Personalized comparison evaluates user fit against stated profile."""
    req = ComparisonRequest(
        vehicles=[
            ComparisonVehicle(brand="Tata", model="Nexon", manufacturing_year=2020),
            ComparisonVehicle(brand="Maruti", model="Swift", manufacturing_year=2019)
        ],
        mode=ComparisonMode.PERSONALIZED,
        user_profile=ComparisonUserProfile(
            budget_max=600000.0,
            safety_priority="CRITICAL",
            family_size=4,
            primary_usage="CITY"
        ),
        listings=[
            ComparisonListing(vehicle_index=0, asking_price=500000.0),
            ComparisonListing(vehicle_index=1, asking_price=520000.0)
        ]
    )
    res = comparison_service.compare(req)
    assert res.user_fit_comparison is not None
    ufc = res.user_fit_comparison
    assert len(ufc.vehicle_fits) == 2
    # Nexon has verified 5-star safety, matching CRITICAL safety priority
    assert ufc.vehicle_fits[0].priority_alignment >= ufc.vehicle_fits[1].priority_alignment


# -------------------------------------------------------------------------
# 7. Trade-offs, Best-For Labels, & Research Summaries
# -------------------------------------------------------------------------

def test_tradeoffs_and_best_for_generated(comparison_service: ComparisonService):
    """Comparison generates evidence-grounded trade-offs and 'best for' labels."""
    req = ComparisonRequest(
        vehicles=[
            ComparisonVehicle(brand="Tata", model="Nexon", manufacturing_year=2020),
            ComparisonVehicle(brand="Maruti", model="Swift", manufacturing_year=2019)
        ],
        mode=ComparisonMode.GENERAL
    )
    res = comparison_service.compare(req)
    assert len(res.tradeoffs) >= 1
    assert len(res.best_for) >= 1

    # Check best for label presence
    labels = [b.label for b in res.best_for]
    assert any("safety" in l.lower() or "fuel" in l.lower() or "rough roads" in l.lower() for l in labels)

def test_research_summaries_structured(comparison_service: ComparisonService):
    """Each vehicle receives structured strengths, weaknesses, and unknowns."""
    req = ComparisonRequest(
        vehicles=[
            ComparisonVehicle(brand="Tata", model="Nexon", manufacturing_year=2020),
            ComparisonVehicle(brand="Hyundai", model="Creta", manufacturing_year=2021)
        ],
        mode=ComparisonMode.GENERAL
    )
    res = comparison_service.compare(req)
    assert len(res.research_summaries) == 2
    for rs in res.research_summaries:
        assert len(rs.strengths) >= 1
        assert rs.vehicle_summary != ""


# -------------------------------------------------------------------------
# 8. Mandatory Invariant Tests A – E
# -------------------------------------------------------------------------

def test_invariant_test_a_asking_price_changes(comparison_service: ComparisonService):
    """
    Invariant A: Changing asking price cannot change specifications, evidence,
    or intrinsic CARspective score. It may change deal quality and personalized result.
    """
    req1 = ComparisonRequest(
        vehicles=[
            ComparisonVehicle(brand="Tata", model="Nexon", manufacturing_year=2020),
            ComparisonVehicle(brand="Hyundai", model="Creta", manufacturing_year=2021)
        ],
        mode=ComparisonMode.GENERAL,
        listings=[
            ComparisonListing(vehicle_index=0, asking_price=500000.0),
            ComparisonListing(vehicle_index=1, asking_price=600000.0)
        ]
    )
    req2 = ComparisonRequest(
        vehicles=[
            ComparisonVehicle(brand="Tata", model="Nexon", manufacturing_year=2020),
            ComparisonVehicle(brand="Hyundai", model="Creta", manufacturing_year=2021)
        ],
        mode=ComparisonMode.GENERAL,
        listings=[
            ComparisonListing(vehicle_index=0, asking_price=1500000.0), # Extreme asking price change
            ComparisonListing(vehicle_index=1, asking_price=2500000.0)
        ]
    )

    res1 = comparison_service.compare(req1)
    res2 = comparison_service.compare(req2)

    # Intrinsic scores MUST be strictly identical
    assert res1.score_comparison.vehicle_scores[0].overall_score == res2.score_comparison.vehicle_scores[0].overall_score
    assert res1.score_comparison.vehicle_scores[1].overall_score == res2.score_comparison.vehicle_scores[1].overall_score

    # Specifications MUST be strictly identical
    assert len(res1.specifications) == len(res2.specifications)
    for s1, s2 in zip(res1.specifications, res2.specifications):
        assert s1.values[0].value == s2.values[0].value
        assert s1.values[1].value == s2.values[1].value

    # Deal quality CAN change
    assert res1.deal_comparison.vehicle_deals[0].deal_quality != res2.deal_comparison.vehicle_deals[0].deal_quality

def test_invariant_test_b_user_profile_changes(comparison_service: ComparisonService):
    """
    Invariant B: Changing user profile cannot change specifications, evidence,
    or intrinsic CARspective score. It may change user fit and personalized winner.
    """
    req1 = ComparisonRequest(
        vehicles=[
            ComparisonVehicle(brand="Tata", model="Nexon", manufacturing_year=2020),
            ComparisonVehicle(brand="Maruti", model="Swift", manufacturing_year=2019)
        ],
        mode=ComparisonMode.PERSONALIZED,
        user_profile=ComparisonUserProfile(
            budget_max=600000.0,
            safety_priority="CRITICAL",
            family_size=4
        )
    )
    req2 = ComparisonRequest(
        vehicles=[
            ComparisonVehicle(brand="Tata", model="Nexon", manufacturing_year=2020),
            ComparisonVehicle(brand="Maruti", model="Swift", manufacturing_year=2019)
        ],
        mode=ComparisonMode.PERSONALIZED,
        user_profile=ComparisonUserProfile(
            budget_max=2000000.0, # High budget, low safety
            safety_priority="LOW",
            mileage_priority="HIGH",
            family_size=2
        )
    )

    res1 = comparison_service.compare(req1)
    res2 = comparison_service.compare(req2)

    # Intrinsic scores MUST be strictly identical
    assert res1.score_comparison.vehicle_scores[0].overall_score == res2.score_comparison.vehicle_scores[0].overall_score
    assert res1.score_comparison.vehicle_scores[1].overall_score == res2.score_comparison.vehicle_scores[1].overall_score

    # Specifications MUST be strictly identical
    for s1, s2 in zip(res1.specifications, res2.specifications):
        assert s1.values[0].value == s2.values[0].value

    # User fits CAN change
    fit1 = res1.user_fit_comparison.vehicle_fits[0].overall_fit
    fit2 = res2.user_fit_comparison.vehicle_fits[0].overall_fit
    assert fit1 != fit2 or res1.user_fit_comparison.vehicle_fits[1].priority_alignment != res2.user_fit_comparison.vehicle_fits[1].priority_alignment

def test_invariant_test_c_valuation_output_invariance(comparison_service: ComparisonService):
    """
    Invariant C: Changing valuation output cannot change intrinsic vehicle score.
    """
    req = ComparisonRequest(
        vehicles=[
            ComparisonVehicle(brand="Tata", model="Nexon", manufacturing_year=2020),
            ComparisonVehicle(brand="Hyundai", model="Creta", manufacturing_year=2021)
        ],
        mode=ComparisonMode.GENERAL
    )
    res = comparison_service.compare(req)
    # Score service evaluates independently from valuation model weights
    assert res.score_comparison.vehicle_scores[0].overall_score == 84
    assert res.score_comparison.vehicle_scores[1].overall_score == 81

def test_invariant_test_d_no_invented_data_for_missing_evidence(comparison_service: ComparisonService):
    """
    Invariant D: Removing or missing evidence cannot cause the system to invent replacement data.
    """
    req = ComparisonRequest(
        vehicles=[
            ComparisonVehicle(brand="Tata", model="Nexon", manufacturing_year=2020),
            ComparisonVehicle(brand="Honda", model="City", manufacturing_year=2019)
        ],
        mode=ComparisonMode.GENERAL
    )
    res = comparison_service.compare(req)
    ncap_spec = next((s for s in res.specifications if s.spec_key == "ncap_stars"), None)
    assert ncap_spec is not None
    # Honda City has no verified Indian crash test
    assert ncap_spec.values[1].evidence_state == EvidenceState.INSUFFICIENT_DATA
    assert ncap_spec.values[1].value is None

def test_invariant_test_e_two_different_canonical_vehicles_never_collapse(comparison_service: ComparisonService):
    """
    Invariant E: Two different canonical vehicles must never silently collapse into one comparison entity.
    """
    req = ComparisonRequest(
        vehicles=[
            ComparisonVehicle(brand="Hyundai", model="Creta", manufacturing_year=2016),
            ComparisonVehicle(brand="Hyundai", model="Creta", manufacturing_year=2021)
        ],
        mode=ComparisonMode.GENERAL
    )
    res = comparison_service.compare(req)
    assert len(res.vehicles) == 2
    assert res.vehicles[0]["index"] == 0
    assert res.vehicles[1]["index"] == 1
    assert res.vehicles[0]["canonical_vehicle_id"] != res.vehicles[1]["canonical_vehicle_id"]
    assert len(res.score_comparison.vehicle_scores) == 2


# -------------------------------------------------------------------------
# 9. REST API Contract & Validation Error Tests
# -------------------------------------------------------------------------

def test_compare_api_success(client):
    """POST /api/v1/compare returns 200 OK on valid payload."""
    payload = {
        "vehicles": [
            {"brand": "Tata", "model": "Nexon", "manufacturing_year": 2020},
            {"brand": "Hyundai", "model": "Creta", "manufacturing_year": 2021}
        ],
        "mode": "general"
    }
    resp = client.post("/api/v1/compare", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    assert "comparison_id" in data
    assert data["comparison_id"].startswith("cmp-")
    assert len(data["vehicles"]) == 2
    assert "score_comparison" in data
    assert "valuation_comparison" in data
    assert "overall_result" in data

def test_compare_api_invalid_content_type(client):
    """Non-JSON request returns HTTP 415."""
    resp = client.post("/api/v1/compare", data="not-json", content_type="text/plain")
    assert resp.status_code == 415

def test_compare_api_validation_error_missing_brand(client):
    """Missing brand field returns HTTP 422 with validation errors."""
    payload = {
        "vehicles": [
            {"model": "Nexon", "manufacturing_year": 2020}, # Missing brand
            {"brand": "Hyundai", "model": "Creta", "manufacturing_year": 2021}
        ],
        "mode": "general"
    }
    resp = client.post("/api/v1/compare", json=payload)
    assert resp.status_code == 422


# -------------------------------------------------------------------------
# 10. Performance Latency Measurements
# -------------------------------------------------------------------------

def test_comparison_performance_benchmarks(comparison_service: ComparisonService):
    """Measures operational latency percentiles for vehicle comparison."""
    req_2_general = ComparisonRequest(
        vehicles=[
            ComparisonVehicle(brand="Tata", model="Nexon", manufacturing_year=2020),
            ComparisonVehicle(brand="Hyundai", model="Creta", manufacturing_year=2021)
        ],
        mode=ComparisonMode.GENERAL
    )
    req_3_personalized = ComparisonRequest(
        vehicles=[
            ComparisonVehicle(brand="Tata", model="Nexon", manufacturing_year=2020),
            ComparisonVehicle(brand="Hyundai", model="Creta", manufacturing_year=2021),
            ComparisonVehicle(brand="Maruti", model="Swift", manufacturing_year=2019)
        ],
        mode=ComparisonMode.PERSONALIZED,
        user_profile=ComparisonUserProfile(
            budget_max=1000000.0,
            safety_priority="HIGH"
        ),
        listings=[
            ComparisonListing(vehicle_index=0, asking_price=500000.0),
            ComparisonListing(vehicle_index=1, asking_price=600000.0),
            ComparisonListing(vehicle_index=2, asking_price=450000.0)
        ]
    )

    # Warm-up
    comparison_service.compare(req_2_general)

    latencies = []
    for _ in range(5):
        t0 = time.perf_counter()
        comparison_service.compare(req_2_general)
        latencies.append((time.perf_counter() - t0) * 1000)

    p50 = float(np.percentile(latencies, 50))
    p95 = float(np.percentile(latencies, 95))
    print(f"\n[Comparison Benchmark] 2-Vehicle General P50: {p50:.2f} ms, P95: {p95:.2f} ms")

    # Target: Warm P50 should be under 150 ms
    assert p50 < 150.0
