"""
CarSpective — Phase 20E Concurrency & Session Lifecycle Regression Suite
Verifies thread-scoped database session isolation across process-level service singletons,
proving that concurrent worker threads resolve distinct sessions without contention,
cross-thread state leakage, or teardown disruption.
"""

import threading
import pytest
from typing import List, Dict, Any

from server.infrastructure.database import ScopedSession
from server.api.v1.valuation_routes import get_valuation_service
from server.api.v1.comparison_routes import get_comparison_service
from server.domain.valuation.service import ValuationService
from server.domain.valuation.models import ValuationRequest
from server.domain.comparison.service import ComparisonService
from server.domain.comparison.models import ComparisonRequest, ComparisonVehicle
from server.domain.scoring.service import ScoringService
from server.domain.recommendation.service import RecommendationService
from server.repositories.taxonomy_repository import TaxonomyRepository


def test_valuation_service_distinct_session_per_thread():
    """Verify ValuationService singleton resolves unique thread-scoped sessions across threads."""
    val_service = get_valuation_service()
    sessions = {}
    threads = []

    def worker(tid: int):
        # Resolve repo session on this thread
        sess = val_service.taxonomy_resolver.repo.session
        sessions[tid] = id(sess)
        ScopedSession.remove()

    for i in range(5):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # All session object IDs across distinct threads must be distinct
    unique_session_ids = set(sessions.values())
    assert len(unique_session_ids) == 5, f"Expected 5 distinct sessions, got {len(unique_session_ids)}: {sessions}"


def test_comparison_service_distinct_session_per_thread():
    """Verify ComparisonService singleton and child services resolve unique sessions across threads."""
    cmp_service = get_comparison_service()
    sessions = {}
    threads = []

    def worker(tid: int):
        cmp_sess_id = id(cmp_service.session)
        score_sess_id = id(cmp_service.scoring_service.session)
        rec_sess_id = id(cmp_service.recommendation_service.session)
        know_sess_id = id(cmp_service.knowledge_service.session)
        sessions[tid] = {
            "cmp": cmp_sess_id,
            "score": score_sess_id,
            "rec": rec_sess_id,
            "know": know_sess_id,
        }
        ScopedSession.remove()

    for i in range(5):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # Within each thread, all child services on default scoped session resolve the same thread-local session
    for tid, sess_map in sessions.items():
        assert sess_map["cmp"] == sess_map["score"] == sess_map["rec"] == sess_map["know"], (
            f"Thread {tid} child services did not share thread-local session: {sess_map}"
        )

    # Across different threads, the session IDs must be unique
    cmp_ids = {s["cmp"] for s in sessions.values()}
    assert len(cmp_ids) == 5, f"Expected 5 distinct thread sessions, got {len(cmp_ids)}: {cmp_ids}"


def test_concurrent_valuation_inference_barrier():
    """Verify 10 threads concurrently executing evaluate_valuation run cleanly with zero contention."""
    val_service = get_valuation_service()
    num_threads = 10
    barrier = threading.Barrier(num_threads)
    results = [None] * num_threads
    errors = []

    req = ValuationRequest(
        brand="Hyundai",
        model="Creta",
        manufacturing_year=2020,
        km_driven=45000,
        fuel_type="Petrol",
        transmission_type="Manual",
        variant="SX",
    )

    def worker(index: int):
        try:
            barrier.wait(timeout=5.0)
            res = val_service.evaluate_valuation(req)
            results[index] = res
        except Exception as e:
            errors.append((index, e))
        finally:
            ScopedSession.remove()

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Concurrent valuation errors encountered: {errors}"
    assert len([r for r in results if r is not None]) == num_threads

    # Verify deterministic output across all threads
    first_val = results[0].estimated_fair_market_value
    for r in results:
        assert r.estimated_fair_market_value == first_val
        assert r.vehicle_resolution_status in ("EXACT_MATCH", "FUZZY_MATCH")
        assert r.confidence_state != "INSUFFICIENT_DATA"


def test_teardown_isolation_between_threads():
    """Verify ScopedSession.remove() on Thread-1 does not invalidate or close Thread-2's session."""
    val_service = get_valuation_service()
    event_thread1_done = threading.Event()
    thread2_success = []
    thread2_error = []

    def thread1_worker():
        _ = val_service.taxonomy_resolver.repo.session
        # Simulate request completion and teardown
        ScopedSession.remove()
        event_thread1_done.set()

    def thread2_worker():
        # Wait until Thread-1 has completely removed its session
        event_thread1_done.wait(timeout=5.0)
        try:
            req = ValuationRequest(
                brand="Maruti",
                model="Swift",
                manufacturing_year=2019,
                km_driven=35000,
                fuel_type="Petrol",
                transmission_type="Manual",
                variant="VXI",
            )
            res = val_service.evaluate_valuation(req)
            assert res.estimated_fair_market_value is not None
            thread2_success.append(True)
        except Exception as e:
            thread2_error.append(e)
        finally:
            ScopedSession.remove()

    t1 = threading.Thread(target=thread1_worker)
    t2 = threading.Thread(target=thread2_worker)

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    assert not thread2_error, f"Thread 2 failed after Thread 1 teardown: {thread2_error}"
    assert thread2_success == [True]


def test_explicit_session_injection_backwards_compatibility():
    """Verify that explicitly passing a session pins the session and preserves backwards compatibility."""
    explicit_sess = ScopedSession()
    try:
        repo = TaxonomyRepository(session=explicit_sess)
        assert repo.session is explicit_sess

        val_svc = ValuationService(session=explicit_sess)
        assert val_svc.session is explicit_sess

        cmp_svc = ComparisonService(session=explicit_sess)
        assert cmp_svc.session is explicit_sess
        assert cmp_svc.scoring_service.session is explicit_sess
    finally:
        ScopedSession.remove()


def test_concurrent_comparison_barrier():
    """Verify concurrent comparison calls across 4 threads run cleanly with independent sessions."""
    cmp_service = get_comparison_service()
    num_threads = 4
    barrier = threading.Barrier(num_threads)
    results = [None] * num_threads
    errors = []

    req = ComparisonRequest(
        mode="general",
        vehicles=[
            ComparisonVehicle(
                brand="Hyundai",
                model="Creta",
                manufacturing_year=2020,
                km_driven=45000,
                fuel_type="Petrol",
                transmission_type="Manual",
                variant="SX",
            ),
            ComparisonVehicle(
                brand="Kia",
                model="Seltos",
                manufacturing_year=2020,
                km_driven=40000,
                fuel_type="Petrol",
                transmission_type="Manual",
                variant="HTX",
            ),
        ]
    )

    def worker(index: int):
        try:
            barrier.wait(timeout=5.0)
            res = cmp_service.compare(req)
            results[index] = res
        except Exception as e:
            errors.append((index, e))
        finally:
            ScopedSession.remove()

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Concurrent comparison errors encountered: {errors}"
    assert len([r for r in results if r is not None]) == num_threads
    for r in results:
        assert len(r.vehicles) == 2
        assert r.overall_result is not None

