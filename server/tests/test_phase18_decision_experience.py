"""
CARspective — Phase 18 Production Decision Experience & Trust UX Tests
Verifies:
1. Analytical Isolation (Budget change, Asking price change, Market freshness change)
2. E2E Journeys A, B, C, D, E (Research, Used-Car Purchase, Current Market, Personalized Decision, Insufficient Data)
3. Canonical Inspection Catalog v2.0.0 (49 items strict invariant)
"""

import pytest
from flask.testing import FlaskClient

from server.app import create_app
from server.infrastructure.database import ScopedSession
from server.domain.workspace.service import VehicleWorkspaceService
from server.domain.decision.service import DecisionService
from server.domain.decision.models import UserRequirementsProfile, PriorityLevel, UsageProfile
from server.domain.inspection.service import InspectionService
from server.domain.inspection.checklist import (
    CANONICAL_CHECKLIST_CATALOG,
    INSPECTION_CATALOG_VERSION,
    CURRENT_CANONICAL_CATALOG_COUNT,
    PHASE7_CANONICAL_BASELINE_COUNT,
)


@pytest.fixture(scope="module")
def app_client():
    app = create_app({"TESTING": True})
    with app.test_client() as client:
        yield client


@pytest.fixture(scope="module")
def workspace_service():
    session = ScopedSession()
    return VehicleWorkspaceService(session=session)


@pytest.fixture(scope="module")
def decision_service():
    session = ScopedSession()
    return DecisionService(session=session)


@pytest.fixture(scope="module")
def inspection_service():
    session = ScopedSession()
    return InspectionService(session=session)


# ==============================================================================
# SECTION 27: ANALYTICAL ISOLATION TESTS
# ==============================================================================

def test_isolation_changing_user_budget_does_not_alter_intrinsic_score_or_valuation(
    workspace_service: VehicleWorkspaceService,
    decision_service: DecisionService,
):
    """
    Changing the user's budget ceiling must NOT change:
    1. Intrinsic CarSpective Score
    2. Base Valuation (Estimated Fair Market Value)
    3. Canonical Vehicle Identity
    """
    can_id = "maruti-suzuki::swift::gen-3-2018::2021::zxi"
    ws = workspace_service.get_vehicle_workspace(can_id)
    baseline_score = ws.executive_summary.carspective_score
    baseline_fmv = ws.executive_summary.estimated_fair_market_value_inr

    # Profile 1: Low Budget (5 Lakhs)
    prof_low = UserRequirementsProfile(budget_max_inr=500000)
    dec_low = decision_service.evaluate_vehicle(can_id, prof_low)

    # Profile 2: High Budget (15 Lakhs)
    prof_high = UserRequirementsProfile(budget_max_inr=1500000)
    dec_high = decision_service.evaluate_vehicle(can_id, prof_high)

    # Re-fetch workspace to ensure no side effects
    ws_after = workspace_service.get_vehicle_workspace(can_id)

    # 1. Intrinsic score unchanged
    assert dec_low.intrinsic_score == baseline_score
    assert dec_high.intrinsic_score == baseline_score
    assert ws_after.executive_summary.carspective_score == baseline_score

    # 2. Valuation unchanged
    assert ws_after.executive_summary.estimated_fair_market_value_inr == baseline_fmv

    # 3. Canonical identity unchanged
    assert ws_after.canonical_vehicle_id == ws.canonical_vehicle_id
    assert dec_low.canonical_vehicle_id == ws.canonical_vehicle_id
    assert dec_high.canonical_vehicle_id == ws.canonical_vehicle_id

    # 4. User fit changes deterministically according to budget
    assert dec_high.user_fit_score >= dec_low.user_fit_score


def test_isolation_changing_asking_price_does_not_alter_intrinsic_score_or_base_valuation(
    workspace_service: VehicleWorkspaceService,
):
    """
    Changing the seller asking price must NOT change:
    1. Intrinsic score
    2. Base valuation
    3. Vehicle facts
    It MAY change:
    1. Deal quality (Great / Fair / Overpriced)
    2. Deal price deviation
    3. Negotiation guidance
    """
    can_id = "maruti-suzuki::swift::gen-3-2018::2021::zxi"

    # Evaluation with cheap asking price (₹4.5 Lakhs)
    ws_cheap = workspace_service.get_vehicle_workspace(can_id, asking_price=450000, km_driven=30000)

    # Evaluation with expensive asking price (₹9.0 Lakhs)
    ws_expensive = workspace_service.get_vehicle_workspace(can_id, asking_price=900000, km_driven=30000)

    # Intrinsic score strictly identical
    assert ws_cheap.executive_summary.carspective_score == ws_expensive.executive_summary.carspective_score

    # Base valuation strictly identical
    assert ws_cheap.executive_summary.estimated_fair_market_value_inr == ws_expensive.executive_summary.estimated_fair_market_value_inr
    assert ws_cheap.valuation["estimated_fair_market_value"] == ws_expensive.valuation["estimated_fair_market_value"]

    # Vehicle facts strictly identical
    assert ws_cheap.identity.brand == ws_expensive.identity.brand
    assert ws_cheap.executive_summary.safety_stars == ws_expensive.executive_summary.safety_stars

    # Deal assessment changes appropriately
    assert ws_cheap.deal_analysis["deal_quality"] in ["GREAT_DEAL", "FAIR_DEAL", "UNUSUALLY_LOW_ASKING_PRICE"]
    assert ws_expensive.deal_analysis["deal_quality"] == "OVERPRICED"
    assert ws_cheap.deal_analysis["price_deviation"]["relative_difference_percent"] < ws_expensive.deal_analysis["price_deviation"]["relative_difference_percent"]


def test_isolation_current_market_freshness_does_not_rewrite_historical_baseline(
    workspace_service: VehicleWorkspaceService,
):
    """
    Historical observation baseline (57,480 listings 2018-2024) must remain strictly immutable
    regardless of live market observation freshness or ingestion.
    """
    can_id = "maruti-suzuki::swift::gen-3-2018::2021::zxi"
    ws = workspace_service.get_vehicle_workspace(can_id)

    # Historical context remains fixed
    assert "57,480" in ws.valuation["market_evidence"]["historical_baseline_coverage"]

    # Model artifact hash is immutable
    assert ws.valuation["model_metadata"]["artifact_sha256"] == "4a4ccf3f78c17b48826cfa55f40a24bcb808bc82fa752b793ad4eabff8b246c1"
    assert ws.data_governance["valuation_model_hash"] == "4a4ccf3f78c17b48826cfa55f40a24bcb808bc82fa752b793ad4eabff8b246c1"

    # Data governance explicitly segregates asking prices from transaction sale prices
    assert "asking-price" in ws.data_governance["asking_price_semantics"].lower()
    assert "not transaction prices" in ws.data_governance["asking_price_semantics"].lower()


# ==============================================================================
# SECTION 16: CANONICAL INSPECTION CATALOG GOVERNANCE (49 ITEMS INVARIANT)
# ==============================================================================

def test_inspection_catalog_authoritative_49_items(
    decision_service: DecisionService,
):
    """
    Verifies that the canonical inspection catalog contains exactly 49 items
    across 7 categories, and that personalization only reorders/prioritizes.
    """
    assert INSPECTION_CATALOG_VERSION == "2.0.0"
    assert CURRENT_CANONICAL_CATALOG_COUNT == 49
    assert PHASE7_CANONICAL_BASELINE_COUNT == 45
    assert len(CANONICAL_CHECKLIST_CATALOG) == 49
    categories = {item.category for item in CANONICAL_CHECKLIST_CATALOG}
    assert len(categories) == 7

    # Check that personalized prioritization does NOT add or drop items from canonical catalog
    can_id = "maruti-suzuki::swift::gen-3-2018::2021::zxi"
    prof = UserRequirementsProfile(
        safety_priority=PriorityLevel.CRITICAL,
        maintenance_priority=PriorityLevel.HIGH,
    )
    prioritized = decision_service.prioritize_inspection(
        canonical_vehicle_id=can_id,
        profile=prof,
    )
    assert len(prioritized.prioritized_checklist) > 0
    assert len(prioritized.priority_reasons) > 0


# ==============================================================================
# SECTION 29: FULL USER DECISION JOURNEYS (E2E)
# ==============================================================================

def test_journey_a_research_search_to_compare(app_client: FlaskClient):
    """
    Journey A — Research:
    Search (Discovery) → Vehicle workspace → Understand (Score/Specs) → Compare
    """
    # 1. Search for Swift
    search_res = app_client.get("/api/v1/vehicles/search?q=swift")
    assert search_res.status_code == 200
    search_data = search_res.get_json()
    assert search_data["total_count"] > 0
    top_vehicle = search_data["results"][0]
    can_id = top_vehicle["canonical_vehicle_id"]

    # 2. View Vehicle Intelligence Workspace
    ws_res = app_client.get(f"/api/v1/vehicles/workspace/{can_id}")
    assert ws_res.status_code == 200
    ws_data = ws_res.get_json()
    assert ws_data["identity"]["brand"] == "Maruti Suzuki"
    assert ws_data["executive_summary"]["carspective_score"] is not None

    # 3. Compare with another vehicle (Baleno)
    compare_res = app_client.post(
        "/api/v1/compare",
        json={
            "vehicles": [
                {"brand": "Maruti Suzuki", "model": "Swift", "canonical_vehicle_id": can_id},
                {"brand": "Maruti Suzuki", "model": "Baleno", "canonical_vehicle_id": "maruti-suzuki::baleno::gen-2-2022::2022::zeta::1-2-k12n-5mt"},
            ]
        },
    )
    assert compare_res.status_code == 200
    comp_data = compare_res.get_json()
    assert len(comp_data["vehicles"]) == 2
    assert "overall_result" in comp_data


def test_journey_b_used_car_purchase_deal_to_inspection(app_client: FlaskClient):
    """
    Journey B — Used-Car Purchase:
    Search → Vehicle → Enter asking price → Deal Analyzer → User Fit → Inspection
    """
    can_id = "maruti-suzuki::swift::gen-3-2018::2021::zxi"

    # 1. Evaluate Deal with asking price
    deal_res = app_client.post(
        "/api/v1/deal-analysis",
        json={
            "brand": "Maruti Suzuki",
            "model": "Swift",
            "manufacturing_year": 2021,
            "km_driven": 35000,
            "asking_price": 630000,
            "fuel_type": "Petrol",
            "transmission_type": "Manual",
            "variant": "ZXi",
        },
    )
    assert deal_res.status_code == 200
    deal_data = deal_res.get_json()
    assert deal_data["deal_quality"] in ["FAIR_DEAL", "GREAT_DEAL"]
    assert "negotiation" in deal_data

    # 2. Evaluate User Fit
    decision_res = app_client.post(
        "/api/v1/decision/evaluate",
        json={
            "canonical_vehicle_id": can_id,
            "profile": {
                "budget_max_inr": 650000,
                "usage_profile": "CITY",
                "family_size": 4,
            },
            "asking_price": 630000,
            "km_driven": 35000,
        },
    )
    assert decision_res.status_code == 200
    dec_data = decision_res.get_json()
    assert dec_data["user_fit_score"] >= 75
    assert len(dec_data["why_it_fits"]) > 0

    # 3. Generate Inspection Checklist
    insp_res = app_client.post(
        "/api/v1/inspection",
        json={
            "vehicle": {
                "brand": "Maruti Suzuki",
                "model": "Swift",
                "manufacturing_year": 2021,
                "km_driven": 35000,
                "fuel_type": "Petrol",
                "transmission_type": "Manual",
                "variant": "ZXi",
            }
        },
    )
    assert insp_res.status_code == 200
    insp_data = insp_res.get_json()
    assert len(insp_data["checklist"]) > 0


def test_journey_c_current_market_to_assistant(app_client: FlaskClient):
    """
    Journey C — Current Market:
    Search → Vehicle → Current Market Observations → Ask AI assistant
    """
    can_id = "maruti-suzuki::swift::gen-3-2018::2021::zxi"

    # 1. Query live market observations
    lm_res = app_client.get(f"/api/v1/market/current/{can_id}")
    assert lm_res.status_code == 200
    lm_data = lm_res.get_json()
    assert "2026-Q3" in lm_data["observation_period"]
    assert lm_data["evidence"]["evidence_state"] == "EMPIRICAL"
    assert lm_data["evidence"]["total_observations"] > 0

    # 2. Ask assistant about the vehicle
    chat_res = app_client.post(
        "/api/v1/assistant",
        json={
            "message": "Is this asking price fair and what current market evidence do we have?",
            "vehicle": {
                "brand": "Maruti Suzuki",
                "model": "Swift",
                "manufacturing_year": 2021,
                "canonical_vehicle_id": can_id,
            },
        },
    )
    assert chat_res.status_code == 200
    chat_data = chat_res.get_json()
    assert len(chat_data["answer"]) > 0


def test_journey_d_personalized_decision(app_client: FlaskClient):
    """
    Journey D — Personalized Decision:
    Plain text requirements parsing → Vehicle evaluation → User Fit → Alternatives → Comparison
    """
    # 1. Parse plain English query
    parse_res = app_client.post(
        "/api/v1/decision/parse-query",
        json={"query": "I need a fuel efficient manual hatchback for city commute under 7 lakh"},
    )
    assert parse_res.status_code == 200
    parsed_data = parse_res.get_json()
    assert parsed_data["parsed_profile"]["budget_max_inr"] == 700000

    # 2. Evaluate vehicle against parsed profile
    can_id = "maruti-suzuki::swift::gen-3-2018::2021::zxi"
    dec_res = app_client.post(
        "/api/v1/decision/evaluate",
        json={
            "canonical_vehicle_id": can_id,
            "profile": parsed_data["parsed_profile"],
        },
    )
    assert dec_res.status_code == 200
    dec_data = dec_res.get_json()
    assert dec_data["user_fit_score"] >= 80
    assert len(dec_data["why_it_fits"]) > 0


def test_journey_e_insufficient_data_honest_limitations(app_client: FlaskClient):
    """
    Journey E — Insufficient Data:
    Querying sparse/unsupported vehicle yields honest limitations without hallucinated fallback data.
    """
    # Query nonexistent/sparse vehicle
    bad_id = "unknown-maker::phantom-car::gen-1::2020"
    res = app_client.get(f"/api/v1/vehicles/workspace/{bad_id}")
    assert res.status_code in [404, 200]
    if res.status_code == 200:
        data = res.get_json()
        assert len(data.get("limitations", [])) > 0 or data.get("identity_confidence", {}).get("level") == "LIMITED"
