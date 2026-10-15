"""
CARspective — Server Valuation Test Suite
Comprehensive unit, domain, security, and latency tests for the Valuation Engine.
"""

import time
import pytest
import numpy as np
from server.domain.valuation.service import ValuationService, ModelSecurityIntegrityError
from server.domain.valuation.models import ValuationRequest

def test_valuation_normal_prediction(app_client):
    """Verify normal valuation calculation for standard vehicle."""
    payload = {
        "brand": "Maruti",
        "model": "Swift",
        "manufacturing_year": 2021,
        "km_driven": 35000,
        "fuel_type": "Petrol",
        "transmission_type": "Manual",
        "city": "Delhi",
        "bodytype": "Hatchback",
        "number_of_owners": 1
    }
    response = app_client.post("/api/v1/valuation", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    
    assert data["estimated_fair_market_value"] is not None
    assert data["estimated_fair_market_value"] > 200000
    assert data["estimated_fair_market_value"] < 1200000
    
    # Range check
    rng = data["expected_fair_market_range"]
    assert rng is not None
    assert rng["lower_bound"] < data["estimated_fair_market_value"]
    assert rng["upper_bound"] > data["estimated_fair_market_value"]
    assert rng["confidence_interval_percent"] == 80.0
    
    # Confidence and quality
    assert data["confidence_state"] in ["HIGH_CONFIDENCE", "MODERATE_CONFIDENCE"]
    assert data["evidence_quality"] == "SUPPORTED"
    assert "Statistical Model Estimate" in data["model_metadata"]["target_concept"]

def test_valuation_asking_price_isolation(app_client):
    """Verify asking price is completely isolated and does not alter valuation estimate."""
    base_payload = {
        "brand": "Hyundai",
        "model": "Creta",
        "manufacturing_year": 2020,
        "km_driven": 40000,
        "fuel_type": "Diesel",
        "transmission_type": "Manual",
        "city": "Mumbai",
        "bodytype": "SUV",
        "number_of_owners": 1
    }
    
    # Without asking price
    resp1 = app_client.post("/api/v1/valuation", json=base_payload)
    val1 = resp1.get_json()["estimated_fair_market_value"]
    
    # With low asking price
    payload_low = dict(base_payload, asking_price=150000)
    resp2 = app_client.post("/api/v1/valuation", json=payload_low)
    val2 = resp2.get_json()["estimated_fair_market_value"]
    
    # With absurd high asking price
    payload_high = dict(base_payload, asking_price=50000000)
    resp3 = app_client.post("/api/v1/valuation", json=payload_high)
    val3 = resp3.get_json()["estimated_fair_market_value"]
    
    assert val1 == val2 == val3, "LEAKAGE: Valuation altered by user asking price!"

def test_valuation_unseen_model_graceful_handling(app_client):
    """Verify unseen/rare model executes safely without crashing and flags LIMITED_CONFIDENCE."""
    payload = {
        "brand": "Koenigsegg",
        "model": "Jesko",
        "manufacturing_year": 2023,
        "km_driven": 2000,
        "fuel_type": "Petrol",
        "transmission_type": "Automatic",
        "city": "Bangalore",
        "bodytype": "Coupe",
        "number_of_owners": 1
    }
    response = app_client.post("/api/v1/valuation", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["confidence_state"] == "LIMITED_CONFIDENCE"
    assert data["evidence_quality"] == "MODEL_ESTIMATE"
    assert any("fallback" in lim.lower() or "unseen" in lim.lower() or "not be fully matched" in lim.lower() for lim in data["limitations"])

def test_valuation_insufficient_data_behavior(app_client):
    """Verify out-of-distribution invalid vehicle returns INSUFFICIENT_DATA."""
    payload = {
        "brand": "AncientUnknownCo",
        "model": "ExperimentalSteamCar",
        "manufacturing_year": 1985,
        "km_driven": 950000,
        "fuel_type": "Diesel",
        "transmission_type": "Manual",
        "city": "UnknownCity",
        "bodytype": "Other",
        "number_of_owners": 5
    }
    response = app_client.post("/api/v1/valuation", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["confidence_state"] == "INSUFFICIENT_DATA"
    assert data["evidence_quality"] == "INSUFFICIENT_DATA"
    assert data["estimated_fair_market_value"] is None
    assert data["expected_fair_market_range"] is None

def test_valuation_conformal_range_calibration_multiplier(app_client):
    """Verify fair market range conforms strictly to calibrated empirical multiplier."""
    payload = {
        "brand": "Tata",
        "model": "Nexon",
        "manufacturing_year": 2022,
        "km_driven": 25000,
        "fuel_type": "Petrol",
        "transmission_type": "Manual",
        "city": "Pune",
        "bodytype": "SUV",
        "number_of_owners": 1
    }
    response = app_client.post("/api/v1/valuation", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    
    val = data["estimated_fair_market_value"]
    rng = data["expected_fair_market_range"]
    mult = rng["multiplier"]
    
    expected_lower = max(10000, int(round(val * (1.0 - mult))))
    expected_upper = int(round(val * (1.0 + mult)))
    
    assert abs(rng["lower_bound"] - expected_lower) <= 2
    assert abs(rng["upper_bound"] - expected_upper) <= 2

def test_valuation_security_hash_verification(tmp_path):
    """Verify startup security gate halts loading when SHA-256 integrity check fails."""
    fake_manifest = tmp_path / "tampered_manifest.json"
    fake_manifest.write_text('{"artifact": {"sha256": "bad_hash_1234567890abcdef"}}')
    
    with pytest.raises(ModelSecurityIntegrityError):
        _ = ValuationService(manifest_path=str(fake_manifest))

def test_valuation_schema_validation(app_client):
    """Verify 422 Unprocessable Entity on invalid input values."""
    # Negative km
    res = app_client.post("/api/v1/valuation", json={
        "brand": "Maruti", "model": "Swift", "manufacturing_year": 2020, "km_driven": -500
    })
    assert res.status_code == 422
    
    # Year in future
    res = app_client.post("/api/v1/valuation", json={
        "brand": "Maruti", "model": "Swift", "manufacturing_year": 2035, "km_driven": 10000
    })
    assert res.status_code == 422

    # Non-json body
    res = app_client.post("/api/v1/valuation", data="plain text")
    assert res.status_code == 415

def test_valuation_latency_benchmarks(app_client):
    """Measure empirical API latency across 50 requests (p50, p95, p99)."""
    payload = {
        "brand": "Maruti",
        "model": "Swift",
        "manufacturing_year": 2021,
        "km_driven": 35000,
        "fuel_type": "Petrol",
        "transmission_type": "Manual"
    }
    
    latencies = []
    for _ in range(50):
        t0 = time.perf_counter()
        resp = app_client.post("/api/v1/valuation", json=payload)
        lat = (time.perf_counter() - t0) * 1000
        assert resp.status_code == 200
        latencies.append(lat)
        
    p50 = float(np.percentile(latencies, 50))
    p95 = float(np.percentile(latencies, 95))
    p99 = float(np.percentile(latencies, 99))
    
    print(f"\n[Valuation API Latency] p50: {p50:.2f}ms | p95: {p95:.2f}ms | p99: {p99:.2f}ms")
    # Verify reasonable operational latency (< 50ms)
    assert p50 < 40.0
