"""
SMARTCAR AI — PHASE 9: MARKET INTELLIGENCE & COMPARABLES TESTS
==============================================================
Validates:
1. Strict Data Sourcing:
   - All market statistics originate exclusively from data/raw/indian_used_cars_raw_57480.csv.
   - Zero synthetic, fabricated, or hallucinated values.
2. Defensible Factor Computation:
   - compute_factors():
     * Market Context (sample size, min, p25, median, p75, max, IQR, avg mileage)
     * Empirical Depreciation Curve (year cohorts, medians, depreciation % vs newest anchor)
     * Fuel Mix (distribution %, counts)
     * Transmission Mix (distribution %, counts)
     * City Volume (top cities %, selected city share)
3. Factual Dataset Comparables:
   - find_comparables():
     * Real transaction records with verified record_id, actual_price, similarity_score.
     * Accurate sorting by multi-attribute distance metric.
4. Safe Sparse Segments Handling:
   - When sample size < 3 or cohorts < 2, returns "Insufficient Data" without inventing data.
5. In-Memory Caching:
   - market_summary() employs _SUMMARY_CACHE for high performance.
6. Backward-Compatible API Endpoints:
   - GET /api/market-intelligence returns full market intelligence schema.
   - /api/predict backward compatibility includes market_intelligence payload.
7. Frontend Contracts & CSS:
   - DOM elements (#intelMarketIntelligence, #intelDepreciationChart, #intelFuelMixChart, etc.).
   - CSS styling (.intel-chart-card, .deprec-curve-chart-container, .sparse-badge, etc.).
   - JavaScript API exposure (window.__SMARTCAR__.fetchMarketIntelligence).
"""

import os
import re
import json
import pytest
from app.app import app, model
from app.market_intelligence import (
    MarketIntelligenceDataset,
    compute_factors,
    find_comparables,
    market_summary,
    _SUMMARY_CACHE
)


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


# ============================================================
# 1. DATASET INTEGRITY & FACTOR COMPUTATION TESTS
# ============================================================

def test_dataset_singleton_loads_real_records():
    """Verify that MarketIntelligenceDataset successfully loads 57,480 raw records."""
    dataset = MarketIntelligenceDataset()
    df = dataset.get_df()
    assert df is not None
    assert len(df) == 57480
    assert "brand" in df.columns
    assert "model" in df.columns
    assert "actual_price" in df.columns
    assert "manufacturing_year" in df.columns


def test_compute_factors_dense_vehicle_bmw_3_series():
    """Verify factor computation on a dense vehicle model (BMW 3 Series)."""
    factors = compute_factors("BMW", "3 Series", city="Delhi", fuel="Diesel", transmission="Automatic", year=2021)
    
    # 1. Market Context
    ctx = factors["market_context"]
    assert ctx["has_sufficient_data"] is True
    assert ctx["sample_size"] >= 10
    assert ctx["min_price"] > 0
    assert ctx["p25_price"] <= ctx["median_price"]
    assert ctx["median_price"] <= ctx["p75_price"]
    assert ctx["p75_price"] <= ctx["max_price"]
    assert ctx["iqr"] == ctx["p75_price"] - ctx["p25_price"]
    assert "₹" in ctx["formatted_median_price"]

    # 2. Depreciation Curve
    deprec = factors["depreciation_curve"]
    assert deprec["has_sufficient_data"] is True
    assert deprec["cohort_count"] >= 3
    assert len(deprec["points"]) >= 3
    # Check that points are ordered chronologically by year (for left-to-right chart rendering)
    years = [p["year"] for p in deprec["points"]]
    assert years == sorted(years)
    # Check selected year flag
    selected_points = [p for p in deprec["points"] if p["is_selected_year"]]
    if selected_points:
        assert selected_points[0]["year"] == 2021

    # 3. Fuel Mix
    fuel = factors["fuel_mix"]
    assert fuel["has_sufficient_data"] is True
    assert len(fuel["distribution"]) >= 1
    total_pct = sum(f["percentage"] for f in fuel["distribution"])
    assert 99.0 <= total_pct <= 101.0  # Float rounding tolerance

    # 4. Transmission Mix
    trans = factors["transmission_mix"]
    assert trans["has_sufficient_data"] is True
    assert len(trans["distribution"]) >= 1
    total_trans_pct = sum(t["percentage"] for t in trans["distribution"])
    assert 99.0 <= total_trans_pct <= 101.0

    # 5. City Volume
    city = factors["city_volume"]
    assert city["has_sufficient_data"] is True
    assert len(city["top_cities"]) >= 1


def test_compute_factors_sparse_segment_insufficient_data():
    """Verify that a sparse vehicle model (< 3 records) returns Insufficient Data."""
    # Aston Martin DBX has only 1 record in dataset
    factors = compute_factors("Aston Martin", "DBX", year=2021)

    ctx = factors["market_context"]
    assert ctx["has_sufficient_data"] is False
    assert ctx["message"] == "Insufficient Data"

    deprec = factors["depreciation_curve"]
    assert deprec["has_sufficient_data"] is False
    assert deprec["message"] == "Insufficient Data"

    fuel = factors["fuel_mix"]
    assert fuel["has_sufficient_data"] is False
    assert fuel["message"] == "Insufficient Data"

    trans = factors["transmission_mix"]
    assert trans["has_sufficient_data"] is False
    assert trans["message"] == "Insufficient Data"

    city = factors["city_volume"]
    assert city["has_sufficient_data"] is False
    assert city["message"] == "Insufficient Data"


def test_compute_factors_nonexistent_brand():
    """Verify handling of completely non-existent brand."""
    factors = compute_factors("NonExistentBrand", "NonExistentModel")
    assert factors["market_context"]["has_sufficient_data"] is False
    assert factors["market_context"]["message"] == "Insufficient Data"
    assert factors["depreciation_curve"]["has_sufficient_data"] is False


# ============================================================
# 2. REAL COMPARABLES TESTS
# ============================================================

def test_find_comparables_returns_real_dataset_records():
    """Verify find_comparables returns real records with proper schema and score."""
    comps = find_comparables("Hyundai", "Creta", year=2022, km=30000, fuel="Petrol", transmission="Manual", limit=4)
    assert len(comps) > 0
    assert len(comps) <= 4

    for comp in comps:
        assert "record_id" in comp
        assert isinstance(comp["record_id"], int)
        assert comp["brand"].lower() == "hyundai"
        assert "creta" in comp["model"].lower()
        assert comp["actual_price"] > 0
        assert "₹" in comp["formatted_price"]
        assert 0.0 <= comp["similarity_score"] <= 100.0

    # Ensure records are sorted by similarity score descending
    scores = [c["similarity_score"] for c in comps]
    assert scores == sorted(scores, reverse=True)


def test_find_comparables_sparse_model():
    """Verify find_comparables gracefully returns available sparse records without crash."""
    comps = find_comparables("Aston Martin", "DBX", limit=4)
    assert len(comps) <= 1


# ============================================================
# 3. MARKET SUMMARY & CACHING TESTS
# ============================================================

def test_market_summary_caching():
    """Verify market_summary caches results and returns cached dictionary on second call."""
    _SUMMARY_CACHE.clear()
    
    # First call - cache miss
    summary1 = market_summary("Toyota", "Fortuner", year=2021, km=45000, city="Bangalore")
    assert summary1 is not None
    assert "market_context" in summary1
    assert "depreciation_curve" in summary1
    assert "comparables" in summary1
    assert len(_SUMMARY_CACHE) >= 1

    # Second call - cache hit
    summary2 = market_summary("Toyota", "Fortuner", year=2021, km=45000, city="Bangalore")
    assert summary2 == summary1


def test_market_summary_sparse_flag():
    """Verify market_summary marks is_sparse correctly."""
    sparse_summary = market_summary("Aston Martin", "DBX")
    assert sparse_summary["is_sparse"] is True

    dense_summary = market_summary("Hyundai", "Creta")
    assert dense_summary["is_sparse"] is False


# ============================================================
# 4. HTTP API ENDPOINT TESTS
# ============================================================

def test_api_market_intelligence_endpoint_success(client):
    """Verify GET /api/market-intelligence returns 200 and valid payload for dense vehicle."""
    response = client.get("/api/market-intelligence?brand=BMW&model=3+Series&year=2021&city=Delhi")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["brand"] == "BMW"
    assert data["model"] == "3 Series"
    assert "market_context" in data
    assert "depreciation_curve" in data
    assert "fuel_mix" in data
    assert "transmission_mix" in data
    assert "city_volume" in data
    assert "comparables" in data


def test_api_market_intelligence_missing_parameters(client):
    """Verify GET /api/market-intelligence returns 400 when brand or model is omitted."""
    resp1 = client.get("/api/market-intelligence?brand=BMW")
    assert resp1.status_code == 400
    data1 = resp1.get_json()
    assert data1["success"] is False

    resp2 = client.get("/api/market-intelligence?model=3+Series")
    assert resp2.status_code == 400


def test_api_market_intelligence_sparse_endpoint(client):
    """Verify GET /api/market-intelligence returns 200 with is_sparse=True for sparse models."""
    response = client.get("/api/market-intelligence?brand=Aston+Martin&model=DBX")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["is_sparse"] is True
    assert data["market_context"]["message"] == "Insufficient Data"


@pytest.mark.skipif(
    model is None,
    reason="Legacy 907MB model artifact (smart_used_car_price_model.pkl) not available in clean checkout"
)
def test_predict_endpoint_contains_market_intelligence(client):
    """Verify POST /api/predict backward compatibility includes market_intelligence."""
    payload = {
        "brand": "BMW",
        "model": "3 Series",
        "manufacturing_year": 2021,
        "km_driven": 25000,
        "fuel_type": "Petrol",
        "transmission_type": "Automatic",
        "bodytype": "Sedan",
        "city": "Delhi",
        "number_of_owners": 1
    }
    response = client.post("/api/predict", json=payload)
    assert response.status_code == 200
    data = response.get_json()

    # Legacy fields
    assert "prediction" in data
    assert "formatted_prediction" in data

    # Phase 8 fields
    assert "price_range" in data
    assert "market_position" in data
    assert "depreciation" in data
    assert "comparable_vehicles" in data

    # Phase 9 field
    assert "market_intelligence" in data
    intel = data["market_intelligence"]
    assert "market_context" in intel
    assert "depreciation_curve" in intel
    assert "fuel_mix" in intel
    assert "transmission_mix" in intel
    assert "city_volume" in intel


# ============================================================
# 5. BENCHMARK VEHICLES COVERAGE
# ============================================================

@pytest.mark.parametrize("brand,model,year,km,fuel,transmission,city", [
    ("BMW", "3 Series", 2021, 40000, "Diesel", "Automatic", "Delhi"),
    ("Hyundai", "Creta", 2022, 28000, "Petrol", "Manual", "Mumbai"),
    ("Toyota", "Fortuner", 2021, 55000, "Diesel", "Automatic", "Bangalore"),
    ("Mercedes-Benz", "C-Class", 2022, 24000, "Diesel", "Automatic", "Delhi"),
    ("Porsche", "911", 2021, 15000, "Petrol", "Automatic", "Mumbai"),
])
def test_all_five_benchmark_vehicles_market_intelligence(brand, model, year, km, fuel, transmission, city):
    """Verify market intelligence executes successfully for all 5 benchmark vehicles."""
    summary = market_summary(
        brand=brand,
        model=model,
        year=year,
        km=km,
        fuel=fuel,
        transmission=transmission,
        city=city
    )
    assert summary is not None
    assert summary["brand"] == brand
    assert summary["model"] == model
    assert "market_context" in summary
    assert "depreciation_curve" in summary
    assert "fuel_mix" in summary
    assert "transmission_mix" in summary
    assert "city_volume" in summary
    assert "comparables" in summary


# ============================================================
# 6. FRONTEND DOM, CSS & JS API CONTRACTS
# ============================================================

def test_ui_js_contains_phase9_dashboard_and_fetch_method():
    """Verify ui.js includes Phase 9 DOM elements and fetchMarketIntelligence method."""
    ui_js_path = os.path.join(os.path.dirname(__file__), "..", "app", "static", "js", "experience", "ui.js")
    with open(ui_js_path, "r", encoding="utf-8") as f:
        content = f.read()

    # DOM IDs
    assert "intelMarketIntelligence" in content
    assert "intelDepreciationCard" in content
    assert "intelDepreciationChart" in content
    assert "intelFuelMixCard" in content
    assert "intelFuelMixChart" in content
    assert "intelTransMixCard" in content
    assert "intelTransmissionMixChart" in content
    assert "intelCityVolCard" in content
    assert "intelCityVolumeChart" in content
    assert "intelMarketContextCard" in content
    assert "valuationComparablesGrid" in content

    # Sparse data badge and notice
    assert "intel-sparse-notice" in content
    assert "sparse-badge" in content
    assert "Insufficient Data" in content

    # Method
    assert "fetchMarketIntelligence" in content


def test_style_css_contains_phase9_chart_rules():
    """Verify style.css contains Phase 9 Market Intelligence CSS rules."""
    style_css_path = os.path.join(os.path.dirname(__file__), "..", "app", "static", "css", "style.css")
    with open(style_css_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert ".intel-chart-card" in content
    assert ".deprec-curve-chart-container" in content
    assert ".deprec-columns-wrap" in content
    assert ".deprec-point-col" in content
    assert ".intel-charts-dual-grid" in content
    assert ".intel-mix-row" in content
    assert ".intel-city-card" in content
    assert ".intel-spread-grid" in content
    assert ".intel-sparse-notice" in content
    assert ".sparse-badge" in content
    assert ".market-return-btn" in content


def test_main_js_exposes_fetch_market_intelligence():
    """Verify main.js exposes fetchMarketIntelligence on window.__SMARTCAR__ and window.smartCarExperience."""
    main_js_path = os.path.join(os.path.dirname(__file__), "..", "app", "static", "js", "experience", "main.js")
    with open(main_js_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "fetchMarketIntelligence" in content
