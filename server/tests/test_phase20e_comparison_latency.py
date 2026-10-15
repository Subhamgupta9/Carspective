"""
CARspective — Phase 20E Targeted Comparison Latency Remediation Tests
Verifies:
1. Targeted specification retrieval in KnowledgeService (only specs/dims/safety).
2. Canonical taxonomy resolution reuse across Scoring, Valuation, and Comparison.
3. Query count reduction (under 25 queries for a 2-vehicle comparison, down from 36-44).
4. Unchanged semantic equivalence for vehicle specifications, scoring, and valuation.
5. Graceful handling of missing or partial vehicle specifications (e.g. i20).
6. Multi-threaded session concurrency and safety during comparison execution.
"""

import os
import pytest
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import event

from server.infrastructure.database import ScopedSession
from server.domain.knowledge.service import KnowledgeService
from server.domain.scoring.service import ScoringService
from server.domain.scoring.models import ScoreRequest
from server.domain.valuation.service import ValuationService
from server.domain.valuation.models import ValuationRequest
from server.domain.comparison.service import ComparisonService, SPEC_DEFINITIONS
from server.domain.comparison.models import ComparisonRequest, ComparisonVehicle, EvidenceState
from server.schemas.taxonomy import CanonicalResolutionRequest, CanonicalResolutionResult, ResolutionStatus


@pytest.fixture(scope="module")
def db_session():
    session = ScopedSession()
    yield session
    session.close()


def test_targeted_specifications_retrieval(db_session):
    """KnowledgeService.get_comparison_specifications retrieves only specs, dims, safety."""
    ks = KnowledgeService(session=db_session)
    can_id = "maruti-suzuki::swift::gen-3-2018::2021"

    specs_data = ks.get_comparison_specifications(can_id)
    assert specs_data is not None
    assert "specifications" in specs_data
    assert "dimensions" in specs_data
    assert "safety" in specs_data

    # Check that data is accurately populated
    spec = specs_data["specifications"]
    assert spec is not None
    assert spec.displacement_cc == 1197
    assert spec.fuel_type == "Petrol"

    dim = specs_data["dimensions"]
    assert dim is not None
    assert dim.length_mm == 3845

    safety = specs_data["safety"]
    assert safety is not None
    assert safety.adult_stars == 2


def test_targeted_specifications_missing_data(db_session):
    """KnowledgeService.get_comparison_specifications handles missing/partial vehicles honestly."""
    ks = KnowledgeService(session=db_session)
    can_id = "hyundai::i20"

    specs_data = ks.get_comparison_specifications(can_id)
    assert specs_data is not None
    # i20 has no specs, dimensions, or safety rows in knowledge tables
    assert specs_data["specifications"] is None
    assert specs_data["dimensions"] is None
    assert specs_data["safety"] is None


def test_taxonomy_resolution_reuse_in_scoring(db_session):
    """ScoringService uses pre-resolved taxonomy when provided."""
    scoring = ScoringService(session=db_session)
    req = ScoreRequest(brand="Maruti", model="Swift", manufacturing_year=2021)

    # Resolve taxonomy beforehand
    tax_req = CanonicalResolutionRequest(brand="Maruti", model="Swift", year=2021)
    resolved = scoring.taxonomy_resolver.resolve(tax_req)
    assert resolved.canonical_vehicle_id.startswith("maruti-suzuki::swift::gen-3-2018::2021")

    # Pass pre-resolved taxonomy
    resp = scoring.calculate_score(req, resolved_taxonomy=resolved)
    assert resp.canonical_vehicle_id == resolved.canonical_vehicle_id
    assert resp.overall_score > 0


def test_taxonomy_resolution_reuse_in_valuation(db_session):
    """ValuationService uses pre-resolved taxonomy when provided."""
    val_service = ValuationService(session=db_session)
    req = ValuationRequest(
        brand="Maruti", model="Swift", manufacturing_year=2021,
        km_driven=25000, fuel_type="Petrol", transmission_type="Manual", city="Delhi"
    )

    tax_req = CanonicalResolutionRequest(brand="Maruti", model="Swift", year=2021)
    resolved = val_service.taxonomy_resolver.resolve(tax_req)
    assert resolved.canonical_vehicle_id.startswith("maruti-suzuki::swift::gen-3-2018::2021")

    resp = val_service.evaluate_valuation(req, resolved_taxonomy=resolved)
    assert resp.canonical_vehicle_id == resolved.canonical_vehicle_id
    assert resp.estimated_fair_market_value is not None
    assert resp.estimated_fair_market_value > 0


def test_comparison_query_count_reduction(db_session):
    """Verifies that a 2-vehicle comparison executes under 25 queries (baseline was 36-44)."""
    comp_service = ComparisonService(session=db_session)

    # Hook query counter to engine
    query_log = []
    def record_query(conn, cursor, statement, parameters, context, executemany):
        query_log.append(statement)

    listener = event.listen(db_session.bind, "before_cursor_execute", record_query)

    req = ComparisonRequest(
        vehicles=[
            ComparisonVehicle(
                brand="Maruti", model="Swift", manufacturing_year=2021,
                fuel_type="Petrol", transmission_type="Manual", km_driven=25000,
            ),
            ComparisonVehicle(
                brand="Hyundai", model="Creta", manufacturing_year=2022,
                fuel_type="Petrol", transmission_type="Manual", km_driven=30000,
            ),
        ]
    )

    query_log.clear()
    resp = comp_service.compare(req)
    total_queries = len(query_log)

    event.remove(db_session.bind, "before_cursor_execute", record_query)

    # Assert significant query reduction
    assert total_queries <= 25, f"Expected <= 25 queries, got {total_queries}"
    assert resp.specifications is not None
    assert len(resp.specifications) == len(SPEC_DEFINITIONS)


def test_comparison_semantic_equivalence(db_session):
    """Verifies that optimized comparison maintains exact spec values and winners."""
    comp_service = ComparisonService(session=db_session)
    req = ComparisonRequest(
        vehicles=[
            ComparisonVehicle(
                brand="Maruti", model="Swift", manufacturing_year=2021,
                fuel_type="Petrol", transmission_type="Manual", km_driven=25000,
            ),
            ComparisonVehicle(
                brand="Hyundai", model="Creta", manufacturing_year=2022,
                fuel_type="Petrol", transmission_type="Manual", km_driven=30000,
            ),
        ]
    )

    resp = comp_service.compare(req)

    # Check vehicle summaries
    assert len(resp.vehicles) == 2
    assert resp.vehicles[0]["canonical_vehicle_id"].startswith("maruti-suzuki::swift::gen-3-2018::2021")
    assert resp.vehicles[1]["canonical_vehicle_id"].startswith("hyundai::creta::gen-2-2020::2022")

    # Check specific specifications
    spec_map = {s.spec_key: s for s in resp.specifications}

    # Displacement: Swift 1197cc vs Creta 1497cc (directionless spec -> winner is None)
    disp_spec = spec_map["engine_displacement_cc"]
    assert disp_spec.values[0].value == 1197
    assert disp_spec.values[1].value == 1497
    assert disp_spec.winner_index is None

    # Power: Swift 89 bhp vs Creta 113.4 bhp (higher is better -> Creta wins)
    power_spec = spec_map["power_bhp"]
    assert power_spec.values[0].value == 89.0
    assert power_spec.values[1].value == 113.4
    assert power_spec.winner_index == 1

    # Mileage / Claimed efficiency: Swift 23.2 km/l vs Creta 16.9 km/l
    eff_spec = spec_map["claimed_efficiency_kmpl"]
    assert eff_spec.values[0].value == 23.2
    assert eff_spec.values[1].value == 16.9
    assert eff_spec.winner_index == 0 # Swift has better mileage

    # NCAP stars: Swift 2 vs Creta 3
    ncap_spec = spec_map["ncap_stars"]
    assert ncap_spec.values[0].value == 2
    assert ncap_spec.values[1].value == 3
    assert ncap_spec.winner_index == 1 # Creta has more stars


def test_comparison_missing_specs_graceful(db_session):
    """Verifies that comparing vehicles with missing specs (e.g. i20) produces INSUFFICIENT_DATA."""
    comp_service = ComparisonService(session=db_session)
    req = ComparisonRequest(
        vehicles=[
            ComparisonVehicle(
                brand="Maruti", model="Swift", manufacturing_year=2021,
                fuel_type="Petrol", transmission_type="Manual", km_driven=25000,
            ),
            ComparisonVehicle(
                brand="Hyundai", model="i20", manufacturing_year=2020,
                fuel_type="Petrol", transmission_type="Manual", km_driven=35000,
            ),
        ]
    )

    resp = comp_service.compare(req)
    assert len(resp.vehicles) == 2

    spec_map = {s.spec_key: s for s in resp.specifications}
    ncap_spec = spec_map["ncap_stars"]
    # Vehicle 1 (i20) has no NCAP rating in DB or static fallback
    assert ncap_spec.values[1].value is None
    assert ncap_spec.values[1].display_value == "Data unavailable"
    assert ncap_spec.values[1].evidence_state == EvidenceState.INSUFFICIENT_DATA


def test_concurrent_comparisons_thread_safety():
    """Verifies that concurrent comparison executions across multiple worker threads do not collide."""
    req = ComparisonRequest(
        vehicles=[
            ComparisonVehicle(
                brand="Maruti", model="Swift", manufacturing_year=2021,
                fuel_type="Petrol", transmission_type="Manual", km_driven=25000,
            ),
            ComparisonVehicle(
                brand="Hyundai", model="Creta", manufacturing_year=2022,
                fuel_type="Petrol", transmission_type="Manual", km_driven=30000,
            ),
        ]
    )

    def run_worker():
        thread_session = ScopedSession()
        try:
            svc = ComparisonService(session=thread_session)
            resp = svc.compare(req)
            assert resp.specifications is not None
            assert len(resp.vehicles) == 2
            return True
        finally:
            thread_session.close()

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(run_worker) for _ in range(10)]
        results = [f.result() for f in futures]

    assert all(results)
    assert len(results) == 10
