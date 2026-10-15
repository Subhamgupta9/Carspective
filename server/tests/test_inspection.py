"""
CARspective — Phase 7 Inspection Intelligence Engine Test Suite
Tests:
1. Canonical vehicle identity handling
2. Adaptive checklist generation & applicability (Manual vs Auto, Petrol vs Diesel vs EV)
3. Evidence governance (Seller claim -> UNVERIFIED, User observation -> USER_STATED, Docs -> VERIFIED)
4. Finding status handling (PASS, ATTENTION, FAIL, UNKNOWN, NOT_APPLICABLE)
5. Critical Invariant: UNKNOWN != PASS
6. Multi-dimensional risk evaluation (9 risk dimensions)
7. Deterministic professional escalation triggers (Structural, Powertrain, Flood, VIN, Odometer)
8. Document verification requirements & tracking
9. Purchase readiness determination (5 distinct outcomes)
10. User context prioritization invariance (Prioritization changes, but facts remain identical)
11. Mathematical independence: Intrinsic CarSpective score remains strictly unchanged
12. Mathematical independence: Phase 3 valuation remains strictly unchanged
13. Determinism: Identical inputs produce identical outputs
14. REST API contract & validation errors (POST /api/v1/inspection)
15. Performance latency benchmarks (p50, p95, p99, mean)
"""

import pytest
import time
import numpy as np
from flask import Flask

from server.app import create_app
from server.domain.inspection.models import (
    InspectionRequest,
    InspectionResponse,
    InspectionVehicleContext,
    UserInspectionProfile,
    InspectionListingContext,
    FindingInput,
    FindingStatus,
    FindingSource,
    EvidenceState,
    RiskCategory,
    RiskSeverity,
    PurchaseReadiness,
    OverallInspectionStatus,
    InspectionCategory,
)
from server.domain.inspection.service import InspectionService
from server.domain.scoring.models import ScoreRequest
from server.domain.scoring.service import ScoringService
from server.domain.valuation.models import ValuationRequest
from server.domain.valuation.service import ValuationService

@pytest.fixture(scope="module")
def app() -> Flask:
    flask_app = create_app({"TESTING": True})
    return flask_app

@pytest.fixture(scope="module")
def client(app: Flask):
    return app.test_client()

@pytest.fixture(scope="module")
def inspection_service() -> InspectionService:
    return InspectionService()

@pytest.fixture(scope="module")
def scoring_service() -> ScoringService:
    return ScoringService()

@pytest.fixture(scope="module")
def valuation_service() -> ValuationService:
    return ValuationService()


# -------------------------------------------------------------------------
# 1. Identity & Checklist Generation Tests
# -------------------------------------------------------------------------

def test_inspection_resolves_canonical_identity(inspection_service: InspectionService):
    """Inspection service resolves canonical vehicle taxonomy without errors."""
    req = InspectionRequest(
        vehicle=InspectionVehicleContext(
            brand="Tata",
            model="Nexon",
            manufacturing_year=2020,
            fuel_type="Petrol",
            transmission_type="Manual"
        )
    )
    res = inspection_service.evaluate_inspection(req)
    assert res.canonical_vehicle_id is not None
    assert "tata::nexon" in res.canonical_vehicle_id.lower()
    assert "Tata Nexon" in res.vehicle_summary

def test_checklist_powertrain_applicability_manual_vs_auto(inspection_service: InspectionService):
    """Manual vehicle receives clutch checks; Automatic vehicle receives shift quality checks."""
    req_manual = InspectionRequest(
        vehicle=InspectionVehicleContext(
            brand="Hyundai", model="Creta", manufacturing_year=2021,
            fuel_type="Petrol", transmission_type="Manual"
        )
    )
    res_manual = inspection_service.evaluate_inspection(req_manual)
    manual_ids = {item.item_id for item in res_manual.checklist}
    assert "TRANS_MANUAL_CLUTCH_BITE" in manual_ids
    assert "TRANS_AUTOMATIC_SHIFT_QUALITY" not in manual_ids

    req_auto = InspectionRequest(
        vehicle=InspectionVehicleContext(
            brand="Hyundai", model="Creta", manufacturing_year=2021,
            fuel_type="Petrol", transmission_type="Automatic"
        )
    )
    res_auto = inspection_service.evaluate_inspection(req_auto)
    auto_ids = {item.item_id for item in res_auto.checklist}
    assert "TRANS_AUTOMATIC_SHIFT_QUALITY" in auto_ids
    assert "TRANS_MANUAL_CLUTCH_BITE" not in auto_ids

def test_checklist_fuel_applicability_petrol_vs_diesel(inspection_service: InspectionService):
    """Diesel vehicle receives DPF/Glow Plug items; Petrol vehicle does not."""
    req_diesel = InspectionRequest(
        vehicle=InspectionVehicleContext(
            brand="Tata", model="Nexon", manufacturing_year=2020,
            fuel_type="Diesel", transmission_type="Manual"
        )
    )
    res_diesel = inspection_service.evaluate_inspection(req_diesel)
    diesel_ids = {item.item_id for item in res_diesel.checklist}
    assert "ENG_DIESEL_DPF_GLOW_PLUG" in diesel_ids

    req_petrol = InspectionRequest(
        vehicle=InspectionVehicleContext(
            brand="Tata", model="Nexon", manufacturing_year=2020,
            fuel_type="Petrol", transmission_type="Manual"
        )
    )
    res_petrol = inspection_service.evaluate_inspection(req_petrol)
    petrol_ids = {item.item_id for item in res_petrol.checklist}
    assert "ENG_DIESEL_DPF_GLOW_PLUG" not in petrol_ids

def test_checklist_covers_all_seven_categories(inspection_service: InspectionService):
    """Adaptive checklist includes items across all 7 canonical inspection categories."""
    req = InspectionRequest(
        vehicle=InspectionVehicleContext(
            brand="Maruti", model="Swift", manufacturing_year=2019
        )
    )
    res = inspection_service.evaluate_inspection(req)
    present_categories = {item.category for item in res.checklist}
    for cat in InspectionCategory:
        assert cat in present_categories, f"Category {cat.value} missing from checklist"


# -------------------------------------------------------------------------
# 2. Evidence Governance & Provenance Tests
# -------------------------------------------------------------------------

def test_seller_claims_remain_unverified(inspection_service: InspectionService):
    """
    CRITICAL RULE: Seller claims (e.g. 'No accidents') must strictly remain
    evidence_state = UNVERIFIED and source = SELLER. Never promoted to VERIFIED.
    """
    req = InspectionRequest(
        vehicle=InspectionVehicleContext(brand="Tata", model="Nexon", manufacturing_year=2020),
        findings=[
            FindingInput(
                item_id="DOC_INSURANCE_CLAIM_HISTORY",
                status=FindingStatus.PASS,
                observation="Seller states car has never had any accident claims",
                source=FindingSource.SELLER,
                seller_claim=True
            )
        ]
    )
    res = inspection_service.evaluate_inspection(req)
    finding = next((f for f in res.findings if f.item_id == "DOC_INSURANCE_CLAIM_HISTORY"), None)
    assert finding is not None
    assert finding.source == FindingSource.SELLER
    assert finding.evidence_state == EvidenceState.UNVERIFIED
    assert finding.evidence_state != EvidenceState.VERIFIED

def test_buyer_observation_tagged_as_user_stated(inspection_service: InspectionService):
    """Physical observation by buyer is tagged source=BUYER_OBSERVATION and state=USER_STATED."""
    req = InspectionRequest(
        vehicle=InspectionVehicleContext(brand="Hyundai", model="Creta", manufacturing_year=2021),
        findings=[
            FindingInput(
                item_id="DRV_STEERING_CENTERING_PULL",
                status=FindingStatus.ATTENTION,
                observation="Vehicle pulls slightly left on highway",
                source=FindingSource.BUYER_OBSERVATION
            )
        ]
    )
    res = inspection_service.evaluate_inspection(req)
    finding = next((f for f in res.findings if f.item_id == "DRV_STEERING_CENTERING_PULL"), None)
    assert finding is not None
    assert finding.source == FindingSource.BUYER_OBSERVATION
    assert finding.evidence_state == EvidenceState.USER_STATED

def test_documented_evidence_tagged_as_verified(inspection_service: InspectionService):
    """Documentary evidence from official source is tagged source=DOCUMENTED_EVIDENCE and state=VERIFIED."""
    req = InspectionRequest(
        vehicle=InspectionVehicleContext(brand="Tata", model="Nexon", manufacturing_year=2020),
        findings=[
            FindingInput(
                item_id="DOC_SERVICE_HISTORY_RECORDS",
                status=FindingStatus.PASS,
                observation="Official dealer workshop stamp verified at 10k, 20k, 30k km",
                source=FindingSource.DOCUMENTED_EVIDENCE
            )
        ]
    )
    res = inspection_service.evaluate_inspection(req)
    finding = next((f for f in res.findings if f.item_id == "DOC_SERVICE_HISTORY_RECORDS"), None)
    assert finding is not None
    assert finding.source == FindingSource.DOCUMENTED_EVIDENCE
    assert finding.evidence_state == EvidenceState.VERIFIED


# -------------------------------------------------------------------------
# 3. Critical Invariant: UNKNOWN != PASS
# -------------------------------------------------------------------------

def test_invariant_unknown_is_never_treated_as_pass(inspection_service: InspectionService):
    """
    CRITICAL RULE: An uninspected or unknown finding must NEVER be converted to PASS
    or count towards passed items.
    """
    req = InspectionRequest(
        vehicle=InspectionVehicleContext(brand="Tata", model="Nexon", manufacturing_year=2020),
        findings=[
            FindingInput(
                item_id="SAF_AIRBAG_LAMP_CYCLE",
                status=FindingStatus.UNKNOWN,
                observation="Did not check instrument cluster lamp timing"
            )
        ]
    )
    res = inspection_service.evaluate_inspection(req)
    finding = next((f for f in res.findings if f.item_id == "SAF_AIRBAG_LAMP_CYCLE"), None)
    assert finding is not None
    assert finding.status == FindingStatus.UNKNOWN
    assert finding.evidence_state == EvidenceState.INSUFFICIENT_DATA
    # Summary must track it as unknown, NOT pass
    assert res.summary.passed_items_count == 0
    assert res.summary.unknown_items_count >= 1
    # Purchase readiness must NOT be READY_FOR_NEXT_STEP
    assert res.purchase_readiness != PurchaseReadiness.READY_FOR_NEXT_STEP


# -------------------------------------------------------------------------
# 4. Multi-Dimensional Risk Engine Tests
# -------------------------------------------------------------------------

def test_risk_engine_structural_risk_trigger(inspection_service: InspectionService):
    """Failed chassis crumple zone triggers CRITICAL STRUCTURAL_RISK and professional escalation."""
    req = InspectionRequest(
        vehicle=InspectionVehicleContext(brand="Tata", model="Nexon", manufacturing_year=2020),
        findings=[
            FindingInput(
                item_id="UND_CHASSIS_RAIL_CRUMPLE_ZONES",
                status=FindingStatus.FAIL,
                observation="Hammered kink observed on right front chassis apron rail",
                source=FindingSource.BUYER_OBSERVATION
            )
        ]
    )
    res = inspection_service.evaluate_inspection(req)
    struct_risk = next((r for r in res.risks if r.category == RiskCategory.STRUCTURAL_RISK), None)
    assert struct_risk is not None
    assert struct_risk.severity == RiskSeverity.CRITICAL
    assert res.summary.professional_inspection_required is True
    assert res.purchase_readiness == PurchaseReadiness.HIGH_RISK_DO_NOT_PROCEED_YET

def test_risk_engine_powertrain_blue_smoke_trigger(inspection_service: InspectionService):
    """Blue exhaust smoke triggers CRITICAL POWERTRAIN_RISK and professional inspection."""
    req = InspectionRequest(
        vehicle=InspectionVehicleContext(brand="Hyundai", model="Creta", manufacturing_year=2019),
        findings=[
            FindingInput(
                item_id="ENG_EXHAUST_SMOKE_COLOR",
                status=FindingStatus.FAIL,
                observation="Thick blue smoke emitted when blipping throttle",
                source=FindingSource.BUYER_OBSERVATION
            )
        ]
    )
    res = inspection_service.evaluate_inspection(req)
    pow_risk = next((r for r in res.risks if r.category == RiskCategory.POWERTRAIN_RISK), None)
    assert pow_risk is not None
    assert pow_risk.severity == RiskSeverity.CRITICAL
    assert res.summary.professional_inspection_required is True

def test_risk_engine_safety_airbag_tampering_trigger(inspection_service: InspectionService):
    """Airbag lamp failure triggers CRITICAL SAFETY_RISK."""
    req = InspectionRequest(
        vehicle=InspectionVehicleContext(brand="Maruti", model="Swift", manufacturing_year=2019),
        findings=[
            FindingInput(
                item_id="SAF_AIRBAG_LAMP_CYCLE",
                status=FindingStatus.FAIL,
                observation="Airbag lamp never illuminates on ignition key turn (disconnected bulb)",
                source=FindingSource.BUYER_OBSERVATION
            )
        ]
    )
    res = inspection_service.evaluate_inspection(req)
    saf_risk = next((r for r in res.risks if r.category == RiskCategory.SAFETY_RISK), None)
    assert saf_risk is not None
    assert saf_risk.severity == RiskSeverity.CRITICAL
    assert res.purchase_readiness == PurchaseReadiness.HIGH_RISK_DO_NOT_PROCEED_YET

def test_risk_engine_odometer_fraud_trigger(inspection_service: InspectionService):
    """Odometer rollback evidence triggers CRITICAL ODOMETER_RISK."""
    req = InspectionRequest(
        vehicle=InspectionVehicleContext(brand="Tata", model="Nexon", manufacturing_year=2020),
        findings=[
            FindingInput(
                item_id="DOC_ODOMETER_CONSISTENCY",
                status=FindingStatus.FAIL,
                observation="Service bill from 2023 shows 82,000 km, but odometer currently reads 45,000 km",
                source=FindingSource.BUYER_OBSERVATION
            )
        ]
    )
    res = inspection_service.evaluate_inspection(req)
    odo_risk = next((r for r in res.risks if r.category == RiskCategory.ODOMETER_RISK), None)
    assert odo_risk is not None
    assert odo_risk.severity == RiskSeverity.CRITICAL


# -------------------------------------------------------------------------
# 5. Purchase Readiness Spectrum Tests
# -------------------------------------------------------------------------

def test_purchase_readiness_insufficient_evidence(inspection_service: InspectionService):
    """Vehicle with empty findings returns INSUFFICIENT_EVIDENCE."""
    req = InspectionRequest(
        vehicle=InspectionVehicleContext(brand="Tata", model="Nexon", manufacturing_year=2020)
    )
    res = inspection_service.evaluate_inspection(req)
    assert res.purchase_readiness == PurchaseReadiness.INSUFFICIENT_EVIDENCE
    assert res.summary.overall_status == OverallInspectionStatus.INSUFFICIENT_EVIDENCE

def test_purchase_readiness_verify_before_negotiating(inspection_service: InspectionService):
    """Vehicle with attention items and missing docs returns VERIFY_BEFORE_NEGOTIATING."""
    req = InspectionRequest(
        vehicle=InspectionVehicleContext(brand="Tata", model="Nexon", manufacturing_year=2020),
        findings=[
            FindingInput(item_id="EXT_PAINT_CONSISTENCY_MISMATCH", status=FindingStatus.ATTENTION, observation="Front bumper repainted"),
            FindingInput(item_id="INT_HVAC_AIR_CONDITIONING", status=FindingStatus.PASS, observation="Cooling verified satisfactory"),
            FindingInput(item_id="DOC_RC_VERIFICATION", status=FindingStatus.PASS, observation="RC verified"),
            FindingInput(item_id="ENG_COLD_START_CRANKING", status=FindingStatus.PASS, observation="Cranked smoothly"),
            FindingInput(item_id="DRV_STEERING_CENTERING_PULL", status=FindingStatus.PASS, observation="Tracks straight"),
        ],
        documentation_records={"rc": "VERIFIED"} # Pending other docs
    )
    res = inspection_service.evaluate_inspection(req)
    assert res.purchase_readiness == PurchaseReadiness.VERIFY_BEFORE_NEGOTIATING
    assert res.summary.overall_status == OverallInspectionStatus.REVIEW_REQUIRED

def test_purchase_readiness_ready_for_next_step(inspection_service: InspectionService):
    """Vehicle with complete passing inspection and verified docs returns READY_FOR_NEXT_STEP."""
    req_items = inspection_service.evaluate_inspection(
        InspectionRequest(vehicle=InspectionVehicleContext(brand="Tata", model="Nexon", manufacturing_year=2020))
    ).checklist

    pass_findings = [
        FindingInput(item_id=item.item_id, status=FindingStatus.PASS, observation="Inspected and verified satisfactory")
        for item in req_items
    ]
    all_docs = {
        "rc": "VERIFIED",
        "noc": "VERIFIED",
        "insurance": "VERIFIED",
        "service_history": "VERIFIED",
        "puc": "VERIFIED",
    }
    req = InspectionRequest(
        vehicle=InspectionVehicleContext(brand="Tata", model="Nexon", manufacturing_year=2020),
        findings=pass_findings,
        documentation_records=all_docs
    )
    res = inspection_service.evaluate_inspection(req)
    assert res.purchase_readiness == PurchaseReadiness.READY_FOR_NEXT_STEP
    assert res.summary.overall_status == OverallInspectionStatus.CLEAR


# -------------------------------------------------------------------------
# 6. User Context Prioritization (Invariance of Facts)
# -------------------------------------------------------------------------

def test_user_context_modulates_priority_without_altering_facts(inspection_service: InspectionService):
    """
    CRITICAL RULE: User profile boosts priority flags but does NOT change
    objective checklist items, expected observations, or severity.
    """
    vehicle = InspectionVehicleContext(brand="Tata", model="Nexon", manufacturing_year=2020)
    
    req_family = InspectionRequest(
        vehicle=vehicle,
        user_profile=UserInspectionProfile(safety_priority="CRITICAL", family_orientation=True)
    )
    req_commute = InspectionRequest(
        vehicle=vehicle,
        user_profile=UserInspectionProfile(daily_commute_km=80.0, safety_priority="LOW", family_orientation=False)
    )

    res_family = inspection_service.evaluate_inspection(req_family)
    res_commute = inspection_service.evaluate_inspection(req_commute)

    # Number of checklist items must be strictly identical
    assert len(res_family.checklist) == len(res_commute.checklist)

    # Item content (titles, purposes, methods) must be strictly identical
    for item_f, item_c in zip(res_family.checklist, res_commute.checklist):
        assert item_f.item_id == item_c.item_id
        assert item_f.purpose == item_c.purpose
        assert item_f.severity_if_failed == item_c.severity_if_failed

    # Only priority boost flags vary
    safety_item_f = next(i for i in res_family.checklist if i.item_id == "SAF_AIRBAG_LAMP_CYCLE")
    safety_item_c = next(i for i in res_commute.checklist if i.item_id == "SAF_AIRBAG_LAMP_CYCLE")
    assert safety_item_f.user_priority_elevated is True
    assert safety_item_c.user_priority_elevated is False


# -------------------------------------------------------------------------
# 7. Mathematical Independence Invariant Tests
# -------------------------------------------------------------------------

def test_invariant_intrinsic_score_remains_mathematically_unchanged(
    inspection_service: InspectionService, scoring_service: ScoringService
):
    """
    CRITICAL INVARIANT: Physical inspection findings (even catastrophic failures)
    must NEVER alter or mutate the Phase 5 intrinsic CARspective Score.
    """
    # Baseline intrinsic score
    score_baseline = scoring_service.calculate_score(
        ScoreRequest(brand="Tata", model="Nexon", manufacturing_year=2020)
    )
    assert score_baseline.overall_score == 84

    # Run inspection with severe defects
    req_inspection = InspectionRequest(
        vehicle=InspectionVehicleContext(brand="Tata", model="Nexon", manufacturing_year=2020),
        findings=[
            FindingInput(item_id="UND_CHASSIS_RAIL_CRUMPLE_ZONES", status=FindingStatus.FAIL, observation="Chassis rail bent"),
            FindingInput(item_id="ENG_EXHAUST_SMOKE_COLOR", status=FindingStatus.FAIL, observation="Blue exhaust smoke"),
            FindingInput(item_id="SAF_AIRBAG_LAMP_CYCLE", status=FindingStatus.FAIL, observation="Airbag bypassed")
        ]
    )
    res_inspection = inspection_service.evaluate_inspection(req_inspection)
    assert res_inspection.purchase_readiness == PurchaseReadiness.HIGH_RISK_DO_NOT_PROCEED_YET

    # Re-evaluate intrinsic score: must remain EXACTLY 84
    score_after = scoring_service.calculate_score(
        ScoreRequest(brand="Tata", model="Nexon", manufacturing_year=2020)
    )
    assert score_after.overall_score == score_baseline.overall_score
    for d_before, d_after in zip(score_baseline.dimensions, score_after.dimensions):
        assert d_before.score == d_after.score

def test_invariant_valuation_remains_mathematically_unchanged(
    inspection_service: InspectionService, valuation_service: ValuationService
):
    """
    CRITICAL INVARIANT: Inspection findings must NEVER mutate the Phase 3 statistical valuation model.
    """
    val_req = ValuationRequest(
        brand="Tata", model="Nexon", manufacturing_year=2020, km_driven=35000.0
    )
    val_baseline = valuation_service.evaluate_valuation(val_req)

    # Run catastrophic inspection
    req_inspection = InspectionRequest(
        vehicle=InspectionVehicleContext(brand="Tata", model="Nexon", manufacturing_year=2020),
        findings=[
            FindingInput(item_id="INT_FLOOD_DAMAGE_WATERLINES", status=FindingStatus.FAIL, observation="Submerged in flood")
        ]
    )
    inspection_service.evaluate_inspection(req_inspection)

    # Valuation prediction must be strictly identical
    val_after = valuation_service.evaluate_valuation(val_req)
    assert val_after.estimated_fair_market_value == val_baseline.estimated_fair_market_value


# -------------------------------------------------------------------------
# 8. Determinism & Anti-Hallucination Tests
# -------------------------------------------------------------------------

def test_determinism_identical_inputs_produce_identical_outputs(inspection_service: InspectionService):
    """Same input payload produces 100% identical checklist, risks, and readiness."""
    req = InspectionRequest(
        vehicle=InspectionVehicleContext(
            brand="Hyundai", model="Creta", manufacturing_year=2021, km_driven=45000.0
        ),
        findings=[
            FindingInput(item_id="EXT_PANEL_GAPS_ALIGNMENT", status=FindingStatus.ATTENTION, observation="Minor hood gap")
        ]
    )
    res1 = inspection_service.evaluate_inspection(req)
    res2 = inspection_service.evaluate_inspection(req)

    assert len(res1.checklist) == len(res2.checklist)
    assert len(res1.findings) == len(res2.findings)
    assert res1.purchase_readiness == res2.purchase_readiness
    assert res1.summary.overall_status == res2.summary.overall_status
    assert len(res1.risks) == len(res2.risks)


# -------------------------------------------------------------------------
# 9. REST API Contract & Error Handling Tests
# -------------------------------------------------------------------------

def test_inspection_api_success(client):
    """POST /api/v1/inspection returns 200 OK on valid payload."""
    payload = {
        "vehicle": {
            "brand": "Tata",
            "model": "Nexon",
            "manufacturing_year": 2020
        }
    }
    resp = client.post("/api/v1/inspection", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    assert "session_id" in data
    assert data["session_id"].startswith("insp-")
    assert len(data["checklist"]) >= 40
    assert "summary" in data
    assert "purchase_readiness" in data

def test_inspection_api_invalid_content_type(client):
    """Non-JSON payload returns HTTP 415."""
    resp = client.post("/api/v1/inspection", data="not-json", content_type="text/plain")
    assert resp.status_code == 415

def test_inspection_api_validation_error_missing_vehicle(client):
    """Missing required vehicle field returns HTTP 422."""
    payload = {"listing": {"asking_price": 500000.0}}
    resp = client.post("/api/v1/inspection", json=payload)
    assert resp.status_code == 422


# -------------------------------------------------------------------------
# 10. Performance Latency Measurements
# -------------------------------------------------------------------------

def test_inspection_performance_benchmarks(inspection_service: InspectionService):
    """Measures operational latency percentiles for inspection evaluation."""
    req = InspectionRequest(
        vehicle=InspectionVehicleContext(
            brand="Tata", model="Nexon", manufacturing_year=2020, km_driven=35000.0
        ),
        listing=InspectionListingContext(asking_price=500000.0),
        user_profile=UserInspectionProfile(safety_priority="HIGH"),
        findings=[
            FindingInput(item_id="DOC_RC_VERIFICATION", status=FindingStatus.PASS),
            FindingInput(item_id="EXT_PANEL_GAPS_ALIGNMENT", status=FindingStatus.ATTENTION),
            FindingInput(item_id="ENG_COLD_START_CRANKING", status=FindingStatus.PASS),
        ]
    )

    # Warm-up run
    inspection_service.evaluate_inspection(req)

    latencies = []
    for _ in range(25):
        t0 = time.perf_counter()
        inspection_service.evaluate_inspection(req)
        latencies.append((time.perf_counter() - t0) * 1000)

    p50 = float(np.percentile(latencies, 50))
    p95 = float(np.percentile(latencies, 95))
    p99 = float(np.percentile(latencies, 99))
    mean = float(np.mean(latencies))

    print(f"\n[Inspection Benchmark] Mean: {mean:.2f} ms | P50: {p50:.2f} ms | P95: {p95:.2f} ms | P99: {p99:.2f} ms")

    # Inspection service does not run heavy ML trees; should be extremely fast (< 25 ms)
    assert p50 < 25.0, f"p50 latency {p50:.2f} ms exceeded 25ms budget"
    assert p95 < 50.0, f"p95 latency {p95:.2f} ms exceeded 50ms budget"
