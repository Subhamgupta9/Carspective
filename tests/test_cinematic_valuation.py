"""
SMARTCAR AI — PHASE 8: CINEMATIC VALUATION FLOW TESTS
=====================================================
Validates:
1. 6 Sequential Analysis Stages:
   - ANALYZING VEHICLE
   - ANALYZING MARKET
   - COMPARING VEHICLES
   - CALCULATING DEPRECIATION
   - ESTIMATING VALUE
   - PRICE REVEAL
2. Total default duration <= 6 seconds (4.5s default).
3. Backward-compatible /api/predict schema preserving all legacy keys.
4. Non-fabricated, factual market dimensions:
   - Price range with documented methodology
   - Market position
   - Depreciation schedule
   - Usage intensity
   - Ownership impact
   - Demand level
   - Comparable vehicles strictly from real 57,480 dataset
5. Animated price count-up and UI DOM contracts.
6. Execution against all 5 benchmark vehicles.
"""

import os
import re
import json
import pytest
from app.app import app, df, calculate_cinematic_valuation_analysis, predict_vehicle_price, model

requires_legacy_model = pytest.mark.skipif(
    model is None,
    reason="Legacy 907MB model artifact (smart_used_car_price_model.pkl) not available in clean checkout"
)


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


# ============================================================
# 1. 6 SEQUENTIAL STAGES DEFINITION & DURATION CONSTRAINTS
# ============================================================

def test_six_stages_defined_in_ui_js():
    """Verify that ui.js exports CINEMATIC_VALUATION_STAGES with the exact 6 stages."""
    ui_js_path = os.path.join(os.path.dirname(__file__), "..", "app", "static", "js", "experience", "ui.js")
    with open(ui_js_path, "r", encoding="utf-8") as f:
        content = f.read()

    expected_stages = [
        "ANALYZING VEHICLE",
        "ANALYZING MARKET",
        "COMPARING VEHICLES",
        "CALCULATING DEPRECIATION",
        "ESTIMATING VALUE",
        "PRICE REVEAL"
    ]

    assert "CINEMATIC_VALUATION_STAGES" in content

    for stage_name in expected_stages:
        assert f'"{stage_name}"' in content or f"'{stage_name}'" in content, f"Missing stage: {stage_name}"


def test_cinematic_valuation_duration_under_six_seconds():
    """Verify that stage duration per step yields total default duration <= 6 seconds."""
    ui_js_path = os.path.join(os.path.dirname(__file__), "..", "app", "static", "js", "experience", "ui.js")
    with open(ui_js_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Match stageDuration in ui.js
    match = re.search(r"stageDuration\s*=\s*(\d+)", content)
    assert match is not None, "stageDuration not found in ui.js"
    duration_ms = int(match.group(1))

    # 6 stages
    total_duration_sec = (6 * duration_ms) / 1000.0
    assert total_duration_sec <= 6.0, f"Total duration {total_duration_sec}s exceeds 6 seconds constraint!"
    assert total_duration_sec >= 3.0, f"Total duration {total_duration_sec}s too fast for cinematic flow"


def test_main_js_exposes_valuation_flow_api():
    """Verify that main.js exposes valuationStages and runValuationFlow on window.__SMARTCAR__."""
    main_js_path = os.path.join(os.path.dirname(__file__), "..", "app", "static", "js", "experience", "main.js")
    with open(main_js_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "valuationStages" in content
    assert "runValuationFlow" in content


# ============================================================
# 2. BACKWARD-COMPATIBLE /api/predict ENDPOINT INTEGRITY
# ============================================================

def test_api_predict_returns_503_when_model_unavailable(client, monkeypatch):
    """Verify /api/predict returns HTTP 503 (MODEL_UNAVAILABLE) when the legacy model artifact is absent."""
    import app.app as app_mod
    monkeypatch.setattr(app_mod, "model", None)
    res = client.post("/api/predict", json={
        "brand": "BMW",
        "model": "3 Series",
        "manufacturing_year": 2021,
        "km_driven": 40000,
        "fuel_type": "Diesel",
        "transmission_type": "Automatic",
        "city": "Delhi",
        "bodytype": "Sedan",
        "number_of_owners": 1
    })
    assert res.status_code == 503
    data = res.get_json()
    assert data["success"] is False
    assert data["code"] == "MODEL_UNAVAILABLE"
    assert "smart_used_car_price_model.pkl" in data["error"]


@requires_legacy_model
def test_api_predict_backward_compatibility(client):
    """Verify that /api/predict preserves all legacy keys while adding Phase 8 fields."""
    payload = {
        "brand": "BMW",
        "model": "3 Series",
        "manufacturing_year": 2021,
        "km_driven": 45000,
        "fuel_type": "Diesel",
        "transmission_type": "Automatic",
        "city": "Delhi",
        "bodytype": "Sedan",
        "number_of_owners": 1
    }

    res = client.post("/api/predict", json=payload)
    assert res.status_code == 200
    data = res.get_json()

    # Legacy keys must all exist
    legacy_keys = [
        "success", "prediction", "formatted_prediction",
        "vehicle_summary", "vehicle", "details", "derived",
        "model_metrics", "market_context"
    ]
    for key in legacy_keys:
        assert key in data, f"Missing legacy key: {key}"

    # Phase 8 7 dimensions must exist at top-level
    phase8_dimensions = [
        "price_range",
        "market_position",
        "depreciation",
        "usage_intensity",
        "ownership_impact",
        "demand_level",
        "comparable_vehicles"
    ]
    for dim in phase8_dimensions:
        assert dim in data, f"Missing Phase 8 dimension: {dim}"


# ============================================================
# 3. NON-FABRICATED DIMENSIONS & DOCUMENTED METHODOLOGY
# ============================================================

@requires_legacy_model
def test_price_range_documented_methodology(client):
    """Verify price range is grounded in documented MAE / test error methodology."""
    payload = {
        "brand": "BMW",
        "model": "3 Series",
        "manufacturing_year": 2021,
        "km_driven": 45000,
        "fuel_type": "Diesel",
        "transmission_type": "Automatic",
        "city": "Delhi",
        "bodytype": "Sedan",
        "number_of_owners": 1
    }

    res = client.post("/api/predict", json=payload)
    assert res.status_code == 200
    data = res.get_json()

    pr = data["price_range"]
    assert "min" in pr and "max" in pr
    assert "methodology" in pr
    assert len(pr["methodology"]) > 20
    assert "MAE" in pr["methodology"] or "Mean Absolute Error" in pr["methodology"]
    assert pr["min"] < data["prediction"] < pr["max"]
    assert pr["formatted_min"].startswith("₹")
    assert pr["formatted_max"].startswith("₹")


@requires_legacy_model
def test_market_position_grounded_in_dataset(client):
    """Verify market position reflects dataset percentile and observed median."""
    payload = {
        "brand": "BMW",
        "model": "3 Series",
        "manufacturing_year": 2021,
        "km_driven": 45000,
        "fuel_type": "Diesel",
        "transmission_type": "Automatic",
        "city": "Delhi",
        "bodytype": "Sedan",
        "number_of_owners": 1
    }

    res = client.post("/api/predict", json=payload)
    data = res.get_json()
    mp = data["market_position"]

    assert 0 <= mp["percentile"] <= 100
    assert mp["median_price"] > 0
    assert "verdict" in mp
    assert "summary" in mp


@requires_legacy_model
def test_depreciation_schedule(client):
    """Verify automotive depreciation schedule attributes."""
    payload = {
        "brand": "Toyota",
        "model": "Fortuner",
        "manufacturing_year": 2021,
        "km_driven": 50000,
        "fuel_type": "Diesel",
        "transmission_type": "Automatic (TC)",
        "city": "Mumbai",
        "bodytype": "SUV",
        "number_of_owners": 1
    }

    res = client.post("/api/predict", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    deprec = data["depreciation"]

    assert deprec["age_years"] >= 1
    assert 0.0 < deprec["total_depreciation_pct"] < 90.0
    assert 0.0 < deprec["annual_depreciation_rate"] < 50.0
    assert round(deprec["retained_value_pct"] + deprec["total_depreciation_pct"], 1) == 100.0


@requires_legacy_model
def test_usage_intensity_benchmark(client):
    """Verify usage intensity evaluates against national 11,000 KM benchmark."""
    payload = {
        "brand": "Hyundai",
        "model": "Creta",
        "manufacturing_year": 2022,
        "km_driven": 22000,
        "fuel_type": "Petrol",
        "transmission_type": "Manual",
        "city": "Bangalore",
        "bodytype": "SUV",
        "number_of_owners": 1
    }

    res = client.post("/api/predict", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    usage = data["usage_intensity"]

    assert usage["benchmark_annual_km"] == 11000
    assert usage["annual_km"] > 0
    assert usage["badge"] in ["LOW MILEAGE", "STANDARD", "HIGH USAGE"]
    assert "KM" in usage["formatted_annual_km"]


@requires_legacy_model
def test_ownership_impact(client):
    """Verify ownership impact adjustment."""
    # First owner
    res1 = client.post("/api/predict", json={
        "brand": "Hyundai", "model": "Creta", "manufacturing_year": 2022,
        "km_driven": 30000, "fuel_type": "Petrol", "transmission_type": "Manual",
        "city": "Delhi", "bodytype": "SUV", "number_of_owners": 1
    })
    assert res1.status_code == 200
    data1 = res1.get_json()
    assert data1["ownership_impact"]["number_of_owners"] == 1
    assert data1["ownership_impact"]["adjustment_pct"] == 0.0

    # Second owner
    res2 = client.post("/api/predict", json={
        "brand": "Hyundai", "model": "Creta", "manufacturing_year": 2022,
        "km_driven": 30000, "fuel_type": "Petrol", "transmission_type": "Manual",
        "city": "Delhi", "bodytype": "SUV", "number_of_owners": 2
    })
    assert res2.status_code == 200
    data2 = res2.get_json()
    assert data2["ownership_impact"]["number_of_owners"] == 2
    assert data2["ownership_impact"]["adjustment_pct"] < 0.0


@requires_legacy_model
def test_demand_level_liquidity_score(client):
    """Verify demand level returns calibrated liquidity score."""
    res = client.post("/api/predict", json={
        "brand": "Mercedes-Benz", "model": "C-Class", "manufacturing_year": 2022,
        "km_driven": 25000, "fuel_type": "Mild Hybrid (Electric + Diesel)", "transmission_type": "Automatic (TC)",
        "city": "Delhi", "bodytype": "Sedan", "number_of_owners": 1
    })
    assert res.status_code == 200
    data = res.get_json()
    dl = data["demand_level"]

    assert 0 <= dl["liquidity_score"] <= 100
    assert dl["comparable_count"] >= 0
    assert "label" in dl
    assert "description" in dl


@requires_legacy_model
def test_comparables_come_from_actual_dataset(client):
    """CRITICAL: Verify that comparable vehicles are genuine records from 57,480 CSV dataset."""
    payload = {
        "brand": "BMW",
        "model": "3 Series",
        "manufacturing_year": 2021,
        "km_driven": 45000,
        "fuel_type": "Diesel",
        "transmission_type": "Automatic",
        "city": "Delhi",
        "bodytype": "Sedan",
        "number_of_owners": 1
    }

    res = client.post("/api/predict", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    comps = data["comparable_vehicles"]

    assert len(comps) > 0, "Expected comparable vehicle records from dataset"

    # Cross-reference each returned comparable against the real loaded DataFrame
    for comp in comps:
        rec_id = comp["record_id"]
        assert rec_id in df.index, f"Comparable record_id {rec_id} not found in actual dataset!"
        df_row = df.loc[rec_id]

        # Verify attributes match the real raw dataset record
        assert str(df_row["brand"]).strip().lower() == comp["brand"].strip().lower()
        assert comp["actual_price"] == int(round(float(df_row["_num_price"])))
        assert comp["km_driven"] == int(round(float(df_row["_num_km"])))


# ============================================================
# 4. BENCHMARK VEHICLES FULL VALUATION PASS
# ============================================================

@requires_legacy_model
@pytest.mark.parametrize("brand,model,year,km,fuel,trans,city,body,owners", [
    ("BMW", "3 Series", 2021, 40000, "Diesel", "Automatic", "Delhi", "Sedan", 1),
    ("Hyundai", "Creta", 2022, 28000, "Petrol", "Manual", "Mumbai", "SUV", 1),
    ("Toyota", "Fortuner", 2021, 55000, "Diesel", "Automatic (TC)", "Bangalore", "SUV", 1),
    ("Mercedes-Benz", "C-Class", 2022, 24000, "Mild Hybrid (Electric + Diesel)", "Automatic (TC)", "Delhi", "Sedan", 1),
    ("Porsche", "911", 2021, 15000, "Petrol", "Automatic (DCT)", "Mumbai", "Coupe", 1),
])
def test_all_five_benchmark_vehicles_cinematic_valuation(client, brand, model, year, km, fuel, trans, city, body, owners):
    """Verify complete cinematic valuation payload for all 5 benchmark vehicles."""
    payload = {
        "brand": brand,
        "model": model,
        "manufacturing_year": year,
        "km_driven": km,
        "fuel_type": fuel,
        "transmission_type": trans,
        "city": city,
        "bodytype": body,
        "number_of_owners": owners
    }

    res = client.post("/api/predict", json=payload)
    assert res.status_code == 200
    data = res.get_json()

    assert data["success"] is True
    assert data["prediction"] > 0
    assert data["price_range"]["min"] < data["prediction"] < data["price_range"]["max"]
    assert len(data["comparable_vehicles"]) > 0


# ============================================================
# 5. UI DOM AND ANIMATION COMPONENT VERIFICATION
# ============================================================

def test_ui_js_contains_estimated_market_value_and_all_seven_cards():
    """Verify that ui.js renders ESTIMATED MARKET VALUE and all 7 dimension cards."""
    ui_js_path = os.path.join(os.path.dirname(__file__), "..", "app", "static", "js", "experience", "ui.js")
    with open(ui_js_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "ESTIMATED MARKET VALUE" in content
    assert "animatePriceCountUp" in content
    assert "cardPriceRange" in content
    assert "cardMarketPosition" in content
    assert "cardDepreciation" in content
    assert "cardUsageIntensity" in content
    assert "cardOwnershipImpact" in content
    assert "cardDemandLevel" in content
    assert "cardComparableVehicles" in content


def test_style_css_contains_phase8_rules():
    """Verify that style.css defines the Phase 8 visual classes."""
    css_path = os.path.join(os.path.dirname(__file__), "..", "app", "static", "css", "style.css")
    with open(css_path, "r", encoding="utf-8") as f:
        content = f.read()

    required_classes = [
        "cinematic-valuation-flow",
        "valuation-active-stage-title",
        "val-stage-node",
        "val-progress-bar-fill",
        "val-telemetry-hud",
        "valuation-dimensions-grid",
        "val-dimension-card",
        "range-hero-numbers",
        "val-methodology-callout",
        "val-metrics-triplet",
        "val-comps-grid"
    ]
    for cls in required_classes:
        assert cls in content, f"Missing CSS class: {cls}"
