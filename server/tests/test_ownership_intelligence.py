"""
CARspective — Phase 14 Ownership Intelligence Test Suite
Verifies maintenance cadence, interactive fuel cost calculator, multi-year TCO model,
deterministic risk signals, and REST API contracts.
"""

import pytest
from server.app import create_app
from server.domain.ownership.service import OwnershipIntelligenceService
from server.domain.ownership.models import (
    VehicleOwnershipIntelligence,
    FuelCostRequest,
    FuelCostResponse,
    TCORequest,
    TCOResponse,
    TCOComponentStatus,
)


@pytest.fixture
def ownership_service():
    return OwnershipIntelligenceService()


@pytest.fixture
def client():
    app = create_app({"TESTING": True})
    with app.test_client() as client:
        yield client


def test_ownership_intelligence_profile_generation(ownership_service):
    """Verify end-to-end ownership intelligence profile for canonical vehicle."""
    import time
    # Warm up repository
    ownership_service.get_ownership_intelligence("maruti-suzuki::swift")
    
    t0 = time.perf_counter()
    intel = ownership_service.get_ownership_intelligence("maruti-suzuki::swift")
    t1 = time.perf_counter()
    latency_ms = (t1 - t0) * 1000.0

    assert isinstance(intel, VehicleOwnershipIntelligence)
    assert latency_ms < 150.0, f"Query took {latency_ms:.2f}ms, SLA is < 150ms"
    assert intel.canonical_vehicle_id == "maruti-suzuki::swift"
    assert intel.maintenance.service_interval_km > 0
    assert intel.default_tco_summary is not None
    assert intel.default_tco_summary.total_cost_of_ownership_inr > 0
    assert len(intel.risk_signals) > 0


def test_fuel_cost_calculator_logic(ownership_service):
    """Verify fuel cost calculator computation and edge case handling."""
    req = FuelCostRequest(
        mileage_kmpl=15.0,
        annual_km=12000.0,
        fuel_type="Petrol",
        fuel_price_per_unit=96.72,
    )
    res = ownership_service.calculate_fuel_cost(req)
    assert isinstance(res, FuelCostResponse)
    assert res.annual_km == 12000.0
    expected_annual_litres = 12000.0 / 15.0
    expected_annual_cost = expected_annual_litres * 96.72
    assert round(res.annual_fuel_cost_inr, 0) == round(expected_annual_cost, 0)
    assert round(res.cost_per_km_inr, 2) == round(96.72 / 15.0, 2)
    assert round(res.monthly_fuel_cost_inr, 0) == round(expected_annual_cost / 12.0, 0)


def test_tco_component_statuses(ownership_service):
    """Verify TCO calculation tags each component with explicit provenance status."""
    req = TCORequest(
        canonical_vehicle_id="honda::city",
        ownership_years=5,
        annual_km=12000.0,
        custom_purchase_price=750000.0,
    )
    res = ownership_service.calculate_tco(req)
    assert isinstance(res, TCOResponse)
    assert res.ownership_years == 5
    assert res.total_cost_of_ownership_inr > 0
    assert res.cost_per_km_inr > 0
    assert res.net_depreciation_loss_inr > 0

    component_names = [c.component_name for c in res.components]
    assert any("Depreciation" in c for c in component_names)
    assert any("Fuel" in c for c in component_names)
    assert any("Maintenance" in c for c in component_names)
    assert any("Insurance" in c for c in component_names)

    for comp in res.components:
        assert comp.status in (
            TCOComponentStatus.USER_PROVIDED,
            TCOComponentStatus.EVIDENCE_BACKED,
            TCOComponentStatus.MODEL_ESTIMATED,
        )


def test_ownership_risk_signals(ownership_service):
    """Verify deterministic risk signals are generated with descriptions and advice."""
    intel = ownership_service.get_ownership_intelligence("hyundai::creta")
    assert len(intel.risk_signals) >= 1
    for r in intel.risk_signals:
        assert r.title != ""
        assert r.description != ""
        assert r.mitigation_advice != ""


def test_real_world_mileage_present(ownership_service):
    """Verify that city and highway mileage estimates are present."""
    intel = ownership_service.get_ownership_intelligence("tata::nexon")
    assert intel.real_world_city_mileage != ""
    assert intel.real_world_highway_mileage != ""


def test_api_get_ownership(client):
    """Verify GET /api/v1/ownership/<cid> endpoint."""
    res = client.get("/api/v1/ownership/maruti-suzuki::swift")
    assert res.status_code == 200
    data = res.get_json()
    assert data["canonical_vehicle_id"] == "maruti-suzuki::swift"
    assert "maintenance" in data
    assert "default_tco_summary" in data
    assert "risk_signals" in data


def test_api_post_fuel_cost(client):
    """Verify POST /api/v1/ownership/cost endpoint."""
    res = client.post(
        "/api/v1/ownership/cost",
        json={"mileage_kmpl": 18.0, "annual_km": 12000.0, "fuel_type": "Petrol"},
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["annual_fuel_cost_inr"] > 0
    assert data["monthly_fuel_cost_inr"] > 0
    assert data["cost_per_km_inr"] > 0


def test_api_post_tco(client):
    """Verify POST /api/v1/ownership/tco endpoint."""
    res = client.post(
        "/api/v1/ownership/tco",
        json={
            "canonical_vehicle_id": "hyundai::creta",
            "ownership_years": 3,
            "annual_km": 10000.0,
            "custom_purchase_price": 850000.0,
        },
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["ownership_years"] == 3
    assert data["total_cost_of_ownership_inr"] > 0
    assert len(data["components"]) >= 4
