"""
CarSpective Phase 20E — Targeted Taxonomy Caching Remediation Tests
Verifies that:
1. Cached and uncached search results are 100% equivalent.
2. Cached search avoids repeated database reads (0 SQL queries on cache hits).
3. Taxonomy hierarchy cache invalidation works cleanly and thread-safely.
4. Cached and uncached canonical resolution results are 100% equivalent.
5. Canonical resolution cache hits avoid repeated database reads (0 SQL queries).
6. Ambiguous and unresolved resolution inputs are safely handled and cached without degradation.
7. Cache returns deep-copied models preventing cross-request mutation leakage.
8. Database/session failures do not poison the canonical resolution cache.
9. Concurrent access across worker threads is thread-safe with zero detached-session errors.
10. Valuation outputs and schemas remain completely compatible with resolution caching.
"""

import pytest
import threading
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import event

from server.infrastructure.database import ScopedSession
from server.repositories.taxonomy_repository import TaxonomyRepository, ManufacturerSnapshot
from server.domain.knowledge.service import KnowledgeService
from server.domain.taxonomy.resolver import (
    CanonicalResolver,
    make_canonical_cache_key,
    CanonicalResolutionCache,
)
from server.schemas.taxonomy import (
    CanonicalResolutionRequest,
    CanonicalResolutionResult,
    ResolutionStatus,
)
from server.domain.valuation.service import ValuationService
from server.domain.valuation.models import ValuationRequest


class QueryCounter:
    """Helper context manager to count executed SQL queries on an active connection."""
    def __init__(self, connection):
        self._connection = connection
        self.queries = []

    def __enter__(self):
        self.queries.clear()
        event.listen(self._connection, "before_cursor_execute", self._callback)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        event.remove(self._connection, "before_cursor_execute", self._callback)

    def _callback(self, conn, cursor, statement, parameters, context, executemany):
        self.queries.append(statement)

    @property
    def count(self):
        return len(self.queries)


@pytest.fixture(autouse=True)
def reset_caches():
    """Ensure caches are flushed before and after each test."""
    TaxonomyRepository.invalidate_hierarchy_cache()
    CanonicalResolver.clear_resolution_cache()
    yield
    TaxonomyRepository.invalidate_hierarchy_cache()
    CanonicalResolver.clear_resolution_cache()


# -----------------------------------------------------------------------------
# Part A: Search Taxonomy Hierarchy Cache Tests
# -----------------------------------------------------------------------------

def test_cached_and_uncached_search_results_equivalent(db_session: Session):
    """Verify that search results with use_cache=True and use_cache=False are identical."""
    service = KnowledgeService(session=db_session)
    
    test_queries = [
        {"query": "Swift"},
        {"query": "Creta"},
        {"query": "Nexon"},
        {"query": "City"},
        {"brand": "Hyundai"},
        {"brand": "Maruti Suzuki", "model": "Swift"},
        {"query": "Diesel Manual"},
        {"query": "NonexistentVehicleModelXYZ"},
    ]
    
    for q_args in test_queries:
        uncached_results = service.search_vehicles(**q_args, use_cache=False)
        cached_results = service.search_vehicles(**q_args, use_cache=True)
        assert cached_results == uncached_results, f"Mismatch for query arguments: {q_args}"


def test_cached_search_avoids_database_reads(db_session: Session):
    """Verify that search hits on the hierarchy cache issue exactly 0 database queries."""
    connection = db_session.connection()
    service = KnowledgeService(session=db_session)
    
    # Cold search: populates cache
    with QueryCounter(connection) as qc_cold:
        res1 = service.search_vehicles(query="Swift", use_cache=True)
    assert qc_cold.count > 0, "Cold search should load hierarchy from DB"
    assert len(res1) > 0
    
    # Warm search: must issue exactly 0 database queries!
    with QueryCounter(connection) as qc_warm:
        res2 = service.search_vehicles(query="Swift", use_cache=True)
    assert qc_warm.count == 0, f"Expected 0 queries on warm cache, got {qc_warm.count}"
    assert res1 == res2
    
    # Warm search with different query: still 0 database queries!
    with QueryCounter(connection) as qc_warm2:
        res3 = service.search_vehicles(query="Creta", use_cache=True)
    assert qc_warm2.count == 0, f"Expected 0 queries for second query, got {qc_warm2.count}"
    assert len(res3) > 0


def test_search_taxonomy_invalidation(db_session: Session):
    """Verify that invalidation bumps the version and reloads from DB on next access."""
    connection = db_session.connection()
    v1 = TaxonomyRepository.get_hierarchy_cache_version()
    repo = TaxonomyRepository(session=db_session)
    
    # Populate cache
    snapshot = repo.get_taxonomy_hierarchy_snapshot()
    assert isinstance(snapshot, tuple)
    assert len(snapshot) > 0
    assert isinstance(snapshot[0], ManufacturerSnapshot)
    
    # Invalidate
    TaxonomyRepository.invalidate_hierarchy_cache()
    v2 = TaxonomyRepository.get_hierarchy_cache_version()
    assert v2 == v1 + 1
    
    # Next call issues queries to reload
    with QueryCounter(connection) as qc:
        snapshot2 = repo.get_taxonomy_hierarchy_snapshot()
    assert qc.count > 0, "Cache invalidation should trigger DB reload on next call"
    assert len(snapshot2) == len(snapshot)


# -----------------------------------------------------------------------------
# Part B: Canonical Resolution Cache Tests
# -----------------------------------------------------------------------------

def test_cached_and_uncached_canonical_resolution_equivalent(db_session: Session):
    """Verify that canonical resolution outputs match whether cached or uncached."""
    repo = TaxonomyRepository(session=db_session)
    resolver = CanonicalResolver(repo)
    
    requests = [
        CanonicalResolutionRequest(brand="Maruti Suzuki", model="Swift", year=2021),
        CanonicalResolutionRequest(brand="Hyundai", model="Creta", year=2020),
        CanonicalResolutionRequest(brand="Tata", model="Nexon", year=2022),
        CanonicalResolutionRequest(brand="Honda", model="City", year=2019, fuel_type="Petrol", transmission_type="Manual"),
        CanonicalResolutionRequest(brand="UnknownBrand", model="UnknownModel"),
    ]
    
    for r in requests:
        uncached = resolver.resolve(r, use_cache=False)
        cached = resolver.resolve(r, use_cache=True)
        assert cached.status == uncached.status
        assert cached.canonical_vehicle_id == uncached.canonical_vehicle_id
        assert cached.confidence_score == uncached.confidence_score
        assert cached.hierarchy == uncached.hierarchy
        assert cached.matched_tier == uncached.matched_tier
        assert cached.match_notes == uncached.match_notes


def test_canonical_resolution_cache_hits_avoid_db_reads(db_session: Session):
    """Verify that repeated resolution requests issue 0 database queries and increment hit count."""
    connection = db_session.connection()
    repo = TaxonomyRepository(session=db_session)
    resolver = CanonicalResolver(repo)
    req = CanonicalResolutionRequest(brand="Maruti Suzuki", model="Swift", year=2021)
    
    # 1. Cold resolution: cache miss
    with QueryCounter(connection) as qc_cold:
        res1 = resolver.resolve(req)
    assert qc_cold.count > 0, "Cold resolution should issue SQL queries"
    assert res1.status in (ResolutionStatus.EXACT_MATCH, ResolutionStatus.PARTIAL_MATCH)
    
    stats1 = CanonicalResolver.get_resolution_cache_stats()
    assert stats1["hits"] == 0
    assert stats1["misses"] == 1
    
    # 2. Warm resolution: cache hit (0 database queries)
    with QueryCounter(connection) as qc_warm:
        res2 = resolver.resolve(req)
    assert qc_warm.count == 0, f"Expected 0 queries on warm resolution, got {qc_warm.count}"
    assert res2.canonical_vehicle_id == res1.canonical_vehicle_id
    
    stats2 = CanonicalResolver.get_resolution_cache_stats()
    assert stats2["hits"] == 1
    assert stats2["misses"] == 1


def test_canonical_resolution_ambiguous_and_unresolved_inputs(db_session: Session):
    """Verify that ambiguous matches and unresolved inputs are safely and deterministically cached."""
    connection = db_session.connection()
    repo = TaxonomyRepository(session=db_session)
    resolver = CanonicalResolver(repo)
    
    # Unresolved input
    unresolved_req = CanonicalResolutionRequest(brand="MarsRover", model="Curiosity")
    res_unres = resolver.resolve(unresolved_req)
    assert res_unres.status == ResolutionStatus.UNRESOLVED
    assert res_unres.confidence_score == 0.0
    
    # Hit cache on unresolved
    with QueryCounter(connection) as qc:
        res_unres_cached = resolver.resolve(unresolved_req)
    assert qc.count == 0
    assert res_unres_cached.status == ResolutionStatus.UNRESOLVED
    
    # Ambiguous input (multi-generation model without year)
    ambiguous_req = CanonicalResolutionRequest(brand="Maruti Suzuki", model="Swift")
    res_ambig = resolver.resolve(ambiguous_req)
    if res_ambig.status == ResolutionStatus.AMBIGUOUS_MATCH:
        assert res_ambig.ambiguous_candidates is not None
        with QueryCounter(connection) as qc:
            res_ambig_cached = resolver.resolve(ambiguous_req)
        assert qc.count == 0
        assert res_ambig_cached.ambiguous_candidates == res_ambig.ambiguous_candidates


def test_canonical_resolution_no_mutation_leakage(db_session: Session):
    """Verify that mutating a returned CanonicalResolutionResult does not leak into subsequent cache returns."""
    repo = TaxonomyRepository(session=db_session)
    resolver = CanonicalResolver(repo)
    req = CanonicalResolutionRequest(brand="Maruti Suzuki", model="Swift", year=2021)
    
    res1 = resolver.resolve(req)
    original_notes_count = len(res1.match_notes)
    
    # Mutate the returned object
    res1.match_notes.append("MUTATION_POISON_NOTE")
    assert len(res1.match_notes) == original_notes_count + 1
    
    # Fetch from cache again
    res2 = resolver.resolve(req)
    assert len(res2.match_notes) == original_notes_count
    assert "MUTATION_POISON_NOTE" not in res2.match_notes


def test_database_failure_does_not_poison_cache(db_session: Session):
    """Verify that database errors during resolution raise cleanly and are not cached."""
    repo = TaxonomyRepository(session=db_session)
    resolver = CanonicalResolver(repo)
    req = CanonicalResolutionRequest(brand="Tata", model="Nexon", year=2022)
    
    # Monkey-patch repo.find_manufacturer to simulate a transient operational error
    original_find = repo.find_manufacturer
    def failing_find(name):
        raise RuntimeError("Transient SQLite Connection Failure")
    repo.find_manufacturer = failing_find
    
    with pytest.raises(RuntimeError, match="Transient SQLite Connection Failure"):
        resolver.resolve(req)
        
    # Restore original method
    repo.find_manufacturer = original_find
    
    # Cache must NOT have cached the failure
    key = make_canonical_cache_key(req)
    assert resolver._cache.get(key) is None
    
    # Subsequent resolution succeeds and caches valid result
    res_recovered = resolver.resolve(req)
    assert res_recovered.status in (ResolutionStatus.EXACT_MATCH, ResolutionStatus.PARTIAL_MATCH)
    assert resolver._cache.get(key) is not None


# -----------------------------------------------------------------------------
# Part C: Concurrency and Thread-Safety Tests
# -----------------------------------------------------------------------------

def test_concurrent_search_and_resolution_thread_safety(db_session: Session):
    """Verify thread safety under concurrent multi-threaded execution."""
    service = KnowledgeService(session=db_session)
    resolver = CanonicalResolver(TaxonomyRepository(session=db_session))
    
    errors = []
    
    def worker_task(thread_id: int):
        try:
            # 1. Concurrent search
            queries = ["Swift", "Creta", "Nexon", "City", "Baleno"]
            q = queries[thread_id % len(queries)]
            s_results = service.search_vehicles(query=q, use_cache=True)
            assert len(s_results) > 0
            
            # 2. Concurrent resolution
            reqs = [
                CanonicalResolutionRequest(brand="Maruti Suzuki", model="Swift", year=2021),
                CanonicalResolutionRequest(brand="Hyundai", model="Creta", year=2020),
                CanonicalResolutionRequest(brand="Tata", model="Nexon", year=2022),
            ]
            r = reqs[thread_id % len(reqs)]
            c_res = resolver.resolve(r, use_cache=True)
            assert c_res.status in (ResolutionStatus.EXACT_MATCH, ResolutionStatus.PARTIAL_MATCH)
        except Exception as e:
            errors.append(e)
        finally:
            ScopedSession.remove()
            
    threads = [threading.Thread(target=worker_task, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
        
    assert len(errors) == 0, f"Thread errors encountered: {errors}"


# -----------------------------------------------------------------------------
# Part D: Valuation Service Compatibility Tests
# -----------------------------------------------------------------------------

def test_valuation_service_with_resolution_cache(db_session: Session):
    """Verify that ValuationService runs seamlessly with the canonical resolution cache."""
    val_service = ValuationService(session=db_session)
    req = ValuationRequest(
        brand="Maruti Suzuki",
        model="Swift",
        manufacturing_year=2021,
        km_driven=25000,
        fuel_type="Petrol",
        transmission_type="Manual",
        city="Delhi"
    )
    
    # First call: populates resolution cache
    resp1 = val_service.evaluate_valuation(req)
    assert resp1.estimated_fair_market_value is not None
    assert resp1.expected_fair_market_range is not None
    assert resp1.confidence_state in ["HIGH_CONFIDENCE", "MODERATE_CONFIDENCE"]
    
    # Second call: uses cached resolution, produces identical valuation
    resp2 = val_service.evaluate_valuation(req)
    assert resp2.estimated_fair_market_value == resp1.estimated_fair_market_value
    assert resp2.expected_fair_market_range.lower_bound == resp1.expected_fair_market_range.lower_bound
    assert resp2.expected_fair_market_range.upper_bound == resp1.expected_fair_market_range.upper_bound
    assert resp2.canonical_vehicle_id == resp1.canonical_vehicle_id
    d1 = resp1.model_dump(exclude={"valuation_timestamp"})
    d2 = resp2.model_dump(exclude={"valuation_timestamp"})
    assert d1 == d2
