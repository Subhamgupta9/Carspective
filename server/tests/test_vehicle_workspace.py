"""
CARspective — Phase 13 Vehicle Intelligence Workspace Tests
Verifies end-to-end multi-engine synthesis, identity confidence states,
strict asking price isolation, generation isolation, and API contracts.
"""

import time
import pytest
import numpy as np
from flask.testing import FlaskClient

from server.infrastructure.database import ScopedSession
from server.domain.workspace.service import VehicleWorkspaceService
from server.domain.workspace.models import IdentityConfidenceLevel
from server.app import create_app


@pytest.fixture(scope="module")
def app_client():
    app = create_app({"TESTING": True})
    with app.test_client() as client:
        yield client


@pytest.fixture(scope="module")
def workspace_service():
    session = ScopedSession()
    return VehicleWorkspaceService(session=session)


def test_workspace_exact_identity_resolution(workspace_service: VehicleWorkspaceService):
    """Verifies that a fully qualified 6-tier canonical ID resolves to EXACT confidence."""
    canonical_id = "maruti-suzuki::swift::gen-3-2018::2021::zxi::1-2-k12m-5mt"
    res = workspace_service.get_vehicle_workspace(canonical_id, km_driven=30000)

    assert res is not None
    assert res.identity_confidence.level == IdentityConfidenceLevel.EXACT
    assert res.identity_confidence.needs_user_confirmation is False
    assert res.identity_confidence.is_confirmed is True
    assert res.identity.brand == "Maruti Suzuki"
    assert res.identity.model == "Swift"
    assert res.identity.generation == "3rd Generation"
    assert res.identity.year == 2021
    assert res.identity.variant == "ZXi"
    assert len(res.identity_confidence.sibling_variants) >= 3


def test_workspace_resolved_baseline_identity(workspace_service: VehicleWorkspaceService):
    """Verifies that generation/year without explicit variant resolves to RESOLVED baseline."""
    canonical_id = "maruti-suzuki::swift::gen-3-2018::2021"
    res = workspace_service.get_vehicle_workspace(canonical_id)

    assert res is not None
    assert res.identity_confidence.level == IdentityConfidenceLevel.RESOLVED
    assert res.identity_confidence.needs_user_confirmation is False
    assert res.identity.variant is not None  # Default baseline variant loaded
    assert len(res.identity_confidence.sibling_variants) >= 3


def test_workspace_ambiguous_identity_resolution(workspace_service: VehicleWorkspaceService):
    """Verifies that model-only query spanning multiple generations resolves to AMBIGUOUS with confirmation prompt."""
    canonical_id = "maruti-suzuki::swift"
    res = workspace_service.get_vehicle_workspace(canonical_id)

    assert res is not None
    assert res.identity_confidence.level == IdentityConfidenceLevel.AMBIGUOUS
    assert res.identity_confidence.needs_user_confirmation is True
    assert res.identity_confidence.is_confirmed is False
    assert len(res.identity_confidence.sibling_generations) >= 2


def test_workspace_limited_knowledge_resolution(workspace_service: VehicleWorkspaceService):
    """Verifies that vehicles without deep 9-table knowledge resolve to LIMITED with graceful baseline."""
    canonical_id = "toyota::innova-crysta::gen-1-2016"
    res = workspace_service.get_vehicle_workspace(canonical_id)

    assert res is not None
    assert res.identity_confidence.level == IdentityConfidenceLevel.LIMITED
    assert res.executive_summary.estimated_fair_market_value_inr is not None
    assert res.executive_summary.carspective_score is not None


def test_strict_asking_price_isolation(workspace_service: VehicleWorkspaceService):
    """
    CRITICAL GOVERNANCE INVARIANT:
    Passing an asking price must NOT alter intrinsic Fair Market Value or intrinsic CARspective Score.
    Deal Analysis is isolated to commercial comparison only.
    """
    canonical_id = "tata::nexon::gen-1-2017::2020::xz-plus"

    res_without_price = workspace_service.get_vehicle_workspace(canonical_id, km_driven=35000)
    res_with_price = workspace_service.get_vehicle_workspace(canonical_id, asking_price=950000, km_driven=35000)

    assert res_without_price is not None
    assert res_with_price is not None

    # Score isolation
    assert res_without_price.executive_summary.carspective_score == res_with_price.executive_summary.carspective_score
    assert res_without_price.score["overall_score"] == res_with_price.score["overall_score"]

    # Valuation isolation
    assert res_without_price.executive_summary.estimated_fair_market_value_inr == res_with_price.executive_summary.estimated_fair_market_value_inr
    assert res_without_price.valuation["estimated_fair_market_value"] == res_with_price.valuation["estimated_fair_market_value"]

    # Deal analysis isolated
    assert res_without_price.deal_analysis is None
    assert res_without_price.executive_summary.deal_quality is None
    assert res_with_price.deal_analysis is not None
    assert res_with_price.executive_summary.deal_quality is not None


def test_generation_safety_isolation(workspace_service: VehicleWorkspaceService):
    """Verifies that safety ratings are scoped to generation without cross-generation contamination."""
    swift_gen3 = workspace_service.get_vehicle_workspace("maruti-suzuki::swift::gen-3-2018::2021::zxi")
    nexon_gen1 = workspace_service.get_vehicle_workspace("tata::nexon::gen-1-2017::2020::xz-plus")

    assert swift_gen3.executive_summary.safety_stars == 2
    assert swift_gen3.executive_summary.safety_agency == "Global NCAP"
    assert swift_gen3.executive_summary.bodyshell_integrity == "Unstable"

    assert nexon_gen1.executive_summary.safety_stars == 5
    assert nexon_gen1.executive_summary.safety_agency == "Global NCAP"
    assert nexon_gen1.executive_summary.bodyshell_integrity == "Stable"


def test_executive_summary_structure(workspace_service: VehicleWorkspaceService):
    """Verifies that executive summary contains all decision anchors."""
    res = workspace_service.get_vehicle_workspace("honda::city::gen-5-2020::2021::zx")

    assert res is not None
    summary = res.executive_summary
    assert summary.carspective_score is not None
    assert summary.score_band in ["EXCELLENT", "GOOD", "FAIR", "CAUTION"]
    assert summary.estimated_fair_market_value_lakhs is not None
    assert summary.expected_fair_market_range_low_lakhs is not None
    assert summary.expected_fair_market_range_high_lakhs is not None
    assert summary.recommendation_verdict is not None
    assert summary.typical_annual_maintenance_inr is not None
    assert summary.maintenance_complexity is not None
    assert len(summary.one_line_summary) > 10


def test_workspace_api_endpoint(app_client: FlaskClient):
    """Verifies the GET /api/v1/vehicles/workspace/<path:canonical_id> REST API endpoint."""
    resp = app_client.get(
        "/api/v1/vehicles/workspace/maruti-suzuki::swift::gen-3-2018::2021::zxi?asking_price=620000&km_driven=30000"
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["canonical_vehicle_id"] == "maruti-suzuki::swift::gen-3-2018::2021::zxi"
    assert data["identity"]["brand"] == "Maruti Suzuki"
    assert data["identity"]["model"] == "Swift"
    assert data["identity_confidence"]["level"] == "exact"
    assert data["executive_summary"]["carspective_score"] is not None
    assert data["executive_summary"]["estimated_fair_market_value_lakhs"] is not None
    assert data["executive_summary"]["deal_quality"] is not None
    assert data["inspection_summary"]["total_applicable_items"] > 0
    assert "visual" in data


def test_workspace_api_404_handling(app_client: FlaskClient):
    """Verifies that requesting an invalid vehicle returns RFC 7807 404 Problem JSON."""
    resp = app_client.get("/api/v1/vehicles/workspace/nonexistent-brand::phantom-model")
    assert resp.status_code == 404
    data = resp.get_json()
    assert data["status"] == 404
    assert "Vehicle Not Found" in data["title"]


def test_workspace_slug_and_hyphen_normalization_toyota_innova_crysta(app_client: FlaskClient):
    """Verifies that 'Toyota-Innova Crysta' and 'toyota-innova-crysta' resolve correctly without 404."""
    # 1. Exact production failure case: hyphen-separated brand and spaced model
    resp = app_client.get("/api/v1/vehicles/workspace/Toyota-Innova%20Crysta")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["canonical_vehicle_id"].startswith("toyota::innova-crysta")
    assert data["identity"]["brand"] == "Toyota"
    assert data["identity"]["model"] == "Innova Crysta"
    assert data["executive_summary"]["carspective_score"] is not None

    # 2. Fully slugified format
    resp_slug = app_client.get("/api/v1/vehicles/workspace/toyota-innova-crysta")
    assert resp_slug.status_code == 200
    assert resp_slug.get_json()["identity"]["brand"] == "Toyota"

    # 3. Canonical format parity
    resp_can = app_client.get("/api/v1/vehicles/workspace/toyota::innova-crysta")
    assert resp_can.status_code == 200
    assert resp_can.get_json()["identity"]["brand"] == "Toyota"


def test_workspace_slug_popular_vehicles_normalization(app_client: FlaskClient):
    """Verifies all popular homepage vehicle slugs resolve to verified workspace payloads."""
    popular_slugs = [
        ("Honda-City", "Honda", "City"),
        ("Maruti-Swift", "Maruti Suzuki", "Swift"),
        ("Tata-Nexon", "Tata", "Nexon"),
        ("Mahindra-Thar", "Mahindra", "Thar"),
    ]
    for slug, expected_brand, expected_model in popular_slugs:
        resp = app_client.get(f"/api/v1/vehicles/workspace/{slug}")
        assert resp.status_code == 200, f"Expected 200 for slug '{slug}', got {resp.status_code}"
        data = resp.get_json()
        assert data["identity"]["brand"] == expected_brand
        assert data["identity"]["model"] == expected_model


def test_workspace_slug_invalid_vehicle_fails_closed_404(app_client: FlaskClient):
    """Verifies unverified or fake vehicles strictly fail-closed with 404 and never fabricate matches."""
    for invalid in ["Ferrari-F40", "Toyota-PhantomSupercar", "InvalidBrand-InvalidModel"]:
        resp = app_client.get(f"/api/v1/vehicles/workspace/{invalid}")
        assert resp.status_code == 404
        data = resp.get_json()
        assert data["status"] == 404
        assert "Vehicle Not Found" in data["title"]


def test_workspace_performance_sla(workspace_service: VehicleWorkspaceService):
    """Measures operational latency percentiles for the unified workspace synthesis."""
    cid = "maruti-suzuki::swift::gen-3-2018::2021::zxi"

    # Warm-up
    workspace_service.get_vehicle_workspace(cid, asking_price=650000, km_driven=35000)

    latencies = []
    for _ in range(15):
        t0 = time.perf_counter()
        workspace_service.get_vehicle_workspace(cid, asking_price=650000, km_driven=35000)
        latencies.append((time.perf_counter() - t0) * 1000.0)

    p50 = float(np.percentile(latencies, 50))
    p95 = float(np.percentile(latencies, 95))

    # All 6 domain engines synthesized in-memory
    assert p50 < 500.0, f"Workspace p50 {p50:.2f} ms exceeded 500ms budget"
    assert p95 < 1000.0, f"Workspace p95 {p95:.2f} ms exceeded 1000ms budget"


def test_workspace_valuation_deal_analyzer_consistency_honda_city(app_client: FlaskClient, workspace_service: VehicleWorkspaceService):
    """
    Regression test for Honda City valuation consistency:
    Verifies that the estimated fair market value in the primary valuation engine
    and the baseline valuation in the Deal Analyzer match exactly and reflect the
    canonical Sedan body type rather than defaulting to Hatchback.
    """
    canonical_id = "honda::city::gen-4-2014::2020"
    asking_price = 850000.0
    res = workspace_service.get_vehicle_workspace(canonical_id, asking_price=asking_price)

    assert res is not None
    assert res.identity.body_type == "Sedan"
    val_fmv = res.valuation.get("estimated_fair_market_value")
    deal_fmv = res.deal_analysis.get("valuation", {}).get("estimated_fair_market_value")
    assert val_fmv is not None
    assert deal_fmv is not None
    assert val_fmv == deal_fmv, f"Valuation FMV ({val_fmv}) does not match Deal Analyzer baseline ({deal_fmv})"

    # End-to-end HTTP API check
    resp = app_client.get(f"/api/v1/vehicles/workspace/Honda-City?asking_price=850000&year=2020")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["identity"]["body_type"] == "Sedan"
    http_val = data["valuation"]["estimated_fair_market_value"]
    http_deal = data["deal_analysis"]["valuation"]["estimated_fair_market_value"]
    assert http_val == http_deal
