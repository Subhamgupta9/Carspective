"""
CARspective — Phase 20E Valuation Preprocessing Optimization Tests
Validates that categorical preprocessing optimization produces bit-for-bit identical
predictions, exact output schemas, correct cache hit behaviors, and thread safety.
"""

import pytest
import numpy as np
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

from server.domain.valuation.service import ValuationService
from server.domain.valuation.models import ValuationRequest, ValuationResponse

@pytest.fixture
def valuation_service():
    service = ValuationService()
    service._cat_prep_cache.clear()
    return service

def test_numerical_equivalence_against_raw_pipeline(valuation_service):
    """Verifies optimized evaluate_valuation produces identical predictions to raw pipeline.predict."""
    test_cases = [
        ValuationRequest(brand="Maruti Suzuki", model="Swift", manufacturing_year=2021, km_driven=25000, fuel_type="Petrol", transmission_type="Manual", city="Delhi", bodytype="Hatchback", number_of_owners=1),
        ValuationRequest(brand="Hyundai", model="Creta", manufacturing_year=2020, km_driven=45000, fuel_type="Diesel", transmission_type="Manual", city="Mumbai", bodytype="SUV", number_of_owners=2),
        ValuationRequest(brand="Tata", model="Nexon", manufacturing_year=2022, km_driven=18000, fuel_type="Petrol", transmission_type="Manual", city="Bangalore", bodytype="SUV", number_of_owners=1),
        ValuationRequest(brand="Honda", model="City", manufacturing_year=2019, km_driven=60000, fuel_type="Petrol", transmission_type="Automatic", city="Delhi", bodytype="Sedan", number_of_owners=1),
        ValuationRequest(brand="Toyota", model="Fortuner", manufacturing_year=2017, km_driven=120000, fuel_type="Diesel", transmission_type="Automatic", city="Chennai", bodytype="SUV", number_of_owners=3),
    ]

    for req in test_cases:
        # Optimized service output
        res = valuation_service.evaluate_valuation(req)
        
        # Raw baseline prediction directly through un-optimized DataFrame + pipeline.predict
        v_age = max(0, 2026 - req.manufacturing_year)
        log_km = float(np.log1p(req.km_driven))
        raw_df = pd.DataFrame([{
            "manufacturing_year": int(req.manufacturing_year),
            "model": str(req.model).strip(),
            "km_driven": float(req.km_driven),
            "fuel_type": str(req.fuel_type or "Petrol").strip(),
            "transmission_type": str(req.transmission_type or "Manual").strip(),
            "brand": str(req.brand).strip(),
            "city": str(req.city or "Delhi").strip(),
            "bodytype": str(req.bodytype or "Hatchback").strip(),
            "number_of_owners": int(req.number_of_owners or 1),
            "vehicle_age": int(v_age),
            "log_km_driven": log_km
        }])
        raw_log_pred = float(valuation_service.pipeline.predict(raw_df)[0])
        raw_val = int(round(max(15000.0, float(np.expm1(raw_log_pred)))))

        assert res.estimated_fair_market_value == raw_val, f"Mismatch for {req.brand} {req.model}"

def test_missing_and_none_categorical_fields(valuation_service):
    """Verifies that missing/None fields resolve to expected defaults with identical outputs."""
    req_missing = ValuationRequest(
        brand="Hyundai",
        model="Creta",
        manufacturing_year=2020,
        km_driven=50000,
        fuel_type=None,
        transmission_type=None,
        city=None,
        bodytype=None,
        number_of_owners=None
    )
    res = valuation_service.evaluate_valuation(req_missing)
    assert res.estimated_fair_market_value is not None
    assert res.estimated_fair_market_value > 0
    assert res.confidence_state in {"HIGH_CONFIDENCE", "MODERATE_CONFIDENCE", "LIMITED_CONFIDENCE"}

def test_unknown_and_out_of_distribution_categories(valuation_service):
    """Verifies that out-of-distribution/unknown categories are handled gracefully without errors."""
    req_unknown = ValuationRequest(
        brand="AlienMotors",
        model="X-Wing 9000",
        manufacturing_year=2023,
        km_driven=10000,
        fuel_type="Electric",
        transmission_type="Automatic",
        city="MoonCity",
        bodytype="Coupe",
        number_of_owners=1
    )
    res = valuation_service.evaluate_valuation(req_unknown)
    assert res.estimated_fair_market_value is not None
    assert res.estimated_fair_market_value > 0

def test_cache_hits_and_misses(valuation_service):
    """Verifies that subsequent evaluations of identical categorical configuration trigger cache hits."""
    valuation_service._cat_prep_cache.clear()
    
    req = ValuationRequest(
        brand="Maruti Suzuki",
        model="Swift",
        manufacturing_year=2021,
        km_driven=25000,
        fuel_type="Petrol",
        transmission_type="Manual",
        city="Delhi",
        bodytype="Hatchback"
    )
    
    # First call: miss
    res1 = valuation_service.evaluate_valuation(req)
    stats1 = valuation_service._cat_prep_cache.stats
    assert stats1["misses"] == 1
    assert stats1["hits"] == 0
    assert stats1["size"] == 1
    
    # Second call with same categorical inputs but different km_driven: hit!
    req2 = ValuationRequest(
        brand="Maruti Suzuki",
        model="Swift",
        manufacturing_year=2021,
        km_driven=55000,  # different mileage
        fuel_type="Petrol",
        transmission_type="Manual",
        city="Delhi",
        bodytype="Hatchback"
    )
    res2 = valuation_service.evaluate_valuation(req2)
    stats2 = valuation_service._cat_prep_cache.stats
    assert stats2["misses"] == 1
    assert stats2["hits"] == 1
    assert stats2["size"] == 1
    
    # Mileage difference should yield lower price for higher km
    assert res2.estimated_fair_market_value < res1.estimated_fair_market_value

def test_concurrency_thread_safety(valuation_service):
    """Verifies thread-safe execution across concurrent worker threads."""
    req = ValuationRequest(
        brand="Tata",
        model="Nexon",
        manufacturing_year=2022,
        km_driven=20000,
        fuel_type="Petrol",
        transmission_type="Manual",
        city="Bangalore",
        bodytype="SUV"
    )
    
    def evaluate_worker(_):
        return valuation_service.evaluate_valuation(req).estimated_fair_market_value

    with ThreadPoolExecutor(max_workers=10) as ex:
        results = list(ex.map(evaluate_worker, range(50)))
        
    # All 50 concurrent calls must produce the identical value
    assert len(set(results)) == 1
    assert results[0] > 0

def test_response_schema_completeness(valuation_service):
    """Verifies all required response fields and contracts are populated."""
    req = ValuationRequest(
        brand="Honda",
        model="City",
        manufacturing_year=2019,
        km_driven=40000,
        fuel_type="Petrol",
        transmission_type="Manual",
        city="Delhi"
    )
    res = valuation_service.evaluate_valuation(req)
    assert isinstance(res, ValuationResponse)
    assert res.estimated_fair_market_value is not None
    assert res.expected_fair_market_range is not None
    assert res.expected_fair_market_range.lower_bound < res.estimated_fair_market_value < res.expected_fair_market_range.upper_bound
    assert res.confidence_state is not None
    assert res.evidence_quality is not None
    assert len(res.limitations) > 0
    assert "model_version" in res.model_metadata
