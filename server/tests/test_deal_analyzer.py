"""
CARspective — Phase 4 Deal Analyzer & Negotiation Intelligence Test Suite
Tests:
1. Deal quality classifications (GREAT_DEAL, FAIR_DEAL, OVERPRICED, UNUSUALLY_LOW_ASKING_PRICE)
2. Empirical boundary conditions
3. Mathematical precision of price deviation and range position
4. Evidence-grounded negotiation guidance (targets, strength, walk-away signals)
5. Structured risk signals (Price, Documentation, Condition, Data risks)
6. CRITICAL ASKING PRICE ISOLATION: Changing asking price NEVER alters valuation baseline
7. Graceful handling of out-of-distribution / insufficient data inputs
8. REST API contract & validation errors (POST /api/v1/deal-analysis)
9. Performance latency measurements
"""

import pytest
import time
import numpy as np
from flask import Flask

from server.app import create_app
from server.domain.deal_analyzer.models import (
    DealAnalysisRequest,
    DealQualityEnum,
    RangePositionCategory,
    NegotiationStrength,
    RiskCategory,
    RiskSeverity
)
from server.domain.deal_analyzer.service import DealAnalyzerService
from server.domain.valuation.service import ValuationService

@pytest.fixture(scope="module")
def app() -> Flask:
    flask_app = create_app({"TESTING": True})
    return flask_app

@pytest.fixture(scope="module")
def client(app: Flask):
    return app.test_client()

@pytest.fixture(scope="module")
def deal_service() -> DealAnalyzerService:
    return DealAnalyzerService()

# -------------------------------------------------------------------------
# 1. Classification & Boundary Condition Tests
# -------------------------------------------------------------------------

def test_deal_quality_fair_deal_within_range(deal_service: DealAnalyzerService):
    """Test that an asking price equal to or near estimated baseline is classified as FAIR_DEAL."""
    # First get fair market baseline for standard car
    probe_req = DealAnalysisRequest(
        brand="Hyundai",
        model="Creta",
        manufacturing_year=2019,
        km_driven=45000,
        fuel_type="Diesel",
        transmission_type="Manual",
        city="Delhi",
        asking_price=950000
    )
    res = deal_service.analyze_deal(probe_req)
    baseline = res.valuation.estimated_fair_market_value
    assert baseline is not None
    lower = res.valuation.expected_fair_market_lower
    upper = res.valuation.expected_fair_market_upper
    
    # Test exactly at baseline
    req_mid = DealAnalysisRequest(
        brand="Hyundai",
        model="Creta",
        manufacturing_year=2019,
        km_driven=45000,
        fuel_type="Diesel",
        transmission_type="Manual",
        city="Delhi",
        asking_price=float(baseline)
    )
    res_mid = deal_service.analyze_deal(req_mid)
    assert res_mid.deal_quality == DealQualityEnum.FAIR_DEAL
    assert res_mid.range_position.category == RangePositionCategory.INSIDE_RANGE
    assert abs(res_mid.price_deviation.relative_difference_percent) < 0.1

def test_deal_quality_exact_boundary_conditions(deal_service: DealAnalyzerService):
    """Test boundary conditions at lower_bound and upper_bound."""
    probe_req = DealAnalysisRequest(
        brand="Maruti",
        model="Swift",
        manufacturing_year=2018,
        km_driven=50000,
        fuel_type="Petrol",
        transmission_type="Manual",
        city="Delhi",
        asking_price=500000
    )
    res = deal_service.analyze_deal(probe_req)
    lower = res.valuation.expected_fair_market_lower
    upper = res.valuation.expected_fair_market_upper
    
    # Exactly at lower bound: still inside 80% range -> FAIR_DEAL
    req_lower = probe_req.model_copy(update={"asking_price": float(lower)})
    res_lower = deal_service.analyze_deal(req_lower)
    assert res_lower.deal_quality == DealQualityEnum.FAIR_DEAL
    assert res_lower.range_position.category == RangePositionCategory.INSIDE_RANGE
    assert abs(res_lower.range_position.position_ratio - 0.0) < 0.01

    # Exactly at upper bound: still inside 80% range -> FAIR_DEAL
    req_upper = probe_req.model_copy(update={"asking_price": float(upper)})
    res_upper = deal_service.analyze_deal(req_upper)
    assert res_upper.deal_quality == DealQualityEnum.FAIR_DEAL
    assert res_upper.range_position.category == RangePositionCategory.INSIDE_RANGE
    assert abs(res_upper.range_position.position_ratio - 1.0) < 0.01

def test_deal_quality_great_deal_below_range(deal_service: DealAnalyzerService):
    """Test asking price below fair range but above anomaly threshold is GREAT_DEAL."""
    probe_req = DealAnalysisRequest(
        brand="Maruti",
        model="Swift",
        manufacturing_year=2018,
        km_driven=50000,
        asking_price=500000
    )
    res = deal_service.analyze_deal(probe_req)
    baseline = res.valuation.estimated_fair_market_value
    
    # 26% discount from baseline (ratio ~0.74): below lower bound (0.7822) and above 0.65 threshold
    great_deal_price = float(round(baseline * 0.74))
    req_great = probe_req.model_copy(update={"asking_price": great_deal_price})
    res_great = deal_service.analyze_deal(req_great)
    
    assert res_great.deal_quality == DealQualityEnum.GREAT_DEAL
    assert res_great.deal_quality_label == "Great Deal"
    assert res_great.range_position.category == RangePositionCategory.BELOW_RANGE
    assert res_great.range_position.position_ratio < 0.0
    assert res_great.anomaly_status.is_anomaly is False

def test_deal_quality_overpriced_above_range(deal_service: DealAnalyzerService):
    """Test asking price above fair range is OVERPRICED."""
    probe_req = DealAnalysisRequest(
        brand="Maruti",
        model="Swift",
        manufacturing_year=2018,
        km_driven=50000,
        asking_price=500000
    )
    res = deal_service.analyze_deal(probe_req)
    baseline = res.valuation.estimated_fair_market_value
    
    # 30% premium above baseline (ratio 1.30): above upper bound (1.2178)
    overpriced_price = float(round(baseline * 1.30))
    req_op = probe_req.model_copy(update={"asking_price": overpriced_price})
    res_op = deal_service.analyze_deal(req_op)
    
    assert res_op.deal_quality == DealQualityEnum.OVERPRICED
    assert res_op.deal_quality_label == "Overpriced"
    assert res_op.range_position.category == RangePositionCategory.ABOVE_RANGE
    assert res_op.range_position.position_ratio > 1.0

def test_deal_quality_unusually_low_asking_price(deal_service: DealAnalyzerService):
    """Test statistically anomalous asking price (>35% discount) triggers UNUSUALLY_LOW_ASKING_PRICE."""
    probe_req = DealAnalysisRequest(
        brand="Hyundai",
        model="Creta",
        manufacturing_year=2019,
        km_driven=45000,
        asking_price=900000
    )
    res = deal_service.analyze_deal(probe_req)
    baseline = res.valuation.estimated_fair_market_value
    
    # 50% discount from baseline (ratio 0.50): extreme anomaly
    anomaly_price = float(round(baseline * 0.50))
    req_anom = probe_req.model_copy(update={"asking_price": anomaly_price})
    res_anom = deal_service.analyze_deal(req_anom)
    
    assert res_anom.deal_quality == DealQualityEnum.UNUSUALLY_LOW_ASKING_PRICE
    assert res_anom.deal_quality_label == "Unusually Low Asking Price"
    assert res_anom.anomaly_status.is_anomaly is True
    assert res_anom.anomaly_status.anomaly_type == "ANOMALOUS_LOW"
    assert res_anom.anomaly_status.advisory is not None
    # Verify advisory text matches architectural mandate without hallucinating words
    assert "Verify mechanical condition, accident history, ownership documents" in res_anom.anomaly_status.advisory
    assert "scam" not in res_anom.anomaly_status.advisory.lower()
    assert "fraud" not in res_anom.anomaly_status.advisory.lower()

# -------------------------------------------------------------------------
# 2. Mathematical Correctness Tests
# -------------------------------------------------------------------------

def test_deal_deviation_and_range_position_math(deal_service: DealAnalyzerService):
    """Test precision of absolute difference, relative percentage, and range position formula."""
    req = DealAnalysisRequest(
        brand="Tata",
        model="Nexon",
        manufacturing_year=2021,
        km_driven=30000,
        fuel_type="Petrol",
        asking_price=800000
    )
    res = deal_service.analyze_deal(req)
    baseline = res.valuation.estimated_fair_market_value
    lower = res.valuation.expected_fair_market_lower
    upper = res.valuation.expected_fair_market_upper
    
    # Check absolute diff
    expected_abs = 800000 - baseline
    assert res.price_deviation.absolute_difference == expected_abs
    
    # Check relative diff
    expected_rel_pct = round(((800000 - baseline) / baseline) * 100.0, 2)
    assert res.price_deviation.relative_difference_percent == expected_rel_pct
    
    # Check range position
    expected_pos = round((800000 - lower) / float(upper - lower), 4)
    assert abs(res.range_position.position_ratio - expected_pos) < 0.0001

# -------------------------------------------------------------------------
# 3. CRITICAL ASKING PRICE ISOLATION TEST (Mandatory Architecture Rule)
# -------------------------------------------------------------------------

def test_mandatory_asking_price_isolation(deal_service: DealAnalyzerService):
    """
    CRITICAL MANDATORY TEST:
    Varying the asking price across three vastly different figures (₹2L, ₹8L, ₹25L)
    MUST NOT alter the underlying ML valuation estimate, fair range, or confidence state!
    Valuation baseline MUST remain invariant.
    """
    base_kwargs = {
        "brand": "Maruti",
        "model": "Swift",
        "manufacturing_year": 2018,
        "km_driven": 40000.0,
        "fuel_type": "Petrol",
        "transmission_type": "Manual",
        "city": "Delhi"
    }

    # Probe baseline dynamically
    probe = deal_service.analyze_deal(DealAnalysisRequest(**base_kwargs, asking_price=450000.0))
    baseline = probe.valuation.estimated_fair_market_value
    assert baseline is not None

    req_low = DealAnalysisRequest(**base_kwargs, asking_price=float(round(baseline * 0.45)))
    req_mid = DealAnalysisRequest(**base_kwargs, asking_price=float(baseline))
    req_high = DealAnalysisRequest(**base_kwargs, asking_price=float(round(baseline * 2.00)))

    res_low = deal_service.analyze_deal(req_low)
    res_mid = deal_service.analyze_deal(req_mid)
    res_high = deal_service.analyze_deal(req_high)

    # 1. Valuation outputs MUST BE IDENTICAL
    assert res_low.valuation.estimated_fair_market_value == res_mid.valuation.estimated_fair_market_value
    assert res_mid.valuation.estimated_fair_market_value == res_high.valuation.estimated_fair_market_value

    assert res_low.valuation.expected_fair_market_lower == res_mid.valuation.expected_fair_market_lower
    assert res_mid.valuation.expected_fair_market_lower == res_high.valuation.expected_fair_market_lower

    assert res_low.valuation.expected_fair_market_upper == res_mid.valuation.expected_fair_market_upper
    assert res_mid.valuation.expected_fair_market_upper == res_high.valuation.expected_fair_market_upper

    assert res_low.valuation.confidence_state == res_mid.valuation.confidence_state
    assert res_mid.valuation.confidence_state == res_high.valuation.confidence_state

    # 2. Deal quality and commercial attributes MUST CHANGE
    assert res_low.deal_quality == DealQualityEnum.UNUSUALLY_LOW_ASKING_PRICE
    assert res_mid.deal_quality == DealQualityEnum.FAIR_DEAL
    assert res_high.deal_quality == DealQualityEnum.OVERPRICED

    assert res_low.price_deviation.relative_difference_percent < -50.0
    assert abs(res_mid.price_deviation.relative_difference_percent) < 25.0
    assert res_high.price_deviation.relative_difference_percent >= 90.0

    assert res_high.negotiation.walk_away_signal is True
    assert res_low.negotiation.walk_away_signal is False

# -------------------------------------------------------------------------
# 4. Negotiation Intelligence Tests
# -------------------------------------------------------------------------

def test_negotiation_guidance_for_overpriced_vehicle(deal_service: DealAnalyzerService):
    """Test negotiation output for overpriced listing provides defensible target and walk-away flag."""
    probe = deal_service.analyze_deal(DealAnalysisRequest(
        brand="Hyundai",
        model="Creta",
        manufacturing_year=2019,
        km_driven=45000,
        asking_price=1500000
    ))
    baseline = probe.valuation.estimated_fair_market_value
    
    # Excessively overpriced: >35% above baseline -> triggers walk-away signal
    req_extreme = DealAnalysisRequest(
        brand="Hyundai",
        model="Creta",
        manufacturing_year=2019,
        km_driven=45000,
        asking_price=float(round(baseline * 1.50))
    )
    res_extreme = deal_service.analyze_deal(req_extreme)
    
    assert res_extreme.negotiation.walk_away_signal is True
    assert res_extreme.negotiation.walk_away_rationale is not None
    assert res_extreme.negotiation.target_price is not None
    assert res_extreme.negotiation.target_price <= baseline

def test_negotiation_safety_disclaimer_presence(deal_service: DealAnalyzerService):
    """Test that negotiation output never implies false certainty and provides safety disclaimer."""
    req = DealAnalysisRequest(
        brand="Tata",
        model="Harrier",
        manufacturing_year=2020,
        km_driven=40000,
        asking_price=1400000
    )
    res = deal_service.analyze_deal(req)
    assert res.negotiation.safety_disclaimer is not None
    assert "does not guarantee seller acceptance" in res.negotiation.safety_disclaimer.lower()

# -------------------------------------------------------------------------
# 5. Structured Risk Signals Tests
# -------------------------------------------------------------------------

def test_risk_signals_triggered_by_condition_and_provenance(deal_service: DealAnalyzerService):
    """Test that unverified documentation, accidents, and high km trigger structured risk signals."""
    req = DealAnalysisRequest(
        brand="Mahindra",
        model="XUV500",
        manufacturing_year=2016,
        km_driven=140000,  # High km > 120k -> DATA_RISK
        number_of_owners=3,  # Multiple owners -> DOCUMENTATION_RISK
        service_history_status="UNAVAILABLE",  # Missing records -> DOCUMENTATION_RISK
        accident_history_status="MINOR_ACCIDENT",  # Accident -> CONDITION_RISK
        insurance_status="EXPIRED",  # Expired insurance -> DOCUMENTATION_RISK
        tyre_condition="WORN",  # Worn tyres -> CONDITION_RISK
        asking_price=600000
    )
    res = deal_service.analyze_deal(req)
    
    risk_codes = {r.code for r in res.risk_signals}
    assert "HIGH_ODOMETER_ACCUMULATION" in risk_codes
    assert "MULTIPLE_PREVIOUS_OWNERS" in risk_codes
    assert "SERVICE_HISTORY_UNVERIFIED" in risk_codes
    assert "ACCIDENT_HISTORY_REPORTED" in risk_codes
    assert "INSURANCE_EXPIRED_OR_UNAVAILABLE" in risk_codes
    assert "TYRE_CONDITION_UNVERIFIED" in risk_codes

    # Verify severity and categories
    for r in res.risk_signals:
        assert isinstance(r.category, RiskCategory)
        assert isinstance(r.severity, RiskSeverity)
        assert r.recommended_action is not None

# -------------------------------------------------------------------------
# 6. Graceful Handling of Insufficient Data
# -------------------------------------------------------------------------

def test_insufficient_data_handling(deal_service: DealAnalyzerService):
    """Test that out-of-distribution vehicles return INSUFFICIENT_DATA deal analysis."""
    req = DealAnalysisRequest(
        brand="UnknownBrandXYZ",
        model="UnknownModel123",
        manufacturing_year=1982,
        km_driven=850000,
        asking_price=200000
    )
    res = deal_service.analyze_deal(req)
    assert res.deal_quality == DealQualityEnum.INSUFFICIENT_DATA
    assert res.range_position.category == RangePositionCategory.UNAVAILABLE
    assert res.valuation.estimated_fair_market_value is None
    assert "unavailable" in res.explanation.lower()

# -------------------------------------------------------------------------
# 7. REST API Endpoint Tests (POST /api/v1/deal-analysis)
# -------------------------------------------------------------------------

def test_deal_analysis_api_success(client):
    """Test successful POST /api/v1/deal-analysis request."""
    payload = {
        "brand": "Maruti",
        "model": "Baleno",
        "manufacturing_year": 2020,
        "km_driven": 35000,
        "fuel_type": "Petrol",
        "transmission_type": "Manual",
        "city": "Mumbai",
        "asking_price": 680000
    }
    resp = client.post("/api/v1/deal-analysis", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    assert "deal_quality" in data
    assert "valuation" in data
    assert "price_deviation" in data
    assert "range_position" in data
    assert "negotiation" in data
    assert "risk_signals" in data
    assert "explanation" in data
    assert "asking_price" in data
    assert data["asking_price"] == 680000

def test_deal_analysis_api_validation_error_missing_asking_price(client):
    """Test missing asking_price returns 422."""
    payload = {
        "brand": "Maruti",
        "model": "Baleno",
        "manufacturing_year": 2020,
        "km_driven": 35000
    }
    resp = client.post("/api/v1/deal-analysis", json=payload)
    assert resp.status_code == 422
    data = resp.get_json()
    assert data["status"] == 422

def test_deal_analysis_api_validation_error_non_positive_price(client):
    """Test negative or zero asking price returns 422."""
    payload = {
        "brand": "Maruti",
        "model": "Baleno",
        "manufacturing_year": 2020,
        "km_driven": 35000,
        "asking_price": -5000
    }
    resp = client.post("/api/v1/deal-analysis", json=payload)
    assert resp.status_code == 422

def test_deal_analysis_api_invalid_content_type(client):
    """Test non-JSON Content-Type returns 415."""
    resp = client.post("/api/v1/deal-analysis", data="hello", content_type="text/plain")
    assert resp.status_code == 415

# -------------------------------------------------------------------------
# 8. Performance Latency Benchmark
# -------------------------------------------------------------------------

def test_deal_analysis_performance_benchmarks(deal_service: DealAnalyzerService):
    """Measures latency of repeated deal analysis evaluations (cold and warm)."""
    req = DealAnalysisRequest(
        brand="Hyundai",
        model="Creta",
        manufacturing_year=2019,
        km_driven=45000,
        fuel_type="Diesel",
        asking_price=950000
    )
    # Warm-up run
    deal_service.analyze_deal(req)

    latencies = []
    for _ in range(25):
        t0 = time.perf_counter()
        deal_service.analyze_deal(req)
        latencies.append((time.perf_counter() - t0) * 1000)

    p50 = float(np.percentile(latencies, 50))
    p95 = float(np.percentile(latencies, 95))
    
    # Deal analysis (including ML inference & taxonomy resolution) should be fast
    assert p50 < 75.0, f"p50 latency {p50:.2f} ms exceeded 75ms budget"
    assert p95 < 120.0, f"p95 latency {p95:.2f} ms exceeded 120ms budget"
